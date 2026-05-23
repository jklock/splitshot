# Remediation And Completion Plan

This plan converts the current failure state into implementation work.

| Item | Current State | Desired State | Owner | Tests | Proof |
|---|---|---|---|---|---|
| View model | One cockpit with conditional panels | Four distinct frontend views with shared shell/state | UI | browser shell tests | empty/loaded screenshots |
| Landing | Present but visually basic | Professional front door with recent work and quick starts | UI | landing tests | landing screenshots |
| Stage | Useful editor buried under competing chrome | Deep editor with simplified grouped tools and integrated output/multi-angle controls | UI | Stage browser E2E | Stage empty/loaded screenshots |
| Match | Panel-like surface inside editor chrome | First-class workspace frontend | UI + backend | workspace tests, browser E2E | Match empty/loaded screenshots |
| Library | Panel-like surface inside editor chrome | First-class historical analytics frontend | UI + backend | library tests, browser E2E | Library empty/loaded screenshots |
| PiP sync | Needs proof against jump/reseek churn | Smooth by-eye sync and drag | UI | PiP interaction/perf tests | audit artifact |
| Waveform | Single-track foundation | Multi-track, segments, auto-cuts | UI | waveform tests | loaded Stage screenshot |
| Export | Scattered controls | Stage, batch, recap, composite workflows with progress | UI + backend | export/browser tests | progress/completion screenshots |
| Proof | Current screenshots show failure | Complete proof matrix | QA | command suite | final contact sheet |

## Blocking Rules

- Do not polish Match/Library inside the old editor chrome; split the view structure first.
- Do not implement visual-only controls without backend/test proof.
- Do not mark any matrix row done without artifact or command evidence.
