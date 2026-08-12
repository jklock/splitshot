#!/usr/bin/env python3
"""Validate the immutable real-data corpus used by packaged release gates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from splitshot.scoring.practiscore import describe_practiscore_file

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS_ROOT = ROOT / "tests" / "release_data"
DEFAULT_MANIFEST = DEFAULT_CORPUS_ROOT / "corpus-v1.json"
EXPECTED_FILES = {"primary.MP4", "secondary.MP4", "practiscore.csv"}
DURATION_TOLERANCE_SECONDS = 0.002


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    passed: bool
    detail: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[str], *, input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        input=input_bytes,
        capture_output=True,
        check=True,
        timeout=120,
    )


def _resolve_tool(name: str) -> str:
    override = os.environ.get(f"SPLITSHOT_PACKAGED_{name.upper()}", "").strip()
    candidate = override or name
    resolved = shutil.which(candidate)
    if resolved:
        return resolved
    path = Path(candidate)
    if path.is_file():
        return str(path)
    raise FileNotFoundError(f"Required {name} executable not found: {candidate}")


def _probe_video(path: Path, ffprobe: str) -> dict[str, Any]:
    result = _run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,codec_name,width,height,r_frame_rate,channels:format=duration",
            "-of",
            "json",
            str(path),
        ]
    )
    return json.loads(result.stdout.decode("utf-8"))


def _decoded_frame_stats(path: Path, duration: float, ffmpeg: str) -> dict[str, float | str]:
    result = _run(
        [
            ffmpeg,
            "-v",
            "error",
            "-ss",
            f"{duration / 2:.6f}",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            "scale=160:90",
            "-pix_fmt",
            "gray",
            "-f",
            "rawvideo",
            "pipe:1",
        ]
    )
    pixels = result.stdout
    if len(pixels) != 160 * 90:
        raise ValueError(f"Decoded frame had {len(pixels)} bytes; expected {160 * 90}")
    minimum = min(pixels)
    maximum = max(pixels)
    mean = sum(pixels) / len(pixels)
    return {
        "minimum": float(minimum),
        "maximum": float(maximum),
        "mean": mean,
        "range": float(maximum - minimum),
        "sha256": hashlib.sha256(pixels).hexdigest(),
    }


def _tracked_files(root: Path, paths: list[Path]) -> set[str]:
    result = _run(
        [
            "git",
            "-C",
            str(root),
            "ls-files",
            "--",
            *[str(path.relative_to(root)) for path in paths],
        ]
    )
    return {line.strip() for line in result.stdout.decode().splitlines() if line.strip()}


def validate(
    *,
    root: Path = ROOT,
    corpus_root: Path = DEFAULT_CORPUS_ROOT,
    manifest_path: Path = DEFAULT_MANIFEST,
) -> dict[str, Any]:
    root = root.resolve()
    corpus_root = corpus_root.resolve()
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared = manifest.get("files")
    if not isinstance(declared, dict) or set(declared) != EXPECTED_FILES:
        raise ValueError(f"Corpus manifest must declare exactly {sorted(EXPECTED_FILES)}")

    checks: list[Check] = []
    paths = [corpus_root / name for name in sorted(EXPECTED_FILES)]
    for path in paths:
        checks.append(Check(f"present:{path.name}", path.is_file(), str(path)))
    if not all(check.passed for check in checks):
        return _report(manifest, checks, {})

    tracked = _tracked_files(root, paths)
    for path in paths:
        relative = str(path.relative_to(root))
        checks.append(Check(f"tracked:{path.name}", relative in tracked, relative))

    actual_files = {path.name for path in corpus_root.iterdir() if path.is_file()}
    expected_on_disk = EXPECTED_FILES | {manifest_path.name}
    checks.append(
        Check(
            "exact-file-set",
            actual_files == expected_on_disk,
            f"actual={sorted(actual_files)} expected={sorted(expected_on_disk)}",
        )
    )

    file_evidence: dict[str, Any] = {}
    for path in paths:
        expected = declared[path.name]
        size = path.stat().st_size
        digest = _sha256(path)
        checks.extend(
            [
                Check(f"nonempty:{path.name}", size > 0, f"bytes={size}"),
                Check(f"size:{path.name}", size == int(expected["bytes"]), f"bytes={size}"),
                Check(
                    f"sha256:{path.name}",
                    digest == str(expected["sha256"]),
                    digest,
                ),
            ]
        )
        file_evidence[path.name] = {"bytes": size, "sha256": digest}

    ffprobe = _resolve_tool("ffprobe")
    ffmpeg = _resolve_tool("ffmpeg")
    decoded_hashes: set[str] = set()
    for name in ("primary.MP4", "secondary.MP4"):
        path = corpus_root / name
        expected = declared[name]
        probe = _probe_video(path, ffprobe)
        streams = list(probe.get("streams") or [])
        video = next((item for item in streams if item.get("codec_type") == "video"), None)
        audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
        duration = float((probe.get("format") or {}).get("duration") or 0)
        expected_video = expected["video"]
        expected_audio = expected["audio"]
        checks.extend(
            [
                Check(f"video-stream:{name}", video is not None, json.dumps(video)),
                Check(f"audio-stream:{name}", audio is not None, json.dumps(audio)),
                Check(
                    f"video-metadata:{name}",
                    bool(video)
                    and video.get("codec_name") == expected_video["codec"]
                    and int(video.get("width") or 0) == expected_video["width"]
                    and int(video.get("height") or 0) == expected_video["height"]
                    and video.get("r_frame_rate") == expected_video["frame_rate"],
                    json.dumps(video, sort_keys=True),
                ),
                Check(
                    f"audio-metadata:{name}",
                    bool(audio)
                    and audio.get("codec_name") == expected_audio["codec"]
                    and int(audio.get("channels") or 0) == expected_audio["channels"],
                    json.dumps(audio, sort_keys=True),
                ),
                Check(
                    f"duration:{name}",
                    abs(duration - float(expected_video["duration_seconds"]))
                    <= DURATION_TOLERANCE_SECONDS,
                    f"seconds={duration}",
                ),
            ]
        )
        frame = _decoded_frame_stats(path, duration, ffmpeg)
        decoded_hashes.add(str(frame["sha256"]))
        checks.append(
            Check(
                f"nonblank-frame:{name}",
                float(frame["maximum"]) >= 32
                and float(frame["mean"]) >= 8
                and float(frame["range"]) >= 16,
                json.dumps(frame, sort_keys=True),
            )
        )
        file_evidence[name].update({"probe": probe, "decoded_frame": frame})

    checks.append(
        Check(
            "videos-distinct",
            len(decoded_hashes) == 2
            and declared["primary.MP4"]["sha256"] != declared["secondary.MP4"]["sha256"],
            f"decoded_frame_hashes={sorted(decoded_hashes)}",
        )
    )

    csv_path = corpus_root / "practiscore.csv"
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        columns = len(reader.fieldnames or [])
    options = describe_practiscore_file(csv_path)
    expected_csv = declared["practiscore.csv"]["csv"]
    csv_valid = (
        options.match_type == expected_csv["match_type"]
        and options.stage_numbers == expected_csv["stages"]
        and len(options.competitors) == expected_csv["competitors"]
        and len(rows) == expected_csv["competitors"]
        and columns == expected_csv["columns"]
    )
    checks.append(
        Check(
            "practiscore-content",
            csv_valid,
            (
                f"match_type={options.match_type} competitors={len(rows)} "
                f"stages={options.stage_numbers} columns={columns}"
            ),
        )
    )
    file_evidence["practiscore.csv"].update(
        {
            "match_type": options.match_type,
            "competitors": len(rows),
            "stages": options.stage_numbers,
            "columns": columns,
        }
    )
    return _report(manifest, checks, file_evidence)


def _report(manifest: dict[str, Any], checks: list[Check], files: dict[str, Any]) -> dict[str, Any]:
    failures = [check.name for check in checks if not check.passed]
    return {
        "schema_version": 1,
        "corpus_revision": manifest.get("corpus_revision", ""),
        "result": "passed" if not failures else "failed",
        "checks": [asdict(check) for check in checks],
        "failed_checks": failures,
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args()
    report = validate(corpus_root=args.corpus_root, manifest_path=args.manifest)
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {key: report[key] for key in ("result", "corpus_revision", "failed_checks")}, indent=2
        )
    )
    return 0 if report["result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
