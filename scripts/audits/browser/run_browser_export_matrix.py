from __future__ import annotations

import argparse
import csv
import json
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from splitshot.browser.server import BrowserControlServer
from splitshot.media.ffmpeg import resolve_media_binary
from splitshot.ui.controller import ProjectController


ROOT = Path(__file__).resolve().parents[3]
TEST_VIDEO_DIR = ROOT / "tests" / "artifacts" / "test_video"
DEFAULT_STAGE_VIDEOS = sorted(TEST_VIDEO_DIR.glob("*.MP4"))

BUILTIN_PRESETS = [
    "source_mp4",
    "universal_vertical",
    "short_form_vertical",
    "youtube_long_1080p",
    "youtube_long_4k",
]

CUSTOM_PROFILES: list[dict[str, Any]] = [
    {
        "id": "custom_m4v_720p_h264",
        "extension": ".m4v",
        "payload": {
            "preset": "custom",
            "quality": "high",
            "aspect_ratio": "16:9",
            "target_width": 1280,
            "target_height": 720,
            "frame_rate": "30",
            "video_codec": "h264",
            "video_bitrate_mbps": 8,
            "audio_codec": "aac",
            "audio_sample_rate": 48000,
            "audio_bitrate_kbps": 192,
            "color_space": "bt709_sdr",
            "two_pass": False,
            "ffmpeg_preset": "fast",
        },
    },
    {
        "id": "custom_mov_square_hevc",
        "extension": ".mov",
        "payload": {
            "preset": "custom",
            "quality": "medium",
            "aspect_ratio": "1:1",
            "target_width": 1080,
            "target_height": 1080,
            "frame_rate": "30",
            "video_codec": "hevc",
            "video_bitrate_mbps": 8,
            "audio_codec": "aac",
            "audio_sample_rate": 44100,
            "audio_bitrate_kbps": 96,
            "color_space": "bt709_sdr",
            "two_pass": False,
            "ffmpeg_preset": "fast",
        },
    },
    {
        "id": "custom_mkv_4x5_h264",
        "extension": ".mkv",
        "payload": {
            "preset": "custom",
            "quality": "high",
            "aspect_ratio": "4:5",
            "target_width": 1080,
            "target_height": 1350,
            "frame_rate": "60",
            "video_codec": "h264",
            "video_bitrate_mbps": 12,
            "audio_codec": "aac",
            "audio_sample_rate": 48000,
            "audio_bitrate_kbps": 192,
            "color_space": "bt709_sdr",
            "two_pass": False,
            "ffmpeg_preset": "medium",
        },
    },
]


@dataclass(frozen=True, slots=True)
class MatrixCase:
    case_id: str
    primary_video: Path
    merge_mode: str
    merge_videos: tuple[Path, ...]
    export_payload: dict[str, Any]
    output_extension: str
    description: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the SplitShot browser export matrix against the bundled stage videos.",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=ROOT / "artifacts" / "browser-export-matrix-20260413-debug",
        help="Directory where exports, logs, and reports will be written.",
    )
    parser.add_argument(
        "--clip-seconds",
        type=float,
        default=None,
        help="If set, create clipped copies of each stage video at this duration and run the matrix against those inputs.",
    )
    return parser


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=300) as response:
        return json.loads(response.read().decode("utf-8"))


def _fraction_to_float(value: str | None) -> float | None:
    if not value:
        return None
    if "/" in value:
        left, right = value.split("/", 1)
        denominator = float(right)
        if denominator == 0:
            return None
        return float(left) / denominator
    return float(value)


def _probe_video(path: Path) -> dict[str, Any]:
    ffprobe = resolve_media_binary("ffprobe")
    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height,avg_frame_rate,r_frame_rate:format=duration,size",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    stream = payload.get("streams", [{}])[0]
    fmt = payload.get("format", {})
    return {
        "codec_name": stream.get("codec_name"),
        "width": int(stream["width"]) if stream.get("width") is not None else None,
        "height": int(stream["height"]) if stream.get("height") is not None else None,
        "fps": _fraction_to_float(stream.get("avg_frame_rate") or stream.get("r_frame_rate")),
        "duration": float(fmt["duration"]) if fmt.get("duration") is not None else None,
        "size": int(fmt["size"]) if fmt.get("size") is not None else path.stat().st_size,
    }


def _sanitize_case_name(value: str) -> str:
    return value.replace(" ", "-").replace("/", "-").lower()


def _case_output_path(artifact_dir: Path, case: MatrixCase) -> Path:
    return artifact_dir / "exports" / f"{_sanitize_case_name(case.case_id)}{case.output_extension}"


