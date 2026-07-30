from __future__ import annotations

import re
from pathlib import Path

from splitshot.domain.models import ProjectStage, QueueEntry, QueueStatus
from splitshot.ui.controller import ProjectController


def test_applying_saved_export_profile_restores_settings_and_stales_queue(
    tmp_path: Path,
) -> None:
    controller = ProjectController()
    controller.project_path = tmp_path / "profile.ssproj"
    controller.project_path.mkdir()
    stage = ProjectStage(label="Stage 1")
    controller.project.stages = [stage]
    controller.project.active_stage_id = stage.id
    controller.project.export.video_bitrate_mbps = 18.0
    profile = controller.create_output_profile("Match Export")
    controller.project.queue = [QueueEntry(stage_id=stage.id, status=QueueStatus.QUEUED)]
    stage.queue_status = QueueStatus.QUEUED

    controller.project.export.video_bitrate_mbps = 7.0
    controller.apply_output_profile(profile["output_id"])

    assert controller.project.export.video_bitrate_mbps == 18.0
    assert controller.project.queue[0].status == QueueStatus.STALE
    assert stage.queue_status == QueueStatus.STALE


def test_trimmed_derivative_filename_uses_stage_time_date_and_collision_suffix(
    tmp_path: Path,
) -> None:
    controller = ProjectController()
    controller.project_path = tmp_path / "trim.ssproj"
    controller.project_path.mkdir()
    stage = ProjectStage(label="Stage", order_index=2, imported_stage_number=7)
    controller.project.stages = [stage]
    controller.project.active_stage_id = stage.id

    first = Path(controller._trimmed_derivative_path(tmp_path / "source.mp4"))
    assert re.fullmatch(
        r"Trim_Stage7_\d{2}-\d{2}-\d{2}_\d{4}-\d{2}-\d{2}\.mp4",
        first.name,
    )
    first.touch()
    second = Path(controller._trimmed_derivative_path(tmp_path / "source.mp4"))
    assert second.stem == f"{first.stem}_2"
