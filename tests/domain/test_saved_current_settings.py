from __future__ import annotations

from pathlib import Path

from splitshot.config import AppSettings
from splitshot.domain.models import (
    AspectRatio,
    ExportFrameRate,
    MergeLayout,
    OverlayTextBox,
    VideoAsset,
)
from splitshot.ui.controller import ProjectController


def _assert_saved_current_settings(controller: ProjectController, intro_path: str) -> None:
    project = controller.project
    assert project.overlay.style_type == "rounded"
    assert project.overlay.spacing == 17
    assert project.overlay.show_draw is False
    assert project.overlay.font_size == 31
    assert project.overlay.text_boxes[0].text == "Saved review box"
    assert project.merge.layout == MergeLayout.PIP
    assert project.merge.primary_is_left_or_top is False
    assert project.export.aspect_ratio == AspectRatio.PORTRAIT
    assert project.export.target_width == 1080
    assert project.export.target_height == 1920
    assert project.export.frame_rate == ExportFrameRate.FPS_60
    assert project.export.video_bitrate_mbps == 22.5
    assert project.export.audio_sample_rate == 44100
    assert project.export.audio_bitrate_kbps == 192
    assert project.export.multi_track is True
    assert project.export.output_path is None
    assert project.export.last_log == ""
    assert project.export.last_error is None
    assert project.popup_template.font_size == 26
    assert project.popup_template.background_color == "#123456"
    assert project.analysis.shotml_settings.min_shot_interval_ms == 175
    assert project.analysis.shotml_settings.sound_profile_distance_limit == 3.25
    assert project.queue_settings.fade_in_s == 0.8
    assert project.queue_settings.fade_out_s == 1.2
    assert project.queue_settings.intro_path == intro_path
    assert project.queue_settings.include_intro is True
    assert project.combined_export_settings.separator_duration_s == 1.75
    assert project.intro_clip.fade_in_s == 0.6
    assert project.intro_clip.fade_out_s == 0.9
    assert project.intro_clip.asset.path == intro_path
    assert project.intro_clip.overlay.text_boxes[0].text == "Saved intro box"
    assert project.outro_clip.fade_in_s == 1.1
    assert project.outro_clip.fade_out_s == 1.4


def test_save_current_settings_captures_all_persistent_values_across_projects_and_reload(
    tmp_path,
) -> None:
    controller = ProjectController()
    project = controller.project
    intro_path = str(tmp_path / "default-intro.mp4")
    Path(intro_path).write_bytes(b"default intro")
    project.overlay.style_type = "rounded"
    project.overlay.spacing = 17
    project.overlay.show_draw = False
    project.overlay.font_size = 31
    project.overlay.text_boxes = [OverlayTextBox(text="Saved review box")]
    project.merge.layout = MergeLayout.PIP
    project.merge.primary_is_left_or_top = False
    project.export.aspect_ratio = AspectRatio.PORTRAIT
    project.export.target_width = 1080
    project.export.target_height = 1920
    project.export.frame_rate = ExportFrameRate.FPS_60
    project.export.video_bitrate_mbps = 22.5
    project.export.audio_sample_rate = 44100
    project.export.audio_bitrate_kbps = 192
    project.export.multi_track = True
    project.export.output_path = "/runtime-only/output.mp4"
    project.export.last_log = "runtime log"
    project.export.last_error = "runtime error"
    project.popup_template.font_size = 26
    project.popup_template.background_color = "#123456"
    project.analysis.shotml_settings.min_shot_interval_ms = 175
    project.analysis.shotml_settings.sound_profile_distance_limit = 3.25
    project.queue_settings.fade_in_s = 0.8
    project.queue_settings.fade_out_s = 1.2
    project.queue_settings.intro_path = intro_path
    project.queue_settings.include_intro = True
    project.combined_export_settings.separator_duration_s = 1.75
    project.intro_clip.fade_in_s = 0.6
    project.intro_clip.fade_out_s = 0.9
    project.intro_clip.asset = VideoAsset(path=intro_path, duration_ms=1500, width=1920, height=1080)
    project.intro_clip.overlay.text_boxes = [OverlayTextBox(text="Saved intro box")]
    project.outro_clip.fade_in_s = 1.1
    project.outro_clip.fade_out_s = 1.4
    project.trim_keep_before_beep_s = 1.25
    project.trim_keep_after_last_shot_s = 2.75
    project.ui_state.timing_enabled = False
    project.scoring.enabled = False

    controller.set_settings_defaults({}, capture_current_project=True)
    cached_intro_path = str(
        controller.settings.project_defaults["intro_clip_settings"]["asset"]["path"]
    )
    assert Path(cached_intro_path).parent.name == "default-media"
    assert Path(cached_intro_path).is_file()

    controller.new_project()
    _assert_saved_current_settings(controller, cached_intro_path)

    reloaded_controller = ProjectController()
    _assert_saved_current_settings(reloaded_controller, cached_intro_path)
    assert reloaded_controller.settings.project_defaults["schema_version"] == 1
    assert reloaded_controller.project.trim_keep_before_beep_s == 1.25
    assert reloaded_controller.project.trim_keep_after_last_shot_s == 2.75
    assert reloaded_controller.project.ui_state.timing_enabled is False
    assert reloaded_controller.project.scoring.enabled is False
    serialized = str(reloaded_controller.settings.project_defaults)
    assert cached_intro_path in serialized


