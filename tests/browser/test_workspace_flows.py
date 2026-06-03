from __future__ import annotations


import pytest

from splitshot.domain.models import (
    AspectRatio,
    ExportPreset,
    ExportQuality,
    MatchWorkspace,
    OverlayPosition,
    StageEntry,
    VideoAsset,
)
import splitshot.ui.controller as controller_module
from splitshot.ui.controller import ProjectController


@pytest.fixture
def controller():
    """Return a fresh ProjectController."""
    return ProjectController()


@pytest.fixture
def controller_with_workspace(controller, tmp_path):
    """Return a controller with a saved workspace containing stages."""
    controller.new_workspace()
    controller.workspace.name = "Test Match"
    controller.workspace.description = "A test match workspace"

    # Add stages
    controller.workspace_add_stage("stage_1", "Bay 1", "")
    controller.workspace_add_stage("stage_2", "Bay 2", "")
    controller.workspace_add_stage("stage_3", "Bay 3", "")

    # Save workspace
    ws_path = tmp_path / "test_match"
    controller.save_workspace(str(ws_path))

    return controller


def _build_workspace_with_stage_profiles(controller: ProjectController, workspace_path) -> None:
    controller.new_workspace()
    controller.workspace.name = "Stage Bundle"
    controller.workspace.description = "Workspace apply-from-first proof"
    controller.workspace_add_stage("stage_1", "Stage 1")
    controller.workspace_add_stage("stage_2", "Stage 2")
    controller.workspace.stage_entries["stage_1"].source_media_present = True
    controller.workspace.stage_entries["stage_2"].source_media_present = True
    controller.save_workspace(str(workspace_path))

    controller.new_project()
    controller.project.export.preset = ExportPreset.YOUTUBE_LONG_1080P
    controller.project.export.aspect_ratio = AspectRatio.LANDSCAPE
    controller.project.export.quality = ExportQuality.MEDIUM
    controller.project.overlay.position = OverlayPosition.TOP
    controller.project.overlay.show_timer = True
    controller.project.overlay.show_score = False
    assert controller._save_stage_project("stage_1", controller.project) is True

    controller.new_project()
    controller.project.export.preset = ExportPreset.SOURCE
    controller.project.export.aspect_ratio = AspectRatio.ORIGINAL
    controller.project.export.quality = ExportQuality.HIGH
    controller.project.overlay.position = OverlayPosition.BOTTOM
    controller.project.overlay.show_timer = False
    controller.project.overlay.show_score = True
    assert controller._save_stage_project("stage_2", controller.project) is True

    controller.output_profile_create(
        "stage",
        "stage_1",
        "Stage Output",
        "stage_output",
        frame_profile="16:9",
        metric_caption_preset={
            "preset": "score",
            "enabled_fields": ["time", "score", "hit_factor"],
            "position": "bottom_right",
            "lead_in_padding_ms": 1100,
            "tail_padding_ms": 2200,
        },
        lead_in_card={"style": "stage_info", "duration_s": 2.5},
        brand_mark={"style": "splitshot", "text": "SplitShot", "duration_s": 1.2},
        subject_track_crop={"enabled": True, "margin_percent": 12},
    )

    controller.workspace_set_stage_override(
        "stage_2",
        {
            "frame_profile": "1:1",
            "metric_caption_preset": "splits",
            "lead_in_card": "competitor",
            "brand_mark": "splitshot",
        },
    )
    controller.save_workspace()


def test_workspace_controller_methods_delegate_to_workspace_service(monkeypatch, tmp_path) -> None:
    import splitshot.ui.services.workspace_service as workspace_service_module

    controller = ProjectController()
    expected_open_error = {"reason": "delegated"}
    expected_reset_result = {"reset": True}
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        workspace_service_module,
        "new_workspace",
        lambda passed_controller, eligible_fields: calls.append(
            ("new_workspace", passed_controller, eligible_fields)
        ),
    )
    monkeypatch.setattr(
        workspace_service_module,
        "save_workspace",
        lambda passed_controller, path=None: calls.append(
            ("save_workspace", passed_controller, path)
        ),
    )
    monkeypatch.setattr(
        workspace_service_module,
        "open_workspace",
        lambda passed_controller, path: calls.append(("open_workspace", passed_controller, path)),
    )
    monkeypatch.setattr(
        workspace_service_module,
        "workspace_add_stage",
        lambda passed_controller, stage_id, display_name="", project_path="": calls.append(
            ("workspace_add_stage", passed_controller, stage_id, display_name, project_path)
        ),
    )
    monkeypatch.setattr(
        workspace_service_module,
        "workspace_remove_stage",
        lambda passed_controller, stage_id: calls.append(
            ("workspace_remove_stage", passed_controller, stage_id)
        ),
    )
    monkeypatch.setattr(
        workspace_service_module,
        "workspace_open_stage",
        lambda passed_controller, stage_id: (
            calls.append(("workspace_open_stage", passed_controller, stage_id))
            or expected_open_error
        ),
    )
    monkeypatch.setattr(
        workspace_service_module,
        "workspace_return_to_workspace",
        lambda passed_controller: calls.append(
            ("workspace_return_to_workspace", passed_controller)
        ),
    )
    monkeypatch.setattr(
        workspace_service_module,
        "workspace_set_defaults",
        lambda passed_controller, payload, eligible_fields: calls.append(
            ("workspace_set_defaults", passed_controller, payload, eligible_fields)
        ),
    )
    monkeypatch.setattr(
        workspace_service_module,
        "workspace_set_stage_override",
        lambda passed_controller, stage_id, payload, eligible_fields: calls.append(
            ("workspace_set_stage_override", passed_controller, stage_id, payload, eligible_fields)
        ),
    )
    monkeypatch.setattr(
        workspace_service_module,
        "workspace_reset_stage_override",
        lambda passed_controller, stage_id, keys=None: calls.append(
            ("workspace_reset_stage_override", passed_controller, stage_id, keys)
        ),
    )
    monkeypatch.setattr(
        workspace_service_module,
        "workspace_reset_defaults",
        lambda passed_controller: (
            calls.append(("workspace_reset_defaults", passed_controller)) or expected_reset_result
        ),
    )

    controller.new_workspace()
    controller.save_workspace(str(tmp_path / "delegated-workspace"))
    controller.open_workspace(str(tmp_path / "delegated-workspace"))
    controller.workspace_add_stage("stage_1", "Stage 1", "")
    controller.workspace_remove_stage("stage_1")
    assert controller.workspace_open_stage("stage_1") == expected_open_error
    controller.workspace_return_to_workspace()
    controller.workspace_set_defaults({"frame_profile": "16:9"})
    controller.workspace_set_stage_override("stage_1", {"frame_profile": "9:16"})
    controller.workspace_reset_stage_override("stage_1", ["frame_profile"])
    assert controller.workspace_reset_defaults() == expected_reset_result

    assert calls[0][0] == "new_workspace"
    assert calls[0][1] is controller
    assert "frame_profile" in calls[0][2]
    assert calls[1] == ("save_workspace", controller, str(tmp_path / "delegated-workspace"))
    assert calls[2] == ("open_workspace", controller, str(tmp_path / "delegated-workspace"))
    assert calls[3] == ("workspace_add_stage", controller, "stage_1", "Stage 1", "")
    assert calls[4] == ("workspace_remove_stage", controller, "stage_1")
    assert calls[5] == ("workspace_open_stage", controller, "stage_1")
    assert calls[6] == ("workspace_return_to_workspace", controller)
    assert calls[7][0] == "workspace_set_defaults"
    assert calls[7][1] is controller
    assert calls[7][2] == {"frame_profile": "16:9"}
    assert "frame_profile" in calls[7][3]
    assert calls[8][0] == "workspace_set_stage_override"
    assert calls[8][1] is controller
    assert calls[8][2] == "stage_1"
    assert calls[8][3] == {"frame_profile": "9:16"}
    assert "frame_profile" in calls[8][4]
    assert calls[9] == ("workspace_reset_stage_override", controller, "stage_1", ["frame_profile"])
    assert calls[10] == ("workspace_reset_defaults", controller)


