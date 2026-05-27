from __future__ import annotations

import ast
import json
from pathlib import Path


PANE_MANIFEST = Path("scripts/testing/pane_feature_manifests.json")
SUITE_TAXONOMY = Path("scripts/testing/test_suite_taxonomy.json")
GENERIC_SHARED_SUPPORT_SELECTORS = {
    ".lock-button",
    ".timing-adjustment-input",
    ".restore-button",
    ".danger-button",
}


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _defined_test_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
    }


def _defined_test_sources(path: Path) -> dict[str, str]:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    tree = ast.parse(source, filename=str(path))
    return {
        node.name: "\n".join(lines[node.lineno - 1 : node.end_lineno])
        for node in ast.walk(tree)
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
    }


def test_pane_manifest_foundation_covers_project_match_performance_settings_metrics_and_stage_support_surfaces() -> None:
    payload = _load_json(PANE_MANIFEST)

    assert payload["version"] == 1
    assert payload["wave_id"] == "tax-0-tax-1-wave-a"
    assert payload["status"] == "foundation"
    assert payload["feature_audit_models"] == {
        "control-led": {
            "description": "Use when a feature has explicit browser control identifiers that must stay mapped to the pane inventory.",
            "requires_control_ids": True,
            "requires_state_values": False,
        },
        "state-led": {
            "description": "Use when a feature is audited through required state, status, or result assertions instead of pane-owned control identifiers.",
            "requires_control_ids": False,
            "requires_state_values": True,
            "notes": "State-led features remain first-class TAX-0 rows. Empty control_ids are intentional only when the manifest makes the state/result assertions explicit.",
        },
    }

    panes = {pane["pane_id"]: pane for pane in payload["panes"]}
    support_surfaces = {
        surface["surface_id"]: surface for surface in payload["support_surfaces"]
    }
    assert set(panes) == {
        "pane.project",
        "pane.match",
        "pane.performance",
        "pane.settings",
        "pane.metrics",
    }
    assert set(support_surfaces) == {
        "surface.stage.compose",
        "surface.stage.scoring",
        "surface.stage.splits_waveform",
        "surface.stage.markers_review_overlay",
        "surface.stage.export",
        "surface.stage.shotml",
    }

    expected = {
        "pane.project": ("pane-project", "project."),
        "pane.match": ("pane-match", "match."),
        "pane.performance": ("pane-performance", "performance."),
        "pane.settings": ("pane-settings", "settings."),
        "pane.metrics": ("pane-metrics", "metrics."),
    }
    for pane_id, (suite_name, feature_prefix) in expected.items():
        pane = panes[pane_id]
        assert pane["taxonomy_class"] == "TAX-1"
        assert pane["pane_test_id"].startswith("tax1.")
        assert suite_name in pane["runner_suites"]
        assert "scripts/testing/test_suite_taxonomy.json" in pane["taxonomy_surfaces"]
        assert "docs/tests/TEST_SUITE_GUIDE.md" in pane["doc_refs"]
        assert pane["feature_id_prefix"] == feature_prefix
        for feature in pane["features"]:
            assert feature["taxonomy_class"] == "TAX-0"
            assert feature["test_id"].startswith("tax0.")
            assert feature["feature_id"].startswith(feature_prefix)
            assert feature["audit_model"] in payload["feature_audit_models"]
            assert feature["control_ids"] or feature["state_values"]
            assert feature["inventory_terms"]
            if feature["audit_model"] == "control-led":
                assert feature["control_ids"]
            if feature["audit_model"] == "state-led":
                assert not feature["control_ids"]
                assert feature["state_values"]

    project_practiscore = next(
        feature
        for feature in panes["pane.project"]["features"]
        if feature["feature_id"] == "project.practiscore_import"
    )
    assert project_practiscore["browser_contract_keys"] == [
        "practiscore_session",
        "practiscore_sync",
        "practiscore_options",
    ]
    assert {
        "open-practiscore-dashboard",
        "import-practiscore",
        "match-type",
        "match-stage-number",
        "match-competitor-name",
        "match-competitor-place",
    }.issubset(set(project_practiscore["control_ids"]))
    assert "project.practiscore_bridge" in panes["pane.project"]["proof_seams"]

    assert {feature["feature_id"] for feature in panes["pane.match"]["features"]} == {
        "match.workspace_lifecycle",
        "match.setup_once_and_defaults",
        "match.stage_navigation_shell",
        "match.composite_editor",
        "match.recap",
        "match.batch_export",
        "match.settings",
    }
    assert {feature["feature_id"] for feature in panes["pane.performance"]["features"]} == {
        "performance.overview",
        "performance.records_filtering",
        "performance.record_detail_actions",
        "performance.analytics",
        "performance.backup_and_export",
        "performance.settings",
    }
    assert {feature["feature_id"] for feature in panes["pane.settings"]["features"]} == {
        "settings.global_template_scope",
        "settings.layout_defaults",
        "settings.scoring_and_compose_defaults",
        "settings.overlay_and_marker_defaults",
        "settings.export_and_shotml_defaults",
        "settings.section_visibility",
    }
    assert {feature["feature_id"] for feature in panes["pane.metrics"]["features"]} == {
        "metrics.summary_and_workbench",
        "metrics.row_propagation",
        "metrics.stage_story",
        "metrics.scoring_context",
        "metrics.export",
    }
    layout_defaults = next(
        feature
        for feature in panes["pane.settings"]["features"]
        if feature["feature_id"] == "settings.layout_defaults"
    )
    assert layout_defaults["audit_model"] == "control-led"
    assert layout_defaults["control_ids"] == [
        "settings-use-current-layout",
        "settings-release-layout",
    ]
    assert {
        "saved layout defaults",
        "released layout defaults",
        "rendered layout status and summary state",
    }.issubset(set(layout_defaults["state_values"]))
    match_recap = next(
        feature
        for feature in panes["pane.match"]["features"]
        if feature["feature_id"] == "match.recap"
    )
    assert match_recap["audit_model"] == "control-led"
    assert {
        "recap-select-all",
        "recap-select-none",
        ".recap-stage-check",
        "[data-stage-move]",
        ".recap-stage-subtitle",
        ".recap-stage-gain",
        ".recap-stage-mute",
        "recap-transition",
        "recap-result-card",
        "recap-render",
    }.issubset(set(match_recap["control_ids"]))
    assert {
        "selected recap stages",
        "recap stage order",
        "per-stage subtitle/audio options",
        "transition configuration",
        "result-card configuration",
        "recap success and error state",
    }.issubset(set(match_recap["state_values"]))
    assert {
        feature["feature_id"]
        for pane in panes.values()
        for feature in pane["features"]
        if feature["audit_model"] == "state-led"
    } == {
        "performance.overview",
        "performance.analytics",
        "settings.section_visibility",
        "metrics.row_propagation",
        "metrics.stage_story",
        "metrics.scoring_context",
    }

    for surface_id, feature_prefix in {
        "surface.stage.compose": "stage.compose.",
        "surface.stage.scoring": "stage.scoring.",
        "surface.stage.splits_waveform": "stage.splits_waveform.",
        "surface.stage.markers_review_overlay": "stage.markers_review_overlay.",
        "surface.stage.export": "stage.export.",
        "surface.stage.shotml": "stage.shotml.",
    }.items():
        surface = support_surfaces[surface_id]
        assert surface["support_kind"] == "stage-tool-support"
        assert surface["support_only"] is True
        assert surface["runner_suites"] == ["browser"]
        assert surface["feature_id_prefix"] == feature_prefix
        assert surface["support_note"] == (
            "Stage-tool support surface only; not a first-class pane or view closure record."
        )
        assert surface["owner_targets"]
        assert "scripts/testing/test_suite_taxonomy.json" in surface["taxonomy_surfaces"]
        assert "docs/tests/TEST_SUITE_GUIDE.md" in surface["doc_refs"]
        assert surface["taxonomy_support"]
        for feature in surface["features"]:
            assert feature["taxonomy_class"] == "TAX-0"
            assert feature["test_id"].startswith("tax0.")
            assert feature["feature_id"].startswith(feature_prefix)
            assert feature["audit_model"] in payload["feature_audit_models"]
            assert feature["control_ids"] or feature["state_values"]
            assert feature["inventory_terms"]
            if feature["audit_model"] == "control-led":
                assert feature["control_ids"]
            if feature["audit_model"] == "state-led":
                assert not feature["control_ids"]
                assert feature["state_values"]

    assert {
        feature["feature_id"]
        for surface in support_surfaces.values()
        for feature in surface["features"]
    } == {
        "stage.compose.defaults_and_media",
        "stage.compose.per_source_authoring",
        "stage.compose.secondary_waveform_sync",
        "stage.scoring.enablement_and_preset",
        "stage.scoring.summary_and_editing",
        "stage.splits_waveform.summary_and_workbench",
        "stage.splits_waveform.waveform_navigation",
        "stage.splits_waveform.split_row_editing",
        "stage.markers_review_overlay.marker_authoring",
        "stage.markers_review_overlay.review_boxes_and_visibility",
        "stage.markers_review_overlay.overlay_styling_and_positioning",
        "stage.export.render_settings",
        "stage.export.output_profiles_and_hooks",
        "stage.export.log_and_artifact_output",
        "stage.shotml.threshold_and_defaults",
        "stage.shotml.detector_settings",
        "stage.shotml.proposals_and_section_persistence",
    }
    compose_secondary_waveform = next(
        feature
        for feature in support_surfaces["surface.stage.compose"]["features"]
        if feature["feature_id"] == "stage.compose.secondary_waveform_sync"
    )
    assert compose_secondary_waveform["audit_model"] == "state-led"
    assert compose_secondary_waveform["state_values"] == [
        "beep-sync analysis status",
        "secondary waveform visibility",
        "secondary waveform lane layout",
        "secondary preview sync state",
    ]
    scoring_enablement = next(
        feature
        for feature in support_surfaces["surface.stage.scoring"]["features"]
        if feature["feature_id"] == "stage.scoring.enablement_and_preset"
    )
    assert scoring_enablement["audit_model"] == "control-led"
    assert scoring_enablement["control_ids"] == [
        "scoring-enabled",
        "scoring-preset",
        "expand-scoring",
        "collapse-scoring",
    ]
    splits_waveform_navigation = next(
        feature
        for feature in support_surfaces["surface.stage.splits_waveform"]["features"]
        if feature["feature_id"] == "stage.splits_waveform.waveform_navigation"
    )
    assert {
        "expand-waveform",
        "zoom-waveform-in",
        "zoom-waveform-out",
        "amp-waveform-in",
        "amp-waveform-out",
        "reset-waveform-view",
        "waveform-mode-single",
        "waveform-mode-multi",
    }.issubset(set(splits_waveform_navigation["control_ids"]))
    split_row_editing = next(
        feature
        for feature in support_surfaces["surface.stage.splits_waveform"]["features"]
        if feature["feature_id"] == "stage.splits_waveform.split_row_editing"
    )
    assert split_row_editing["control_ids"] == [
        '#timing-workbench-table [data-timing-row-action="toggle-edit"]',
        '#timing-workbench-table [data-timing-row-field="adjustment-seconds"]',
        '#timing-workbench-table [data-timing-row-action="restore-shot"]',
        '#timing-workbench-table [data-timing-row-action="delete-shot"]',
    ]
    marker_authoring = next(
        feature
        for feature in support_surfaces["surface.stage.markers_review_overlay"]["features"]
        if feature["feature_id"] == "stage.markers_review_overlay.marker_authoring"
    )
    assert {
        "markers-enable",
        "popup-edit-selected",
        "popup-add-bubble",
        "popup-add-bubble-workbench",
        "popup-add-selected-shot-workbench",
        "popup-import-shots-workbench",
        "markers-workbench-filter",
        "popup-prev-workbench",
        "popup-next-workbench",
    }.issubset(set(marker_authoring["control_ids"]))
    export_render_settings = next(
        feature
        for feature in support_surfaces["surface.stage.export"]["features"]
        if feature["feature_id"] == "stage.export.render_settings"
    )
    assert {
        "export-preset",
        "quality",
        "aspect-ratio",
        "frame-rate",
        "video-codec",
        "audio-codec",
        "color-space",
        "ffmpeg-preset",
        "two-pass",
        "export-path",
        "browse-export-path",
        "export-video",
    }.issubset(set(export_render_settings["control_ids"]))
    shotml_threshold = next(
        feature
        for feature in support_surfaces["surface.stage.shotml"]["features"]
        if feature["feature_id"] == "stage.shotml.threshold_and_defaults"
    )
    assert shotml_threshold["control_ids"] == [
        "apply-threshold",
        "reset-shotml-defaults",
        "threshold",
    ]