def test_save_current_export_section_does_not_replace_other_saved_sections() -> None:
    controller = ProjectController()
    controller.project.overlay.style_type = "rounded"
    controller.set_settings_defaults({}, section="overlay", capture_current_project=True)

    controller.project.overlay.style_type = "square"
    controller.project.export.target_width = 720
    controller.set_settings_defaults({}, section="export", capture_current_project=True)

    reloaded_controller = ProjectController()
    assert reloaded_controller.project.overlay.style_type == "rounded"
    assert reloaded_controller.project.export.target_width == 720


def test_saved_intro_outro_default_media_is_copied_into_new_project(
    tmp_path, monkeypatch
) -> None:
    intro_source = tmp_path / "shared-intro.mp4"
    outro_source = tmp_path / "shared-outro.mp4"
    intro_source.write_bytes(b"intro")
    outro_source.write_bytes(b"outro")
    controller = ProjectController()
    controller.project.intro_clip.asset = VideoAsset(path=str(intro_source), duration_ms=1000)
    controller.project.outro_clip.asset = VideoAsset(path=str(outro_source), duration_ms=1200)
    controller.project.queue_settings.intro_path = str(intro_source)
    controller.project.queue_settings.outro_path = str(outro_source)
    controller.project.queue_settings.include_intro = True
    controller.project.queue_settings.include_outro = True
    controller.set_settings_defaults({}, capture_current_project=True)

    controller.new_project()
    monkeypatch.setattr(
        "splitshot.ui.controller.probe_video",
        lambda path: VideoAsset(path=str(path), duration_ms=1000),
    )
    project_path = tmp_path / "next-match"
    controller.save_project(str(project_path))

    intro_path = controller.project.intro_clip.asset.path
    outro_path = controller.project.outro_clip.asset.path
    assert Path(intro_path).parent.name == "IntroOutro"
    assert Path(outro_path).parent.name == "IntroOutro"
    assert Path(intro_path).read_bytes() == b"intro"
    assert Path(outro_path).read_bytes() == b"outro"
    assert controller.project.queue_settings.intro_path == intro_path
    assert controller.project.queue_settings.outro_path == outro_path


def test_legacy_compose_defaults_migrate_to_path_free_slot_templates() -> None:
    settings = AppSettings.from_dict(
        {
            "merge_source_defaults": [
                {
                    "asset": {"path": "/legacy/camera.mp4"},
                    "id": "legacy-source",
                    "pip_size_percent": 42,
                    "pip_x": 0.2,
                    "pip_y": 0.8,
                    "opacity": 0.75,
                    "sync_offset_ms": 900,
                }
            ]
        }
    )

    assert settings.project_defaults["schema_version"] == 1
    assert settings.project_defaults["compose_source_templates"] == [
        {"pip_size_percent": 42, "pip_x": 0.2, "pip_y": 0.8, "opacity": 0.75}
    ]
