# Track 06: Proof, Regression, And Release

## Goal

Define the proof and closure path for the UI overhaul.

## Required Proof Layers

- `v1.0.5` baseline-preservation proof
- targeted UI suites
- PiP performance contract
- browser E2E
- packaged UI proof
- release wording check if shipping

## Required Targeted Suites

- workspace UI contracts
- output-profile UI contracts
- library UI contracts
- PiP performance contracts
- Stage Composite UI contracts

## Required Broader Proof

- browser E2E for Single Video, Multi Video, and Performance Library
- packaged proof for one stage flow and one workspace/composite flow
- packaged PiP playback smoothness proof

## Regression Rules

- protect the released Windows export-font and OCR-proof path
- protect packaged/test workflow use of `docs/Clip1.MP4`
- protect legacy single-stage behavior
- protect existing `/api/project/*` semantics
- protect existing export behavior
- protect previously proven packaged launch and interaction flows

## Release Rules

- SplitShot-native naming only
- no release claim without packaged proof
- changelog and release notes must match shipped UI outcomes
