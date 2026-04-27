from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
from typing import Any, Sequence
from urllib.parse import urlparse

import splitshot.config as splitshot_config


EXPIRED_AUTHENTICATION_ERROR = "expired_authentication"
TRANSIENT_NETWORK_FAILURE_ERROR = "transient_network_failure"
MALFORMED_REMOTE_RESPONSE_ERROR = "malformed_remote_response"
MISSING_REQUIRED_REMOTE_ARTIFACT_ERROR = "missing_required_remote_artifact"
NORMALIZATION_IMPORT_FAILURE_ERROR = "normalization_import_failure"

_SUPPORTED_SOURCE_SUFFIXES = {".csv", ".txt"}
_SYNC_AUDIT_DIRNAME = "sync-audit"
_PRACTISCORE_MATCH_SEARCH_URL = "https://practiscore.com/search/matches"
_TIMEOUT_TOKENS = (
    "timeout",
    "timed out",
    "network",
    "fetch",
    "net::",
    "connection",
    "econn",
    "socket",
)

_DISCOVER_MATCHES_SCRIPT = r"""
() => {
  /* splitshot-practiscore-discover-matches */
  const normalizeText = (value) => String(value || "").replace(/\s+/g, " ").trim();
    const isMatchLikeHref = (value) => {
        const href = String(value || "").toLowerCase();
        return /\/(?:results?|match(?:es)?|events?)\b/.test(href)
            || /(?:remote_id|match_id|result_id|event_id)=/i.test(href);
    };
  const resolveRemoteId = (value) => {
    const text = String(value || "");
    const queryMatch = text.match(/(?:remote_id|match_id|result_id|event_id)=([^&#]+)/i);
    if (queryMatch) {
      return decodeURIComponent(queryMatch[1]);
    }
    const resultMatch = text.match(/\/(?:results?|match|event)s?\/(?:new\/)?([^/?#]+)/i);
    if (resultMatch) {
      return resultMatch[1];
    }
    const trailingMatch = text.match(/\/([^/?#]+)(?:[?#].*)?$/);
    return trailingMatch ? trailingMatch[1] : "";
  };
  const inferMatchType = (value) => {
    const lowered = normalizeText(value).toLowerCase();
    if (lowered.includes("idpa")) {
      return "idpa";
    }
    if (lowered.includes("ipsc")) {
      return "ipsc";
    }
    if (lowered.includes("uspsa")) {
      return "uspsa";
    }
    return "";
  };
  const inferEventDate = (value) => {
    const text = normalizeText(value);
    const match = text.match(/\b(\d{4}-\d{2}-\d{2}|\d{1,2}\/\d{1,2}\/\d{2,4}|[A-Z][a-z]{2,8}\s+\d{1,2},\s+\d{4})\b/);
    return match ? match[1] : "";
  };
  const matches = [];
  const seen = new Set();
  const candidates = Array.from(document.querySelectorAll("[data-remote-id], a[href]"));
  for (const node of candidates) {
    const isAnchor = typeof node.matches === "function" && node.matches("a[href]");
    const anchor = isAnchor ? node : (typeof node.querySelector === "function" ? node.querySelector("a[href]") : null);
    const detailsUrl = anchor && anchor.href ? anchor.href : "";
        const explicitRemoteId = normalizeText(typeof node.getAttribute === "function" ? node.getAttribute("data-remote-id") : "");
        if (!explicitRemoteId && !isMatchLikeHref(detailsUrl)) {
            continue;
        }
    const container = typeof node.closest === "function"
      ? (node.closest("[data-remote-id], tr, li, article, section, .match-card, .event-card") || node)
      : node;
        const remoteId = explicitRemoteId
      || resolveRemoteId(detailsUrl)
      || resolveRemoteId(typeof node.getAttribute === "function" ? node.getAttribute("href") : "");
    if (!remoteId || seen.has(remoteId)) {
      continue;
    }
    const containerText = normalizeText(container && container.textContent ? container.textContent : "");
    const label = normalizeText(typeof node.getAttribute === "function" ? node.getAttribute("data-label") : "")
      || normalizeText(anchor && anchor.textContent ? anchor.textContent : "")
      || containerText
      || remoteId;
    const eventName = normalizeText(typeof node.getAttribute === "function" ? node.getAttribute("data-event-name") : "")
      || label;
    const eventDate = normalizeText(typeof node.getAttribute === "function" ? node.getAttribute("data-event-date") : "")
      || inferEventDate(containerText);
    const matchType = normalizeText(typeof node.getAttribute === "function" ? node.getAttribute("data-match-type") : "")
      || inferMatchType(containerText);
    matches.push({
      remote_id: remoteId,
      label,
      match_type: matchType,
      event_name: eventName,
      event_date: eventDate,
      details_url: detailsUrl,
    });
    seen.add(remoteId);
  }
  return matches;
}
"""

