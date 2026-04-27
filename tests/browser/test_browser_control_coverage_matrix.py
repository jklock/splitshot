from __future__ import annotations

from pathlib import Path


def test_browser_control_qa_matrix_documents_current_browser_suites() -> None:
    matrix = Path("docs/project/browser-control-qa-matrix.md").read_text(encoding="utf-8")

    assert "It is not a claim that every button or field has its own direct behavior test." in matrix
    assert "If a control is missing from this matrix, it does not have an explicit owner yet." in matrix
    assert "| Project / import | project details, choose/open project, primary import, remote PractiScore connect, remote match select, selected-match import, clear session, manual fallback file import, delete project |" in matrix
    assert "| Splits / waveform | timing edit, selected shot actions, add/delete/move/nudge, waveform expand/zoom/amplitude, waveform pan |" in matrix
    assert "| Markers / Review / Overlay | marker import, marker template defaults, playback window, collapsed nav, timeline selectors, time-marker list cards, bubble enabled, bubble card actions, show overlay checkbox, badge size, style, locks, timer/draw/score position inputs and lock-to-stack controls, bubble size override, font size, bold/italic controls, color pickers, review text-box background/text color and opacity, text boxes, popup editor, text-box drag |" in matrix
    assert "tests/browser/test_browser_interactions.py" in matrix
    assert "tests/browser/test_metrics_e2e.py" in matrix
    assert "tests/browser/test_settings_e2e.py" in matrix
    assert "match-list load" in matrix
    assert "selected-match import" in matrix
    assert "expired-session rendering" in matrix
    assert "manual fallback parity" in matrix
    assert "waveform expand/zoom/amplitude" in matrix
    assert "waveform pan and shot movement" in matrix
    assert "marker import-selected-shot seek" in matrix
    assert "marker playback-window seek or loop wrap" in matrix
    assert "time-marker list-card select and seek" in matrix
    assert "bubble enabled live-badge toggle" in matrix
    assert "bubble card toggle or duplicate or remove rerender" in matrix
    assert "timer badge background color-picker live preview and close-commit" in matrix
    assert "marker template defaults for fresh shot-linked markers" in matrix
    assert "collapsed marker navigation" in matrix
    assert "shot-editor step or duplicate or delete flows" in matrix
    assert "overlay visibility and badge toggles" in matrix
    assert "timer/draw/score badge position inputs and lock-to-stack controls" in matrix
    assert "overlay bubble size override" in matrix
    assert "font size, bold/italic controls" in matrix
    assert "export log modal open/close/backdrop and download" in matrix
    assert "review text-box background/text color and opacity" in matrix
    assert "review text-box background/text/opacity preview" in matrix
    assert "review source-switch after-final render" in matrix
    assert "review custom placement or size" in matrix
    assert "review stack-lock editor behavior" in matrix
    assert "review text-box creation and drag" in matrix
    assert "| ShotML | threshold apply/reset, rerun, proposal generation, reset defaults |" in matrix
    assert "metrics pane row propagation" in matrix
    assert "timing-event metrics ordering" in matrix
    assert "section collapse state within a live session" in matrix

    for test_path in [
        "tests/browser/test_browser_static_ui.py",
        "tests/browser/test_browser_control.py",
        "tests/browser/test_browser_control_inventory_audit.py",
        "tests/browser/test_browser_control_coverage_matrix.py",
        "tests/browser/test_browser_interactions.py",
        "tests/browser/test_metrics_e2e.py",
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
        "Score",
        "Splits / waveform",
        "Markers / Review / Overlay",
        "Settings",
        "Metrics",
        "Export",
        "ShotML",
    ]:
        assert surface in matrix