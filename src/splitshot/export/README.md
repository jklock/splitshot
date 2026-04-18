# Export

The export package turns a project into a rendered local video file with overlays, merge layouts, aspect-ratio cropping, and FFmpeg encoding.

## Files

- [presets.py](presets.py) defines export presets, preset summaries, and the helper that applies a preset to a project.
- [pipeline.py](pipeline.py) builds render plans, crops the output, renders overlays, and writes the final file.

## Pipeline Overview

1. `export_project` validates the project and ensures the primary video exists.
2. `_ensure_qt_gui_application` creates a headless Qt GUI context when export runs outside the desktop app.
3. `build_base_render_plan` chooses the single-video, dual-angle, or grid-merge render path.
4. `compute_crop_box` and `_target_dimensions` determine the output framing.
5. `_render_pass` decodes raw frames, draws overlays with `OverlayRenderer`, and pipes them into FFmpeg for encoding.

## Presets and Settings

- `ExportPresetDefinition` describes the built-in preset catalog.
- `apply_export_preset` updates the project export settings from a preset id.
- `export_settings_summary` produces API-friendly export settings for the browser UI.

## Output Constraints

- Supported output extensions are `.mp4`, `.m4v`, `.mov`, and `.mkv`.
- H.264 and HEVC are the available video codecs.
- AAC is the available audio codec.
- The pipeline uses BT.709 SDR color settings.

## Implementation Notes

- Merge export uses `calculate_merge_canvas` to determine layout geometry.
- Still-image merge sources are looped so they can participate in video export.
- Two-pass encoding is supported and uses a temporary pass log directory.
- The final export log is stored on `project.export.last_log`, the last error on `project.export.last_error`, and browser mode can stream incremental progress and log lines through the activity logger while export is running.

**Last updated:** 2026-04-15
**Referenced files last updated:** 2026-04-15