_SELECT_MATCH_SCRIPT = r"""
(remoteId) => {
  /* splitshot-practiscore-select-match */
  const normalizeText = (value) => String(value || "").replace(/\s+/g, " ").trim();
    const isMatchLikeHref = (value) => {
        const href = String(value || "").toLowerCase();
        return /\/(?:results?|match(?:es)?|events?)\b/.test(href)
            || /(?:remote_id|match_id|result_id|event_id)=/i.test(href);
    };
  const resolveRemoteId = (value) => {
    const text = String(value || "");
    const queryMatch = text.match(/(?:remote_id|match_id|result_id|event_id)=([^&#]+)/i);
    if (queryMatch) {
      return decodeURIComponent(queryMatch[1]);
    }
    const resultMatch = text.match(/\/(?:results?|match|event)s?\/(?:new\/)?([^/?#]+)/i);
    if (resultMatch) {
      return resultMatch[1];
    }
    const trailingMatch = text.match(/\/([^/?#]+)(?:[?#].*)?$/);
    return trailingMatch ? trailingMatch[1] : "";
  };
  const inferMatchType = (value) => {
    const lowered = normalizeText(value).toLowerCase();
    if (lowered.includes("idpa")) {
      return "idpa";
    }
    if (lowered.includes("ipsc")) {
      return "ipsc";
    }
    if (lowered.includes("uspsa")) {
      return "uspsa";
    }
    return "";
  };
  const inferEventDate = (value) => {
    const text = normalizeText(value);
    const match = text.match(/\b(\d{4}-\d{2}-\d{2}|\d{1,2}\/\d{1,2}\/\d{2,4}|[A-Z][a-z]{2,8}\s+\d{1,2},\s+\d{4})\b/);
    return match ? match[1] : "";
  };
  const candidates = Array.from(document.querySelectorAll("[data-remote-id], a[href]"));
  for (const node of candidates) {
    const isAnchor = typeof node.matches === "function" && node.matches("a[href]");
    const anchor = isAnchor ? node : (typeof node.querySelector === "function" ? node.querySelector("a[href]") : null);
    const detailsUrl = anchor && anchor.href ? anchor.href : "";
        const explicitRemoteId = normalizeText(typeof node.getAttribute === "function" ? node.getAttribute("data-remote-id") : "");
        if (!explicitRemoteId && !isMatchLikeHref(detailsUrl)) {
            continue;
        }
        const remoteMatchId = explicitRemoteId
      || resolveRemoteId(detailsUrl)
      || resolveRemoteId(typeof node.getAttribute === "function" ? node.getAttribute("href") : "");
    if (remoteMatchId !== remoteId) {
      continue;
    }
    const container = typeof node.closest === "function"
      ? (node.closest("[data-remote-id], tr, li, article, section, .match-card, .event-card") || node)
      : node;
    const text = normalizeText(container && container.textContent ? container.textContent : "");
    const label = normalizeText(typeof node.getAttribute === "function" ? node.getAttribute("data-label") : "")
      || normalizeText(anchor && anchor.textContent ? anchor.textContent : "")
      || text
      || remoteId;
    return {
      remote_id: remoteId,
      label,
      match_type: normalizeText(typeof node.getAttribute === "function" ? node.getAttribute("data-match-type") : "") || inferMatchType(text),
      event_name: normalizeText(typeof node.getAttribute === "function" ? node.getAttribute("data-event-name") : "") || label,
      event_date: normalizeText(typeof node.getAttribute === "function" ? node.getAttribute("data-event-date") : "") || inferEventDate(text),
      details_url: detailsUrl,
    };
  }
  return null;
}
"""

