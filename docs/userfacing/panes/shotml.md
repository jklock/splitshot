# ShotML Pane

The ShotML pane owns detector tuning, detector reruns, and timing-change proposals. Use it when the automatic beep or shot list needs a detector-level correction before you finish manual timing, scoring, overlay review, metrics, or export.

## When To Use This Pane

- After importing a primary video, before making detailed manual timing edits.
- When quiet shots are missing or extra shots were created by echoes, props, spectators, or other range noise.
- When the detected beep appears too early or too late.
- When ShotML review suggestions should become explicit proposals that can be previewed, applied, or discarded.
- When you want detector settings saved with this project instead of changing every future project.

## What Is Saved

ShotML settings are project settings. They are stored in the project under `analysis.shotml_settings`, so one stage can use a different detector profile without silently changing another stage.

Changing a ShotML field saves the setting, but it does not rerun detection by itself. Click `Re-run ShotML` when you want the current settings to replace the automatic beep and shot detections.

`Reset Defaults` restores the current project to the factory ShotML profile. `Re-run ShotML` also saves the current threshold and settings as the app defaults so new projects start from that known profile.

## Basic Workflow

1. Import the primary video from the Project pane.
2. Open ShotML.
3. Start with `Detection threshold`; the value is saved for the project as you edit it.
4. Click `Re-run ShotML` when you are ready to run detection with the saved setting.
5. Check the Splits pane and waveform markers.
6. Return to ShotML and tune only the section related to the problem you see.
7. Click `Generate Proposals` when the review suggestions look useful.
8. Apply only the proposals that match the video and waveform.
9. Finish detailed manual timing in Splits.

## Threshold

| Control | Default | What it changes |
| --- | ---: | --- |
| Detection threshold | 0.35 | Overall shot sensitivity. Lower values accept quieter or weaker shots. Higher values reject more noise. |
| Cutoff base | 0.42 | The base probability cutoff used when threshold is mapped into the model peak picker. |
| Cutoff span | 0.28 | The amount added as threshold rises from low to high sensitivity. |

Use the threshold first. Most stage videos should not need advanced settings.

The default threshold is `0.35` because the current timing accuracy artifact recommends `0.35` with 0 missed shots, 0 extra shots, 304 matched shots at 0 ms mean absolute shot error, and 4.188 ms mean absolute beep/stage-time error across 16 auto-consensus training videos.

## Beep Detection

These controls choose where ShotML searches for the timer beep and how it refines the beep timestamp.

| Control | Default | What it changes |
| --- | ---: | --- |
| Onset fraction | 0.24 | How early in the beep tonal peak the timestamp is placed. Lower is earlier. Higher is later. |
| Search lead ms | 4000 | How far before the first provisional shot ShotML searches for a beep. |
| Tail guard ms | 40 | How much space is reserved between the beep search end and the first provisional shot. |
| Fallback window ms | 80 | Minimum beep search span when the first provisional shot is near the start. |
| FFT window s | 0.02 | Window length for the fallback tonal heuristic. |
| FFT hop s | 0.005 | Step size for the fallback tonal heuristic. |
| FFT band min/max Hz | 1800/4200 | Frequency band favored by the fallback beep heuristic. |
| Fallback multiplier | 0.8 | Sensitivity multiplier for fallback beep selection. |
| Tonal window ms | 80 | Main tonal scoring window for beep refinement. |
| Tonal hop ms | 1 | Main tonal scoring step size. |
| Tonal band min/max Hz | 1500/5000 | Frequency band favored by main beep scoring. |
| Refine pre/post ms | 500/450 | Search window around the rough beep estimate. |
| Gap before first shot ms | 40 | Minimum separation between refined beep and first shot. |
| Shot exclusion radius ms | 70 | Shot peak area excluded from beep selection. |
| Region cutoff base | 0.82 | Base value for the weighted beep region cutoff. |
| Region threshold weight | 0.1 | Amount the threshold lowers the weighted region cutoff. |
| Model boost floor | 0.3 | Baseline multiplier added before model beep probability boosts tonal score. |

## Shot Candidate Detection

| Control | Default | What it changes |
| --- | ---: | --- |
| Minimum shot interval ms | 100 | Shots closer than this are treated as invalid or duplicate candidates. It also gates the earliest auto shot after the beep. |
| Peak minimum spacing ms | 200 | Minimum spacing used by model peak picking before refinement and filtering. |
| Confidence source | Shot minus noise and beep | How ShotML converts model class probabilities into shot confidence. |

Use `Minimum shot interval ms` carefully. Very low values can keep echoes. Very high values can remove legitimate fast pairs.

## Shot Refinement

