from __future__ import annotations

from dataclasses import dataclass, field
import json
import queue
import signal
import threading
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QDateTime, QEventLoop, QObject, QTimer, QUrl
from PySide6.QtNetwork import QNetworkCookie
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication


_QT_INVOKER_LOCK = threading.Lock()
_QT_INVOKER: QtMainThreadInvoker | None = None
_TASK_TIMEOUT_MS = 15000
_COOKIE_LOAD_TIMEOUT_MS = 300
_INVOKER_INTERVAL_MS = 10
_SERVER_MONITOR_INTERVAL_MS = 250


@dataclass(slots=True)
class _QueuedCall:
    callback: Callable[[], Any]
    result: Any = None
    error: BaseException | None = None
    completed: threading.Event = field(default_factory=threading.Event)


class QtMainThreadInvoker(QObject):
    def __init__(self) -> None:
        super().__init__()
        self._queue: queue.Queue[_QueuedCall] = queue.Queue()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._drain)
        self._timer.start(_INVOKER_INTERVAL_MS)
        self._stopped = False

    def stop(self) -> None:
        self._stopped = True
        self._timer.stop()

    def call(self, callback: Callable[[], Any], *, timeout_ms: int | None = None) -> Any:
        if self._stopped:
            raise RuntimeError("The SplitShot desktop runtime is not active.")
        if threading.current_thread() is threading.main_thread():
            return callback()
        task = _QueuedCall(callback=callback)
        self._queue.put(task)
        waited = task.completed.wait(None if timeout_ms is None else timeout_ms / 1000)
        if not waited:
            raise RuntimeError("Timed out waiting for the SplitShot desktop runtime.")
        if task.error is not None:
            raise task.error
        return task.result

    def _drain(self) -> None:
        while True:
            try:
                task = self._queue.get_nowait()
            except queue.Empty:
                return
            try:
                task.result = task.callback()
            except BaseException as exc:  # noqa: BLE001
                task.error = exc
            finally:
                task.completed.set()


def configure_practiscore_qt_runtime(invoker: QtMainThreadInvoker | None) -> None:
    global _QT_INVOKER
    with _QT_INVOKER_LOCK:
        _QT_INVOKER = invoker


def current_practiscore_qt_runtime() -> QtMainThreadInvoker:
    with _QT_INVOKER_LOCK:
        invoker = _QT_INVOKER
    if invoker is None:
        raise RuntimeError(
            "PractiScore background sync requires the SplitShot desktop Qt runtime. Launch SplitShot with the standard app entrypoint."
        )
    return invoker


class _AuthBrowserView(QWebEngineView):
    def __init__(self) -> None:
        super().__init__()
        self._allow_close = False

    def force_close(self) -> None:
        self._allow_close = True
        self.close()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._allow_close:
            super().closeEvent(event)
            return
        event.ignore()
        self.hide()


class _QtPageController:
    def __init__(self, profile: QWebEngineProfile, *, visible: bool) -> None:
        self._page = QWebEnginePage(profile)
        self._view: _AuthBrowserView | None = None
        self._closed = False
        if visible:
            view = _AuthBrowserView()
            view.resize(1280, 900)
            view.setWindowTitle("SplitShot PractiScore")
            view.setPage(self._page)
            self._view = view

    def goto(self, url: str, *, timeout_ms: int = _TASK_TIMEOUT_MS) -> None:
        self._ensure_open()
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        finished = {"value": False}

        def _done(_ok: bool) -> None:
            finished["value"] = True
            loop.quit()

        timer.timeout.connect(loop.quit)
        self._page.loadFinished.connect(_done)
        try:
            self._page.load(QUrl(url))
            timer.start(timeout_ms)
            loop.exec()
        finally:
            try:
                self._page.loadFinished.disconnect(_done)
            except Exception:
                pass
            timer.stop()
        if not finished["value"]:
            raise RuntimeError(f"Timed out loading {url}.")

    def evaluate(self, script: str, argument: object | None = None, *, timeout_ms: int = _TASK_TIMEOUT_MS) -> Any:
        self._ensure_open()
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        result: dict[str, Any] = {}
        base_expression = f"({script})({json.dumps(argument)})" if argument is not None else f"({script})()"
        expression = """
(() => {
    const value = %s;
    if (value === undefined) return '__splitshot_undefined__';
    if (value === null) return 'null';
    if (typeof value === 'string') return JSON.stringify(value);
    if (typeof value === 'number' || typeof value === 'boolean') return JSON.stringify(value);
    try {
        return JSON.stringify(value);
    } catch (_error) {
        return JSON.stringify(String(value));
    }
})()
""" % base_expression

        def _done(value: Any) -> None:
            result["value"] = value
            loop.quit()

        timer.timeout.connect(loop.quit)
        self._page.runJavaScript(expression, _done)
        timer.start(timeout_ms)
        loop.exec()
        timer.stop()
        if "value" not in result:
            raise RuntimeError("Timed out waiting for JavaScript evaluation.")
        raw_value = result["value"]
        if raw_value == "__splitshot_undefined__":
            return None
        if isinstance(raw_value, str):
            return json.loads(raw_value)
        return raw_value

    def content(self, *, timeout_ms: int = _TASK_TIMEOUT_MS) -> str:
        self._ensure_open()
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        result: dict[str, str] = {}

        def _done(value: str) -> None:
            result["value"] = value
            loop.quit()

        timer.timeout.connect(loop.quit)
        self._page.toHtml(_done)
        timer.start(timeout_ms)
        loop.exec()
        timer.stop()
        if "value" not in result:
            raise RuntimeError("Timed out waiting for page HTML.")
        return result["value"]

    def bring_to_front(self) -> None:
        if self._view is None or self._closed:
            return
        self._view.show()
        self._view.raise_()
        self._view.activateWindow()

    def url(self) -> str:
        if self._closed:
            return ""
        return self._page.url().toString()

    def is_closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._view is not None:
            self._view.force_close()
            self._view.deleteLater()
            self._view = None
        self._page.deleteLater()

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("PractiScore page is closed.")


