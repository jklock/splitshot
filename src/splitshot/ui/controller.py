from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, fields
from inspect import Parameter, signature
from pathlib import Path
import re

from PySide6.QtCore import QObject, Signal

from splitshot.analysis.detection import analyze_video_audio, timing_change_proposals_from_review_suggestions, TimingReviewSuggestion
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
    _popup_bubble_from_dict,
    MergeLayout,
    OverlayPosition,
    OverlayTextBox,
    PopupBubble,
    PipSize,
    Project,
    MergeSource,
    ScoreLetter,
    ScoreMark,
    ShotEvent,
    ShotMLSettings,
    ShotSource,
    TimingEvent,
    TimingChangeProposal,
    VideoAsset,
    legacy_custom_box_as_text_box,
    overlay_text_boxes_for_render,
    project_to_dict,
    sync_overlay_legacy_custom_box_fields,
)
from splitshot.export.presets import apply_export_preset as apply_export_preset_settings
from splitshot.media.ffmpeg import MediaError
from splitshot.media.probe import probe_video
from splitshot.persistence.projects import (
    INPUT_DIRNAME,
    PRACTISCORE_DIRNAME,
    copy_path_to_project_subdir,
    default_project_output_path,
    delete_project,
    ensure_project_suffix,
    load_project,
    normalize_project_path,
    project_has_metadata,
    save_project,
)
from splitshot.scoring.logic import (
    apply_scoring_preset,
    calculate_hit_factor,
    default_score_mark_for_ruleset,
    ensure_default_shot_scores,
)
from splitshot.scoring.practiscore import (
    PractiScoreOptions,
    _normalize_name,
    describe_practiscore_file,
    default_ruleset_for_match_type,
    import_practiscore_stage,
    infer_practiscore_context,
    normalize_match_type,
)
from splitshot.timeline.model import (
    normalize_project_timing_events,
    normalized_timing_event_for_shots,
    sort_shots,
)


VALID_OVERLAY_BADGE_NAMES = {
    "timer_badge",
    "shot_badge",
    "current_shot_badge",
    "hit_factor_badge",
}

_PRACTISCORE_FILE_SUFFIXES = {".csv", ".txt"}

_VALID_BROWSER_UI_TOOLS = {
    "project",
    "scoring",
    "shotml",
    "timing",
    "merge",
    "overlay",
    "review",
    "popup",
    "export",
    "metrics",
}

_VALID_WAVEFORM_MODES = {"select", "add"}


@dataclass(slots=True)
class _OriginalShotState:
    time_ms: int
    source: ShotSource
    confidence: float | None
    score: ScoreMark | None


@dataclass(slots=True)
class _ShotSelectionContext:
    shot_id: str
    time_ms: int
    index: int
    fallback_mode: str = "time"


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


def _practiscore_name_matches(input_name: str, candidate_name: str) -> bool:
    if _normalize_name(input_name) == _normalize_name(candidate_name):
        return True
    input_parts = sorted(part for part in re.split(r"[^A-Za-z0-9]+", input_name.lower()) if part)
    candidate_parts = sorted(part for part in re.split(r"[^A-Za-z0-9]+", candidate_name.lower()) if part)
    return bool(input_parts) and input_parts == candidate_parts


def _normalize_media_name_fragment(value: str) -> str:
    return re.sub(r"\d+", lambda match: str(int(match.group(0))), value.lower())


def _media_name_tokens(path: str | Path) -> set[str]:
    stem = _normalize_media_name_fragment(Path(path).stem)
    return {token for token in re.split(r"[^a-z0-9]+", stem) if token}


def _project_media_recovery_score(
    expected_path: str,
    expected_asset: VideoAsset,
    candidate_path: Path,
    candidate_asset: VideoAsset,
) -> int:
    if expected_asset.is_still_image != candidate_asset.is_still_image:
        return -1
    if expected_asset.width and candidate_asset.width and expected_asset.width != candidate_asset.width:
        return -1
    if expected_asset.height and candidate_asset.height and expected_asset.height != candidate_asset.height:
        return -1
    if expected_asset.rotation != candidate_asset.rotation:
        return -1
    if expected_asset.duration_ms and candidate_asset.duration_ms:
        duration_delta = abs(expected_asset.duration_ms - candidate_asset.duration_ms)
        if duration_delta > 2000:
            return -1
    else:
        duration_delta = None
    fps_delta = abs(expected_asset.fps - candidate_asset.fps)
    if expected_asset.fps and candidate_asset.fps and fps_delta > 1.0:
        return -1

    expected_name = Path(expected_path).name.lower()
    expected_stem = Path(expected_path).stem.lower()
    expected_name_normalized = _normalize_media_name_fragment(Path(expected_path).name)
    expected_stem_normalized = _normalize_media_name_fragment(Path(expected_path).stem)
    candidate_name = candidate_path.name.lower()
    candidate_stem = candidate_path.stem.lower()
    candidate_name_normalized = _normalize_media_name_fragment(candidate_path.name)
    candidate_stem_normalized = _normalize_media_name_fragment(candidate_path.stem)
    score = 0

    if expected_name and candidate_name == expected_name:
        score += 1000
    elif expected_name_normalized and candidate_name_normalized == expected_name_normalized:
        score += 950
    elif expected_stem and candidate_stem == expected_stem:
        score += 900
    elif expected_stem_normalized and candidate_stem_normalized == expected_stem_normalized:
        score += 850
    elif expected_stem and (expected_stem in candidate_stem or candidate_stem in expected_stem):
        score += 700
    elif expected_stem_normalized and (
        expected_stem_normalized in candidate_stem_normalized
        or candidate_stem_normalized in expected_stem_normalized
    ):
        score += 650
    else:
        score += 120 * len(_media_name_tokens(expected_path).intersection(_media_name_tokens(candidate_path)))

    if Path(expected_path).suffix.lower() == candidate_path.suffix.lower():
        score += 20
    if expected_asset.width and candidate_asset.width == expected_asset.width:
        score += 150
    if expected_asset.height and candidate_asset.height == expected_asset.height:
        score += 150
    if duration_delta is not None:
        if duration_delta <= 50:
            score += 200
        elif duration_delta <= 250:
            score += 150
        elif duration_delta <= 1000:
            score += 100
        else:
            score += 50
    if expected_asset.fps and candidate_asset.fps:
        if fps_delta <= 0.01:
            score += 60
        elif fps_delta <= 0.1:
            score += 40
        else:
            score += 10
    if expected_asset.audio_sample_rate and candidate_asset.audio_sample_rate == expected_asset.audio_sample_rate:
        score += 25
    score += 10
    return score


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
    project.analysis.timing_change_proposals = []
    project.analysis.last_shotml_run_summary = {}
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
    for text_box in project.overlay.text_boxes:
        text_box.text = ""
    sync_overlay_legacy_custom_box_fields(project.overlay)
    project.popups = []
    project.export.last_log = ""
    project.export.last_error = None
    project.ui_state.selected_shot_id = None
    project.ui_state.timeline_offset_ms = 0
    project.ui_state.scoring_shot_expansion = {}
    project.ui_state.waveform_shot_amplitudes = {}
    project.ui_state.timing_edit_shot_ids = []
    project.ui_state.review_text_box_expansion = {}
    project.ui_state.popup_bubble_expansion = {}
    project.ui_state.merge_source_expansion = {}
    project.ui_state.shotml_section_expansion = {}


def _run_analyze_video_audio(path: str, threshold: float, settings: ShotMLSettings):
    parameters = list(signature(analyze_video_audio).parameters.values())
    if any(parameter.kind == Parameter.VAR_POSITIONAL for parameter in parameters) or len(parameters) >= 3:
        return analyze_video_audio(path, threshold, settings)
    return analyze_video_audio(path, threshold)


def _shot_selection_context(
    project: Project,
    shot_id: str | None,
    *,
    fallback_mode: str = "time",
) -> _ShotSelectionContext | None:
    if shot_id is None:
        return None
    shots = sort_shots(project.analysis.shots)
    for index, shot in enumerate(shots):
        if shot.id == shot_id:
            return _ShotSelectionContext(
                shot_id=shot.id,
                time_ms=shot.time_ms,
                index=index,
                fallback_mode=fallback_mode,
            )
    return None


def _fallback_selected_shot_id(
    project: Project,
    context: _ShotSelectionContext | None,
) -> str | None:
    shots = sort_shots(project.analysis.shots)
    if not shots or context is None:
        return None
    if any(shot.id == context.shot_id for shot in shots):
        return context.shot_id
    if context.fallback_mode == "index":
        return shots[min(context.index, len(shots) - 1)].id
    return min(
        enumerate(shots),
        key=lambda item: (abs(item[1].time_ms - context.time_ms), item[0]),
    )[1].id


