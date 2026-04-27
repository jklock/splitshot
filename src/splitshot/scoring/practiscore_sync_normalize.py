from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from splitshot.scoring.practiscore import (
    PractiScoreContext,
    PractiScoreOptions,
    PractiScoreStageImport,
    describe_practiscore_file,
    infer_practiscore_context,
    import_practiscore_stage,
)
from splitshot.scoring.practiscore_web_extract import (
    NORMALIZATION_IMPORT_FAILURE_ERROR,
    PractiScoreSyncError,
)


_SUPPORTED_SOURCE_SUFFIXES = {".csv", ".txt"}


@dataclass(frozen=True, slots=True)
class NormalizedPractiScoreSyncImport:
    source_path: Path
    source_name: str
    options: PractiScoreOptions
    resolved_context: PractiScoreContext
    stage_import: PractiScoreStageImport


def normalize_downloaded_practiscore_artifact(
    path: str | Path,
    *,
    source_name: str | None = None,
    match_type: str | None = None,
    stage_number: int | None = None,
    competitor_name: str | None = None,
    competitor_place: int | None = None,
) -> NormalizedPractiScoreSyncImport:
    resolved_path = Path(path)
    display_name = source_name or resolved_path.name
    if resolved_path.suffix.lower() not in _SUPPORTED_SOURCE_SUFFIXES:
        raise PractiScoreSyncError(
            NORMALIZATION_IMPORT_FAILURE_ERROR,
            f"Downloaded PractiScore artifact must be a CSV or TXT file: {resolved_path.name}.",
            details={"path": str(resolved_path)},
        )

    try:
        options = describe_practiscore_file(resolved_path, source_name=display_name)
        try:
            resolved_context = infer_practiscore_context(
                resolved_path,
                match_type=match_type,
                stage_number=stage_number,
                competitor_name=competitor_name,
                competitor_place=competitor_place,
            )
        except ValueError:
            resolved_context = infer_practiscore_context(resolved_path)
        stage_import = import_practiscore_stage(
            resolved_path,
            match_type=resolved_context.match_type,
            stage_number=resolved_context.stage_number,
            competitor_name=resolved_context.competitor_name,
            competitor_place=resolved_context.competitor_place,
            source_name=display_name,
        )
    except (OSError, ValueError) as exc:
        raise PractiScoreSyncError(
            NORMALIZATION_IMPORT_FAILURE_ERROR,
            f"Unable to normalize the downloaded PractiScore artifact: {exc}",
            details={
                "path": str(resolved_path),
                "source_name": display_name,
            },
        ) from exc

    return NormalizedPractiScoreSyncImport(
        source_path=resolved_path,
        source_name=display_name,
        options=options,
        resolved_context=resolved_context,
        stage_import=stage_import,
    )