class _QtRuntimeOwner:
    def __init__(self, profile_dir: Path) -> None:
        self._profile = QWebEngineProfile("splitshot-practiscore")
        self._profile.setPersistentStoragePath(str(profile_dir))
        cache_path = profile_dir / "cache"
        cache_path.mkdir(parents=True, exist_ok=True)
        set_cache_path = getattr(self._profile, "setCachePath", None)
        if callable(set_cache_path):
            set_cache_path(str(cache_path))
        self._profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        self._cookie_store = self._profile.cookieStore()
        self._cookies: dict[tuple[str, str, bytes], dict[str, object]] = {}
        self._cookie_store.cookieAdded.connect(self._cookie_added)
        self._cookie_store.cookieRemoved.connect(self._cookie_removed)
        self._cookie_store.loadAllCookies()
        self._auth_page = _QtPageController(self._profile, visible=False)
        self._extra_pages: list[_QtPageController] = []
        self._closed = False

    @property
    def auth_page(self) -> _QtPageController:
        return self._auth_page

    def create_page(self) -> _QtPageController:
        self._ensure_open()
        controller = _QtPageController(self._profile, visible=False)
        self._extra_pages.append(controller)
        return controller

    def cookie_payloads(self) -> list[dict[str, object]]:
        self._ensure_open()
        self._refresh_cookies()
        return [dict(payload) for payload in self._cookies.values()]

    def import_cookie_payloads(self, cookie_payloads: list[dict[str, object]]) -> None:
        self._ensure_open()
        for payload in cookie_payloads:
            name = str(payload.get("name") or "").strip()
            if not name:
                continue
            cookie = QNetworkCookie()
            cookie.setName(name.encode("utf-8"))
            cookie.setValue(str(payload.get("value") or "").encode("utf-8"))
            domain = str(payload.get("domain") or "").strip()
            if domain:
                cookie.setDomain(domain)
            path = str(payload.get("path") or "/").strip() or "/"
            cookie.setPath(path)
            cookie.setSecure(bool(payload.get("secure")))
            cookie.setHttpOnly(bool(payload.get("http_only")))
            expires = payload.get("expires")
            if expires not in {None, "", 0}:
                try:
                    cookie.setExpirationDate(QDateTime.fromSecsSinceEpoch(int(expires)))
                except Exception:
                    pass
            origin_host = domain.lstrip(".") or "practiscore.com"
            origin_path = path if path.startswith("/") else f"/{path}"
            origin_scheme = "https" if cookie.isSecure() else "http"
            self._cookie_store.setCookie(cookie, QUrl(f"{origin_scheme}://{origin_host}{origin_path}"))
        self._refresh_cookies()

    def stop(self) -> None:
        if self._closed:
            return
        self._closed = True
        for controller in self._extra_pages:
            controller.close()
        self._extra_pages.clear()
        self._auth_page.close()
        self._profile.deleteLater()

    def _refresh_cookies(self) -> None:
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        self._cookie_store.loadAllCookies()
        timer.start(_COOKIE_LOAD_TIMEOUT_MS)
        loop.exec()
        timer.stop()

    def _cookie_added(self, cookie: QNetworkCookie) -> None:
        key = self._cookie_key(cookie)
        self._cookies[key] = {
            "domain": cookie.domain(),
            "path": cookie.path(),
            "name": bytes(cookie.name()),
            "value": bytes(cookie.value()).decode("utf-8", errors="ignore"),
        }

    def _cookie_removed(self, cookie: QNetworkCookie) -> None:
        self._cookies.pop(self._cookie_key(cookie), None)

    def _cookie_key(self, cookie: QNetworkCookie) -> tuple[str, str, bytes]:
        return (cookie.domain(), cookie.path(), bytes(cookie.name()))

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("PractiScore runtime is closed.")


