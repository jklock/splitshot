from __future__ import annotations

import json
from pathlib import Path


SEAM_REGISTRY = json.loads(
    Path("docs/project/browser-proof-seams.json").read_text(encoding="utf-8")
)


def test_browser_control_qa_matrix_documents_current_browser_suites() -> None:
    matrix = Path("docs/project/browser-control-qa-matrix.md").read_text(encoding="utf-8")

    assert (
        "It is not a claim that every button or field has its own direct behavior test." in matrix
    )
    assert (
        "If a control is missing from this matrix, it does not have an explicit owner yet."
        in matrix
    )
    assert "Coverage ownership in this matrix is **not** a proof-taxonomy class." in matrix
    assert (
        "Inventory presence, surface ownership, or companion-plan status does **not** by itself establish meaningful closure"
        in matrix
    )
    assert (
        "| Project / import | project details, create/select project, project-folder display, gated PractiScore dashboard opener, gated manual PractiScore file import, gated primary import, metadata-only delete |"
        in matrix
    )
    assert (
        "| Match workspace | shared-shell main/lower/right Match layout, media-backed stage tiles, workspace create/open/save/add-stage/remove-stage plus loading/error states, stage card selection/open/return, setup-once preview/apply/dismiss flow, selected-stage lower-pane truth stays pinned while Composite/Export swap beneath it, shared defaults apply/reset, stage overrides apply/reset, stage clip add plus composite reorder/per-clip role-sync-audio editing/plan refresh/apply-clear cut overrides, recap stage selection plus transition/result-card configuration and render outcomes, batch export recipe selection/select all/none/start, Match settings local persistence |"
        in matrix
    )
    assert (
        "| Performance Library | shared-shell main/lower/right Performance layout, loading/empty/stale state affordances, overview summary tiles, records search/sort/filter plus personal-best list, selected-record lower-pane detail, Open Stage/Open Workspace, notes/tags persistence entry points, analytics truth messaging, backup create/restore, CSV/JSON export, Performance settings local persistence |"
        in matrix
    )
    assert (
        "| Compose | add media, Composition Defaults collapse and restore, side-by-side/above-below/picture-in-picture/full-screen-portrait/dual-HUD layout selection, reusable Trim Dead Time run-window editor, per-item card toggle/remove, per-item angle-role selection, per-item layer size/opacity/position/sync controls, visible beep-sync analyze/rerun action, first-video secondary sync-analysis status/rerun, shared-lane secondary waveform visibility, GIF added-media typing |"
        in matrix
    )
    assert (
        "| Splits / waveform | split pane summary, enable splits toggle, Edit, timing-event controls, waveform expand/zoom/amplitude, waveform pan |"
        in matrix
    )
    assert (
        "| Markers / Review / Overlay | compact marker enable toggle, compact Edit or Collapse launcher, compact Add Time Marker action, compact marker list, edit-mode-only selected-marker editor, selected-marker Enable Motion checkbox, guided Start/Finish/Auto/Detail rows, Generate/Add Detail/Previous/Next/Remove Detail/Clear path actions, workbench add/import/filter/navigation controls, settings marker defaults plus marker default motion checkbox, workbench marker list, bubble enabled, editor duplicate/remove actions, show overlay checkbox, review show-box selectors for markers/added media/timer/draw/splits/score, review-source picker, badge size/style/custom font sizing, shared curated font list, stack gap, edge padding, timer/draw/score position inputs and lock-to-stack controls, bubble size override, font size, bold/italic controls, score colors, Export Badges output-profile handoff, marker bubble shape or typography controls, review text-box background/text color and opacity, review text-box typography controls, text boxes, popup editor, text-box drag |"
        in matrix
    )
    assert (
        "| Settings | scope, landing pane, reopen-last-tool, section save current/reset default actions, layout defaults, Compose defaults, overlay defaults, marker defaults, export defaults, ShotML defaults, section collapse, template fields |"
        in matrix
    )
    assert (
        "| Export | output path, preset, quality, output-profile list/create/select/delete, framing/title/logo output-hook save/close controls, show export log modal open/close/backdrop and download, CI Clip1 MP4 proof export |"
        in matrix
    )
    assert (
        "| ShotML | average auto-confidence summary, threshold apply/reset, rerun, proposal generation, reset defaults |"
        in matrix
    )
    assert "tests/browser/test_browser_interactions.py" in matrix
    assert "tests/browser/test_landing_backend_routes.py" in matrix
    assert "tests/browser/test_library_backend_contracts.py" in matrix
    assert "tests/browser/test_metrics_e2e.py" in matrix
    assert "tests/browser/test_settings_e2e.py" in matrix
    assert "dashboard-open action" in matrix
    assert "manual file import parity" in matrix
    assert "missing-folder creation notice" in matrix
    assert "metadata-only delete safety" in matrix
    assert "output-profile create/select plus Compose Trim Dead Time, Overlay Export Badges, and Export framing/title/logo output-hook save/close flows" in matrix
    assert "Match workspace new/open/save lifecycle plus stage add/select/remove and loading/error states" in matrix
    assert "Match workspace stage open and shell return-to-Match behavior" in matrix
    assert "Match workspace live preview tiles and selected-stage lower-pane truth across Composite/Export lower-pane swaps" in matrix
    assert (
        "Match shared defaults apply/reset, stage override apply/reset, and selected-stage lower-pane / workflow-inspector routing"
        in matrix
    )
    assert "setup-once preview/apply confirmation and dismiss" in matrix
    assert "Match Stage Composite reorder, per-clip role/sync/audio editing, plan refresh, and apply/clear cut override actions plus refreshed state" in matrix
    assert "Match recap stage selection plus transition/result-card configuration and success/error status" in matrix
    assert "Match batch export recipe selection, queue select all/none, and truthful success/error reporting" in matrix
    assert "Match settings local persistence and remember-stage behavior" in matrix
    assert "Performance Library selected-record reopen to Stage and Match workspace" in matrix
    assert "Performance Library settings local persistence, stale banner, and manual refresh load behavior" in matrix
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
    assert "review show-box selectors for markers/added media/timer/draw/splits/score" in matrix
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
    assert "DEV-106.landing_recent" in matrix
    assert "DEV-107.root_shell_compat" in matrix
    assert "project.practiscore_bridge" in matrix
    assert (
        "PractiScore proof keeps manual `Select PractiScore File` fallback and local `Match type` / `Stage #` / `Competitor name` / `Place` selectors in scope"
        not in matrix
    )

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
        "Match workspace",
        "Performance Library",
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