def _revalidate_timing_ui_state(
    project: Project,
    fallback_context: _ShotSelectionContext | None = None,
) -> bool:
    valid_shot_ids = {shot.id for shot in project.analysis.shots}
    ui_state = project.ui_state
    changed = False

    if ui_state.selected_shot_id and ui_state.selected_shot_id not in valid_shot_ids:
        next_selected_shot_id = _fallback_selected_shot_id(project, fallback_context)
        if ui_state.selected_shot_id != next_selected_shot_id:
            ui_state.selected_shot_id = next_selected_shot_id
            changed = True
    elif fallback_context and ui_state.selected_shot_id is None:
        next_selected_shot_id = _fallback_selected_shot_id(project, fallback_context)
        if next_selected_shot_id is not None:
            ui_state.selected_shot_id = next_selected_shot_id
            changed = True

    next_scoring_expansion = {
        shot_id: expanded
        for shot_id, expanded in ui_state.scoring_shot_expansion.items()
        if shot_id in valid_shot_ids
    }
    if ui_state.scoring_shot_expansion != next_scoring_expansion:
        ui_state.scoring_shot_expansion = next_scoring_expansion
        changed = True

    next_waveform_amplitudes = {
        shot_id: amplitude
        for shot_id, amplitude in ui_state.waveform_shot_amplitudes.items()
        if shot_id in valid_shot_ids
    }
    if ui_state.waveform_shot_amplitudes != next_waveform_amplitudes:
        ui_state.waveform_shot_amplitudes = next_waveform_amplitudes
        changed = True

    next_timing_edit_shot_ids = [
        shot_id for shot_id in ui_state.timing_edit_shot_ids if shot_id in valid_shot_ids
    ]
    if ui_state.timing_edit_shot_ids != next_timing_edit_shot_ids:
        ui_state.timing_edit_shot_ids = next_timing_edit_shot_ids
        changed = True

    valid_text_box_ids = {box.id for box in project.overlay.text_boxes}
    next_review_text_box_expansion = {
        box_id: expanded
        for box_id, expanded in ui_state.review_text_box_expansion.items()
        if box_id in valid_text_box_ids
    }
    if ui_state.review_text_box_expansion != next_review_text_box_expansion:
        ui_state.review_text_box_expansion = next_review_text_box_expansion
        changed = True

    return changed


def _merge_reanalyzed_shots(
    previous_shots: list[ShotEvent],
    detected_shots: list[ShotEvent],
    settings: ShotMLSettings,
) -> list[ShotEvent]:
    merged_shots = [deepcopy(shot) for shot in detected_shots]
    for shot in merged_shots:
        shot.shotml_time_ms = shot.time_ms
        shot.shotml_confidence = shot.confidence
    manual_shots = [
        deepcopy(shot)
        for shot in previous_shots
        if shot.source == ShotSource.MANUAL and shot.user_added
    ]
    if not manual_shots:
        return sort_shots(merged_shots)

    overlap_window_ms = max(1, int(settings.min_shot_interval_ms or 0))
    for manual_shot in sort_shots(manual_shots):
        merged_shots = [
            shot
            for shot in merged_shots
            if abs(int(shot.time_ms) - int(manual_shot.time_ms)) > overlap_window_ms
        ]
        merged_shots.append(manual_shot)
    return sort_shots(merged_shots)


def _nearest_shot_id_by_time(shots: list[ShotEvent], target_time_ms: int) -> str | None:
    if not shots:
        return None
    return min(
        enumerate(shots),
        key=lambda item: (abs(int(item[1].time_ms) - int(target_time_ms)), item[0]),
    )[1].id


def _event_boundary_index(shots: list[ShotEvent], boundary_time_ms: int) -> int:
    for index, shot in enumerate(shots):
        if int(shot.time_ms) >= int(boundary_time_ms):
            return index
    return len(shots)


