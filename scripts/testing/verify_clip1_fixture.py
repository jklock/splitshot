#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from splitshot.analysis.detection import analyze_video_audio
from splitshot.media.probe import probe_video


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--min-shots", type=int, default=1)
    parser.add_argument("--min-duration", type=float, default=1.0)
    args = parser.parse_args()

    video = args.video.resolve()
    if not video.exists():
        raise FileNotFoundError(f"Clip1 fixture missing: {video}")

    asset = probe_video(video)
    analysis = analyze_video_audio(video, threshold=0.35)
    duration_seconds = (asset.duration_ms or 0) / 1000.0
    payload = {
        "path": str(video),
        "size_bytes": video.stat().st_size,
        "duration_seconds": round(duration_seconds, 3),
        "width": asset.width,
        "height": asset.height,
        "beep_time_ms": analysis.beep_time_ms,
        "shot_count": len(analysis.shots),
        "shot_times_ms": [shot.time_ms for shot in analysis.shots[:20]],
    }
    print(json.dumps(payload, indent=2))

    if duration_seconds < args.min_duration:
        raise SystemExit(
            f"Clip1 duration too short: {duration_seconds:.3f}s < {args.min_duration:.3f}s"
        )
    if analysis.beep_time_ms is None:
        raise SystemExit("Clip1 fixture did not produce a detectable beep")
    if len(analysis.shots) < args.min_shots:
        raise SystemExit(
            f"Clip1 fixture produced {len(analysis.shots)} shots; need at least {args.min_shots}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
