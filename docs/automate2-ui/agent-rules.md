# Agent Rules

These rules govern all implementation work in the Automate2 UI package.

## Scope Rules

1. **Read the spec first.** Every agent must read `spec.md` before touching code.
2. **Follow the naming contract.** Use SplitShot-native labels only.
3. **Preserve the baseline.** Do not break `v1.0.5` features.
4. **Stay in your track.** Do not implement features assigned to another track.
5. **Proof before claim.** Do not mark anything done without proof.

## Code Rules

1. **Follow existing style.** Match the current codebase.
2. **Write tests.** Every feature needs tests.
3. **Update docs.** If you change behavior, update docs.
4. **No forbidden names.** Check `00a-splitshot-naming-contract.md`.
5. **Accessibility.** All interactive elements need aria-labels.

## UI Rules

1. **Layman-friendly labels.** No jargon.
2. **Preview over describe.** Show, don't just tell.
3. **Progress over perfection.** Loading states are required.
4. **Forgiveness.** Undo, reset, cancel always available.
5. **Delight.** Small polish moments are encouraged.

## Communication Rules

1. **Report blockers immediately.**
2. **Ask for clarification.**
3. **Push back on scope creep.**
4. **Update progress daily.**

## Verification Rules

1. **Run tests before claiming done.**
2. **Run targeted tests for your feature.**
3. **Run full suite before release.**
4. **Report results in the required format.**

## Failure Rules

1. **If a test fails, fix it before continuing.**
2. **If a feature is incomplete, mark it partial.**
3. **If a feature is blocked, report the blocker.**
4. **If a feature is rejected, document why.**
