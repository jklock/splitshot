# Domain

The domain package defines the project schema, enums, and serialization helpers shared by the browser UI, desktop UI, analysis code, and export pipeline.

## Files

- [models.py](models.py) contains every enum and dataclass in the shared project model.

## Core Types

Enums in this package include `ShotSource`, `ScoreLetter`, `OverlayPosition`, `BadgeSize`, `MergeLayout`, `PipSize`, `ExportQuality`, `ExportPreset`, `ExportFrameRate`, `ExportVideoCodec`, `ExportAudioCodec`, `ExportColorSpace`, and `AspectRatio`.

The primary dataclasses are:

- `BadgeStyle`
- `VideoAsset`
- `MergeSource`
- `ScoreMark`
- `ShotEvent`
- `TimingEvent`
- `AnalysisState`
- `ScoringState`
- `OverlaySettings`
- `MergeSettings`
- `ExportSettings`
- `UIState`
- `Project`

## Serialization

- `project_to_dict` converts the full nested project model into JSON-safe data.
- `project_from_dict` restores a saved project bundle into a `Project` instance.
- The serializer handles enums, datetimes, paths, lists, dictionaries, and nested dataclasses.

## Model Behavior

- `Project.sort_shots()` keeps detected and manual shots in time order.
- `Project.touch()` refreshes the `updated_at` timestamp.
- `VideoAsset` exposes `path_obj` and `size` convenience properties.

## Persistence Notes

- `project_from_dict` reconstructs `secondary_video` from `merge_sources` when needed.
- Still-image assets are preserved through the `is_still_image` flag and suffix-based fallback.
- `Project` is the shared schema used by both UIs and by the export pipeline.

**Last updated:** 2026-04-13
**Referenced files last updated:** 2026-04-13