def _create_clip(source: Path, destination: Path, clip_seconds: float) -> None:
    ffmpeg = resolve_media_binary("ffmpeg")
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(source),
            "-t",
            str(clip_seconds),
            "-c",
            "copy",
            str(destination),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def prepare_stage_videos(artifact_dir: Path, clip_seconds: float | None) -> list[Path]:
    if clip_seconds is None:
        return list(DEFAULT_STAGE_VIDEOS)
    if clip_seconds <= 0:
        raise ValueError("clip_seconds must be greater than zero.")

    clips_dir = artifact_dir / "clips"
    clipped_videos: list[Path] = []
    for source in DEFAULT_STAGE_VIDEOS:
        destination = clips_dir / source.name
        if not destination.exists() or destination.stat().st_size <= 0:
            _create_clip(source, destination, clip_seconds)
        clipped_videos.append(destination)
    return clipped_videos


def build_cases(stage_videos: list[Path]) -> list[MatrixCase]:
    cases: list[MatrixCase] = []

    for primary in stage_videos:
        stage_name = primary.stem.lower()
        for preset_id in BUILTIN_PRESETS:
            cases.append(
                MatrixCase(
                    case_id=f"{stage_name}-{preset_id}",
                    primary_video=primary,
                    merge_mode="single",
                    merge_videos=(),
                    export_payload={"preset": preset_id},
                    output_extension=".mp4",
                    description=f"{primary.name} with built-in preset {preset_id}",
                )
            )
        for profile in CUSTOM_PROFILES:
            cases.append(
                MatrixCase(
                    case_id=f"{stage_name}-{profile['id']}",
                    primary_video=primary,
                    merge_mode="single",
                    merge_videos=(),
                    export_payload=dict(profile["payload"]),
                    output_extension=str(profile["extension"]),
                    description=f"{primary.name} with custom export profile {profile['id']}",
                )
            )

    for index, primary in enumerate(stage_videos):
        stage_name = primary.stem.lower()
        next_video = stage_videos[(index + 1) % len(stage_videos)]
        remaining = tuple(video for video in stage_videos if video != primary)
        cases.append(
            MatrixCase(
                case_id=f"{stage_name}-pip-{next_video.stem.lower()}-source_mp4",
                primary_video=primary,
                merge_mode="pip",
                merge_videos=(next_video,),
                export_payload={"preset": "source_mp4"},
                output_extension=".mp4",
                description=f"{primary.name} with {next_video.name} as PiP secondary",
            )
        )
        cases.append(
            MatrixCase(
                case_id=(
                    f"{stage_name}-grid-"
                    f"{'-'.join(video.stem.lower() for video in remaining)}-source_mp4"
                ),
                primary_video=primary,
                merge_mode="grid",
                merge_videos=remaining,
                export_payload={"preset": "source_mp4"},
                output_extension=".mp4",
                description=f"{primary.name} with the remaining stage videos in grid export",
            )
        )

    return cases


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(
    path: Path,
    artifact_dir: Path,
    server_log_path: Path,
    case_results: list[dict[str, Any]],
    stage_videos: list[Path],
    clip_seconds: float | None,
) -> None:
    successes = [result for result in case_results if result["success"]]
    failures = [result for result in case_results if not result["success"]]
    total_bytes = sum(int(result.get("size") or 0) for result in successes)
    clip_line = "- Source inputs: full-length stage videos"
    if clip_seconds is not None:
        clip_line = f"- Source inputs: clipped stage videos ({clip_seconds:g}s per source)"
    primary_video_line = "- Primary videos: " + ", ".join(video.name for video in stage_videos)
    lines = [
        "# Browser Export Matrix",
        "",
        f"Artifact directory: {artifact_dir}",
        f"Activity log: {server_log_path}",
        f"Runner log: {artifact_dir / 'runner.log'}",
        "",
        "## Coverage",
        "",
        primary_video_line,
        clip_line,
        "- Built-in presets: source_mp4, universal_vertical, short_form_vertical, youtube_long_1080p, youtube_long_4k",
        "- Custom containers/profiles: .m4v, .mov, .mkv",
        "- Merge modes: single video, single-secondary PiP, multi-video grid",
        "",
        "## Summary",
        "",
        f"- Cases run: {len(case_results)}",
        f"- Successes: {len(successes)}",
        f"- Failures: {len(failures)}",
        f"- Total bytes written: {total_bytes}",
        "",
        "## Results",
        "",
        "| Case | Mode | Status | Output | Codec | Dimensions | FPS | Duration | Size |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |",
    ]

    for result in case_results:
        dimensions = "--"
        if result.get("width") and result.get("height"):
            dimensions = f"{result['width']}x{result['height']}"
        codec = result.get("codec_name") or "--"
        fps = f"{result['fps']:.2f}" if isinstance(result.get("fps"), float) else "--"
        duration = f"{result['duration']:.3f}" if isinstance(result.get("duration"), float) else "--"
        size = str(result.get("size") or "--")
        status = "pass" if result["success"] else f"fail: {result.get('error', 'unknown')}"
        lines.append(
            f"| {result['case_id']} | {result['merge_mode']} | {status} | {result['output_path']} | {codec} | {dimensions} | {fps} | {duration} | {size} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_case(server_url: str, artifact_dir: Path, case: MatrixCase) -> dict[str, Any]:
    output_path = _case_output_path(artifact_dir, case)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    print(f"[matrix] starting {case.case_id}", flush=True)

    result: dict[str, Any] = {
        "case_id": case.case_id,
        "description": case.description,
        "primary_video": str(case.primary_video),
        "merge_mode": case.merge_mode,
        "merge_videos": [str(path) for path in case.merge_videos],
        "output_path": str(output_path),
        "success": False,
        "error": None,
        "codec_name": None,
        "width": None,
        "height": None,
        "fps": None,
        "duration": None,
        "size": None,
    }

    try:
        _post_json(f"{server_url}api/project/new", {})
        _post_json(f"{server_url}api/import/primary", {"path": str(case.primary_video)})
        for merge_video in case.merge_videos:
            _post_json(f"{server_url}api/import/merge", {"path": str(merge_video)})
        if case.merge_mode == "pip":
            _post_json(
                f"{server_url}api/merge",
                {"layout": "pip", "pip_size_percent": 50, "pip_x": 0.25, "pip_y": 0.75},
            )
        export_payload = {"path": str(output_path), **case.export_payload}
        state = _post_json(f"{server_url}api/export", export_payload)
        export_state = state["project"]["export"]
        if export_state.get("last_error"):
            raise RuntimeError(str(export_state["last_error"]))
        if not output_path.exists() or output_path.stat().st_size <= 0:
            raise RuntimeError("Export output was not created.")
        probe = _probe_video(output_path)
        result.update(probe)
        result["size"] = int(output_path.stat().st_size)
        result["success"] = True
        print(f"[matrix] completed {case.case_id} -> {output_path.name}", flush=True)
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)
        print(f"[matrix] failed {case.case_id}: {exc}", flush=True)

    return result


