"""PractiScore remote session and sync helpers for the shared controller lane."""

from __future__ import annotations

import json
import re
import shutil
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Protocol

from splitshot.scoring.practiscore_sync_normalize import (
    normalize_downloaded_practiscore_artifact,
)
from splitshot.scoring.practiscore_web_extract import (
    EXPIRED_AUTHENTICATION_ERROR,
    MALFORMED_REMOTE_RESPONSE_ERROR,
    MISSING_REQUIRED_REMOTE_ARTIFACT_ERROR,
    NORMALIZATION_IMPORT_FAILURE_ERROR,
    PractiScoreSyncError,
    RemotePractiScoreMatch,
    SelectedRemoteMatchArtifacts,
    TRANSIENT_NETWORK_FAILURE_ERROR,
    discover_remote_matches,
    download_remote_match_artifacts,
    practiscore_sync_audit_root,
)


PRACTISCORE_SYNC_UNSET = object()
PRACTISCORE_FILE_SUFFIXES = frozenset({".csv", ".txt"})
VALID_PRACTISCORE_SYNC_STATES = {
    "idle",
    "discovering_matches",
    "match_list_ready",
    "importing_selected_match",
    "success",
    "error",
}


class _PractiScoreController(Protocol):
    _practiscore_session_payload: dict[str, object]
    _practiscore_sync_payload: dict[str, object]
    _practiscore_source_path: Path | None
    project: Any

    def _set_status(self, message: str) -> None: ...

    def _set_practiscore_session_payload(self, payload: dict[str, object]) -> None: ...

    def _set_practiscore_sync_state(
        self,
        state: str,
        message: str,
        *,
        matches: list[RemotePractiScoreMatch] | list[dict[str, object]] | None = None,
        selected_remote_id: str | None | object = PRACTISCORE_SYNC_UNSET,
        error_category: str = "",
        details: dict[str, object] | None = None,
    ) -> None: ...

    def _practiscore_route_payload(self) -> dict[str, object]: ...

    def import_practiscore_file(
        self,
        path: str,
        source_name: str | None = None,
    ) -> None: ...


def default_practiscore_session_payload() -> dict[str, object]:
    return {
        "state": "not_authenticated",
        "message": "Connect PractiScore to use your browser session for background sync.",
        "details": {},
    }


def default_practiscore_sync_payload() -> dict[str, object]:
    return {
        "state": "idle",
        "message": "No remote PractiScore sync activity yet.",
        "matches": [],
        "selected_remote_id": None,
        "error_category": "",
        "details": {},
    }


def practiscore_session_payload_from_status(status: object) -> dict[str, object]:
    payload = default_practiscore_session_payload()
    if isinstance(status, dict):
        source = status
    else:
        to_dict = getattr(status, "to_dict", None)
        if callable(to_dict):
            source = to_dict()
        else:
            source = {
                "state": getattr(status, "state", payload["state"]),
                "message": getattr(status, "message", payload["message"]),
                "details": getattr(status, "details", payload["details"]),
            }
    payload["state"] = str(source.get("state") or payload["state"])
    payload["message"] = str(source.get("message") or payload["message"])
    details = source.get("details")
    payload["details"] = dict(details) if isinstance(details, dict) else {}
    return payload


def practiscore_session_payload_from_manager(
    practiscore_session: object,
) -> dict[str, object]:
    current_status = getattr(practiscore_session, "current_status", None)
    if callable(current_status):
        return practiscore_session_payload_from_status(current_status())
    serialize_status = getattr(practiscore_session, "serialize_status", None)
    if callable(serialize_status):
        return practiscore_session_payload_from_status(serialize_status())
    return default_practiscore_session_payload()


def serialize_practiscore_remote_matches(
    matches: object,
) -> list[dict[str, object]]:
    if not isinstance(matches, list):
        return []
    payloads: list[dict[str, object]] = []
    for item in matches:
        match = (
            item
            if isinstance(item, RemotePractiScoreMatch)
            else RemotePractiScoreMatch.from_dict(item)
        )
        if match is None:
            continue
        payloads.append(match.to_dict())
    return payloads