def test_workspace_controller_helpers_delegate_to_workspace_service(monkeypatch, tmp_path) -> None:
    import splitshot.ui.services.workspace_service as workspace_service_module

    controller = ProjectController()
    workspace = MatchWorkspace()
    stage_entry = StageEntry(stage_id="stage_1")
    project_file = tmp_path / "Stages" / "stage_1" / "project.json"
    expected_snapshot = {"workspace": {"name": "Delegated Workspace"}, "stage_profiles": {}}
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        workspace_service_module,
        "seed_workspace_defaults",
        lambda passed_controller, passed_workspace, eligible_fields: calls.append(
            ("seed_workspace_defaults", passed_controller, passed_workspace, eligible_fields)
        ),
    )
    monkeypatch.setattr(
        workspace_service_module,
        "workspace_stage_entry",
        lambda passed_controller, stage_id: (
            calls.append(("workspace_stage_entry", passed_controller, stage_id)) or stage_entry
        ),
    )
    monkeypatch.setattr(
        workspace_service_module,
        "workspace_stage_project_file",
        lambda passed_controller, stage_id, workspace_path=None, entry=None: (
            calls.append(
                (
                    "workspace_stage_project_file",
                    passed_controller,
                    stage_id,
                    workspace_path,
                    entry,
                )
            )
            or project_file
        ),
    )
    monkeypatch.setattr(
        workspace_service_module,
        "find_workspace_stage_for_project_path",
        lambda passed_controller, project_path, workspace=None, workspace_path=None: (
            calls.append(
                (
                    "find_workspace_stage_for_project_path",
                    passed_controller,
                    project_path,
                    workspace,
                    workspace_path,
                )
            )
            or "stage_1"
        ),
    )
    monkeypatch.setattr(
        workspace_service_module,
        "ensure_project_workspace_membership",
        lambda passed_controller, project_path, eligible_fields: (
            calls.append(
                (
                    "ensure_project_workspace_membership",
                    passed_controller,
                    project_path,
                    eligible_fields,
                )
            )
            or "stage_1"
        ),
    )
    monkeypatch.setattr(
        workspace_service_module,
        "workspace_persistence_snapshot",
        lambda passed_controller: (
            calls.append(("workspace_persistence_snapshot", passed_controller)) or expected_snapshot
        ),
    )
    monkeypatch.setattr(
        workspace_service_module,
        "persist_workspace_stage_profiles",
        lambda passed_controller: calls.append(
            ("persist_workspace_stage_profiles", passed_controller)
        ),
    )
    monkeypatch.setattr(
        workspace_service_module,
        "load_workspace_stage_profiles",
        lambda passed_controller: calls.append(
            ("load_workspace_stage_profiles", passed_controller)
        ),
    )

    controller._seed_workspace_defaults(workspace)
    assert controller._workspace_stage_entry("stage_1") is stage_entry
    assert (
        controller._workspace_stage_project_file(
            "stage_1",
            workspace_path=tmp_path / "delegated-workspace",
            entry=stage_entry,
        )
        == project_file
    )
    assert (
        controller._find_workspace_stage_for_project_path(
            tmp_path / "delegated-workspace" / "Stages" / "stage_1" / "project.json"
        )
        == "stage_1"
    )
    assert (
        controller._ensure_project_workspace_membership(tmp_path / "delegated-project.ssproj")
        == "stage_1"
    )
    assert controller._workspace_persistence_snapshot() == expected_snapshot
    controller._persist_workspace_stage_profiles()
    controller._load_workspace_stage_profiles()

    assert calls[0][0] == "seed_workspace_defaults"
    assert calls[0][1] is controller
    assert calls[0][2] is workspace
    assert "frame_profile" in calls[0][3]
    assert calls[1] == ("workspace_stage_entry", controller, "stage_1")
    assert calls[2][0] == "workspace_stage_project_file"
    assert calls[2][1] is controller
    assert calls[2][2] == "stage_1"
    assert calls[2][4] is stage_entry
    assert calls[3][0] == "find_workspace_stage_for_project_path"
    assert calls[3][1] is controller
    assert calls[4][0] == "ensure_project_workspace_membership"
    assert calls[4][1] is controller
    assert "frame_profile" in calls[4][3]
    assert calls[5] == ("workspace_persistence_snapshot", controller)
    assert calls[6] == ("persist_workspace_stage_profiles", controller)
    assert calls[7] == ("load_workspace_stage_profiles", controller)


