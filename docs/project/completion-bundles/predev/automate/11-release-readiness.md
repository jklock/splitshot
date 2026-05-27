# Release Readiness

This document defines the release-facing work required when the `docs/automate` feature set ships.

It does not mean the package is currently release-ready.

For current audited status, use [14-truth-audit-matrix.md](14-truth-audit-matrix.md).

## Current Stable Baseline

`main` is now the shipped `v1.0.5` baseline.

That release already claims:

- repaired Windows overlay font rendering
- Windows OCR proof for exported overlays
- `docs/Clip1.MP4` fixture-backed packaged validation
- hardened packaged workflow/release proof wiring

Any future automation release must preserve those claims before adding new ones.

## Purpose

This package does not replace the repo-wide semver release process.

It adds an automation-specific ship-readiness checklist for the features defined in `docs/automate` so release claims, release notes, and packaged proof stay aligned to the actual implementation.

## Release Scope For This Package

When the feature set introduced here is shipped, release work must cover:

- preservation of the `v1.0.5` release guarantees
- version-source updates governed by the repo release process
- changelog entries using SplitShot-native feature names
- release notes mapped to user outcomes rather than internal implementation jargon
- packaged proof for the visible feature flows defined in this package
- live GitHub release body updates when an existing release entry is being refreshed

## Release-Facing Files And Outputs

When these capabilities ship, the release pass must update:

- `pyproject.toml`
- `src/splitshot/__init__.py`
- `uv.lock`
- `electron/package.json`
- `CHANGELOG.md`
- `artifacts/release-notes.md` generated from the changelog

The release notes must describe shipped capabilities using SplitShot-native names such as:

- `Run Window`
- `Metric Captions`
- `Match Recap`
- `Stage Composite`
- `Performance Library`

## Mandatory Packaged Proof Before Release

Before these capabilities are released, packaged proof must cover:

- the existing `v1.0.5` Windows export-font/OCR proof path
- stage output profile creation and render
- `Run Window` render behavior
- `Metric Captions` render behavior
- `Lead-In Card` and `Brand Mark` render behavior
- `Match Recap` render behavior
- `Stage Composite` render behavior
- retained review-video generation and refresh
- library browse and reopen flows

Each shipped outcome must have one packaged proof owner in [10-acceptance-and-proof.md](10-acceptance-and-proof.md).

## Live Release Update Rule

If a GitHub release object already exists for the shipping version and its body does not match the final feature set, the live release body must be updated.

For this package, a valid live release update means:

- SplitShot-native feature names are used
- shipped user outcomes are described accurately
- packaged proof-backed capabilities are listed
- unsupported or deferred capabilities are not implied

## Release Naming Rules

Release notes must not:

- use competitor product names as shipped feature labels
- imply 1:1 cloning behavior
- claim packaged support for flows that only passed in source mode
- present source-build prerequisites as packaged end-user requirements

## Release Checklist

The release pass for this package must answer:

1. Which `docs/automate` capabilities are shipping in this version?
2. Which existing `v1.0.5` guarantees were re-proven unchanged?
3. Which of the new automation capabilities passed packaged proof?
4. Which capabilities remain partial, deferred, or rejected by design?
5. Does `CHANGELOG.md` use SplitShot-native names?
6. Does the GitHub release body match the packaged-proof reality?

## Acceptance Rule

No capability from this package may be described as released unless:

- the repo release flow is satisfied
- the capability is mapped in the proof matrix
- the packaged proof exists
- the changelog and release notes use the final SplitShot-native naming