def practiscore_remote_match_objects(matches: object) -> list[RemotePractiScoreMatch]:
    if not isinstance(matches, list):
        return []
    resolved: list[RemotePractiScoreMatch] = []
    for item in matches:
        match = (
            item
            if isinstance(item, RemotePractiScoreMatch)
            else RemotePractiScoreMatch.from_dict(item)
        )
        if match is not None:
            resolved.append(match)
    return resolved


def practiscore_error_category_from_exception(exc: BaseException) -> str:
    message = str(exc).lower()
    if any(
        token in message
        for token in (
            "timeout",
            "timed out",
            "network",
            "fetch",
            "net::",
            "connection",
        )
    ):
        return TRANSIENT_NETWORK_FAILURE_ERROR
    return MALFORMED_REMOTE_RESPONSE_ERROR


def build_practiscore_sync_payload(
    existing_payload: dict[str, object],
    state: str,
    message: str,
    *,
    matches: list[RemotePractiScoreMatch] | list[dict[str, object]] | None = None,
    selected_remote_id: str | None | object = PRACTISCORE_SYNC_UNSET,
    error_category: str = "",
    details: dict[str, object] | None = None,
) -> dict[str, object]:
    next_matches = (
        serialize_practiscore_remote_matches(matches)
        if matches is not None
        else serialize_practiscore_remote_matches(existing_payload.get("matches"))
    )
    next_selected_remote_id = (
        existing_payload.get("selected_remote_id")
        if selected_remote_id is PRACTISCORE_SYNC_UNSET
        else (None if selected_remote_id in {None, ""} else str(selected_remote_id))
    )
    return {
        "state": state if state in VALID_PRACTISCORE_SYNC_STATES else "error",
        "message": str(message),
        "matches": next_matches,
        "selected_remote_id": next_selected_remote_id,
        "error_category": str(error_category or ""),
        "details": deepcopy(details or {}),
    }


def _controller_module_callable(name: str, default: object) -> object:
    controller_module = sys.modules.get("splitshot.ui.controller")
    override = getattr(controller_module, name, None) if controller_module is not None else None
    return override if callable(override) else default


def _safe_sync_cache_component(value: str, *, default: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip()).strip(".-")
    return cleaned or default


def _remote_match_from_host_payload(
    host_payload: dict[str, object],
    remote_id: str,
) -> RemotePractiScoreMatch:
    match = RemotePractiScoreMatch.from_dict(host_payload.get("match"))
    if match is None:
        summary_snapshot = host_payload.get("summary_snapshot")
        if isinstance(summary_snapshot, dict):
            match = RemotePractiScoreMatch.from_dict(summary_snapshot.get("remote_match"))
    if match is not None:
        return match
    label = (
        str(host_payload.get("label") or host_payload.get("source_name") or remote_id).strip()
        or remote_id
    )
    event_name = str(host_payload.get("event_name") or label).strip() or label
    event_date = str(host_payload.get("event_date") or "").strip()
    match_type = str(host_payload.get("match_type") or "").strip()
    return RemotePractiScoreMatch(
        remote_id=remote_id,
        label=label,
        match_type=match_type,
        event_name=event_name,
        event_date=event_date,
    )


