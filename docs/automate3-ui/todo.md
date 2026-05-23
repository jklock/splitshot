# Todo

> **Live remediation checklist.** All code fixes, route wiring, and backend gaps resolved 2026-05-22. Remaining: visual proof screenshots (captured but need human review) and visual review.

## Completed Code Fixes (2026-05-22)

- [x] Route contract test — parse all `callApi("/api/...")` in app.js and fail on unregistered routes
- [x] Shell/rail regression fix — `button[data-tool="project"]` visible after `setActiveSurface("single")`
- [x] Setup-once route fix — UI calls registered `/api/workspace/apply-from-first` and `/api/workspace/apply-from-first/preview`
- [x] Backup handler nesting fix — backup create/restore separate from setup-once handler
- [x] Shared defaults reset route fix — `/api/workspace/defaults/reset` registered with handler
- [x] Output hook persistence — save button wires to `/api/output-profiles/update`
- [x] Stage composite / multi-angle wiring — all 8 routes registered; controls already wired in UI
- [x] Match/export route wiring — `/api/workspace/export` and `/api/workspace/recap/render` registered with handlers
- [x] Library persistence wiring — tags, notes, open, export call registered routes
- [x] Route classification test — 2 new routes added to `NON_PROJECT_JSON_POST_ROUTES`
- [x] Stage composite route coverage test — all 8 composite routes verified in server source
- [x] ESLint config — `eslint.config.js` created (flat config for ESLint v10)

## Completed Backend Gaps (2026-05-22)

- [x] `/api/workspace/apply-from-first` — copies concrete settings, respects overrides, reports conflicts
- [x] `/api/workspace/apply-from-first/preview` — concrete diff with conflict detection
- [x] `/api/library/backup/create` — persists to `~/.splitshot/library/backups/`
- [x] `/api/library/backup/restore` — validates schema, writes records to library store
- [x] `/api/landing/recent` — returns stage projects + match workspaces + library records
- [x] `proxy_refresh` — generates default render plan when no output profile specified

## Remaining: Visual Proof

- [x] Screenshots captured (13 files in `docs/screenshots/automate3/`: 4 empty, 3 loaded, 4 feature, 2 contact sheets)
- [x] Screenshot paths fixed in `capture_browser_screenshots.py`
- [x] Export pipeline proven: workspace_export produces real MP4 files (single + batch)
- [x] Recap pipeline proven: workspace_recap_render produces composite MP4 (2 stages → recap.mp4)
- [ ] Visual review by human or vision-capable reviewer
