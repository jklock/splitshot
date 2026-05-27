# API And Backend Contract

This table records current repo truth and target requirements. It is not a completion claim. The implementation agent must verify payloads with route/controller tests before wiring controls.

| Area | Routes / APIs | Current Repo Truth | Known Gap | Target Requirement |
|---|---|---|---|---|
| Landing recent | `/api/landing/recent` | Handler scans `~/.splitshot/projects` for `project.json` and returns entries with `type: "stage"` and `surface: "single"`. | Does not return Match or Library records. | Display returned stage entries honestly; extend backend before showing Match/Library recent items. |
| Workspace lifecycle | `/api/workspace/new`, `/open`, `/save` | Controller methods exist and are wired through `server.py`. | Payload shape and error behavior must be asserted for final Match UI. | Create/open/save Match from Match view with recoverable errors. |
| Workspace stages | `/api/workspace/stage/add`, `/remove`, `/open`, `/return` | Controller methods exist and are wired. | View-state return behavior is not enough for final Match UI proof. | Stage grid can add/remove/open stages and return to same Match context. |
| Defaults/overrides | `/api/workspace/defaults`, `/api/workspace/stage/override`, `/override/reset` | Controller supports shared defaults and overrides. | UI conflict/visibility semantics need proof. | Match view shows shared/custom/missing state and lets user override/reset safely. |
| Apply from first | `/api/workspace/apply-from-first/preview`, `/api/workspace/apply-from-first` | Routes exist. Preview returns stage entries and `will_inherit`; apply stores snapshot metadata and marks siblings inherited. | Metadata-only; does not diff or copy real Stage 1 project settings. | Preview concrete setting diffs/conflicts and persist copied settings before UI claims complete. |
| Stage clips | `/api/workspace/stage/clip/list`, `/add`, `/update`, `/remove` | Routes appear wired for clip list and mutations. | Payload and persistence must be re-verified against final composite UI. | Multi-angle and Stage Composite views use durable clip state. |
| Angle director | `/api/angle/director/plan`, `/generate`, `/override` | Controller methods exist. Plan keys are not documented in Automate3. | UI cannot safely render plan until schema is captured in tests/docs. | Document schema, test it, then wire smart cuts/override UI. |
| Output profiles | `/api/output-profiles/list`, `/create`, `/update`, `/delete`, `/render` | Controller methods exist. | Render-plan payload is under-specified; `proxy_refresh` calls `output_profile_render("")`, which needs investigation. | Render preview uses verified payload; proxy refresh does not rely on suspicious empty output id behavior. |
| Library records | `/api/library/list`, `/api/library/filter` | Library helpers read JSONL metrics files. Fresh install data may be empty. | Empty-state and seeded loaded-state proof required. | Library handles empty install and loaded fixture records. |
| Library reopen | `/api/library/stage/open`, `/api/library/match/open` | Routes exist. | Unresolved target behavior needs exact UX/test proof. | Reopen buttons enabled only when target is resolvable; otherwise disabled with reason. |
| Proxy | `/api/library/proxy/open`, `/api/library/proxy/refresh` | Routes exist. | Proxy refresh implementation needs investigation because controller calls render with empty output id in one path. | Proxy state clearly reports ready/missing/stale/error and actions work. |
| Analytics | `/api/library/analytics/trend`, `/compare` | Routes exist. | Must prove useful output with seeded records. | Charts and comparison render from verified payloads. |
| Archive/backup | `/api/library/archive/create`, `/backup/create`, `/backup/restore` | Archive route exists. Backup create returns a manifest; restore accepts a manifest and returns counts. | Backup create does not persist a backup; restore does not write library store. | Either implement durable backup/restore or label UI actions as manifest export/import only. |
| Library export | `/api/library/export/json`, `/api/library/export/csv` | Routes exist. | Output path/download behavior requires proof. | Export actions provide clear output/download result and failure state. |
| Tags/notes | `/api/library/tags/update`, `/api/library/notes/update` | Routes exist. | Persistence must be tested with real records. | Tags/notes edit, save, reload, and display correctly. |
| Export jobs | existing render/export APIs plus progress state | Existing export/render paths are scattered. | Final batch/recap/composite progress contract not established. | Export workflows expose progress, completion, failure reason, and output path. |

## Routes With Known Backend Gaps

- `/api/workspace/apply-from-first`: metadata-only; it does not copy actual output profiles, overlay settings, export settings, or other Stage 1 project settings to sibling stages.
- `/api/workspace/apply-from-first/preview`: does not produce concrete diffs or conflict details; it mainly reports whether a stage will inherit based on override presence.
- `/api/library/backup/create`: returns an in-memory JSON manifest; it does not persist a backup to disk.
- `/api/library/backup/restore`: accepts a manifest and returns counts; it does not restore the library store.
- `/api/landing/recent`: returns stage project directories only; it does not aggregate Match or Library records.
- `ProjectController.proxy_refresh`: calls `output_profile_render("")` in one path; this needs investigation before final proxy UI claims.

## Implementation Rule

Do not wire a control to a route just because the route exists. First prove payload shape, persistence, error behavior, and fixture coverage with a targeted test. If the route is a stub or metadata-only, mark the UI feature blocked or implement the backend contract first.
