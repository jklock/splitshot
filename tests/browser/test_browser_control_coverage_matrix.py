from __future__ import annotations

import json
from pathlib import Path


SEAM_REGISTRY = json.loads(
    Path("docs/project/browser-proof-seams.json").read_text(encoding="utf-8")
)
PANE_MANIFEST = json.loads(
    Path("scripts/testing/pane_feature_manifests.json").read_text(encoding="utf-8")
)


def _parse_markdown_table(text: str, heading: str) -> list[dict[str, str]]:
    lines = text.splitlines()
    start = lines.index(heading)
    table_lines: list[str] = []
    for line in lines[start + 1 :]:
        if not line.strip():
            if table_lines:
                break
            continue
        if not line.startswith("|"):
            if table_lines:
                break
            continue
        table_lines.append(line)

    headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows.append(dict(zip(headers, cells, strict=True)))
    return rows


def _split_inline_list(value: str) -> list[str]:
    return [item.strip().strip("`") for item in value.split(",") if item.strip()]


def _assert_relative_repo_files_exist(paths: list[str]) -> None:
    missing = [path for path in paths if not Path(path).is_file()]
    assert not missing, f"Missing repo paths referenced by proof-seam registry: {missing}"


def _manifest_rows() -> dict[str, dict[str, list[str] | str]]:
    return {
        pane["pane_id"]: {
            "pane_test_id": pane["pane_test_id"],
            "feature_ids": [feature["feature_id"] for feature in pane["features"]],
            "runner_suites": list(pane["runner_suites"]),
        }
        for pane in PANE_MANIFEST["panes"]
    }


def _support_surface_rows() -> dict[str, dict[str, list[str] | str]]:
    return {
        surface["surface_id"]: {
            "support_role": surface["support_note"],
            "feature_ids": [feature["feature_id"] for feature in surface["features"]],
            "runner_suites": list(surface["runner_suites"]),
        }
        for surface in PANE_MANIFEST["support_surfaces"]
    }


