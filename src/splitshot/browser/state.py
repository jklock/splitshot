from __future__ import annotations

from dataclasses import asdict
from typing import Any

from splitshot.domain.models import Project, project_to_dict
from splitshot.presentation.stage import build_stage_presentation
from splitshot.scoring.logic import calculate_scoring_summary, scoring_presets_for_api
from splitshot.timeline.model import compute_split_rows


def browser_state(project: Project, status_message: str) -> dict[str, Any]:
    rows = compute_split_rows(project)
    presentation = build_stage_presentation(project)
    return {
        "status": status_message,
        "project": project_to_dict(project),
        "metrics": asdict(presentation.metrics),
        "timing_segments": [asdict(segment) for segment in presentation.timing_segments],
        "split_rows": [asdict(row) for row in rows],
        "scoring_summary": calculate_scoring_summary(project),
        "scoring_presets": scoring_presets_for_api(),
        "media": {
            "primary_available": bool(project.primary_video.path),
            "secondary_available": bool(project.secondary_video and project.secondary_video.path),
            "primary_url": "/media/primary" if project.primary_video.path else None,
            "secondary_url": (
                "/media/secondary"
                if project.secondary_video is not None and project.secondary_video.path
                else None
            ),
        },
    }