def test_support_surface_owner_targets_resolve_to_real_files_or_tests() -> None:
    payload = _load_json(PANE_MANIFEST)

    for surface in payload["support_surfaces"]:
        for owner_target in surface["owner_targets"]:
            file_target, _, test_target = owner_target.partition("::")
            path = Path(file_target)
            assert path.is_file(), f"Missing owner target file for {surface['surface_id']}: {owner_target}"
            if not test_target:
                continue
            test_name = test_target.split("[", 1)[0]
            assert test_name in _defined_test_names(path), (
                f"Missing owner target test for {surface['surface_id']}: {owner_target}"
            )


def test_stage_support_owner_targets_cover_repaired_handoffs_and_context_claims() -> None:
    support_surfaces = {
        surface["surface_id"]: set(surface["owner_targets"])
        for surface in _load_json(PANE_MANIFEST)["support_surfaces"]
    }

    assert {
        "tests/browser/test_browser_static_ui.py::test_browser_automation_surface_scopes_profiles_and_saves_hooks",
        "tests/browser/test_browser_interactions.py::test_compose_pane_trim_dead_time_uses_output_profile_editor",
    }.issubset(support_surfaces["surface.stage.compose"])
    assert {
        "tests/browser/test_scoring_metrics_contracts.py::test_browser_state_refreshes_imported_stage_context_for_metrics_consumers",
        "tests/browser/test_scoring_metrics_contracts.py::test_static_scoring_pane_extracts_owned_scoring_blocks_into_module",
    }.issubset(support_surfaces["surface.stage.scoring"])
    assert {
        "tests/browser/test_browser_static_ui.py::test_browser_automation_surface_scopes_profiles_and_saves_hooks",
        "tests/browser/test_browser_interactions.py::test_project_pane_output_hook_save_updates_selected_output_profile",
        "tests/browser/test_browser_review_owner_targets.py::test_review_source_controls_apply_selected_output_profile_render_plan",
    }.issubset(support_surfaces["surface.stage.markers_review_overlay"])
    assert {
        "tests/browser/test_browser_static_ui.py::test_browser_automation_surface_scopes_profiles_and_saves_hooks",
        "tests/browser/test_browser_interactions.py::test_export_pane_frame_profile_output_hook_persists_selected_profile",
    }.issubset(support_surfaces["surface.stage.export"])


