from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
from typing import Any, Callable, Literal
from urllib.parse import urlparse
import webbrowser

from splitshot.browser.practiscore_browser_cookies import (
    PractiScoreBrowserSession,
    load_practiscore_system_browser_session,
)
from splitshot.browser.practiscore_profile import (
    PractiScoreProfilePaths,
    clear_practiscore_profile_data,
    ensure_practiscore_profile_dir,
    resolve_practiscore_profile_paths,
)


PRACTISCORE_ENTRY_URL = "https://practiscore.com/dashboard/home"
_PRACTISCORE_HOST_SUFFIX = "practiscore.com"
_LOGIN_URL_HINTS = ("login", "signin", "sign-in")
_CHALLENGE_URL_HINTS = ("challenge", "captcha", "verify", "verification", "twofactor", "two-factor", "otp", "mfa")
_NOT_AUTHENTICATED_MESSAGE = "Connect PractiScore to use your browser session for background sync."
_STORED_PROFILE_MESSAGE = "Stored PractiScore background profile found. Click Connect to refresh it from your browser session."
_AUTHENTICATING_MESSAGE = "Complete PractiScore login in your browser. SplitShot will continue in the background."
_EXPIRED_MESSAGE = "PractiScore session expired. Reconnect in your browser to continue."
_CHALLENGE_MESSAGE = "Finish the PractiScore challenge in your browser."
_AUTH_MARKERS_SCRIPT = r"""
() => {
    const normalize = (value) => String(value || '').replace(/\s+/g, ' ').trim().toLowerCase();
    const controls = Array.from(document.querySelectorAll('a[href], button'));
    const hasLoginLink = controls.some((control) => {
        const label = normalize(control.textContent);
        const href = normalize(typeof control.getAttribute === 'function' ? control.getAttribute('href') : '');
        return label === 'login' || href.includes('/login');
    });
    const hasLogoutControl = controls.some((control) => {
        const label = normalize(control.textContent);
        const href = normalize(typeof control.getAttribute === 'function' ? control.getAttribute('href') : '');
        return label.includes('logout') || label.includes('sign out') || href.includes('/logout');
    });
    return {
        hasLoginLink,
        hasLogoutControl,
        hasPasswordField: Boolean(document.querySelector('input[type="password"]')),
    };
}
"""

PractiScoreSessionState = Literal[
    "not_authenticated",
    "authenticating",
    "authenticated_ready",
    "challenge_required",
    "expired",
    "error",
]


@dataclass(frozen=True, slots=True)
class PractiScoreSessionStatus:
    state: PractiScoreSessionState
    message: str
    details: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "state": self.state,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return payload


@dataclass(slots=True)
class _BrowserRuntime:
    playwright: Any
    context: Any


def _launch_qt_practiscore_browser(profile_dir: Path, entry_url: str) -> _BrowserRuntime:
    from splitshot.browser.practiscore_qt_runtime import launch_qt_practiscore_browser

    owner, context = launch_qt_practiscore_browser(profile_dir, entry_url)
    return _BrowserRuntime(playwright=owner, context=context)


def launch_practiscore_browser(
    profile_dir: Path,
    entry_url: str = PRACTISCORE_ENTRY_URL,
) -> _BrowserRuntime:
    return _launch_qt_practiscore_browser(profile_dir, entry_url)


def open_practiscore_in_system_browser(url: str = PRACTISCORE_ENTRY_URL) -> bool:
    try:
        return bool(webbrowser.open(url, new=2))
    except Exception:
        return False


def _page_is_closed(page: Any) -> bool:
    is_closed = getattr(page, "is_closed", None)
    if callable(is_closed):
        try:
            return bool(is_closed())
        except Exception:
            return True
    return False


def _page_url(page: Any) -> str:
    return str(getattr(page, "url", "") or "").strip()


