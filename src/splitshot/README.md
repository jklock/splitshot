# SplitShot Source Tree

<!-- Documentation reviewed: 2026-08-11 -->

This package is the root map for the application code. Use it to decide where to start reading and which subsystem owns a change.

## Start Here

Read these files first:

1. [cli.py](cli.py)
2. [browser/server.py](browser/server.py)
3. [ui/controller.py](ui/controller.py)
4. [domain/models.py](domain/models.py)

Then continue with the package README for the subsystem you are touching.

## Package Map

| Package | Purpose | Read this first |
| --- | --- | --- |
| [analysis/](analysis) | Audio analysis, ShotML inference, timing review suggestions | [analysis/README.md](analysis/README.md) |
| [benchmarks/](benchmarks) | Benchmark CLI and stage-suite CSV export | [benchmarks/README.md](benchmarks/README.md) |
| [browser/](browser) | HTTP server, browser state serialization, browser-shell assets | [browser/README.md](browser/README.md) |
| [domain/](domain) | Shared project schema, enums, serialization | [domain/README.md](domain/README.md) |
| [export/](export) | Render planning, presets, final FFmpeg export | [export/README.md](export/README.md) |
| [media/](media) | FFmpeg resolution, media probing, waveform extraction, thumbnails | [media/README.md](media/README.md) |
| [merge/](merge) | Merge-layout geometry | [merge/README.md](merge/README.md) |
| [overlay/](overlay) | Overlay badge and text-box rendering | [overlay/README.md](overlay/README.md) |
| [persistence/](persistence) | `.ssproj` bundle save/load/delete | [persistence/README.md](persistence/README.md) |
| [presentation/](presentation) | Derived metrics and timing presentation objects | [presentation/README.md](presentation/README.md) |
| [scoring/](scoring) | Scoring presets, score math, PractiScore helpers | [scoring/README.md](scoring/README.md) |
| [timeline/](timeline) | Split-row and timing helpers | [timeline/README.md](timeline/README.md) |
| [ui/](ui) | Shared controller and mutation layer | [ui/README.md](ui/README.md) |
| [utils/](utils) | Small shared helpers | [utils/README.md](utils/README.md) |

## Runtime Path

1. `cli.py` parses arguments and selects browser, headless, or check mode.
2. `browser/server.py` starts the local HTTP server and static shell.
3. `ui/controller.py` mutates the shared `Project`.
4. `domain/models.py` defines the canonical schema that other layers read and write.
5. Analysis, scoring, presentation, merge, overlay, and export derive behavior from that shared project state.

## Related Docs

- [../../docs/project/DEVELOPING.md](../../docs/project/DEVELOPING.md)
- [../../docs/project/ARCHITECTURE.md](../../docs/project/ARCHITECTURE.md)
- [../../docs/tests/TEST_SUITE_GUIDE.md](../../docs/tests/TEST_SUITE_GUIDE.md)
- [../../scripts/README.md](../../scripts/README.md)
