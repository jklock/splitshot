from __future__ import annotations

from datetime import datetime, timezone


from splitshot.domain.models import (
    LibraryMatchRecord,
    LibraryOutputRecord,
    LibraryStageRecord,
    MatchWorkspace,
    OutputProfile,
    Project,
    RetainedProxyRecord,
    StageEntry,
)
from splitshot.persistence.library import (
    append_stage_metric,
    load_match_record,
    load_output_record,
    load_proxy_record,
    load_stage_record,
    read_stage_metrics,
    save_match_record,
    save_output_record,
    save_proxy_record,
    save_stage_record,
)
from splitshot.persistence.projects import load_project, save_project
from splitshot.persistence.workspaces import (
    ensure_workspace_stage_path,
    ensure_workspace_structure,
    load_workspace,
    save_workspace,
    workspace_has_metadata,
    workspace_metadata_path,
    workspace_stage_project_path,
)

UTC = timezone.utc


class TestWorkspaceSerialization:
    """Test MatchWorkspace save/load round-trip."""

    def test_empty_workspace_roundtrip(self, tmp_path):
        ws = MatchWorkspace(name="Empty Test")
        ws_path = save_workspace(ws, tmp_path / "empty_workspace")
        loaded = load_workspace(ws_path)

        assert loaded.match_id == ws.match_id
        assert loaded.name == "Empty Test"
        assert loaded.stage_entries == {}
        assert loaded.stage_order == []
        assert loaded.match_output_profiles == []
        assert loaded.schema_version == 1

    def test_workspace_with_stages_roundtrip(self, tmp_path):
        ws = MatchWorkspace(name="Multi Stage Match")
        ws.stage_order = ["stage_a", "stage_b"]
        ws.stage_entries = {
            "stage_a": StageEntry(
                stage_id="stage_a",
                relative_project_path="Stages/stage_a/project.json",
                display_name="Bay 1",
                stage_number=1,
                status="complete",
                source_media_present=True,
            ),
            "stage_b": StageEntry(
                stage_id="stage_b",
                relative_project_path="Stages/stage_b/project.json",
                display_name="Bay 2",
                stage_number=2,
                status="incomplete",
            ),
        }
        ws_path = save_workspace(ws, tmp_path / "multi_stage")
        loaded = load_workspace(ws_path)

        assert loaded.name == "Multi Stage Match"
        assert loaded.stage_order == ["stage_a", "stage_b"]
        assert len(loaded.stage_entries) == 2
        assert loaded.stage_entries["stage_a"].stage_number == 1
        assert loaded.stage_entries["stage_a"].status == "complete"
        assert loaded.stage_entries["stage_a"].source_media_present is True
        assert loaded.stage_entries["stage_b"].display_name == "Bay 2"
        assert loaded.stage_entries["stage_b"].status == "incomplete"

    def test_workspace_with_output_profiles(self, tmp_path):
        ws = MatchWorkspace(name="Output Profiles")
        ws.match_output_profiles = [
            OutputProfile(
                output_id="out_1",
                scope_type="match",
                scope_id=ws.match_id,
                profile_name="Social Clip",
                profile_kind="match_output",
                frame_profile="portrait",
            ),
            OutputProfile(
                output_id="out_2",
                scope_type="match",
                scope_id=ws.match_id,
                profile_name="Full Review",
                profile_kind="match_output",
                frame_profile="source",
            ),
        ]
        ws_path = save_workspace(ws, tmp_path / "profiles")
        loaded = load_workspace(ws_path)

        assert len(loaded.match_output_profiles) == 2
        assert loaded.match_output_profiles[0].profile_name == "Social Clip"
        assert loaded.match_output_profiles[0].frame_profile == "portrait"
        assert loaded.match_output_profiles[1].profile_name == "Full Review"

    def test_workspace_shared_defaults(self, tmp_path):
        ws = MatchWorkspace(name="Defaults")
        ws.shared_defaults = {"default_layout": "pip", "default_overlay": "compact"}
        ws_path = save_workspace(ws, tmp_path / "defaults")
        loaded = load_workspace(ws_path)

        assert loaded.shared_defaults == {"default_layout": "pip", "default_overlay": "compact"}

    def test_stage_order_preserved(self, tmp_path):
        ws = MatchWorkspace(name="Order Test")
        ws.stage_order = ["s3", "s1", "s2"]
        ws_path = save_workspace(ws, tmp_path / "order")
        loaded = load_workspace(ws_path)

        assert loaded.stage_order == ["s3", "s1", "s2"]

    def test_workspace_ids_stable(self, tmp_path):
        ws = MatchWorkspace(name="ID Stability")
        ws.stage_entries = {
            "sid": StageEntry(
                stage_id="sid",
                relative_project_path="Stages/sid/project.json",
                display_name="Stage",
            )
        }
        ws_path = save_workspace(ws, tmp_path / "ids")
        loaded = load_workspace(ws_path)

        assert loaded.match_id == ws.match_id
        assert "sid" in loaded.stage_entries
        assert loaded.stage_entries["sid"].stage_id == "sid"