def _selected_remote_match_artifacts_from_host_payload(
    host_payload: object,
    remote_id: str,
    *,
    app_dir: str | Path | None = None,
) -> SelectedRemoteMatchArtifacts:
    if not isinstance(host_payload, dict):
        raise PractiScoreSyncError(
            MALFORMED_REMOTE_RESPONSE_ERROR,
            "Electron PractiScore host did not provide a selected-match payload.",
            details={"remote_id": remote_id},
        )

    artifact_text = host_payload.get("artifact_text")
    if artifact_text in {None, ""}:
        raise PractiScoreSyncError(
            MISSING_REQUIRED_REMOTE_ARTIFACT_ERROR,
            f"PractiScore did not expose a CSV or TXT artifact for remote match {remote_id}.",
            details={"remote_id": remote_id},
        )

    source_name = str(host_payload.get("source_name") or "").strip() or f"remote-{remote_id}.csv"
    source_name = Path(source_name).name or f"remote-{remote_id}.csv"
    if Path(source_name).suffix.lower() not in PRACTISCORE_FILE_SUFFIXES:
        raise PractiScoreSyncError(
            MISSING_REQUIRED_REMOTE_ARTIFACT_ERROR,
            f"PractiScore did not expose a CSV or TXT artifact for remote match {remote_id}.",
            details={"remote_id": remote_id, "source_name": source_name},
        )

    remote_match = _remote_match_from_host_payload(host_payload, remote_id)
    cache_dir = practiscore_sync_audit_root(app_dir) / _safe_sync_cache_component(
        remote_id,
        default="selected-match",
    )
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    source_artifact_path = cache_dir / source_name
    source_artifact_path.write_text(str(artifact_text), encoding="utf-8")

    html_path = cache_dir / "selected-match.html"
    html_path.write_text(str(host_payload.get("html") or ""), encoding="utf-8")

    summary_path = cache_dir / "summary.json"
    summary_snapshot = (
        deepcopy(host_payload.get("summary_snapshot"))
        if isinstance(host_payload.get("summary_snapshot"), dict)
        else {}
    )
    summary_snapshot.setdefault("remote_match", remote_match.to_dict())
    artifact_summary = summary_snapshot.get("artifact")
    if not isinstance(artifact_summary, dict):
        artifact_summary = {}
    artifact_summary.setdefault("source_name", source_name)
    artifact_summary["source_artifact_path"] = str(source_artifact_path)
    artifact_summary["html_path"] = str(html_path)
    summary_snapshot["artifact"] = artifact_summary
    summary_path.write_text(
        json.dumps(summary_snapshot, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return SelectedRemoteMatchArtifacts(
        match=remote_match,
        cache_dir=cache_dir,
        source_artifact_path=source_artifact_path,
        source_name=source_name,
        html_path=html_path,
        summary_path=summary_path,
        summary_snapshot=summary_snapshot,
    )


def list_practiscore_matches(
    controller: _PractiScoreController,
    practiscore_session: object,
) -> dict[str, object]:
    session_payload = practiscore_session_payload_from_manager(practiscore_session)
    controller._set_practiscore_session_payload(session_payload)
    if controller._practiscore_session_payload.get("state") != "authenticated_ready":
        message = str(
            controller._practiscore_session_payload.get("message")
            or "PractiScore session is not ready."
        )
        controller._set_status(message)
        controller._set_practiscore_sync_state(
            "error",
            message,
            matches=[],
            error_category=EXPIRED_AUTHENTICATION_ERROR,
            details={"route": "/api/practiscore/matches"},
        )
        return controller._practiscore_route_payload()

    controller._set_status("Discovering remote PractiScore matches...")
    controller._set_practiscore_sync_state(
        "discovering_matches",
        "Discovering remote PractiScore matches...",
        matches=[],
    )
    discover_matches = _controller_module_callable(
        "discover_remote_matches",
        discover_remote_matches,
    )
    try:
        browser_context = practiscore_session.require_authenticated_browser()
        matches = discover_matches(browser_context)
    except PractiScoreSyncError as exc:
        controller._set_status(str(exc))
        controller._set_practiscore_sync_state(
            "error",
            str(exc),
            matches=[],
            error_category=exc.category,
            details=exc.details,
        )
        controller._set_practiscore_session_payload(
            practiscore_session_payload_from_manager(practiscore_session)
        )
        return controller._practiscore_route_payload()
    except Exception as exc:  # noqa: BLE001
        session_payload = practiscore_session_payload_from_manager(practiscore_session)
        controller._set_practiscore_session_payload(session_payload)
        category = (
            EXPIRED_AUTHENTICATION_ERROR
            if controller._practiscore_session_payload.get("state") != "authenticated_ready"
            else practiscore_error_category_from_exception(exc)
        )
        message = str(exc) or "Unable to list remote PractiScore matches."
        controller._set_status(message)
        controller._set_practiscore_sync_state(
            "error",
            message,
            matches=[],
            error_category=category,
            details={"route": "/api/practiscore/matches"},
        )
        return controller._practiscore_route_payload()

    match_payloads = serialize_practiscore_remote_matches(matches)
    previous_selected_remote_id = controller._practiscore_sync_payload.get("selected_remote_id")
    selected_remote_id = (
        previous_selected_remote_id
        if any(
            payload.get("remote_id") == previous_selected_remote_id for payload in match_payloads
        )
        else None
    )
    message = (
        "No remote PractiScore matches found."
        if not match_payloads
        else f"Found {len(match_payloads)} remote PractiScore match(es)."
    )
    controller._set_status(message)
    controller._set_practiscore_sync_state(
        "match_list_ready",
        message,
        matches=match_payloads,
        selected_remote_id=selected_remote_id,
        details={"match_count": len(match_payloads)},
    )
    controller._set_practiscore_session_payload(
        practiscore_session_payload_from_manager(practiscore_session)
    )
    return controller._practiscore_route_payload()


def list_practiscore_matches_from_host_payload(
    controller: _PractiScoreController,
    session_payload: dict[str, object] | object,
    matches_payload: list[dict[str, object]] | list[RemotePractiScoreMatch] | object,
) -> dict[str, object]:
    controller._set_practiscore_session_payload(
        session_payload
        if isinstance(session_payload, dict)
        else default_practiscore_session_payload()
    )
    if controller._practiscore_session_payload.get("state") != "authenticated_ready":
        message = str(
            controller._practiscore_session_payload.get("message")
            or "PractiScore session is not ready."
        )
        controller._set_status(message)
        controller._set_practiscore_sync_state(
            "error",
            message,
            matches=[],
            error_category=EXPIRED_AUTHENTICATION_ERROR,
            details={"route": "/api/practiscore/matches"},
        )
        return controller._practiscore_route_payload()

    match_payloads = serialize_practiscore_remote_matches(matches_payload)
    previous_selected_remote_id = controller._practiscore_sync_payload.get("selected_remote_id")
    selected_remote_id = (
        previous_selected_remote_id
        if any(
            payload.get("remote_id") == previous_selected_remote_id for payload in match_payloads
        )
        else None
    )
    message = (
        "No remote PractiScore matches found."
        if not match_payloads
        else f"Found {len(match_payloads)} remote PractiScore match(es)."
    )
    controller._set_status(message)
    controller._set_practiscore_sync_state(
        "match_list_ready",
        message,
        matches=match_payloads,
        selected_remote_id=selected_remote_id,
        details={"match_count": len(match_payloads)},
    )
    return controller._practiscore_route_payload()


def start_practiscore_sync(
    controller: _PractiScoreController,
    payload: dict[str, object],
    practiscore_session: object,
) -> dict[str, object]:
    remote_id = str(payload.get("remote_id") or "").strip()
    if not remote_id:
        message = "A remote PractiScore match must be selected before import."
        controller._set_status(message)
        controller._set_practiscore_sync_state(
            "error",
            message,
            error_category=MALFORMED_REMOTE_RESPONSE_ERROR,
            details={"route": "/api/practiscore/sync/start"},
        )
        return controller._practiscore_route_payload()

    session_payload = practiscore_session_payload_from_manager(practiscore_session)
    controller._set_practiscore_session_payload(session_payload)
    if controller._practiscore_session_payload.get("state") != "authenticated_ready":
        message = str(
            controller._practiscore_session_payload.get("message")
            or "PractiScore session is not ready."
        )
        controller._set_status(message)
        controller._set_practiscore_sync_state(
            "error",
            message,
            selected_remote_id=remote_id,
            error_category=EXPIRED_AUTHENTICATION_ERROR,
            details={
                "route": "/api/practiscore/sync/start",
                "remote_id": remote_id,
            },
        )
        return controller._practiscore_route_payload()

    existing_matches = practiscore_remote_match_objects(
        controller._practiscore_sync_payload.get("matches")
    )
    controller._set_status("Importing selected remote PractiScore match...")
    controller._set_practiscore_sync_state(
        "importing_selected_match",
        "Importing selected remote PractiScore match...",
        matches=existing_matches,
        selected_remote_id=remote_id,
    )
    try:
        browser_context = practiscore_session.require_authenticated_browser()
        download_match_artifacts = _controller_module_callable(
            "download_remote_match_artifacts",
            download_remote_match_artifacts,
        )
        app_dir = getattr(
            getattr(practiscore_session, "profile_paths", None),
            "app_dir",
            None,
        )
        artifacts = download_match_artifacts(
            browser_context,
            remote_id,
            practiscore_sync_audit_root(app_dir),
            match_catalog=existing_matches,
        )
        normalize_downloaded_practiscore_artifact(
            artifacts.source_artifact_path,
            source_name=artifacts.source_name,
            match_type=controller.project.scoring.match_type or None,
            stage_number=controller.project.scoring.stage_number,
            competitor_name=controller.project.scoring.competitor_name or None,
            competitor_place=controller.project.scoring.competitor_place,
        )
        controller.import_practiscore_file(
            str(artifacts.source_artifact_path),
            source_name=artifacts.source_name,
        )
    except PractiScoreSyncError as exc:
        controller._set_status(str(exc))
        controller._set_practiscore_sync_state(
            "error",
            str(exc),
            matches=existing_matches,
            selected_remote_id=remote_id,
            error_category=exc.category,
            details={**exc.details, "remote_id": remote_id},
        )
        controller._set_practiscore_session_payload(
            practiscore_session_payload_from_manager(practiscore_session)
        )
        return controller._practiscore_route_payload()
    except ValueError as exc:
        message = str(exc) or "Unable to normalize the downloaded PractiScore artifact."
        controller._set_status(message)
        controller._set_practiscore_sync_state(
            "error",
            message,
            matches=existing_matches,
            selected_remote_id=remote_id,
            error_category=NORMALIZATION_IMPORT_FAILURE_ERROR,
            details={"remote_id": remote_id},
        )
        controller._set_practiscore_session_payload(
            practiscore_session_payload_from_manager(practiscore_session)
        )
        return controller._practiscore_route_payload()
    except Exception as exc:  # noqa: BLE001
        session_payload = practiscore_session_payload_from_manager(practiscore_session)
        controller._set_practiscore_session_payload(session_payload)
        category = (
            EXPIRED_AUTHENTICATION_ERROR
            if controller._practiscore_session_payload.get("state") != "authenticated_ready"
            else practiscore_error_category_from_exception(exc)
        )
        message = str(exc) or "Unable to import the selected remote PractiScore match."
        controller._set_status(message)
        controller._set_practiscore_sync_state(
            "error",
            message,
            matches=existing_matches,
            selected_remote_id=remote_id,
            error_category=category,
            details={"remote_id": remote_id},
        )
        return controller._practiscore_route_payload()

    imported_stage = controller.project.scoring.imported_stage
    updated_matches = serialize_practiscore_remote_matches(existing_matches)
    if not any(item.get("remote_id") == artifacts.match.remote_id for item in updated_matches):
        updated_matches.append(artifacts.match.to_dict())
    message = f"Imported remote PractiScore match {artifacts.match.label}."
    controller._set_practiscore_sync_state(
        "success",
        message,
        matches=updated_matches,
        selected_remote_id=remote_id,
        details={
            "remote_id": remote_id,
            "label": artifacts.match.label,
            "cache_dir": str(artifacts.cache_dir),
            "source_artifact_path": str(artifacts.source_artifact_path),
            "html_path": str(artifacts.html_path),
            "summary_path": str(artifacts.summary_path),
            "staged_source_path": ""
            if controller._practiscore_source_path is None
            else str(controller._practiscore_source_path),
            "imported_stage_number": (
                None if imported_stage is None else imported_stage.stage_number
            ),
        },
    )
    controller._set_practiscore_session_payload(
        practiscore_session_payload_from_manager(practiscore_session)
    )
    return controller._practiscore_route_payload()


def start_practiscore_sync_from_host_payload(
    controller: _PractiScoreController,
    payload: dict[str, object],
    session_payload: dict[str, object] | object,
    *,
    app_dir: str | Path | None = None,
) -> dict[str, object]:
    remote_id = str(payload.get("remote_id") or "").strip()
    if not remote_id:
        message = "A remote PractiScore match must be selected before import."
        controller._set_status(message)
        controller._set_practiscore_sync_state(
            "error",
            message,
            error_category=MALFORMED_REMOTE_RESPONSE_ERROR,
            details={"route": "/api/practiscore/sync/start"},
        )
        return controller._practiscore_route_payload()

    controller._set_practiscore_session_payload(
        session_payload
        if isinstance(session_payload, dict)
        else default_practiscore_session_payload()
    )
    if controller._practiscore_session_payload.get("state") != "authenticated_ready":
        message = str(
            controller._practiscore_session_payload.get("message")
            or "PractiScore session is not ready."
        )
        controller._set_status(message)
        controller._set_practiscore_sync_state(
            "error",
            message,
            selected_remote_id=remote_id,
            error_category=EXPIRED_AUTHENTICATION_ERROR,
            details={
                "route": "/api/practiscore/sync/start",
                "remote_id": remote_id,
            },
        )
        return controller._practiscore_route_payload()

    existing_matches = practiscore_remote_match_objects(
        controller._practiscore_sync_payload.get("matches")
    )
    controller._set_status("Importing selected remote PractiScore match...")
    controller._set_practiscore_sync_state(
        "importing_selected_match",
        "Importing selected remote PractiScore match...",
        matches=existing_matches,
        selected_remote_id=remote_id,
    )
    try:
        artifacts = _selected_remote_match_artifacts_from_host_payload(
            payload.get("__electron_host_download"),
            remote_id,
            app_dir=app_dir,
        )
        normalize_downloaded_practiscore_artifact(
            artifacts.source_artifact_path,
            source_name=artifacts.source_name,
            match_type=controller.project.scoring.match_type or None,
            stage_number=controller.project.scoring.stage_number,
            competitor_name=controller.project.scoring.competitor_name or None,
            competitor_place=controller.project.scoring.competitor_place,
        )
        controller.import_practiscore_file(
            str(artifacts.source_artifact_path),
            source_name=artifacts.source_name,
        )
    except PractiScoreSyncError as exc:
        controller._set_status(str(exc))
        controller._set_practiscore_sync_state(
            "error",
            str(exc),
            matches=existing_matches,
            selected_remote_id=remote_id,
            error_category=exc.category,
            details={**exc.details, "remote_id": remote_id},
        )
        return controller._practiscore_route_payload()
    except ValueError as exc:
        message = str(exc) or "Unable to normalize the downloaded PractiScore artifact."
        controller._set_status(message)
        controller._set_practiscore_sync_state(
            "error",
            message,
            matches=existing_matches,
            selected_remote_id=remote_id,
            error_category=NORMALIZATION_IMPORT_FAILURE_ERROR,
            details={"remote_id": remote_id},
        )
        return controller._practiscore_route_payload()
    except Exception as exc:  # noqa: BLE001
        message = str(exc) or "Unable to import the selected remote PractiScore match."
        controller._set_status(message)
        controller._set_practiscore_sync_state(
            "error",
            message,
            matches=existing_matches,
            selected_remote_id=remote_id,
            error_category=practiscore_error_category_from_exception(exc),
            details={"remote_id": remote_id},
        )
        return controller._practiscore_route_payload()

    imported_stage = controller.project.scoring.imported_stage
    updated_matches = serialize_practiscore_remote_matches(existing_matches)
    if not any(item.get("remote_id") == artifacts.match.remote_id for item in updated_matches):
        updated_matches.append(artifacts.match.to_dict())
    message = f"Imported remote PractiScore match {artifacts.match.label}."
    controller._set_practiscore_sync_state(
        "success",
        message,
        matches=updated_matches,
        selected_remote_id=remote_id,
        details={
            "remote_id": remote_id,
            "label": artifacts.match.label,
            "cache_dir": str(artifacts.cache_dir),
            "source_artifact_path": str(artifacts.source_artifact_path),
            "html_path": str(artifacts.html_path),
            "summary_path": str(artifacts.summary_path),
            "staged_source_path": ""
            if controller._practiscore_source_path is None
            else str(controller._practiscore_source_path),
            "imported_stage_number": (
                None if imported_stage is None else imported_stage.stage_number
            ),
        },
    )
    return controller._practiscore_route_payload()
