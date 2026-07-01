"""v107 multi-stage export: dual-angle + BOTH trimmed 5s + overlay.

Each stage uses its video twice. Both primary and merge source trimmed 5s.
- Primary: trimmed first 5s removed (starts at 5s)
- Merge: trimmed first 5s removed (same, starts at 5s — shows offset angle)

v105: basic export, overlay (timer/shots/score/draw)
v106: merge layouts (PIP/SBS/AB), merge source trim derivatives
v107: multi-stage project, per-stage config, combined export, queue model

Usage: uv run python scripts/v107_export_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication

_app = QGuiApplication(sys.argv)

from splitshot.domain.models import (  # noqa: E402
    Project,
    ProjectStage,
    MergeLayout,
    MergeSource,
    MergeSourceTrimDerivative,
    MergeSourceAssetPathKind,
    VideoAsset,
    ExportPreset,
)
from splitshot.export.pipeline import export_project  # noqa: E402


DATA_ROOT = Path("05072026")
OUTPUT_DIR = DATA_ROOT / "Output"
TRIM_SECONDS = 5.0


def probe(path: Path) -> VideoAsset:
    import subprocess
    import json

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        data = json.loads(result.stdout)
        fmt = data.get("format", {})
        vs = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
        if vs:
            fps_str = vs.get("r_frame_rate", "30/1")
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if den != "0" else 30.0
            return VideoAsset(
                path=str(path.resolve()),
                duration_ms=int(float(fmt.get("duration", 0)) * 1000),
                width=int(vs.get("width", 1920)),
                height=int(vs.get("height", 1080)),
                fps=fps,
            )
    except Exception:
        pass
    return VideoAsset(path=str(path.resolve()))


def trim_start(path: Path, out: Path, cut_s: float) -> Path:
    import subprocess

    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            str(cut_s),
            "-i",
            str(path),
            "-c",
            "copy",
            str(out),
        ],
        check=True,
        timeout=120,
    )
    return out


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    videos = {
        2: (DATA_ROOT / "Stage2.MP4").resolve(),
        3: (DATA_ROOT / "Stage3.MP4").resolve(),
        4: (DATA_ROOT / "Stage4.MP4").resolve(),
    }

    trim_dir = OUTPUT_DIR / "trimmed"
    trim_dir.mkdir(exist_ok=True)

    project = Project()
    stages = []
    configs = [
        (2, MergeLayout.PIP, "Stage 2"),
        (3, MergeLayout.SIDE_BY_SIDE, "Stage 3"),
        (4, MergeLayout.ABOVE_BELOW, "Stage 4"),
    ]

    for stage_num, layout, label in configs:
        src = videos[stage_num]
        full_asset = probe(src)
        dur_s = full_asset.duration_ms / 1000

        # Primary: trim first 5s
        primary_path = trim_dir / f"stage{stage_num}-primary-trim{int(TRIM_SECONDS)}s.MP4"
        if not primary_path.exists():
            print(
                f"Trim primary {src.name}: first {int(TRIM_SECONDS)}s removed ({dur_s:.0f}s → {dur_s - TRIM_SECONDS:.0f}s)"
            )
            trim_start(src, primary_path, TRIM_SECONDS)
        primary_asset = probe(primary_path)

        # Merge source: ALSO trim first 5s (separate copy, shows both trimmed)
        merge_path = trim_dir / f"stage{stage_num}-merge-trim{int(TRIM_SECONDS)}s.MP4"
        if not merge_path.exists():
            print(f"Trim merge  {src.name}: first {int(TRIM_SECONDS)}s removed")
            trim_start(src, merge_path, TRIM_SECONDS)
        merge_asset = probe(merge_path)

        merge = MergeSource(
            asset=merge_asset,
            angle_role="follow",
            trim_derivative=MergeSourceTrimDerivative(
                original_path=str(src),
                derivative_path=str(merge_path),
                active_path_kind=MergeSourceAssetPathKind.LOCAL_DERIVATIVE,
            ),
        )
        if layout == MergeLayout.PIP:
            merge.pip_size_percent = 25

        stage = ProjectStage(label=label, order_index=stage_num, primary_media=primary_asset)
        stage.merge.layout = layout
        stage.merge.enabled = True
        stage.added_media = [merge]
        stage.overlay.show_timer = True
        stage.overlay.show_shots = True
        stage.overlay.show_score = True
        stage.overlay.show_draw = True
        stage.overlay.position = "bottom"
        stage.export.preset = ExportPreset.SOURCE
        stage.export.video_bitrate_mbps = 8.0
        stages.append(stage)

    project.stages = stages
    project.active_stage_id = stages[0].id
    project.schema_version = 2

    results = []
    for stage in stages:
        project.primary_video = stage.primary_media
        project.merge_sources = list(stage.added_media)
        project.merge = stage.merge
        project.overlay = stage.overlay
        project.export = stage.export
        project.analysis = stage.analysis
        project.scoring = stage.scoring

        slug = stage.label.lower().replace(" ", "-")
        output_path = OUTPUT_DIR / f"{stage.order_index}-{slug}.mp4"

        pname = Path(stage.primary_media.path).name
        mname = Path(stage.added_media[0].asset.path).name
        trimmed = "yes" if stage.added_media[0].trim_derivative.derivative_path else "no"
        dur = stage.primary_media.duration_ms / 1000
        print(
            f"\nExporting {stage.label}: primary={pname} ({dur:.0f}s trimmed) + merge={mname} ({trimmed} trimmed) | {stage.merge.layout.value}"
        )
        print(f"  → {output_path}")

        try:
            result = export_project(project, str(output_path))
            size_mb = result.stat().st_size / (1024 * 1024)
            print(f"  DONE: {size_mb:.1f} MB")
            results.append(output_path)
        except Exception as e:
            print(f"  FAILED: {e}")

    if len(results) >= 1:
        print(f"\n=== Stitching {len(results)} stages → 1 combined ===")
        combined = OUTPUT_DIR / "IDPA-Match-combined.mp4"
        list_path = OUTPUT_DIR / "concat-list.txt"
        with open(list_path, "w") as f:
            for r in results:
                f.write(f"file '{r.resolve()}'\n")
        import subprocess

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-c",
                "copy",
                str(combined),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        list_path.unlink()
        print(f"  Combined: {combined.name} ({combined.stat().st_size / (1024 * 1024):.0f} MB)")

    print(f"\n  Files in {OUTPUT_DIR}:")
    for f in sorted(OUTPUT_DIR.glob("*.mp4")):
        d = probe(f).duration_ms / 1000
        print(f"    {f.name}: {f.stat().st_size / (1024 * 1024):.0f} MB, {d:.1f}s")


if __name__ == "__main__":
    main()
