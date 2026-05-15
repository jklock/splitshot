# Repository Governance

This document is the maintainer-facing source of truth for SplitShot branch protection, release-tag protection, and branch lifecycle.

## Branch Model

- `main` is the only long-lived branch.
- All feature, fix, and experiment work should happen on short-lived branches such as `codex/*` or focused topic branches.
- Merge the branch back into `main` when the change is ready.
- Delete the branch after merge unless it is intentionally still serving active work.

## `main` Protection

SplitShot uses a PR-first model for `main`.

- Normal changes should arrive through pull requests.
- The maintainer keeps bypass access for urgent hotfixes, release work, or rule recovery.
- `main` should reject force-pushes and branch deletion.
- `main` should require these checks before merge:
  - `linux-tests`
  - `macos-tests`
  - `windows-tests`

The current reproducible ruleset source lives in:

```bash
scripts/release/apply_github_rulesets.sh
```

Apply or refresh the rulesets with:

```bash
bash scripts/release/apply_github_rulesets.sh
```

## Release Tags

- Release tags use semver: `vX.Y.Z`
- Release tags are intended to be immutable
- The maintainer retains bypass access for emergency repair, but the default rules block update and deletion of `refs/tags/v*`

## Release Flow

Current release baseline:

- published first release line: `v1.0.0`
- next patch example: `v1.0.1`

1. Update versioned source of truth files in the repo.
2. Finalize the release notes in [../../CHANGELOG.md](../../CHANGELOG.md).
3. Merge the release-ready changes into `main`.
4. Extract the exact GitHub release body from the changelog:

```bash
uv run python scripts/release/extract_release_notes.py v1.0.1 --output artifacts/release-notes.md
```

5. Create and push the semver tag, for example:

```bash
git tag -a v1.0.1 -m "SplitShot v1.0.1"
git push origin v1.0.1
```

6. Let `.github/workflows/release.yml` build all three platform artifacts and publish the GitHub release from that tag.
7. If the GitHub release body needs a manual refresh after publish:

```bash
gh release edit v1.0.1 --title "SplitShot 1.0.1" --notes-file artifacts/release-notes.md --latest
```

## Branch Cleanup

After merges:

- delete merged topic branches locally
- delete merged remote topic branches on `origin`
- keep the remote branch list short enough that active work is obvious

Check merged remote branches with:

```bash
git branch -r --merged origin/main
```

## Read This Next

- [DEVELOPING.md](DEVELOPING.md)
- [ELECTRON_RELEASE.md](ELECTRON_RELEASE.md)
- [../../CHANGELOG.md](../../CHANGELOG.md)
