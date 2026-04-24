from __future__ import annotations

from pathlib import Path


def test_browser_control_qa_matrix_documents_current_browser_suites() -> None:
    matrix = Path("docs/project/browser-control-qa-matrix.md").read_text(encoding="utf-8")

    assert "It is not a claim that every button or field has its own direct behavior test." in matrix
    assert "If a control is missing from this matrix, it does not have an explicit owner yet." in matrix
    assert "| Splits / waveform | timing edit, selected shot actions, add/delete/move/nudge, waveform expand/zoom/amplitude, waveform pan |" in matrix
    assert "| Markers / Review / Overlay | show overlay checkbox, badge size, style, locks, color pickers, text boxes, popup editor, text-box drag |" in matrix
    assert "tests/browser/test_browser_interactions.py" in matrix
    assert "waveform expand/zoom/amplitude" in matrix
    assert "waveform pan and shot movement" in matrix
    assert "overlay visibility and badge toggles" in matrix
    assert "review text-box creation and drag" in matrix

    for test_path in [
        "tests/browser/test_browser_static_ui.py",
        "tests/browser/test_browser_control.py",
        "tests/browser/test_browser_interactions.py",
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