_SELECTED_MATCH_SCRIPT = r"""
(remoteId) => {
  /* splitshot-practiscore-selected-match */
  const normalizeText = (value) => String(value || "").replace(/\s+/g, " ").trim();
  const inferMatchType = (value) => {
    const lowered = normalizeText(value).toLowerCase();
    if (lowered.includes("idpa")) {
      return "idpa";
    }
    if (lowered.includes("ipsc")) {
      return "ipsc";
    }
    if (lowered.includes("uspsa")) {
      return "uspsa";
    }
    return "";
  };
  const inferEventDate = (value) => {
    const text = normalizeText(value);
    const match = text.match(/\b(\d{4}-\d{2}-\d{2}|\d{1,2}\/\d{1,2}\/\d{2,4}|[A-Z][a-z]{2,8}\s+\d{1,2},\s+\d{4})\b/);
    return match ? match[1] : "";
  };
  const metadata = {};
  for (const term of Array.from(document.querySelectorAll("dt"))) {
    const key = normalizeText(term.textContent);
    const value = normalizeText(term.nextElementSibling && term.nextElementSibling.textContent ? term.nextElementSibling.textContent : "");
    if (key && value && !(key in metadata)) {
      metadata[key] = value;
    }
  }
  for (const row of Array.from(document.querySelectorAll("tr"))) {
    const cells = Array.from(row.querySelectorAll("th, td"));
    if (cells.length !== 2) {
      continue;
    }
    const key = normalizeText(cells[0].textContent);
    const value = normalizeText(cells[1].textContent);
    if (key && value && !(key in metadata)) {
      metadata[key] = value;
    }
  }
  let artifact = null;
  for (const anchor of Array.from(document.querySelectorAll("a[href]"))) {
    const href = anchor.href || "";
    const text = normalizeText(anchor.textContent);
    const lowered = `${href} ${text}`.toLowerCase();
    if (!artifact && (lowered.includes("download") || lowered.includes("report") || lowered.includes(".csv") || lowered.includes(".txt"))) {
      artifact = {
        download_url: href,
        label: text,
        suggested_filename: normalizeText(anchor.getAttribute("download")),
      };
    }
    if (/\.csv(?:[?#]|$)/i.test(href) || /\.txt(?:[?#]|$)/i.test(href)) {
      artifact = {
        download_url: href,
        label: text,
        suggested_filename: normalizeText(anchor.getAttribute("download")),
      };
      break;
    }
  }
  const bodyText = normalizeText(document.body && document.body.textContent ? document.body.textContent : "");
  const headingElement = document.querySelector("h1, h2, h3");
  const heading = normalizeText(headingElement && headingElement.textContent ? headingElement.textContent : "");
  return {
    remote_id: remoteId,
    label: heading || document.title || remoteId,
    match_type: inferMatchType(bodyText),
    event_name: heading || document.title || remoteId,
    event_date: inferEventDate(bodyText),
    title: document.title || "",
    heading,
    metadata,
    artifact,
  };
}
"""

_FETCH_ARTIFACT_SCRIPT = r"""
async (downloadUrl) => {
  /* splitshot-practiscore-fetch-artifact */
  const response = await fetch(downloadUrl, { credentials: "include" });
  return {
    ok: response.ok,
    status: response.status,
    url: response.url,
    content_type: response.headers.get("content-type") || "",
    text: await response.text(),
  };
}
"""


class PractiScoreSyncError(RuntimeError):
    def __init__(
        self,
        category: str,
        message: str,
        *,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.details = dict(details or {})


@dataclass(frozen=True, slots=True)
class RemotePractiScoreMatch:
    remote_id: str
    label: str
    match_type: str
    event_name: str
    event_date: str
    details_url: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "remote_id": self.remote_id,
            "label": self.label,
            "match_type": self.match_type,
            "event_name": self.event_name,
            "event_date": self.event_date,
        }

    @classmethod
    def from_dict(cls, payload: object) -> RemotePractiScoreMatch | None:
        if not isinstance(payload, dict):
            return None
        remote_id = _clean_text(payload.get("remote_id"))
        if not remote_id:
            return None
        label = _clean_text(payload.get("label")) or remote_id
        event_name = _clean_text(payload.get("event_name")) or label
        return cls(
            remote_id=remote_id,
            label=label,
            match_type=_normalize_match_type(payload.get("match_type")),
            event_name=event_name,
            event_date=_clean_text(payload.get("event_date")),
            details_url=_clean_text(payload.get("details_url")),
        )


