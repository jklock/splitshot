from __future__ import annotations

import json
from pathlib import Path
import subprocess

import numpy as np

from splitshot.analysis.detection import analyze_video_audio
from splitshot.domain.models import AspectRatio, Project
from splitshot.media.probe import probe_video
from splitshot.persistence.projects import save_project
from splitshot.persistence.workspaces import workspace_stage_path
from splitshot.ui.controller import ProjectController


ROOT = Path(__file__).resolve().parents[2]
CLIP1_VIDEO = ROOT / "docs" / "Clip1.MP4"
STAGE_VIDEO = ROOT / "tests" / "fixtures" / "media" / "stage.mp4"


def _ffprobe_json(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def _frame_rgb(path: Path, timestamp: float) -> np.ndarray:
    metadata = _ffprobe_json(path)
    video_stream = next(item for item in metadata["streams"] if item["codec_type"] == "video")
    width = int(video_stream["width"])
    height = int(video_stream["height"])
    result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
    )
    return np.frombuffer(result.stdout, dtype=np.uint8).reshape(height, width, 3)


class TestWorkspaceExportAndRecap:
    """Prove that workspace_export and workspace_recap_render produce video files."""

    def _configure_fast_export(self, project: Project) -> None:
        project.export.target_width = 160
        project.export.target_height = 90
        project.export.video_bitrate_mbps = 1
        project.export.ffmpeg_preset = "ultrafast"

    def _make_stage_project(self, video_path: Path, name: str, stage_path: Path) -> Project:
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

    def test_multi_stage_batch_export(self, synthetic_video_factory, tmp_path: Path) -> None:
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
        result = controller.workspace_export(stage_id=None, recipe="stage_output")

        assert result["success"] is True
        assert len(result["outputs"]) == 2
        for output in result["outputs"]:
            output_path = Path(output["output_path"])
            assert output_path.suffix == ".mp4"
            assert output_path.exists()
            assert output_path.stat().st_size > 0
            assert output_path.parent.name == "exports"
            assert output_path.name.endswith("-stage_output.mp4")

    def test_stage_output_recipe_honors_saved_stage_edit_settings(self, tmp_path: Path) -> None:
        controller = ProjectController()
        controller.new_workspace()
        controller.workspace_add_stage("stage_1", "Bay 1", "")
        ws_path = tmp_path / "stage_output_profile"
        controller.save_workspace(str(ws_path))

        stage_path = workspace_stage_path(ws_path, "stage_1")
        project = self._make_stage_project(CLIP1_VIDEO, "Stage 1", stage_path)
        project.export.target_width = 160
        project.export.target_height = 90
        save_project(project, stage_path)

        controller.open_workspace(str(ws_path))
        profile = controller.output_profile_create(
            "stage",
            "stage_1",
            "Single Video",
            "stage_output",
            metric_caption_preset={"lead_in_padding_ms": 0, "tail_padding_ms": 0},
        )

        result = controller.workspace_export(stage_id="stage_1", recipe="stage_output")

        assert result["success"] is True
        assert len(result["outputs"]) == 1
        output = result["outputs"][0]
        assert output["recipe"] == "stage_output"

        output_path = Path(output["output_path"])
        assert output_path.exists()
        assert output_path.parent.name == "exports"
        assert output_path.name == "stage_1-stage_output.mp4"

        output_metadata = _ffprobe_json(output_path)
        source_metadata = _ffprobe_json(CLIP1_VIDEO)
        output_duration = float(output_metadata["format"]["duration"])
        source_duration = float(source_metadata["format"]["duration"])
        assert output_duration < source_duration - 1.0
        assert output_duration > 0.3
        assert profile["profile_kind"] == "stage_output"

    def test_stage_composite_recipe_exports_real_multi_video_output(self, tmp_path: Path) -> None:
        controller = ProjectController()
        controller.new_workspace()
        controller.workspace_add_stage("stage_1", "Bay 1", "")
        ws_path = tmp_path / "stage_composite_export"
        controller.save_workspace(str(ws_path))

        stage_path = workspace_stage_path(ws_path, "stage_1")
        project = self._make_stage_project(STAGE_VIDEO, "Stage 1", stage_path)
        project.export.target_width = 160
        project.export.target_height = 90
        save_project(project, stage_path)

        controller.open_workspace(str(ws_path))
        first_clip = controller.workspace_stage_clip_add("stage_1", str(STAGE_VIDEO), "primary")[0]
        second_clip = controller.workspace_stage_clip_add("stage_1", str(CLIP1_VIDEO), "follow")[-1]
        profile = controller.output_profile_create(
            "stage",
            "stage_1",
            "Composite",
            "stage_composite",
            frame_profile="16:9",
        )
        override_one = controller.angle_director_override_cut(
            "stage_1",
            first_clip["clip_id"],
            0,
            start_ms=0,
            duration_ms=700,
            output_id=profile["output_id"],
        )
        override_two = controller.angle_director_override_cut(
            "stage_1",
            second_clip["clip_id"],
            1,
            start_ms=0,
            duration_ms=900,
            output_id=profile["output_id"],
        )
        assert override_one["success"] is True
        assert override_two["success"] is True

        result = controller.workspace_export(stage_id="stage_1", recipe="stage_composite")

        assert result["success"] is True
        assert len(result["outputs"]) == 1
        output = result["outputs"][0]
        assert output["recipe"] == "stage_composite"
        assert output["segment_count"] == 2

        output_path = Path(output["output_path"])
        assert output_path.exists()
        assert output_path.parent.name == "exports"
        assert output_path.name == "stage_1-stage_composite.mp4"
        assert output_path.stat().st_size > 0

        output_metadata = _ffprobe_json(output_path)
        output_duration = float(output_metadata["format"]["duration"])
        assert 1.2 <= output_duration <= 2.5

        early_frame = _frame_rgb(output_path, 0.2)
        late_frame = _frame_rgb(output_path, 1.0)
        assert float(early_frame.mean()) < 5.0
        assert float(late_frame.mean()) > float(early_frame.mean()) + 10.0

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