class TestWorkspaceLifecycle:
    """Test workspace creation, save, load, and identity stability."""

    def test_new_workspace_creates_empty_workspace(self, controller):
        """New workspace has correct initial state."""
        controller.new_workspace()
        assert controller.workspace is not None
        assert controller.editor_scope == "multi"
        assert controller.workspace.name == "Untitled Match"
        assert len(controller.workspace.stage_entries) == 0

    def test_save_and_reload_workspace(self, controller_with_workspace, tmp_path):
        """Workspace saves and reloads with stable stage membership."""
        c = controller_with_workspace
        ws_path = tmp_path / "test_match"

        # Record original state
        original_match_id = c.workspace.match_id
        original_stage_ids = list(c.workspace.stage_entries.keys())

        # Reopen
        c.open_workspace(str(ws_path))

        assert c.workspace.match_id == original_match_id
        assert list(c.workspace.stage_entries.keys()) == original_stage_ids
        assert c.editor_scope == "multi"

    def test_open_workspace_missing_metadata_sets_status_without_mutation(
        self, controller, tmp_path
    ):
        """Missing workspace open reports an error without mutating the current workspace."""
        controller.new_workspace()
        controller.workspace_add_stage("s1", "Stage 1")

        original_match_id = controller.workspace.match_id
        original_stage_order = list(controller.workspace.stage_order)
        missing_path = tmp_path / "missing-workspace"

        controller.open_workspace(str(missing_path))

        assert controller.workspace is not None
        assert controller.workspace.match_id == original_match_id
        assert controller.workspace.stage_order == original_stage_order
        assert controller.status_message == f"No workspace found at {missing_path}"

    def test_workspace_ids_stable_after_multiple_saves(self, controller_with_workspace, tmp_path):
        """match_id and stage_ids are stable across multiple save/load cycles."""
        c = controller_with_workspace
        ws_path = tmp_path / "test_match"

        original_match_id = c.workspace.match_id
        original_stage_ids = list(c.workspace.stage_entries.keys())

        # Save, reopen, save again, reopen again
        c.save_workspace()
        c.open_workspace(str(ws_path))
        assert c.workspace.match_id == original_match_id

        c.save_workspace()
        c.open_workspace(str(ws_path))
        assert list(c.workspace.stage_entries.keys()) == original_stage_ids

    def test_open_project_inside_saved_workspace_auto_attaches_stage_membership(
        self,
        tmp_path,
    ) -> None:
        workspace_owner = ProjectController()
        workspace_owner.new_workspace()
        workspace_owner.workspace.name = "Owning Match"
        workspace_path = tmp_path / "owning-match"
        workspace_owner.save_workspace(str(workspace_path))

        workspace_owner.new_project()
        workspace_owner.project.name = "Auto Attached Stage"
        stage_path = workspace_path / "Stages" / "stage_auto"
        workspace_owner.save_project(str(stage_path))

        controller = ProjectController()
        controller.open_project(str(stage_path))

        assert controller.workspace is not None
        assert controller.workspace_path == workspace_path
        assert "stage_auto" in controller.workspace.stage_entries
        assert (
            controller.workspace.stage_entries["stage_auto"].display_name == "Auto Attached Stage"
        )
        assert controller.active_stage_id == "stage_auto"
        assert controller._return_to_workspace_available is True

    def test_save_project_without_saved_workspace_auto_creates_unsaved_match_membership(
        self,
        controller,
        tmp_path,
    ) -> None:
        controller.new_project()
        controller.project.name = "Standalone Stage"

        project_path = tmp_path / "standalone-stage"
        controller.save_project(str(project_path))

        assert controller.workspace is not None
        assert controller.workspace_path is None
        assert controller.active_stage_id == controller.project.id
        assert controller.project.id in controller.workspace.stage_entries
        entry = controller.workspace.stage_entries[controller.project.id]
        assert entry.display_name == "Standalone Stage"
        assert entry.relative_project_path == str(project_path.resolve())


class TestStageMembership:
    """Test adding and removing stages from workspace."""

    def test_add_stage_to_workspace(self, controller):
        """Adding a stage creates entry and updates stage_order."""
        controller.new_workspace()
        controller.workspace_add_stage("s1", "Stage 1")

        assert "s1" in controller.workspace.stage_entries
        assert controller.workspace.stage_entries["s1"].display_name == "Stage 1"
        assert "s1" in controller.workspace.stage_order
        assert len(controller.workspace.stage_order) == 1

    def test_add_multiple_stages_preserves_order(self, controller):
        """Stage order is maintained correctly."""
        controller.new_workspace()
        controller.workspace_add_stage("s1", "First")
        controller.workspace_add_stage("s2", "Second")
        controller.workspace_add_stage("s3", "Third")

        assert controller.workspace.stage_order == ["s1", "s2", "s3"]

    def test_remove_stage_from_workspace(self, controller):
        """Removing a stage removes entry and updates order."""
        controller.new_workspace()
        controller.workspace_add_stage("s1", "Stage 1")
        controller.workspace_add_stage("s2", "Stage 2")

        controller.workspace_remove_stage("s1")

        assert "s1" not in controller.workspace.stage_entries
        assert "s1" not in controller.workspace.stage_order
        assert "s2" in controller.workspace.stage_entries
        assert controller.workspace.stage_order == ["s2"]

    def test_remove_nonexistent_stage_no_error(self, controller):
        """Removing a stage that doesn't exist should not raise."""
        controller.new_workspace()
        # Should not raise
        controller.workspace_remove_stage("nonexistent")


