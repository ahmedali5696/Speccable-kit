# Changelog

All notable changes to **Speccable-kit** are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). The version here always matches
`extension.version` in `extension/extension.yml` (the authoritative source).

## [Unreleased]

### Initial open-source release preparation

- **V-02** — `validate-detector.mjs` now preserves the existing line-ending style of
  `tasks.md` when inserting UI Validation Follow-ups, instead of mixing LF with CRLF.
  User-authored content is preserved byte-for-byte; insertion and deduplication are
  unchanged.
- **V-03** — Added an executable-validator regression test for a run carrying both primary
  and advisory findings (overall `FAIL`, advisory-only stays non-blocking, only primary
  findings are materialized into `tasks.md`).
- **V-06** — Documented the PowerShell requirement precisely (which scripts, why, and the
  tested-vs-supported distinction for Windows VS non-Windows `pwsh`).
- **V-05** — Refreshed the repo-local installed snapshot through the native Spec Kit
  install mechanism.
- **V-08 / V-09** — Fixed a documentation typo and tightened hook wording so "mandatory"
  is read as a manifest declaration, not an engine-enforced guarantee.
- Added open-source packaging: `LICENSE` (MIT), `CONTRIBUTING.md`, `SECURITY.md`,
  `CHANGELOG.md`, and a CI workflow (`tests`, native install, clean-room, Windows + Linux).

## [1.0.0]

Initial release of Speccable-kit as a Spec Kit extension.

- Extension-only integration of Impeccable into the native Spec Kit workflow.
- `UI Impact` gate (`before_plan`, authoritative; `after_specify`, eager/optional).
- Impeccable capability + version-range check (`check-compat.ps1`, fail-closed).
- Deterministic validation (`validate-detector.mjs`) surfaced at `after_implement`, with
  `FAIL` findings written (deduplicated) into `tasks.md`.
- Shared layout resolver (`impeccable-layouts.json`) consumed by both the compatibility
  check and the validator.
- Agent-neutral: no provider-specific installation logic, commands, hooks, or branches.
