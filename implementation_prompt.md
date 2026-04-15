# SplitShot Implementation Prompt

You are working in the SplitShot repository. Implement the feature set below using the existing local-first architecture and the current browser and desktop code paths.

Key files and systems to use:

- Browser shell layout and controls: [src/splitshot/browser/static/index.html](src/splitshot/browser/static/index.html), [src/splitshot/browser/static/app.js](src/splitshot/browser/static/app.js), [src/splitshot/browser/static/styles.css](src/splitshot/browser/static/styles.css)
- Browser state payload: [src/splitshot/browser/state.py](src/splitshot/browser/state.py)
- Stage metrics builder: [src/splitshot/presentation/stage.py](src/splitshot/presentation/stage.py)
- Scoring summary logic: [src/splitshot/scoring/logic.py](src/splitshot/scoring/logic.py)
- Export pipeline and progress callbacks: [src/splitshot/export/pipeline.py](src/splitshot/export/pipeline.py)
- Browser server and activity logging: [src/splitshot/browser/server.py](src/splitshot/browser/server.py), [src/splitshot/browser/activity.py](src/splitshot/browser/activity.py)
- Shared controller: [src/splitshot/ui/controller.py](src/splitshot/ui/controller.py)
- Desktop window mirror: [src/splitshot/ui/main_window.py](src/splitshot/ui/main_window.py)
- Root CLI and script entrypoints: [src/splitshot/cli.py](src/splitshot/cli.py), [src/splitshot/browser/cli.py](src/splitshot/browser/cli.py), [pyproject.toml](pyproject.toml)
- Platform bootstrap scripts: [scripts/](scripts/) (PowerShell and Bash setup/install helpers for Windows, macOS, and Linux)
- Existing browser and desktop docs: [src/splitshot/browser/README.md](src/splitshot/browser/README.md), [src/splitshot/browser/static/README.md](src/splitshot/browser/static/README.md), [src/splitshot/ui/README.md](src/splitshot/ui/README.md), [src/splitshot/export/README.md](src/splitshot/export/README.md)
- Existing tests that will likely need updates: [tests/test_browser_static_ui.py](tests/test_browser_static_ui.py), [tests/test_main_window.py](tests/test_main_window.py), [tests/test_browser_control.py](tests/test_browser_control.py), [tests/test_cli.py](tests/test_cli.py)

Current repo facts to preserve:

- `browser_state()` already emits `metrics`, `timing_segments`, `split_rows`, `scoring_summary`, `export_presets`, and media availability flags.
- `StageMetrics` already includes `draw_ms`, `raw_time_ms`, `stage_time_ms`, `total_shots`, `average_split_ms`, `beep_ms`, and `final_shot_ms`.
- The Review pane currently uses a single `custom-box-mode` switch between manual custom text and imported summary text.
- The Export pane currently ends with an inline `export-log` block.
- The browser top strip currently shows `current-file`, `Draw`, `Raw`, `Shots`, and `Avg`.
- The desktop window still uses `Upload` terminology in several places.
- `uv run splitshot` is the default browser launcher, and the shared CLI already exposes `--web`, `--desktop`, `--no-open`, `--host`, `--port`, `--project`, `--check`, and `--log-level`.
- `ActivityLogger` already supports console mirroring levels `off`, `error`, `warning`, `info`, and `debug` while keeping the JSONL file log on.

Product direction:

- The browser shell is the primary production experience. The desktop window is a local validation and tooling surface for the same controller, model, and export pipeline.
- The supported workflow assumes a normal desktop OS session with a visible browser and local GUI. Do not optimize this repository for headless-only execution.
- Cross-browser validation should use real Chromium, Firefox, and WebKit or Safari-class browsers on the supported desktop operating systems.

Implement the following deliverables.

1. Add a new Metrics tab to the left rail.

   Add a new browser tab alongside the existing Project, Score, Splits, PiP, Overlay, Review, and Export buttons. The new tab should be powered by existing derived state rather than ad hoc DOM scraping. Build the view from `metrics`, `split_rows`, `timing_segments`, and `scoring_summary` so it combines stage timing and scoring context in one place.

   The Metrics tab should expose the same summary data that is already computed above the inspector, plus any useful stage trend details from Splits and Score. The goal is to provide a clean dashboard for comparing progress over time.

   Add export support from the Metrics view for both CSV and plain text. Keep the export format readable and flattened enough that users can open it in a spreadsheet or paste it into a tracker without manual cleanup.

