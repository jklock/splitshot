from __future__ import annotations

import json
from pathlib import Path

import pytest

from splitshot.repair import apply_stage_queue_recovery, recover_project_payload


def _stage(stage_id: str, label: str, media_path: str = "") -> dict:
    return {
        "id": stage_id,
        "label": label,
        "primary_media": {"path": media_path},
        "primary_trim_derivative": {},
        "added_media": [],
        "analysis": {"shots": []},
        "scoring": {"competitor_name": "John Klockenkemper", "raw_time_s": 12.34},
        "overlay": {"show_timer": True},
        "ignore_global_settings": True,
        "queue_status": "queued",
    }


def test_recovery_fills_only_missing_stage_owned_state_and_rebuilds_snapshot(tmp_path: Path) -> None:
    media = tmp_path / "Stage2.mp4"
    media.write_bytes(b"video")
    live = _stage("stage-2", "Stage 2")
    queued = _stage("stage-2", "Stage 2", str(media))
    queued["analysis"] = {"shots": [{"id": "shot-1", "time_ms": 4567}]}
    queued["scoring"] = {"competitor_name": "Wrong Person", "raw_time_s": 99.0}
    queued["overlay"] = {"show_timer": False}
    payload = {
        "active_stage_id": "stage-2",
        "stages": [live],
        "queue": [{"stage_id": "stage-2", "status": "done", "snapshot": queued}],
    }

    repaired, labels = recover_project_payload(payload)

    stage = repaired["stages"][0]
    entry = repaired["queue"][0]
    assert labels == ["Stage 2"]
    assert stage["primary_media"]["path"] == str(media)
    assert stage["analysis"] == queued["analysis"]
    assert stage["scoring"] == live["scoring"]
    assert stage["overlay"] == live["overlay"]
    assert stage["ignore_global_settings"] is True
    assert entry["status"] == "stale"
    assert entry["snapshot"] == stage
    assert payload["stages"][0]["primary_media"]["path"] == ""


def test_recovery_never_overwrites_non_empty_live_stage(tmp_path: Path) -> None:
    live_media = tmp_path / "live.mp4"
    queued_media = tmp_path / "queued.mp4"
    live_media.write_bytes(b"live")
    queued_media.write_bytes(b"queued")
    live = _stage("stage-1", "Stage 1", str(live_media))
    queued = _stage("stage-1", "Stage 1", str(queued_media))
    payload = {"stages": [live], "queue": [{"stage_id": "stage-1", "snapshot": queued}]}

    repaired, labels = recover_project_payload(payload)

    assert labels == []
    assert repaired == payload


def test_recovery_refuses_missing_primary_media(tmp_path: Path) -> None:
    live = _stage("stage-3", "Stage 3")
    queued = _stage("stage-3", "Stage 3", str(tmp_path / "missing.mp4"))
    payload = {"stages": [live], "queue": [{"stage_id": "stage-3", "snapshot": queued}]}

    with pytest.raises(FileNotFoundError, match="missing.mp4"):
        recover_project_payload(payload)


def test_apply_recovery_creates_backup_and_preserves_original_payload(tmp_path: Path) -> None:
    media = tmp_path / "stage.mp4"
    media.write_bytes(b"video")
    live = _stage("stage-4", "Stage 4")
    queued = _stage("stage-4", "Stage 4", str(media))
    payload = {"stages": [live], "queue": [{"stage_id": "stage-4", "snapshot": queued}]}
    project_file = tmp_path / "project.json"
    project_file.write_text(json.dumps(payload), encoding="utf-8")

    backup, labels = apply_stage_queue_recovery(project_file)

    assert labels == ["Stage 4"]
    assert backup is not None and backup.is_file()
    assert json.loads(backup.read_text(encoding="utf-8")) == payload
    assert json.loads(project_file.read_text(encoding="utf-8"))["stages"][0]["primary_media"][
        "path"
    ] == str(media)
