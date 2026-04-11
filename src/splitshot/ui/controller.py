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


class ProjectController(QObject):
    project_changed = Signal()
    settings_changed = Signal()
    project_path_changed = Signal(str)
    status_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.settings: AppSettings = load_settings()
        self.project = Project()
        self.project.analysis.detection_threshold = self.settings.detection_threshold
        self.project.overlay.position = self.settings.overlay_position
        self.project.merge.layout = self.settings.merge_layout
        self.project.merge.pip_size = self.settings.pip_size
        self.project.export.quality = self.settings.export_quality
        self.project.overlay.badge_size = self.settings.badge_size
        self.project_path: Path | None = None
        self.status_message = "Ready."
        self._saved_snapshot = project_to_dict(self.project)

    def new_project(self) -> None:
        self.project = Project()
        self.project.analysis.detection_threshold = self.settings.detection_threshold
        self.project.overlay.position = self.settings.overlay_position
        self.project.merge.layout = self.settings.merge_layout
        self.project.merge.pip_size = self.settings.pip_size
        self.project.export.quality = self.settings.export_quality
        self.project.overlay.badge_size = self.settings.badge_size
        self.project_path = None
        self._set_status("Ready.")
        self._saved_snapshot = project_to_dict(self.project)
        self.project_changed.emit()

    def has_unsaved_changes(self) -> bool:
        return project_to_dict(self.project) != self._saved_snapshot

    def load_primary_video(self, path: str) -> None:
        self.project.primary_video = probe_video(path)
        self.project.analysis.waveform_primary = []
        self.project.analysis.shots = []
        self.project.analysis.beep_time_ms_primary = None
        self._set_status("Loaded primary video.")
        self.project.touch()
        self.project_changed.emit()

    def load_secondary_video(self, path: str) -> None:
        self.project.secondary_video = probe_video(path)
        self.project.merge.enabled = True
        self.project.analysis.waveform_secondary = []
        self.project.analysis.beep_time_ms_secondary = None
        self._set_status("Loaded secondary video.")
        self.project.touch()
        self.project_changed.emit()

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
        self.analyze_secondary()

    def set_detection_threshold(self, value: float) -> None:
        self.project.analysis.detection_threshold = value
        self.settings.detection_threshold = value
        save_settings(self.settings)
        self.settings_changed.emit()
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

    def assign_score(self, shot_id: str, letter: ScoreLetter) -> None:
        for shot in self.project.analysis.shots:
            if shot.id == shot_id:
                if shot.score is None:
                    shot.score = ScoreMark(letter=letter)
                else:
                    shot.score.letter = letter
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

    def set_penalties(self, penalties: int) -> None:
        self.project.scoring.penalties = max(0, penalties)
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
        self.settings.badge_size = size
        save_settings(self.settings)
        self.settings_changed.emit()
        self.project.touch()
        self.project_changed.emit()

    def set_overlay_badge_style(
        self,
        badge_name: str,
        background_color: str | None = None,
        text_color: str | None = None,
        opacity: float | None = None,
    ) -> None:
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
        self.settings.pip_size = size
        save_settings(self.settings)
        self.settings_changed.emit()
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
        if self.project.secondary_video is None:
            return
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
        self.project.export.quality = self.settings.export_quality
        self.project.overlay.badge_size = self.settings.badge_size
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

    def _set_status(self, message: str) -> None:
        self.status_message = message
        self.status_changed.emit(message)