class TestStageOpenReturn:
    """Test stage open from workspace and return flows."""

    def test_open_stage_sets_active_stage_id(self, controller_with_workspace):
        """Opening a stage from workspace sets the active stage id."""
        c = controller_with_workspace
        c.workspace_open_stage("stage_1")
        assert c.active_stage_id == "stage_1"
        assert c.editor_scope == "multi"
        assert c._return_to_workspace_available is True

    def test_return_to_workspace_clears_stage_context(self, controller_with_workspace):
        """Return to workspace clears stage context."""
        c = controller_with_workspace
        c.workspace_open_stage("stage_1")
        c.workspace_return_to_workspace()

        assert c.active_stage_id is None
        assert c._return_to_workspace_available is False

    def test_open_stage_from_workspace_no_id_change(self, controller_with_workspace, tmp_path):
        """Stage opens from workspace without changing its stage_id."""
        c = controller_with_workspace

        # Get original stage ids
        original_ids = set(c.workspace.stage_entries.keys())

        # Open a stage
        c.workspace_open_stage("stage_1")

        # Verify workspace stage entries unchanged
        assert set(c.workspace.stage_entries.keys()) == original_ids
        assert "stage_1" in c.workspace.stage_entries

    def test_stage_open_fails_for_nonexistent_stage(self, controller_with_workspace):
        """Opening a nonexistent stage should not crash."""
        c = controller_with_workspace
        c.workspace_open_stage("nonexistent")
        # Should not raise; active_stage_id is unchanged by early return


class TestInheritanceAndOverrides:
    """Test shared defaults and stage overrides."""

    def test_set_workspace_defaults(self, controller):
        """Workspace defaults are persisted."""
        controller.new_workspace()
        controller.workspace_set_defaults({"frame_profile": "16:9", "export_quality": "high"})

        assert controller.workspace.shared_defaults["frame_profile"] == "16:9"
        assert controller.workspace.shared_defaults["export_quality"] == "high"

    def test_set_stage_override(self, controller):
        """Stage override sets value for one stage only."""
        controller.new_workspace()
        controller.workspace_add_stage("s1", "Stage 1")
        controller.workspace_add_stage("s2", "Stage 2")

        controller.workspace_set_stage_override("s1", {"frame_profile": "9:16"})

        assert controller.workspace.stage_entries["s1"].override_values["frame_profile"] == "9:16"
        assert controller.workspace.stage_entries["s1"].status == "overridden"
        # s2 should NOT have the override
        assert "frame_profile" not in controller.workspace.stage_entries["s2"].override_values

    def test_reset_stage_override(self, controller):
        """Resetting stage override removes it."""
        controller.new_workspace()
        controller.workspace_add_stage("s1", "Stage 1")
        controller.workspace_set_stage_override("s1", {"frame_profile": "9:16"})

        controller.workspace_reset_stage_override("s1", ["frame_profile"])

        assert "frame_profile" not in controller.workspace.stage_entries["s1"].override_values

    def test_reset_all_overrides_for_stage(self, controller):
        """Resetting without keys clears all overrides."""
        controller.new_workspace()
        controller.workspace_add_stage("s1", "Stage 1")
        controller.workspace_set_stage_override("s1", {"a": "1", "b": "2"})

        controller.workspace_reset_stage_override("s1")

        assert len(controller.workspace.stage_entries["s1"].override_values) == 0

    def test_resolve_setting_inheritance_chain(self, controller):
        """Setting resolution follows: stage override > match shared > fallback."""
        controller.new_workspace()
        controller.workspace_add_stage("s1", "Stage 1")

        # Set match default
        controller.workspace_set_defaults({"frame_profile": "16:9"})
        assert controller.resolve_setting("s1", "frame_profile") == "16:9"

        # Override for this stage
        controller.workspace_set_stage_override("s1", {"frame_profile": "9:16"})
        assert controller.resolve_setting("s1", "frame_profile") == "9:16"

        # Other stage still gets match default
        controller.workspace_add_stage("s2", "Stage 2")
        assert controller.resolve_setting("s2", "frame_profile") == "16:9"

        # Unknown key falls through to default
        assert controller.resolve_setting("s1", "nonesuch", "fallback") == "fallback"

    def test_override_saved_and_reloaded(self, controller, tmp_path):
        """Override survives workspace save/load round-trip."""
        controller.new_workspace()
        controller.workspace_add_stage("s1", "Stage 1")
        controller.workspace_set_defaults({"frame_profile": "16:9"})
        controller.workspace_set_stage_override("s1", {"frame_profile": "4:5"})

        ws_path = tmp_path / "test_inheritance"
        controller.save_workspace(str(ws_path))

        # Reopen
        controller.open_workspace(str(ws_path))
        assert controller.resolve_setting("s1", "frame_profile") == "4:5"
        assert controller.workspace.stage_entries["s1"].status == "overridden"


