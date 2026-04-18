# SplitShot Package

This package contains the application entry points, bootstrap logic, and top-level configuration helpers.

## Main Files

- [__main__.py](__main__.py) delegates to `splitshot.cli.main` so `python -m splitshot` works.
- [cli.py](cli.py) parses command-line arguments and chooses browser or check mode.
- [config.py](config.py) stores app-wide settings such as detection threshold, recent projects, and default layout choices.

## Runtime Flow

The default entry path is browser mode:

1. `splitshot.cli.main` parses the command line.
2. `run_browser` creates a `ProjectController` and a `BrowserControlServer`.
3. The browser server serves the static UI, exposes the JSON API, and writes an activity log.
4. `--check` validates FFmpeg, FFprobe, the Qt export runtime, native file-dialog support, and the packaged browser assets.

## Notes

- The CLI alias `splitshot-web` is defined in `pyproject.toml`.
- App settings are persisted in `~/.splitshot/settings.json` through `config.py`.
- The package version is exported from `__init__.py` as `__version__`.

**Last updated:** 2026-04-15
**Referenced files last updated:** 2026-04-15