class TestLegacyProjectCompatibility:
    """Prove legacy project.json behavior is NOT broken."""

    def test_legacy_project_still_loads(self, tmp_path):
        project = Project(name="Legacy Compat Test")
        project.description = "Should survive round-trip"
        bundle = save_project(project, tmp_path / "legacy-compat.ssproj")
        loaded = load_project(bundle)

        assert loaded.name == "Legacy Compat Test"
        assert loaded.description == "Should survive round-trip"
        assert loaded.id == project.id
        assert loaded.schema_version == 1

    def test_project_id_stable(self, tmp_path):
        project = Project(name="ID Check")
        project_id = project.id
        bundle = save_project(project, tmp_path / "id-check.ssproj")
        loaded = load_project(bundle)

        assert loaded.id == project_id

    def test_project_with_workspace_module_present(self, tmp_path):
        project = Project(name="With Workspace Module")
        project.scoring.match_type = "uspsa"
        project.scoring.stage_number = 3
        project.scoring.competitor_name = "Test Shooter"
        bundle = save_project(project, tmp_path / "with-ws-module.ssproj")
        loaded = load_project(bundle)

        assert loaded.name == "With Workspace Module"
        assert loaded.scoring.match_type == "uspsa"
        assert loaded.scoring.stage_number == 3
        assert loaded.scoring.competitor_name == "Test Shooter"


class TestCoexistence:
    """Prove workspace and project persistence coexist cleanly."""

    def test_workspace_and_project_in_same_tree(self, tmp_path):
        ws = MatchWorkspace(name="Coexistence Test")
        ws.stage_order = ["test_stage"]
        ws_path = save_workspace(ws, tmp_path / "coexist")

        stage_dir = ensure_workspace_stage_path(ws_path, "test_stage")
        project = Project(name="Nested Stage Project")
        save_project(project, stage_dir / "project.json")

        loaded_ws = load_workspace(ws_path)
        assert loaded_ws.name == "Coexistence Test"
        assert loaded_ws.stage_order == ["test_stage"]

        project_path = workspace_stage_project_path(ws_path, "test_stage")
        assert project_path.is_file()
        loaded_project = load_project(project_path)
        assert loaded_project.name == "Nested Stage Project"

    def test_workspace_metadata_path_and_has_metadata(self, tmp_path):
        ws = MatchWorkspace(name="Metadata Check")
        ws_path = save_workspace(ws, tmp_path / "meta_check")

        assert workspace_has_metadata(ws_path) is True
        meta_path = workspace_metadata_path(ws_path)
        assert meta_path.name == "workspace.json"
        assert meta_path.is_file()

    def test_ensure_workspace_structure_creates_dir(self, tmp_path):
        ws_dir = tmp_path / "new_workspace"
        assert not ws_dir.exists()

        ensure_workspace_structure(ws_dir)
        assert ws_dir.is_dir()

    def test_ensure_workspace_stage_path_creates_stage_dir(self, tmp_path):
        ws = MatchWorkspace(name="Stage Path Test")
        ws_path = save_workspace(ws, tmp_path / "stage_path_test")

        stage_path = ensure_workspace_stage_path(ws_path, "bay_3")
        assert stage_path.is_dir()
        assert stage_path.name == "bay_3"
        assert stage_path.parent.name == "Stages"


