# Shooting Cut Feature Matrix

This document compares [shootingcut.com](https://shootingcut.com) against the current SplitShot direction and decides how each competitor feature should map into SplitShot.

## Decision Vocabulary

- `adopt` — implement in SplitShot because it fits the product directly
- `reframe` — keep the user outcome but fit it to SplitShot's identity
- `defer` — valuable, but not for the first delivery wave
- `reject` — not aligned with SplitShot's product direction

## Matrix

| Competitor feature | Current SplitShot status | SplitShot home | Decision | Notes |
| --- | --- | --- | --- | --- |
| Smart audio analysis | Already core: beep and shot detection, waveform review, timing edits, metrics | Single Video, Multi Video | adopt | Keep and strengthen. This remains a differentiator, not just parity work. |
| Auto Trim | Not productized as a fast named workflow yet | Single Video first, later Multi Video batch | adopt | Derived from reviewed or draft stage boundaries with configurable padding. |
| Performance subtitles | Core data exists, but not as a fast export preset | Single Video, Multi Video | adopt | Reframe as output preset layered over trustworthy timing and metrics. |
| Split Sync | Existing PiP and sync foundations exist | Multi Video for same-stage angle compare, Single Video drill-down | adopt | Needs clearer productization and same-stage dual-angle workflow. |
| Merge | Current merge concepts exist, but not as a dedicated many-stage workflow | Multi Video | adopt | Must define stage montage vs same-stage clip merge explicitly. |
| Stage Mix | No direct productized equivalent | Multi Video | adopt | Reframe as analysis-driven auto-direction across multiple angles, with manual cut overrides. |
| Export ratios | Existing export presets already include social-style aspect ratios | Single Video, Multi Video | adopt | Integrate into named output variants instead of one-off export settings only. |
| Portrait tracking | Not present as a tracked crop system | Single Video first, later Multi Video | adopt | Export/crop feature, not a product identity shift. |
| Intro title cards | Not present | Single Video, Multi Video | adopt | Output recipe component. |
| Custom watermarks | Not present as a first-class recipe component | Single Video, Multi Video | adopt | Output recipe component. |
| Direct social sharing | Not current product direction | none | defer | Useful later, but not product-defining and not required for truth-first editing. |
| Apple device workflows | SplitShot is cross-platform desktop-first | none | reject | Preserve macOS, Windows, Linux identity instead of copying Apple-native UX. |
| iCloud/Photos sync | Not current storage model | none | reject | Performance Library should own canonical history without Apple-specific storage assumptions. |
| Camera-role labeling (`POV`, `Follow`, `Static`) | Not present | Multi Video | adopt | Needed for Stage Mix and multi-angle auto-cut logic. |
| Auto-cut override flow | Not present | Multi Video | adopt | Required if Stage Mix is implemented honestly. |
| Per-clip audio control | Not a first-class workflow today | Multi Video | adopt | Needed for montage and multi-angle workflows. |
| Per-clip score metadata | Core score context exists, but not in match-montage workflow terms | Multi Video | adopt | Useful for stage-to-stage consistency and montage labeling. |
| Four isolated editing modes | Competitor organizes product this way | Single Video, Multi Video, Performance Library | reframe | Replace with SplitShot's three product surfaces. |
| Social-first positioning | Competitor emphasizes posting speed | none | reject | SplitShot should remain analysis-first with optional polished outputs. |
| "Personal director" cinematic identity | Competitor markets this heavily | Multi Video only as limited helper | reframe | Keep analysis truth central; automation assists but does not define the app. |
| Apple-only product framing | Competitor is native Apple-first | none | reject | Preserve cross-platform desktop direction. |
| One-tap multi-platform share | Not current core need | none | defer | Can come after stronger output recipes and library/proxy workflows. |

## SplitShot-specific Conclusions

### Directly aligned

These competitor features fit SplitShot with little philosophical conflict:

- smart audio analysis
- Run Window
- Metric Captions
- export ratios
- Lead-In Card
- Brand Mark

### Valuable but must be re-scoped

These features should be implemented only inside SplitShot's editor model:

- Angle Align
- Match Recap and Stage Composite
- Angle Director
- Subject Track Crop
- Angle Roles
- Cut Override Plan
- Audio Mix Lanes
- Result Cards

### Out of scope for the product definition

These should not steer product architecture:

- Apple-native UX parity
- iCloud/Photos as the product's storage backbone
- social-first sharing as the core promise

## Immediate Feature Ownership

### Single Video

- Run Window
- Metric Caption presets
- output variants
- Frame Profiles
- Subject Track Crop
- Lead-In Card
- Brand Mark

### Multi Video

- match ingest
- shared settings
- stage overrides
- Angle Align
- Match Recap
- Stage Composite
- Angle Director
- Audio Mix Lanes
- Result Cards
- multi-stage output recipes

### Performance Library

- historical retrieval of the results of those workflows
- retained proxy playback
- metric comparisons over time

## SplitShot Translation Contract

The matrix remains the comparison surface only.

Implementation docs, APIs, tasks, and UI labels must use the following SplitShot-native names:

| Competitor feature | SplitShot implementation label |
| --- | --- |
| Smart audio analysis | `Detection Review` |
| Auto Trim | `Run Window` |
| Performance subtitles | `Metric Captions` |
| Split Sync | `Angle Align` |
| Merge (many stages) | `Match Recap` |
| Merge (same stage, many clips) | `Stage Composite` |
| Stage Mix | `Angle Director` |
| Export ratios | `Frame Profiles` |
| Portrait tracking | `Subject Track Crop` |
| Intro title cards | `Lead-In Card` |
| Custom watermarks | `Brand Mark` |
| Camera-role labeling | `Angle Roles` |
| Auto-cut override flow | `Cut Override Plan` |
| Per-clip audio control | `Audio Mix Lanes` |
| Per-clip score metadata | `Result Cards` |

## Implementation Ownership Additions

### Current repo seams to extend

- `src/splitshot/domain/models.py`
- `src/splitshot/persistence/projects.py`
- `src/splitshot/ui/controller.py`
- `src/splitshot/browser/state.py`
- `src/splitshot/browser/server.py`
- `src/splitshot/export/pipeline.py`
- `src/splitshot/browser/static/`

### Delivery decisions locked here

- `Match Recap` and `Stage Composite` are both first-delivery features and must be documented as separate workflows.
- `Angle Align` is same-stage alignment behavior and must not be used as a synonym for match editing.
- `Angle Director` is optional guidance over authoritative review truth; it cannot silently rewrite stage truth.
- `Metric Captions`, `Lead-In Card`, and `Brand Mark` are output-layer capabilities only.

### Required proof mapping

Every `adopt` or `reframe` row in this table must map to:

- one owning spec in `docs/automate`
- one implementation label from this file
- one test or proof owner in [10-acceptance-and-proof.md](10-acceptance-and-proof.md)

No feature may be marked `done` in the final audit unless that mapping exists.

## Outcome Parity Audit Contract

Parity is outcome-based only.

The future implementation must prove the adopted or reframed user outcome while preserving SplitShot-native naming, architecture, and truth ownership.

### Adopted outcome audit

| SplitShot implementation label | Required user outcome | Implementation home | Proof required before parity claim |
| --- | --- | --- | --- |
| `Detection Review` | User can inspect and correct authoritative timing truth quickly | `Single Video`, `Multi Video` | timing/browser proof plus packaged review flow |
| `Run Window` | User can derive a clean run clip from reviewed boundaries without manual timeline editing | `Single Video` | stage render test plus packaged stage-output flow |
| `Metric Captions` | User can render fast data-rich exports from accepted truth | `Single Video`, `Multi Video` | export truth test plus packaged render flow |
| `Angle Align` | User can align same-stage angles predictably | `Multi Video` | persistence/browser proof plus packaged Stage Composite flow |
| `Match Recap` | User can build one many-stage recap output from one match workspace | `Multi Video` | recap tests plus packaged recap render flow |
| `Stage Composite` | User can build one-stage multi-clip outputs without forking stage truth | `Multi Video` | clip composition tests plus packaged composite render flow |
| `Angle Director` | User can receive editable cut guidance for multi-angle outputs | `Multi Video` | state/persistence proof plus packaged guided output flow when shipped |
| `Frame Profiles` | User can render named framing variants without custom one-off setup | `Single Video`, `Multi Video` | export tests plus packaged output flow |
| `Subject Track Crop` | User can persist output-local reframing intent for non-source formats | `Single Video`, later `Multi Video` | profile persistence proof plus packaged crop-aware flow when shipped |
| `Lead-In Card` | User can prepend output identity frames sourced from reviewed metadata | `Single Video`, `Multi Video` | export tests plus packaged output flow |
| `Brand Mark` | User can apply persistent output branding without altering truth | `Single Video`, `Multi Video` | export tests plus packaged output flow |
| `Angle Roles` | User can tag angle purpose for guided multi-angle composition | `Multi Video` | workspace/state proof plus guided-flow proof |
| `Cut Override Plan` | User can override suggested cuts before export | `Multi Video` | route/UI proof plus guided-flow proof |
| `Audio Mix Lanes` | User can control clip-local audio contribution in recap/composite outputs | `Multi Video` | route/export proof plus packaged render flow |
| `Result Cards` | User can insert stage/result summaries sourced from reviewed truth | `Multi Video` | export truth proof plus packaged recap flow |

### Reframe, defer, and reject guardrails

- `reframe`
  - document the desired user outcome
  - document the SplitShot-native implementation name
  - document what must not be copied directly from the competitor UX or architecture
- `defer`
  - document why the outcome is delayed
  - do not implement partial versions that create release or parity ambiguity
- `reject`
  - document the non-goal boundary clearly
  - do not add adjacent features that quietly recreate the rejected direction