2. Rework Review so summary and custom text can coexist.

   The Review pane should allow the imported PractiScore summary and one or more custom text boxes to appear on the same screen at the same time. The current implementation in `app.js` uses `custom-box-mode`, `effectiveCustomBoxText()`, and `syncCustomBoxModeState()` to force an either-or choice. Replace that model with repeatable, independently configurable box entries or an equivalent layout that supports multiple boxes.

   Each box should have its own controls for enable state, text content, placement, sizing, and styling. Reuse the existing custom box controls as the starting point, including `custom-box-enabled`, `custom-box-text`, `custom-box-x`, `custom-box-y`, `custom-box-width`, `custom-box-height`, and the style controls under `review-style-grid`.

   Preserve imported summary behavior from `state.scoring_summary.imported_overlay_text`, but make it coexist with user-authored boxes instead of replacing them.

3. Apply the same combined summary-plus-custom-box capability to Export.

   The Export pane should support the same custom-box-plus-summary layout as Review. Keep the export controls usable while showing the text/results content, and reuse the same rendering and state model rather than inventing a separate one-off implementation.

   The relevant export controls currently include `target-width`, `target-height`, `video-bitrate`, `ffmpeg-preset`, and the inline log block. Keep the content organized so the export options remain easy to scan.

4. Replace the inline export log with a Show Log button and real-time log window.

   Remove the inline `export-log` block from the Export pane. Replace it with a `Show Log` button that opens a separate modal or popup showing the export log while export is running.

   The log view should update in real time and use the existing export data flow. `export_project()` already accepts both `progress_callback` and `log_callback`, and the browser server already emits `api.export.progress` activity entries, so hook into that existing machinery rather than creating a second logging system.

   The log window should surface `project.export.last_log` and `project.export.last_error` in a clear way so users can see the final export output and any failure details.

5. Clarify review and export labels and helper text.

   Rename width and height labels to `Output Width` and `Output Height`. Clarify that `Video bitrate` is measured in megabits per second. Add a short FFmpeg introduction or help box above the output settings so users understand that the renderer is local and based on FFmpeg.

   If the desktop window mirrors these controls, update the corresponding labels there as well so browser and desktop wording remain aligned.

6. Replace the inspector header with a persistent status bar.

   The current browser top strip shows the current file plus Draw, Raw, Shots, and Avg. Turn that into a persistent status bar instead of a metrics summary.

   The bar should say `No Video Selected` until media is loaded, then display the selected video name. It should remain visible across all tabs and span the full width of the pane. Remove the existing summary metrics from that strip and stop using the inspector title as the primary top header.

   Update the aria label and any related status copy so the element reads as a status bar, not a metrics strip.

7. Enhance status and progress behavior for long-running actions.

   The browser should show visible progress for PractiScore import, project save, primary video import, and export. The progress should use a 0 to 100 percent scale and update at least once per second while work is active.

   There is already route-specific processing text in `app.js` for `/api/export`, `/api/import/primary`, `/api/import/secondary`, `/api/import/merge`, `/api/project/save`, and `/api/project/practiscore`, plus the existing `processing-bar` and its delayed show/hide timers. Extend that machinery rather than building a second progress system.

   The desktop export path already uses `QProgressDialog`, so the browser behavior should match that pattern. Make sure export progress uses the pipeline callback instead of a static status string.

8. Replace user-facing `upload` terminology with local-system wording.

   Search the entire repository for `upload` and replace user-facing occurrences with more accurate local-system terms such as `import`, `load`, `add`, `select`, or `choose`, depending on context.

   There are current matches in [src/splitshot/browser/static/app.js](src/splitshot/browser/static/app.js), [src/splitshot/browser/server.py](src/splitshot/browser/server.py), [src/splitshot/ui/main_window.py](src/splitshot/ui/main_window.py), [src/splitshot/ui/widgets/dashboard.py](src/splitshot/ui/widgets/dashboard.py), [src/splitshot/ui/README.md](src/splitshot/ui/README.md), [src/splitshot/browser/README.md](src/splitshot/browser/README.md), and [src/splitshot/browser/static/README.md](src/splitshot/browser/static/README.md). Update labels, hints, section names, status text, and docs so the UI no longer implies cloud uploading.

   Keep machine-facing APIs only where renaming them would create unnecessary churn.

