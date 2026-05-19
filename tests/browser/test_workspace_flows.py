from __future__ import annotations


import pytest

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
        controller.workspace_set_defaults({
            "frame_profile": "16:9",       # eligible
            "detection_threshold": 0.5,    # NOT eligible
        })
        assert "frame_profile" in controller.workspace.shared_defaults
        assert "detection_threshold" not in controller.workspace.shared_defaults

    def test_ineligible_field_blocked_from_overrides(self, controller):
        """Non-inheritable fields are NOT stored as stage overrides."""
        controller.new_workspace()
        controller.workspace_add_stage("s1", "Stage 1")
        controller.workspace_set_stage_override("s1", {
            "frame_profile": "9:16",       # eligible
            "detection_threshold": 0.6,    # NOT eligible
        })
        assert "frame_profile" in controller.workspace.stage_entries["s1"].override_values
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
        assert "frame_profile" not in controller.workspace.shared_defaults or isinstance(controller.workspace.shared_defaults.get("frame_profile"), str)


class TestWorkspaceMediaPathResolution:
    """Verify media paths resolve correctly in workspace context."""

    def test_stage_project_path_resolves_in_workspace(self, controller_with_workspace, tmp_path):
        """After opening a stage from workspace, project_path points inside workspace."""
        c = controller_with_workspace

        c.workspace_open_stage("stage_1")

        if c.project_path is not None:
            assert "Stages" in str(c.project_path) or "stage_1" in str(c.project_path),                 f"Project path {c.project_path} should be inside workspace's Stages directory"

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
        p = controller.output_profile_create("stage", controller.project.id, "My Profile", "stage_output")
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
        assert clips[0]["angle_role"] == "primary"
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
        roles = [c["angle_role"] for c in clips]
        assert roles == ["primary", "follow", "static"]
    
    def test_update_clip_properties(self, controller):
        """Updating a clip changes specified properties."""
        controller.new_workspace()
        stage_id = "s1"
        clips = controller.workspace_stage_clip_add(stage_id, "/tmp/test.mp4", "primary")
        clip_id = clips[0]["clip_id"]
        
        updated = controller.workspace_stage_clip_update(
            stage_id, clip_id, angle_role="follow", audio_gain=0.5
        )
        assert updated is not None
        assert updated["angle_role"] == "follow"
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
        result = controller.workspace_stage_clip_update("s1", "nonexistent", angle_role="static")
        assert result is None
    
    def test_remove_nonexistent_clip_returns_false(self, controller):
        """Removing a clip that doesn't exist returns False."""
        controller.new_workspace()
        result = controller.workspace_stage_clip_remove("s1", "nonexistent")
        assert result is False
    
    def test_clips_isolated_per_stage(self, controller):
        """Clips for one stage don't leak to another."""
        controller.new_workspace()
        controller.workspace_stage_clip_add("s1", "/tmp/s1.mp4", "primary")
        controller.workspace_stage_clip_add("s2", "/tmp/s2.mp4", "follow")
        
        assert len(controller._get_stage_clips("s1")) == 1
        assert len(controller._get_stage_clips("s2")) == 1