class TestLibraryPersistence:
    """Test library record persistence."""

    def test_stage_record_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPLITSHOT_LIBRARY_ROOT", str(tmp_path / "library"))

        record = LibraryStageRecord(
            stage_id="stage_001",
            match_id="match_001",
            display_name="Bay 5 — IDPA",
            discipline="idpa",
            competitor_name="Test Shooter",
            metric_summary={"total_shots": 18, "total_time_s": 28.5},
        )
        save_stage_record(record)

        loaded = load_stage_record(record.library_record_id)
        assert loaded is not None
        assert loaded.stage_id == "stage_001"
        assert loaded.display_name == "Bay 5 — IDPA"
        assert loaded.metric_summary["total_shots"] == 18

    def test_match_record_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPLITSHOT_LIBRARY_ROOT", str(tmp_path / "library"))

        record = LibraryMatchRecord(
            match_id="match_001",
            display_name="State Championship",
            discipline="uspsa",
            stage_ids=["stage_001", "stage_002"],
            aggregate_metric_summary={"total_score": 475.3},
        )
        save_match_record(record)

        loaded = load_match_record(record.library_record_id)
        assert loaded is not None
        assert loaded.match_id == "match_001"
        assert loaded.display_name == "State Championship"
        assert loaded.stage_ids == ["stage_001", "stage_002"]
        assert loaded.aggregate_metric_summary["total_score"] == 475.3

    def test_stage_metrics_append_and_read(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPLITSHOT_LIBRARY_ROOT", str(tmp_path / "library"))

        append_stage_metric({"stage_id": "s1", "score": 95.0})
        append_stage_metric({"stage_id": "s2", "score": 87.5})

        metrics = read_stage_metrics()
        assert len(metrics) == 2
        assert metrics[0]["stage_id"] == "s1"
        assert metrics[1]["score"] == 87.5

    def test_proxy_record_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPLITSHOT_LIBRARY_ROOT", str(tmp_path / "library"))

        now = datetime.now(UTC)
        record = RetainedProxyRecord(
            scope_type="stages",
            scope_id="stage_001",
            source_output_id="out_abc",
            relative_path="proxies/stages/stage_001/abc123.mp4",
            codec_profile="h264_aac",
            width=1920,
            height=1080,
            duration_ms=28500,
            file_size_bytes=12_000_000,
            generated_from_truth_hash="abc123",
            generated_at=now,
        )
        save_proxy_record(record)

        loaded = load_proxy_record("stages", "stage_001")
        assert loaded is not None
        assert loaded.scope_type == "stages"
        assert loaded.scope_id == "stage_001"
        assert loaded.width == 1920
        assert loaded.file_size_bytes == 12_000_000

    def test_missing_record_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPLITSHOT_LIBRARY_ROOT", str(tmp_path / "library"))

        assert load_stage_record("nonexistent") is None
        assert load_match_record("nonexistent") is None
        assert load_proxy_record("stages", "nonexistent") is None

    def test_output_record_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPLITSHOT_LIBRARY_ROOT", str(tmp_path / "library"))

        now = datetime.now(UTC)
        record = LibraryOutputRecord(
            output_id="out_xyz",
            scope_type="match",
            scope_id="match_001",
            profile_name="Social Clip",
            profile_kind="match_output",
            frame_profile="portrait",
            retained_proxy_id="proxy_zzz",
            last_rendered_at=now,
        )
        save_output_record(record)
        loaded = load_output_record(record.library_record_id)
        assert loaded is not None
        assert loaded.output_id == "out_xyz"
        assert loaded.profile_name == "Social Clip"
        assert loaded.retained_proxy_id == "proxy_zzz"


class TestOutputProfilePersistence:
    """Test OutputProfile serialization within workspace context."""

    def test_output_profile_embedded_in_workspace(self, tmp_path):
        ws = MatchWorkspace(name="Profile Embed Test")
        ws.match_output_profiles = [
            OutputProfile(
                output_id="prof_a",
                scope_type="match",
                scope_id=ws.match_id,
                profile_name="Stage Export",
                metric_caption_preset={"show_time": True, "show_hf": True},
                lead_in_card={"title": "Stage 1", "subtitle": "Bay 3"},
                brand_mark={"enabled": True, "position": "top_right"},
            ),
        ]
        ws_path = save_workspace(ws, tmp_path / "embed")
        loaded = load_workspace(ws_path)

        assert len(loaded.match_output_profiles) == 1
        profile = loaded.match_output_profiles[0]
        assert profile.profile_name == "Stage Export"
        assert profile.metric_caption_preset == {"show_time": True, "show_hf": True}
        assert profile.lead_in_card == {"title": "Stage 1", "subtitle": "Bay 3"}
        assert profile.brand_mark == {"enabled": True, "position": "top_right"}

    def test_output_profile_field_types(self, tmp_path):
        ws = MatchWorkspace(name="Field Type Test")
        ws.match_output_profiles = [
            OutputProfile(
                output_id="type_check",
                scope_type="match",
                scope_id=ws.match_id,
                profile_name="Full Export",
                profile_kind="match_output",
                frame_profile="landscape",
                subject_track_crop={"enabled": True, "padding": 0.15},
                visibility_recipe={"show_overlay": True, "show_popups": False},
                retained_proxy_id=None,
                last_rendered_at=None,
            ),
        ]
        ws_path = save_workspace(ws, tmp_path / "field_types")
        loaded = load_workspace(ws_path)

        profile = loaded.match_output_profiles[0]
        assert profile.subject_track_crop == {"enabled": True, "padding": 0.15}
        assert profile.visibility_recipe == {"show_overlay": True, "show_popups": False}
        assert profile.retained_proxy_id is None
        assert profile.last_rendered_at is None

    def test_output_profile_with_rendered_at(self, tmp_path):
        now = datetime(2025, 6, 15, 10, 30, 0, tzinfo=UTC)
        ws = MatchWorkspace(name="Render Time Test")
        ws.match_output_profiles = [
            OutputProfile(
                output_id="rendered",
                scope_type="match",
                scope_id=ws.match_id,
                profile_name="Rendered",
                last_rendered_at=now,
            ),
        ]
        ws_path = save_workspace(ws, tmp_path / "rendered_time")
        loaded = load_workspace(ws_path)

        profile = loaded.match_output_profiles[0]
        assert profile.last_rendered_at is not None
        assert profile.last_rendered_at.year == 2025
        assert profile.last_rendered_at.month == 6
        assert profile.last_rendered_at.hour == 10
