> **Note:** Historical backend-floor package.

# Automation Truth Audit Matrix

Audited on 2026-05-20 against live repo code, route/state surfaces, targeted tests, and the shipped `main` baseline at `v1.0.5`.

This file is the current truth source for automation implementation status.

Authority order:

1. repo code and persisted data shape
2. targeted tests and browser/package proof
3. `docs/automate/*` and `docs/automate-ui/*` claims

Status vocabulary:

- `done`
- `partial`
- `missing`
- `deferred`
- `stale-doc`
- `contradicted`

Proof vocabulary:

- `source`: model, persistence, controller, route/state, targeted source tests
- `browser`: browser-shell behavior or browser-driven proof
- `packaged`: packaged desktop proof

## Capability Matrix

| Capability | Authoritative doc source | Code evidence | Current proof evidence | Verdict | Blocking impact on `automate-ui` | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Match workspace model, open/save, stage open/return | `02-editor-workflow-spec.md`, `04-data-model-spec.md` | `src/splitshot/domain/models.py`, `src/splitshot/persistence/workspaces.py`, `src/splitshot/ui/controller.py`, `src/splitshot/browser/server.py` | `uv run pytest tests/persistence/test_workspace_persistence.py` and `uv run pytest tests/browser/test_workspace_flows.py` both pass | `done` | UI can assume backend contract exists | `automate` | Keep as backend floor; expose it truthfully in UI |
| Shared defaults and stage overrides | `02-editor-workflow-spec.md`, `04-data-model-spec.md` | `resolve_setting`, workspace defaults/override routes and state summaries | `tests/browser/test_workspace_flows.py` passes | `done` | UI can build editors on top of it | `automate` | No backend redesign; add UI editors |
| Output profile CRUD and render-plan resolution | `06-feature-spec-single-video.md`, `10-acceptance-and-proof.md` | `OutputProfile`, `/api/output-profiles/*`, render-plan helpers | `tests/export/test_export.py` and workspace flow tests pass | `done` | UI can treat output-profile backend as present | `automate` | Add first-class Single Video UI |
| Library records, filter/open routes, proxy status summary | `03-performance-library-spec.md`, `08-feature-spec-performance-library.md` | `src/splitshot/persistence/library.py`, `/api/library/*`, `/api/proxy/*`, `browser/state.py` | source-level proof present; no current browser-shell proof of final surface | `done` | UI can use the backend floor, but cannot claim final user flow proof yet | `automate` | Add Performance Library UI and browser proof |
| `opened_from_match`, `stage_workspace_status`, `output_profile_summary` state fields | `02-editor-workflow-spec.md`, `03-performance-library-spec.md` | present in `src/splitshot/browser/state.py` | covered by live code inspection; older proof rows saying missing are stale | `stale-doc` | avoid planning extra backend work for fields that already exist | `automate` | update stale proof snapshots and UI assumptions |
| `library_filters`, `library_selection`, `library_reopen_targets` state fields | `03-performance-library-spec.md` | present in `src/splitshot/browser/state.py` | live code inspection; older proof rows saying missing are stale | `stale-doc` | avoid false backend-gap tracking in UI docs | `automate` | update stale proof snapshots and UI assumptions |
| Stage clip mutation support | `07-feature-spec-multi-video.md`, `automate-ui/spec.md` | `StageEntry.clip_sources` in `src/splitshot/domain/models.py`; clip mutation methods and preview reads in `src/splitshot/ui/controller.py`; clip routes in `src/splitshot/browser/server.py` | `uv run pytest tests/browser/test_workspace_flows.py` passes, including mutation, save/reopen, autosave, and preview-after-reopen coverage | `done` | UI can build truthful Stage Composite clip editors on a durable backend contract | `automate` | keep this as the backend floor; prove UI separately |
| Stage clip persistence | `automate-ui/spec.md`, `13-remediation-and-completion-plan.md` | `StageEntry.clip_sources` serialized in `src/splitshot/persistence/workspaces.py`; workspace save/open and autosave hydrate persisted clip state in `src/splitshot/ui/controller.py` | `uv run pytest tests/persistence/test_workspace_persistence.py` and `uv run pytest tests/browser/test_workspace_flows.py` both pass | `done` | no longer blocks truthful Multi Video composite UI | `automate` | preserve in future workspace/output changes |
| Dedicated stage-clip read route | `automate-ui/spec.md`, `execution-order.md` | `POST /api/workspace/stage/clip/list` implemented in `src/splitshot/browser/server.py`; controller reads persisted clip metadata from workspace stage entries | `uv run pytest tests/browser/test_browser_control.py -k "workspace_stage_clip_list or angle_director_plan_reads_persisted_output_profile_overrides"` passes | `done` | UI can hydrate clip editors from a narrow read surface | `automate` | keep `/api/state` summary-only |
| Dedicated angle-director plan read route | `automate-ui/spec.md`, `execution-order.md` | `OutputProfile.angle_director_plan` in `src/splitshot/domain/models.py`; `POST /api/angle/director/plan` implemented in `src/splitshot/browser/server.py`; merged plan resolution in `src/splitshot/ui/controller.py` | `uv run pytest tests/persistence/test_workspace_persistence.py`, `uv run pytest tests/browser/test_workspace_flows.py`, and `uv run pytest tests/browser/test_browser_control.py -k "workspace_stage_clip_list or angle_director_plan_reads_persisted_output_profile_overrides"` pass | `done` | UI can read current generated plan plus persisted overrides truthfully | `automate` | keep overrides output-profile scoped |
| Three-surface browser shell (`Single Video`, `Multi Video`, `Performance Library`) | `00-product-definition.md`, `automate-ui/spec.md` | browser shell still imports legacy pane set in `src/splitshot/browser/static/app.js` and retains flat tool rail | no browser proof of the three-surface shell | `missing` | primary UI blocker | `automate-ui` | shell overhaul required |
| Legacy flat rail retired as top-level structure | `automate-ui/spec.md` | `app.js` still centers `Project`, `PiP`, `Score`, `Splits`, `Markers`, `Overlay`, `Review`, `Export`, `Metrics`, `ShotML` | code inspection only | `missing` | prevents truthful product framing | `automate-ui` | replace with mode-aware surface model |
| PiP smoothness and merge usability | `automate-ui/spec.md`, `tracks/01-pip-performance-and-merge-editor.md` | known preview implementation still uses hard-seek-heavy path; no audit proving fix | no dedicated passing PiP proof captured in current package | `partial` | blocker number one for UI work | `automate-ui` | land sync strategy and proof it |
| Browser-shell completion proof for automation surfaces | `10-acceptance-and-proof.md`, `automate-ui/artifacts/ui-proof-matrix.md` | existing automation scenario script is controller-only | no current browser E2E proving Single/Multi/Library automation surfaces | `missing` | no UI package may claim completion from source tests alone | `automate-ui` | add browser proof after shell work lands |
| Packaged automation proof | `10-acceptance-and-proof.md`, `11-release-readiness.md`, `tracks/06-proof-regression-release.md` | release prerequisites documented, but package-specific packaged flows not proven | no current packaged proof for automation UI flows | `deferred` | release/shipping claims blocked | `automate` and `automate-ui` | only after browser/source proof is green |
| Baseline preservation from `v1.0.5` | `09-roadmap-and-task-plan.md`, `11-release-readiness.md` | baseline docs and code paths exist | targeted export/workspace tests pass; packaged re-proof still required for future shipping claims | `done` | UI work must preserve this floor | `automate` | keep as regression floor; re-prove when shipping UI changes |
| Automation scenario proof labeling | `10-acceptance-and-proof.md`, `PROOF-09-13.md`, `scripts/testing/*` | controller scenario script renamed away from misleading E2E label | source script remains valid for controller-level coverage only | `done` | prevents future overclaiming | `automate` | keep browser and packaged proof separate |

## Backend Contracts Proven Ready For UI Consumption

- workspace creation, save/load, stage membership, and stage open/return
- inheritance resolution and override summaries
- output profile CRUD and render-plan resolution
- library record storage, browse/filter/open routes, and proxy summary/status routes
- SplitShot-native naming and additive architecture relative to `Project`

## Backend Gaps Still Blocking Truthful UI

- current shell proof does not cover real automation UI surfaces

## Documentation Corrections Required By This Audit

- treat `docs/automate/proofs/*` as scoped snapshots, not current truth, unless they match this audit
- do not call controller-only scenario coverage browser E2E
- do not describe browser-shell or packaged completion from source-only proof
- keep `docs/automate` as backend contract and `docs/automate-ui/spec.md` as UI truth

## Readiness Gate

`docs/automate-ui` may begin the next implementation cycle only when all planning and task docs inherit the validated floor above.

That means:

- stage clip persistence and narrow read APIs are now part of the validated backend floor
- no task assumes the three-surface shell already exists
- no task uses controller-only proof as a substitute for browser or packaged proof
- every UI task is labeled `UI-only`, `narrow backend support required`, or `blocked by backend gap`
