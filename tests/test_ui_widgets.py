from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from splitshot.domain.models import AspectRatio, Project, ShotEvent
from splitshot.ui.widgets.overlay_preview import OverlayPreview
from splitshot.ui.widgets.waveform_editor import WaveformEditor, WaveformState


def test_waveform_editor_adds_and_deletes_markers(qtbot) -> None:
    editor = WaveformEditor()
    editor.resize(400, 180)
    editor.set_state(
        WaveformState(
            duration_ms=1000,
            waveform=[0.2] * 512,
            shots=[ShotEvent(id="shot-1", time_ms=250)],
            beep_time_ms=100,
        )
    )
    qtbot.addWidget(editor)
    editor.show()

    with qtbot.waitSignal(editor.shot_added, timeout=1000) as added:
        qtbot.mouseClick(editor, Qt.LeftButton, pos=QPoint(200, 90))
    assert 480 <= added.args[0] <= 520

    with qtbot.waitSignal(editor.shot_deleted, timeout=1000) as deleted:
        qtbot.mouseClick(editor, Qt.RightButton, pos=QPoint(100, 90))
    assert deleted.args[0] == "shot-1"


def test_overlay_preview_emits_score_position(qtbot) -> None:
    widget = OverlayPreview()
    widget.resize(400, 300)
    project = Project()
    widget.set_state(project, 0)
    widget.set_placement_mode(True)
    qtbot.addWidget(widget)
    widget.show()

    with qtbot.waitSignal(widget.score_position_selected, timeout=1000) as placed:
        qtbot.mouseClick(widget, Qt.LeftButton, pos=QPoint(100, 150))
    x_norm, y_norm = placed.args
    assert 0.24 <= x_norm <= 0.26
    assert 0.49 <= y_norm <= 0.51


def test_waveform_editor_keyboard_nudges_and_deletes_selected_marker(qtbot) -> None:
    editor = WaveformEditor()
    editor.resize(400, 180)
    editor.set_state(
        WaveformState(
            duration_ms=1000,
            waveform=[0.2] * 512,
            shots=[ShotEvent(id="shot-1", time_ms=250)],
            beep_time_ms=100,
            selected_shot_id="shot-1",
            frame_nudge_ms=33,
        )
    )
    qtbot.addWidget(editor)
    editor.show()

    with qtbot.waitSignal(editor.shot_moved, timeout=1000) as moved:
        qtbot.keyClick(editor, Qt.Key_Right)
    assert tuple(moved.args) == ("shot-1", 251)

    with qtbot.waitSignal(editor.shot_moved, timeout=1000) as moved:
        qtbot.keyClick(editor, Qt.Key_Left, modifier=Qt.ShiftModifier)
    assert tuple(moved.args) == ("shot-1", 240)

    with qtbot.waitSignal(editor.shot_moved, timeout=1000) as moved:
        qtbot.keyClick(editor, Qt.Key_Right, modifier=Qt.AltModifier)
    assert tuple(moved.args) == ("shot-1", 283)

    with qtbot.waitSignal(editor.shot_deleted, timeout=1000) as deleted:
        qtbot.keyClick(editor, Qt.Key_Delete)
    assert tuple(deleted.args) == ("shot-1",)


def test_waveform_editor_double_click_requests_seek(qtbot) -> None:
    editor = WaveformEditor()
    editor.resize(400, 180)
    editor.set_state(WaveformState(duration_ms=1000, waveform=[0.2] * 512))
    qtbot.addWidget(editor)
    editor.show()

    with qtbot.waitSignal(editor.seek_requested, timeout=1000) as seek:
        qtbot.mouseDClick(editor, Qt.LeftButton, pos=QPoint(300, 90))
    assert 730 <= seek.args[0] <= 770


def test_overlay_preview_emits_crop_center_selection(qtbot) -> None:
    widget = OverlayPreview()
    widget.resize(400, 300)
    project = Project()
    project.export.aspect_ratio = AspectRatio.PORTRAIT
    widget.set_state(project, 0)
    widget.set_crop_mode(True)
    qtbot.addWidget(widget)
    widget.show()

    with qtbot.waitSignal(widget.crop_center_selected, timeout=1000) as selected:
        qtbot.mouseClick(widget, Qt.LeftButton, pos=QPoint(200, 60))
    x_norm, y_norm = selected.args
    assert 0.49 <= x_norm <= 0.51
    assert 0.19 <= y_norm <= 0.21
