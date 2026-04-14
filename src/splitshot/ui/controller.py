from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from splitshot.analysis.detection import analyze_video_audio
from splitshot.analysis.sync import compute_sync_offset
from splitshot.config import AppSettings, load_settings, save_settings
from splitshot.domain.models import (
    BadgeSize,
    BadgeStyle,
    AspectRatio,
    ExportAudioCodec,
    ExportColorSpace,
    ExportFrameRate,
    ExportPreset,
    ExportQuality,
    ExportVideoCodec,
    MergeLayout,
    OverlayPosition,
    PipSize,
    Project,
    MergeSource,
    ScoreLetter,
    ScoreMark,
    ShotEvent,
    ShotSource,
    VideoAsset,
    project_to_dict,
)
from splitshot.export.presets import apply_export_preset as apply_export_preset_settings
from splitshot.media.probe import probe_video
from splitshot.persistence.projects import delete_project, load_project, save_project
from splitshot.scoring.logic import apply_scoring_preset, calculate_hit_factor
from splitshot.scoring.practiscore import (
    default_ruleset_for_match_type,
    import_practiscore_stage,
    normalize_match_type,
)


VALID_OVERLAY_BADGE_NAMES = {
    "timer_badge",
    "shot_badge",
    "current_shot_badge",
    "hit_factor_badge",
}


def _pip_size_percent_from_enum(size: PipSize) -> int:
    return {
        PipSize.SMALL: 25,
        PipSize.MEDIUM: 35,
        PipSize.LARGE: 50,
    }[size]


def _badge_font_size_from_enum(size: BadgeSize) -> int:
    return {
        BadgeSize.XS: 10,
        BadgeSize.S: 12,
        BadgeSize.M: 14,
        BadgeSize.L: 16,
        BadgeSize.XL: 20,
    }[size]


def _sync_secondary_video_from_merge_sources(project: Project) -> None:
    project.secondary_video = project.merge_sources[0].asset if project.merge_sources else None


def _reset_media_dependent_state_for_primary_video(project: Project) -> None:
    project.analysis.beep_time_ms_primary = None
    project.analysis.beep_time_ms_secondary = None
    project.analysis.sync_offset_ms = 0
    project.analysis.waveform_primary = []
    project.analysis.waveform_secondary = []
    project.analysis.shots = []
    project.analysis.events = []
    if project.scoring.imported_stage is None:
        project.scoring.penalties = 0.0
        project.scoring.penalty_counts = {}
        project.scoring.hit_factor = None
    project.secondary_video = None
    project.merge_sources = []
    project.merge.enabled = False
    project.merge.layout = MergeLayout.SIDE_BY_SIDE
    project.merge.pip_size = PipSize.MEDIUM
    project.merge.pip_size_percent = _pip_size_percent_from_enum(PipSize.MEDIUM)
    project.merge.pip_x = 1.0
    project.merge.pip_y = 1.0
    project.merge.primary_is_left_or_top = True
    project.overlay.custom_box_text = ""
    project.export.last_log = ""
    project.export.last_error = None
    project.ui_state.selected_shot_id = None
    project.ui_state.timeline_offset_ms = 0


