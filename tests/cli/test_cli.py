from __future__ import annotations

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


def test_run_browser_keeps_default_startup_quiet(monkeypatch, capsys) -> None:
    class FakeServer:
        def __init__(self, controller, host, port, log_level) -> None:
            self.url = "http://127.0.0.1:8765/"
            self.activity = SimpleNamespace(path=Path("/tmp/splitshot.log"))

        def serve_forever(self, open_browser: bool) -> None:
            assert open_browser is True

    class FakeController:
        def open_project(self, path: str) -> None:
            raise AssertionError(f"Unexpected project open: {path}")

    monkeypatch.setattr(cli, "_browser_runtime", lambda: (FakeServer, FakeController))

    assert cli.run_browser() == 0
    assert capsys.readouterr().out == ""


def test_run_browser_prints_url_when_no_open_is_requested(monkeypatch, capsys) -> None:
    class FakeServer:
        def __init__(self, controller, host, port, log_level) -> None:
            self.url = "http://127.0.0.1:8765/"
            self.activity = SimpleNamespace(path=Path("/tmp/splitshot.log"))

        def serve_forever(self, open_browser: bool) -> None:
            assert open_browser is False

    class FakeController:
        def open_project(self, path: str) -> None:
            raise AssertionError(f"Unexpected project open: {path}")

    monkeypatch.setattr(cli, "_browser_runtime", lambda: (FakeServer, FakeController))

    assert cli.run_browser(open_browser=False) == 0
    output = capsys.readouterr().out
    assert "Open SplitShot at http://127.0.0.1:8765/" in output
    assert "activity log" not in output


def test_run_browser_prints_log_path_when_terminal_logging_is_enabled(monkeypatch, capsys) -> None:
    class FakeServer:
        def __init__(self, controller, host, port, log_level) -> None:
            self.url = "http://127.0.0.1:8765/"
            self.activity = SimpleNamespace(path=Path("/tmp/splitshot.log"))

        def serve_forever(self, open_browser: bool) -> None:
            assert open_browser is True

    class FakeController:
        def open_project(self, path: str) -> None:
            raise AssertionError(f"Unexpected project open: {path}")

    monkeypatch.setattr(cli, "_browser_runtime", lambda: (FakeServer, FakeController))

    assert cli.run_browser(log_level="debug") == 0
    output = capsys.readouterr().out
    assert "SplitShot activity log: /tmp/splitshot.log" in output


def test_cli_alias_entrypoints_preserve_parser_behavior(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, object]] = []
    project_path = tmp_path / "alias.ssproj"

    def fake_browser(host: str, port: int, open_browser: bool, project_path: Path | None, log_level: str) -> int:
        calls.append(("web", {
            "host": host,
            "port": port,
            "open_browser": open_browser,
            "project_path": project_path,
            "log_level": log_level,
        }))
        return 0

    monkeypatch.setattr(cli, "run_browser", fake_browser)

    assert cli.web_main(["--no-open", "--port", "9000", "--project", str(project_path), "--log-level", "warning"]) == 0
    assert calls == [
        ("web", {
            "host": "127.0.0.1",
            "port": 9000,
            "open_browser": False,
            "project_path": project_path,
            "log_level": "warning",
        }),
    ]
