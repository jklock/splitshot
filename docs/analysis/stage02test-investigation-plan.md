# Stage02test Investigation Plan

## Goal

Figure out what the detector is actually doing on Stage02test, what changed across the branch history, and whether any proposed fix truly improves shot timing, split timing, or false-shot handling on real gunshot audio.

The stage semantics are fixed:

1. The timer beep starts the stage.
2. Any number of shots can happen during the stage. Shot count is variable and is not the goal.
3. The last shot ends the stage, and total time is beep-to-last-shot.

The current clip-level assumption is not that Stage02test has a specific shot count. The assumption is only that the detector must find the beep and every real shot accurately enough to place the last shot correctly and compute the correct stage total.

## Why This Needs A Careful Pass

Gunshot audio is messy:

- one shot can produce a direct impulse plus strong reflections
- indoor echo can look like extra shots
- suppressed or distant shots can be weak but still real
- clipped audio can shift the apparent onset
- overlapping impulses can make a single shot look like multiple events
- a classifier peak can be right in class probability but still be centered at the wrong millisecond

Because of that, shot count alone is not enough. The question is not just "how many detections?" It is whether each detected event lines up with the actual impulse in the waveform and whether the resulting splits, last-shot time, and stage total are better than the prior result.

The model should ignore anything that is not the timer beep or a gunshot impulse. Background noise, voices, impacts, and other incidental sounds are only relevant if they are being mistaken for beep or shot events.

## Known Starting Point

- The user says Stage02test should have 19 shots.
- A previous comparison in the conversation was inconsistent about a historical 22-shot pass.
- The current checkout is on the mainline commit `1a857a3` (`Preserve raw ShotML confidence`), so there is no branch-specific code delta to inspect unless the historical baseline is taken from the parent commit `aee3bb1`.
- The current branch work has already shown that confidence changes do not automatically mean timing changes.
- The working hypothesis must remain open until the clip, the history, and the training corpus are all compared directly.

## Observed Corpus State

- `.training/shotml-label-manifest.json` currently lists 16 videos.
- The current manifest summary shows `use_detector_drafts: false` with all 16 videos skipped, while an older summary shows `use_detector_drafts: true` with 9 included videos and 7 skipped by review flags.
- The autolabel summary reports 16 `auto_labeled` entries and no verified labels in the manifest.
- The current per-video detector output spans 17 to 23 shots across the corpus, so the corpus itself already proves that a raw count is not a reliable correctness signal.
- Duplicate-stage pairs disagree on shot count and often on beep family as well, which means the comparison must be waveform-aware and clip-specific.
- The `.training` directory contains the clip set that needs to be reviewed one by one: `20251116_095437.MP4`, `20251116_103457.MP4`, `20251116_110444.MP4`, `Clip1.MP4`, `Clip2.MP4`, `Clip3.MP4`, `Clip4.MP4`, `Clip5.MP4`, `Stage02test.MP4`, `Stage1 2.MP4`, `Stage1.MP4`, `Stage2.MP4`, `Stage3 2.MP4`, `Stage3.MP4`, `Stage4.MP4`, and `stage2 2.MP4`.

## Upstream Reference

- The upstream `vivsvaan/Gunshot-Detection` repository is relevant, but it is a different architecture from SplitShot's current ShotML pipeline.
- That repo uses a spectrogram-image classifier built with FastAI/ResNet50, with training and testing notebooks that convert `.mp3` audio into mel spectrogram images and classify them as `gun` vs `non gun`.
- It also includes a simple alerting path that emails a contact when the classifier predicts gunshot.
- Treat it as an external baseline for gunshot false-positive behavior, not as a direct timing or split-timeline reference.
- Compare it for acoustic failure modes, class separation, and dataset assumptions, especially where echoes, clipped impulses, or non-gun impulsive sounds can look gunshot-like.

## Current Findings

- The upstream repo confirms that a spectrogram-image classifier is a viable gunshot detector baseline, but it does not solve SplitShot's timestamping problem by itself.
- SplitShot's current detector history shows the real issue is not just detection count; it is whether the selected beep and shot times match the waveform onset closely enough to improve split and stage timing.
- The `.training` corpus currently contains 16 auto-labeled clips with no verified labels, so the current dataset is still a consensus-labeled training set rather than a manually grounded truth set.
- The per-video detector counts already range from 17 to 23 shots across the corpus, which means any useful fix must be clip-specific and waveform-aware rather than count-driven.
- Duplicate-stage pairs are especially important because some of them disagree on both beep family and shot count, which is exactly where echo, clipped onset, or miscentered-window errors are most likely to appear.
- Stage02test still needs to be re-read against the waveform and the historical detector output before any claim about 19 vs 21 vs 22 shots can be treated as settled.

## Investigation Questions

1. What did the commit immediately before this branch do on the same clip?
2. Which Stage02test detections are real shots and which are likely echo, clipping, or miscentered peaks?
3. Do the current detector changes improve actual timing, or only confidence/review metadata?
4. Are there other clips in `.training` with the same failure mode?
5. Is the error coming from the detector, the feature extraction, the refinement logic, or the evaluation assumptions?

## Evidence To Collect

### Historical branch comparison

- Identify the branch point commit.
- Run the historical detector from the parent commit on the same clip.
- Compare shot lists, beep time, last-shot time, and split errors against the current branch.
- Record exact timestamps, not just counts.

### Stage02test audio review

- Inspect the waveform around every candidate shot.
- Check whether each candidate is a clean onset, a reflected echo, or a miscentered window peak.
- Note whether nearby alternate peaks are stronger or weaker than the chosen one.
- Compare confidence, local waveform shape, and neighborhood context for any suspicious detections.

### Training corpus comparison

For every video in `.training`:

- run the current detector
- compare output against the existing saved labels and artifacts
- note whether the failure mode is extra shots, missed shots, shifted onsets, or beep misplacement
- group clips by the same acoustic pattern rather than by final shot count alone

### External research

- Review common gunshot detection failure modes in audio analysis.
- Focus on how echoes, reverberation, and impulse overlap affect timestamp precision.
- Use that research to interpret the clip data, not to replace it.

## Working Rules

- Do not patch code until the historical comparison and corpus review are complete.
- Do not trust counts without checking the waveform neighborhoods.
- Do not assume that a high confidence score means the timestamp is correct.
- Do not assume that a stable shot count means the detector is actually accurate.
- Prefer direct audio evidence over narrative summaries.

## Output Format For The Review

For Stage02test and then for each training clip, record:

- detected beep time
- detected shot times
- suspected false positives
- suspected missed shots
- timestamp shifts versus the historical detector
- whether the current branch is better, worse, or unchanged for actual timing
- the specific audio evidence supporting that conclusion

## Success Criteria

A change is only an actual improvement if it reduces one or more of these on the evaluator or on verified waveform review:

- beep error
- split error
- last-shot error
- stage-time error
- false positives from echoes or clipped transients
- missed real shots

If a change only alters confidence or review metadata, it is not yet an accuracy fix.

## Next Actions

1. Identify the branch point commit and compare the parent revision against the current branch on Stage02test.
2. Review each `.training` clip against the current detector output and saved artifacts.
3. Gather outside references on gunshot timing and echo behavior to interpret the audio evidence.
4. Return to Stage02test with the comparison set in hand and decide whether any code change is actually justified.

Last updated: 2026-04-19
Referenced files last updated: docs/analysis/SHOTML.md, src/splitshot/analysis/detection.py, scripts/analysis/evaluate_timing_accuracy.py, artifacts/old-vs-old-plus-new-comparison.json