class QtPractiScorePage:
    def __init__(self, invoker: QtMainThreadInvoker, controller: _QtPageController) -> None:
        self._invoker = invoker
        self._controller = controller

    def goto(self, url: str, wait_until: str = "domcontentloaded", timeout: int = _TASK_TIMEOUT_MS) -> None:
        del wait_until
        self._invoker.call(lambda: self._controller.goto(url, timeout_ms=timeout), timeout_ms=timeout)

    def evaluate(self, script: str, argument: object | None = None) -> Any:
        return self._invoker.call(lambda: self._controller.evaluate(script, argument), timeout_ms=_TASK_TIMEOUT_MS)

    def content(self) -> str:
        return self._invoker.call(self._controller.content, timeout_ms=_TASK_TIMEOUT_MS)

    def is_closed(self) -> bool:
        return bool(self._invoker.call(self._controller.is_closed, timeout_ms=_TASK_TIMEOUT_MS))

    @property
    def url(self) -> str:
        return str(self._invoker.call(self._controller.url, timeout_ms=_TASK_TIMEOUT_MS) or "")

    def bring_to_front(self) -> None:
        self._invoker.call(self._controller.bring_to_front, timeout_ms=_TASK_TIMEOUT_MS)

    def close(self) -> None:
        self._invoker.call(self._controller.close, timeout_ms=_TASK_TIMEOUT_MS)


class QtPractiScoreBrowserContext:
    def __init__(self, invoker: QtMainThreadInvoker, owner: _QtRuntimeOwner) -> None:
        self._invoker = invoker
        self._owner = owner
        self._auth_page = QtPractiScorePage(invoker, owner.auth_page)

    @property
    def pages(self) -> list[QtPractiScorePage]:
        return [self._auth_page]

    @property
    def page(self) -> QtPractiScorePage:
        return self._auth_page

    def cookies(self) -> list[dict[str, object]]:
        return list(self._invoker.call(self._owner.cookie_payloads, timeout_ms=_TASK_TIMEOUT_MS))

    def import_cookies(self, cookie_payloads: list[dict[str, object]]) -> None:
        self._invoker.call(
            lambda: self._owner.import_cookie_payloads(cookie_payloads),
            timeout_ms=_TASK_TIMEOUT_MS,
        )

    def new_page(self) -> QtPractiScorePage:
        controller = self._invoker.call(self._owner.create_page, timeout_ms=_TASK_TIMEOUT_MS)
        return QtPractiScorePage(self._invoker, controller)

    def close(self) -> None:
        self._invoker.call(self._owner.stop, timeout_ms=_TASK_TIMEOUT_MS)


def launch_qt_practiscore_browser(profile_dir: Path, entry_url: str):
    invoker = current_practiscore_qt_runtime()

    def _create_runtime() -> tuple[_QtRuntimeOwner, QtPractiScoreBrowserContext]:
        owner = _QtRuntimeOwner(profile_dir)
        context = QtPractiScoreBrowserContext(invoker, owner)
        try:
            owner.auth_page.goto(entry_url, timeout_ms=_TASK_TIMEOUT_MS)
        except Exception:
            pass
        return owner, context

    owner, context = invoker.call(_create_runtime, timeout_ms=_TASK_TIMEOUT_MS)
    return owner, context


class SplitShotDesktopRuntime:
    def __init__(self) -> None:
        app = QApplication.instance()
        if app is None:
            app = QApplication(["splitshot"])
        app.setQuitOnLastWindowClosed(False)
        self._app = app
        self._invoker = QtMainThreadInvoker()

    def run_server(self, server: Any, *, open_browser: bool) -> int:
        keepalive = QTimer()
        keepalive.timeout.connect(lambda: None)
        keepalive.start(_SERVER_MONITOR_INTERVAL_MS)

        monitor = QTimer()

        def _watch_server() -> None:
            thread = getattr(server, "_thread", None)
            if thread is not None and not thread.is_alive():
                self._app.quit()

        monitor.timeout.connect(_watch_server)
        monitor.start(_SERVER_MONITOR_INTERVAL_MS)
        previous_sigint = signal.getsignal(signal.SIGINT)

        def _handle_sigint(_signum, _frame) -> None:
            self._app.quit()

        signal.signal(signal.SIGINT, _handle_sigint)
        configure_practiscore_qt_runtime(self._invoker)
        server.start_background(open_browser=open_browser)
        try:
            self._app.exec()
        finally:
            monitor.stop()
            keepalive.stop()
            self._invoker.stop()
            configure_practiscore_qt_runtime(None)
            signal.signal(signal.SIGINT, previous_sigint)
            server.shutdown()
        return 0