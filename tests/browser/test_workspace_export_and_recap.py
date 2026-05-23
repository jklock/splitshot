from __future__ import annotations

from pathlib import Path

from splitshot.analysis.detection import analyze_video_audio
from splitshot.domain.models import AspectRatio, Project
from splitshot.media.probe import probe_video
from splitshot.persistence.projects import save_project
from splitshot.persistence.workspaces import workspace_stage_path
from splitshot.ui.controller import ProjectController


class TestWorkspaceExportAndRecap:
    """Prove that workspace_export and workspace_recap_render produce video files."""

    def _configure_fast_export(self, project: Project) -> None:
        project.export.target_width = 160
        project.export.target_height = 90
        project.export.video_bitrate_mbps = 1
        project.export.ffmpeg_preset = "ultrafast"

    def _make_stage_project(
        self, video_path: Path, name: str, stage_path: Path
    ) -> Project:
        project = Project(name=name)
        project.primary_video = probe_video(video_path)
        analysis = analyze_video_audio(video_path, threshold=0.35)
        project.analysis.beep_time_ms_primary = analysis.beep_time_ms
        project.analysis.shots = analysis.shots
        project.export.aspect_ratio = AspectRatio.LANDSCAPE
        self._configure_fast_export(project)
        stage_path.mkdir(parents=True, exist_ok=True)
        save_project(project, stage_path)
        return project

    def test_single_stage_export(self, synthetic_video_factory, tmp_path: Path) -> None:
        controller = ProjectController()
        controller.new_workspace()
        controller.workspace_add_stage("stage_1", "Bay 1", "")
        ws_path = tmp_path / "single_stage"
        controller.save_workspace(str(ws_path))

        video_path = synthetic_video_factory(resolution=(320, 180))
        stage_path = workspace_stage_path(ws_path, "stage_1")
        self._make_stage_project(video_path, "Stage 1", stage_path)

        controller.open_workspace(str(ws_path))
        result = controller.workspace_export()

        assert result["success"] is True
        assert len(result["outputs"]) == 1
        output_path = Path(result["outputs"][0]["output_path"])
        assert output_path.suffix == ".mp4"
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_multi_stage_batch_export(
        self, synthetic_video_factory, tmp_path: Path
    ) -> None:
        controller = ProjectController()
        controller.new_workspace()
        controller.workspace_add_stage("stage_1", "Bay 1", "")
        controller.workspace_add_stage("stage_2", "Bay 2", "")
        ws_path = tmp_path / "multi_stage"
        controller.save_workspace(str(ws_path))

        for sid, name in [("stage_1", "Stage 1"), ("stage_2", "Stage 2")]:
            video_path = synthetic_video_factory(name=name, resolution=(320, 180))
            stage_path = workspace_stage_path(ws_path, sid)
            self._make_stage_project(video_path, name, stage_path)

        controller.open_workspace(str(ws_path))
        result = controller.workspace_export(stage_id=None)

        assert result["success"] is True
        assert len(result["outputs"]) == 2
        for output in result["outputs"]:
            output_path = Path(output["output_path"])
            assert output_path.suffix == ".mp4"
            assert output_path.exists()
            assert output_path.stat().st_size > 0

    def test_recap_render(self, synthetic_video_factory, tmp_path: Path) -> None:
        controller = ProjectController()
        controller.new_workspace()
        controller.workspace_add_stage("stage_1", "Bay 1", "")
        controller.workspace_add_stage("stage_2", "Bay 2", "")
        ws_path = tmp_path / "recap"
        controller.save_workspace(str(ws_path))

        for sid, name in [("stage_1", "Stage 1"), ("stage_2", "Stage 2")]:
            video_path = synthetic_video_factory(name=name, resolution=(320, 180))
            stage_path = workspace_stage_path(ws_path, sid)
            self._make_stage_project(video_path, name, stage_path)

        controller.open_workspace(str(ws_path))
        result = controller.workspace_recap_render(
            stage_ids=["stage_1", "stage_2"], transition="cut"
        )

        assert result["success"] is True
        recap_path = Path(result["output_path"])
        assert recap_path.name == "recap.mp4"
        assert recap_path.exists()
        assert recap_path.stat().st_size > 0