These controls move rough model peaks to the local waveform onset.

| Control | Default | What it changes |
| --- | ---: | --- |
| Onset fraction | 0.66 | Fraction of the local RMS peak used to place the shot timestamp. Lower is earlier. Higher is later. |
| Pre-window ms | 150 | Search time before each rough shot. |
| Post-window ms | 120 | Search time after each rough shot. |
| Midpoint clamp padding ms | 70 | Extra padding around inter-shot midpoint clamps. |
| Minimum search window ms | 12 | Smallest allowed refinement window. |
| RMS window ms | 3 | RMS frame size for shot refinement. |
| RMS hop ms | 1 | RMS step size for shot refinement. |

Use this section when the count is right but the markers consistently land early or late.

## False Positive Suppression

| Control | Default | What it changes |
| --- | ---: | --- |
| Weak onset threshold | 0.35 | Local onset support below this value is treated as weak. |
| Near-cutoff interval ms | 150 | Close-pair review range above the hard minimum interval. |
| Confidence weight | 0.55 | Model-confidence contribution when choosing between close candidates. |
| Support weight | 0.45 | Local waveform-support contribution when choosing between close candidates. |
| Weak support penalty | 0.08 | Penalty applied to weak-support candidates. |
| Suppress close-pair duplicates | On | Allows ShotML to remove weaker close-pair duplicates. |
| Suppress sound-profile outliers | On | Allows ShotML to remove shots that do not match the stage sound profile. |

Turn suppression off only when ShotML removes real shots that you can clearly see and hear.

## Confidence And Review

| Control | Default | What it changes |
| --- | ---: | --- |
| Refinement confidence weight | 0.35 | How much local onset support can lift model confidence. |
| Support pre/post ms | 45/80 | Window around a shot used to score local onset support. |
| Support RMS window/hop ms | 3/1 | RMS frame and step for onset support. |
| Alignment divisor ms | 45 | Distance scale used by the support alignment penalty. |
| Alignment multiplier | 0.25 | Maximum penalty applied when local support is far from the shot marker. |
| Profile search radius ms | 120 | Search radius for the best sound-profile window around a shot. |
| Profile distance limit | 5.0 | Feature-distance limit for sound-profile outlier review. |
| Profile high confidence limit | 0.995 | High-confidence shots are protected from profile outlier review. |

Use this section when the shot list is close but review pressure is too noisy or too quiet.

## Timing Changer

`Reset Defaults` is available at the top of the ShotML pane. `Generate Proposals` turns ShotML review suggestions into pending timing changes. A proposal does not change the timeline until you choose `Apply`.

| Proposal | Meaning |
| --- | --- |
| Move Beep | Move the beep marker to a proposed timestamp. |
| Move Shot | Move one shot marker to a proposed timestamp. |
| Suppress Shot | Remove a likely false shot. |
| Restore Shot | Return a manually edited shot to the original ShotML timestamp. |
| Choose Close Pair | Keep one candidate from a close pair and suppress the weaker duplicate. |

Proposal rows show the shot number, current time, target or alternate time, confidence, support, and the review message. Use the waveform and video to verify the proposal before applying it.

## Advanced Runtime

| Control | Default | What it changes |
| --- | ---: | --- |
| Window size | 2048 | Audio frame size passed into the classifier. |
| Hop size | 128 | Classifier step size. Lower values increase temporal density and runtime cost. |

These are model-runtime values. Keep the defaults unless you are testing detector behavior and validating the result against known footage.

## Relationship To Splits

ShotML owns detector settings and explicit reruns. Splits owns manual timeline editing after the detector pass. The threshold control no longer lives in Splits.

Use ShotML to change how automatic detection works. Use Splits and the waveform to select, nudge, drag, add, delete, and label the final timeline.

## Common Fixes

| Problem | First control to try |
| --- | --- |
| Quiet shots are missing. | Lower `Detection threshold`, then rerun. |
| Echoes are counted as shots. | Raise `Detection threshold`, or increase `Minimum shot interval ms`. |
| The count is right but shots are late. | Lower Shot Refinement `Onset fraction`. |
| The count is right but shots are early. | Raise Shot Refinement `Onset fraction`. |
| The beep is too close to the first shot. | Increase `Gap before first shot ms` or `Tail guard ms`. |
| Real fast pairs are suppressed. | Lower `Minimum shot interval ms` or turn off `Suppress close-pair duplicates`. |
| The proposal list is empty. | Rerun ShotML first, then generate proposals from the latest review suggestions. |

## Related Guides

Previous: [project.md](project.md)
Next: [splits.md](splits.md)

**Last updated:** 2026-04-20
**Referenced files last updated:** 2026-04-20