def test_support_surface_control_owner_targets_resolve_to_real_owner_tests() -> None:
    payload = _load_json(PANE_MANIFEST)

    for surface in payload["support_surfaces"]:
        surface_owner_targets = set(surface["owner_targets"])
        for feature in surface["features"]:
            control_owner_targets = feature.get("control_owner_targets", {})
            assert set(control_owner_targets).issubset(set(feature["control_ids"]))
            for control_id, owner_targets in control_owner_targets.items():
                assert owner_targets, (
                    f"Missing owner targets for {feature['feature_id']} control {control_id}"
                )
                for owner_target in owner_targets:
                    assert owner_target in surface_owner_targets, (
                        f"Control owner target not listed on {surface['surface_id']}: {owner_target}"
                    )
                    file_target, _, test_target = owner_target.partition("::")
                    assert test_target, (
                        f"Control owner target must reference a concrete test: {owner_target}"
                    )
                    path = Path(file_target)
                    sources = _defined_test_sources(path)
                    test_name = test_target.split("[", 1)[0]
                    assert test_name in sources, (
                        f"Missing control owner target test for {surface['surface_id']}: {owner_target}"
                    )
                    assert control_id in sources[test_name], (
                        f"Control owner target does not mention {control_id}: {owner_target}"
                    )


