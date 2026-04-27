from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import splitshot.browser.practiscore_session as practiscore_session_module

from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController


def _post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_error(url: str, *, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {} if payload is None else {"Content-Type": "application/json"}
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(request, timeout=30)
    response = exc_info.value
    return response.code, json.loads(response.read().decode("utf-8"))


def _controller_without_task_b_hooks() -> ProjectController:
    controller = ProjectController()
    controller.list_practiscore_matches = None
    controller.start_practiscore_sync = None
    return controller


class _FakePage:
    def __init__(self, url: str, *, auth_markers: dict[str, bool] | None = None) -> None:
        self.url = url
        self._auth_markers = dict(auth_markers or {})
        self.bring_to_front_calls = 0
        self.goto_calls: list[str] = []

    def is_closed(self) -> bool:
        return False

    def evaluate(self, script: str) -> dict[str, bool]:
        return dict(self._auth_markers)

    def bring_to_front(self) -> None:
        self.bring_to_front_calls += 1

    def goto(self, url: str, timeout: int | None = None) -> None:
        del timeout
        self.goto_calls.append(url)
        self.url = url


class _FakeContext:
    def __init__(
        self,
        *,
        url: str,
        cookies: list[dict[str, object]] | None = None,
        auth_markers: dict[str, bool] | None = None,
        imported_url: str | None = None,
        imported_auth_markers: dict[str, bool] | None = None,
    ) -> None:
        self.pages = [_FakePage(url, auth_markers=auth_markers)]
        self._cookies = list(cookies or [])
        self._imported_url = imported_url
        self._imported_auth_markers = dict(imported_auth_markers or {})
        self.import_cookie_calls = 0

    def cookies(self) -> list[dict[str, object]]:
        return list(self._cookies)

    @property
    def page(self) -> _FakePage:
        return self.pages[0]

    def import_cookies(self, cookies: list[dict[str, object]]) -> None:
        self.import_cookie_calls += 1
        self._cookies = list(cookies)
        if self._imported_url:
            self.page.url = self._imported_url
        if self._imported_auth_markers:
            self.page._auth_markers = dict(self._imported_auth_markers)

    def close(self) -> None:
        self.pages = []


class _FakePlaywright:
    def stop(self) -> None:
        return


class _FakeRuntime:
    def __init__(
        self,
        *,
        url: str,
        cookies: list[dict[str, object]] | None = None,
        auth_markers: dict[str, bool] | None = None,
        imported_url: str | None = None,
        imported_auth_markers: dict[str, bool] | None = None,
    ) -> None:
        self.playwright = _FakePlaywright()
        self.context = _FakeContext(
            url=url,
            cookies=cookies,
            auth_markers=auth_markers,
            imported_url=imported_url,
            imported_auth_markers=imported_auth_markers,
        )


def _browser_session(
    *,
    browser_name: str = "safari",
    cookies: list[dict[str, object]] | None = None,
) -> practiscore_session_module.PractiScoreBrowserSession:
    return practiscore_session_module.PractiScoreBrowserSession(
        browser_name=browser_name,
        cookies=list(
            cookies
            or [{"name": "laravel_session", "value": "token", "domain": ".practiscore.com", "path": "/", "secure": True}]
        ),
    )


def test_practiscore_session_status_defaults_to_not_authenticated() -> None:
    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)

    try:
        payload = _get_json(f"{server.url}api/practiscore/session/status")
    finally:
        server.shutdown()

    assert payload["state"] == "not_authenticated"
    assert "browser session" in payload["message"]
    assert payload["details"]["profile_path"].endswith("practiscore/browser-profile")


def test_practiscore_session_start_route_returns_status_payload(monkeypatch) -> None:
    open_calls: list[str] = []

    def fake_launch(profile_dir: Path, entry_url: str) -> _FakeRuntime:
        assert profile_dir.name == "browser-profile"
        assert entry_url == practiscore_session_module.PRACTISCORE_ENTRY_URL
        return _FakeRuntime(url="https://practiscore.com/login")

    monkeypatch.setattr(practiscore_session_module, "launch_practiscore_browser", fake_launch)
    monkeypatch.setattr(practiscore_session_module, "load_practiscore_system_browser_session", lambda: None)
    monkeypatch.setattr(
        practiscore_session_module,
        "open_practiscore_in_system_browser",
        lambda url: open_calls.append(url) or True,
    )

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)

    try:
        payload = _post_json(f"{server.url}api/practiscore/session/start", {})
    finally:
        server.shutdown()

    assert payload["state"] == "authenticating"
    assert payload["message"] == "Complete PractiScore login in your browser. SplitShot will continue in the background."
    assert payload["details"]["profile_path"].endswith("practiscore/browser-profile")
    assert open_calls == [practiscore_session_module.PRACTISCORE_ENTRY_URL]