def _is_practiscore_url(url: str) -> bool:
    if not url:
        return False
    host = (urlparse(url).hostname or "").lower()
    return host == _PRACTISCORE_HOST_SUFFIX or host.endswith(f".{_PRACTISCORE_HOST_SUFFIX}")


def _url_matches(url: str, hints: tuple[str, ...]) -> bool:
    lowered = url.lower()
    return any(hint in lowered for hint in hints)


def _has_practiscore_cookie(cookies: list[dict[str, Any]]) -> bool:
    for cookie in cookies:
        domain = str(cookie.get("domain", "") or "").lower().lstrip(".")
        if not domain:
            continue
        if domain == _PRACTISCORE_HOST_SUFFIX or domain.endswith(f".{_PRACTISCORE_HOST_SUFFIX}"):
            if str(cookie.get("value", "") or ""):
                return True
    return False


def _page_auth_markers(page: Any) -> dict[str, bool] | None:
    evaluate = getattr(page, "evaluate", None)
    if not callable(evaluate):
        return None
    try:
        payload = evaluate(_AUTH_MARKERS_SCRIPT)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return {
        "hasLoginLink": bool(payload.get("hasLoginLink")),
        "hasLogoutControl": bool(payload.get("hasLogoutControl")),
        "hasPasswordField": bool(payload.get("hasPasswordField")),
    }


def _page_requires_login(page: Any) -> bool:
    markers = _page_auth_markers(page)
    if not markers:
        return False
    return bool(
        (markers["hasLoginLink"] or markers["hasPasswordField"])
        and not markers["hasLogoutControl"]
    )


def _cookie_signature(cookies: list[dict[str, object]]) -> tuple[tuple[str, str, str, str], ...]:
    return tuple(
        sorted(
            (
                str(cookie.get("domain") or ""),
                str(cookie.get("path") or ""),
                str(cookie.get("name") or ""),
                str(cookie.get("value") or ""),
            )
            for cookie in cookies
        )
    )


