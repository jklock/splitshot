# Export

This package owns final render planning, export presets, overlay composition, merge integration, and FFmpeg encoding.

## Purpose

Use it when the change affects output geometry, codec or preset behavior, overlay rendering during export, pass logging, or final file generation.

## Read This First

- [pipeline.py](pipeline.py)
- [presets.py](presets.py)

## Main Files

- [pipeline.py](pipeline.py): export pipeline, render planning, encoding, log capture
- [presets.py](presets.py): built-in export presets and API summaries

## Runtime Flow

1. Validate the project and source media.
2. Build the render plan and crop geometry.
3. Render merge layouts and overlays.
4. Encode through FFmpeg and persist export logs and errors back to the project.

## Key Extension Points

- `export_project`
- `build_base_render_plan`
- `apply_export_preset`
- `export_settings_summary`

## Related Tests

- [../../../tests/export/](../../../tests/export/)
- [../../../tests/browser/test_merge_export_contracts.py](../../../tests/browser/test_merge_export_contracts.py)

## Related Docs

- [../../../docs/project/ARCHITECTURE.md](../../../docs/project/ARCHITECTURE.md)
- [../../../docs/userfacing/panes/export.md](../../../docs/userfacing/panes/export.md)
