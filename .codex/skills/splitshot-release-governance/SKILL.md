---
name: splitshot-release-governance
description: Cut and maintain SplitShot releases with the repo's semver tags, changelog-backed GitHub release notes, branch protections, and cross-platform release workflow.
---
Use this skill when:
- The manager asks to cut a SplitShot release.
- The manager asks to update release notes.
- The manager asks to fix GitHub branch/tag protections.
- The manager asks about the exact release flow from code change to published release.
- Version files, release workflows, GitHub releases, or maintainer release docs change.

Core rule:
SplitShot releases are semver releases. The current first real release is `v1.0.0`. Future examples should use the next patch tag, such as `v1.0.1`, unless the manager requests another version.

Source of truth:
- `pyproject.toml`
- `src/splitshot/__init__.py`
- `uv.lock`
- `electron/package.json`
- `CHANGELOG.md`
- `.github/workflows/release.yml`
- `scripts/release/extract_release_notes.py`
- `scripts/release/apply_github_rulesets.sh`
- `docs/project/GOVERNANCE.md`
- `docs/project/ELECTRON_RELEASE.md`

Exact flow from code change to release:

1. Make and verify the code changes on a short-lived branch.
2. Update release-facing docs and `CHANGELOG.md` in the same change when behavior, setup, or release process changes.
3. Before cutting a release version, update every version source together:
   - `pyproject.toml`
   - `src/splitshot/__init__.py`
   - `uv.lock`
   - `electron/package.json`
4. Write or update the matching changelog section:
   - existing first release: `## v1.0.0`
   - next patch example: `## v1.0.1`
5. Verify the repo:

```bash
uv run splitshot --check
uv run python scripts/testing/run_test_suite.py --mode all-together --format table
```

6. Merge the release-ready state into `main`.
7. Confirm protections and branch hygiene:

```bash
bash scripts/release/apply_github_rulesets.sh
git branch -r --merged origin/main
```

8. Create and push the semver tag:

```bash
git tag -a v1.0.1 -m "SplitShot v1.0.1"
git push origin v1.0.1
```

9. Let `.github/workflows/release.yml` publish the release from the tag.
10. If release notes need a manual refresh after publish:

```bash
uv run python scripts/release/extract_release_notes.py v1.0.1 --output artifacts/release-notes.md
gh release edit v1.0.1 --title "SplitShot 1.0.1" --notes-file artifacts/release-notes.md --latest
```

11. Delete merged topic branches when the release work is complete.

If an old non-semver release exists:
- create the proper semver tag and release for the same commit
- move the long-form notes onto the semver release
- remove or retire the legacy release/tag so the release line is unambiguous

Done means:
- Version files agree.
- The GitHub release tag is semver.
- The GitHub release body is sourced from `CHANGELOG.md`.
- Branch/tag protections are active.
- The exact flow is documented in repo instructions and maintainer docs.

Report:
Changed:
Verified:
Result:
Risks:
