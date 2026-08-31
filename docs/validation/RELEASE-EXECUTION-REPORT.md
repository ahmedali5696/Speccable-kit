# Release Execution Report — v1.0.0

**Status:** `RELEASE READY — PENDING MANUAL PUBLISH`
**Date:** 2026-08-31
**Phase:** Final open-source publication execution (no functional changes)

This report records the execution of the v1.0.0 publication step for the already-approved
Speccable-kit Spec Kit extension. It is the release-phase companion to
`docs/validation/RELEASE-PREP-REPORT.md`, which remains the authoritative release-preparation
record and was not modified.

---

## 1. Release Verdict

`RELEASE READY — PENDING MANUAL PUBLISH`

All local validation passed and the release tree, metadata, and boundary audit are correct.
The remote CI gate **could not be executed** because the GitHub account is locked due to a
billing issue (jobs never started). Per the release rules, a green CI is a hard gate: the
`v1.0.0` tag was **not** created and the PR was **not** merged. The remaining actions are
exactly the ones listed in §7.

---

## 2. Repository State

- **HEAD before:** `b41f9af` (edits) — on `main`, in sync with `origin/main`.
- **HEAD after:** `21da97d` (chore(release): v1.0.0) — on `release/v1.0.0`.
- **git status:** working tree clean of release files; one unrelated pre-existing
  modification remains in the working tree.
- **Unrelated changes detected:** `.zcode/config.json` (modified vs HEAD — ZCode's own hook
  settings, not part of Speccable). It was **left untouched** and **excluded** from the
  release commit. No user change was overwritten.
- **Release commit hash:** `21da97d` (30 files, +4246 lines; no `.zcode`, `.specify`, or
  `__pycache__` paths included).

Branch: `release/v1.0.0` pushed to `origin` (`origin/release/v1.0.0`). `origin/main` remains
at `b41f9af`.

---

## 3. Validation

- **Contract tests:** `python -m unittest tests.test_contract` → **Ran 113 tests, OK.**
- **Clean-room harness:** `python tests/run_cleanroom.py` → **exit 0** (native
  `specify extension add` install, script+skill materialization, hook registration, layout
  matrix, detector behavior all exercised against the shipped `extension/`).
- **Installed snapshot:** `diff -r extension .specify/extensions/speccable` → **no diff**
  (snapshot in sync with source). `extension/` is authoritative; snapshot is a gitignored
  byproduct (`/.specify/extensions/`).
- **Boundary audit:** PASS.
  - Spec Kit: extension-only; no core modification, no template fork, no preset, no
    replacement of native commands.
  - Impeccable: reads only public surfaces; no vendoring, no `.impeccable/` writes, no
    internal API/manifest dependency, no auto-install/upgrade.
  - Agent: no provider-specific commands, hooks, env vars, or install logic. `.agent`,
    `.agents`, `.claude` are the documented public layout dirs in the shared resolver, not
    provider branching.

---

## 4. CI

- **Workflow authored:** yes — `.github/workflows/ci.yml` (jobs: `windows` = PowerShell 5.1
  + Node + `specify` CLI, full suite + clean-room; `linux-ps-core` = pwsh + Node, full
  suite). YAML parses cleanly with both jobs present.
- **Local equivalent execution:** the Windows job is equivalent to what was run locally on
  this host — full suite (113 OK) and clean-room (exit 0). The Linux pwsh job was not run
  locally (Windows host); its tests use the conservative `pwsh` fallback so they are
  designed to run there.
- **Actual remote CI result:** triggered on the PR as run
  `33355226548`, but **both jobs failed in ~4s without starting**:
  > "The job was not started because your account is locked due to a billing issue."

  This is an account/infrastructure billing lock, **not** a workflow or code defect (no step
  logs exist; jobs never started).

**CI gate conclusion: NOT PASSED (CI NOT VERIFIED).** A green CI is required before tagging;
the billing lock is an environment blocker outside this release. Therefore `v1.0.0` was not
tagged and the PR was not merged.

---

## 5. Release Metadata

- **Version:** `1.0.0` (authoritative `extension.version` in `extension/extension.yml`);
  consistent with `CHANGELOG.md`, `README.md`, `CONTRIBUTING.md` (tag `v<version>`).
- **License:** MIT — `LICENSE` (Copyright (c) 2026 Ahmed Ali) matches
  `extension.license: MIT`.
- **Changelog / contributor / security docs:** `CHANGELOG.md` (Keep a Changelog + SemVer),
  `CONTRIBUTING.md`, `SECURITY.md` (threat model, no invented guarantees).
- **Release tree staged & committed (30 files):**
  `extension/`, `tests/`, `docs/` (+`docs/validation/`), `.github/`, `README.md`, `LICENSE`,
  `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `.gitignore`. No generated artifacts
  (install snapshot, `__pycache__`, temp projects) are included.
- **Registry:** not published to npm/PyPI/any registry. Distribution is the native Spec Kit
  mechanism (`specify extension add <extension>`). No registry metadata created.

---

## 6. Git Release

- **Commit:** `21da97d chore(release): v1.0.0` on `release/v1.0.0`;
  pushed to `origin/release/v1.0.0`.
- **PR:** opened — https://github.com/ahmedali5696/Speccable-kit/pull/1 (`release/v1.0.0` →
  `main`). State: **OPEN**, mergeable. **Not merged** (CI gate unmet; no merge authorization).
- **Tag:** **NOT created** (`git tag --list` empty). `v1.0.0` deliberately not made because
  the CI gate is not satisfied.
- **Tag pushed:** not applicable (no tag).
- **PR created:** yes.

---

## 7. Remaining Manual Actions

1. Resolve the GitHub **account billing lock** (`Settings > Billing`, or contact GitHub
   support) so Actions can run.
2. Trigger/confirm the CI run on **PR #1** (`windows` and `linux-ps-core` jobs) reaches **PASS**.
3. Merge **PR #1** into `main` (or land the equivalent), after CI is green.
4. Create and push the tag **after** CI passes:
   ```
   git tag v1.0.0
   git push origin v1.0.0
   ```
5. Update the GitHub Release notes from the `[Unreleased]`/`[1.0.0]` entries in
   `CHANGELOG.md`.

No functional or release-tree changes are required — the tree is locally verified
release-ready.

---

## 8. Post-Release Notes

Non-blocking observations, not silently fixed:

- The `.zcode/config.json` workspace modification (ZCode host hook settings) is a local/CI
  concern unrelated to Speccable and was intentionally not staged; decide whether to commit
  it separately or keep it local.
- The Linux `pwsh` CI job is authored and designed to exercise the `.ps1` scripts on a
  non-Windows host, but has **not yet been verified** by an actual green run; until the
  billing lock is cleared, non-Windows `pwsh` remains *supported-by-design, not tested*.
- Windows PowerShell 5.1 and the `specify` CLI path are covered by the local Windows run
  (113 tests + clean-room), which is equivalent to the `windows` CI job.