class TestApplyFromFirst:
    """Verify Stage 1 apply-to-all copies truthful reusable state."""

    def test_apply_from_first_copies_profiles_and_materializes_overrides(
        self, controller, tmp_path
    ):
        workspace_path = tmp_path / "apply-from-first"
        _build_workspace_with_stage_profiles(controller, workspace_path)

        result = controller.workspace_apply_from_first()

        assert result["applied"] == 1
        assert result["skipped"] == 0
        assert result["snapshot"]["stage_id"] == "stage_1"
        assert result["snapshot"]["profiles"]
        assert any(
            conflict["stage_id"] == "stage_2"
            and conflict["setting"] == "frame_profile"
            and conflict["retained_value"] == "1:1"
            for conflict in result["conflicts"]
        )

        applied_project = controller._load_stage_project("stage_2")
        assert applied_project is not None
        assert applied_project.export.preset == ExportPreset.YOUTUBE_LONG_1080P
        assert applied_project.export.aspect_ratio == AspectRatio.SQUARE
        assert applied_project.export.quality == ExportQuality.MEDIUM
        assert applied_project.overlay.position == OverlayPosition.TOP
        assert applied_project.overlay.show_timer is True
        assert applied_project.overlay.show_score is False

        stage_profiles = controller._load_stage_profiles_for_stage("stage_2")
        cloned_profile = next(
            profile
            for profile in stage_profiles
            if profile.profile_kind == "stage_output" and profile.profile_name == "Stage Output"
        )
        assert cloned_profile.frame_profile == "1:1"
        assert cloned_profile.metric_caption_preset["preset"] == "splits"
        assert cloned_profile.metric_caption_preset["enabled_fields"] == [
            "split_times",
            "cumulative_time",
        ]
        assert cloned_profile.metric_caption_preset["position"] == "bottom_right"
        assert cloned_profile.metric_caption_preset["lead_in_padding_ms"] == 1100
        assert cloned_profile.metric_caption_preset["tail_padding_ms"] == 2200
        assert cloned_profile.lead_in_card == {"style": "competitor", "duration_s": 2.5}
        assert cloned_profile.brand_mark == {
            "style": "splitshot",
            "text": "SplitShot",
            "duration_s": 1.2,
        }
        assert cloned_profile.subject_track_crop == {"enabled": True, "margin_percent": 12}
        assert controller.workspace.stage_entries["stage_2"].inherited_from_first is True

        controller.save_workspace()
        controller.open_workspace(str(workspace_path))
        assert controller.workspace.first_stage_snapshot["stage_id"] == "stage_1"
        assert controller.workspace.first_stage_snapshot["profiles"]
        assert controller.workspace.stage_entries["stage_2"].inherited_from_first is True

    def test_apply_from_first_preview_reports_profile_changes_and_retained_overrides(
        self, controller, tmp_path
    ):
        workspace_path = tmp_path / "apply-preview"
        _build_workspace_with_stage_profiles(controller, workspace_path)

        preview = controller.workspace_apply_from_first_preview()

        assert preview["source_stage"] == "Stage 1"
        assert "output_profiles" in preview["reusable_settings"]
        assert len(preview["preview"]) == 1

        stage_preview = preview["preview"][0]
        assert stage_preview["stage_id"] == "stage_2"
        assert stage_preview["status"] == "conflict"
        assert any(
            conflict["setting"] == "frame_profile"
            and conflict["retained_value"] == "1:1"
            and conflict["proposed_value"] == "16:9"
            for conflict in stage_preview["conflicts"]
        )
        assert any(
            change["setting"] == "output_profile"
            and change["action"] == "created"
            and change["profile_name"] == "Stage Output"
            for change in stage_preview["changes"]
        )

    def test_apply_from_first_uses_workspace_stage_order_for_source(self, controller, tmp_path):
        workspace_path = tmp_path / "apply-stage-order"
        _build_workspace_with_stage_profiles(controller, workspace_path)

        controller.workspace.stage_order = ["stage_2", "stage_1"]
        controller.workspace.stage_entries["stage_1"].override_values.clear()

        result = controller.workspace_apply_from_first()

        assert result["snapshot"]["stage_id"] == "stage_2"
        applied_project = controller._load_stage_project("stage_1")
        assert applied_project is not None
        assert applied_project.export.preset == ExportPreset.SOURCE
        assert applied_project.export.aspect_ratio == AspectRatio.ORIGINAL
        assert applied_project.export.quality == ExportQuality.HIGH
        assert applied_project.overlay.position == OverlayPosition.BOTTOM
        assert applied_project.overlay.show_timer is False
        assert applied_project.overlay.show_score is True


class TestSingleProjectCompatibility:
    """Prove existing single-project flows are NOT broken."""

    def test_new_project_still_works(self, controller):
        """Creating a new project should still work normally."""
        controller.new_project()
        assert controller.project is not None
        assert controller.project.name == "Untitled Project"
        assert controller.editor_scope == "single"
        assert controller.active_stage_id is None

    def test_project_open_after_workspace(self, controller, tmp_path):
        """Project operations work fine after workspace use."""
        # Create and use workspace
        controller.new_workspace()
        controller.workspace_add_stage("s1", "S1")

        # Switch to single project
        controller.new_project()
        assert controller.editor_scope == "single"
        assert controller.project.name == "Untitled Project"

    def test_project_save_load_unaffected(self, controller, tmp_path):
        """Project save/load is not affected by workspace module presence."""
        from splitshot.persistence.projects import save_project, load_project

        controller.new_project()
        controller.project.name = "Test Project"

        proj_path = tmp_path / "test_proj"
        save_project(controller.project, proj_path)

        loaded = load_project(proj_path)
        assert loaded.name == "Test Project"


class TestInheritanceEligibility:
    """Test that inheritance is scoped to eligible fields."""

    def test_ineligible_field_blocked_from_defaults(self, controller):
        """Non-inheritable fields are NOT stored as shared defaults."""
        controller.new_workspace()
        controller.workspace_set_defaults(
            {
                "frame_profile": "16:9",  # eligible
                "trim_dead_time": {"start_ms": 100, "end_ms": 500},  # retired
                "detection_threshold": 0.5,  # NOT eligible
            }
        )
        assert "frame_profile" in controller.workspace.shared_defaults
        assert "trim_dead_time" not in controller.workspace.shared_defaults
        assert "detection_threshold" not in controller.workspace.shared_defaults

    def test_ineligible_field_blocked_from_overrides(self, controller):
        """Non-inheritable fields are NOT stored as stage overrides."""
        controller.new_workspace()
        controller.workspace_add_stage("s1", "Stage 1")
        controller.workspace_set_stage_override(
            "s1",
            {
                "frame_profile": "9:16",  # eligible
                "trim_dead_time": {"start_ms": 120, "end_ms": 420},  # retired
                "detection_threshold": 0.6,  # NOT eligible
            },
        )
        assert "frame_profile" in controller.workspace.stage_entries["s1"].override_values
        assert "trim_dead_time" not in controller.workspace.stage_entries["s1"].override_values
        assert "detection_threshold" not in controller.workspace.stage_entries["s1"].override_values

    def test_resolve_blocks_ineligible_field(self, controller):
        """Ineligible fields bypass workspace layers."""
        controller.new_workspace()
        controller.workspace_add_stage("s1", "Stage 1")
        controller.workspace_set_defaults({"frame_profile": "16:9"})
        result = controller.resolve_setting("s1", "detection_threshold", 0.35)
        assert result is not None

    def test_initial_defaults_populated(self, controller):
        """New workspace gets default values for eligible fields."""
        controller.new_workspace()
        assert len(controller.workspace.shared_defaults) > 0, "Shared defaults should not be empty"
        assert "frame_profile" not in controller.workspace.shared_defaults or isinstance(
            controller.workspace.shared_defaults.get("frame_profile"), str
        )


