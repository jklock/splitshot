from __future__ import annotations

from pathlib import Path

from splitshot import cli


def test_splitshot_defaults_to_browser_mode(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_browser(
        host: str,
        port: int,
        open_browser: bool,
        project_path: Path | None,
    ) -> int:
        calls["mode"] = "web"
        calls["host"] = host
        calls["port"] = port
        calls["open_browser"] = open_browser
        calls["project_path"] = project_path
        return 0

    monkeypatch.setattr(cli, "run_browser", fake_browser)

    assert cli.main(["--no-open", "--port", "0"]) == 0
    assert calls == {
        "mode": "web",
        "host": "127.0.0.1",
        "port": 0,
        "open_browser": False,
        "project_path": None,
    }


def test_splitshot_desktop_flag_dispatches_to_desktop(monkeypatch, tmp_path: Path) -> None:
    calls: dict[str, object] = {}
    project_path = tmp_path / "demo.ssproj"

    def fake_desktop(project_path: Path | None = None) -> int:
        calls["mode"] = "desktop"
        calls["project_path"] = project_path
        return 0

    monkeypatch.setattr(cli, "run_desktop", fake_desktop)

    assert cli.main(["--desktop", "--project", str(project_path)]) == 0
    assert calls == {"mode": "desktop", "project_path": project_path}


def test_splitshot_check_validates_runtime(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "resolve_media_binary", lambda tool: f"/fake/{tool}")

    assert cli.main(["--check"]) == 0

    output = capsys.readouterr().out
    assert "SplitShot runtime check" in output
    assert "- ffmpeg: /fake/ffmpeg" in output
    assert "- browser:index.html: present" in output


def test_cli_help_documents_browser_default() -> None:
    help_text = cli.build_parser().format_help()

    assert "Browser control is the default mode" in help_text
    assert "--desktop" in help_text
