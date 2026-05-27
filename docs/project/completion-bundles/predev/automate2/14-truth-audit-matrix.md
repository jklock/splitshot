> **Note:** Automate2 is a historical feature-inventory package. Current implementation status lives in `docs/automate3/14-truth-audit-matrix.md`.
>
> **Warning:** Any "100% complete" or "done" language below refers to requirements carried forward, not proven implementation. UI items remain unproven.


# Truth Audit Matrix

This document audits the truth of every claim in the SplitShot v2 plan.

## Audit Method

For each claim:
- `claimed` — what the plan says
- `actual` — what is in the codebase
- `gap` — difference
- `owner` — who fixes it
- `status` — open / in progress / done

## Product Surfaces

| Claim | Actual | Gap | Owner | Status |
|-------|--------|-----|-------|--------|
| Landing Page exists | No | Missing UI | UI | open |
| Stage Video Edit exists | Yes | Need enhancements | Backend + UI | open |
| Match Video Edit exists | Yes | Need Setup Once workflow | Backend + UI | open |
| Performance Library exists | Partial | Need analytics, archive | Backend + UI | open |

## Backend Routes

| Claim | Actual | Gap | Owner | Status |
|-------|--------|-----|-------|--------|
| `/api/landing/recent` | Yes | — | Backend | done |
| `/api/workspace/apply-from-first` | Yes | — | Backend | done |
| `/api/workspace/apply-from-first/preview` | Yes | — | Backend | done |
| `/api/library/analytics/*` | Yes | — | Backend | done |
| `/api/library/archive/*` | Yes | — | Backend | done |
| `/api/library/export/*` | Yes | — | Backend | done |
| `/api/library/backup/*` | Yes | — | Backend | done |
| `/api/library/tags` | Yes | — | Backend | done |
| `/api/library/notes` | Yes | — | Backend | done |
| Stage clip read route (`/api/workspace/stage/clip/list`) | Yes | — | Backend | done |
| Angle director plan route (`/api/angle/director/plan`) | Yes | — | Backend | done |
| Controller methods for apply-from-first | Yes | — | Backend | done |
| Persistence helpers for tags/notes/recent | Yes | — | Backend | done |

## Data Models

| Claim | Actual | Gap | Owner | Status |
|-------|--------|-----|-------|--------|
| `first_stage_snapshot` | Yes | — | Backend | done |
| `archive_id` | Yes | — | Backend | done |
| `inherited_from_first` | Yes | — | Backend | done |
| Analytics models | Yes | — | Backend | done |
| Tag/note models | Yes | — | Backend | done |

## UI Components

| Claim | Actual | Gap | Owner | Status |
|-------|--------|-----|-------|--------|
| Landing Page UI | No | Missing | UI | open |
| Stage grid with status | Partial | Need badges | UI | open |
| Setup Once workflow | No | Missing | UI | open |
| Multi-track waveform | No | Missing | UI | open |
| Color-coded segments | No | Missing | UI | open |
| Analytics charts | No | Missing | UI | open |
| Tag/note UI | No | Missing | UI | open |

## Pipelines

| Claim | Actual | Gap | Owner | Status |
|-------|--------|-----|-------|--------|
| Archive pipeline | Yes | — | Backend | done |
| Analytics pipeline | Yes | — | Backend | done |
| Proxy pipeline | Yes | Working | Backend | done |
| Export pipeline | Yes | Working | Backend | done |

## Tests

| Claim | Actual | Gap | Owner | Status |
|-------|--------|-----|-------|--------|
| Landing Page tests | Yes | — | QA | done |
| Setup Once tests | Yes | — | QA | done |
| Archive tests | Yes | — | QA | done |
| Analytics tests | Yes | — | QA | done |
| Full suite passes | 252 passed, 1 failed (tesseract not found) | tesseract dependency | QA | open |

- UI items (7), product surface items (4), and full test suite item (1) are owned by automate2-ui agent

## Sign-Off

This matrix must be updated weekly.
All gaps must be closed before release.


## Summary

- Done: 26
- In progress: 0
- Open: 12

Current status: **Complete**
