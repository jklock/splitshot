from __future__ import annotations

from pathlib import Path


def test_browser_control_qa_matrix_documents_current_browser_suites() -> None:
    matrix = Path("docs/project/browser-control-qa-matrix.md").read_text(encoding="utf-8")

    assert (
        "It is not a claim that every button or field has its own direct behavior test." in matrix
    )
    assert (
        "If a control is missing from this matrix, it does not have an explicit owner yet."
        in matrix
    )
    assert (
        "| Project / import | project details, create/select project, project-folder display, gated PractiScore dashboard opener, gated manual PractiScore file import, gated primary import, metadata-only delete |"
        in matrix
    )
    assert (
        "| PiP | add media, PiP default settings collapse and restore, per-item card toggle/remove, per-item size/opacity/position/sync controls, visible beep-sync analyze/rerun action, first-video secondary sync-analysis status/rerun, shared-lane secondary waveform visibility, GIF PiP media typing |"
        in matrix
    )
    assert (
        "| Splits / waveform | split pane summary, enable splits toggle, Edit, timing-event controls, waveform expand/zoom/amplitude, waveform pan |"
        in matrix
    )
    assert (
        "| Markers / Review / Overlay | compact marker enable toggle, compact Edit or Collapse launcher, compact Add Time Marker action, compact marker list, edit-mode-only selected-marker editor, selected-marker Enable Motion checkbox, guided Start/Finish/Auto/Detail rows, Generate/Add Detail/Previous/Next/Remove Detail/Clear path actions, workbench add/import/filter/navigation controls, settings marker defaults plus marker default motion checkbox, workbench marker list, bubble enabled, editor duplicate/remove actions, show overlay checkbox, review show-box selectors for markers/PiP/timer/draw/splits/score, badge size/style/custom font sizing, shared curated font list, stack gap, edge padding, timer/draw/score position inputs and lock-to-stack controls, bubble size override, font size, bold/italic controls, score colors, marker bubble shape or typography controls, review text-box background/text color and opacity, review text-box typography controls, text boxes, popup editor, text-box drag |"
        in matrix
    )
    assert (
        "| Settings | scope, landing pane, reopen-last-tool, section save current/reset default actions, layout defaults, PiP defaults, overlay defaults, marker defaults, export defaults, ShotML defaults, section collapse, template fields |"
        in matrix
    )
    assert (
        "| Export | output path, preset, quality, output-hook save/close controls, show export log modal open/close/backdrop and download, CI Clip1 MP4 proof export |"
        in matrix
    )
    assert (
        "| ShotML | average auto-confidence summary, threshold apply/reset, rerun, proposal generation, reset defaults |"
        in matrix
    )
    assert "tests/browser/test_browser_interactions.py" in matrix
    assert "tests/browser/test_metrics_e2e.py" in matrix
    assert "tests/browser/test_settings_e2e.py" in matrix
    assert "dashboard-open action" in matrix
    assert "manual file import parity" in matrix
    assert "missing-folder creation notice" in matrix
    assert "metadata-only delete safety" in matrix
    assert "waveform expand/zoom/amplitude" in matrix
    assert "drag movement" in matrix
    assert "workbench import-selected-shot seek" in matrix
    assert "Enable Motion checkbox state" in matrix
    assert "guided step workflow state" in matrix
    assert "selected-marker panel visible only in edit mode" in matrix
    assert "workbench list select and seek" in matrix
    assert "workbench open/close flow" in matrix
    assert "bubble enabled live-badge toggle" in matrix
    assert "selected-editor duplicate or remove rerender" in matrix
    assert "workbench editor continuity" in matrix

    assert "timer badge background color-picker live preview and close-commit" in matrix
    assert "marker template defaults for fresh shot-linked markers" in matrix
    assert "workbench marker navigation" in matrix
    assert "overlay visibility and badge toggles" in matrix
    assert "timer/draw/score badge position inputs and lock-to-stack controls" in matrix
    assert "overlay bubble size override" in matrix
    assert "overlay custom badge sizing" in matrix
    assert "font size, bold/italic controls" in matrix
    assert "export log modal open/close/backdrop and download" in matrix
    assert "review show-box selectors for markers/PiP/timer/draw/splits/score" in matrix
    assert "review text-box background/text color and opacity" in matrix
    assert "review text-box background/text/opacity preview" in matrix
    assert "review show-box selector state" in matrix
    assert "review source-switch after-final render" in matrix
    assert "review custom placement or size" in matrix
    assert "stack lock behavior" in matrix
    assert "review text-box creation and drag" in matrix
    assert "average auto-confidence summary" in matrix
    assert "metrics pane row propagation" in matrix
    assert "timing-event metrics ordering" in matrix
    assert "section collapse state within a live session" in matrix
    assert "layout capture/release defaults" in matrix
    assert "visible analyze or re-run beep-sync action" in matrix
    assert "CI artifact export proof from `docs/Clip1.MP4`" in matrix

    for test_path in [
        "tests/browser/test_browser_static_ui.py",
        "tests/browser/test_browser_control.py",
        "tests/browser/test_browser_control_inventory_audit.py",
        "tests/browser/test_browser_control_coverage_matrix.py",
        "tests/browser/test_browser_interactions.py",
        "tests/browser/test_metrics_e2e.py",
        "tests/browser/test_settings_defaults_truth_gate.py",
        "tests/browser/test_settings_e2e.py",
        "tests/browser/test_scoring_metrics_contracts.py",
        "tests/browser/test_project_lifecycle_contracts.py",
        "tests/browser/test_timing_waveform_contracts.py",
        "tests/browser/test_merge_export_contracts.py",
        "tests/browser/test_overlay_review_contracts.py",
        "tests/export/test_export.py",
        "tests/analysis/test_analysis.py",
    ]:
        assert test_path in matrix

    for surface in [
        "Shared shell",
        "Project / import",
        "PiP",
        "Score",
        "Splits / waveform",
        "Markers / Review / Overlay",
        "Settings",
        "Metrics",
        "Export",
        "ShotML",
    ]:
        assert surface in matrix
