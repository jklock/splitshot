#!/usr/bin/env python3
"""Build the release proof video from live feature audits and rendered outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _tool(environment_name: str, fallback: str) -> str:
    requested = os.environ.get(environment_name, fallback)
    resolved = shutil.which(requested)
    if resolved:
        return resolved
    candidate = Path(requested)
    if candidate.is_file():
        return str(candidate)
    raise FileNotFoundError(f"Required media tool not found: {requested}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _probe(path: Path, ffprobe: str) -> dict[str, Any]:
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def _duration(metadata: dict[str, Any]) -> float:
    return float((metadata.get("format") or {}).get("duration") or 0.0)


def _has_audio(metadata: dict[str, Any]) -> bool:
    return any(item.get("codec_type") == "audio" for item in metadata.get("streams") or [])


def _normalize_segment(
    source: Path,
    destination: Path,
    *,
    playback_rate: float,
    ffmpeg: str,
    ffprobe: str,
) -> float:
    metadata = _probe(source, ffprobe)
    source_duration = _duration(metadata)
    if source_duration <= 0:
        raise RuntimeError(f"Video segment has no duration: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    video_filter = (
        "scale=1280:900:force_original_aspect_ratio=decrease,"
        "pad=1280:900:(ow-iw)/2:(oh-ih)/2:black,"
        f"fps=30,setpts=PTS/{playback_rate:g},format=yuv420p"
    )
    command = [ffmpeg, "-y", "-v", "error", "-i", str(source)]
    if _has_audio(metadata):
        command.extend(
            [
                "-filter_complex",
                f"[0:v]{video_filter}[v];[0:a]aresample=48000[a]",
                "-map",
                "[v]",
                "-map",
                "[a]",
            ]
        )
    else:
        normalized_duration = source_duration / playback_rate
        command.extend(
            [
                "-f",
                "lavfi",
                "-t",
                f"{normalized_duration:.6f}",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-filter_complex",
                f"[0:v]{video_filter}[v]",
                "-map",
                "[v]",
                "-map",
                "1:a",
                "-shortest",
            ]
        )
    command.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "24",
            "-g",
            "60",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(destination),
        ]
    )
    subprocess.run(command, check=True)
    duration = _duration(_probe(destination, ffprobe))
    if duration <= 0:
        raise RuntimeError(f"Normalized video segment has no duration: {destination}")
    return duration


def _manifest_cases(manifest_path: Path) -> dict[str, list[str]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        str(shard["id"]): [str(case_id) for case_id in shard.get("cases") or []]
        for shard in manifest.get("shards") or []
    }


def build_video(artifact_root: Path, manifest_path: Path) -> dict[str, Any]:
    artifact_root = artifact_root.resolve()
    ffmpeg = _tool("SPLITSHOT_PACKAGED_FFMPEG", "ffmpeg")
    ffprobe = _tool("SPLITSHOT_PACKAGED_FFPROBE", "ffprobe")
    shard_cases = _manifest_cases(manifest_path)
    all_ui_cases = [
        case_id
        for shard, cases in shard_cases.items()
        if shard != "rendered-output"
        for case_id in cases
    ]
    output_cases = shard_cases.get("rendered-output", [])
    segments = [
        {
            "id": "installed-workflow",
            "kind": "live-feature-use",
            "path": artifact_root / "browser-workflow.webm",
            "playback_rate": 8.0,
            "cases": all_ui_cases,
        },
        {
            "id": "ui-surface-audit",
            "kind": "live-feature-use",
            "path": artifact_root / "browser-audits" / "ui-surface.webm",
            "playback_rate": 1.0,
            "cases": shard_cases.get("shell", []),
        },
        {
            "id": "interaction-audit",
            "kind": "live-feature-use",
            "path": artifact_root / "browser-audits" / "interaction.webm",
            "playback_rate": 1.0,
            "cases": all_ui_cases,
        },
        {
            "id": "value-control-audit",
            "kind": "live-feature-use",
            "path": artifact_root / "browser-audits" / "value-controls.webm",
            "playback_rate": 1.0,
            "cases": all_ui_cases,
        },
        {
            "id": "remaining-control-audit",
            "kind": "live-feature-use",
            "path": artifact_root / "browser-audits" / "remaining-controls.webm",
            "playback_rate": 1.0,
            "cases": all_ui_cases,
        },
        {
            "id": "rendered-individual-output",
            "kind": "rendered-output",
            "path": artifact_root / "exports" / "e2e-export-test.mp4",
            "playback_rate": 1.0,
            "cases": output_cases,
        },
        {
            "id": "rendered-combined-output",
            "kind": "rendered-output",
            "path": artifact_root / "exports" / "combined-output.mp4",
            "playback_rate": 1.0,
            "cases": output_cases,
        },
    ]
    for segment in segments:
        path = Path(segment["path"])
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Missing full-feature video segment: {path}")

    work_root = artifact_root / ".full-feature-video"
    shutil.rmtree(work_root, ignore_errors=True)
    work_root.mkdir(parents=True)
    timeline: list[dict[str, Any]] = []
    cursor = 0.0
    normalized_paths: list[Path] = []
    for index, segment in enumerate(segments, start=1):
        normalized = work_root / f"{index:02d}-{segment['id']}.mp4"
        duration = _normalize_segment(
            Path(segment["path"]),
            normalized,
            playback_rate=float(segment["playback_rate"]),
            ffmpeg=ffmpeg,
            ffprobe=ffprobe,
        )
        normalized_paths.append(normalized)
        timeline.append(
            {
                "id": segment["id"],
                "kind": segment["kind"],
                "source": str(Path(segment["path"]).relative_to(artifact_root)),
                "source_sha256": _sha256(Path(segment["path"])),
                "playback_rate": segment["playback_rate"],
                "start_s": round(cursor, 6),
                "end_s": round(cursor + duration, 6),
                "duration_s": round(duration, 6),
                "cases": segment["cases"],
            }
        )
        cursor += duration

    concat_file = work_root / "concat.txt"
    concat_file.write_text(
        "".join(f"file '{path.as_posix()}'\n" for path in normalized_paths),
        encoding="utf-8",
    )
    output = artifact_root / "full-feature-validation.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output),
        ],
        check=True,
    )
    output_metadata = _probe(output, ffprobe)
    output_duration = _duration(output_metadata)
    streams = output_metadata.get("streams") or []
    if not any(item.get("codec_type") == "video" for item in streams):
        raise RuntimeError("Full-feature validation video has no video stream")
    if not any(item.get("codec_type") == "audio" for item in streams):
        raise RuntimeError("Full-feature validation video has no audio stream")
    if abs(output_duration - cursor) > max(1.0, cursor * 0.01):
        raise RuntimeError(
            f"Full-feature video duration mismatch: expected {cursor:.3f}, got {output_duration:.3f}"
        )
    covered_cases = sorted({case_id for item in timeline for case_id in item["cases"]})
    expected_cases = sorted(case_id for cases in shard_cases.values() for case_id in cases)
    missing_cases = sorted(set(expected_cases) - set(covered_cases))
    if missing_cases:
        raise RuntimeError(f"Full-feature video has unmapped cases: {missing_cases}")
    payload = {
        "result": "passed",
        "video": output.name,
        "sha256": _sha256(output),
        "duration_s": output_duration,
        "width": 1280,
        "height": 900,
        "segments": timeline,
        "cases": {
            "required": len(expected_cases),
            "covered": len(covered_cases),
            "gaps": 0,
        },
        "rendered_outputs_are_final_segments": [
            item["id"] for item in timeline[-2:]
        ]
        == ["rendered-individual-output", "rendered-combined-output"],
    }
    timeline_path = artifact_root / "full-feature-validation.json"
    timeline_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(work_root, ignore_errors=True)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "tests"
        / "release_validation"
        / "manifest-v1.json",
    )
    args = parser.parse_args()
    payload = build_video(args.artifact_root, args.manifest)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