class ProjectController(QObject):
    project_changed = Signal()
    settings_changed = Signal()
    project_path_changed = Signal(str)
    status_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.settings: AppSettings = load_settings()
        self.project = self._new_project_with_settings_defaults()
        self.project_path: Path | None = None
        self.status_message = "Ready."
        self._saved_snapshot = project_to_dict(self.project)

    def new_project(self) -> None:
        self.project = self._new_project_with_settings_defaults()
        self.project_path = None
        self._set_status("Ready.")
        self._saved_snapshot = project_to_dict(self.project)
        self.project_changed.emit()

    def has_unsaved_changes(self) -> bool:
        return project_to_dict(self.project) != self._saved_snapshot

    def load_primary_video(self, path: str) -> None:
        _reset_media_dependent_state_for_primary_video(self.project)
        self.project.primary_video = probe_video(path)
        self._set_status("Loaded primary video.")
        self.project.touch()
        self.project_changed.emit()

    def load_secondary_video(self, path: str) -> None:
        self.add_merge_source(path)

    def analyze_primary(self) -> None:
        if not self.project.primary_video.path:
            return
        self._set_status("Analyzing primary video for beep and shot detections...")
        result = analyze_video_audio(
            self.project.primary_video.path,
            self.project.analysis.detection_threshold,
        )
        self.project.analysis.beep_time_ms_primary = result.beep_time_ms
        self.project.analysis.waveform_primary = result.waveform
        self.project.analysis.shots = result.shots
        self.update_hit_factor()
        self._set_status(
            f"Primary analysis complete. Detected {len(result.shots)} shots"
            + ("" if result.beep_time_ms is None else f" and beep at {result.beep_time_ms} ms")
            + "."
        )
        self.project.touch()
        self.project_changed.emit()

    def analyze_secondary(self) -> None:
        if self.project.secondary_video is None or not self.project.secondary_video.path:
            return
        self._set_status("Analyzing secondary video and computing sync offset...")
        result = analyze_video_audio(
            self.project.secondary_video.path,
            self.project.analysis.detection_threshold,
        )
        self.project.analysis.beep_time_ms_secondary = result.beep_time_ms
        self.project.analysis.waveform_secondary = result.waveform
        self.project.analysis.sync_offset_ms = compute_sync_offset(
            self.project.analysis.beep_time_ms_primary,
            self.project.analysis.beep_time_ms_secondary,
        )
        self._set_status(
            "Secondary analysis complete."
            + ("" if result.beep_time_ms is None else f" Sync offset: {self.project.analysis.sync_offset_ms} ms.")
        )
        self.project.touch()
        self.project_changed.emit()

    def ingest_primary_video(self, path: str) -> None:
        self._set_status("Importing primary video...")
        self.load_primary_video(path)
        self.analyze_primary()

    def ingest_secondary_video(self, path: str) -> None:
        self._set_status("Importing secondary video...")
        self.load_secondary_video(path)

    def set_project_details(self, name: str | None = None, description: str | None = None) -> None:
        if name is not None:
            self.project.name = name.strip() or "Untitled Project"
        if description is not None:
            self.project.description = str(description)
        self.project.touch()
        self.project_changed.emit()

    def set_practiscore_context(
        self,
        match_type: str | None = None,
        stage_number: int | None = None,
        competitor_name: str | None = None,
        competitor_place: int | None = None,
    ) -> None:
        scoring = self.project.scoring
        changed = False
        if match_type is not None:
            clean_match_type = "" if not str(match_type).strip() else normalize_match_type(str(match_type))
            if scoring.match_type != clean_match_type:
                scoring.match_type = clean_match_type
                changed = True
            if clean_match_type:
                apply_scoring_preset(self.project, default_ruleset_for_match_type(clean_match_type))
        if stage_number is not None:
            next_stage_number = max(1, int(stage_number))
            if scoring.stage_number != next_stage_number:
                scoring.stage_number = next_stage_number
                changed = True
        if competitor_name is not None:
            next_competitor_name = str(competitor_name).strip()
            if scoring.competitor_name != next_competitor_name:
                scoring.competitor_name = next_competitor_name
                changed = True
        if competitor_place is not None or (competitor_place is None and scoring.competitor_place is not None):
            if scoring.competitor_place != competitor_place:
                scoring.competitor_place = competitor_place
                changed = True
        if changed:
            scoring.imported_stage = None
            scoring.penalties = 0.0
            scoring.penalty_counts = {}
            self.update_hit_factor()
            self._set_status("Updated PractiScore import settings.")
        self.project.touch()
        self.project_changed.emit()

    def import_practiscore_file(self, path: str, source_name: str | None = None) -> None:
        scoring = self.project.scoring
        previous_import = scoring.imported_stage
        if not scoring.match_type:
            raise ValueError("Choose a match type before importing PractiScore results.")
        if scoring.stage_number is None:
            raise ValueError("Stage number is required before importing PractiScore results.")
        if not scoring.competitor_name.strip():
            raise ValueError("Competitor name is required before importing PractiScore results.")
        imported = import_practiscore_stage(
            path,
            match_type=scoring.match_type,
            stage_number=scoring.stage_number,
            competitor_name=scoring.competitor_name,
            competitor_place=scoring.competitor_place,
            source_name=source_name,
        )
        apply_scoring_preset(self.project, imported.ruleset)
        self.project.scoring.enabled = True
        self.project.scoring.penalties = max(0.0, float(imported.manual_penalties))
        self.project.scoring.penalty_counts = dict(imported.penalty_counts)
        self.project.scoring.imported_stage = imported.imported_stage
        self.project.scoring.competitor_name = imported.imported_stage.competitor_name
        self.project.scoring.competitor_place = imported.imported_stage.competitor_place
        self.project.scoring.match_type = imported.imported_stage.match_type
        self.project.scoring.stage_number = imported.imported_stage.stage_number
        if previous_import is None:
            self.project.overlay.custom_box_enabled = True
            self.project.overlay.custom_box_mode = "imported_summary"
        self.update_hit_factor()
        stage_label = imported.imported_stage.stage_name or f"Stage {imported.imported_stage.stage_number}"
        self._set_status(f"Imported PractiScore results for {stage_label}.")
        self.project.touch()
        self.project_changed.emit()

    def add_merge_source(self, path: str) -> None:
        asset = probe_video(path)
        self.project.merge_sources.append(
            MergeSource(
                asset=asset,
                pip_x=self.project.merge.pip_x,
                pip_y=self.project.merge.pip_y,
            )
        )
        self.project.merge.enabled = True
        _sync_secondary_video_from_merge_sources(self.project)
        if len(self.project.merge_sources) == 1 and not asset.is_still_image:
            self._set_status("Imported merge media.")
            self.analyze_secondary()
            return
        self._set_status("Imported merge media.")
        self.project.touch()
        self.project_changed.emit()

    def remove_merge_source(self, source_id: str) -> None:
        before_sources = list(self.project.merge_sources)
        before_count = len(before_sources)
        self.project.merge_sources = [source for source in self.project.merge_sources if source.id != source_id]
        if len(self.project.merge_sources) == before_count:
            return
        if not self.project.merge_sources:
            self.project.merge.enabled = False
        removed_first = bool(before_sources and before_sources[0].id == source_id)
        _sync_secondary_video_from_merge_sources(self.project)
        if removed_first:
            self.project.analysis.beep_time_ms_secondary = None
            self.project.analysis.waveform_secondary = []
            if self.project.merge_sources and not self.project.merge_sources[0].asset.is_still_image:
                self.analyze_secondary()
                return
        self._set_status("Removed merge media.")
        self.project.touch()
        self.project_changed.emit()

    def set_detection_threshold(self, value: float) -> None:
        self.project.analysis.detection_threshold = value
        self.settings.detection_threshold = value
        save_settings(self.settings)
        self.settings_changed.emit()
        if self.project.primary_video.path:
            self.analyze_primary()
            if self.project.secondary_video is not None and not self.project.secondary_video.is_still_image:
                self.analyze_secondary()
            return
        self.project.touch()
        self._set_status("Updated detection threshold.")
        self.project_changed.emit()

    def set_beep_time(self, time_ms: int) -> None:
        self.project.analysis.beep_time_ms_primary = time_ms
        self.project.touch()
        self.project_changed.emit()

    def add_shot(self, time_ms: int) -> None:
        self.project.analysis.shots.append(
            ShotEvent(time_ms=time_ms, source=ShotSource.MANUAL, confidence=1.0)
        )
        self.project.sort_shots()
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def move_shot(self, shot_id: str, time_ms: int) -> None:
        for shot in self.project.analysis.shots:
            if shot.id == shot_id:
                shot.time_ms = max(0, time_ms)
                if shot.source == ShotSource.AUTO:
                    shot.source = ShotSource.MANUAL
                break
        self.project.sort_shots()
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def delete_shot(self, shot_id: str) -> None:
        self.project.analysis.shots = [shot for shot in self.project.analysis.shots if shot.id != shot_id]
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def nudge_shot(self, shot_id: str, delta_ms: int) -> None:
        for shot in self.project.analysis.shots:
            if shot.id == shot_id:
                self.move_shot(shot.id, shot.time_ms + delta_ms)
                return

    def select_shot(self, shot_id: str | None) -> None:
        self.project.ui_state.selected_shot_id = shot_id
        self.project_changed.emit()

    def assign_score(
        self,
        shot_id: str,
        letter: ScoreLetter | None = None,
        penalty_counts: dict[str, float] | None = None,
    ) -> None:
        for shot in self.project.analysis.shots:
            if shot.id == shot_id:
                if shot.score is None:
                    shot.score = ScoreMark(letter=letter or ScoreLetter.A)
                elif letter is not None:
                    shot.score.letter = letter
                if penalty_counts is not None:
                    shot.score.penalty_counts = {
                        str(key): max(0.0, float(value))
                        for key, value in penalty_counts.items()
                        if max(0.0, float(value)) > 0
                    }
                break
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def set_scoring_preset(self, ruleset: str) -> None:
        apply_scoring_preset(self.project, ruleset)
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def set_score_position(self, shot_id: str, x_norm: float, y_norm: float) -> None:
        for shot in self.project.analysis.shots:
            if shot.id == shot_id:
                if shot.score is None:
                    shot.score = ScoreMark()
                shot.score.x_norm = x_norm
                shot.score.y_norm = y_norm
                break
        self.project.touch()
        self.project_changed.emit()

    def set_penalties(self, penalties: float) -> None:
        self.project.scoring.penalties = max(0.0, float(penalties))
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def set_penalty_counts(self, penalty_counts: dict[str, float]) -> None:
        self.project.scoring.penalty_counts = {
            str(key): max(0.0, float(value))
            for key, value in penalty_counts.items()
        }
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def set_scoring_enabled(self, enabled: bool) -> None:
        self.project.scoring.enabled = enabled
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def set_overlay_position(self, position: OverlayPosition) -> None:
        self.project.overlay.position = position
        self.settings.overlay_position = position
        save_settings(self.settings)
        self.settings_changed.emit()
        self.project.touch()
        self.project_changed.emit()

    def set_badge_size(self, size: BadgeSize) -> None:
        self.project.overlay.badge_size = size
        self.project.overlay.font_size = _badge_font_size_from_enum(size)
        self.settings.badge_size = size
        save_settings(self.settings)
        self.settings_changed.emit()
        self.project.touch()
        self.project_changed.emit()

    def set_overlay_badge_layout(self, style_type: str, spacing: int, margin: int) -> None:
        self.project.overlay.style_type = style_type if style_type in {"square", "bubble", "rounded"} else "square"
        self.project.overlay.spacing = max(0, min(40, int(spacing)))
        self.project.overlay.margin = max(0, min(40, int(margin)))
        self.project.touch()
        self.project_changed.emit()

    def set_overlay_display_options(self, payload: dict[str, object]) -> None:
        overlay = self.project.overlay
        valid_quadrants = {
            "top_left",
            "top_middle",
            "top_right",
            "middle_left",
            "middle_middle",
            "middle_right",
            "bottom_left",
            "bottom_middle",
            "bottom_right",
        }
        valid_shot_quadrants = {*valid_quadrants, "custom"}
        valid_directions = {"right", "left", "down", "up"}
        valid_custom_box_modes = {"manual", "imported_summary"}
        if "max_visible_shots" in payload:
            overlay.max_visible_shots = max(1, min(40, int(payload["max_visible_shots"])))
        if "shot_quadrant" in payload:
            value = str(payload["shot_quadrant"])
            overlay.shot_quadrant = value if value in valid_shot_quadrants else "bottom_left"
        if "shot_direction" in payload:
            value = str(payload["shot_direction"])
            overlay.shot_direction = value if value in valid_directions else "right"
        if "custom_x" in payload:
            value = payload["custom_x"]
            overlay.custom_x = None if value in {"", None} else max(0.0, min(1.0, float(value)))
        if "custom_y" in payload:
            value = payload["custom_y"]
            overlay.custom_y = None if value in {"", None} else max(0.0, min(1.0, float(value)))
        for field_name in ("timer_x", "timer_y", "draw_x", "draw_y", "score_x", "score_y"):
            if field_name in payload:
                value = payload[field_name]
                setattr(
                    overlay,
                    field_name,
                    None if value in {"", None} else max(0.0, min(1.0, float(value))),
                )
        if "bubble_width" in payload:
            overlay.bubble_width = max(0, min(400, int(payload["bubble_width"])))
        if "bubble_height" in payload:
            overlay.bubble_height = max(0, min(220, int(payload["bubble_height"])))
        if "font_family" in payload:
            overlay.font_family = str(payload["font_family"])[:80]
        if "font_size" in payload:
            overlay.font_size = max(8, min(72, int(payload["font_size"])))
        if "font_bold" in payload:
            overlay.font_bold = bool(payload["font_bold"])
        if "font_italic" in payload:
            overlay.font_italic = bool(payload["font_italic"])
        for field_name in ("show_timer", "show_draw", "show_shots", "show_score"):
            if field_name in payload:
                setattr(overlay, field_name, bool(payload[field_name]))
        if "custom_box_enabled" in payload:
            overlay.custom_box_enabled = bool(payload["custom_box_enabled"])
        if "custom_box_mode" in payload:
            value = str(payload["custom_box_mode"])
            overlay.custom_box_mode = value if value in valid_custom_box_modes else "manual"
        if "custom_box_text" in payload:
            overlay.custom_box_text = str(payload["custom_box_text"])[:500]
        if "custom_box_quadrant" in payload:
            value = str(payload["custom_box_quadrant"])
            overlay.custom_box_quadrant = value if value in valid_quadrants else "top_right"
        if "custom_box_x" in payload:
            value = payload["custom_box_x"]
            overlay.custom_box_x = None if value in {"", None} else max(0.0, min(1.0, float(value)))
        if "custom_box_y" in payload:
            value = payload["custom_box_y"]
            overlay.custom_box_y = None if value in {"", None} else max(0.0, min(1.0, float(value)))
        if "custom_box_background_color" in payload:
            overlay.custom_box_background_color = str(payload["custom_box_background_color"])
        if "custom_box_text_color" in payload:
            overlay.custom_box_text_color = str(payload["custom_box_text_color"])
        if "custom_box_opacity" in payload:
            overlay.custom_box_opacity = max(0.0, min(1.0, float(payload["custom_box_opacity"])))
        if "custom_box_width" in payload:
            overlay.custom_box_width = max(0, int(payload["custom_box_width"]))
        if "custom_box_height" in payload:
            overlay.custom_box_height = max(0, int(payload["custom_box_height"]))
        self.project.touch()
        self.project_changed.emit()

    def set_overlay_badge_style(
        self,
        badge_name: str,
        background_color: str | None = None,
        text_color: str | None = None,
        opacity: float | None = None,
    ) -> None:
        if badge_name not in VALID_OVERLAY_BADGE_NAMES:
            raise ValueError(f"Unknown badge style: {badge_name}")
        style = getattr(self.project.overlay, badge_name)
        if not isinstance(style, BadgeStyle):
            raise ValueError(f"Unknown badge style: {badge_name}")
        if background_color is not None:
            style.background_color = background_color
        if text_color is not None:
            style.text_color = text_color
        if opacity is not None:
            style.opacity = max(0.0, min(1.0, opacity))
        self.project.touch()
        self.project_changed.emit()

    def set_scoring_color(self, letter: ScoreLetter, color: str) -> None:
        self.project.overlay.scoring_colors[letter.value] = color
        self.project.touch()
        self.project_changed.emit()

    def set_merge_enabled(self, enabled: bool) -> None:
        self.project.merge.enabled = enabled
        self.project.touch()
        self.project_changed.emit()

    def set_merge_layout(self, layout: MergeLayout) -> None:
        self.project.merge.layout = layout
        self.settings.merge_layout = layout
        save_settings(self.settings)
        self.settings_changed.emit()
        self.project.touch()
        self.project_changed.emit()

    def set_pip_size(self, size: PipSize) -> None:
        self.project.merge.pip_size = size
        self.project.merge.pip_size_percent = _pip_size_percent_from_enum(size)
        self.settings.pip_size = size
        save_settings(self.settings)
        self.settings_changed.emit()
        self.project.touch()
        self.project_changed.emit()

    def set_pip_size_percent(self, percent: int) -> None:
        self.project.merge.pip_size_percent = max(10, min(95, int(percent)))
        self.project.touch()
        self.project_changed.emit()

    def set_pip_position(self, pip_x: float | None = None, pip_y: float | None = None) -> None:
        if pip_x is not None:
            self.project.merge.pip_x = max(0.0, min(1.0, float(pip_x)))
        if pip_y is not None:
            self.project.merge.pip_y = max(0.0, min(1.0, float(pip_y)))
        if self.project.merge_sources:
            first_source = self.project.merge_sources[0]
            if pip_x is not None:
                first_source.pip_x = self.project.merge.pip_x
            if pip_y is not None:
                first_source.pip_y = self.project.merge.pip_y
        self.project.touch()
        self.project_changed.emit()

    def set_merge_source_position(
        self,
        source_id: str,
        pip_x: float | None = None,
        pip_y: float | None = None,
    ) -> None:
        for source in self.project.merge_sources:
            if source.id != source_id:
                continue
            if pip_x is not None:
                source.pip_x = max(0.0, min(1.0, float(pip_x)))
            if pip_y is not None:
                source.pip_y = max(0.0, min(1.0, float(pip_y)))
            if self.project.merge_sources and self.project.merge_sources[0].id == source_id:
                self.project.merge.pip_x = source.pip_x
                self.project.merge.pip_y = source.pip_y
            self.project.touch()
            self.project_changed.emit()
            return
        raise ValueError("Merge source not found")

    def add_timing_event(
        self,
        kind: str,
        after_shot_id: str | None = None,
        before_shot_id: str | None = None,
        label: str | None = None,
        note: str = "",
    ) -> None:
        from splitshot.domain.models import TimingEvent

        event_label = label or kind.replace("_", " ").title()
        self.project.analysis.events.append(
            TimingEvent(
                kind=kind,
                label=event_label,
                after_shot_id=after_shot_id,
                before_shot_id=before_shot_id,
                note=note,
            )
        )
        self.project.touch()
        self.project_changed.emit()

    def delete_timing_event(self, event_id: str) -> None:
        remaining_events = [event for event in self.project.analysis.events if event.id != event_id]
        if len(remaining_events) == len(self.project.analysis.events):
            raise ValueError("Timing event not found")
        self.project.analysis.events = remaining_events
        self.project.touch()
        self.project_changed.emit()

    def set_export_quality(self, quality: ExportQuality) -> None:
        self.project.export.quality = quality
        self.settings.export_quality = quality
        save_settings(self.settings)
        self.settings_changed.emit()
        self.project.touch()
        self.project_changed.emit()

    def apply_export_preset(self, preset: str) -> None:
        if preset == ExportPreset.CUSTOM.value:
            self.project.export.preset = ExportPreset.CUSTOM
            self.project.touch()
            self.project_changed.emit()
            return
        apply_export_preset_settings(self.project, preset)
        self.settings.export_quality = self.project.export.quality
        save_settings(self.settings)
        self.settings_changed.emit()
        self.project_changed.emit()

    def set_export_settings(self, payload: dict[str, object]) -> None:
        export = self.project.export
        if "quality" in payload:
            export.quality = ExportQuality(str(payload["quality"]))
            self.settings.export_quality = export.quality
            save_settings(self.settings)
            self.settings_changed.emit()
        if "aspect_ratio" in payload:
            export.aspect_ratio = AspectRatio(str(payload["aspect_ratio"]))
        if "crop_center_x" in payload:
            export.crop_center_x = float(payload["crop_center_x"])
        if "crop_center_y" in payload:
            export.crop_center_y = float(payload["crop_center_y"])
        if "target_width" in payload:
            value = payload["target_width"]
            export.target_width = None if value in {"", None} else max(2, int(value))
        if "target_height" in payload:
            value = payload["target_height"]
            export.target_height = None if value in {"", None} else max(2, int(value))
        if "frame_rate" in payload:
            export.frame_rate = ExportFrameRate(str(payload["frame_rate"]))
        if "video_codec" in payload:
            export.video_codec = ExportVideoCodec(str(payload["video_codec"]))
        if "video_bitrate_mbps" in payload:
            export.video_bitrate_mbps = max(0.1, float(payload["video_bitrate_mbps"]))
        if "audio_codec" in payload:
            export.audio_codec = ExportAudioCodec(str(payload["audio_codec"]))
        if "audio_sample_rate" in payload:
            export.audio_sample_rate = max(8000, int(payload["audio_sample_rate"]))
        if "audio_bitrate_kbps" in payload:
            export.audio_bitrate_kbps = max(32, int(payload["audio_bitrate_kbps"]))
        if "color_space" in payload:
            export.color_space = ExportColorSpace(str(payload["color_space"]))
        if "two_pass" in payload:
            export.two_pass = bool(payload["two_pass"])
        if "ffmpeg_preset" in payload:
            export.ffmpeg_preset = str(payload["ffmpeg_preset"])
        export.preset = ExportPreset.CUSTOM
        self.project.touch()
        self.project_changed.emit()

    def adjust_sync_offset(self, delta_ms: int) -> None:
        self.project.analysis.sync_offset_ms += delta_ms
        self._set_status(f"Adjusted sync offset to {self.project.analysis.sync_offset_ms} ms.")
        self.project.touch()
        self.project_changed.emit()

    def set_sync_offset(self, offset_ms: int) -> None:
        self.project.analysis.sync_offset_ms = offset_ms
        self._set_status(f"Sync offset set to {self.project.analysis.sync_offset_ms} ms.")
        self.project.touch()
        self.project_changed.emit()

    def swap_videos(self) -> None:
        if self.project.merge_sources:
            first_source = self.project.merge_sources[0].asset
            self.project.merge_sources[0].asset = self.project.primary_video
            self.project.primary_video = first_source
            _sync_secondary_video_from_merge_sources(self.project)
        elif self.project.secondary_video is None:
            return
        else:
            self.project.primary_video, self.project.secondary_video = (
                self.project.secondary_video,
                self.project.primary_video,
            )
        self.project.analysis.beep_time_ms_primary, self.project.analysis.beep_time_ms_secondary = (
            self.project.analysis.beep_time_ms_secondary,
            self.project.analysis.beep_time_ms_primary,
        )
        self.project.analysis.sync_offset_ms *= -1
        self._set_status("Swapped primary and secondary videos.")
        self.project.touch()
        self.project_changed.emit()

    def save_project(self, path: str | None = None) -> None:
        target_path = Path(path) if path else self.project_path
        if target_path is None:
            raise ValueError("Project path is required")
        self.project.touch()
        self.project_path = save_project(self.project, target_path)
        self.project = load_project(self.project_path)
        self._saved_snapshot = project_to_dict(self.project)
        self._remember_project(self.project_path)
        self._set_status(f"Saved project to {self.project_path}.")
        self.project_path_changed.emit(str(self.project_path))
        self.project_changed.emit()

    def open_project(self, path: str) -> None:
        self.project = load_project(path)
        self.project_path = Path(path)
        self._saved_snapshot = project_to_dict(self.project)
        self._remember_project(self.project_path)
        self._set_status(f"Opened project from {self.project_path}.")
        self.project_path_changed.emit(str(self.project_path))
        self.project_changed.emit()

    def delete_current_project(self) -> None:
        if self.project_path is None:
            return
        delete_project(self.project_path)
        self.new_project()
        self._set_status("Deleted the saved project bundle.")

    def restore_defaults(self) -> None:
        self.settings = AppSettings()
        save_settings(self.settings)
        self.project.analysis.detection_threshold = self.settings.detection_threshold
        self.project.overlay.position = self.settings.overlay_position
        self.project.merge.layout = self.settings.merge_layout
        self.project.merge.pip_size = self.settings.pip_size
        self.project.merge.pip_size_percent = _pip_size_percent_from_enum(self.settings.pip_size)
        self.project.export.quality = self.settings.export_quality
        self.project.overlay.badge_size = self.settings.badge_size
        self.project.overlay.font_size = _badge_font_size_from_enum(self.settings.badge_size)
        self.project.touch()
        self._set_status("Restored SplitShot defaults.")
        self.settings_changed.emit()
        self.project_changed.emit()

    def update_hit_factor(self) -> None:
        self.project.sort_shots()
        self.project.scoring.hit_factor = calculate_hit_factor(self.project)

    def _remember_project(self, path: Path) -> None:
        entries = [str(path), *[item for item in self.settings.recent_projects if item != str(path)]]
        self.settings.recent_projects = entries[:10]
        save_settings(self.settings)
        self.settings_changed.emit()

    def _new_project_with_settings_defaults(self) -> Project:
        project = Project()
        project.analysis.detection_threshold = self.settings.detection_threshold
        project.overlay.position = self.settings.overlay_position
        project.merge.layout = self.settings.merge_layout
        project.merge.pip_size = self.settings.pip_size
        project.merge.pip_size_percent = _pip_size_percent_from_enum(self.settings.pip_size)
        project.export.quality = self.settings.export_quality
        project.overlay.badge_size = self.settings.badge_size
        project.overlay.font_size = _badge_font_size_from_enum(self.settings.badge_size)
        return project

    def _set_status(self, message: str) -> None:
        self.status_message = message
        self.status_changed.emit(message)