class TestWorkspaceMediaPathResolution:
    """Verify media paths resolve correctly in workspace context."""

    def test_stage_project_path_resolves_in_workspace(self, controller_with_workspace, tmp_path):
        """After opening a stage from workspace, project_path points inside workspace."""
        c = controller_with_workspace

        c.workspace_open_stage("stage_1")

        if c.project_path is not None:
            assert "Stages" in str(c.project_path) or "stage_1" in str(c.project_path), (
                f"Project path {c.project_path} should be inside workspace's Stages directory"
            )

    def test_workspace_open_stage_preserves_workspace(self, controller_with_workspace):
        """After opening stage, workspace context is preserved."""
        c = controller_with_workspace
        c.workspace_open_stage("stage_1")

        assert c.workspace is not None
        assert c.editor_scope == "multi"
        assert c._return_to_workspace_available is True
        assert "stage_1" in c.workspace.stage_entries


class TestExportCoexistence:
    """Verifies OutputProfile / ExportSettings coexistence."""

    def test_legacy_export_fallback_when_no_profile(self, controller):
        """When no output profile exists, falls back to legacy export settings."""
        controller.new_project()
        controller.project.export.aspect_ratio = "source"

        plan = controller.output_profile_render("nonexistent_id")
        assert plan["success"] is True
        assert plan["source"] == "legacy_export_settings"
        assert plan["profile_name"] == "Legacy Export"

    def test_output_profile_takes_priority(self, controller):
        """When an output profile exists, it takes priority over legacy export."""
        controller.new_project()
        p = controller.output_profile_create(
            "stage", controller.project.id, "My Profile", "stage_output"
        )
        plan = controller.output_profile_render(p["output_id"])

        assert plan["success"] is True
        assert plan["source"] == "output_profile"
        assert plan["profile_name"] == "My Profile"


class TestStageClips:
    """Test clip CRUD for Stage Composite workflow."""

    def test_add_clip_to_stage(self, controller):
        """Adding a clip creates it with correct defaults."""
        controller.new_workspace()
        stage_id = "s1"
        clips = controller.workspace_stage_clip_add(stage_id, "/tmp/test.mp4", "primary")

        assert len(clips) == 1
        assert clips[0]["camera_role"] == "primary"
        assert clips[0]["source_path"] == "/tmp/test.mp4"
        assert clips[0]["audio_gain"] == 1.0
        assert clips[0]["audio_muted"] is False
        assert clips[0]["audio_primary"] is True

    def test_add_multiple_clips_to_stage(self, controller):
        """Multiple clips maintain correct order."""
        controller.new_workspace()
        stage_id = "s1"
        controller.workspace_stage_clip_add(stage_id, "/tmp/1.mp4", "primary")
        controller.workspace_stage_clip_add(stage_id, "/tmp/2.mp4", "follow")
        controller.workspace_stage_clip_add(stage_id, "/tmp/3.mp4", "static")

        clips = controller._get_stage_clips(stage_id)
        assert len(clips) == 3
        roles = [c["camera_role"] for c in clips]
        assert roles == ["primary", "follow", "static"]

    def test_update_clip_properties(self, controller):
        """Updating a clip changes specified properties."""
        controller.new_workspace()
        stage_id = "s1"
        clips = controller.workspace_stage_clip_add(stage_id, "/tmp/test.mp4", "primary")
        clip_id = clips[0]["clip_id"]

        updated = controller.workspace_stage_clip_update(
            stage_id, clip_id, camera_role="follow", audio_gain=0.5
        )
        assert updated is not None
        assert updated["camera_role"] == "follow"
        assert updated["audio_gain"] == 0.5

    def test_remove_clip_from_stage(self, controller):
        """Removing a clip shrinks the clip list."""
        controller.new_workspace()
        stage_id = "s1"
        clips = controller.workspace_stage_clip_add(stage_id, "/tmp/a.mp4", "primary")
        controller.workspace_stage_clip_add(stage_id, "/tmp/b.mp4", "follow")
        clip_id = clips[0]["clip_id"]

        removed = controller.workspace_stage_clip_remove(stage_id, clip_id)
        assert removed is True

        remaining = controller._get_stage_clips(stage_id)
        assert len(remaining) == 1
        assert remaining[0]["source_path"] == "/tmp/b.mp4"

    def test_update_nonexistent_clip_returns_none(self, controller):
        """Updating a clip that doesn't exist returns None."""
        controller.new_workspace()
        result = controller.workspace_stage_clip_update("s1", "nonexistent", camera_role="static")
        assert result is None

    def test_remove_nonexistent_clip_returns_false(self, controller):
        """Removing a clip that doesn't exist returns False."""
        controller.new_workspace()
        result = controller.workspace_stage_clip_remove("s1", "nonexistent")
        assert result is False

    def test_reorder_clip_within_stage_updates_clip_sequence(self, controller):
        """Reordering a clip persists the new composite order."""
        controller.new_workspace()
        first = controller.workspace_stage_clip_add("s1", "/tmp/first.mp4", "primary")[0]
        controller.workspace_stage_clip_add("s1", "/tmp/second.mp4", "follow")
        controller.workspace_stage_clip_add("s1", "/tmp/third.mp4", "detail")

        reordered = controller.workspace_stage_clip_reorder("s1", first["clip_id"], 2)

        assert reordered is not None
        assert [clip["source_path"] for clip in reordered] == [
            "/tmp/second.mp4",
            "/tmp/third.mp4",
            "/tmp/first.mp4",
        ]

    def test_clips_isolated_per_stage(self, controller):
        """Clips for one stage don't leak to another."""
        controller.new_workspace()
        controller.workspace_stage_clip_add("s1", "/tmp/s1.mp4", "primary")
        controller.workspace_stage_clip_add("s2", "/tmp/s2.mp4", "follow")

        assert len(controller._get_stage_clips("s1")) == 1
        assert len(controller._get_stage_clips("s2")) == 1

    def test_stage_clips_persist_across_workspace_save_reopen(self, controller, tmp_path):
        """Stage clip metadata survives workspace save/reopen."""
        controller.new_workspace()
        controller.workspace_add_stage("s1", "Stage 1")
        clips = controller.workspace_stage_clip_add("s1", "/tmp/s1.mp4", "primary")
        clip_id = clips[0]["clip_id"]
        controller.workspace_stage_clip_update("s1", clip_id, sync_offset_ms=135, audio_gain=0.6)

        ws_path = tmp_path / "clip_persist"
        controller.save_workspace(str(ws_path))
        controller.open_workspace(str(ws_path))

        reloaded = controller._get_stage_clips("s1")
        assert len(reloaded) == 1
        assert reloaded[0]["clip_id"] == clip_id
        assert reloaded[0]["sync_offset_ms"] == 135
        assert reloaded[0]["audio_gain"] == 0.6

    def test_stage_clips_autosave_when_workspace_has_path(self, controller_with_workspace):
        """Clip mutations participate in workspace autosave."""
        controller_with_workspace.workspace_stage_clip_add("stage_1", "/tmp/auto.mp4", "primary")
        controller_with_workspace.open_workspace(str(controller_with_workspace.workspace_path))

        reloaded = controller_with_workspace._get_stage_clips("stage_1")
        assert len(reloaded) == 1
        assert reloaded[0]["source_path"] == "/tmp/auto.mp4"

    def test_stage_composite_preview_uses_persisted_clips_after_reopen(self, controller, tmp_path):
        """Stage composite preview reads persisted stage clips after reopen."""
        controller.new_workspace()
        controller.workspace_add_stage("s1", "Stage 1")
        controller.workspace_stage_clip_add("s1", "/tmp/1.mp4", "primary")
        controller.workspace_stage_clip_add("s1", "/tmp/2.mp4", "follow")
        profile = controller.output_profile_create("stage", "s1", "Composite", "stage_composite")

        ws_path = tmp_path / "composite_persist"
        controller.save_workspace(str(ws_path))
        controller.open_workspace(str(ws_path))

        preview = controller.stage_composite_preview(profile["output_id"])
        assert preview["success"] is True
        assert preview["clip_count"] == 2
        assert [clip["camera_role"] for clip in preview["clips"]] == ["primary", "follow"]


