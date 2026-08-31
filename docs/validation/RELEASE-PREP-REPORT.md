# Speccable-kit — Open-Source Release Preparation Report

**Phase 3 deliverable.** Prepared the already-accepted Speccable-kit implementation for
public open-source distribution without changing its approved architecture.

---

## 1. Executive Verdict

**RELEASE READY** — with the non-blocking verification caveat that non-Windows PowerShell
(`pwsh`) execution and the cross-platform CI jobs are authored but were not executed in this
session (they run on GitHub Actions when the workflow is triggered).

The repository now contains an installable, versioned, tested, documented, license-compliant,
CI-ready, contributor-friendly, agent-neutral Spec Kit extension. All prior acceptance findings
were resolved or documented, and the full contract suite passes (113 tests).

---

## 2. Repository Baseline

- **Extension source of truth:** `extension/` (manifest, 3 commands, 4 scripts).
- **Extension version:** `1.0.0` — kept unchanged (no functional contract change; see §8).
- **Tests:** `tests/test_contract.py` (113 tests) + `tests/run_cleanroom.py` harness.
- **Docs:** `docs/speccable/` (9 documents) + `docs/validation/` (evidence records).
- **Installed snapshot:** `.specify/extensions/speccable/` now in sync with `extension/`
  (V-05 resolved via native install).
- **Git:** deliverable files are untracked on branch `main` (not yet committed/published).

---

## 3. Release-Prep Changes

Additions made to the baseline (extension source and manifest unchanged in behavior):

| Artifact | Purpose |
| --- | --- |
| `LICENSE` (MIT) | license-compliant; matches `extension.yml` `license: MIT` |
| `CHANGELOG.md` | Keep-a-Changelog + SemVer; links version to `extension.yml` |
| `CONTRIBUTING.md` | contributor workflow, boundaries, testing, release steps |
| `SECURITY.md` | honest threat model + private reporting, no invented guarantees |
| `.github/workflows/ci.yml` | Windows (PowerShell 5.1) + Linux (pwsh) verification |
| `tests/` pwsh fallback | `_powershell_cmd()` / cleanroom helper resolve `pwsh` on non-Windows |

---

## 4. V-02 Resolution — tasks.md line-ending preservation (PASS)

`extension/scripts/validate-detector.mjs` `writeTasks()` now detects the file's existing EOL
(`\r\n` vs `\n`) and builds its insertion with that EOL, instead of forcing LF.

- Preserves existing line-ending style: **yes** (verified: CRLF stays CRLF, LF stays LF).
- Preserves user-authored content byte-for-byte: **yes** (verified).
- Deterministic insertion + deduplication: **unchanged**.
- All other validator behavior: **unchanged** (PASS/NOT_RUN never write; only FAIL writes).

Regression tests added in `tests/test_contract.py`:
`test_write_preserves_crlf_line_endings`, `test_write_preserves_lf_line_endings` — both pass.

---

## 5. V-03 Resolution — primary + advisory findings (PASS)

Automated coverage now exercises the **shipped executable validator**
(`validate-detector.mjs`) against a `mixed` fake-detector mode producing one primary and one
advisory finding:

- overall status = **FAIL** (primary drives failure);
- advisory finding stays advisory (non-blocking, `advisoryOnly=false`, primary count = 1);
- **only primary findings** are materialized into `tasks.md` (advisory is not).

Verified by `test_mixed_primary_and_advisory_fail_closes_on_primary` (passes) and confirmed by
the clean-room `detector_modes` evidence. This removes the prior MEDIUM coverage gap.

---

## 6. V-06 Resolution — PowerShell requirement documented (PASS)

`docs/speccable/development.md` (new **Runtime** section) and `docs/speccable/compatibility.md`
now state precisely:

- **Which scripts require PowerShell:** `ui-impact.ps1` (ui-gate Step 1) and
  `check-compat.ps1` (ui-gate Step 3); the validator is Node.js.