def test_practiscore_session_clear_route_resets_state(monkeypatch) -> None:
    monkeypatch.setattr(practiscore_session_module, "open_practiscore_in_system_browser", lambda url: pytest.fail(f"unexpected browser open for {url}"))

    def fake_launch(profile_dir: Path, entry_url: str) -> _FakeRuntime:
        return _FakeRuntime(
            url="https://practiscore.com/search/matches",
            cookies=[{"domain": ".practiscore.com", "value": "session-token"}],
            auth_markers={"hasLoginLink": False, "hasLogoutControl": True, "hasPasswordField": False},
        )

    monkeypatch.setattr(practiscore_session_module, "launch_practiscore_browser", fake_launch)

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)

    try:
        started = _post_json(f"{server.url}api/practiscore/session/start", {})
        profile_path = Path(started["details"]["profile_path"])
        assert profile_path.exists()

        cleared = _post_json(f"{server.url}api/practiscore/session/clear", {})
    finally:
        server.shutdown()

    assert started["state"] == "authenticated_ready"
    assert cleared["state"] == "not_authenticated"
    assert profile_path.exists() is False


def test_practiscore_session_start_route_stays_authenticating_when_login_controls_are_visible(monkeypatch) -> None:
    open_calls: list[str] = []

    def fake_launch(profile_dir: Path, entry_url: str) -> _FakeRuntime:
        return _FakeRuntime(
            url="https://practiscore.com/search/matches",
            cookies=[{"domain": ".practiscore.com", "value": "session-token"}],
            auth_markers={"hasLoginLink": True, "hasLogoutControl": False, "hasPasswordField": False},
        )

    monkeypatch.setattr(practiscore_session_module, "launch_practiscore_browser", fake_launch)
    monkeypatch.setattr(practiscore_session_module, "load_practiscore_system_browser_session", lambda: None)
    monkeypatch.setattr(
        practiscore_session_module,
        "open_practiscore_in_system_browser",
        lambda url: open_calls.append(url) or True,
    )

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)

    try:
        payload = _post_json(f"{server.url}api/practiscore/session/start", {})
    finally:
        server.shutdown()

    assert payload["state"] == "authenticating"
    assert payload["message"] == "Complete PractiScore login in your browser. SplitShot will continue in the background."
    assert open_calls == [practiscore_session_module.PRACTISCORE_ENTRY_URL]


def test_practiscore_session_start_route_reuses_existing_authenticated_runtime(monkeypatch) -> None:
    launches: list[_FakeRuntime] = []
    open_calls: list[str] = []

    def fake_launch(profile_dir: Path, entry_url: str) -> _FakeRuntime:
        runtime = _FakeRuntime(
            url="https://practiscore.com/dashboard/home",
            cookies=[{"domain": ".practiscore.com", "value": "session-token"}],
            auth_markers={"hasLoginLink": False, "hasLogoutControl": True, "hasPasswordField": False},
        )
        launches.append(runtime)
        return runtime

    monkeypatch.setattr(practiscore_session_module, "launch_practiscore_browser", fake_launch)
    monkeypatch.setattr(practiscore_session_module, "load_practiscore_system_browser_session", lambda: None)
    monkeypatch.setattr(
        practiscore_session_module,
        "open_practiscore_in_system_browser",
        lambda url: open_calls.append(url) or True,
    )

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)

    try:
        first_payload = _post_json(f"{server.url}api/practiscore/session/start", {})
        second_payload = _post_json(f"{server.url}api/practiscore/session/start", {})
    finally:
        server.shutdown()

    assert first_payload["state"] == "authenticated_ready"
    assert second_payload["state"] == "authenticated_ready"
    assert len(launches) == 1
    assert open_calls == []


def test_practiscore_session_start_route_imports_existing_system_browser_session_without_opening_browser(monkeypatch) -> None:
    launches: list[_FakeRuntime] = []
    open_calls: list[str] = []

    def fake_launch(profile_dir: Path, entry_url: str) -> _FakeRuntime:
        runtime = _FakeRuntime(
            url="https://practiscore.com/login",
            imported_url="https://practiscore.com/dashboard/home",
            imported_auth_markers={"hasLoginLink": False, "hasLogoutControl": True, "hasPasswordField": False},
        )
        launches.append(runtime)
        return runtime

    monkeypatch.setattr(practiscore_session_module, "launch_practiscore_browser", fake_launch)
    monkeypatch.setattr(
        practiscore_session_module,
        "load_practiscore_system_browser_session",
        lambda: _browser_session(browser_name="safari"),
    )
    monkeypatch.setattr(
        practiscore_session_module,
        "open_practiscore_in_system_browser",
        lambda url: open_calls.append(url) or True,
    )

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)

    try:
        payload = _post_json(f"{server.url}api/practiscore/session/start", {})
        imported_calls = launches[0].context.import_cookie_calls
        goto_calls = list(launches[0].context.page.goto_calls)
    finally:
        server.shutdown()

    assert payload["state"] == "authenticated_ready"
    assert payload["details"]["source_browser"] == "safari"
    assert imported_calls == 1
    assert goto_calls[-1] == practiscore_session_module.PRACTISCORE_ENTRY_URL
    assert open_calls == []


