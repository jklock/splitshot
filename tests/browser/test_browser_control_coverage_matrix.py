from __future__ import annotations

from pathlib import Path


def test_browser_control_qa_matrix_documents_current_browser_suites() -> None:
    matrix = Path("docs/project/browser-control-qa-matrix.md").read_text(encoding="utf-8")

    assert "It is not a claim that every button or field has its own direct behavior test." in matrix
    assert "If a control is missing from this matrix, it does not have an explicit owner yet." in matrix
    assert "| Project / import | project details, create/select project, project-folder display, gated PractiScore dashboard opener, gated manual PractiScore file import, imported stage selector, `match-stage-number`, `match-competitor-name`, `match-competitor-place`, compact imported summary rows |" in matrix
    assert "| Media | stage cards, per-stage collapse, stage file rows, file intake, `Set Primary`, `Primary`, `Remove`, `Add More`, `Edit Stage` |" in matrix
    assert "| Compose | compose default settings collapse and restore, per-item card toggle/remove, per-item size/opacity/position/layout controls |" in matrix
    assert "| Markers / Review / Overlay | marker authoring, review visibility selectors, overlay badge/text-box controls, imported summary preview formatting, popup editor, text-box drag |" in matrix
    assert "| Settings | scope, landing pane, reopen-last-tool, section save current/reset default actions, layout defaults, Compose defaults, overlay defaults, marker defaults, export defaults, ShotML defaults, section collapse, template fields |" in matrix
    for surface in [
        "Media",
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