class TestAngleAlignAndAudioMix:
    """Test Match composite align/audio actions directly on controller truth."""

    def test_angle_align_marks_all_stage_clips_aligned_for_reference(self, controller):
        """Angle Align marks all clips aligned using the selected reference clip."""
        controller.new_workspace()
        first_clip = controller.workspace_stage_clip_add("s1", "/tmp/1.mp4", "primary")[0]
        controller.workspace_stage_clip_add("s1", "/tmp/2.mp4", "follow")

        result = controller.angle_align("s1", first_clip["clip_id"])

        assert result["success"] is True
        assert result["stage_id"] == "s1"
        assert result["reference_clip_id"] == first_clip["clip_id"]
        assert result["aligned_clips"] == 2
        assert all(clip["angle_aligned"] is True for clip in controller._get_stage_clips("s1"))

    def test_angle_align_returns_error_for_unknown_reference_clip(self, controller):
        """Angle Align rejects a reference clip that does not belong to the stage."""
        controller.new_workspace()
        controller.workspace_stage_clip_add("s1", "/tmp/1.mp4", "primary")

        result = controller.angle_align("s1", "missing-clip")

        assert result == {"success": False, "error": "Reference clip missing-clip not found"}

    def test_audio_mix_set_updates_gain_mute_and_primary_exclusivity(self, controller):
        """Audio Mix updates clip gain/mute and keeps a single primary clip."""
        controller.new_workspace()
        first_clip = controller.workspace_stage_clip_add("s1", "/tmp/1.mp4", "primary")[0]
        second_clip = controller.workspace_stage_clip_add("s1", "/tmp/2.mp4", "follow")[-1]

        result = controller.audio_mix_set(
            "s1",
            second_clip["clip_id"],
            gain=1.5,
            muted=True,
            primary=True,
        )

        assert result is not None
        assert result["clip_id"] == second_clip["clip_id"]
        assert result["audio_gain"] == 1.5
        assert result["audio_muted"] is True
        assert result["audio_primary"] is True

        clips_by_id = {clip["clip_id"]: clip for clip in controller._get_stage_clips("s1")}
        assert clips_by_id[second_clip["clip_id"]]["audio_primary"] is True
        assert clips_by_id[first_clip["clip_id"]]["audio_primary"] is False


