# SplitShot Package

This package contains the application entry points, bootstrap logic, and top-level configuration helpers.

## Main Files

- [__main__.py](__main__.py) delegates to `splitshot.cli.main` so `python -m splitshot` works.
- [cli.py](cli.py) parses command-line arguments and chooses browser, desktop, or check mode.
- [app.py](app.py) creates the Qt application and opens the desktop window.
- [config.py](config.py) stores app-wide settings such as detection threshold, recent projects, and default layout choices.

## Runtime Flow

The default entry path is browser mode:

1. `splitshot.cli.main` parses the command line.
2. `run_browser` creates a `ProjectController` and a `BrowserControlServer`.
3. The browser server serves the static UI, exposes the JSON API, and writes an activity log.
4. `--desktop` switches to the PySide6 window in `splitshot.app.run`.
5. `--check` validates FFmpeg, FFprobe, the Qt export runtime, native file-dialog support, and the packaged browser assets.

## Notes

- The CLI aliases `splitshot-web` and `splitshot-desktop` are defined in `pyproject.toml`.
- App settings are persisted in `~/.splitshot/settings.json` through `config.py`.
- The package version is exported from `__init__.py` as `__version__`.

**Last updated:** 2026-04-15
**Referenced files last updated:** 2026-04-15
