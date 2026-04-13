# Scoring

The scoring package defines the preset catalog and the helpers that calculate score totals, penalties, and hit factor.

## Files

- [logic.py](logic.py) contains `ScoringPreset`, `PenaltyField`, the preset catalog, and the scoring calculations.

## Presets

The built-in preset ids are:

- `uspsa_minor`
- `uspsa_major`
- `ipsc_minor`
- `ipsc_major`
- `idpa_time_plus`
- `steel_challenge`
- `gpa_time_plus`

Each preset defines its point map, scoring mode, human-readable description, penalty fields, and selectable score letters.

## Core Functions

- `scoring_presets_for_api` returns preset data for the browser UI.
- `get_scoring_preset` resolves a preset id to a `ScoringPreset`.
- `apply_scoring_preset` updates the project scoring state and clears invalid penalty counters.
- `assign_score` writes a `ScoreMark` onto a shot.
- `set_score_position` stores the normalized position for the score mark.
- `calculate_hit_factor` computes hit factor when the active preset uses hit-factor scoring.
- `calculate_scoring_summary` produces the summary shown in the browser UI and the overlay renderer.
- `current_shot_index` finds the shot at or before a playback position.

## Calculation Notes

- Penalties can come from manual penalty totals, score-letter penalties, or preset-specific penalty fields.
- Hit factor is only meaningful when scoring is enabled and the active preset is a hit-factor ruleset.
- Time-plus presets report a final time instead of hit factor.