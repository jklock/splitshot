# Browser Overlay and Score Cleanup Plan

## Goal

Correct the failed browser pass by removing half-built UI, making per-shot scoring assignment visible and direct, and fixing overlay positioning so badge controls produce usable overlays instead of full-height blocks.

## Requirements From User Feedback

- Remove the split-card box grid entirely.
- Remove the Scoring `Behavior` row.
- Let users assign score values directly, not through a hidden/lower control.
- Fix overlay placement, sizing, colors, and direction so it works in the live video preview.
- Shrink the left rail by about 25%.
- Add spacing around the red Delete Project button.
- Fix the export pipeline so successful encodes are not reported as failed when FFmpeg decoder shutdown produces an expected pipe-close message.
- Iterate through the app again with feature-level tests, not just string checks.

## Implementation Steps

1. Remove split-card markup, renderer calls, CSS, and tests.
2. Rebuild scoring shot list rows with shot label, shot time, assigned score, and inline score select.
3. Remove the obsolete score-position button and behavior copy from the scoring page.
4. Rewrite live overlay CSS to rely on inline placement instead of `.overlay-left/.overlay-right` stretching the overlay full height.
5. Clamp live overlay badges to normal intrinsic size and apply chosen dimensions only as width/height, not layout-stretching bars.
6. Shrink the left rail default and layout reset values.
7. Add project action spacing and keep Delete Project red/full-width.
8. Accept expected decoder broken-pipe shutdown only when the encoder completed successfully.
9. Update tests to assert the removed UI stays removed and the new scoring/overlay/export behavior exists.
10. Run full validation, generate Stage1 output, and commit/merge.