def test_current_wave_thin_support_controls_have_explicit_owner_targets() -> None:
    support_surfaces = {
        surface["surface_id"]: surface for surface in _load_json(PANE_MANIFEST)["support_surfaces"]
    }

    compose_defaults = next(
        feature
        for feature in support_surfaces["surface.stage.compose"]["features"]
        if feature["feature_id"] == "stage.compose.defaults_and_media"
    )
    assert compose_defaults["control_owner_targets"]["add-merge-media"] == [
        "tests/browser/test_browser_remaining_controls_e2e.py::test_merge_remaining_controls_commit_default_and_per_source_state"
    ]

    waveform_navigation = next(
        feature
        for feature in support_surfaces["surface.stage.splits_waveform"]["features"]
        if feature["feature_id"] == "stage.splits_waveform.waveform_navigation"
    )
    assert waveform_navigation["control_owner_targets"]["waveform-mode-single"] == [
        "tests/browser/test_browser_remaining_controls_e2e.py::test_waveform_shell_remaining_controls_and_workbench_toggles_survive_routes"
    ]
    assert waveform_navigation["control_owner_targets"]["waveform-mode-multi"] == [
        "tests/browser/test_browser_remaining_controls_e2e.py::test_waveform_shell_remaining_controls_and_workbench_toggles_survive_routes"
    ]

    review_visibility = next(
        feature
        for feature in support_surfaces["surface.stage.markers_review_overlay"]["features"]
        if feature["feature_id"] == "stage.markers_review_overlay.review_boxes_and_visibility"
    )
    assert review_visibility["control_owner_targets"]["retained-review-source"] == [
        "tests/browser/test_browser_review_owner_targets.py::test_review_source_controls_apply_selected_output_profile_render_plan"
    ]
    assert review_visibility["control_owner_targets"]["retained-review-apply"] == [
        "tests/browser/test_browser_review_owner_targets.py::test_review_source_controls_apply_selected_output_profile_render_plan"
    ]


