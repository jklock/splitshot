from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog

from splitshot.domain.models import ScoreLetter
from splitshot.ui.controller import ProjectController
from splitshot.ui.main_window import MainWindow
from splitshot.ui.widgets.dashboard import SplitCard


def test_main_window_switches_from_media_selection_to_review_after_primary_ingest(qtbot, synthetic_video_factory) -> None:
    controller = ProjectController()
    window = MainWindow(controller)
    qtbot.addWidget(window)
    window.show()

    assert window.center_stack.currentIndex() == 0

    video_path = synthetic_video_factory()
    window._ingest_primary_video(str(video_path))

    qtbot.waitUntil(lambda: window.center_stack.currentIndex() == 1)
    assert window.center_stack.currentIndex() == 1
    assert len(controller.project.analysis.shots) == 3
    assert window.draw_card.value_label.text() != "--.--"
    card_ids = {card.shot_id for card in window.findChildren(SplitCard)}
    assert len(card_ids) == 3
    cards = sorted(window.findChildren(SplitCard), key=lambda card: card.data.title)
    first_shot_card = next(card for card in cards if card.data.title == "Shot 1")
    assert "Draw" in first_shot_card.data.meta
    assert "ShotML" in first_shot_card.data.meta


def test_split_card_click_selects_shot_in_loaded_review(qtbot, synthetic_video_factory) -> None:
    controller = ProjectController()
    video_path = synthetic_video_factory()
    controller.ingest_primary_video(str(video_path))

    window = MainWindow(controller)
    qtbot.addWidget(window)
    window.show()
    window.refresh_ui()

    cards = [card for card in window.findChildren(SplitCard) if card.isVisible()]
    assert len(cards) == 3

    qtbot.mouseClick(cards[1], Qt.LeftButton)

    assert controller.project.ui_state.selected_shot_id == cards[1].shot_id
    assert "Selected shot at" in window.scoring_target_label.text()


def test_main_window_opens_project_bundle_via_file_picker(qtbot, monkeypatch, tmp_path) -> None:
    controller = ProjectController()
    window = MainWindow(controller)
    qtbot.addWidget(window)
    window.show()

    project_dir = tmp_path / "review.ssproj"
    project_dir.mkdir()
    project_file = project_dir / "project.json"
    opened_paths: list[str] = []
    selected_sections: list[str] = []

    monkeypatch.setattr(window, "_confirm_unsaved", lambda: True)
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(project_file), "SplitShot project file (project.json)"),
    )
    monkeypatch.setattr(controller, "open_project", lambda path: opened_paths.append(path))
    monkeypatch.setattr(window, "_select_section", lambda section_id: selected_sections.append(section_id))

    window._open_project()

    assert opened_paths == [str(project_file)]
    assert selected_sections == ["manage"]


def test_main_window_surfaces_runtime_validation_checks(qtbot, monkeypatch) -> None:
    controller = ProjectController()
    monkeypatch.setattr("splitshot.ui.main_window.resolve_media_binary", lambda tool: f"/opt/{tool}")

    window = MainWindow(controller)
    qtbot.addWidget(window)
    window.show()
    window.refresh_ui()

    assert window.section_buttons["upload"].text() == "Media"
    assert window.validation_ffmpeg_label.text() == "/opt/ffmpeg"
    assert window.validation_ffprobe_label.text() == "/opt/ffprobe"
    assert window.validation_browser_assets_label.text() == "Ready"
    assert "No local media selected yet." == window.validation_media_label.text()


def test_main_window_uses_audio_outputs_for_both_video_players(qtbot) -> None:
    controller = ProjectController()
    window = MainWindow(controller)
    qtbot.addWidget(window)

    assert window.primary_player.audioOutput() is window.primary_audio
    assert window.secondary_player.audioOutput() is window.secondary_audio


def test_main_window_score_picker_defaults_to_active_preset(qtbot) -> None:
    controller = ProjectController()
    controller.set_scoring_preset("idpa_time_plus")
    controller.add_shot(1200)

    window = MainWindow(controller)
    qtbot.addWidget(window)
    window.refresh_ui()

    assert window.score_letter.currentData() == ScoreLetter.DOWN_0
