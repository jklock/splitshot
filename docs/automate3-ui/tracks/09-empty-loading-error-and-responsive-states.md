# Track 09: Empty, Loading, Error, And Responsive States

## Required States

Every view must define:

- empty
- loading
- loaded
- route failure
- unavailable action
- stale data
- narrow viewport.

## Specific States

- no media in Stage
- no match open
- match with no stages
- empty library
- missing proxy
- stale proxy
- missing archive
- unresolved reopen target
- failed export
- failed route mutation
- offline/local file unavailable.

## Exact UX

| State | Visual Treatment | Copy | Primary Action | Secondary Action |
|---|---|---|---|---|
| Route failure | Red shell banner, persists until dismissed | `Unable to load {view}. {error detail}.` | Retry | Go Home |
| No media in Stage | Centered empty state graphic or dark illustration placeholder | `Import a video to begin editing this stage.` | Import Video | Open File |
| No match open | Centered empty state in Match view | `Create a match or open a recent one to get started.` | New Match | Open Recent |
| Match with no stages | Inline hint inside match workspace | `This match has no stages yet. Add your first stage.` | Add Stage | None |
| Empty library | Centered empty state | `No performance history yet. Complete a stage or match to see records here.` | None | None |
| Missing proxy | Inline warning in detail panel | `Proxy not generated. Generate a proxy to preview this stage.` | Generate Proxy | None |
| Stale proxy | Inline warning in detail panel | `Proxy is out of date. Refresh to see the latest version.` | Refresh Proxy | Dismiss |
| Missing archive | Inline warning in detail panel | `Archive not found. Regenerate the archive before export or comparison.` | Regenerate Archive | Dismiss |
| Failed export | Inline error plus log link/status detail | `Export failed: {reason}. Check the log for details.` | Retry | Dismiss |
| Unresolved reopen target | Disabled button with tooltip | `Cannot open: {reason}` | None | None |
| Failed mutation | Inline error near the affected control | `{action} failed: {reason}` | Retry | Dismiss |

## Responsive Requirements

- no overlapping text
- stable toolbar heights
- tables degrade to scroll or stacked layouts
- preview/timeline remains usable
- primary actions remain visible.

## Proof

- screenshot matrix includes empty and loaded states
- responsive screenshots for at least one narrow width
- browser tests cover route failure UI where practical.
