from __future__ import annotations

from pathlib import Path


def test_browser_control_qa_matrix_documents_current_browser_suites() -> None:
    matrix = Path("docs/project/browser-control-qa-matrix.md").read_text(encoding="utf-8")

    assert (
        "Use `scripts/audits/browser/pane_function_audit.py` as the code-first companion audit."
        in matrix
    )
    assert (
        "| Project / import | project details, project output root, create/select/open project, project-folder display, gated PractiScore dashboard opener, project-rooted PractiScore file import, inferred match type, competitor/place/class/division selectors |"
        in matrix
    )
    assert (
        "| Media | active stage selector, stage name, `Save`, `Delete`, `Add Stage`, persistent Primary Media/Secondary Media disclosures, `Add Primary`, primary asset `Replace`/`Clear`, `Set Primary`, `Remove`, `Add Media` |"
        in matrix
    )
    assert (
        "| Compose | stage default layout/size/position controls, `Reset Defaults`, per-item card toggle, per-item size/opacity/position/layout/sync controls |"
        in matrix
    )
    assert (
        "| Markers / Review / Overlay | marker authoring, review visibility selectors, independent split-badge score visibility, overlay badge/text-box controls, imported and computed summary preview formatting, stage presentation waterfall, marker editor, text-box drag |"
        in matrix
    )
    assert "| In / Out |" in matrix
    assert (
        "| Queue | one-action `Queue All Files`, all-match stage membership, always-visible status rows, intro/outro include choices, project fades, output-folder reveal, live processing log, whole-queue progress, `Process Queue`, `Process as One File` |"
        in matrix
    )
    assert (
        "| Settings | scope, landing pane, reopen-last-tool, section save current/reset default actions, layout defaults, Compose defaults, complete Overlay/Review defaults, marker defaults including default quadrant, complete persistent Export and Queue/combined-output defaults, Intro/Outro fade/overlay defaults, complete ShotML defaults, section collapse, template fields |"
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
