from __future__ import annotations

from pathlib import Path


def test_browser_control_qa_matrix_documents_current_browser_suites() -> None:
    matrix = Path("docs/project/browser-control-qa-matrix.md").read_text(encoding="utf-8")

    assert "It is not a claim that every button or field has its own direct behavior test." in matrix
    assert "If a control is missing from this matrix, it does not have an explicit owner yet." in matrix
    assert "| Project / import | project details, create/select project, project-folder display, gated PractiScore dashboard opener, gated manual PractiScore file import, gated primary import, metadata-only delete |" in matrix
    assert "| Compose | add media, compose default settings collapse and restore, per-item card toggle/remove, per-item size/opacity/position/layout controls |" in matrix
    assert "review show-box selectors for markers/added media/timer/draw/splits/score" in matrix
    assert "| Settings | scope, landing pane, reopen-last-tool, section save current/reset default actions, layout defaults, Compose defaults, overlay defaults, marker defaults, export defaults, ShotML defaults, section collapse, template fields |" in matrix
    for surface in [
        "Compose",
        "Score",
        "Splits / waveform",
        "Markers / Review / Overlay",
        "Settings",
        "Metrics",
        "Export",
        "ShotML",
    ]:
        assert surface in matrix