@dataclass(frozen=True, slots=True)
class SelectedRemoteMatchArtifacts:
    match: RemotePractiScoreMatch
    cache_dir: Path
    source_artifact_path: Path
    source_name: str
    html_path: Path
    summary_path: Path
    summary_snapshot: dict[str, object]


def practiscore_sync_audit_root(app_dir: str | Path | None = None) -> Path:
    resolved_app_dir = Path(app_dir) if app_dir is not None else splitshot_config.APP_DIR
    root = resolved_app_dir / "practiscore" / _SYNC_AUDIT_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def discover_remote_matches(
    authenticated_browser: Any,
    *,
    timeout_ms: int = 15000,
) -> list[RemotePractiScoreMatch]:
    page, should_close_page = _matches_discovery_page(
        authenticated_browser,
        timeout_ms=timeout_ms,
    )
    try:
        raw_matches = _page_hook_or_evaluate(
            owner=page,
            hook_name="discover_remote_matches_data",
            script=_DISCOVER_MATCHES_SCRIPT,
        )
        if not isinstance(raw_matches, list):
            raise PractiScoreSyncError(
                MALFORMED_REMOTE_RESPONSE_ERROR,
                "PractiScore returned an unexpected match-list payload.",
                details={"payload_type": type(raw_matches).__name__},
            )

        discovered: list[RemotePractiScoreMatch] = []
        seen_ids: set[str] = set()
        for item in raw_matches:
            match = RemotePractiScoreMatch.from_dict(item)
            if match is None or match.remote_id in seen_ids:
                continue
            discovered.append(match)
            seen_ids.add(match.remote_id)
        return discovered
    finally:
        if should_close_page:
            _close_page(page)


