from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from splitshot import cli


def test_splitshot_defaults_to_browser_mode(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_browser(
        host: str,
        port: int,
        open_browser: bool,
        project_path: Path | None,
        log_level: str,
    ) -> int:
        calls["mode"] = "web"
        calls["host"] = host
        calls["port"] = port
        calls["open_browser"] = open_browser
        calls["project_path"] = project_path
        calls["log_level"] = log_level
        return 0

    monkeypatch.setattr(cli, "run_browser", fake_browser)

    assert cli.main(["--no-open", "--port", "0"]) == 0
    assert calls == {
        "mode": "web",
        "host": "127.0.0.1",
        "port": 0,
        "open_browser": False,
        "project_path": None,
        "log_level": "off",
    }


def test_splitshot_log_level_dispatches_to_browser(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_browser(
        host: str,
        port: int,
        open_browser: bool,
        project_path: Path | None,
        log_level: str,
    ) -> int:
        calls["log_level"] = log_level
        return 0

    monkeypatch.setattr(cli, "run_browser", fake_browser)

    assert cli.main(["--no-open", "--log-level", "debug", "--port", "0"]) == 0
    assert calls == {"log_level": "debug"}


def test_splitshot_check_validates_runtime(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_check_media_tool", lambda tool: f"/fake/{tool}")
    monkeypatch.setattr(cli, "_check_qt_runtime", lambda: "6.9.0")
    monkeypatch.setattr(cli, "_check_dialog_runtime", lambda: "tkinter")

    assert cli.main(["--check"]) == 0

    output = capsys.readouterr().out
    assert "SplitShot runtime check" in output
    assert "- ffmpeg: /fake/ffmpeg" in output
    assert "- pyside6: 6.9.0" in output
    assert "- browser:index.html: present" in output


def test_cli_help_documents_browser_default() -> None:
    help_text = cli.build_parser().format_help()

    assert "SplitShot local stage video analyzer." in help_text
    assert "--desktop" not in help_text
    assert "--log-level" in help_text


class FakeRuntime:
    def run_server(self, server, *, open_browser: bool) -> int:
        server.start_background(open_browser=open_browser)
        return 0


def test_run_browser_keeps_default_startup_quiet(monkeypatch, capsys) -> None:
    class FakeServer:
        def __init__(self, controller, host, port, log_level) -> None:
            self.url = "http://127.0.0.1:8765/"
            self.activity = SimpleNamespace(path=Path("/tmp/splitshot.log"))

        def start_background(self, open_browser: bool) -> None:
            assert open_browser is True

    class FakeController:
        def open_project(self, path: str) -> None:
            raise AssertionError(f"Unexpected project open: {path}")

    monkeypatch.setattr(cli, "_browser_runtime", lambda: (FakeServer, FakeController, FakeRuntime))

    assert cli.run_browser() == 0
    assert capsys.readouterr().out == ""


def test_run_browser_prints_url_when_no_open_is_requested(monkeypatch, capsys) -> None:
    class FakeServer:
        def __init__(self, controller, host, port, log_level) -> None:
            self.url = "http://127.0.0.1:8765/"
            self.activity = SimpleNamespace(path=Path("/tmp/splitshot.log"))

        def start_background(self, open_browser: bool) -> None:
            assert open_browser is False

    class FakeController:
        def open_project(self, path: str) -> None:
            raise AssertionError(f"Unexpected project open: {path}")

    monkeypatch.setattr(cli, "_browser_runtime", lambda: (FakeServer, FakeController, FakeRuntime))

    assert cli.run_browser(open_browser=False) == 0
    output = capsys.readouterr().out
    assert "Open SplitShot at http://127.0.0.1:8765/" in output
    assert "activity log" not in output


def test_run_browser_prints_log_path_when_terminal_logging_is_enabled(monkeypatch, capsys) -> None:
    class FakeServer:
        def __init__(self, controller, host, port, log_level) -> None:
            self.url = "http://127.0.0.1:8765/"
            self.activity = SimpleNamespace(path=Path("/tmp/splitshot.log"))

        def start_background(self, open_browser: bool) -> None:
            assert open_browser is True

    class FakeController:
        def open_project(self, path: str) -> None:
            raise AssertionError(f"Unexpected project open: {path}")

    monkeypatch.setattr(cli, "_browser_runtime", lambda: (FakeServer, FakeController, FakeRuntime))

    assert cli.run_browser(log_level="debug") == 0
    output = capsys.readouterr().out
    assert "SplitShot activity log:" in output
    assert "splitshot.log" in output


def test_run_headless_emits_ready_line_and_respects_claim_env(monkeypatch, capsys) -> None:
    import splitshot.browser.server as browser_server_module
    import splitshot.ui.controller as controller_module

    calls: dict[str, object] = {}

    class FakeServer:
        def __init__(self, controller, host, port, log_level, require_session_claim) -> None:
            calls["host"] = host
            calls["port"] = port
            calls["log_level"] = log_level
            calls["require_session_claim"] = require_session_claim
            self.url = "http://127.0.0.1:9900/"
            self.activity = SimpleNamespace(path=Path("/tmp/splitshot.log"))

        def start_background(self, open_browser: bool) -> None:
            calls["open_browser"] = open_browser

        def shutdown(self) -> None:
            calls["shutdown"] = True

        def ready_line_payload(self) -> dict[str, object]:
            return {
                "protocol_version": "1",
                "session_id": "session-123",
                "base_url": "http://127.0.0.1:9900",
                "port": 9900,
                "claim_path": "/api/startup/claim",
                "startup_status_path": "/api/startup/status",
                "health_path": "/api/health",
                "events_path": "/api/events",
                "bootstrap_token": "bootstrap-token",
            }

    class FakeController:
        def open_project(self, path: str) -> None:
            calls["project_path"] = path

    class FakeEvent:
        def set(self) -> None:
            return

        def wait(self) -> bool:
            return True

    monkeypatch.setattr(browser_server_module, "BrowserControlServer", FakeServer)
    monkeypatch.setattr(browser_server_module, "find_free_port", lambda host, port: 9900)
    monkeypatch.setattr(controller_module, "ProjectController", FakeController)
    monkeypatch.setattr(cli.signal, "signal", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli.threading, "Event", FakeEvent)
    monkeypatch.setenv("SPLITSHOT_REQUIRE_SESSION_CLAIM", "1")

    assert cli.run_headless(port=0) == 0

    output_lines = capsys.readouterr().out.strip().splitlines()
    assert output_lines[0].startswith("SPLITSHOT_READY ")
    ready_payload = json.loads(output_lines[0].removeprefix("SPLITSHOT_READY "))
    assert ready_payload["session_id"] == "session-123"
    assert output_lines[1] == "Open SplitShot at http://127.0.0.1:9900/"
    assert calls == {
        "host": "127.0.0.1",
        "port": 9900,
        "log_level": "off",
        "require_session_claim": True,
        "open_browser": False,
        "shutdown": True,
    }


def test_cli_alias_entrypoints_preserve_parser_behavior(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, object]] = []
    project_path = tmp_path / "alias.ssproj"

    def fake_browser(
        host: str, port: int, open_browser: bool, project_path: Path | None, log_level: str
    ) -> int:
        calls.append(
            (
                "web",
                {
                    "host": host,
                    "port": port,
                    "open_browser": open_browser,
                    "project_path": project_path,
                    "log_level": log_level,
                },
            )
        )
        return 0

    monkeypatch.setattr(cli, "run_browser", fake_browser)

    assert (
        cli.web_main(
            [
                "--no-open",
                "--port",
                "9000",
                "--project",
                str(project_path),
                "--log-level",
                "warning",
            ]
        )
        == 0
    )
    assert calls == [
        (
            "web",
            {
                "host": "127.0.0.1",
                "port": 9000,
                "open_browser": False,
                "project_path": project_path,
                "log_level": "warning",
            },
        ),
    ]
