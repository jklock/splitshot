from __future__ import annotations

from pathlib import Path


def test_browser_control_qa_matrix_documents_current_browser_suites() -> None:
    matrix = Path("docs/project/browser-control-qa-matrix.md").read_text(encoding="utf-8")

    assert (
        "Use `scripts/audits/browser/pane_function_audit.py` as the code-first companion audit."
        in matrix
    )
    assert (
        "| Project / import | project details, project output root, create/select/reveal project, project-folder display, gated PractiScore dashboard opener, project-rooted PractiScore file import, match-type selection, competitor/place/class/division selectors |"
        in matrix
    )
    assert (
        "| Media | active stage selector, stage name, `Save Stage`, `Delete Stage`, active-stage `Add Stage`, primary asset, stage file rows, file intake, `Set Primary`, `Remove`, `Add Media` |"
        in matrix
    )
    assert (
        "| Compose | stage default layout/size/position controls, default restore, per-item card toggle, per-item size/opacity/position/layout/sync controls |"
        in matrix
    )
    assert (
        "| Markers / Review / Overlay | marker authoring, review visibility selectors, independent split-badge score visibility, overlay badge/text-box controls, imported summary preview formatting, marker editor, text-box drag |"
        in matrix
    )
    assert (
        "| Queue | stage selector, queue membership, queue status, per-stage collapse, `Apply Active Stage Settings to Queued`, `Process Many`, `Process Into 1 File` |"
        in matrix
    )
    assert (
        "| Settings | scope, landing pane, reopen-last-tool, section save current/reset default actions, layout defaults, Compose defaults, overlay defaults, marker defaults including default quadrant, export defaults, ShotML defaults, section collapse, template fields |"
        in matrix
    )
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