def download_remote_match_artifacts(
    authenticated_browser: Any,
    remote_id: str,
    cache_root: str | Path,
    *,
    match_catalog: Sequence[RemotePractiScoreMatch | dict[str, object]] | None = None,
    timeout_ms: int = 15000,
) -> SelectedRemoteMatchArtifacts:
    selected_remote_id = _clean_text(remote_id)
    if not selected_remote_id:
        raise PractiScoreSyncError(
            MALFORMED_REMOTE_RESPONSE_ERROR,
            "A remote PractiScore match must be selected before import.",
        )

    known_match = _match_from_catalog(match_catalog, selected_remote_id)
    details_page, should_close_page, details_url = _selected_match_page(
        authenticated_browser,
        selected_remote_id,
        known_match,
        timeout_ms=timeout_ms,
    )
    try:
        html = _page_content(details_page)
        snapshot = _page_hook_or_evaluate(
            owner=details_page,
            hook_name="selected_match_snapshot",
            script=_SELECTED_MATCH_SCRIPT,
            argument=selected_remote_id,
        )
        if not isinstance(snapshot, dict):
            raise PractiScoreSyncError(
                MALFORMED_REMOTE_RESPONSE_ERROR,
                "PractiScore returned an unexpected selected-match payload.",
                details={"payload_type": type(snapshot).__name__},
            )

        artifact_payload = snapshot.get("artifact")
        if not isinstance(artifact_payload, dict):
            raise PractiScoreSyncError(
                MISSING_REQUIRED_REMOTE_ARTIFACT_ERROR,
                f"PractiScore did not expose a CSV or TXT artifact for remote match {selected_remote_id}.",
                details={"remote_id": selected_remote_id},
            )

        download_url = _clean_text(artifact_payload.get("download_url"))
        if not download_url:
            raise PractiScoreSyncError(
                MISSING_REQUIRED_REMOTE_ARTIFACT_ERROR,
                f"PractiScore did not expose a CSV or TXT artifact for remote match {selected_remote_id}.",
                details={"remote_id": selected_remote_id},
            )

        fetched_artifact = _page_hook_or_evaluate(
            owner=details_page,
            hook_name="fetch_artifact_payload",
            script=_FETCH_ARTIFACT_SCRIPT,
            argument=download_url,
        )
        if not isinstance(fetched_artifact, dict):
            raise PractiScoreSyncError(
                MALFORMED_REMOTE_RESPONSE_ERROR,
                "PractiScore returned an unexpected download payload.",
                details={"payload_type": type(fetched_artifact).__name__},
            )
        _validate_fetched_artifact(fetched_artifact, selected_remote_id, download_url)

        resolved_artifact_url = _clean_text(fetched_artifact.get("url")) or download_url
        content_type = _clean_text(fetched_artifact.get("content_type"))
        suffix = _artifact_suffix(
            resolved_artifact_url,
            content_type,
            suggested_name=_clean_text(artifact_payload.get("suggested_filename")),
        )
        if suffix not in _SUPPORTED_SOURCE_SUFFIXES:
            raise PractiScoreSyncError(
                MISSING_REQUIRED_REMOTE_ARTIFACT_ERROR,
                f"PractiScore did not expose a CSV or TXT artifact for remote match {selected_remote_id}.",
                details={
                    "remote_id": selected_remote_id,
                    "content_type": content_type,
                    "resolved_url": resolved_artifact_url,
                },
            )

        source_name = _source_name(
            _clean_text(artifact_payload.get("suggested_filename")),
            resolved_artifact_url,
            selected_remote_id,
            suffix,
        )
        cache_dir = Path(cache_root) / _safe_path_component(selected_remote_id, default="selected-match")
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

        source_artifact_path = cache_dir / source_name
        html_path = cache_dir / "selected-match.html"
        summary_path = cache_dir / "summary.json"
        source_artifact_path.write_text(str(fetched_artifact.get("text", "")), encoding="utf-8")
        html_path.write_text(html, encoding="utf-8")

        selected_match = known_match or RemotePractiScoreMatch.from_dict({
            **snapshot,
            "details_url": details_url,
        }) or RemotePractiScoreMatch(
            remote_id=selected_remote_id,
            label=_clean_text(snapshot.get("label")) or selected_remote_id,
            match_type=_normalize_match_type(snapshot.get("match_type")),
            event_name=_clean_text(snapshot.get("event_name")) or _clean_text(snapshot.get("label")) or selected_remote_id,
            event_date=_clean_text(snapshot.get("event_date")),
            details_url=details_url,
        )

        summary_snapshot = {
            "remote_match": selected_match.to_dict(),
            "details_url": details_url,
            "page_url": _page_url(details_page) or details_url,
            "page_title": _clean_text(snapshot.get("title")),
            "page_heading": _clean_text(snapshot.get("heading")),
            "metadata": _snapshot_metadata(snapshot.get("metadata")),
            "artifact": {
                "download_url": resolved_artifact_url,
                "source_name": source_name,
                "content_type": content_type,
                "source_artifact_path": str(source_artifact_path),
                "html_path": str(html_path),
            },
        }
        summary_path.write_text(json.dumps(summary_snapshot, indent=2, sort_keys=True), encoding="utf-8")

        return SelectedRemoteMatchArtifacts(
            match=selected_match,
            cache_dir=cache_dir,
            source_artifact_path=source_artifact_path,
            source_name=source_name,
            html_path=html_path,
            summary_path=summary_path,
            summary_snapshot=summary_snapshot,
        )
    finally:
        if should_close_page:
            _close_page(details_page)


def _active_page(authenticated_browser: Any) -> Any:
    pages = list(getattr(authenticated_browser, "pages", []) or [])
    for page in reversed(pages):
        is_closed = getattr(page, "is_closed", None)
        if callable(is_closed):
            try:
                if is_closed():
                    continue
            except Exception:
                continue
        return page
    page = getattr(authenticated_browser, "page", None)
    if page is not None:
        return page
    raise PractiScoreSyncError(
        MALFORMED_REMOTE_RESPONSE_ERROR,
        "No authenticated PractiScore page is available for remote discovery.",
    )


