# Remediation and Completion Plan

This document is the post-merge execution reset for the automation branch after importing `main` at `v1.0.5`.

It exists to answer one question precisely:

What work remains on `automate`, and what released `main` behavior must stay untouched while that work lands?

## Stable Baseline Now Inherited From `main`

These are no longer open automation tasks. They are released baseline behavior that continuing work must preserve:

- Windows overlay export font repair via `src/splitshot/overlay/font_policy.py`
- browser preview font-stack alignment for Windows-safe families
- packaged Windows OCR proof for exported overlay readability
- `docs/Clip1.MP4` fixture validation across packaged/test workflows
- packaged-app workflow and release-proof hardening already cut on the `v1.0.5` line

## Automation Capability Already Present On This Branch

The merged branch already contains the backend/product foundation for:

- match workspaces and stage entries
- match shared defaults and stage overrides
- output profile contracts and render-plan resolution
- performance library records and reopen flows
- retained proxy metadata and refresh orchestration
- Stage Composite, Match Recap, Angle Align, Angle Director, Audio Mix, Result Card data paths

The remaining work is primarily about truthful UI exposure, final integration, and proof.

## Remaining Work That Still Matters

### 1. UI Shell Completion

The browser shell still does not expose the automation backend as a coherent product.

Still required:

- top-level `Single Video` / `Multi Video` / `Performance Library` surface model
- context header and scope-aware shell state
- first-class output profile UI
- first-class workspace UI
- first-class Performance Library UI

Primary planning source:

- `docs/automate-ui/spec.md`

### 2. PiP Smoothness And Merge Usability

This is still the first visible blocker.

Still required:

- bounded playback-rate correction for small drift
- hard-seek only at explicit sync boundaries
- drag/update behavior that does not churn sync state every frame

Primary planning source:

- `docs/automate-ui/tracks/01-pip-performance-and-merge-editor.md`

### 3. Narrow Backend Support That The UI Still Needs

The UI package should assume the backend is mostly present, but not fully done.

Still verify and finish only if missing after code inspection:

- persistence for stage clip state used by `Stage Composite`
- dedicated read route for stage clips
- dedicated read route for current angle-director plan
- keep `/api/state` summary-oriented instead of moving heavy UI payloads into the poll path

### 4. Baseline-Preservation Proof

Every future automation slice now needs a proof layer that did not matter before the merge:

- re-prove `v1.0.5` export-font behavior did not regress
- re-prove packaged OCR overlay readability did not regress
- re-prove packaged/test workflows still use `docs/Clip1.MP4`
- re-prove legacy single-stage browser/export flows still pass their narrow contracts

### 5. Automation-Specific Packaged Proof

After UI completion, still required:

- one packaged Single Video output-profile flow
- one packaged Multi Video recap or composite flow
- one retained proxy/library reopen flow

## Work To Avoid Re-Doing

Do not reopen these as speculative plan items unless a regression is proven:

- Windows font-family policy design
- OCR proof mechanism for packaged Windows export
- `docs/Clip1.MP4` CI fixture plumbing
- baseline packaged workflow/release hardening already merged from `main`
- version-source mismatch cleanup already reflected on the automate branch

## Execution Order From Here

1. Preserve the `v1.0.5` baseline with targeted proof.
2. Finish PiP smoothness and merge-editor usability.
3. Land the three-surface shell model.
4. Expose Single Video output-profile UI.
5. Expose Multi Video workspace/recap/composite UI.
6. Expose Performance Library UI.
7. Add only the narrow backend support still required by that UI.
8. Run targeted proof, relevant suites, browser audits when applicable, then packaged automation proof.

## Validation Checklist

Use the narrowest useful check first:

- `uv run pytest tests/export/test_export.py`
- `uv run pytest tests/browser/test_browser_static_ui.py`
- `uv run pytest tests/browser/test_browser_control.py`
- `uv run pytest tests/browser/test_workspace_flows.py`
- `uv run pytest tests/export/test_merge_export_contracts.py`
- `uv run pytest tests/browser/test_browser_full_app_e2e.py`
- `uv run python scripts/audits/browser/run_browser_ui_surface_audit.py`
- `uv run python scripts/testing/run_test_suite.py --mode all-together --format table`

## Completion Standard

The automate branch is ready for the next implementation cycle only when:

- the remaining work list above reflects actual merged code reality
- the UI package and backend package agree on what is still missing
- `v1.0.5` released behavior is treated as a regression floor, not as future work
- new capabilities are backed by the targeted proof their owning package requires
- broader suite or packaged-proof expectations are called out explicitly before claiming closure