def test_browser_proof_seam_registry_tracks_cross_surface_closeout_targets() -> None:
    landing = SEAM_REGISTRY["DEV-106.landing_recent"]
    compat = SEAM_REGISTRY["DEV-107.root_shell_compat"]
    practiscore = SEAM_REGISTRY["project.practiscore_bridge"]

    assert landing["status"] == "interaction-proven"
    assert landing["proof_strength"] == "backend-route + static-contract + interaction"
    assert (
        "tests/browser/test_browser_interactions.py::test_landing_recent_stage_rows_switch_surface_without_auto_open"
        in landing["evidence_tests"]
    )
    assert "docs/project/browser-control-qa-matrix.md" in landing["doc_refs"]

    assert compat["status"] == "interaction-proven"
    assert compat["proof_strength"] == "compat-static-contract + guarded interaction consumers"
    assert (
        "tests/browser/test_browser_interactions.py::test_shell_compat_host_on_open_project_callback_opens_saved_project"
        in compat["evidence_tests"]
    )
    assert (
        "tests/browser/test_browser_interactions.py::test_performance_library_compat_selected_record_and_render_rerender_detail_truth"
        in compat["evidence_tests"]
    )
    assert compat["compat_consumers"] == [
        "window.splitshot.onOpenProject",
        "renderAutomationSurface",
        "selectedLibraryRecord",
    ]

    assert practiscore["status"] == "bridge-proven"
    assert "docs/project/completion-bundles/development/stage-reference.md" in practiscore["doc_refs"]
    assert "tests/browser/test_practiscore_session_api.py" in practiscore["evidence_tests"]


def test_development_proof_docs_capture_mixed_family_taxonomy_and_honesty_caveats() -> None:
    proof = Path("docs/project/completion-bundles/development/proof.md").read_text(
        encoding="utf-8"
    )
    stage_reference = Path(
        "docs/project/completion-bundles/development/stage-reference.md"
    ).read_text(encoding="utf-8")
    match_reference = Path(
        "docs/project/completion-bundles/development/match-reference.md"
    ).read_text(encoding="utf-8")

    assert "docs/project/browser-proof-seams.json" in proof
    assert "DEV-106.landing_recent" in proof
    assert "DEV-107.root_shell_compat" in proof
    assert (
        "Coverage-plan phases and inventory ownership describe browser test/document ownership"
        in proof
    )

    assert "## Stage family proof-taxonomy summary" in stage_reference
    assert "project.practiscore_bridge" in stage_reference

    assert "## Match family proof-taxonomy summary" in match_reference
    assert (
        "Stage selection/order/options are runtime-only until `Render Recap` produces `recap.mp4`."
        in match_reference
    )
    assert "DEV-107.root_shell_compat" in match_reference