def _matches_discovery_page(
    authenticated_browser: Any,
    *,
    timeout_ms: int,
) -> tuple[Any, bool]:
    active_page = _active_page(authenticated_browser)
    new_page = getattr(authenticated_browser, "new_page", None)
    if callable(new_page):
        page = new_page()
        _goto_page(page, _PRACTISCORE_MATCH_SEARCH_URL, timeout_ms=timeout_ms)
        return page, True
    _goto_page(active_page, _PRACTISCORE_MATCH_SEARCH_URL, timeout_ms=timeout_ms)
    return active_page, False


def _page_hook_or_evaluate(
    *,
    owner: Any,
    hook_name: str,
    script: str,
    argument: object | None = None,
) -> object:
    hook = getattr(owner, hook_name, None)
    if callable(hook):
        try:
            return hook(argument) if argument is not None else hook()
        except PractiScoreSyncError:
            raise
        except Exception as exc:
            raise _remote_exception(
                exc,
                MALFORMED_REMOTE_RESPONSE_ERROR,
                f"PractiScore {hook_name} failed.",
            ) from exc

    evaluate = getattr(owner, "evaluate", None)
    if not callable(evaluate):
        raise PractiScoreSyncError(
            MALFORMED_REMOTE_RESPONSE_ERROR,
            f"PractiScore page does not support {hook_name} extraction.",
        )
    try:
        if argument is None:
            return evaluate(script)
        return evaluate(script, argument)
    except PractiScoreSyncError:
        raise
    except Exception as exc:
        raise _remote_exception(exc, _category_from_exception(exc), str(exc) or f"PractiScore {hook_name} failed.") from exc


def _selected_match_page(
    authenticated_browser: Any,
    remote_id: str,
    known_match: RemotePractiScoreMatch | None,
    *,
    timeout_ms: int,
) -> tuple[Any, bool, str]:
    open_page = getattr(authenticated_browser, "open_remote_match_page", None)
    if callable(open_page):
        page = open_page(remote_id)
        if page is None:
            raise PractiScoreSyncError(
                MISSING_REQUIRED_REMOTE_ARTIFACT_ERROR,
                f"PractiScore could not open remote match {remote_id}.",
                details={"remote_id": remote_id},
            )
        return page, False, _page_url(page)

    active_page = _active_page(authenticated_browser)
    selection = _page_hook_or_evaluate(
        owner=active_page,
        hook_name="select_remote_match_data",
        script=_SELECT_MATCH_SCRIPT,
        argument=remote_id,
    )
    if not isinstance(selection, dict):
        raise PractiScoreSyncError(
            MALFORMED_REMOTE_RESPONSE_ERROR,
            f"PractiScore could not resolve remote match {remote_id} from the current session page.",
            details={"remote_id": remote_id},
        )

    details_url = _clean_text(selection.get("details_url")) or ("" if known_match is None else known_match.details_url)
    if not details_url:
        current_page_url = _page_url(active_page)
        if _remote_id_from_value(current_page_url) == remote_id:
            return active_page, False, current_page_url
        raise PractiScoreSyncError(
            MALFORMED_REMOTE_RESPONSE_ERROR,
            f"PractiScore did not expose a details page for remote match {remote_id}.",
            details={"remote_id": remote_id},
        )

    new_page = getattr(authenticated_browser, "new_page", None)
    if callable(new_page):
        details_page = new_page()
        _goto_page(details_page, details_url, timeout_ms=timeout_ms)
        return details_page, True, details_url

    _goto_page(active_page, details_url, timeout_ms=timeout_ms)
    return active_page, False, details_url


def _goto_page(page: Any, url: str, *, timeout_ms: int) -> None:
    goto = getattr(page, "goto", None)
    if not callable(goto):
        return
    try:
        goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    except Exception as exc:
        raise _remote_exception(
            exc,
            _category_from_exception(exc),
            f"PractiScore could not load {url}.",
            details={"url": url},
        ) from exc


def _page_content(page: Any) -> str:
    content = getattr(page, "content", None)
    if callable(content):
        try:
            return str(content())
        except Exception as exc:
            raise _remote_exception(
                exc,
                _category_from_exception(exc),
                "PractiScore selected-match HTML could not be captured.",
            ) from exc
    html = getattr(page, "html", None)
    if html is not None:
        return str(html)
    raise PractiScoreSyncError(
        MALFORMED_REMOTE_RESPONSE_ERROR,
        "PractiScore selected-match HTML could not be captured.",
    )


