# Source Launcher Packaging Plan

## Inputs

- Browser mode should be the default experience.
- Desktop/PySide mode should remain available as a secondary launch option.
- `.dmg` and `.exe` artifacts are out of scope for this pass.
- The app should run from the repo/package with one command and no separate mode-specific command knowledge.

## Goals

1. Make `splitshot` the one public command.
2. Launch browser control by default with `splitshot`.
3. Launch desktop UI with `splitshot --desktop`.
4. Keep `splitshot-web` and add/keep a desktop alias for compatibility, but document `splitshot` as the primary path.
5. Add a preflight/doctor mode so users can confirm FFmpeg/FFprobe and packaged assets are available.
6. Keep the implementation simple: one CLI module delegates to the existing browser server or desktop app.

## Launch Contract

Primary:

```bash
uv run splitshot
```

Starts the local browser control interface at `127.0.0.1:8765` and opens the browser.

Secondary:

```bash
uv run splitshot --desktop
```

Starts the PySide desktop interface.

Utility:

```bash
uv run splitshot --check
```

Validates that the media toolchain and browser assets are available.

## Validation

- CLI help must show browser default and desktop option.
- Browser default must be testable without launching a browser by starting with `--no-open` in API tests.
- Desktop smoke must still pass.
- Full automated suite must pass.
