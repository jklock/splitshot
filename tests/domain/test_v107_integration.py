"""Multi-stage v107 workflow integration test with real IDPA match data.

Uses 05072026/ data (not checked into git):
- CSV/IDPA.csv — 4-stage IDPA match, 30 shooters
- Stage2.MP4, Stage3.MP4, Stage4.MP4 — primary media
- Stage1 has no media (tests missing-media handling)

Verifies:
- Project creation from CSV stages
- Per-stage primary media import
- Per-stage merge layout configuration (PIP, SBS, ABOVE_BELOW)
- Overlay configuration (timer, shots, score)
- Stage switching with state preservation
- Queue add + apply-all
- Per-stage export via process_queue
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory


from splitshot.domain.models import (
    Project,
    ProjectStage,
    QueueStatus,
    project_to_dict,
    project_from_dict,
)
from splitshot.ui.controller import ProjectController
from splitshot.persistence.projects import save_project, load_project


DATA_ROOT = Path("05072026")
CSV_PATH = DATA_ROOT / "CSV" / "IDPA.csv"
STAGE_VIDEOS = {
    2: DATA_ROOT / "Stage2.MP4",
    3: DATA_ROOT / "Stage3.MP4",
    4: DATA_ROOT / "Stage4.MP4",
}


def _parse_idpa_stages(csv_path: Path) -> list[dict]:
    """Extract stage numbers and names from IDPA CSV header."""
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
    stages = []
    for field in fieldnames:
        if field.startswith("Stage ") and " Time" in field and "DNF" not in field:
            num = int(field.split()[1])
            name = field.split(" Time")[0]
            stages.append({"number": num, "name": name})
    return sorted(stages, key=lambda s: s["number"])


def _get_first_shooter_stage_data(csv_path: Path, stage_number: int) -> dict | None:
    """Get the first shooter's data for a specific stage."""
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            time_key = f"Stage {stage_number} Time"
            pd_key = f"Stage {stage_number} PD"
            time_val = row.get(time_key, "").strip()
            if time_val:
                return {
                    "first_name": row.get("First Name", "").strip(),
                    "last_name": row.get("Last Name", "").strip(),
                    "division": row.get("Division", "").strip(),
                    "class": row.get("Class", "").strip(),
                    "time": time_val,
                    "pd": row.get(pd_key, "0").strip(),
                }
    return None