def _page_url(page: Any) -> str:
    return _clean_text(getattr(page, "url", ""))


def _close_page(page: Any) -> None:
    close = getattr(page, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            return


def _match_from_catalog(
    match_catalog: Sequence[RemotePractiScoreMatch | dict[str, object]] | None,
    remote_id: str,
) -> RemotePractiScoreMatch | None:
    if match_catalog is None:
        return None
    for item in match_catalog:
        match = item if isinstance(item, RemotePractiScoreMatch) else RemotePractiScoreMatch.from_dict(item)
        if match is not None and match.remote_id == remote_id:
            return match
    return None


def _validate_fetched_artifact(
    payload: dict[str, object],
    remote_id: str,
    download_url: str,
) -> None:
    if bool(payload.get("ok")):
        return
    status = int(payload.get("status") or 0)
    category = TRANSIENT_NETWORK_FAILURE_ERROR
    if status in {401, 403}:
        category = EXPIRED_AUTHENTICATION_ERROR
    elif status == 404:
        category = MISSING_REQUIRED_REMOTE_ARTIFACT_ERROR
    raise PractiScoreSyncError(
        category,
        f"PractiScore could not download the selected-match scoring artifact (status {status}).",
        details={
            "remote_id": remote_id,
            "status": status,
            "download_url": download_url,
        },
    )


def _artifact_suffix(url: str, content_type: str, *, suggested_name: str) -> str:
    suggested_suffix = Path(suggested_name).suffix.lower()
    if suggested_suffix in _SUPPORTED_SOURCE_SUFFIXES:
        return suggested_suffix
    url_suffix = Path(urlparse(url).path).suffix.lower()
    if url_suffix in _SUPPORTED_SOURCE_SUFFIXES:
        return url_suffix
    lowered_content_type = content_type.lower()
    if "csv" in lowered_content_type:
        return ".csv"
    if "text/plain" in lowered_content_type or lowered_content_type.endswith("/txt") or "text/" in lowered_content_type:
        return ".txt"
    return ""


def _source_name(suggested_name: str, url: str, remote_id: str, suffix: str) -> str:
    candidate = suggested_name or Path(urlparse(url).path).name
    if Path(candidate).suffix.lower() not in _SUPPORTED_SOURCE_SUFFIXES:
        candidate = f"remote-{remote_id}{suffix}"
    stem = _safe_path_component(Path(candidate).stem, default=f"remote-{remote_id}")
    return f"{stem}{suffix}"


def _snapshot_metadata(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    metadata: dict[str, str] = {}
    for key, value in payload.items():
        clean_key = _clean_text(key)
        clean_value = _clean_text(value)
        if clean_key and clean_value:
            metadata[clean_key] = clean_value
    return metadata


def _normalize_match_type(value: object) -> str:
    lowered = _clean_text(value).lower()
    if lowered in {"uspsa", "ipsc", "idpa"}:
        return lowered
    return ""


def _clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _safe_path_component(value: str, *, default: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", _clean_text(value)).strip(".-")
    return cleaned or default


def _remote_id_from_value(value: object) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    query_match = re.search(r"(?:remote_id|match_id|result_id|event_id)=([^&#]+)", text, re.IGNORECASE)
    if query_match:
        return query_match.group(1)
    result_match = re.search(r"/(?:results?|match|event)s?/(?:new/)?([^/?#]+)", text, re.IGNORECASE)
    if result_match:
        return result_match.group(1)
    return ""


def _category_from_exception(exc: BaseException) -> str:
    text = str(exc).lower()
    if any(token in text for token in _TIMEOUT_TOKENS):
        return TRANSIENT_NETWORK_FAILURE_ERROR
    return MALFORMED_REMOTE_RESPONSE_ERROR


def _remote_exception(
    exc: BaseException,
    category: str,
    message: str,
    *,
    details: dict[str, object] | None = None,
) -> PractiScoreSyncError:
    payload = dict(details or {})
    payload.setdefault("reason", str(exc))
    return PractiScoreSyncError(category, message if message else str(exc), details=payload)