from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from splitshot.domain.models import Project, project_to_dict
from splitshot.export.presets import export_presets_for_api
from splitshot.presentation.stage import build_stage_presentation
from splitshot.scoring.logic import calculate_scoring_summary, scoring_presets_for_api
from splitshot.timeline.model import compute_split_rows


def browser_state(
    project: Project,
    status_message: str,
    practiscore_options: dict[str, Any] | None = None,
    media_cache_token: str | None = None,
) -> dict[str, Any]:
    rows = compute_split_rows(project)
    presentation = build_stage_presentation(project)
    primary_path = Path(project.primary_video.path) if project.primary_video.path else None
    secondary_path = (
        Path(project.secondary_video.path)
        if project.secondary_video is not None and project.secondary_video.path
        else None
    )
    primary_available = bool(primary_path and primary_path.exists() and primary_path.is_file())
    secondary_available = bool(secondary_path and secondary_path.exists() and secondary_path.is_file())
    return {
        "status": status_message,
        "project": project_to_dict(project),
        "metrics": asdict(presentation.metrics),
        "timing_segments": [asdict(segment) for segment in presentation.timing_segments],
        "split_rows": [asdict(row) for row in rows],
        "scoring_summary": calculate_scoring_summary(project),
        "scoring_presets": scoring_presets_for_api(),
        "practiscore_options": practiscore_options or {
            "has_source": False,
            "source_name": "",
            "detected_match_type": "",
            "stage_numbers": [],
            "competitors": [],
        },
        "export_presets": export_presets_for_api(),
        "default_project_path": str(Path.home() / "splitshot"),
        "media": {
            "primary_available": primary_available,
            "secondary_available": secondary_available,
            "primary_url": "/media/primary" if primary_available else None,
            "secondary_url": (
                "/media/secondary"
                if secondary_available
                else None
            ),
            "cache_token": media_cache_token or "",
        },
    }