def test_browser_control_qa_matrix_documents_current_browser_suites() -> None:
    matrix = Path("docs/project/browser-control-qa-matrix.md").read_text(encoding="utf-8")
    interaction_heading = "The interaction suite (`tests/browser/test_browser_interactions.py`) contributes browser evidence support for:"
    settings_heading = "The Settings pane suites (`tests/browser/test_settings_e2e.py` and `tests/browser/test_settings_defaults_truth_gate.py`) contribute browser evidence support for:"
    metrics_heading = "The Metrics pane suites (`tests/browser/test_metrics_e2e.py` and `tests/browser/test_scoring_metrics_contracts.py`) contribute browser evidence support for:"

    assert (
        "This matrix maps SplitShot’s browser-visible control surfaces to the tests that exercise them and to the canonical taxonomy IDs they support."
        in matrix
    )
    assert (
        "This matrix is a browser inventory and support map. It is **not** a closure ledger."
        in matrix
    )
    assert (
        "If a control is missing from this matrix, it does not have an explicit browser-QA owner yet."
        in matrix
    )
    assert (
        "| Landing | Supports `TAX-0` and `TAX-2`; contributes to `TAX-1` and `TAX-5` | Three workflow entry cards, quick-start shortcuts, landing Open File bootstrap, recent-stage list hydration from /api/landing/recent, and surface-only recent-row handoff |"
        in matrix
    )
    assert (
        "| Shared shell | Supports `TAX-0`, `TAX-1`, and `TAX-2`; contributes to `TAX-5` | Shared `stage-workspace` shell markers across Stage/Match/Performance, home and return controls, tool-rail collapse/minimize, context/status header display, layout lock toggle, resize handles, and compat rerender/open-project consumers |"
        in matrix
    )
    assert (
        "| Project / import | Supports `TAX-0` and `TAX-1`; contributes to `TAX-5` | Project details, create/select project, project-folder display, gated PractiScore dashboard opener, manual `Select PractiScore File` fallback, local `Match type` / `Stage #` / `Competitor name` / `Place` selectors, remote PractiScore session and sync state rendering, ungated empty-stage `Import Video` chooser bootstrap without a saved project, readonly `Primary Video` display, gated Project-pane `Import Primary Video` chooser with project-folder home fallback once a project exists, metadata-only delete |"
        in matrix
    )
    assert (
        "| Match workspace | Supports `TAX-0` and `TAX-1`; contributes to `TAX-5` | Shared-shell main/lower/right Match layout, media-backed stage tiles, workspace create/open/save/add-stage/remove-stage plus loading/error states, stage card selection/open/return, setup-once preview/apply/dismiss flow, selected-stage lower-pane truth stays pinned while Composite/Export swap beneath it, shared defaults apply/reset, stage overrides apply/reset, stage clip add plus composite reorder/per-clip role-sync-audio editing/plan refresh/apply-clear cut overrides, recap stage selection plus transition/result-card configuration and render outcomes, batch export recipe selection/select all/none/start, Match settings local persistence |"
        in matrix
    )
    assert (
        "| Performance Library | Supports `TAX-0` and `TAX-1`; contributes to `TAX-5` | Shared-shell main/lower/right Performance layout, loading/empty/stale state affordances, overview summary tiles, records search/sort/filter plus personal-best list, selected-record lower-pane detail, Open Stage/Open Workspace, notes/tags persistence entry points, analytics truth messaging, backup create/restore, CSV/JSON export, Performance settings local persistence |"
        in matrix
    )
    assert "## Pane manifest references" in matrix
    assert "scripts/testing/pane_feature_manifests.json" in matrix
    assert (
        "| Project / import | `pane.project` | `tax1.project.pane` | `project.lifecycle`, `project.practiscore_import`, `project.primary_video_import` | `pane-project`, `browser` |"
        in matrix
    )
    assert (
        "| Match workspace | `pane.match` | `tax1.match.pane` | `match.workspace_lifecycle`, `match.setup_once_and_defaults`, `match.stage_navigation_shell`, `match.composite_editor`, `match.recap`, `match.batch_export`, `match.settings` | `pane-match`, `browser` |"
        in matrix
    )
    assert (
        "| Performance Library | `pane.performance` | `tax1.performance.pane` | `performance.overview`, `performance.records_filtering`, `performance.record_detail_actions`, `performance.analytics`, `performance.backup_and_export`, `performance.settings` | `pane-performance`, `browser` |"
        in matrix
    )
    assert (
        "| Settings | `pane.settings` | `tax1.settings.pane` | `settings.global_template_scope`, `settings.layout_defaults`, `settings.scoring_and_compose_defaults`, `settings.overlay_and_marker_defaults`, `settings.export_and_shotml_defaults`, `settings.section_visibility` | `pane-settings`, `browser` |"
        in matrix
    )
    assert (
        "| Metrics | `pane.metrics` | `tax1.metrics.pane` | `metrics.summary_and_workbench`, `metrics.row_propagation`, `metrics.stage_story`, `metrics.scoring_context`, `metrics.export` | `pane-metrics`, `browser` |"
        in matrix
    )
    assert "## Support surface manifests" in matrix
    assert "support_surface_ids" in matrix
    assert "surface.landing" in matrix
    assert "surface.shared_shell" in matrix
    assert "surface.stage.compose" in matrix
    assert "surface.stage.scoring" in matrix
    assert "surface.stage.splits_waveform" in matrix
    assert "surface.stage.markers_review_overlay" in matrix
    assert "surface.stage.export" in matrix
    assert "surface.stage.shotml" in matrix
    assert "landing.entry_cards_and_quick_start" in matrix
    assert "landing.recent_activity" in matrix
    assert "shared_shell.shell_markers_and_surface_routing" in matrix
    assert "shared_shell.home_and_return_controls" in matrix
    assert "shared_shell.rail_layout_and_resize" in matrix
    assert "stage.compose.secondary_waveform_sync" in matrix
    assert "stage.scoring.summary_and_editing" in matrix
    assert "stage.splits_waveform.waveform_navigation" in matrix
    assert "stage.markers_review_overlay.overlay_styling_and_positioning" in matrix
    assert "stage.export.output_profiles_and_hooks" in matrix
    assert "stage.shotml.proposals_and_section_persistence" in matrix
    assert (
        "Stage-tool support surface only; not a first-class pane or view closure record." in matrix
    )
    assert "Landing support surface only; not a first-class pane or view closure record." in matrix
    assert (
        "Shared-shell support surface only; not a first-class pane or view closure record."
        in matrix
    )
    assert "tests/browser/test_browser_interactions.py" in matrix
    assert "tests/browser/test_landing_page.py" in matrix
    assert "tests/browser/test_landing_backend_routes.py" in matrix
    assert "tests/browser/test_automation_ui_shell_contracts.py" in matrix
    assert "tests/browser/test_browser_rail_layout.py" in matrix
    assert "tests/browser/test_library_backend_contracts.py" in matrix
    assert "tests/browser/test_metrics_e2e.py" in matrix
    assert "tests/browser/test_settings_e2e.py" in matrix
    assert interaction_heading in matrix
    assert settings_heading in matrix
    assert metrics_heading in matrix
    assert "dashboard-open action" in matrix
    assert (
        "landing Open File and stage-empty Import Video chooser/path bootstrap parity without a saved project"
        in matrix
    )
    assert "manual PractiScore file import fallback parity" in matrix
    assert "missing-folder creation notice" in matrix
    assert "metadata-only delete safety" in matrix
    assert (
        "Match workspace new/open/save lifecycle plus stage add/select/remove and loading/error states"
        in matrix
    )
    assert "Match workspace stage open and shell return-to-Match behavior" in matrix
    assert (
        "Match workspace live preview tiles and selected-stage lower-pane truth across Composite/Export lower-pane swaps"
        in matrix
    )
    assert (
        "Match shared defaults apply/reset, stage override apply/reset, and selected-stage lower-pane / workflow-inspector routing"
        in matrix
    )
    assert "setup-once preview/apply confirmation and dismiss" in matrix
    assert (
        "Match Stage Composite reorder, per-clip role/sync/audio editing, plan refresh, and apply/clear cut override actions plus refreshed state"
        in matrix
    )
    assert (
        "Match recap stage selection plus transition/result-card configuration and success/error status"
        in matrix
    )
    assert (
        "Match batch export recipe selection, queue select all/none, and truthful success/error reporting"
        in matrix
    )
    assert "Match settings local persistence and remember-stage behavior" in matrix
    assert "Performance Library selected-record reopen to Stage and Match workspace" in matrix
    assert (
        "Performance Library settings local persistence, stale banner, and manual refresh load behavior"
        in matrix
    )
    assert "average auto-confidence summary" in matrix
    assert "metrics pane row propagation" in matrix
    assert "timing-event metrics ordering" in matrix
    assert (
        "settings defaults seeding overlay/marker/export/pip/shotml state into fresh projects"
        in matrix
    )
    assert (
        "landing pane and reopen-last-tool defaults across reload and project switching" in matrix
    )
    assert "app-vs-folder settings scope separation without cross-scope rewrites" in matrix
    assert "metrics stage story graphs and scoring-context truth" in matrix
    assert "metrics CSV/Text export downloads for the current context" in matrix
    assert "section collapse state within a live session" in matrix
    assert "layout capture/release defaults" in matrix
    assert "visible analyze or re-run beep-sync action" in matrix
    assert "CI artifact export proof from `docs/Clip1.MP4`" in matrix
    assert "DEV-106.landing_recent" in matrix
    assert "DEV-107.root_shell_compat" in matrix
    assert "project.practiscore_bridge" in matrix

    interaction_section = matrix.split(interaction_heading, 1)[1].split(settings_heading, 1)[0]
    settings_section = matrix.split(settings_heading, 1)[1].split(metrics_heading, 1)[0]
    metrics_section = matrix.split(metrics_heading, 1)[1]

    for snippet in [
        "metrics pane row propagation",
        "timing-event metrics ordering",
        "settings defaults seeding overlay/marker/export/pip/shotml state into fresh projects",
        "settings save-current and section-reset actions for scoring, pip, overlay, markers, export, and ShotML defaults",
        "landing pane and reopen-last-tool defaults across reload and project switching",
        "app-vs-folder settings scope separation without cross-scope rewrites",
        "metrics workbench expand/collapse shell state",
        "metrics stage story graphs and scoring-context truth",
        "metrics CSV/Text export downloads for the current context",
        "section collapse state within a live session",
        "layout capture/release defaults",
    ]:
        assert snippet not in interaction_section

    for snippet in [
        "settings defaults seeding overlay/marker/export/pip/shotml state into fresh projects",
        "settings save-current and section-reset actions for scoring, pip, overlay, markers, export, and ShotML defaults",
        "landing pane and reopen-last-tool defaults across reload and project switching",
        "app-vs-folder settings scope separation without cross-scope rewrites",
        "section collapse state within a live session",
        "layout capture/release defaults; rendered layout field values remain state assertions rather than live interaction owners",
    ]:
        assert snippet in settings_section

    for snippet in [
        "metrics pane row propagation",
        "timing-event metrics ordering",
        "metrics workbench expand/collapse shell state",
        "metrics stage story graphs and scoring-context truth",
        "metrics CSV/Text export downloads for the current context",
    ]:
        assert snippet in metrics_section

    assert "support_target_exceptions" in matrix
    assert "state-led" in matrix

    for test_path in [
        "tests/browser/test_browser_static_ui.py",
        "tests/browser/test_browser_control.py",
        "tests/browser/test_landing_page.py",
        "tests/browser/test_landing_backend_routes.py",
        "tests/browser/test_automation_ui_shell_contracts.py",
        "tests/browser/test_browser_rail_layout.py",
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
        "Landing",
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

    assert "`match.recap` is `control-led`" in matrix
    assert "`settings.section_visibility`" in matrix
    assert "`metrics.row_propagation`" in matrix
    assert "`metrics.stage_story`" in matrix
    assert "`metrics.scoring_context`" in matrix
    assert "`recap-select-all`" in matrix
    assert "`recap-render`" in matrix


def test_wave_a_guide_and_browser_matrix_tables_match_the_manifest_rows() -> None:
    guide = Path("docs/tests/TEST_SUITE_GUIDE.md").read_text(encoding="utf-8")
    matrix = Path("docs/project/browser-control-qa-matrix.md").read_text(encoding="utf-8")
    manifest_rows = _manifest_rows()
    support_surface_rows = _support_surface_rows()

    guide_rows = {
        row["Pane ID"].strip("`").strip(): {
            "pane_test_id": row["`TAX-1` record"].strip("`").strip(),
            "feature_ids": _split_inline_list(row["`TAX-0` feature IDs"]),
            "runner_suites": _split_inline_list(row["Current runner surfaces"]),
        }
        for row in _parse_markdown_table(guide, "## Current pane manifest foundation")
    }
    matrix_rows = {
        row["Pane ID"].strip("`").strip(): {
            "pane_test_id": row["`TAX-1` record"].strip("`").strip(),
            "feature_ids": _split_inline_list(row["`TAX-0` feature IDs"]),
            "runner_suites": _split_inline_list(row["Current runner support"]),
        }
        for row in _parse_markdown_table(matrix, "## Pane manifest references")
    }
    guide_support_rows = {
        row["Support surface ID"].strip("`").strip(): {
            "support_role": row["Support role"].strip(),
            "feature_ids": _split_inline_list(row["`TAX-0` feature IDs"]),
            "runner_suites": _split_inline_list(row["Current runner surfaces"]),
        }
        for row in _parse_markdown_table(guide, "## Current support surface extension")
    }
    matrix_support_rows = {
        row["Support surface ID"].strip("`").strip(): {
            "support_role": row["Support role"].strip(),
            "feature_ids": _split_inline_list(row["`TAX-0` feature IDs"]),
            "runner_suites": _split_inline_list(row["Current runner support"]),
        }
        for row in _parse_markdown_table(matrix, "## Support surface manifests")
    }

    assert set(guide_rows) == set(manifest_rows)
    assert set(matrix_rows) == set(manifest_rows)
    assert set(guide_support_rows) == set(support_surface_rows)
    assert set(matrix_support_rows) == set(support_surface_rows)
    for pane_id, manifest_row in manifest_rows.items():
        assert guide_rows[pane_id] == manifest_row
        assert matrix_rows[pane_id] == manifest_row
    for surface_id, manifest_row in support_surface_rows.items():
        assert guide_support_rows[surface_id] == manifest_row
        assert matrix_support_rows[surface_id] == manifest_row


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
    assert "docs/project/development/completion-bundles/development/proof.md" in landing["doc_refs"]
    assert "docs/project/browser-control-qa-matrix.md" in landing["doc_refs"]
    assert landing["manifest_ref"] == "scripts/testing/pane_feature_manifests.json"
    assert landing["support_surface_ids"] == ["surface.landing"]

    assert compat["status"] == "interaction-proven"
    assert compat["proof_strength"] == "compat-static-contract + guarded interaction consumers"
    assert (
        "tests/browser/test_browser_interactions.py::test_shell_compat_host_on_open_project_callback_opens_saved_project"
        in compat["evidence_tests"]
    )
    assert "docs/project/development/completion-bundles/development/proof.md" in compat["doc_refs"]
    assert (
        "docs/project/development/completion-bundles/development/match-reference.md"
        in compat["doc_refs"]
    )
    assert compat["manifest_ref"] == "scripts/testing/pane_feature_manifests.json"
    assert compat["pane_ids"] == ["pane.match", "pane.performance"]
    assert compat["support_surface_ids"] == ["surface.shared_shell"]
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
    assert practiscore["manifest_ref"] == "scripts/testing/pane_feature_manifests.json"
    assert practiscore["pane_ids"] == ["pane.project"]
    assert (
        "docs/project/development/completion-bundles/development/stage-reference.md"
        in practiscore["doc_refs"]
    )
    assert "tests/browser/test_practiscore_session_api.py" in practiscore["evidence_tests"]
    assert "tax0.project.practiscore_import" in practiscore["taxonomy_note"]

    for seam in SEAM_REGISTRY.values():
        _assert_relative_repo_files_exist(list(seam.get("doc_refs", [])))
        manifest_ref = seam.get("manifest_ref")
        if isinstance(manifest_ref, str):
            assert Path(manifest_ref).is_file()


def test_development_proof_docs_capture_mixed_family_taxonomy_and_honesty_caveats() -> None:
    spec = Path("docs/project/development/Testing/spec.md").read_text(encoding="utf-8")
    guide = Path("docs/tests/TEST_SUITE_GUIDE.md").read_text(encoding="utf-8")
    matrix = Path("docs/project/browser-control-qa-matrix.md").read_text(encoding="utf-8")
    coverage_plan = Path("docs/project/browser-control-coverage-plan.md").read_text(
        encoding="utf-8"
    )
    full_e2e_plan = Path("docs/project/browser-full-e2e-qa-plan.md").read_text(encoding="utf-8")

    assert "scripts/testing/pane_feature_manifests.json" in guide
    assert "scripts/testing/pane_feature_manifests.json" in matrix
    assert "scripts/testing/pane_feature_manifests.json" in coverage_plan
    assert "scripts/testing/pane_feature_manifests.json" in full_e2e_plan
    assert "surface.landing" in guide
    assert "surface.landing" in matrix
    assert "surface.landing" in coverage_plan
    assert "surface.landing" in full_e2e_plan
    assert "surface.shared_shell" in guide
    assert "surface.shared_shell" in matrix
    assert "surface.shared_shell" in coverage_plan
    assert "surface.shared_shell" in full_e2e_plan
    assert "surface.stage.compose" in guide
    assert "surface.stage.compose" in matrix
    assert "surface.stage.compose" in coverage_plan
    assert "surface.stage.compose" in full_e2e_plan
    assert "support_surface_ids" in guide
    assert "support_surface_ids" in matrix
    assert "support_surface_ids" in coverage_plan
    assert "DEV-106.landing_recent" in matrix
    assert "DEV-107.root_shell_compat" in matrix
    assert "project.practiscore_bridge" in matrix
    assert "support_target_exceptions" in guide
    assert "state-led" in guide
    assert "Landing support surface only; not a first-class pane or view closure record." in guide
    assert "Landing support surface only; not a first-class pane or view closure record." in matrix
    assert (
        "Shared-shell support surface only; not a first-class pane or view closure record." in guide
    )
    assert (
        "Shared-shell support surface only; not a first-class pane or view closure record."
        in matrix
    )
    assert (
        "Stage-tool support surface only; not a first-class pane or view closure record." in guide
    )
    assert (
        "Stage-tool support surface only; not a first-class pane or view closure record." in matrix
    )
    assert "`match.recap` is `audit_model: control-led`" in guide
    assert "`settings.section_visibility`" in guide
    assert "`metrics.row_propagation`" in guide
    assert "`metrics.stage_story`" in guide
    assert "`metrics.scoring_context`" in guide
    assert "`match.recap` is `control-led`" in coverage_plan
    assert (
        "Project, Match, Performance, Settings, and Metrics now have first-class machine-readable manifests"
        in spec
    )
    assert "supporting seam only; never a standalone TAX-0..TAX-5 closeout" in json.dumps(
        SEAM_REGISTRY,
        sort_keys=True,
    )