class PractiScoreSessionManager:
    def __init__(
        self,
        *,
        app_dir: Path | None = None,
        entry_url: str = PRACTISCORE_ENTRY_URL,
        browser_launcher: Callable[[Path, str], _BrowserRuntime] | None = None,
        system_cookie_loader: Callable[[], PractiScoreBrowserSession | None] | None = None,
        browser_opener: Callable[[str], bool] | None = None,
    ) -> None:
        self._entry_url = entry_url
        self._browser_launcher = browser_launcher or launch_practiscore_browser
        self._system_cookie_loader = system_cookie_loader or load_practiscore_system_browser_session
        self._browser_opener = browser_opener or open_practiscore_in_system_browser
        self._profile_paths = resolve_practiscore_profile_paths(app_dir)
        self._lock = threading.RLock()
        self._runtime: _BrowserRuntime | None = None
        self._had_authenticated_session = False
        self._external_login_requested = False
        self._imported_cookie_signature: tuple[tuple[str, str, str, str], ...] | None = None
        self._source_browser_name: str | None = None
        self._status = self._not_authenticated_status(_NOT_AUTHENTICATED_MESSAGE)

    @property
    def profile_paths(self) -> PractiScoreProfilePaths:
        return self._profile_paths

    def start_login_flow(self) -> PractiScoreSessionStatus:
        with self._lock:
            profile_dir = ensure_practiscore_profile_dir(self._profile_paths.app_dir)
            if self._runtime is not None:
                self._sync_system_browser_cookies_locked(force_reload=True)
                status = self._refresh_status_locked()
                if status.state == "authenticated_ready":
                    self._external_login_requested = False
                    return status
                if status.state == "error":
                    self._close_runtime_locked()
            if self._runtime is None:
                try:
                    self._runtime = self._browser_launcher(profile_dir, self._entry_url)
                except Exception as exc:
                    self._runtime = None
                    self._status = PractiScoreSessionStatus(
                        state="error",
                        message="Unable to prepare the background PractiScore sync session.",
                        details=self._details(profile_path=profile_dir, error=str(exc)),
                    )
                    raise RuntimeError(self._status.message) from exc
                self._sync_system_browser_cookies_locked(force_reload=True)
            status = self._refresh_status_locked()
            if status.state == "authenticated_ready":
                self._external_login_requested = False
                return status
            if status.state in {"authenticating", "challenge_required"} and self._external_login_requested:
                return status
            try:
                opened = self._browser_opener(self._entry_url)
            except Exception as exc:
                opened = False
                self._status = PractiScoreSessionStatus(
                    state="error",
                    message="Unable to open PractiScore in your browser.",
                    details=self._details(profile_path=profile_dir, error=str(exc)),
                )
                raise RuntimeError(self._status.message) from exc
            if not opened:
                self._status = PractiScoreSessionStatus(
                    state="error",
                    message="Unable to open PractiScore in your browser.",
                    details=self._details(profile_path=profile_dir),
                )
                raise RuntimeError(self._status.message)
            self._external_login_requested = True
            current_url = ""
            if isinstance(status.details, dict):
                current_url = str(status.details.get("current_url") or "")
            self._status = PractiScoreSessionStatus(
                state="challenge_required" if status.state == "challenge_required" else "authenticating",
                message=_CHALLENGE_MESSAGE if status.state == "challenge_required" else _AUTHENTICATING_MESSAGE,
                details=self._details(profile_path=profile_dir, current_url=current_url),
            )
            return self._status

    def current_status(self) -> PractiScoreSessionStatus:
        with self._lock:
            if self._runtime is not None:
                self._sync_system_browser_cookies_locked()
            status = self._refresh_status_locked()
            if status.state == "authenticated_ready":
                self._external_login_requested = False
            return status

    def clear_session(self) -> PractiScoreSessionStatus:
        with self._lock:
            self._close_runtime_locked()
            cleared_paths = clear_practiscore_profile_data(self._profile_paths.app_dir)
            self._had_authenticated_session = False
            self._external_login_requested = False
            self._status = self._not_authenticated_status(
                "PractiScore background session cleared. Connect again to import your browser session.",
                profile_path=cleared_paths.profile_dir,
            )
            return self._status

    def serialize_status(self) -> dict[str, object]:
        return self.current_status().to_dict()

    def require_authenticated_browser(self) -> Any:
        with self._lock:
            if self._runtime is None:
                profile_dir = ensure_practiscore_profile_dir(self._profile_paths.app_dir)
                try:
                    self._runtime = self._browser_launcher(profile_dir, self._entry_url)
                except Exception as exc:
                    self._status = PractiScoreSessionStatus(
                        state="error",
                        message="Unable to prepare the background PractiScore sync session.",
                        details=self._details(profile_path=profile_dir, error=str(exc)),
                    )
                    raise RuntimeError(self._status.message) from exc
            self._sync_system_browser_cookies_locked(force_reload=True)
            status = self._refresh_status_locked()
            if status.state != "authenticated_ready" or self._runtime is None:
                raise RuntimeError(status.message)
            return self._runtime.context

    def shutdown(self) -> None:
        with self._lock:
            self._close_runtime_locked()

    def _refresh_status_locked(self) -> PractiScoreSessionStatus:
        if self._runtime is None:
            if self._profile_has_contents():
                self._status = self._not_authenticated_status(_STORED_PROFILE_MESSAGE)
            else:
                self._status = self._not_authenticated_status(_NOT_AUTHENTICATED_MESSAGE)
            return self._status

        try:
            context = self._runtime.context
            pages = [page for page in getattr(context, "pages", []) if not _page_is_closed(page)]
            active_page = pages[-1] if pages else None
            current_url = _page_url(active_page) if active_page is not None else ""
            cookies = list(context.cookies())
        except Exception as exc:
            was_authenticated = self._had_authenticated_session
            self._close_runtime_locked()
            if was_authenticated:
                self._status = PractiScoreSessionStatus(
                    state="expired",
                    message=_EXPIRED_MESSAGE,
                    details=self._details(error=str(exc)),
                )
            else:
                self._status = self._not_authenticated_status(_NOT_AUTHENTICATED_MESSAGE, error=str(exc))
            return self._status

        has_cookie = _has_practiscore_cookie(cookies)
        details = self._details(current_url=current_url)
        if _url_matches(current_url, _CHALLENGE_URL_HINTS):
            self._status = PractiScoreSessionStatus(
                state="challenge_required",
                message=_CHALLENGE_MESSAGE,
                details=details,
            )
            return self._status
        if active_page is not None and _page_requires_login(active_page):
            state = "expired" if self._had_authenticated_session else "authenticating"
            message = _EXPIRED_MESSAGE if state == "expired" else _AUTHENTICATING_MESSAGE
            self._status = PractiScoreSessionStatus(state=state, message=message, details=details)
            return self._status
        if has_cookie and (_is_practiscore_url(current_url) or not current_url):
            self._had_authenticated_session = True
            self._status = PractiScoreSessionStatus(
                state="authenticated_ready",
                message="PractiScore session is authenticated and ready.",
                details=details,
            )
            return self._status
        if _url_matches(current_url, _LOGIN_URL_HINTS):
            state: PractiScoreSessionState = "expired" if self._had_authenticated_session else "authenticating"
            message = _EXPIRED_MESSAGE if state == "expired" else _AUTHENTICATING_MESSAGE
            self._status = PractiScoreSessionStatus(state=state, message=message, details=details)
            return self._status
        self._status = PractiScoreSessionStatus(
            state="authenticating",
            message=_AUTHENTICATING_MESSAGE,
            details=details,
        )
        return self._status

    def _sync_system_browser_cookies_locked(self, *, force_reload: bool = False) -> bool:
        if self._runtime is None:
            return False
        try:
            browser_session = self._system_cookie_loader()
        except Exception:
            return False
        if browser_session is None or not browser_session.cookies:
            return False
        signature = _cookie_signature(browser_session.cookies)
        if not force_reload and signature == self._imported_cookie_signature:
            return False
        context = self._runtime.context
        import_cookies = getattr(context, "import_cookies", None)
        if not callable(import_cookies):
            return False
        try:
            import_cookies(browser_session.cookies)
        except Exception:
            return False
        page = getattr(context, "page", None)
        goto = getattr(page, "goto", None) if page is not None else None
        if callable(goto):
            try:
                goto(self._entry_url, timeout=15000)
            except TypeError:
                try:
                    goto(self._entry_url)
                except Exception:
                    pass
            except Exception:
                pass
        self._imported_cookie_signature = signature
        self._source_browser_name = browser_session.browser_name
        return True

    def _close_runtime_locked(self) -> None:
        runtime = self._runtime
        self._runtime = None
        self._imported_cookie_signature = None
        self._source_browser_name = None
        if runtime is None:
            return
        try:
            runtime.context.close()
        except Exception:
            pass
        try:
            runtime.playwright.stop()
        except Exception:
            pass

    def _profile_has_contents(self) -> bool:
        profile_dir = self._profile_paths.profile_dir
        return profile_dir.exists() and any(profile_dir.iterdir())

    def _details(
        self,
        *,
        profile_path: Path | None = None,
        current_url: str | None = None,
        error: str | None = None,
    ) -> dict[str, object]:
        details: dict[str, object] = {
            "profile_path": str(profile_path or self._profile_paths.profile_dir),
        }
        if self._source_browser_name:
            details["source_browser"] = self._source_browser_name
        if current_url:
            details["current_url"] = current_url
        if error:
            details["error"] = error
        return details

    def _not_authenticated_status(
        self,
        message: str,
        *,
        profile_path: Path | None = None,
        error: str | None = None,
    ) -> PractiScoreSessionStatus:
        return PractiScoreSessionStatus(
            state="not_authenticated",
            message=message,
            details=self._details(profile_path=profile_path, error=error),
        )