- **Why:** they are Spec Kit `{SCRIPT}`-substituted PowerShell helpers.
- **Windows:** bundled Windows PowerShell 5.1 — **tested** (full suite + clean-room here).
- **Non-Windows:** requires PowerShell Core (`pwsh`) on PATH — **supported by design, not yet
  verified by CI as of this writing** (the CI workflow authors this verification; it has not
  yet run). The docs explicitly do not claim non-Windows is tested.

---

## 7. Optional Findings Resolution

- **V-05 (INFO):** repo-local installed snapshot `.specify/extensions/speccable/` refreshed
  through the native `specify extension add` mechanism; now identical to `extension/`. (PASS)
- **V-08 (INFO):** "behaviorable" typo in `docs/speccable/hooks.md` corrected. (PASS)
- **V-09 (INFO):** `docs/speccable/hooks.md` now clarifies "mandatory" is a *manifest
  declaration*, not engine-enforced enforcement — the documented agent-mediated routing.
  (PASS)
- **V-04 (INFO):** left as-is — the redundant parser reimplementation tests were judged
  acceptable and removing them risked coverage; documented as deferred.
- **V-01 (INFO):** left as-is (not naturally release-prep; cosmetic). Deferred.
- **V-07 (INFO):** tilde fences remain non-fences per explicit scope decision. No expansion.

---

## 8. Versioning (PASS — keep 1.0.0)

- **Authoritative source:** `extension.version` in `extension/extension.yml` (`1.0.0`).
- Kept at **1.0.0**: this is still the initial public release; release-prep changes are
  documentation/tests/CI — no functional contract change to the extension.
- **Release/tag version** = extension version, tagged `v<version>` (per CONTRIBUTING).
- **Future:** SemVer — patch = bug fix, minor = compatible addition, major = breaking change;
  manifest, CHANGELOG, and README updated together.
- **No package/publishing registry metadata** is required: the extension is distributed as a
  Git repository and installed via `specify extension add ./extension` (or by identifier once
  published). Node validator uses only built-ins (no `node_modules`).

---

## 9. License (PASS)

- `LICENSE` added (MIT) matching `extension.yml` `license: MIT`. Copyright line uses the
  repository owner. No invented legal entity.

---

## 10. CI (PASS, with run-pending note)

`.github/workflows/ci.yml` (two jobs):
- **Windows:** full contract suite (PowerShell 5.1 + Node + native-install test) + clean-room
  harness.
- **Linux:** installs PowerShell Core (`pwsh`), runs the full contract suite; skips the
  clean-room/native-install that require the Windows-native `specify` binary.

The test harness now resolves `pwsh` on non-Windows so the Linux job is real, not cosmetic.
**Caveat:** these jobs have not been executed in this session; they run on the first CI trigger.

---

## 11. Documentation (PASS)

`README.md` (rewritten: what/why, relationship to Spec Kit & Impeccable, compatibility,
runtime requirements, PowerShell distinction, failure behavior, validation, development, CI,
contributing, license). `docs/speccable/` covers architecture, UI Impact, commands, hooks,
compatibility, failure modes, validation, and development. Wording does not overclaim:
agent-mediated routing is never described as engine-enforced (§9/clarified V-09), and
non-Windows PowerShell is not claimed tested.

## 12. Installation UX (PASS)

Documented path uses the native Spec Kit mechanism only: install Speccable via
`specify extension add ./extension --dev`; install/configure Impeccable separately via its own
installer (never auto-installed); create/initiate the Spec Kit project; select the agent
integration via Spec Kit; the workflow runs via native hooks. No custom installer, no
auto-install.

## 13. Agent-Neutrality Audit (PASS)

No provider-specific commands, hooks, env vars, or behavior branches. Speaker's layouts
(`.agent`, `.agents`, `.claude`) are plain filesystem roots in one shared data file iterated
by a single loop — they are not provider branches. Speccable owns the extension contract; Spec
Kit owns agent integration; Impeccable owns its installation/workflow.

## 14. Spec Kit Boundary Audit (PASS)

