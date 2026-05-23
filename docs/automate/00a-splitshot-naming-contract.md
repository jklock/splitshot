# SplitShot Naming Contract

This document governs every implementation-facing addition in `docs/automate`.

## Purpose

The automation package may compare SplitShot to competitors, but the implementation itself must remain SplitShot-native.

This document prevents copied terminology from leaking into:

- user-facing UI
- API routes
- state payload keys
- schema/type names
- task names
- acceptance claims

## Naming Rules

1. Preserve the current SplitShot product surfaces:
   - `Single Video`
   - `Multi Video`
   - `Performance Library`
2. Competitor names may appear only in:
   - comparison docs
   - parity audits
   - rationale notes that explain why SplitShot chose a different label
3. Competitor names must not appear in:
   - new route names
   - new persisted field names
   - browser state keys
   - implementation task labels
   - final feature labels
4. When a competitor capability is adopted, document it as:
   - competitor concept
   - SplitShot concept
   - actual implementation label

## Required Translation Table

| Competitor concept | SplitShot concept | Implementation label |
| --- | --- | --- |
| Auto Trim | fast reviewed run windowing | `Run Window` |
| Performance subtitles | truth-derived export captions | `Metric Captions` |
| Split Sync | same-stage angle alignment | `Angle Align` |
| Stage Mix | directed multi-angle cut planning | `Angle Director` |
| Merge (match recap) | many-stage recap assembly | `Match Recap` |
| Merge (same-stage multi-clip) | one-stage multi-clip composition | `Stage Composite` |
| Export ratios | reusable framing outputs | `Frame Profiles` |
| Portrait tracking | tracked reframing | `Subject Track Crop` |
| Intro title cards | opening identity frame | `Lead-In Card` |
| Custom watermarks | persistent brand overlay | `Brand Mark` |
| Camera-role labeling | angle purpose tagging | `Angle Roles` |
| Per-clip audio control | angle-level mix control | `Audio Mix Lanes` |
| Per-clip score metadata | stage/result transition summaries | `Result Cards` |

## Documentation Rules

- Use the SplitShot implementation label as the primary term in all docs after this point.
- If a competitor comparison is helpful, mention it once in parentheses and then continue with the SplitShot term only.
- If an old heading in the package still uses a competitor label, keep the old heading only where changing it would erase historical comparison context; add the SplitShot term immediately beneath it.

## Acceptance Rule

No implementation agent should have to invent names.

Before work begins from this package, the agent must be able to answer:

- what the SplitShot feature is called
- which competitor concept it corresponds to
- which route/state/schema names are allowed
- which copied names are forbidden