def test_stage_support_control_led_rows_avoid_known_generic_shared_selectors() -> None:
    payload = _load_json(PANE_MANIFEST)
    flagged: dict[str, list[str]] = {}

    for surface in payload["support_surfaces"]:
        for feature in surface["features"]:
            if feature["audit_model"] != "control-led":
                continue
            generic_controls = sorted(
                set(feature["control_ids"]) & GENERIC_SHARED_SUPPORT_SELECTORS
            )
            if generic_controls:
                flagged[feature["feature_id"]] = generic_controls

    assert not flagged, f"Support-surface control rows still use generic shared selectors: {flagged}"


def test_suite_taxonomy_pane_manifest_refs_match_the_pane_manifest_file() -> None:
    suites = {
        suite["name"]: suite for suite in _load_json(SUITE_TAXONOMY)["suites"]
    }
    panes = {
        pane["pane_id"] for pane in _load_json(PANE_MANIFEST)["panes"]
    }
    support_surfaces = {
        surface["surface_id"]
        for surface in _load_json(PANE_MANIFEST)["support_surfaces"]
    }

    expected = {
        "pane-project": "pane.project",
        "pane-match": "pane.match",
        "pane-performance": "pane.performance",
        "pane-settings": "pane.settings",
        "pane-metrics": "pane.metrics",
    }
    for suite_name, pane_id in expected.items():
        suite = suites[suite_name]
        assert suite["taxonomy_support"] == ["TAX-0", "TAX-1"]
        assert suite["pane_ids"] == [pane_id]
        assert suite["pane_manifest_refs"] == ["scripts/testing/pane_feature_manifests.json"]
        assert pane_id in panes

    assert suites["browser"]["support_surface_ids"] == [
        "surface.stage.compose",
        "surface.stage.scoring",
        "surface.stage.splits_waveform",
        "surface.stage.markers_review_overlay",
        "surface.stage.export",
        "surface.stage.shotml",
    ]
    assert suites["browser"]["support_manifest_refs"] == [
        "scripts/testing/pane_feature_manifests.json"
    ]
    assert set(suites["browser"]["support_surface_ids"]) == support_surfaces


def test_pane_project_suite_declares_explicit_landing_support_exceptions() -> None:
    pane_project = {
        suite["name"]: suite for suite in _load_json(SUITE_TAXONOMY)["suites"]
    }["pane-project"]

    exceptions = pane_project["support_target_exceptions"]
    assert {entry["target"] for entry in exceptions} == {
        "tests/browser/test_landing_page.py",
        "tests/browser/test_landing_backend_routes.py",
        "tests/browser/test_browser_interactions.py::test_landing_and_stage_empty_primary_import_buttons_work_without_saved_project",
        "tests/browser/test_browser_interactions.py::test_landing_recent_stage_rows_switch_surface_without_auto_open",
    }
    assert {entry["surface_id"] for entry in exceptions} == {"surface.landing"}
    assert any(
        entry["related_feature_ids"] == ["project.primary_video_import"]
        for entry in exceptions
    )
    assert all(entry["reason"] for entry in exceptions)


def test_wave_a_docs_reference_the_manifest_surface() -> None:
    for path in [
        Path("docs/project/development/Testing/README.md"),
        Path("docs/project/development/Testing/spec.md"),
        Path("docs/project/development/Testing/plan.md"),
        Path("docs/project/development/Testing/tasks.md"),
        Path("docs/project/development/Testing/artifacts.md"),
        Path("docs/tests/TEST_SUITE_GUIDE.md"),
        Path("docs/project/browser-control-qa-matrix.md"),
        Path("docs/project/browser-control-coverage-plan.md"),
        Path("docs/project/browser-full-e2e-qa-plan.md"),
    ]:
        assert "scripts/testing/pane_feature_manifests.json" in path.read_text(
            encoding="utf-8"
        )