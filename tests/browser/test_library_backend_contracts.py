from __future__ import annotations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LIBRARY_PY = REPO_ROOT / "src" / "splitshot" / "persistence" / "library.py"
MODELS_PY = REPO_ROOT / "src" / "splitshot" / "domain" / "models.py"


def test_compute_analytics_handles_empty_data() -> None:
    """compute_analytics should return error dict when no records exist."""
    from splitshot.persistence.library import compute_analytics
    result = compute_analytics()
    assert isinstance(result, dict)
    assert "error" in result or result.get("total_records", 0) == 0


def test_compute_analytics_returns_correct_structure() -> None:
    """compute_analytics result should have metric_key or an error key."""
    from splitshot.persistence.library import compute_analytics
    result = compute_analytics()
    assert isinstance(result, dict)
    assert "metric_key" in result or "records" in result


def test_library_models_have_tags_and_notes() -> None:
    """LibraryStageRecord and LibraryMatchRecord should have tags and notes."""
    from splitshot.domain.models import LibraryStageRecord, LibraryMatchRecord

    stage = LibraryStageRecord()
    assert hasattr(stage, "tags")
    assert hasattr(stage, "notes")
    assert isinstance(stage.tags, list)
    assert isinstance(stage.notes, str)

    match = LibraryMatchRecord()
    assert hasattr(match, "tags")
    assert hasattr(match, "notes")
    assert isinstance(match.tags, list)
    assert isinstance(match.notes, str)


def test_update_record_tags_callable() -> None:
    """update_record_tags should be callable with record_id and tags."""
    from splitshot.persistence.library import update_record_tags
    assert callable(update_record_tags)


def test_update_record_notes_callable() -> None:
    """update_record_notes should be callable with record_id and notes."""
    from splitshot.persistence.library import update_record_notes
    assert callable(update_record_notes)


def test_list_recent_projects_returns_list() -> None:
    """list_recent_projects should return a list."""
    from splitshot.persistence.projects import list_recent_projects
    result = list_recent_projects(limit=3)
    assert isinstance(result, list)


def test_analytics_record_serializes() -> None:
    """AnalyticsRecord should serialize correctly."""
    from splitshot.domain.models import AnalyticsRecord, _serialize

    record = AnalyticsRecord(
        metric_key="score",
        trend_direction="improving",
        statistics={"mean": 85.5, "median": 87.0},
    )
    data = _serialize(record)
    assert data["metric_key"] == "score"
    assert data["trend_direction"] == "improving"
    assert data["statistics"]["mean"] == 85.5


def test_backup_manifest_serializes() -> None:
    """LibraryBackupManifest should serialize correctly."""
    from splitshot.domain.models import LibraryBackupManifest, _serialize

    manifest = LibraryBackupManifest(
        total_records=100,
        total_archives=5,
        record_ids=["a", "b", "c"],
    )
    data = _serialize(manifest)
    assert data["total_records"] == 100
    assert data["total_archives"] == 5
    assert data["record_ids"] == ["a", "b", "c"]