9. Update tests and documentation to match the new contract.

   Refresh [tests/test_browser_static_ui.py](tests/test_browser_static_ui.py), [tests/test_main_window.py](tests/test_main_window.py), and [tests/test_browser_control.py](tests/test_browser_control.py) because they currently assert the old status strip, inspector, export log, and upload wording.

   Add or update coverage for the new Metrics tab, the Show Log modal, the persistent status bar, and the revised local-only terminology.

10. Harden the root `splitshot` command for production use.

   Keep `uv run splitshot` as the clean default launcher and make sure the existing command-line options continue to work exactly as they do now across the main entrypoint and the `splitshot-web` / `splitshot-desktop` aliases. Verify the help text and docs stay aligned with the real parser behavior.

   Make console logging quiet by default while preserving the file-based activity log. The user should be able to raise or reduce terminal verbosity from the command line with `--log-level`, and reset back to the quiet default without editing code or environment variables. If any startup path currently leaks extra noise, route it through the existing logging controls rather than adding another logging system.

   Add or update CLI, startup, and logging tests to cover the default command path, the alias entrypoints, and the console log-level behavior.

11. Reframe the PySide desktop app as a local validation and tool-testing interface.

   Make the browser shell the primary user-facing experience and use the desktop window as a controlled surface for validating the same controller, media analysis, merge, scoring, export, and filesystem behavior on each supported operating system. Keep the shared controller and derived state so the browser and desktop can be compared against the same data, but optimize the desktop window for diagnostics, smoke tests, and toolchain verification instead of trying to mirror the browser layout pixel-for-pixel.

   The desktop surface should expose the same underlying project and export actions as the browser, surface explicit checks for FFmpeg, FFprobe, file selection, path handling, and local media loading, and preserve only the platform-native affordances that are useful for validating real OS behavior. Any differences from the browser should be intentional, documented, and clearly framed as testing ergonomics rather than product drift.

   Validate the desktop surface on macOS, Windows, and Linux in a real GUI session, not headless.

12. Add cross-platform setup and installation scripts.

   Create PowerShell and Bash setup scripts under `scripts/` that install and configure everything required to run SplitShot on Windows, macOS, and Linux. The scripts should cover the pinned Python environment, `uv`, FFmpeg, FFprobe, a supported local browser for validation, and any other prerequisites needed for local launch, tests, and browser-based verification. Keep the scripts easy to discover from the repository root and from the README/docs.

   Include script variants or clear branches for the target shells so the Windows path uses PowerShell and the macOS/Linux path uses Bash, with consistent output and failure handling. The scripts should assume a real desktop session and should not present headless bootstrap as the primary workflow.

13. Polish the GitHub-facing project presentation.

   Make the repository landing page feel complete and polished for first-time visitors. Update the main README and any supporting repo docs so the page clearly explains that SplitShot is a local-first browser application, how it runs on macOS, Windows, and Linux, and how the browser shell is the main user experience while the desktop window serves as a local validation and tooling surface.

   At minimum, include prominent status badges, a clearer feature overview, screenshots or an animated capture of the browser flow and the desktop validation flow, a simple platform and browser support matrix, and a concise getting-started section that points to the new setup scripts and the normal `uv run splitshot` launch path. Keep the messaging local-first, browser-first, and avoid implying cloud services or headless deployment.

Implementation constraints:

- Prefer minimal, targeted changes that preserve the current controller/state flow and local-only architecture.
- Do not introduce a new backend model if the existing derived state can support the feature cleanly.
- Keep browser and desktop terminology aligned where the same user-facing concept appears in both surfaces.
- Preserve existing behavior that is already working unless it directly conflicts with the new requirements.