No fork/vendor/modification of Spec Kit core, templates, or built-in commands. Ships no
Preset. Uses only the native extension mechanism (`schema_version 1.0`, `provides.commands[]`,
`provides.scripts[]`, `hooks{}`, front-matter `scripts:` substitution).

## 15. Impeccable Boundary Audit (PASS)

No vendoring/forking/copying/reimplementing of Impeccable internals; no writes inside
Impeccable's namespace (`.impeccable/`, `PRODUCT.md`, `DESIGN.md`, surface briefs); no
dependency on `.impeccable/live`, `hook.cache.json`, internal scripts/subagents/manifests/
slugs, or the rule inventory; no auto-install/auto-upgrade. The validator's only `writeFile`
targets the user-specified `tasks.md`.

## 16-18. Test Results / Clean-Room / Cross-Agent (PASS)

- **Full contract suite: 113 tests pass** (`python -m unittest tests.test_contract`).
- **Clean-room evidence harness: exit 0**; fresh native install materializes all 4 scripts +
  3 skills; the full layout matrix (missing / `.agent` / `.agents` / `.claude` /
  unsupported-major / malformed-version / no-detector / preference-order) and detector modes
  (clean/findings/advisory/mixed/malformed/degraded/timeout) all behave correctly.
- **Cross-agent:** `.agent` (Antigravity), `.agents` (Codex), `.claude` (Claude Code) layouts
  all detected and resolved identically by check-compat and the validator (layout-consistency
  proof). No agent-specific coupling introduced.

## 19. Repository Hygiene (PASS)

`.gitignore` excludes reinstallable byproducts (`.specify/extensions/`, materialized
`.zcode/skills/speckit-speccable-*`, `__pycache__/`). Source of truth is `extension/`. Live
docs updated to the current 113-test count; broken Code-of-conduct empty-link in README
corrected to plain text; historical acceptance reports left intact as point-in-time evidence.

## 20. Remaining Limitations

- Non-Windows PowerShell (`pwsh`) execution and the cross-platform CI jobs are authored but
  not yet executed in this session; they are verified when CI runs.
- The real Impeccable detector's optional HTML-parser modules are unavailable in this
  environment, so scans run in a regex fallback surfaced honestly as `DEGRADED=1`.
- Tilde-fence behavior (V-07) is intentionally unchanged (non-fences), documented.
- Repo-local `.impeccable/` hooks in `.zcode/config.json` are disabled; they are Impeccable's
  own configuration, not part of Speccable.

## 21. Deferred Findings

- **V-04 (INFO):** parser reimplementation test cleanup — deferred; current tests directly
  exercise the shipped validator.
- **V-01 (INFO):** granular crash reason in the validator — deferred (cosmetic).
- **Code of Conduct:** none adopted; README notes it is governed by maintainer discretion.
- **Issue/PR templates:** not added; CONTRIBUTING.md documents reporting; defer to maintainer.

## 22. Release Checklist

- [x] Full contract suite passes (113)
- [x] Clean-room install/evidence regenerated
- [x] All acceptance findings resolved or documented
- [x] LICENSE (MIT), CHANGELOG, CONTRIBUTING, SECURITY present
- [x] CI workflow authored (Windows + Linux)
- [x] PowerShell requirement documented with tested-vs-supported distinction
- [x] Agent-neutrality / Spec Kit / Impeccable boundaries audited clean
- [x] Version pinned at 1.0.0 with release/tag guidance
- [ ] Commit and open PR; tag `v1.0.0` on first publish
- [ ] Let CI run; confirm Windows + Linux jobs pass (pending)
- [ ] Enable private vulnerability reporting on GitHub

## 23. Final Release Recommendation

**RELEASE READY.**

No blocking release requirement remains unresolved. The already-approved architecture is
preserved; the implementation is installable, understood, versioned, tested, documented,
reproducible, contributor-friendly, license-compliant, CI-ready, and agent-neutral. The only
outstanding item is CI execution (pending) and final git commit/PR — both are expected steps of
the release action, not blockers to declaring readiness.