def test_practiscore_session_start_route_does_not_open_system_browser_twice_while_authenticating(monkeypatch) -> None:
    launches: list[_FakeRuntime] = []
    open_calls: list[str] = []

    def fake_launch(profile_dir: Path, entry_url: str) -> _FakeRuntime:
        runtime = _FakeRuntime(url="https://practiscore.com/login")
        launches.append(runtime)
        return runtime

    monkeypatch.setattr(practiscore_session_module, "launch_practiscore_browser", fake_launch)
    monkeypatch.setattr(practiscore_session_module, "load_practiscore_system_browser_session", lambda: None)
    monkeypatch.setattr(
        practiscore_session_module,
        "open_practiscore_in_system_browser",
        lambda url: open_calls.append(url) or True,
    )

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)

    try:
        first_payload = _post_json(f"{server.url}api/practiscore/session/start", {})
        second_payload = _post_json(f"{server.url}api/practiscore/session/start", {})
    finally:
        server.shutdown()

    assert first_payload["state"] == "authenticating"
    assert second_payload["state"] == "authenticating"
    assert len(launches) == 1
    assert open_calls == [practiscore_session_module.PRACTISCORE_ENTRY_URL]


def test_practiscore_matches_route_returns_structured_unavailable_error_without_task_b_hook() -> None:
    server = BrowserControlServer(controller=_controller_without_task_b_hooks(), port=0)
    server.start_background(open_browser=False)

    try:
        status_code, payload = _get_error(f"{server.url}api/practiscore/matches")
    finally:
        server.shutdown()

    assert status_code == 503
    assert payload["error"]["code"] == "practiscore_task_b_unavailable"
    assert payload["error"]["details"]["required_hook"] == "list_practiscore_matches"


def test_practiscore_sync_route_returns_structured_unavailable_error_without_task_b_hook() -> None:
    server = BrowserControlServer(controller=_controller_without_task_b_hooks(), port=0)
    server.start_background(open_browser=False)

    try:
        status_code, payload = _get_error(
            f"{server.url}api/practiscore/sync/start",
            method="POST",
            payload={"remote_id": "123"},
        )
    finally:
        server.shutdown()

    assert status_code == 503
    assert payload["error"]["code"] == "practiscore_task_b_unavailable"
    assert payload["error"]["details"]["required_hook"] == "start_practiscore_sync"


def test_practiscore_session_routes_return_structured_error_payload(monkeypatch) -> None:
    def fake_launch(profile_dir: Path, entry_url: str) -> _FakeRuntime:
        raise RuntimeError("browser launch failed")

    monkeypatch.setattr(practiscore_session_module, "launch_practiscore_browser", fake_launch)

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)

    try:
        status_code, payload = _get_error(
            f"{server.url}api/practiscore/session/start",
            method="POST",
            payload={},
        )
    finally:
        server.shutdown()

    assert status_code == 500
    assert payload["error"]["code"] == "practiscore_session_start_failed"
    assert payload["error"]["details"]["route"] == "/api/practiscore/session/start"


def test_launch_practiscore_browser_reports_missing_desktop_runtime(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        practiscore_session_module,
        "_launch_qt_practiscore_browser",
        lambda profile_dir, entry_url: (_ for _ in ()).throw(
            RuntimeError("PractiScore background sync requires the SplitShot desktop Qt runtime.")
        ),
    )

    with pytest.raises(RuntimeError, match="desktop Qt runtime"):
        practiscore_session_module.launch_practiscore_browser(tmp_path)


def test_launch_practiscore_browser_delegates_to_qt_runtime(monkeypatch, tmp_path: Path) -> None:
    launched: dict[str, object] = {}

    def fake_launch(profile_dir: Path, entry_url: str) -> _FakeRuntime:
        launched["profile_dir"] = profile_dir
        launched["entry_url"] = entry_url
        return _FakeRuntime(url="https://practiscore.com/clubs")

    monkeypatch.setattr(practiscore_session_module, "_launch_qt_practiscore_browser", fake_launch)

    runtime = practiscore_session_module.launch_practiscore_browser(tmp_path)

    assert launched["profile_dir"] == tmp_path
    assert launched["entry_url"] == practiscore_session_module.PRACTISCORE_ENTRY_URL
    assert isinstance(runtime.context, _FakeContext)
