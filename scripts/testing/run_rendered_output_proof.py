#!/usr/bin/env python3
"""Generate local rendered-output proof artifacts for v1.0.7."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from splitshot.analysis.detection import analyze_video_audio
from splitshot.domain.models import (
    ImportedStageScore,
    MergeLayout,
    MergeSource,
    OverlayTextBox,
)
from splitshot.export.pipeline import export_project
from splitshot.media.ffmpeg import resolve_media_binary, run_ffprobe_json
from splitshot.media.probe import probe_video
from splitshot.scoring.logic import apply_scoring_preset, ensure_default_shot_scores
from splitshot.ui.controller import ProjectController

REPO = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT_ROOT = REPO / "artifacts" / "v107-release-proof" / "source-rendered-output"
PRIMARY_CLIP = REPO / "tests" / "fixtures" / "media" / "e2e-stage.mp4"
PRACTISCORE_CSV = REPO / "05072026" / "CSV" / "IDPA.csv"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _seconds(value: float | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _extract_frames(video_path: Path, frame_dir: Path, stem: str) -> list[str]:
    metadata = run_ffprobe_json(video_path)
    duration = float((metadata.get("format") or {}).get("duration") or 0.0)
    duration = max(duration, 6.0)
    sample_points = [
        max(0.5, round(duration * fraction, 2)) for fraction in (0.15, 0.35, 0.55, 0.75)
    ]
    ffmpeg = resolve_media_binary("ffmpeg")
    frame_paths: list[str] = []
    for index, timestamp in enumerate(sample_points, start=1):
        frame_path = frame_dir / f"{stem}-frame-{index}.png"
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-ss",
                str(timestamp),
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                str(frame_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        frame_paths.append(str(frame_path))
    return frame_paths


def _write_contact_sheet_html(contact_sheet: Path, entries: list[dict[str, object]]) -> None:
    lines = [
        "<html><body>",
        "<h1>SplitShot Rendered Output Proof</h1>",
    ]
    for entry in entries:
        lines.append(f"<h2>{entry['layout']}</h2>")
        lines.append(f"<p>{entry['video']}</p>")
        for frame in entry["frames"]:
            rel = Path(frame).relative_to(contact_sheet.parent)
            lines.append(f'<img src="{rel.as_posix()}" style="width: 24%; margin: 0.5%;">')
    lines.append("</body></html>")
    contact_sheet.write_text("\n".join(lines), encoding="utf-8")


def _build_project(
    primary_path: Path, secondary_path: Path, layout: MergeLayout
) -> ProjectController:
    controller = ProjectController()
    controller.load_primary_video(str(primary_path))
    controller.project.name = f"Rendered Output Proof {layout.value}"
    controller.project.merge.enabled = True
    controller.project.merge.layout = layout
    source = MergeSource(asset=probe_video(str(secondary_path)))
    source.placement.mode = layout.value
    controller.project.merge_sources = [source]
    controller.project.secondary_video = source.asset

    if PRACTISCORE_CSV.is_file():
        controller.import_practiscore_file(str(PRACTISCORE_CSV), source_name=PRACTISCORE_CSV.name)
    else:
        apply_scoring_preset(controller.project, "idpa_time_plus")
        controller.project.scoring.imported_stage = ImportedStageScore(
            source_name="manual-proof",
            source_path="",
            match_type="idpa",
            competitor_name="Proof Shooter",
            competitor_place=4,
            stage_number=1,
            stage_name="Stage 1",
            division="CO",
            classification="MA",
            raw_seconds=19.71,
            aggregate_points=14,
            final_time=33.71,
            score_counts={"PD": 14},
        )

    analysis = analyze_video_audio(primary_path, threshold=0.35)
    controller.project.primary_video = probe_video(str(primary_path))
    controller.project.merge_sources = [source]
    controller.project.secondary_video = source.asset
    controller.project.analysis.beep_time_ms_primary = analysis.beep_time_ms
    controller.project.analysis.waveform_primary = analysis.waveform
    controller.project.analysis.shots = analysis.shots
    active_stage = controller.project.active_stage
    if active_stage is not None:
        active_stage.primary_media = controller.project.primary_video
        active_stage.added_media = list(controller.project.merge_sources)
    apply_scoring_preset(controller.project, "idpa_time_plus")
    ensure_default_shot_scores(controller.project)
    controller.project.overlay.show_timer = True
    controller.project.overlay.show_draw = True
    controller.project.overlay.show_shots = True
    controller.project.overlay.show_score = True
    controller.project.overlay.text_boxes = [
        OverlayTextBox(
            enabled=True,
            source="imported_summary",
            quadrant="above_final",
            summary_metric_ids=["score_time", "raw_time"],
            width=180,
            height=52,
        ),
        OverlayTextBox(
            enabled=True,
            source="manual",
            text="Rendered output proof",
            quadrant="top_left",
            width=180,
            height=42,
        ),
    ]
    return controller


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    args = parser.parse_args()

    artifact_root = args.artifact_root.expanduser().resolve()
    exports_dir = artifact_root / "exports"
    frames_dir = artifact_root / "decoded-frames"
    logs_dir = artifact_root / "logs"
    state_dir = artifact_root / "state"
    for path in (exports_dir, frames_dir, logs_dir, state_dir):
        path.mkdir(parents=True, exist_ok=True)

    secondary_path = exports_dir / "e2e-stage-secondary.mp4"
    if not secondary_path.exists():
        shutil.copy2(PRIMARY_CLIP, secondary_path)

    proof_entries: list[dict[str, object]] = []
    state_summary: list[dict[str, object]] = []
    for layout in (MergeLayout.SIDE_BY_SIDE, MergeLayout.ABOVE_BELOW, MergeLayout.PIP):
        controller = _build_project(PRIMARY_CLIP, secondary_path, layout)
        shot_count = len(controller.project.analysis.shots)
        if shot_count < 3:
            raise RuntimeError(
                f"{PRIMARY_CLIP} only produced {shot_count} detected shots; expected at least 3 for proof."
            )
        output_path = exports_dir / f"{layout.value}.mp4"
        export_project(controller.project, output_path)
        ffprobe_payload = run_ffprobe_json(output_path)
        frame_paths = _extract_frames(output_path, frames_dir, layout.value)
        proof_entries.append(
            {
                "layout": layout.value,
                "video": str(output_path),
                "frames": frame_paths,
            }
        )
        ffprobe_path = state_dir / f"{layout.value}-ffprobe.json"
        _write_json(ffprobe_path, ffprobe_payload)
        state_summary.append(
            {
                "layout": layout.value,
                "output_path": str(output_path),
                "ffprobe_path": str(ffprobe_path),
                "shot_count": shot_count,
                "merge_layout": layout.value,
                "overlay": {
                    "show_timer": controller.project.overlay.show_timer,
                    "show_draw": controller.project.overlay.show_draw,
                    "show_shots": controller.project.overlay.show_shots,
                    "show_score": controller.project.overlay.show_score,
                    "text_boxes": [
                        {
                            "source": box.source,
                            "text": box.text,
                            "summary_metric_ids": list(box.summary_metric_ids),
                        }
                        for box in controller.project.overlay.text_boxes
                    ],
                },
                "imported_stage": (
                    None
                    if controller.project.scoring.imported_stage is None
                    else {
                        "match_type": controller.project.scoring.imported_stage.match_type,
                        "stage_number": controller.project.scoring.imported_stage.stage_number,
                        "stage_name": controller.project.scoring.imported_stage.stage_name,
                        "competitor_name": controller.project.scoring.imported_stage.competitor_name,
                    }
                ),
            }
        )

    _write_json(state_dir / "state-summary.json", state_summary)
    _write_contact_sheet_html(artifact_root / "contact-sheet.html", proof_entries)
    (logs_dir / "proof.log").write_text(
        "Generated side_by_side, above_below, and pip exports from final rendered mp4 files.\nDecoded frames were extracted from the rendered outputs themselves.\nEach export used tests/fixtures/media/e2e-stage.mp4 as primary input with a copied secondary clip.",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