def main() -> int:
    args = build_parser().parse_args()
    artifact_dir = args.artifact_dir.resolve()
    logs_dir = artifact_dir / "logs"
    exports_dir = artifact_dir / "exports"
    logs_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)

    if not DEFAULT_STAGE_VIDEOS:
        raise SystemExit(f"No bundled test videos were found under {TEST_VIDEO_DIR}.")

    missing = [path for path in DEFAULT_STAGE_VIDEOS if not path.exists()]
    if missing:
        raise SystemExit(f"Missing stage videos: {', '.join(str(path) for path in missing)}")

    stage_videos = prepare_stage_videos(artifact_dir, args.clip_seconds)
    cases = build_cases(stage_videos)
    print(f"[matrix] cases: {len(cases)}", flush=True)

    server = BrowserControlServer(
        controller=ProjectController(),
        host="127.0.0.1",
        port=0,
        log_dir=logs_dir,
        log_level="debug",
    )
    server.start_background(open_browser=False)
    print(f"[matrix] server: {server.url}", flush=True)
    print(f"[matrix] activity log: {server.activity.path}", flush=True)

    case_results: list[dict[str, Any]] = []
    try:
        _get_json(f"{server.url}api/state")
        for case in cases:
            case_results.append(run_case(server.url, artifact_dir, case))
    finally:
        server.shutdown()

    _write_json(artifact_dir / "matrix-results.json", case_results)
    csv_rows = [
        {
            "case_id": result["case_id"],
            "merge_mode": result["merge_mode"],
            "primary_video": result["primary_video"],
            "merge_videos": ";".join(result["merge_videos"]),
            "output_path": result["output_path"],
            "success": result["success"],
            "error": result["error"] or "",
            "codec_name": result["codec_name"] or "",
            "width": result["width"] or "",
            "height": result["height"] or "",
            "fps": result["fps"] or "",
            "duration": result["duration"] or "",
            "size": result["size"] or "",
        }
        for result in case_results
    ]
    _write_csv(artifact_dir / "matrix-results.csv", csv_rows)
    _write_markdown(
        artifact_dir / "matrix-summary.md",
        artifact_dir,
        server.activity.path,
        case_results,
        stage_videos,
        args.clip_seconds,
    )

    failures = [result for result in case_results if not result["success"]]
    print(f"[matrix] successes: {len(case_results) - len(failures)} / {len(case_results)}", flush=True)
    if failures:
        print("[matrix] failed cases:", flush=True)
        for failure in failures:
            print(f"  - {failure['case_id']}: {failure['error']}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())