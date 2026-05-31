"""Merge, workspace export, and recap helpers extracted from the UI controller."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from splitshot.domain.models import ExportSettings, MergeSource, OutputProfile, Project
    from splitshot.ui.controller import ProjectController


def _controller_module():
    import splitshot.ui.controller as controller_module

    return controller_module


def workspace_export_recipe(value: str | None) -> tuple[str, bool]:
    raw_value = "" if value is None else str(value).strip().lower()
    if not raw_value:
        return "stage_output", True
    if raw_value in {"stage_output", "stage_composite"}:
        return raw_value, False
    raise ValueError(f"Unsupported workspace export recipe: {value}")


def workspace_export_output_path(
    workspace_path: Path,
    stage_id: str,
    recipe: str,
    *,
    legacy_default: bool = False,
) -> Path:
    if legacy_default and recipe == "stage_output":
        return workspace_path / f"{stage_id}.mp4"
    exports_dir = workspace_path / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    return exports_dir / f"{stage_id}-{recipe}.mp4"


def target_even_dimensions(width: int, height: int) -> tuple[int, int]:
    safe_width = max(2, int(width) - (int(width) % 2))
    safe_height = max(2, int(height) - (int(height) % 2))
    return safe_width, safe_height


def workspace_export_dimensions(
    controller: ProjectController,
    project: Project | None,
    frame_profile: str,
    base_width: int,
    base_height: int,
) -> tuple[int, int]:
    if (
        project is not None
        and project.export.target_width
        and project.export.target_height
        and int(project.export.target_width) > 0
        and int(project.export.target_height) > 0
    ):
        return controller._target_even_dimensions(
            int(project.export.target_width),
            int(project.export.target_height),
        )
    profile_dimensions = {
        "16:9": (640, 360),
        "9:16": (360, 640),
        "1:1": (360, 360),
        "4:5": (360, 450),
    }
    if frame_profile in profile_dimensions:
        return profile_dimensions[frame_profile]
    return controller._target_even_dimensions(base_width, base_height)


def run_media_command(
    command: list[str],
    *,
    timeout: int = 600,
    error_message: str,
) -> None:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or error_message)


def stage_profile_for_kind(
    controller: ProjectController,
    stage_id: str,
    profile_kind: str,
) -> OutputProfile | None:
    for candidate in controller._output_profiles.values():
        if (
            candidate.scope_type == "stage"
            and candidate.scope_id == stage_id
            and candidate.profile_kind == profile_kind
        ):
            return candidate
    return None


def output_profile_render_plan_for_project(
    controller: ProjectController,
    project: Project,
    profile: OutputProfile,
) -> dict[str, object]:
    return {
        "success": True,
        "output_id": profile.output_id,
        "profile_name": profile.profile_name,
        "profile_kind": profile.profile_kind,
        "scope_type": profile.scope_type,
        "scope_id": profile.scope_id,
        "frame_profile": profile.frame_profile,
        "metric_caption_preset": dict(profile.metric_caption_preset),
        "lead_in_card": dict(profile.lead_in_card),
        "brand_mark": dict(profile.brand_mark),
        "subject_track_crop": dict(profile.subject_track_crop),
        "visibility_recipe": dict(profile.visibility_recipe),
        "trim_settings": controller._resolve_trim_settings(profile, project=project),
        "source": "output_profile",
    }


def workspace_export_stage_output_item(
    controller: ProjectController,
    stage_id: str,
    workspace_path: Path,
    *,
    legacy_default: bool = False,
) -> dict[str, object]:
    controller_module = _controller_module()
    entry = controller.workspace.stage_entries.get(stage_id) if controller.workspace is not None else None
    if entry is None:
        raise ValueError("Stage entry not found")

    project = controller._load_stage_project(stage_id)
    if not project:
        raise ValueError("Cannot load stage project")
    if not project.primary_video or not project.primary_video.path:
        raise ValueError("No video imported for this stage")

    output_path = controller._workspace_export_output_path(
        workspace_path,
        stage_id,
        "stage_output",
        legacy_default=legacy_default,
    )
    display_name = entry.display_name or f"Stage {entry.stage_number}"
    profile = controller._stage_profile_for_kind(stage_id, "stage_output")

    controller._set_status(f"Exporting {display_name}...")
    if profile is None:
        exported_path = controller_module.export_project(
            project,
            str(output_path),
            progress_callback=lambda _value: None,
            log_callback=lambda _line: None,
        )
    else:
        render_plan = controller._output_profile_render_plan_for_project(project, profile)
        exported_path = controller_module.export_output_profile(
            project,
            output_path,
            render_plan,
            progress_callback=lambda _value: None,
            log_callback=lambda _line: None,
        )
        profile.last_rendered_at = controller_module._utc_now()

    size_bytes = exported_path.stat().st_size if exported_path.exists() else 0
    return {
        "stage_id": stage_id,
        "display_name": display_name,
        "output_path": str(exported_path),
        "size_bytes": size_bytes,
        "status": "completed",
        "recipe": "stage_output",
    }


def workspace_stage_composite_segments(
    controller: ProjectController,
    stage_id: str,
    output_id: str | None = None,
) -> tuple[OutputProfile, list[dict[str, object]]]:
    controller_module = _controller_module()
    entry = controller._workspace_stage_entry(stage_id)
    if entry is None:
        raise ValueError("Stage not found in workspace")

    profile = controller._stage_composite_profile(stage_id, output_id)
    if profile is None:
        raise ValueError("Stage composite output profile not found")

    clips = [
        clip
        for clip in controller._workspace_stage_clip_models(stage_id)
        if clip.source_path and Path(clip.source_path).exists()
    ]
    if not clips:
        raise ValueError("No clip sources available for Stage Composite export")

    clip_by_id = {clip.clip_id: clip for clip in clips}
    segments: list[dict[str, object]] = []
    persisted_plan = [
        controller._angle_director_cut_to_dict(cut)
        for cut in profile.angle_director_plan
        if int(cut.duration_ms) > 0
    ]

    if persisted_plan:
        for plan_item in sorted(
            persisted_plan,
            key=lambda item: (int(item.get("position") or 0), int(item.get("start_ms") or 0)),
        ):
            clip = clip_by_id.get(str(plan_item.get("clip_id") or ""))
            if clip is None:
                continue
            asset = controller_module.probe_video(Path(clip.source_path))
            asset_duration_ms = max(1, int(asset.duration_ms or 0))
            start_ms = max(0, int(plan_item.get("start_ms") or 0))
            if start_ms >= asset_duration_ms:
                continue
            duration_ms = max(0, int(plan_item.get("duration_ms") or 0))
            if duration_ms <= 0:
                continue
            duration_ms = min(duration_ms, asset_duration_ms - start_ms)
            if duration_ms <= 0:
                continue
            segments.append(
                {
                    "clip": clip,
                    "asset": asset,
                    "start_ms": start_ms,
                    "duration_ms": duration_ms,
                    "position": int(plan_item.get("position") or 0),
                }
            )

    if not segments:
        for index, clip in enumerate(clips):
            asset = controller_module.probe_video(Path(clip.source_path))
            asset_duration_ms = max(1, int(asset.duration_ms or 0))
            start_ms = max(0, int(clip.sync_offset_ms) if int(clip.sync_offset_ms) > 0 else 0)
            if start_ms >= asset_duration_ms:
                continue
            duration_ms = min(asset_duration_ms - start_ms, 1500)
            if duration_ms <= 0:
                continue
            segments.append(
                {
                    "clip": clip,
                    "asset": asset,
                    "start_ms": start_ms,
                    "duration_ms": duration_ms,
                    "position": index,
                }
            )

    if not segments:
        raise ValueError("Stage composite export has no renderable clip segments")

    return profile, segments


def workspace_export_stage_composite_item(
    controller: ProjectController,
    stage_id: str,
    workspace_path: Path,
) -> dict[str, object]:
    entry = controller.workspace.stage_entries.get(stage_id) if controller.workspace is not None else None
    if entry is None:
        raise ValueError("Stage entry not found")

    stage_project = controller._load_stage_project(stage_id)
    profile, segments = controller._workspace_stage_composite_segments(stage_id)
    display_name = entry.display_name or f"Stage {entry.stage_number}"
    first_asset = segments[0]["asset"]
    target_width, target_height = controller._workspace_export_dimensions(
        stage_project,
        profile.frame_profile,
        int(first_asset.width or 640),
        int(first_asset.height or 360),
    )
    output_path = controller._workspace_export_output_path(
        workspace_path,
        stage_id,
        "stage_composite",
    )

    controller._set_status(f"Exporting {display_name} composite...")
    with TemporaryDirectory(prefix="splitshot-stage-composite-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        rendered_segments: list[Path] = []
        for index, segment in enumerate(segments):
            clip = segment["clip"]
            source_path = Path(clip.source_path)
            segment_path = temp_dir / f"segment-{index:02d}.mp4"
            segment_seconds = max(0.05, float(segment["duration_ms"]) / 1000.0)
            command = [
                "ffmpeg",
                "-y",
                "-ss",
                f"{float(segment['start_ms']) / 1000.0:.3f}",
                "-i",
                str(source_path),
                "-t",
                f"{segment_seconds:.3f}",
                "-vf",
                (
                    f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                    f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color=black,"
                    "setsar=1"
                ),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
            ]
            if clip.audio_muted:
                command.extend(["-af", "volume=0.000"])
            elif abs(float(clip.audio_gain) - 1.0) > 0.001:
                command.extend(
                    [
                        "-af",
                        f"volume={max(0.0, min(2.0, float(clip.audio_gain))):.3f}",
                    ]
                )
            command.extend(
                [
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "18",
                    "-c:a",
                    "aac",
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    "-b:a",
                    "192k",
                    str(segment_path),
                ]
            )
            controller._run_media_command(
                command,
                error_message=f"Stage composite segment export failed for {source_path.name}",
            )
            rendered_segments.append(segment_path)

        concat_path = temp_dir / "segments.txt"
        concat_path.write_text(
            "\n".join(
                f"file '{str(path).replace("'", "'\\''")}'" for path in rendered_segments
            )
            + "\n",
            encoding="utf-8",
        )
        controller._run_media_command(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_path),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(output_path),
            ],
            error_message="Stage composite export failed",
        )

    profile.last_rendered_at = _controller_module()._utc_now()
    size_bytes = output_path.stat().st_size if output_path.exists() else 0
    return {
        "stage_id": stage_id,
        "display_name": display_name,
        "output_path": str(output_path),
        "size_bytes": size_bytes,
        "status": "completed",
        "recipe": "stage_composite",
        "segment_count": len(segments),
    }


def workspace_export(
    controller: ProjectController,
    stage_id: str | None = None,
    recipe: str | None = None,
) -> dict:
    if not controller.workspace:
        return {"success": False, "error": "No workspace open", "outputs": [], "errors": []}

    if not controller.workspace_path:
        return {
            "success": False,
            "error": "Workspace has not been saved",
            "outputs": [],
            "errors": [],
        }

    if stage_id and stage_id not in controller.workspace.stage_entries:
        return {
            "success": False,
            "error": f"Stage {stage_id} not in workspace",
            "outputs": [],
            "errors": [{"stage_id": stage_id, "error": "Not found in workspace"}],
        }

    try:
        resolved_recipe, legacy_default = controller._workspace_export_recipe(recipe)
    except ValueError as exc:
        return {
            "success": False,
            "error": str(exc),
            "outputs": [],
            "errors": [{"stage_id": stage_id or "", "error": str(exc)}],
        }

    stages_to_export = [stage_id] if stage_id else list(controller.workspace.stage_entries.keys())
    outputs = []
    errors = []
    ws_path = Path(controller.workspace_path)

    for sid in stages_to_export:
        entry = controller.workspace.stage_entries.get(sid)
        if not entry:
            errors.append({"stage_id": sid, "error": "Stage entry not found"})
            continue

        try:
            if resolved_recipe == "stage_composite":
                outputs.append(controller._workspace_export_stage_composite_item(sid, ws_path))
            else:
                outputs.append(
                    controller._workspace_export_stage_output_item(
                        sid,
                        ws_path,
                        legacy_default=legacy_default,
                    )
                )
        except Exception as exc:
            errors.append({"stage_id": sid, "error": str(exc)})

    if errors:
        controller._set_status(f"Export completed with {len(errors)} error(s).")
    else:
        controller._set_status(f"Exported {len(outputs)} stage(s).")

    return {
        "success": len(errors) == 0,
        "outputs": outputs,
        "errors": errors,
        "total": len(stages_to_export),
        "completed": len(outputs),
        "failed": len(errors),
    }


def recap_transition(value: str | None) -> str:
    transition = str(value or "cut").strip().lower()
    return transition if transition in {"cut", "fade", "dissolve"} else "cut"


def recap_result_card_mode(value: str | None) -> str:
    mode = str(value or "none").strip().lower()
    return mode if mode in {"none", "end", "each"} else "none"


def recap_status_label(value: str | None) -> str:
    return str(value or "incomplete").replace("_", " ").strip().title() or "Incomplete"


def recap_stage_options(value: object) -> dict[str, dict[str, object]]:
    raw_items: list[object] = []
    if isinstance(value, dict):
        raw_items = [
            {"stage_id": stage_id, **(raw if isinstance(raw, dict) else {})}
            for stage_id, raw in value.items()
        ]
    elif isinstance(value, list):
        raw_items = value

    options_by_stage: dict[str, dict[str, object]] = {}
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        stage_id = str(raw_item.get("stage_id") or "").strip()
        if not stage_id:
            continue
        subtitle = " ".join(str(raw_item.get("subtitle") or "").split()).strip()[:120]
        try:
            audio_gain = float(raw_item.get("audio_gain", 1.0))
        except (TypeError, ValueError):
            audio_gain = 1.0
        options_by_stage[stage_id] = {
            "subtitle": subtitle,
            "audio_gain": max(0.0, min(2.0, audio_gain)),
            "audio_muted": bool(raw_item.get("audio_muted", False)),
        }
    return options_by_stage


def recap_stage_option_requested(stage_option: dict[str, object] | None) -> bool:
    if not isinstance(stage_option, dict):
        return False
    subtitle = str(stage_option.get("subtitle") or "").strip()
    try:
        audio_gain = float(stage_option.get("audio_gain", 1.0))
    except (TypeError, ValueError):
        audio_gain = 1.0
    return (
        bool(subtitle)
        or bool(stage_option.get("audio_muted", False))
        or abs(audio_gain - 1.0) > 0.001
    )


def render_recap_card_image(
    controller: ProjectController,
    title: str,
    detail_lines: list[str],
    output_path: Path,
    *,
    width: int,
    height: int,
) -> Path:
    controller_module = _controller_module()
    image = controller_module.QImage(
        width,
        height,
        controller_module.QImage.Format.Format_ARGB32,
    )
    image.fill(controller_module.QColor("#0b0f14"))

    painter = controller_module.QPainter(image)
    painter.setRenderHint(controller_module.QPainter.Antialiasing, True)
    painter.setRenderHint(controller_module.QPainter.TextAntialiasing, True)
    painter.fillRect(0, 0, width, height, controller_module.QColor("#0b0f14"))
    painter.fillRect(0, 0, width, max(8, height // 48), controller_module.QColor("#ff7b22"))
    painter.fillRect(
        width // 12,
        height // 6,
        width // 18,
        (height * 2) // 3,
        controller_module.QColor("#141c27"),
    )

    title_font = controller_module.QFont("Helvetica Neue")
    title_font.setBold(True)
    title_font.setPixelSize(max(32, min(68, height // 11)))
    painter.setFont(title_font)
    painter.setPen(controller_module.QColor("#ffffff"))
    title_rect = controller_module.QRectF(
        width * 0.14,
        height * 0.18,
        width * 0.72,
        height * 0.24,
    )
    painter.drawText(
        title_rect,
        controller_module.Qt.AlignCenter | controller_module.Qt.TextWordWrap,
        title,
    )

    detail_font = controller_module.QFont("Helvetica Neue")
    detail_font.setPixelSize(max(18, min(34, height // 26)))
    painter.setFont(detail_font)
    painter.setPen(controller_module.QColor("#d7dee8"))
    detail_rect = controller_module.QRectF(
        width * 0.18,
        height * 0.46,
        width * 0.64,
        height * 0.28,
    )
    painter.drawText(
        detail_rect,
        controller_module.Qt.AlignHCenter
        | controller_module.Qt.AlignTop
        | controller_module.Qt.TextWordWrap,
        "\n".join(detail_lines),
    )

    footer_font = controller_module.QFont("Helvetica Neue")
    footer_font.setPixelSize(max(14, min(22, height // 36)))
    painter.setFont(footer_font)
    painter.setPen(controller_module.QColor("#8ca0b7"))
    painter.drawText(
        controller_module.QRectF(width * 0.12, height * 0.82, width * 0.76, height * 0.08),
        controller_module.Qt.AlignCenter | controller_module.Qt.AlignVCenter,
        "Rendered by SplitShot Match Recap",
    )
    painter.end()

    image.save(str(output_path))
    return output_path


def render_recap_card_video(
    controller: ProjectController,
    title: str,
    detail_lines: list[str],
    output_path: Path,
    *,
    width: int,
    height: int,
    fps: float,
    duration_ms: int,
) -> Path:
    image_path = output_path.with_suffix(".png")
    controller._render_recap_card_image(
        title,
        detail_lines,
        image_path,
        width=width,
        height=height,
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(image_path),
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-t",
        f"{max(0.5, duration_ms / 1000):.3f}",
        "-vf",
        (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"fps={fps:.3f}"
        ),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Result card render failed")
    return output_path


def render_recap_subtitle_overlay_image(
    controller: ProjectController,
    subtitle: str,
    output_path: Path,
    *,
    width: int,
    height: int,
) -> Path:
    controller_module = _controller_module()
    image = controller_module.QImage(
        width,
        height,
        controller_module.QImage.Format.Format_ARGB32,
    )
    image.fill(controller_module.QColor(0, 0, 0, 0))

    painter = controller_module.QPainter(image)
    painter.setRenderHint(controller_module.QPainter.Antialiasing, True)
    painter.setRenderHint(controller_module.QPainter.TextAntialiasing, True)

    band_height = max(72, min(132, height // 6 if height else 96))
    top_accent_height = max(4, band_height // 18)
    band_y = max(0, height - band_height)
    painter.fillRect(
        controller_module.QRectF(0, band_y, width, band_height),
        controller_module.QColor(0, 0, 0, 176),
    )
    painter.fillRect(
        controller_module.QRectF(0, band_y, width, top_accent_height),
        controller_module.QColor("#ff7b22"),
    )

    text_font = controller_module.QFont("Helvetica Neue")
    text_font.setBold(True)
    text_font.setPixelSize(max(22, min(38, band_height // 2)))
    painter.setFont(text_font)
    painter.setPen(controller_module.QColor("#ffffff"))
    painter.drawText(
        controller_module.QRectF(
            width * 0.08,
            band_y + max(8, band_height * 0.18),
            width * 0.84,
            band_height * 0.62,
        ),
        controller_module.Qt.AlignCenter
        | controller_module.Qt.AlignVCenter
        | controller_module.Qt.TextWordWrap,
        subtitle,
    )
    painter.end()

    image.save(str(output_path))
    return output_path


def render_recap_stage_variant(
    controller: ProjectController,
    source_path: Path,
    output_path: Path,
    *,
    subtitle: str = "",
    audio_gain: float = 1.0,
    audio_muted: bool = False,
    width: int,
    height: int,
) -> Path:
    normalized_subtitle = " ".join(str(subtitle or "").split()).strip()
    normalized_audio_gain = max(0.0, min(2.0, float(audio_gain)))
    apply_subtitle = bool(normalized_subtitle)
    apply_audio_filter = audio_muted or abs(normalized_audio_gain - 1.0) > 0.001

    if not apply_subtitle and not apply_audio_filter:
        shutil.copy2(str(source_path), str(output_path))
        return output_path

    input_args = ["-i", str(source_path)]
    filter_parts: list[str] = []
    video_label = "0:v:0"
    audio_label = "0:a:0?"

    if apply_subtitle:
        overlay_path = output_path.with_suffix(".subtitle.png")
        controller._render_recap_subtitle_overlay_image(
            normalized_subtitle,
            overlay_path,
            width=width,
            height=height,
        )
        input_args.extend(["-i", str(overlay_path)])
        filter_parts.append("[1:v]format=rgba[subtitle_overlay]")
        filter_parts.append("[0:v][subtitle_overlay]overlay=0:0[vout]")
        video_label = "[vout]"

    if apply_audio_filter:
        volume_level = 0.0 if audio_muted else normalized_audio_gain
        filter_parts.append(f"[0:a]volume={volume_level:.3f}[aout]")
        audio_label = "[aout]"

    cmd = ["ffmpeg", "-y", *input_args]
    if filter_parts:
        cmd.extend(
            [
                "-filter_complex",
                ";".join(filter_parts),
                "-map",
                video_label,
                "-map",
                audio_label,
            ]
        )
    else:
        cmd.extend(["-map", "0:v:0", "-map", "0:a:0?"])
    cmd.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output_path),
        ]
    )
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Recap stage render failed")
    return output_path


def render_recap_sequence(
    controller: ProjectController,
    sequence_paths: list[Path],
    recap_path: Path,
    *,
    transition: str,
    target_width: int,
    target_height: int,
    target_fps: float,
) -> dict:
    controller_module = _controller_module()
    if not sequence_paths:
        return {"success": False, "error": "No recap media to render"}

    if len(sequence_paths) == 1 and transition == "cut":
        shutil.copy2(str(sequence_paths[0]), str(recap_path))
        return {"success": True, "sequence_count": 1, "transition": transition}

    sequence_assets = [controller_module.probe_video(path) for path in sequence_paths]
    filter_parts: list[str] = []
    input_args: list[str] = []
    for index, path in enumerate(sequence_paths):
        input_args.extend(["-i", str(path)])
        filter_parts.append(
            (
                f"[{index}:v]scale={target_width}:{target_height}:"
                "force_original_aspect_ratio=decrease,"
                f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color=black,"
                f"setsar=1,fps={target_fps:.3f},format=yuv420p[v{index}]"
            )
        )
        filter_parts.append(
            f"[{index}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a{index}]"
        )

    if transition == "cut" or len(sequence_paths) == 1:
        concat_inputs = "".join(
            f"[v{index}][a{index}]" for index in range(len(sequence_paths))
        )
        filter_parts.append(
            f"{concat_inputs}concat=n={len(sequence_paths)}:v=1:a=1[vout][aout]"
        )
        video_label = "[vout]"
        audio_label = "[aout]"
    else:
        fade_duration_s = 0.35
        xfade_transition = "dissolve" if transition == "dissolve" else "fade"
        video_label = "[v0]"
        audio_label = "[a0]"
        elapsed_s = max(0.0, sequence_assets[0].duration_ms / 1000)
        for index in range(1, len(sequence_paths)):
            next_video = f"[v{index}]"
            next_audio = f"[a{index}]"
            out_video = f"[vx{index}]"
            out_audio = f"[ax{index}]"
            offset_s = max(0.0, elapsed_s - fade_duration_s)
            filter_parts.append(
                (
                    f"{video_label}{next_video}xfade=transition={xfade_transition}:"
                    f"duration={fade_duration_s:.3f}:offset={offset_s:.3f}{out_video}"
                )
            )
            filter_parts.append(
                f"{audio_label}{next_audio}acrossfade=d={fade_duration_s:.3f}{out_audio}"
            )
            video_label = out_video
            audio_label = out_audio
            elapsed_s = max(
                fade_duration_s,
                elapsed_s + (sequence_assets[index].duration_ms / 1000) - fade_duration_s,
            )

    cmd = [
        "ffmpeg",
        "-y",
        *input_args,
        "-filter_complex",
        ";".join(filter_parts),
        "-map",
        video_label,
        "-map",
        audio_label,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(recap_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        return {
            "success": False,
            "error": f"Recap render failed: {result.stderr[:500]}",
        }
    return {
        "success": True,
        "sequence_count": len(sequence_paths),
        "transition": transition,
    }


def workspace_recap_render(controller: ProjectController, **kwargs) -> dict:
    controller_module = _controller_module()
    if not controller.workspace:
        return {"success": False, "error": "No workspace open"}

    if not controller.workspace_path:
        return {"success": False, "error": "Workspace has not been saved"}

    raw_stage_ids = kwargs.get("stage_ids") or list(
        controller.workspace.stage_order or controller.workspace.stage_entries.keys()
    )
    if isinstance(raw_stage_ids, (str, bytes)):
        stage_ids = [str(raw_stage_ids).strip()] if str(raw_stage_ids).strip() else []
    else:
        stage_ids = [
            str(stage_id).strip() for stage_id in raw_stage_ids if str(stage_id).strip()
        ]
    transition = controller._recap_transition(kwargs.get("transition"))
    result_card_mode = controller._recap_result_card_mode(kwargs.get("result_card"))
    stage_options = controller._recap_stage_options(kwargs.get("stage_options"))

    ws_path = Path(controller.workspace_path)
    recap_path = ws_path / "recap.mp4"
    temp_dir = ws_path / ".recap-tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    exported_segments: list[dict] = []
    errors: list[dict] = []

    try:
        for sid in stage_ids:
            entry = controller.workspace.stage_entries.get(sid)
            if not entry:
                errors.append({"stage_id": sid, "error": "Stage entry not found"})
                continue

            project = controller._load_stage_project(sid)
            if not project:
                errors.append({"stage_id": sid, "error": "Cannot load stage project"})
                continue
            if not project.primary_video or not project.primary_video.path:
                errors.append({"stage_id": sid, "error": "No video imported for this stage"})
                continue

            seg_path = temp_dir / f"{sid}.mp4"
            controller._set_status(f"Exporting {sid} for recap...")
            controller_module.export_project(
                project,
                str(seg_path),
                progress_callback=lambda v: None,
                log_callback=lambda line: None,
            )
            if seg_path.exists() and seg_path.stat().st_size > 0:
                segment_path = seg_path
                segment_asset = controller_module.probe_video(seg_path)
                stage_option = stage_options.get(str(sid), {})
                if controller._recap_stage_option_requested(stage_option):
                    processed_path = temp_dir / f"{sid}-recap-variant.mp4"
                    try:
                        controller._set_status(f"Applying recap options to {sid}...")
                        controller._render_recap_stage_variant(
                            seg_path,
                            processed_path,
                            subtitle=str(stage_option.get("subtitle") or ""),
                            audio_gain=float(stage_option.get("audio_gain", 1.0)),
                            audio_muted=bool(stage_option.get("audio_muted", False)),
                            width=max(2, int(segment_asset.width or 0)),
                            height=max(2, int(segment_asset.height or 0)),
                        )
                        if processed_path.exists() and processed_path.stat().st_size > 0:
                            segment_path = processed_path
                            segment_asset = controller_module.probe_video(segment_path)
                        else:
                            errors.append(
                                {
                                    "stage_id": sid,
                                    "error": "Recap stage overrides produced an empty file",
                                }
                            )
                    except Exception as exc:
                        errors.append(
                            {
                                "stage_id": sid,
                                "error": f"Recap stage overrides failed: {exc}",
                            }
                        )
                exported_segments.append(
                    {
                        "stage_id": sid,
                        "entry": entry,
                        "path": segment_path,
                        "asset": segment_asset,
                        "recap_options": stage_option,
                    }
                )
            else:
                errors.append({"stage_id": sid, "error": "Export produced empty file"})

        if not exported_segments:
            return {
                "success": False,
                "error": "No stages could be exported for recap",
                "errors": errors,
            }

        reference_asset = exported_segments[0]["asset"]
        target_width = max(2, int(reference_asset.width) - (int(reference_asset.width) % 2))
        target_height = max(2, int(reference_asset.height) - (int(reference_asset.height) % 2))
        target_fps = max(1.0, float(reference_asset.fps or 30.0))

        sequence_paths = [segment["path"] for segment in exported_segments]
        if result_card_mode != "none":
            cards_result = controller.resolve_result_cards("recap")
            if not cards_result.get("success"):
                errors.append(
                    {"error": cards_result.get("error", "Result cards unavailable")}
                )
            else:
                cards_by_stage = {
                    str(card.get("stage_id") or ""): card
                    for card in cards_result.get("cards", [])
                }
                if result_card_mode == "each":
                    sequence_paths = []
                    for segment in exported_segments:
                        sequence_paths.append(segment["path"])
                        card = cards_by_stage.get(segment["stage_id"])
                        if not card or not card.get("enabled", True):
                            continue
                        card_path = temp_dir / f"{segment['stage_id']}-result-card.mp4"
                        try:
                            controller._render_recap_card_video(
                                card.get("stage_name")
                                or f"Stage {card.get('stage_number') or ''}".strip(),
                                [
                                    f"Stage {card.get('stage_number') or '--'}",
                                    f"Status: {controller._recap_status_label(card.get('status'))}",
                                ],
                                card_path,
                                width=target_width,
                                height=target_height,
                                fps=target_fps,
                                duration_ms=int(card.get("duration_ms", 3000)),
                            )
                            sequence_paths.append(card_path)
                        except Exception as exc:
                            errors.append(
                                {
                                    "stage_id": segment["stage_id"],
                                    "error": f"Result card render failed: {exc}",
                                }
                            )
                elif result_card_mode == "end":
                    summary_lines = []
                    for segment in exported_segments:
                        card = cards_by_stage.get(segment["stage_id"])
                        if not card or not card.get("enabled", True):
                            continue
                        summary_lines.append(
                            f"Stage {card.get('stage_number') or '--'} • {card.get('stage_name') or segment['stage_id']} • {controller._recap_status_label(card.get('status'))}"
                        )
                    if summary_lines:
                        summary_path = temp_dir / "recap-summary-card.mp4"
                        try:
                            controller._render_recap_card_video(
                                controller.workspace.name or "Match Recap",
                                summary_lines[:8],
                                summary_path,
                                width=target_width,
                                height=target_height,
                                fps=target_fps,
                                duration_ms=3500,
                            )
                            sequence_paths.append(summary_path)
                        except Exception as exc:
                            errors.append({"error": f"Result card render failed: {exc}"})

        render_result = controller._render_recap_sequence(
            sequence_paths,
            recap_path,
            transition=transition,
            target_width=target_width,
            target_height=target_height,
            target_fps=target_fps,
        )
        if not render_result.get("success"):
            return {
                "success": False,
                "error": render_result.get("error", "Recap render failed"),
                "errors": errors,
            }

        if not recap_path.exists() or recap_path.stat().st_size <= 0:
            return {
                "success": False,
                "error": "Recap file was not produced",
                "errors": errors,
            }

        controller._set_status(f"Recap rendered to {recap_path}")
        return {
            "success": True,
            "output_path": str(recap_path),
            "size_bytes": recap_path.stat().st_size,
            "stage_count": len(exported_segments),
            "transition": transition,
            "result_card": result_card_mode,
            "sequence_count": len(sequence_paths),
            "stage_options_applied": [
                segment["stage_id"]
                for segment in exported_segments
                if controller._recap_stage_option_requested(segment.get("recap_options"))
            ],
            "errors": errors,
        }

    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def add_merge_source(
    controller: ProjectController,
    path: str,
    source_name: str | None = None,
) -> None:
    controller_module = _controller_module()
    del source_name
    asset = controller_module.probe_video(path)
    merge_source = controller_module.MergeSource(
        asset=asset,
        angle_role=controller_module.default_merge_source_angle_role(asset),
        pip_size_percent=controller.project.merge.pip_size_percent,
        pip_x=controller.project.merge.pip_x,
        pip_y=controller.project.merge.pip_y,
        sync_offset_ms=0,
    )
    next_order_index = controller_module._next_merge_source_order_index(controller.project)
    merge_source.placement.order_index = next_order_index
    merge_source.placement.layer_index = next_order_index
    merge_source.trim_derivative.original_path = asset.path
    merge_source.trim_derivative.derivative_path = None
    merge_source.trim_derivative.active_path_kind = (
        controller_module.MergeSourceAssetPathKind.ORIGINAL
    )
    controller.project.merge_sources.append(merge_source)
    for existing_source in controller.project.merge_sources:
        controller_module._apply_merge_source_role_seed_defaults(
            controller.project,
            existing_source,
            force=existing_source.id == merge_source.id,
        )
    controller.project.merge.enabled = True
    controller_module._sync_secondary_video_from_merge_sources(controller.project)
    if controller_module._first_analyzable_merge_source(controller.project) is not None:
        controller._set_status("Imported merge media.")
        controller.analyze_secondary()
        return
    controller._set_status("Imported merge media.")
    controller.project.touch()
    controller.project_changed.emit()


def remove_merge_source(controller: ProjectController, source_id: str) -> None:
    controller_module = _controller_module()
    before_sources = list(controller.project.merge_sources)
    before_count = len(before_sources)
    controller.project.merge_sources = [
        source for source in controller.project.merge_sources if source.id != source_id
    ]
    if len(controller.project.merge_sources) == before_count:
        return
    if not controller.project.merge_sources:
        controller.project.merge.enabled = False
    removed_analyzed = controller.project.analysis.analyzed_secondary_source_id == source_id
    controller_module._sync_secondary_video_from_merge_sources(controller.project)
    if removed_analyzed:
        controller_module._clear_secondary_analysis_state(
            controller.project,
            preserve_sync_offset=bool(controller.project.merge_sources),
        )
        if controller_module._first_analyzable_merge_source(controller.project) is not None:
            controller.analyze_secondary()
            return
        controller.project.analysis.sync_offset_ms = 0
    controller._set_status("Removed merge media.")
    controller.project.touch()
    controller.project_changed.emit()


def rerun_merge_source_analysis(controller: ProjectController, source_id: str) -> None:
    controller_module = _controller_module()
    source = next(
        (item for item in controller.project.merge_sources if item.id == source_id),
        None,
    )
    if source is None:
        raise ValueError("Merge source not found")
    analyzed_source = controller_module._first_analyzable_merge_source(controller.project)
    if analyzed_source is None or analyzed_source.id != source_id:
        raise ValueError("Only the first analyzable PiP video can be reanalyzed")
    controller.analyze_secondary()


def merge_source_by_id(controller: ProjectController, source_id: str) -> MergeSource:
    source = next((item for item in controller.project.merge_sources if item.id == source_id), None)
    if source is None:
        raise ValueError("Merge source not found")
    return source


def require_saved_project_for_trim_derivative(controller: ProjectController) -> Path:
    if controller.project_path is None:
        raise ValueError(
            "Trim derivative generation requires a saved project folder because derivatives live under Input/."
        )
    return controller.project_path


def merge_source_trim_derivative_filename(
    controller: ProjectController,
    source: MergeSource,
) -> str:
    controller_module = _controller_module()
    source_path = (
        controller_module._merge_source_original_path(source)
        or str(source.asset.path or "")
        or source.id
    )
    base_name = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(source_path).stem).strip("-._")
    if not base_name:
        base_name = "merge-source"
    suffix = Path(source_path).suffix.lower()
    if suffix not in controller_module._TRIM_DERIVATIVE_CONTAINER_SUFFIXES:
        suffix = ".mp4"
    return f"{base_name}-{source.id[:8]}-trim{suffix}"


def merge_source_trim_derivative_path(
    controller: ProjectController,
    source: MergeSource,
) -> Path:
    controller_module = _controller_module()
    existing_path = str(source.trim_derivative.derivative_path or "").strip()
    if existing_path:
        return Path(existing_path).expanduser().resolve(strict=False)

    project_path = controller._require_saved_project_for_trim_derivative()
    derivative_path = (
        project_path
        / controller_module.INPUT_DIRNAME
        / controller._merge_source_trim_derivative_filename(source)
    ).resolve(strict=False)
    return derivative_path


def merge_source_available_original_path(
    controller: ProjectController,
    source: MergeSource,
) -> Path | None:
    original_path = str(source.trim_derivative.original_path or "").strip()
    if original_path:
        original_candidate = Path(original_path).expanduser().resolve(strict=False)
        if original_candidate.is_file():
            return original_candidate

    asset_path = str(source.asset.path or "").strip()
    if not asset_path:
        return None

    asset_candidate = Path(asset_path).expanduser().resolve(strict=False)
    if not asset_candidate.is_file():
        return None

    derivative_path = str(source.trim_derivative.derivative_path or "").strip()
    if derivative_path:
        derivative_candidate = Path(derivative_path).expanduser().resolve(strict=False)
        if asset_candidate == derivative_candidate:
            return None

    return asset_candidate


def refresh_merge_source_trim_derivative_from_original(
    controller: ProjectController,
    original_source_path: Path,
    derivative_path: Path,
) -> Path:
    del controller
    derivative_path.parent.mkdir(parents=True, exist_ok=True)
    if original_source_path != derivative_path:
        shutil.copy2(original_source_path, derivative_path)
    elif not derivative_path.is_file():
        raise FileNotFoundError(
            "Trim derivative source is unavailable. Restore the original media before trimming again."
        )
    return derivative_path


def merge_source_trim_source_path(
    controller: ProjectController,
    source: MergeSource,
) -> Path:
    controller_module = _controller_module()
    original_path = controller_module._merge_source_original_path(source)
    if original_path:
        original_candidate = Path(original_path).expanduser().resolve(strict=False)
        if original_candidate.is_file():
            return original_candidate

    derivative_path = str(source.trim_derivative.derivative_path or "").strip()
    if derivative_path:
        derivative_candidate = Path(derivative_path).expanduser().resolve(strict=False)
        if derivative_candidate.is_file():
            return derivative_candidate

    asset_path = str(source.asset.path or "").strip()
    if asset_path:
        asset_candidate = Path(asset_path).expanduser().resolve(strict=False)
        if asset_candidate.is_file():
            return asset_candidate

    raise FileNotFoundError(
        "Trim source is unavailable. Restore the original media or keep the local derivative available before trimming again."
    )


def trim_merge_source_to_derivative(
    controller: ProjectController,
    source_id: str,
    *,
    start_ms: int,
    end_ms: int | None = None,
    export_settings: ExportSettings | None = None,
) -> MergeSource:
    controller_module = _controller_module()
    project_path = controller._require_saved_project_for_trim_derivative()
    source = controller._merge_source_by_id(source_id)
    if source.asset.is_still_image:
        raise ValueError("Only video merge sources can generate trim derivatives.")

    derivative_path = controller._merge_source_trim_derivative_path(source)
    (project_path / controller_module.INPUT_DIRNAME).mkdir(parents=True, exist_ok=True)
    original_source_path = controller._merge_source_available_original_path(source)
    if original_source_path is not None:
        trim_source_path = controller._refresh_merge_source_trim_derivative_from_original(
            original_source_path,
            derivative_path,
        )
    else:
        trim_source_path = controller._merge_source_trim_source_path(source)

    trim_source_fps = controller_module.probe_video(trim_source_path).fps
    controller_module.generate_trimmed_derivative(
        trim_source_path,
        derivative_path,
        start_ms=start_ms,
        end_ms=end_ms,
        source_fps=trim_source_fps,
        export_settings=export_settings or controller.project.export,
    )

    if (
        not str(source.trim_derivative.original_path or "").strip()
        and original_source_path is not None
    ):
        source.trim_derivative.original_path = str(original_source_path)
    source.trim_derivative.derivative_path = str(derivative_path)
    source.asset = controller_module.probe_video(derivative_path)
    controller_module._sync_merge_source_trim_provenance(source)
    controller_module._sync_secondary_video_from_merge_sources(controller.project)
    controller.project.merge.enabled = bool(controller.project.merge_sources)
    controller._set_status("Updated merge trim derivative.")
    controller.project.touch()
    controller.project_changed.emit()
    return source


def trim_export_settings_from_payload(
    controller: ProjectController,
    payload: dict[str, object] | None = None,
):
    controller_module = _controller_module()
    export_payload = payload
    if isinstance(payload, dict) and isinstance(payload.get("export"), dict):
        export_payload = payload.get("export")
    return controller_module.resolved_export_settings(
        controller.project.export,
        export_payload if isinstance(export_payload, dict) else {},
        synchronize_preset=True,
    )


def trim_merge_source_from_payload(
    controller: ProjectController,
    payload: dict[str, object] | None = None,
) -> MergeSource:
    request_payload = payload if isinstance(payload, dict) else {}
    source_id = request_payload.get("source_id", request_payload.get("id"))
    if source_id in {None, ""}:
        raise ValueError("source_id is required")

    trim_payload = request_payload.get("trim")
    trim_request = trim_payload if isinstance(trim_payload, dict) else request_payload
    start_ms_value = trim_request.get(
        "start_ms",
        request_payload.get("start_ms", request_payload.get("trim_start_ms")),
    )
    if start_ms_value in {None, ""}:
        raise ValueError("start_ms is required")
    end_ms_value = trim_request.get(
        "end_ms",
        request_payload.get("end_ms", request_payload.get("trim_end_ms")),
    )

    return controller.trim_merge_source_to_derivative(
        str(source_id),
        start_ms=int(start_ms_value),
        end_ms=None if end_ms_value in {None, ""} else int(end_ms_value),
        export_settings=controller.trim_export_settings_from_payload(request_payload),
    )


def set_merge_source_position(
    controller: ProjectController,
    source_id: str,
    pip_size_percent: int | None = None,
    pip_x: float | None = None,
    pip_y: float | None = None,
    opacity: float | None = None,
    angle_role: str | None = None,
    placement_mode: str | None = None,
    placement_slot: str | None = None,
    target_kind: str | None = None,
    target_source_id: str | None = None,
) -> None:
    controller_module = _controller_module()
    for index, source in enumerate(controller.project.merge_sources):
        if source.id != source_id:
            continue
        explicit_placement_requested = any(
            value is not None
            for value in (placement_mode, placement_slot, target_kind, target_source_id)
        )
        role_changed = False
        previous_angle_role = source.angle_role
        if source.placement.order_index is None:
            source.placement.order_index = controller_module._merge_source_stable_order_index(
                source,
                index,
            )
        if source.placement.layer_index is None:
            source.placement.layer_index = source.placement.order_index
        if pip_size_percent is not None:
            source.pip_size_percent = max(1, min(95, int(pip_size_percent)))
        if pip_x is not None:
            source.pip_x = max(0.0, min(1.0, float(pip_x)))
        if pip_y is not None:
            source.pip_y = max(0.0, min(1.0, float(pip_y)))
        if opacity is not None:
            source.opacity = max(0.0, min(1.0, float(opacity)))
        if angle_role is not None:
            next_angle_role = controller_module._normalize_merge_source_angle_role(
                angle_role,
                source.asset,
            )
            role_changed = source.angle_role != next_angle_role
            previous_angle_role = source.angle_role
            source.angle_role = next_angle_role
        if explicit_placement_requested:
            next_mode = (
                source.placement.mode
                if placement_mode is None
                else controller_module._normalize_merge_source_placement_mode(placement_mode)
            )
            next_target_source_id = (
                source.placement.target_source_id
                if target_source_id is None
                else str(target_source_id).strip() or None
            )
            next_target_kind = controller_module._normalize_merge_source_placement_target_kind(
                source.placement.target_kind if target_kind is None else target_kind,
                target_source_id=next_target_source_id,
            )
            if next_target_kind != controller_module.MergePlacementTargetKind.MERGE_SOURCE:
                next_target_source_id = None
            next_slot_input = placement_slot
            if next_slot_input is None:
                next_slot_input = (
                    None if placement_mode is not None else source.placement.slot
                )
            source.placement.mode = next_mode
            source.placement.slot = controller_module._normalize_merge_source_placement_slot(
                next_slot_input,
                mode=next_mode,
            )
            source.placement.target_kind = next_target_kind
            source.placement.target_source_id = next_target_source_id
        if role_changed:
            if not explicit_placement_requested:
                controller_module._apply_merge_source_role_seed_defaults(
                    controller.project,
                    source,
                    reference_role=previous_angle_role,
                )
            for other_source in controller.project.merge_sources:
                if other_source.id == source_id:
                    continue
                controller_module._apply_merge_source_role_seed_defaults(
                    controller.project,
                    other_source,
                )
            controller_module._realign_live_merge_reference_state(controller.project)
        controller.project.touch()
        controller.project_changed.emit()
        return
    raise ValueError("Merge source not found")


def set_merge_source_sync_offset(
    controller: ProjectController,
    source_id: str,
    offset_ms: int,
) -> None:
    controller_module = _controller_module()
    for source in controller.project.merge_sources:
        if source.id != source_id:
            continue
        source.sync_offset_ms = int(offset_ms)
        preferred_source = controller_module._preferred_merge_reference_source(controller.project)
        if preferred_source is not None and preferred_source.id == source_id:
            controller.project.analysis.sync_offset_ms = source.sync_offset_ms
            controller.project.analysis.secondary_sync_source = "manual"
            controller.project.secondary_video = (
                source.asset if controller_module._source_supports_secondary_analysis(source) else None
            )
        controller._set_status(f"Adjusted merge source sync to {source.sync_offset_ms} ms.")
        controller.project.touch()
        controller.project_changed.emit()
        return
    raise ValueError("Merge source not found")


def reset_merge_defaults(controller: ProjectController) -> None:
    controller_module = _controller_module()
    controller.project.merge.enabled = False
    controller_module._reset_project_merge_defaults(controller.project)
    controller.project.touch()
    controller._set_status("Restored PiP defaults.")
    controller.project_changed.emit()


def adjust_merge_source_sync_offset(
    controller: ProjectController,
    source_id: str,
    delta_ms: int,
) -> None:
    for source in controller.project.merge_sources:
        if source.id == source_id:
            controller.set_merge_source_sync_offset(
                source_id,
                source.sync_offset_ms + int(delta_ms),
            )
            return
    raise ValueError("Merge source not found")


def adjust_sync_offset(controller: ProjectController, delta_ms: int) -> None:
    controller_module = _controller_module()
    controller.project.analysis.sync_offset_ms += delta_ms
    source = controller_module._preferred_merge_reference_source(controller.project)
    if source is not None:
        source.sync_offset_ms = controller.project.analysis.sync_offset_ms
        if controller_module._source_supports_secondary_analysis(source):
            controller.project.secondary_video = source.asset
    controller.project.analysis.secondary_sync_source = "manual"
    controller._set_status(
        f"Adjusted sync offset to {controller.project.analysis.sync_offset_ms} ms."
    )
    controller.project.touch()
    controller.project_changed.emit()


def set_sync_offset(controller: ProjectController, offset_ms: int) -> None:
    controller_module = _controller_module()
    controller.project.analysis.sync_offset_ms = offset_ms
    source = controller_module._preferred_merge_reference_source(controller.project)
    if source is not None:
        source.sync_offset_ms = controller.project.analysis.sync_offset_ms
        if controller_module._source_supports_secondary_analysis(source):
            controller.project.secondary_video = source.asset
    controller.project.analysis.secondary_sync_source = "manual"
    controller._set_status(
        f"Sync offset set to {controller.project.analysis.sync_offset_ms} ms."
    )
    controller.project.touch()
    controller.project_changed.emit()


def swap_videos(controller: ProjectController) -> None:
    controller_module = _controller_module()
    swapped_merge_source: MergeSource | None = None
    if controller.project.merge_sources:
        swapped_merge_source = controller_module._preferred_merge_reference_source(
            controller.project
        )
        if swapped_merge_source is None:
            return
        first_source = swapped_merge_source.asset
        swapped_merge_source.asset = controller.project.primary_video
        controller_module._reset_merge_source_trim_provenance(swapped_merge_source)
        controller.project.primary_video = first_source
    elif controller.project.secondary_video is None:
        return
    else:
        controller.project.primary_video, controller.project.secondary_video = (
            controller.project.secondary_video,
            controller.project.primary_video,
        )
    (
        controller.project.analysis.beep_time_ms_primary,
        controller.project.analysis.beep_time_ms_secondary,
    ) = (
        controller.project.analysis.beep_time_ms_secondary,
        controller.project.analysis.beep_time_ms_primary,
    )
    if swapped_merge_source is not None and controller_module._source_supports_secondary_analysis(
        swapped_merge_source
    ):
        analyzed_source = swapped_merge_source
    else:
        analyzed_source = controller_module._first_analyzable_merge_source(controller.project)
    if controller.project.merge_sources:
        controller.project.secondary_video = (
            None if analyzed_source is None else analyzed_source.asset
        )
    controller.project.analysis.analyzed_secondary_source_id = (
        None if analyzed_source is None else analyzed_source.id
    )
    controller.project.analysis.sync_offset_ms *= -1
    if analyzed_source is not None:
        analyzed_source.sync_offset_ms = controller.project.analysis.sync_offset_ms
    controller._set_status("Swapped primary and secondary videos.")
    controller.project.touch()
    controller.project_changed.emit()