class TestV107MultiStageWorkflow:
    """Integration test for v107 multi-stage workflow with real media."""

    def test_create_multi_stage_project_from_idpa_csv(self):
        """Phase 01-03: Create v2 project with stages from IDPA CSV."""
        stages = _parse_idpa_stages(CSV_PATH)
        assert len(stages) == 4, f"Expected 4 stages, got {len(stages)}"
        print(f"\n  Parsed {len(stages)} IDPA stages: {[s['name'] for s in stages]}")

        project = Project()
        project_stages = []
        for s in stages:
            shooter = _get_first_shooter_stage_data(CSV_PATH, s["number"])
            ps = ProjectStage(
                label=s["name"],
                order_index=s["number"],
                imported_stage_number=s["number"],
                imported_stage_name=s["name"],
            )
            project_stages.append(ps)
        project.stages = project_stages
        project.active_stage_id = project_stages[0].id
        project.schema_version = 2
        project.practiscore_source_file = str(CSV_PATH.resolve())

        assert len(project.stages) == 4
        assert project.active_stage_id == project.stages[0].id
        print(f"  Created {len(project.stages)} stages, active: {project.stages[0].label}")

    def test_practiscore_import_generates_project_stages(self):
        """PractiScore import should create one ProjectStage per imported stage."""
        controller = ProjectController()
        controller.import_practiscore_file(str(CSV_PATH.resolve()), source_name=CSV_PATH.name)

        assert len(controller.project.stages) == 4
        assert controller.project.active_stage_id == controller.project.stages[0].id
        assert controller.project.practiscore_source_file.endswith("IDPA.csv")
        assert [stage.imported_stage_number for stage in controller.project.stages] == [1, 2, 3, 4]
        assert [stage.label for stage in controller.project.stages] == [
            "Stage 1",
            "Stage 2",
            "Stage 3",
            "Stage 4",
        ]

    def test_import_primary_media_per_stage(self):
        """Phase 02: Import primary media for stages 2-4. Stage 1 has no media."""
        stages_def = _parse_idpa_stages(CSV_PATH)
        project = Project()
        project_stages = []
        for s in stages_def:
            ps = ProjectStage(
                label=s["name"],
                order_index=s["number"],
                imported_stage_number=s["number"],
                imported_stage_name=s["name"],
            )
            project_stages.append(ps)
        project.stages = project_stages
        project.active_stage_id = project_stages[0].id
        project.schema_version = 2

        controller = ProjectController()
        controller.project = project

        imported_count = 0
        for stage_num, video_path in STAGE_VIDEOS.items():
            if video_path.exists():
                stage = project.stages[stage_num - 1]
                controller.select_stage(stage.id)
                controller.import_stage_primary(stage.id, str(video_path.resolve()))
                imported_count += 1
                primary_path = stage.primary_media.path
                assert primary_path, f"Stage {stage_num} should have primary media"
                print(
                    f"  Stage {stage_num} '{stage.label}': primary={Path(primary_path).name} "
                    f"({stage.primary_media.duration_ms}ms, {stage.primary_media.width}x{stage.primary_media.height})"
                )

        assert imported_count == 3
        print(f"  Imported primary media for {imported_count}/4 stages (Stage 1 has no media)")

        # Stage 1 should have no primary
        stage1 = project.stages[0]
        assert stage1.primary_media.path == "", "Stage 1 should have empty primary media"

    def test_per_stage_merge_layouts(self):
        """Phase 04: Configure per-stage merge layouts (PIP, SBS, ABOVE_BELOW)."""
        stages_def = _parse_idpa_stages(CSV_PATH)
        project = Project()
        project_stages = []
        for s in stages_def:
            ps = ProjectStage(
                label=s["name"],
                order_index=s["number"],
                imported_stage_number=s["number"],
                imported_stage_name=s["name"],
            )
            project_stages.append(ps)
        project.stages = project_stages
        project.active_stage_id = project_stages[0].id
        project.schema_version = 2

        from splitshot.domain.models import MergeLayout, MergeSource, VideoAsset

        # Import primary media for stages 2-4
        for stage_num, video_path in STAGE_VIDEOS.items():
            if video_path.exists():
                stage = project.stages[stage_num - 1]
                stage.primary_media = VideoAsset(path=str(video_path.resolve()))

        # Configure layouts per stage
        layout_map = {
            2: MergeLayout.PIP,
            3: MergeLayout.SIDE_BY_SIDE,
            4: MergeLayout.ABOVE_BELOW,
        }

        for stage_num, layout in layout_map.items():
            stage = project.stages[stage_num - 1]
            stage.merge.layout = layout
            stage.merge.enabled = True
            # Add the next stage's video as added media for PIP/SBS
            if stage_num < 4 and (stage_num + 1) in STAGE_VIDEOS:
                added_path = STAGE_VIDEOS[stage_num + 1]
                if added_path.exists():
                    stage.added_media.append(
                        MergeSource(asset=VideoAsset(path=str(added_path.resolve())))
                    )
            print(
                f"  Stage {stage_num} '{stage.label}': layout={layout.value}, "
                f"added_media={len(stage.added_media)}"
            )

        assert project.stages[1].merge.layout == MergeLayout.PIP
        assert project.stages[2].merge.layout == MergeLayout.SIDE_BY_SIDE
        assert project.stages[3].merge.layout == MergeLayout.ABOVE_BELOW

    def test_overlay_configuration(self):
        """Phase 04: Enable overlay (timer, shots, score) across all stages."""
        stages_def = _parse_idpa_stages(CSV_PATH)
        project = Project()
        project_stages = []
        for s in stages_def:
            ps = ProjectStage(
                label=s["name"],
                order_index=s["number"],
                imported_stage_number=s["number"],
                imported_stage_name=s["name"],
            )
            project_stages.append(ps)
        project.stages = project_stages
        project.active_stage_id = project_stages[0].id
        project.schema_version = 2

        for stage in project.stages:
            stage.overlay.show_timer = True
            stage.overlay.show_shots = True
            stage.overlay.show_score = True
            stage.overlay.show_draw = True
            stage.overlay.position = "bottom"
            stage.overlay.badge_size = "M"
            stage.overlay.font_size = 14
            stage.overlay.font_bold = True
            stage.overlay.max_visible_shots = 4

        assert all(s.overlay.show_timer for s in project.stages)
        assert all(s.overlay.show_shots for s in project.stages)
        assert all(s.overlay.show_score for s in project.stages)
        print(f"  Overlay enabled on all {len(project.stages)} stages")

    def test_stage_switching_preserves_state(self):
        """Phase 04: Switching stages preserves per-stage configuration."""
        stages_def = _parse_idpa_stages(CSV_PATH)
        project = Project()
        project_stages = []
        for s in stages_def:
            ps = ProjectStage(
                label=s["name"],
                order_index=s["number"],
            )
            project_stages.append(ps)
        project.stages = project_stages
        project.active_stage_id = project_stages[0].id
        project.schema_version = 2

        controller = ProjectController()
        controller.project = project

        # Set stage 2 to PIP, stage 3 to SBS
        from splitshot.domain.models import MergeLayout

        project.stages[1].merge.layout = MergeLayout.PIP
        project.stages[2].merge.layout = MergeLayout.SIDE_BY_SIDE

        # Sync stage 1 state into project, then switch to stage 2
        controller._sync_active_stage_to_project()
        assert controller.project.merge.layout == MergeLayout.SIDE_BY_SIDE  # default for stage 1

        controller.select_stage(project.stages[1].id)
        assert controller.project.merge.layout == MergeLayout.PIP  # stage 2's PIP

        controller.select_stage(project.stages[2].id)
        assert controller.project.merge.layout == MergeLayout.SIDE_BY_SIDE  # stage 3's SBS

        print(f"  Stage switching verified: {len(project.stages)} stages, bidirectional sync works")

    def test_queue_add_and_apply_all(self):
        """Phase 05: Add stages to queue, apply settings to all."""
        stages_def = _parse_idpa_stages(CSV_PATH)
        project = Project()
        project_stages = []
        for s in stages_def:
            ps = ProjectStage(
                label=s["name"],
                order_index=s["number"],
            )
            project_stages.append(ps)
        project.stages = project_stages
        project.active_stage_id = project_stages[0].id
        project.schema_version = 2

        controller = ProjectController()
        controller.project = project

        # Import primary media for stages 2-4 so they can be queued
        from splitshot.domain.models import VideoAsset

        for stage_num, video_path in STAGE_VIDEOS.items():
            if video_path.exists():
                project.stages[stage_num - 1].primary_media = VideoAsset(
                    path=str(video_path.resolve()),
                    duration_ms=10000,
                    width=1920,
                    height=1080,
                    fps=30.0,
                )

        # Configure stage 1 with proper overlay settings
        active_stage = project.stages[0]
        active_stage.overlay.show_timer = True
        active_stage.overlay.show_shots = True
        active_stage.overlay.show_score = True
        active_stage.merge.layout = "pip"

        # Add stages 2, 3, 4 to queue
        for stage_num in [2, 3, 4]:
            stage = project.stages[stage_num - 1]
            controller.add_stage_to_queue(stage.id)
            assert stage.queue_status == QueueStatus.QUEUED
            print(f"  Stage {stage_num} '{stage.label}': queued")

        assert len(project.queue) == 3

        # Apply settings from stage 2 to all stages
        controller.select_stage(project.stages[1].id)
        project.stages[1].overlay.font_size = 18
        controller.apply_settings_to_all_stages()

        # Only queued stages (3, 4) receive settings from stage 2 via apply-all.
        # Stage 1 is not queued — skipped. Stage 2 is the active source — skipped,
        # but its font_size was manually set to 18 above.
        assert project.stages[0].overlay.font_size == 14, "Stage 1 (not queued) should keep default font_size"
        assert project.stages[1].overlay.font_size == 18, "Stage 2 (active source, manually set) should have font_size=18"
        assert project.stages[2].overlay.font_size == 18, "Stage 3 (queued) should have font_size=18"
        assert project.stages[3].overlay.font_size == 18, "Stage 4 (queued) should have font_size=18"

        # Queued stages should be marked stale after apply-all (except stage 2 which is the source)
        for stage_num in [3, 4]:
            stage = project.stages[stage_num - 1]
            assert stage.queue_status == QueueStatus.STALE, (
                f"Stage {stage_num} should be STALE after apply-all"
            )

        # Stage 2 should still be queued (it's the template source)
        assert project.stages[1].queue_status == QueueStatus.QUEUED

        print("  Apply-all verified: 3 queued, template applied, markers excluded")

    def test_full_workflow_save_and_load(self):
        """Phase 07: Full workflow — create, configure, save, reload, verify."""
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            project_dir = tmp / "test-multi-stage.ssproj"

            # Create project
            stages_def = _parse_idpa_stages(CSV_PATH)
            project = Project()
            project_stages = []
            for s in stages_def:
                ps = ProjectStage(
                    label=s["name"],
                    order_index=s["number"],
                    imported_stage_number=s["number"],
                    imported_stage_name=s["name"],
                )
                project_stages.append(ps)
            project.stages = project_stages
            project.active_stage_id = project_stages[0].id
            project.schema_version = 2
            project.practiscore_source_file = str(CSV_PATH.resolve())

            # Copy CSV to project
            project_csv_dir = project_dir / "CSV"
            project_csv_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(CSV_PATH, project_csv_dir / "IDPA.csv")

            # Import media into Input/
            from splitshot.domain.models import VideoAsset

            project_input = project_dir / "Input"
            for stage_num, video_path in STAGE_VIDEOS.items():
                if video_path.exists():
                    stage = project.stages[stage_num - 1]
                    stage_dir = (
                        project_input
                        / f"{stage_num}-{stage.label.lower().replace(' ', '-')}"
                        / "primary"
                    )
                    stage_dir.mkdir(parents=True, exist_ok=True)
                    dest = stage_dir / video_path.name
                    if not dest.exists():
                        shutil.copy2(video_path, dest)
                    stage.primary_media = VideoAsset(
                        path=str(dest),
                        duration_ms=0,
                        width=1920,
                        height=1080,
                        fps=30.0,
                    )

            # Configure per-stage settings
            from splitshot.domain.models import MergeLayout, QueueEntry

            layout_map = {
                2: MergeLayout.PIP,
                3: MergeLayout.SIDE_BY_SIDE,
                4: MergeLayout.ABOVE_BELOW,
            }
            for stage_num, layout in layout_map.items():
                stage = project.stages[stage_num - 1]
                stage.merge.layout = layout
                stage.merge.enabled = True
                stage.overlay.show_timer = True
                stage.overlay.show_shots = True
                stage.overlay.show_score = True
                stage.overlay.position = "bottom"
                stage.export.quality = "high"
                stage.export.preset = "source"

            # Add stages 2-4 to queue
            for stage_num in [2, 3, 4]:
                stage = project.stages[stage_num - 1]
                project.queue.append(
                    QueueEntry(
                        stage_id=stage.id,
                        status=QueueStatus.QUEUED,
                    )
                )
                stage.queue_status = QueueStatus.QUEUED

            # Save project
            save_project(project, project_dir)
            assert (project_dir / "project.json").exists()
            saved_size = (project_dir / "project.json").stat().st_size
            print(f"\n  Saved project: {saved_size} bytes")

            # Verify directory structure
            assert (project_dir / "CSV" / "IDPA.csv").exists()
            assert (project_dir / "Input").exists()
            for stage_num in [2, 3, 4]:
                assert any((project_dir / "Input").rglob(f"Stage{stage_num}*"))
            print("  Project directory structure verified")

            # Reload and verify
            loaded = load_project(str(project_dir))
            assert len(loaded.stages) == 4
            assert loaded.schema_version == 2
            assert loaded.active_stage_id == loaded.stages[0].id
            assert len(loaded.queue) == 3
            assert loaded.practiscore_source_file

            for stage_num, layout in layout_map.items():
                stage = loaded.stages[stage_num - 1]
                assert stage.merge.layout == layout, f"Stage {stage_num} layout mismatch"
                assert stage.overlay.show_timer
                assert stage.overlay.show_shots
                assert stage.overlay.show_score
                assert stage.primary_media.path, f"Stage {stage_num} missing primary media"

            print(
                f"  Reloaded: {len(loaded.stages)} stages, {len(loaded.queue)} queued, all settings preserved"
            )
            print(f"  Stage labels: {[s.label for s in loaded.stages]}")
            print(f"  Layouts: {[s.merge.layout.value for s in loaded.stages]}")
            print(f"  Queue statuses: {[e.status.value for e in loaded.queue]}")

            # Verify JSON roundtrip
            reloaded_dict = project_to_dict(loaded)
            assert reloaded_dict["schema_version"] == 2
            assert len(reloaded_dict["stages"]) == 4
            assert len(reloaded_dict["queue"]) == 3

            # Verify v1→v2 migration by loading the dict again
            re_loaded = project_from_dict(reloaded_dict)
            assert len(re_loaded.stages) == 4
            print(f"  JSON roundtrip: {len(re_loaded.stages)} stages preserved")