def _reanchor_timing_events_for_shots(
    events: list[TimingEvent],
    previous_shots: list[ShotEvent],
    next_shots: list[ShotEvent],
) -> list[TimingEvent]:
    if not events:
        return []
    previous_by_id = {shot.id: shot for shot in previous_shots}
    reanchored_events: list[TimingEvent] = []

    for event in events:
        if not event.after_shot_id and not event.before_shot_id:
            reanchored_events.append(deepcopy(event))
            continue

        previous_after = previous_by_id.get(event.after_shot_id or "")
        previous_before = previous_by_id.get(event.before_shot_id or "")
        rebased_event = deepcopy(event)

        if previous_after is not None and previous_before is not None:
            boundary_time_ms = previous_after.time_ms + max(1, (previous_before.time_ms - previous_after.time_ms) // 2)
            boundary_index = _event_boundary_index(next_shots, boundary_time_ms)
            rebased_event.after_shot_id = next_shots[boundary_index - 1].id if boundary_index > 0 else None
            rebased_event.before_shot_id = next_shots[boundary_index].id if boundary_index < len(next_shots) else None
        elif previous_after is not None:
            rebased_event.after_shot_id = _nearest_shot_id_by_time(next_shots, previous_after.time_ms)
            rebased_event.before_shot_id = None
        elif previous_before is not None:
            rebased_event.after_shot_id = None
            rebased_event.before_shot_id = _nearest_shot_id_by_time(next_shots, previous_before.time_ms)
        else:
            rebased_event.after_shot_id = None
            rebased_event.before_shot_id = None

        normalized_event = normalized_timing_event_for_shots(rebased_event, next_shots)
        if normalized_event is not None:
            reanchored_events.append(normalized_event)

    return reanchored_events


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
        self._practiscore_source_path: Path | None = None
        self._practiscore_source_name: str = ""
        self._practiscore_options: PractiScoreOptions | None = None
        self.status_message = "Ready."
        self._saved_snapshot = project_to_dict(self.project)
        self._original_shot_state_by_id: dict[str, _OriginalShotState] = {}
        self._autosave_in_progress = False
        self._remember_original_shots()
        self.project_changed.connect(self._autosave_project_if_needed)

    def new_project(self) -> None:
        self.project = self._new_project_with_settings_defaults()
        self.project_path = None
        self._clear_practiscore_source()
        self._set_status("Ready.")
        self._saved_snapshot = project_to_dict(self.project)
        self._remember_original_shots()
        self.project_changed.emit()

    def has_unsaved_changes(self) -> bool:
        return project_to_dict(self.project) != self._saved_snapshot

    def load_primary_video(self, path: str) -> None:
        _reset_media_dependent_state_for_primary_video(self.project)
        self.project.primary_video = probe_video(path)
        self._remember_original_shots()
        self._set_status("Loaded primary video.")
        self.project.touch()
        self.project_changed.emit()

    def load_secondary_video(self, path: str) -> None:
        self.add_merge_source(path)

    def analyze_primary(self) -> None:
        if not self.project.primary_video.path:
            return
        selection_context = _shot_selection_context(
            self.project,
            self.project.ui_state.selected_shot_id,
            fallback_mode="time",
        )
        previous_shots = [deepcopy(shot) for shot in self.project.analysis.shots]
        previous_events = [deepcopy(event) for event in self.project.analysis.events]
        self._set_status("Analyzing primary video for beep and shot detections...")
        result = _run_analyze_video_audio(
            self.project.primary_video.path,
            self.project.analysis.shotml_settings.detection_threshold,
            self.project.analysis.shotml_settings,
        )
        self.project.analysis.beep_time_ms_primary = result.beep_time_ms
        self.project.analysis.waveform_primary = result.waveform
        self.project.analysis.shots = _merge_reanalyzed_shots(
            previous_shots,
            result.shots,
            self.project.analysis.shotml_settings,
        )
        self.project.analysis.events = _reanchor_timing_events_for_shots(
            previous_events,
            previous_shots,
            self.project.analysis.shots,
        )
        self.project.analysis.detection_review_suggestions = [
            asdict(suggestion) for suggestion in result.review_suggestions
        ]
        self.project.analysis.detection_threshold = self.project.analysis.shotml_settings.detection_threshold
        self.project.analysis.timing_change_proposals = []
        self.project.analysis.last_shotml_run_summary = {
            "video_path": self.project.primary_video.path,
            "threshold": self.project.analysis.shotml_settings.detection_threshold,
            "sample_rate": result.sample_rate,
            "beep_time_ms": result.beep_time_ms,
            "shot_count": len(result.shots),
            "review_suggestion_count": len(result.review_suggestions),
        }
        ensure_default_shot_scores(self.project)
        normalize_project_timing_events(self.project)
        _revalidate_timing_ui_state(self.project, selection_context)
        self._remember_original_shots()
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
        result = _run_analyze_video_audio(
            self.project.secondary_video.path,
            self.project.analysis.shotml_settings.detection_threshold,
            self.project.analysis.shotml_settings,
        )
        self.project.analysis.beep_time_ms_secondary = result.beep_time_ms
        self.project.analysis.waveform_secondary = result.waveform
        self.project.analysis.sync_offset_ms = compute_sync_offset(
            self.project.analysis.beep_time_ms_primary,
            self.project.analysis.beep_time_ms_secondary,
        )
        if self.project.merge_sources:
            self.project.merge_sources[0].sync_offset_ms = self.project.analysis.sync_offset_ms
        self._set_status(
            "Secondary analysis complete."
            + ("" if result.beep_time_ms is None else f" Sync offset: {self.project.analysis.sync_offset_ms} ms.")
        )
        self.project.touch()
        self.project_changed.emit()

    def ingest_primary_video(self, path: str, source_name: str | None = None) -> None:
        self._set_status("Importing primary video...")
        self.load_primary_video(self._stage_project_input_path(path, source_name=source_name))
        self.analyze_primary()

    def ingest_secondary_video(self, path: str, source_name: str | None = None) -> None:
        self._set_status("Importing secondary video...")
        self.load_secondary_video(self._stage_project_input_path(path, source_name=source_name))

    def set_project_details(self, name: str | None = None, description: str | None = None) -> None:
        changed = False
        if name is not None:
            next_name = name.strip() or "Untitled Project"
            if self.project.name != next_name:
                self.project.name = next_name
                changed = True
        if description is not None:
            next_description = str(description)
            if self.project.description != next_description:
                self.project.description = next_description
                changed = True
        if changed:
            self.project.touch()
            self.project_changed.emit()
            self._set_status("Updated project details.")
        else:
            self._set_status("Project details unchanged.")

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
                target_ruleset = default_ruleset_for_match_type(clean_match_type)
                if scoring.ruleset != target_ruleset:
                    changed = True
                apply_scoring_preset(self.project, target_ruleset)
        if stage_number is not None or scoring.stage_number is not None:
            next_stage_number = None if stage_number is None else max(1, int(stage_number))
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
            if self._can_reimport_practiscore_source():
                self._import_practiscore_source(
                    str(self._practiscore_source_path),
                    self._practiscore_source_name,
                )
                return
            scoring.imported_stage = None
            scoring.penalties = 0.0
            scoring.penalty_counts = {}
            self.update_hit_factor()
            self._set_status("Updated PractiScore import settings.")
        else:
            self._set_status("PractiScore import settings unchanged.")
        self.project.touch()
        self.project_changed.emit()

    def import_practiscore_file(self, path: str, source_name: str | None = None) -> None:
        path = self._stage_practiscore_source_path(path, source_name=source_name)
        self._set_practiscore_source(path, source_name)
        self._import_practiscore_source(path, source_name)

    def practiscore_browser_state(self) -> dict[str, object]:
        options = self._practiscore_options
        competitors = [] if options is None else [
            {"name": option.name, "place": option.place}
            for option in options.competitors
        ]
        return {
            "has_source": self._practiscore_source_path is not None,
            "source_name": self._practiscore_source_name,
            "detected_match_type": "" if options is None else options.match_type,
            "stage_numbers": [] if options is None else list(options.stage_numbers),
            "competitors": competitors,
        }

    def _clear_practiscore_source(self) -> None:
        self._practiscore_source_path = None
        self._practiscore_source_name = ""
        self._practiscore_options = None
        self.project.scoring.practiscore_source_path = ""
        self.project.scoring.practiscore_source_name = ""

    def _set_practiscore_source(self, path: str, source_name: str | None = None) -> None:
        resolved_path = Path(path)
        display_name = source_name or resolved_path.name
        options = describe_practiscore_file(resolved_path, source_name=display_name)
        self._practiscore_source_path = resolved_path
        self._practiscore_source_name = display_name
        self._practiscore_options = options
        self.project.scoring.practiscore_source_path = str(resolved_path)
        self.project.scoring.practiscore_source_name = display_name

    def _project_practiscore_candidates(self) -> list[Path]:
        if self.project_path is None:
            return []
        practiscore_dir = self.project_path / PRACTISCORE_DIRNAME
        if not practiscore_dir.is_dir():
            return []

        candidates: list[Path] = []
        for path in practiscore_dir.iterdir():
            if not path.is_file() or path.suffix.lower() not in _PRACTISCORE_FILE_SUFFIXES:
                continue
            candidates.append(path.resolve())
        candidates.sort(key=lambda item: (item.stat().st_mtime_ns, item.name.lower()), reverse=True)
        return candidates

    def _recover_practiscore_path_from_project_folder(
        self,
        stored_path: str,
        stored_name: str | None,
    ) -> tuple[Path | None, str | None, bool]:
        candidates = self._project_practiscore_candidates()
        if not candidates:
            return None, stored_name, False

        preferred_names = [
            stored_name or "",
            Path(stored_path).name if stored_path else "",
        ]
        imported_stage = self.project.scoring.imported_stage
        if imported_stage is not None:
            preferred_names.extend([
                imported_stage.source_name or "",
                Path(imported_stage.source_path).name if imported_stage.source_path else "",
            ])

        for preferred_name in preferred_names:
            clean_name = preferred_name.strip()
            if not clean_name:
                continue
            for candidate in candidates:
                if candidate.name == clean_name:
                    return candidate, clean_name, True

        if stored_path or imported_stage is not None or len(candidates) != 1:
            return None, stored_name, False
        return candidates[0], stored_name or candidates[0].name, True

    def _restore_practiscore_source_from_project(self, *, emit_change: bool = True) -> bool:
        stored_path = self.project.scoring.practiscore_source_path.strip()
        stored_name = self.project.scoring.practiscore_source_name.strip() or None
        resolved_path = Path(stored_path) if stored_path else None
        recovered_from_folder = False

        if resolved_path is None or not resolved_path.exists():
            recovered_path, recovered_name, recovered_from_folder = self._recover_practiscore_path_from_project_folder(
                stored_path,
                stored_name,
            )
            if recovered_path is not None:
                resolved_path = recovered_path
                stored_name = recovered_name or resolved_path.name

        if resolved_path is None:
            self._clear_practiscore_source()
            return False

        display_name = stored_name or resolved_path.name
        changed = False
        if self.project.scoring.practiscore_source_path != str(resolved_path):
            self.project.scoring.practiscore_source_path = str(resolved_path)
            changed = True
        if self.project.scoring.practiscore_source_name != display_name:
            self.project.scoring.practiscore_source_name = display_name
            changed = True
        if self.project.scoring.imported_stage is not None:
            if self.project.scoring.imported_stage.source_path != str(resolved_path):
                self.project.scoring.imported_stage.source_path = str(resolved_path)
                changed = True
            if self.project.scoring.imported_stage.source_name != display_name:
                self.project.scoring.imported_stage.source_name = display_name
                changed = True

        try:
            options = describe_practiscore_file(resolved_path, source_name=display_name)
        except (OSError, ValueError):
            self._practiscore_source_path = resolved_path
            self._practiscore_source_name = display_name
            self._practiscore_options = None
            return changed or recovered_from_folder

        self._practiscore_source_path = resolved_path
        self._practiscore_source_name = display_name
        self._practiscore_options = options
        if self.project.scoring.imported_stage is None:
            try:
                self._import_practiscore_source(str(resolved_path), display_name, emit_change=emit_change)
                return True
            except ValueError:
                return changed or recovered_from_folder
        return changed or recovered_from_folder

    def _project_input_candidates(self) -> list[tuple[Path, VideoAsset]]:
        if self.project_path is None:
            return []

        candidates: list[tuple[Path, VideoAsset]] = []
        seen_paths: set[Path] = set()
        candidate_dirs = [self.project_path]
        input_dir = self.project_path / INPUT_DIRNAME
        if input_dir.is_dir():
            candidate_dirs.insert(0, input_dir)

        for directory in candidate_dirs:
            for path in directory.iterdir():
                if not path.is_file():
                    continue
                resolved_path = path.resolve()
                if resolved_path in seen_paths:
                    continue
                seen_paths.add(resolved_path)
                try:
                    candidates.append((resolved_path, probe_video(resolved_path)))
                except (MediaError, OSError, ValueError):
                    continue
        candidates.sort(key=lambda item: item[0].name.lower())
        return candidates

    def _recover_media_asset_from_project_folder(
        self,
        asset: VideoAsset,
        candidates: list[tuple[Path, VideoAsset]],
        used_paths: set[Path],
    ) -> VideoAsset | None:
        stored_path = asset.path.strip()
        if not stored_path:
            return None

        resolved_path = Path(stored_path)
        if resolved_path.exists():
            used_paths.add(resolved_path.resolve())
            return None

        scored_candidates: list[tuple[int, Path, VideoAsset]] = []
        for candidate_path, candidate_asset in candidates:
            if candidate_path in used_paths:
                continue
            score = _project_media_recovery_score(stored_path, asset, candidate_path, candidate_asset)
            if score <= 0:
                continue
            scored_candidates.append((score, candidate_path, candidate_asset))
        if not scored_candidates:
            return None

        scored_candidates.sort(key=lambda item: (-item[0], item[1].name.lower()))
        if len(scored_candidates) > 1 and scored_candidates[0][0] == scored_candidates[1][0]:
            return None

        best_score, best_path, best_asset = scored_candidates[0]
        if best_score < 350:
            return None
        used_paths.add(best_path)
        return best_asset

    def _restore_media_sources_from_project(self) -> bool:
        candidates = self._project_input_candidates()
        if not candidates:
            return False

        used_paths: set[Path] = set()
        changed = False

        recovered_primary = self._recover_media_asset_from_project_folder(self.project.primary_video, candidates, used_paths)
        if recovered_primary is not None:
            self.project.primary_video = recovered_primary
            changed = True

        for source in self.project.merge_sources:
            recovered_asset = self._recover_media_asset_from_project_folder(source.asset, candidates, used_paths)
            if recovered_asset is None:
                continue
            source.asset = recovered_asset
            changed = True

        if self.project.merge_sources:
            _sync_secondary_video_from_merge_sources(self.project)
        elif self.project.secondary_video is not None:
            recovered_secondary = self._recover_media_asset_from_project_folder(
                self.project.secondary_video,
                candidates,
                used_paths,
            )
            if recovered_secondary is not None:
                self.project.secondary_video = recovered_secondary
                changed = True

        return changed

    def _current_practiscore_selection_matches_source(self) -> bool:
        scoring = self.project.scoring
        options = self._practiscore_options
        if options is None:
            return False
        if not scoring.match_type or scoring.match_type != options.match_type:
            return False
        if scoring.stage_number is None or scoring.stage_number not in options.stage_numbers:
            return False
        competitor_name = scoring.competitor_name.strip()
        if not competitor_name:
            return False
        normalized_competitor_name = _normalize_name(competitor_name)
        matching_competitors = [
            option for option in options.competitors
            if _normalize_name(option.name) == normalized_competitor_name
            or _practiscore_name_matches(competitor_name, option.name)
        ]
        if not matching_competitors:
            return False
        if scoring.competitor_place is None and len(matching_competitors) > 1:
            return False
        if scoring.competitor_place is None:
            return True
        if any(option.place == scoring.competitor_place for option in matching_competitors):
            return True
        return len(matching_competitors) == 1

    def _can_reimport_practiscore_source(self) -> bool:
        return self._practiscore_source_path is not None and self._current_practiscore_selection_matches_source()

    def _import_practiscore_source(
        self,
        path: str,
        source_name: str | None = None,
        *,
        emit_change: bool = True,
    ) -> None:
        scoring = self.project.scoring
        try:
            resolved = infer_practiscore_context(
                path,
                match_type=scoring.match_type or None,
                stage_number=scoring.stage_number,
                competitor_name=scoring.competitor_name or None,
                competitor_place=scoring.competitor_place,
            )
        except ValueError:
            resolved = infer_practiscore_context(path)
        imported = import_practiscore_stage(
            path,
            match_type=resolved.match_type,
            stage_number=resolved.stage_number,
            competitor_name=resolved.competitor_name,
            competitor_place=resolved.competitor_place,
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
        imported_box = next(
            (box for box in self.project.overlay.text_boxes if box.source == "imported_summary"),
            None,
        )
        if imported_box is None:
            boxes = list(overlay_text_boxes_for_render(self.project.overlay))
            boxes.append(
                OverlayTextBox(
                    enabled=True,
                    lock_to_stack=False,
                    source="imported_summary",
                    quadrant="above_final",
                    x=None,
                    y=None,
                    background_color=self.project.overlay.custom_box_background_color,
                    text_color=self.project.overlay.custom_box_text_color,
                    opacity=self.project.overlay.custom_box_opacity,
                    width=0,
                    height=0,
                )
            )
            self.project.overlay.text_boxes = boxes
        else:
            imported_box.enabled = True
        sync_overlay_legacy_custom_box_fields(self.project.overlay)
        self.update_hit_factor()
        stage_label = imported.imported_stage.stage_name or f"Stage {imported.imported_stage.stage_number}"
        self._set_status(f"Imported PractiScore results for {stage_label}.")
        if emit_change:
            self.project.touch()
            self.project_changed.emit()

    def add_merge_source(self, path: str, source_name: str | None = None) -> None:
        path = self._stage_project_input_path(path, source_name=source_name)
        asset = probe_video(path)
        self.project.merge_sources.append(
            MergeSource(
                asset=asset,
                pip_size_percent=self.project.merge.pip_size_percent,
                pip_x=self.project.merge.pip_x,
                pip_y=self.project.merge.pip_y,
                sync_offset_ms=0,
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
            self.project.analysis.sync_offset_ms = self.project.merge_sources[0].sync_offset_ms if self.project.merge_sources else 0
        self._set_status("Removed merge media.")
        self.project.touch()
        self.project_changed.emit()

    def set_detection_threshold(self, value: float) -> None:
        self.set_shotml_settings({"detection_threshold": value}, rerun=True)

    def set_shotml_settings(
        self,
        updates: dict[str, object],
        *,
        rerun: bool = False,
        update_app_defaults: bool = False,
    ) -> None:
        settings = self.project.analysis.shotml_settings
        changed = False
        valid_fields = {item.name: item for item in fields(ShotMLSettings)}
        for key, raw_value in updates.items():
            field_info = valid_fields.get(str(key))
            if field_info is None:
                continue
            current_value = getattr(settings, field_info.name)
            try:
                if isinstance(current_value, bool):
                    next_value = bool(raw_value)
                elif isinstance(current_value, int) and not isinstance(current_value, bool):
                    next_value = int(raw_value)
                elif isinstance(current_value, float):
                    next_value = float(raw_value)
                else:
                    next_value = str(raw_value)
            except (TypeError, ValueError):
                continue
            if current_value != next_value:
                setattr(settings, field_info.name, next_value)
                changed = True

        self.project.analysis.detection_threshold = settings.detection_threshold
        if update_app_defaults:
            persisted_defaults = ShotMLSettings(**asdict(settings))
            persisted_defaults.detection_threshold = ShotMLSettings().detection_threshold
            self.settings.detection_threshold = persisted_defaults.detection_threshold
            self.settings.shotml_defaults = persisted_defaults
            save_settings(self.settings)
            self.settings_changed.emit()
        if rerun and self.project.primary_video.path:
            if changed:
                self.project.analysis.timing_change_proposals = []
            self.analyze_primary()
            if self.project.secondary_video is not None and not self.project.secondary_video.is_still_image:
                self.analyze_secondary()
            return
        if changed:
            self.project.analysis.timing_change_proposals = []
            self._set_status("Updated ShotML settings.")
        else:
            self._set_status("ShotML settings unchanged.")
        self.project.touch()
        self.project_changed.emit()

    def reset_shotml_settings(self) -> None:
        self.project.analysis.shotml_settings = ShotMLSettings()
        self.project.analysis.detection_threshold = self.project.analysis.shotml_settings.detection_threshold
        self.project.analysis.timing_change_proposals = []
        self.settings.detection_threshold = self.project.analysis.shotml_settings.detection_threshold
        self.settings.shotml_defaults = ShotMLSettings()
        save_settings(self.settings)
        self.settings_changed.emit()
        self._set_status("Reset ShotML settings to factory defaults.")
        self.project.touch()
        self.project_changed.emit()

    def rerun_shotml(self) -> None:
        if self.project.primary_video.path:
            self.analyze_primary()
            if self.project.secondary_video is not None and not self.project.secondary_video.is_still_image:
                self.analyze_secondary()
            return
        self.project.touch()
        self._set_status("ShotML settings saved.")
        self.project_changed.emit()

    def _review_suggestion_objects(self) -> list[TimingReviewSuggestion]:
        suggestions: list[TimingReviewSuggestion] = []
        for item in self.project.analysis.detection_review_suggestions:
            if not isinstance(item, dict):
                continue
            suggestions.append(
                TimingReviewSuggestion(
                    kind=str(item.get("kind", "")),
                    severity=str(item.get("severity", "review")),
                    message=str(item.get("message", "")),
                    suggested_action=str(item.get("suggested_action", "")),
                    shot_number=None if item.get("shot_number") in {None, ""} else int(item["shot_number"]),
                    shot_time_ms=None if item.get("shot_time_ms") in {None, ""} else int(item["shot_time_ms"]),
                    confidence=None if item.get("confidence") in {None, ""} else float(item["confidence"]),
                    support_confidence=None if item.get("support_confidence") in {None, ""} else float(item["support_confidence"]),
                    interval_ms=None if item.get("interval_ms") in {None, ""} else int(item["interval_ms"]),
                )
            )
        return suggestions

    def generate_timing_change_proposals(self) -> None:
        proposals = timing_change_proposals_from_review_suggestions(
            self.project.analysis.shots,
            self.project.analysis.beep_time_ms_primary,
            self._review_suggestion_objects(),
        )
        existing_restore_ids = {
            proposal.shot_id
            for proposal in self.project.analysis.timing_change_proposals
            if proposal.proposal_type == "restore_shot" and proposal.status == "pending"
        }
        for shot in self.project.analysis.shots:
            original = self._original_shot_state_by_id.get(shot.id)
            if original is None or original.time_ms == shot.time_ms or shot.id in existing_restore_ids:
                continue
            proposals.append(
                TimingChangeProposal(
                    proposal_type="restore_shot",
                    shot_id=shot.id,
                    shot_number=next(
                        (index + 1 for index, candidate in enumerate(sort_shots(self.project.analysis.shots)) if candidate.id == shot.id),
                        None,
                    ),
                    source_time_ms=shot.time_ms,
                    target_time_ms=original.time_ms,
                    message=f"Restore ShotML's original timestamp for this edited shot ({original.time_ms} ms).",
                    evidence={"original_source": original.source.value},
                )
            )
        self.project.analysis.timing_change_proposals = proposals
        self._set_status(f"Generated {len(proposals)} ShotML timing proposal{'s' if len(proposals) != 1 else ''}.")
        self.project.touch()
        self.project_changed.emit()

    def _pending_proposal(self, proposal_id: str) -> TimingChangeProposal:
        for proposal in self.project.analysis.timing_change_proposals:
            if proposal.id == proposal_id and proposal.status == "pending":
                return proposal
        raise ValueError("Pending proposal not found")

    def apply_timing_change_proposal(self, proposal_id: str) -> None:
        proposal = self._pending_proposal(proposal_id)
        proposal.status = "applied"
        if proposal.proposal_type == "move_beep":
            if proposal.target_time_ms is None:
                raise ValueError("Proposal target time is required")
            self.project.analysis.beep_time_ms_primary = max(0, int(proposal.target_time_ms))
        elif proposal.proposal_type == "move_shot":
            if proposal.shot_id is None or proposal.target_time_ms is None:
                raise ValueError("Proposal shot and target time are required")
            self.move_shot(proposal.shot_id, int(proposal.target_time_ms))
            return
        elif proposal.proposal_type in {"suppress_shot", "choose_close_pair_survivor"}:
            if proposal.shot_id is None:
                raise ValueError("Proposal shot is required")
            self.delete_shot(proposal.shot_id)
            return
        elif proposal.proposal_type == "restore_shot":
            if proposal.shot_id is None:
                raise ValueError("Proposal shot is required")
            self.restore_original_shot_timing(proposal.shot_id)
            proposal.status = "applied"
            return
        else:
            raise ValueError(f"Unsupported proposal type: {proposal.proposal_type}")
        normalize_project_timing_events(self.project)
        _revalidate_timing_ui_state(self.project)
        self.update_hit_factor()
        self._set_status("Applied ShotML timing proposal.")
        self.project.touch()
        self.project_changed.emit()

    def discard_timing_change_proposal(self, proposal_id: str) -> None:
        proposal = self._pending_proposal(proposal_id)
        proposal.status = "discarded"
        self._set_status("Discarded ShotML timing proposal.")
        self.project.touch()
        self.project_changed.emit()

    def set_beep_time(self, time_ms: int) -> None:
        self.project.analysis.beep_time_ms_primary = time_ms
        self.project.touch()
        self.project_changed.emit()

    def add_shot(self, time_ms: int) -> None:
        shot = ShotEvent(
            time_ms=time_ms,
            shotml_time_ms=time_ms,
            source=ShotSource.MANUAL,
            confidence=None,
            score=default_score_mark_for_ruleset(self.project.scoring.ruleset),
            user_added=True,
        )
        self.project.analysis.shots.append(shot)
        self.project.sort_shots()
        self._remember_original_shot(shot)
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def move_shot(self, shot_id: str, time_ms: int, *, preserve_following_splits: bool = False) -> None:
        if preserve_following_splits:
            shots = sort_shots(self.project.analysis.shots)
            shot_index = next((index for index, shot in enumerate(shots) if shot.id == shot_id), None)
            if shot_index is None:
                raise ValueError("Shot not found")
            shot = shots[shot_index]
            if shot.shotml_time_ms is None:
                shot.shotml_time_ms = shot.time_ms
            if shot.shotml_confidence is None:
                original = self._original_shot_state_by_id.get(shot.id)
                shot.shotml_confidence = original.confidence if original is not None else shot.confidence
            lower_bound_ms = (
                self.project.analysis.beep_time_ms_primary
                if shot_index == 0 and self.project.analysis.beep_time_ms_primary is not None
                else (shots[shot_index - 1].time_ms if shot_index > 0 else 0)
            )
            target_time_ms = max(lower_bound_ms, time_ms)
            delta_ms = target_time_ms - shot.time_ms
            if delta_ms:
                for shifted_shot in shots[shot_index:]:
                    if shifted_shot.shotml_time_ms is None:
                        shifted_shot.shotml_time_ms = shifted_shot.time_ms
                    if shifted_shot.shotml_confidence is None:
                        original = self._original_shot_state_by_id.get(shifted_shot.id)
                        shifted_shot.shotml_confidence = (
                            original.confidence if original is not None else shifted_shot.confidence
                        )
                    shifted_shot.time_ms = max(0, shifted_shot.time_ms + delta_ms)
        else:
            for shot in self.project.analysis.shots:
                if shot.id == shot_id:
                    if shot.shotml_time_ms is None:
                        shot.shotml_time_ms = shot.time_ms
                    if shot.shotml_confidence is None:
                        original = self._original_shot_state_by_id.get(shot.id)
                        shot.shotml_confidence = original.confidence if original is not None else shot.confidence
                    shot.time_ms = max(0, time_ms)
                    if shot.source == ShotSource.AUTO:
                        shot.source = ShotSource.MANUAL
                        shot.confidence = None
                    break
        self.project.sort_shots()
        normalize_project_timing_events(self.project)
        _revalidate_timing_ui_state(self.project)
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def delete_shot(self, shot_id: str) -> None:
        selection_context = (
            _shot_selection_context(self.project, shot_id, fallback_mode="index")
            if self.project.ui_state.selected_shot_id == shot_id
            else None
        )
        self.project.analysis.shots = [shot for shot in self.project.analysis.shots if shot.id != shot_id]
        self._forget_original_shot(shot_id)
        normalize_project_timing_events(self.project)
        _revalidate_timing_ui_state(self.project, selection_context)
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def nudge_shot(self, shot_id: str, delta_ms: int) -> None:
        for shot in self.project.analysis.shots:
            if shot.id == shot_id:
                self.move_shot(shot.id, shot.time_ms + delta_ms)
                return

    def select_shot(self, shot_id: str | None) -> None:
        if shot_id is not None and not any(shot.id == shot_id for shot in self.project.analysis.shots):
            shot_id = None
        self.project.ui_state.selected_shot_id = shot_id
        self.project_changed.emit()

    def set_ui_state(self, payload: dict[str, object]) -> None:
        ui_state = self.project.ui_state
        changed = False

        if "selected_shot_id" in payload:
            next_shot_id = None if payload.get("selected_shot_id") in {None, ""} else str(payload["selected_shot_id"])
            if next_shot_id is not None and not any(
                shot.id == next_shot_id for shot in self.project.analysis.shots
            ):
                next_shot_id = None
            if ui_state.selected_shot_id != next_shot_id:
                ui_state.selected_shot_id = next_shot_id
                changed = True
        if "timeline_zoom" in payload:
            next_zoom = max(1.0, min(200.0, float(payload["timeline_zoom"])))
            if ui_state.timeline_zoom != next_zoom:
                ui_state.timeline_zoom = next_zoom
                changed = True
        if "timeline_offset_ms" in payload:
            next_offset = max(0, int(payload["timeline_offset_ms"]))
            if ui_state.timeline_offset_ms != next_offset:
                ui_state.timeline_offset_ms = next_offset
                changed = True
        if "active_tool" in payload:
            next_active_tool = str(payload["active_tool"])
            if next_active_tool not in _VALID_BROWSER_UI_TOOLS:
                next_active_tool = "project"
            if ui_state.active_tool != next_active_tool:
                ui_state.active_tool = next_active_tool
                changed = True
        if "waveform_mode" in payload:
            next_waveform_mode = str(payload["waveform_mode"])
            if next_waveform_mode not in _VALID_WAVEFORM_MODES:
                next_waveform_mode = "select"
            if ui_state.waveform_mode != next_waveform_mode:
                ui_state.waveform_mode = next_waveform_mode
                changed = True
        if "waveform_expanded" in payload:
            next_waveform_expanded = bool(payload["waveform_expanded"])
            if ui_state.waveform_expanded != next_waveform_expanded:
                ui_state.waveform_expanded = next_waveform_expanded
                changed = True
            if next_waveform_expanded and ui_state.timing_expanded:
                ui_state.timing_expanded = False
                changed = True
        if "timing_expanded" in payload:
            next_timing_expanded = bool(payload["timing_expanded"])
            if ui_state.timing_expanded != next_timing_expanded:
                ui_state.timing_expanded = next_timing_expanded
                changed = True
            if next_timing_expanded and ui_state.waveform_expanded:
                ui_state.waveform_expanded = False
                changed = True
            if next_timing_expanded and ui_state.metrics_expanded:
                ui_state.metrics_expanded = False
                changed = True
        if "metrics_expanded" in payload:
            next_metrics_expanded = bool(payload["metrics_expanded"])
            if ui_state.metrics_expanded != next_metrics_expanded:
                ui_state.metrics_expanded = next_metrics_expanded
                changed = True
            if next_metrics_expanded and ui_state.waveform_expanded:
                ui_state.waveform_expanded = False
                changed = True
            if next_metrics_expanded and ui_state.timing_expanded:
                ui_state.timing_expanded = False
                changed = True
        if "layout_locked" in payload:
            next_layout_locked = bool(payload["layout_locked"])
            if ui_state.layout_locked != next_layout_locked:
                ui_state.layout_locked = next_layout_locked
                changed = True
        for field_name, minimum, maximum in (
            ("rail_width", 48, 72),
            ("inspector_width", 320, 4096),
            ("waveform_height", 112, 4096),
        ):
            if field_name not in payload:
                continue
            next_value = max(minimum, min(maximum, int(payload[field_name])))
            if getattr(ui_state, field_name) != next_value:
                setattr(ui_state, field_name, next_value)
                changed = True
        if "scoring_shot_expansion" in payload:
            next_expansion: dict[str, bool] = {}
            raw_expansion = payload.get("scoring_shot_expansion")
            if isinstance(raw_expansion, dict):
                for key, value in raw_expansion.items():
                    clean_key = str(key).strip()
                    if clean_key:
                        next_expansion[clean_key] = bool(value)
            if ui_state.scoring_shot_expansion != next_expansion:
                ui_state.scoring_shot_expansion = next_expansion
                changed = True
        if "waveform_shot_amplitudes" in payload:
            next_amplitudes: dict[str, float] = {}
            raw_amplitudes = payload.get("waveform_shot_amplitudes")
            if isinstance(raw_amplitudes, dict):
                for key, value in raw_amplitudes.items():
                    clean_key = str(key).strip()
                    if not clean_key:
                        continue
                    try:
                        numeric = float(value)
                    except (TypeError, ValueError):
                        continue
                    next_amplitudes[clean_key] = max(0.25, min(12.0, numeric))
            if ui_state.waveform_shot_amplitudes != next_amplitudes:
                ui_state.waveform_shot_amplitudes = next_amplitudes
                changed = True
        if "timing_edit_shot_ids" in payload:
            next_timing_edit_ids: list[str] = []
            raw_timing_edit_ids = payload.get("timing_edit_shot_ids")
            if isinstance(raw_timing_edit_ids, list):
                valid_shot_ids = {shot.id for shot in self.project.analysis.shots}
                for value in raw_timing_edit_ids:
                    clean_value = str(value).strip()
                    if clean_value and clean_value in valid_shot_ids:
                        next_timing_edit_ids.append(clean_value)
            if ui_state.timing_edit_shot_ids != next_timing_edit_ids:
                ui_state.timing_edit_shot_ids = next_timing_edit_ids
                changed = True
        if "timing_column_widths" in payload:
            next_timing_column_widths: dict[str, float] = {}
            raw_timing_column_widths = payload.get("timing_column_widths")
            if isinstance(raw_timing_column_widths, dict):
                minimums = {
                    "lock": 60,
                    "segment": 104,
                    "split": 92,
                    "total": 88,
                    "action": 140,
                    "score": 68,
                    "confidence": 92,
                    "adjustment": 112,
                    "final": 88,
                    "delete": 76,
                    "restore": 88,
                }
                for key, value in raw_timing_column_widths.items():
                    clean_key = str(key).strip()
                    if clean_key not in minimums:
                        continue
                    try:
                        numeric = float(value)
                    except (TypeError, ValueError):
                        continue
                    next_timing_column_widths[clean_key] = max(minimums[clean_key], round(numeric))
            if ui_state.timing_column_widths != next_timing_column_widths:
                ui_state.timing_column_widths = next_timing_column_widths
                changed = True
        if "review_text_box_expansion" in payload:
            next_expansion: dict[str, bool] = {}
            raw_expansion = payload.get("review_text_box_expansion")
            if isinstance(raw_expansion, dict):
                valid_box_ids = {box.id for box in self.project.overlay.text_boxes}
                for key, value in raw_expansion.items():
                    clean_key = str(key).strip()
                    if clean_key and clean_key in valid_box_ids:
                        next_expansion[clean_key] = bool(value)
            if ui_state.review_text_box_expansion != next_expansion:
                ui_state.review_text_box_expansion = next_expansion
                changed = True
        if "popup_bubble_expansion" in payload:
            next_expansion: dict[str, bool] = {}
            raw_expansion = payload.get("popup_bubble_expansion")
            if isinstance(raw_expansion, dict):
                valid_bubble_ids = {bubble.id for bubble in self.project.popups}
                for key, value in raw_expansion.items():
                    clean_key = str(key).strip()
                    if clean_key and clean_key in valid_bubble_ids:
                        next_expansion[clean_key] = bool(value)
            if ui_state.popup_bubble_expansion != next_expansion:
                ui_state.popup_bubble_expansion = next_expansion
                changed = True
        if "merge_source_expansion" in payload:
            next_expansion: dict[str, bool] = {}
            raw_expansion = payload.get("merge_source_expansion")
            if isinstance(raw_expansion, dict):
                valid_source_ids = {source.id for source in self.project.merge_sources}
                valid_source_ids.add("pip-defaults")
                for key, value in raw_expansion.items():
                    clean_key = str(key).strip()
                    if clean_key and clean_key in valid_source_ids:
                        next_expansion[clean_key] = bool(value)
            if ui_state.merge_source_expansion != next_expansion:
                ui_state.merge_source_expansion = next_expansion
                changed = True
        if "shotml_section_expansion" in payload:
            next_expansion: dict[str, bool] = {}
            raw_expansion = payload.get("shotml_section_expansion")
            if isinstance(raw_expansion, dict):
                valid_section_ids = {
                    "threshold",
                    "beep_detection",
                    "shot_candidate_detection",
                    "shot_refinement",
                    "false_positive_suppression",
                    "confidence_review",
                    "timing_changer",
                    "advanced_runtime",
                }
                for key, value in raw_expansion.items():
                    clean_key = str(key).strip()
                    if clean_key and clean_key in valid_section_ids:
                        next_expansion[clean_key] = bool(value)
            if ui_state.shotml_section_expansion != next_expansion:
                ui_state.shotml_section_expansion = next_expansion
                changed = True

        if changed:
            self.project.touch()
            self.project_changed.emit()

    def assign_score(
        self,
        shot_id: str,
        letter: ScoreLetter | None = None,
        penalty_counts: dict[str, float] | None = None,
    ) -> None:
        normalized_penalty_counts = None if penalty_counts is None else {
            str(key): max(0.0, float(value))
            for key, value in penalty_counts.items()
            if max(0.0, float(value)) > 0
        }
        for shot in self.project.analysis.shots:
            if shot.id == shot_id:
                if shot.score is None:
                    shot.score = default_score_mark_for_ruleset(self.project.scoring.ruleset)
                elif letter is not None:
                    shot.score.letter = letter
                if normalized_penalty_counts is not None:
                    shot.score.penalty_counts = normalized_penalty_counts
                break
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def restore_original_shot_timing(self, shot_id: str, *, preserve_following_splits: bool = False) -> None:
        original = self._original_shot_state_by_id.get(shot_id)
        if original is None:
            raise ValueError("Original split not found")
        shots = sort_shots(self.project.analysis.shots)
        for shot_index, shot in enumerate(shots):
            if shot.id != shot_id:
                continue
            restored_time_ms = max(0, shot.shotml_time_ms if shot.shotml_time_ms is not None else original.time_ms)
            if preserve_following_splits:
                delta_ms = restored_time_ms - shot.time_ms
                if delta_ms:
                    for shifted_shot in shots[shot_index:]:
                        if shifted_shot.shotml_time_ms is None:
                            shifted_shot.shotml_time_ms = shifted_shot.time_ms
                        if shifted_shot.shotml_confidence is None:
                            original_shifted = self._original_shot_state_by_id.get(shifted_shot.id)
                            shifted_shot.shotml_confidence = (
                                original_shifted.confidence if original_shifted is not None else shifted_shot.confidence
                            )
                        shifted_shot.time_ms = max(0, shifted_shot.time_ms + delta_ms)
            else:
                shot.time_ms = restored_time_ms
            shot.source = original.source
            shot.confidence = shot.shotml_confidence if shot.shotml_confidence is not None else original.confidence
            self.project.sort_shots()
            self.update_hit_factor()
            self._set_status("Restored original split.")
            self.project.touch()
            self.project_changed.emit()
            return
        raise ValueError("Shot not found")

    def restore_original_shot_score(self, shot_id: str) -> None:
        original = self._original_shot_state_by_id.get(shot_id)
        if original is None:
            raise ValueError("Original score not found")
        for shot in self.project.analysis.shots:
            if shot.id != shot_id:
                continue
            shot.score = (
                default_score_mark_for_ruleset(self.project.scoring.ruleset)
                if original.score is None
                else deepcopy(original.score)
            )
            self.update_hit_factor()
            self._set_status("Restored original score.")
            self.project.touch()
            self.project_changed.emit()
            return
        raise ValueError("Shot not found")

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
            "above_final",
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
        valid_custom_box_quadrants = {*valid_quadrants, "custom"}
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
        for field_name in (
            "show_timer",
            "show_draw",
            "show_shots",
            "show_score",
            "timer_lock_to_stack",
            "draw_lock_to_stack",
            "score_lock_to_stack",
        ):
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
            overlay.custom_box_quadrant = value if value in valid_custom_box_quadrants else "top_right"
        if "custom_box_x" in payload:
            value = payload["custom_box_x"]
            overlay.custom_box_x = None if value in {"", None} else max(0.0, min(1.0, float(value)))
        if "custom_box_y" in payload:
            value = payload["custom_box_y"]
            overlay.custom_box_y = None if value in {"", None} else max(0.0, min(1.0, float(value)))
        if overlay.custom_box_x is not None or overlay.custom_box_y is not None:
            overlay.custom_box_quadrant = "custom"
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
        if "text_boxes" in payload:
            parsed_boxes: list[OverlayTextBox] = []
            for item in payload.get("text_boxes", []):
                if not isinstance(item, dict):
                    continue
                source = str(item.get("source", "manual"))
                quadrant = str(item.get("quadrant", "top_right"))
                box = OverlayTextBox(
                    id=str(item.get("id") or OverlayTextBox().id),
                    enabled=bool(item.get("enabled", False)),
                    lock_to_stack=bool(item.get("lock_to_stack", False)),
                    source=source if source in valid_custom_box_modes else "manual",
                    text=str(item.get("text", ""))[:500],
                    quadrant=quadrant if quadrant in valid_custom_box_quadrants else "top_right",
                    x=None if item.get("x") in {None, ""} else max(0.0, min(1.0, float(item["x"]))),
                    y=None if item.get("y") in {None, ""} else max(0.0, min(1.0, float(item["y"]))),
                    background_color=str(item.get("background_color", overlay.custom_box_background_color)),
                    text_color=str(item.get("text_color", overlay.custom_box_text_color)),
                    opacity=max(0.0, min(1.0, float(item.get("opacity", overlay.custom_box_opacity)))),
                    width=max(0, int(item.get("width", 0))),
                    height=max(0, int(item.get("height", 0))),
                )
                if box.x is not None or box.y is not None:
                    box.quadrant = "custom"
                if box.quadrant == "custom":
                    if box.x is None:
                        box.x = 0.5
                    if box.y is None:
                        box.y = 0.5
                parsed_boxes.append(box)
            overlay.text_boxes = parsed_boxes
            sync_overlay_legacy_custom_box_fields(overlay)
        else:
            legacy_box = legacy_custom_box_as_text_box(overlay)
            overlay.text_boxes = [] if legacy_box is None else [legacy_box]
        self.project.touch()
        self.project_changed.emit()

    def set_popups(self, payload: dict[str, object]) -> None:
        parsed_popups: list[PopupBubble] = []
        for item in payload.get("popups", []):
            if not isinstance(item, dict):
                continue
            parsed_popups.append(_popup_bubble_from_dict(item))
        self.project.popups = parsed_popups
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

    def set_scoring_color(self, score_key: str, color: str) -> None:
        normalized_key = str(score_key).strip()
        if not normalized_key:
            raise ValueError("score color key is required")
        if "|" in normalized_key:
            raise ValueError("score color keys must be individual tokens")
        self.project.overlay.scoring_colors[normalized_key] = color
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
        self.project.merge.pip_size_percent = max(1, min(95, int(percent)))
        self.project.touch()
        self.project_changed.emit()

    def set_pip_position(self, pip_x: float | None = None, pip_y: float | None = None) -> None:
        if pip_x is not None:
            self.project.merge.pip_x = max(0.0, min(1.0, float(pip_x)))
        if pip_y is not None:
            self.project.merge.pip_y = max(0.0, min(1.0, float(pip_y)))
        self.project.touch()
        self.project_changed.emit()

    def set_merge_source_position(
        self,
        source_id: str,
        pip_size_percent: int | None = None,
        pip_x: float | None = None,
        pip_y: float | None = None,
        opacity: float | None = None,
    ) -> None:
        for source in self.project.merge_sources:
            if source.id != source_id:
                continue
            if pip_size_percent is not None:
                source.pip_size_percent = max(1, min(95, int(pip_size_percent)))
            if pip_x is not None:
                source.pip_x = max(0.0, min(1.0, float(pip_x)))
            if pip_y is not None:
                source.pip_y = max(0.0, min(1.0, float(pip_y)))
            if opacity is not None:
                source.opacity = max(0.0, min(1.0, float(opacity)))
            self.project.touch()
            self.project_changed.emit()
            return
        raise ValueError("Merge source not found")

    def set_merge_source_sync_offset(self, source_id: str, offset_ms: int) -> None:
        for index, source in enumerate(self.project.merge_sources):
            if source.id != source_id:
                continue
            source.sync_offset_ms = int(offset_ms)
            if index == 0:
                self.project.analysis.sync_offset_ms = source.sync_offset_ms
            self._set_status(f"Adjusted merge source sync to {source.sync_offset_ms} ms.")
            self.project.touch()
            self.project_changed.emit()
            return
        raise ValueError("Merge source not found")

    def adjust_merge_source_sync_offset(self, source_id: str, delta_ms: int) -> None:
        for source in self.project.merge_sources:
            if source.id == source_id:
                self.set_merge_source_sync_offset(source_id, source.sync_offset_ms + int(delta_ms))
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
        event = TimingEvent(
            kind=kind,
            label=event_label,
            after_shot_id=after_shot_id,
            before_shot_id=before_shot_id,
            note=note,
        )
        normalized_event = normalized_timing_event_for_shots(
            event,
            sort_shots(self.project.analysis.shots),
        )
        if normalized_event is None:
            raise ValueError("Timing event anchor is invalid")
        self.project.analysis.events.append(normalized_event)
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
        manual_override_keys = {
            "quality",
            "aspect_ratio",
            "crop_center_x",
            "crop_center_y",
            "target_width",
            "target_height",
            "frame_rate",
            "video_codec",
            "video_bitrate_mbps",
            "audio_codec",
            "audio_sample_rate",
            "audio_bitrate_kbps",
            "color_space",
            "two_pass",
            "ffmpeg_preset",
        }
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
        if "output_path" in payload:
            next_output_path = str(payload["output_path"]).strip()
            export.output_path = None if not next_output_path else next_output_path
        if manual_override_keys.intersection(payload):
            export.preset = ExportPreset.CUSTOM
        self.project.touch()
        self.project_changed.emit()

    def adjust_sync_offset(self, delta_ms: int) -> None:
        self.project.analysis.sync_offset_ms += delta_ms
        if self.project.merge_sources:
            self.project.merge_sources[0].sync_offset_ms = self.project.analysis.sync_offset_ms
        self._set_status(f"Adjusted sync offset to {self.project.analysis.sync_offset_ms} ms.")
        self.project.touch()
        self.project_changed.emit()

    def set_sync_offset(self, offset_ms: int) -> None:
        self.project.analysis.sync_offset_ms = offset_ms
        if self.project.merge_sources:
            self.project.merge_sources[0].sync_offset_ms = self.project.analysis.sync_offset_ms
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
        if self.project.merge_sources:
            self.project.merge_sources[0].sync_offset_ms = self.project.analysis.sync_offset_ms
        self._set_status("Swapped primary and secondary videos.")
        self.project.touch()
        self.project_changed.emit()

    def save_project(self, path: str | None = None) -> None:
        previous_project_path = self.project_path
        target_path = Path(path) if path else self.project_path
        if target_path is None:
            raise ValueError("Project path is required")
        self.project.touch()
        self.project_path = ensure_project_suffix(target_path)
        self._ensure_project_output_path(previous_project_path=previous_project_path)
        save_project(self.project, self.project_path)
        self._restore_practiscore_source_from_project()
        self._saved_snapshot = project_to_dict(self.project)
        self._remember_original_shots()
        self._remember_project(self.project_path)
        self._set_status(f"Project folder ready at {self.project_path}.")
        self.project_path_changed.emit(str(self.project_path))
        self.project_changed.emit()

    def open_project(self, path: str) -> None:
        self.project = load_project(path)
        self.project_path = ensure_project_suffix(path)
        self._ensure_project_output_path()
        loaded_snapshot = project_to_dict(self.project)
        recovered_media = self._restore_media_sources_from_project()
        recovered_practiscore = self._restore_practiscore_source_from_project(emit_change=False)
        if recovered_media or recovered_practiscore:
            self.project.touch()
        self._saved_snapshot = loaded_snapshot if (recovered_media or recovered_practiscore) else project_to_dict(self.project)
        self._remember_original_shots()
        self._remember_project(self.project_path)
        if recovered_media and recovered_practiscore and self._practiscore_source_name:
            self._set_status(
                f"Opened project folder {self.project_path} and restored renamed project media and PractiScore from {self._practiscore_source_name}."
            )
        elif recovered_media:
            self._set_status(f"Opened project folder {self.project_path} and restored renamed project media.")
        elif recovered_practiscore and self._practiscore_source_name:
            self._set_status(
                f"Opened project folder {self.project_path} and restored PractiScore from {self._practiscore_source_name}."
            )
        else:
            self._set_status(f"Opened project folder {self.project_path}.")
        self.project_path_changed.emit(str(self.project_path))
        self.project_changed.emit()

    def delete_current_project(self) -> None:
        if self.project_path is None:
            return
        delete_project(self.project_path)
        self.new_project()
        self._set_status("Deleted the saved project folder.")

    def restore_defaults(self) -> None:
        self.settings = AppSettings()
        save_settings(self.settings)
        self.project.analysis.shotml_settings = ShotMLSettings(**asdict(self.settings.shotml_defaults))
        self.project.analysis.detection_threshold = self.project.analysis.shotml_settings.detection_threshold
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

    def _remember_original_shots(self) -> None:
        self._original_shot_state_by_id = {
            shot.id: _OriginalShotState(
                time_ms=shot.shotml_time_ms if shot.shotml_time_ms is not None else shot.time_ms,
                source=shot.source,
                confidence=shot.shotml_confidence if shot.shotml_confidence is not None else shot.confidence,
                score=None if shot.score is None else deepcopy(shot.score),
            )
            for shot in self.project.analysis.shots
        }

    def _remember_original_shot(self, shot: ShotEvent) -> None:
        self._original_shot_state_by_id[shot.id] = _OriginalShotState(
            time_ms=shot.shotml_time_ms if shot.shotml_time_ms is not None else shot.time_ms,
            source=shot.source,
            confidence=shot.shotml_confidence if shot.shotml_confidence is not None else shot.confidence,
            score=None if shot.score is None else deepcopy(shot.score),
        )

    def _forget_original_shot(self, shot_id: str) -> None:
        self._original_shot_state_by_id.pop(shot_id, None)

    def _remember_project(self, path: Path) -> None:
        entries = [str(path), *[item for item in self.settings.recent_projects if item != str(path)]]
        next_entries = entries[:10]
        if self.settings.recent_projects == next_entries:
            return
        self.settings.recent_projects = next_entries
        save_settings(self.settings)
        self.settings_changed.emit()

    def _autosave_project_if_needed(self) -> None:
        if self._autosave_in_progress or self.project_path is None:
            return
        current_snapshot = project_to_dict(self.project)
        if current_snapshot == self._saved_snapshot:
            return
        try:
            self._autosave_in_progress = True
            save_project(self.project, self.project_path)
            if self.project.scoring.practiscore_source_path:
                self._restore_practiscore_source_from_project()
            self._saved_snapshot = project_to_dict(self.project)
            self._remember_project(self.project_path)
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Project autosave failed: {exc}")
        finally:
            self._autosave_in_progress = False

    def autosave_project_if_needed(self) -> None:
        self._autosave_project_if_needed()

    def _stage_project_input_path(self, path: str, source_name: str | None = None) -> str:
        if self.project_path is None:
            return path
        return copy_path_to_project_subdir(
            self.project_path,
            path,
            INPUT_DIRNAME,
            preferred_name=source_name,
        )

    def _stage_practiscore_source_path(self, path: str, source_name: str | None = None) -> str:
        if self.project_path is None:
            return path
        return copy_path_to_project_subdir(
            self.project_path,
            path,
            PRACTISCORE_DIRNAME,
            preferred_name=source_name,
        )

    def project_folder_has_project_file(self, path: str | Path) -> bool:
        return project_has_metadata(normalize_project_path(path))

    def normalize_project_folder_path(self, path: str | Path) -> Path:
        return normalize_project_path(path)

    def _new_project_with_settings_defaults(self) -> Project:
        project = Project()
        project.analysis.shotml_settings = ShotMLSettings(**asdict(self.settings.shotml_defaults))
        project.analysis.detection_threshold = project.analysis.shotml_settings.detection_threshold
        project.overlay.position = self.settings.overlay_position
        project.merge.layout = self.settings.merge_layout
        project.merge.pip_size = self.settings.pip_size
        project.merge.pip_size_percent = _pip_size_percent_from_enum(self.settings.pip_size)
        project.export.quality = self.settings.export_quality
        project.overlay.badge_size = self.settings.badge_size
        project.overlay.font_size = _badge_font_size_from_enum(self.settings.badge_size)
        return project

    def _ensure_project_output_path(self, previous_project_path: Path | None = None) -> None:
        if self.project_path is None:
            return
        current_output_path = str(self.project.export.output_path or "").strip()
        project_output_path = str(default_project_output_path(self.project_path))
        previous_output_path = (
            str(default_project_output_path(previous_project_path))
            if previous_project_path is not None
            else ""
        )
        if not current_output_path or (previous_output_path and current_output_path == previous_output_path):
            self.project.export.output_path = project_output_path

    def _set_status(self, message: str) -> None:
        self.status_message = message
        self.status_changed.emit(message)