class TestAngleDirectorPersistence:
    """Test angle-director durability on output profiles."""

    def test_angle_director_override_persists_across_workspace_save_reopen(
        self, controller, tmp_path
    ):
        """Accepted cut decisions persist on the target output profile."""
        controller.new_workspace()
        controller.workspace_add_stage("s1", "Stage 1")
        clips = controller.workspace_stage_clip_add("s1", "/tmp/1.mp4", "primary")
        controller.workspace_stage_clip_add("s1", "/tmp/2.mp4", "follow")
        profile = controller.output_profile_create("stage", "s1", "Composite", "stage_composite")

        result = controller.angle_director_override_cut(
            "s1",
            clips[0]["clip_id"],
            0,
            start_ms=150,
            duration_ms=275,
            output_id=profile["output_id"],
        )
        assert result["success"] is True

        ws_path = tmp_path / "angle_plan_persist"
        controller.save_workspace(str(ws_path))
        controller.open_workspace(str(ws_path))

        plan = controller.angle_director_plan("s1", profile["output_id"])
        assert plan["success"] is True
        assert plan["has_overrides"] is True
        assert plan["cut_plan"][0]["clip_id"] == clips[0]["clip_id"]
        assert plan["cut_plan"][0]["start_ms"] == 150
        assert plan["cut_plan"][0]["duration_ms"] == 275

    def test_angle_director_override_autosaves_when_workspace_has_path(
        self, controller_with_workspace
    ):
        """Angle-director overrides participate in workspace autosave."""
        clips = controller_with_workspace.workspace_stage_clip_add(
            "stage_1", "/tmp/1.mp4", "primary"
        )
        controller_with_workspace.workspace_stage_clip_add("stage_1", "/tmp/2.mp4", "follow")
        profile = controller_with_workspace.output_profile_create(
            "stage", "stage_1", "Composite", "stage_composite"
        )

        result = controller_with_workspace.angle_director_override_cut(
            "stage_1",
            clips[0]["clip_id"],
            0,
            start_ms=90,
            duration_ms=200,
            output_id=profile["output_id"],
        )
        assert result["success"] is True

        controller_with_workspace.open_workspace(str(controller_with_workspace.workspace_path))
        plan = controller_with_workspace.angle_director_plan("stage_1", profile["output_id"])
        assert plan["success"] is True
        assert plan["has_overrides"] is True
        assert plan["cut_plan"][0]["start_ms"] == 90

    def test_angle_director_plan_merges_generated_cuts_with_persisted_override(self, controller):
        """Overrides replace the matching generated slot without dropping the rest of the plan."""
        controller.new_workspace()
        first_clip = controller.workspace_stage_clip_add("s1", "/tmp/1.mp4", "primary")[0]
        controller.workspace_stage_clip_add("s1", "/tmp/2.mp4", "follow")
        profile = controller.output_profile_create("stage", "s1", "Composite", "stage_composite")

        override = controller.angle_director_override_cut(
            "s1",
            first_clip["clip_id"],
            1,
            start_ms=250,
            duration_ms=500,
            output_id=profile["output_id"],
        )

        assert override["success"] is True
        plan = controller.angle_director_plan("s1", profile["output_id"])
        assert plan["success"] is True
        assert len(plan["cut_plan"]) == 2
        assert plan["cut_plan"][1]["clip_id"] == first_clip["clip_id"]
        assert plan["cut_plan"][1]["start_ms"] == 250
        assert plan["cut_plan"][1]["duration_ms"] == 500

    def test_angle_director_clear_cut_removes_only_requested_override(self, controller):
        """Clearing one override preserves other persisted cut decisions."""
        controller.new_workspace()
        first_clip = controller.workspace_stage_clip_add("s1", "/tmp/1.mp4", "primary")[0]
        second_clip = controller.workspace_stage_clip_add("s1", "/tmp/2.mp4", "follow")[-1]
        profile = controller.output_profile_create("stage", "s1", "Composite", "stage_composite")

        controller.angle_director_override_cut(
            "s1",
            first_clip["clip_id"],
            0,
            start_ms=100,
            duration_ms=200,
            output_id=profile["output_id"],
        )
        controller.angle_director_override_cut(
            "s1",
            second_clip["clip_id"],
            1,
            start_ms=300,
            duration_ms=400,
            output_id=profile["output_id"],
        )

        cleared = controller.angle_director_clear_cut("s1", 0, profile["output_id"])

        assert cleared["success"] is True
        assert len(cleared["cut_plan"]) == 1
        assert cleared["cut_plan"][0]["clip_id"] == second_clip["clip_id"]


class TestWorkspaceRecapRender:
    """Test recap rendering orchestration on controller truth."""

    def test_workspace_recap_render_uses_transition_and_result_cards(
        self, controller, tmp_path, monkeypatch
    ):
        """Recap render threads transition and result-card mode into the final render sequence."""
        controller.new_workspace()
        controller.workspace_add_stage("s1", "Stage 1")
        controller.workspace_add_stage("s2", "Stage 2")
        controller.workspace.stage_entries["s1"].source_media_present = True
        controller.workspace.stage_entries["s2"].source_media_present = True
        workspace_path = tmp_path / "recap-workspace"
        controller.save_workspace(str(workspace_path))

        for stage_id in ("s1", "s2"):
            controller.new_project()
            controller.project.primary_video = VideoAsset(
                path=f"/tmp/{stage_id}.mp4",
                width=640,
                height=360,
                duration_ms=1000,
                fps=30.0,
            )
            assert controller._save_stage_project(stage_id, controller.project) is True

        def fake_export_project(project, output_path, progress_callback=None, log_callback=None):
            path = controller_module.Path(output_path)
            path.write_bytes(b"segment")
            return path

        def fake_probe_video(path):
            return VideoAsset(
                path=str(path),
                width=640,
                height=360,
                duration_ms=1000,
                fps=30.0,
            )

        rendered_cards: list[str] = []
        render_calls: list[dict] = []

        def fake_render_card_video(self, title, detail_lines, output_path, **kwargs):
            rendered_cards.append(title)
            controller_module.Path(output_path).write_bytes(b"card")
            return controller_module.Path(output_path)

        def fake_render_sequence(self, sequence_paths, recap_path, **kwargs):
            recap_path.write_bytes(b"recap")
            render_calls.append(
                {
                    "paths": [controller_module.Path(path).name for path in sequence_paths],
                    "transition": kwargs["transition"],
                }
            )
            return {"success": True, "sequence_count": len(sequence_paths)}

        monkeypatch.setattr(controller_module, "export_project", fake_export_project)
        monkeypatch.setattr(controller_module, "probe_video", fake_probe_video)
        monkeypatch.setattr(ProjectController, "_render_recap_card_video", fake_render_card_video)
        monkeypatch.setattr(ProjectController, "_render_recap_sequence", fake_render_sequence)

        result = controller.workspace_recap_render(
            stage_ids=["s1", "s2"],
            transition="fade",
            result_card="each",
        )

        assert result["success"] is True
        assert result["transition"] == "fade"
        assert result["result_card"] == "each"
        assert rendered_cards == ["Stage 1", "Stage 2"]
        assert render_calls == [
            {
                "paths": [
                    "s1.mp4",
                    "s1-result-card.mp4",
                    "s2.mp4",
                    "s2-result-card.mp4",
                ],
                "transition": "fade",
            }
        ]
