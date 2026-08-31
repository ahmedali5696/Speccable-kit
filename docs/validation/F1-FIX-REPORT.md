# Speccable-kit — F1 Targeted Fix Report

**Verdict: FIXED**

This report documents the F1 (HIGH) fix and its evidence-based verification, per the
F1-targeted-fix mission. Phase 0 evidence-first discovery showed that the F1 layout fix is
**already implemented and shipped in the current working tree** (introduced during the
prior Phase 2 targeted-fix pass; see `docs/validation/ACCEPTANCE-REPORT.md`). This report
does not stop at that claim — it independently re-proves, from a fresh native install and a
real Claude Code-style Impeccable installation, that the Claude layout is detected and
successfully participates in the `direct` UI workflow without blocking.

---

## 1. Verdict

**FIXED.** A real Claude-code Impeccable installation at `.claude/skills/impeccable/` is
detected (`IMPECCABLE=present`, `SUPPORTED=supported`, `DETECTOR=present`), and a `direct`
UI-impact feature routes to the design-aware workflow (`ROUTE=design`) instead of being
incorrectly BLOCKed. Capability detection and detector invocation agree via one shared
layout file.

## 2. Root cause

The original F1 defect: the compatibility/capability scan enumerated only two hardcoded
Impeccable install roots (`.agent/skills/impeccable`, `.agents/skills/impeccable`), so a
real Claude Code install at `.claude/skills/impeccable/` was reported `IMPECCABLE=missing /
SUPPORTED=missing`, and the gate BLOCKed a `direct` feature. This is now fixed in-tree.

## 3. Files modified

Per Phase 0 ("stop and report the discrepancy before changing code"), the fix was found
**already present**; no further source changes were required. The files that constitute the
shipped fix (already in the working tree) are:

- `extension/scripts/impeccable-layouts.json` — the single authoritative layout definition,
  now listing `.claude/skills/impeccable` as the third root.
- `extension/scripts/check-compat.ps1` — capability detection reads the shared layouts file
  (no hardcoded two-root list).
- `extension/scripts/validate-detector.mjs` — detector invocation reads the same shared file.
- `extension/extension.yml` — registers the shared `impeccable-layouts` data file under
  `provides.scripts[]` so it materializes at install.
- `extension/commands/speckit.speccable.ui-validate.md` — documents the `.claude` layout in
  the shared discovery order.
- `docs/speccable/compatibility.md`, `docs/speccable/validation.md` — document the three
  supported layouts and the deterministic preference order.
- `tests/test_contract.py` — the contract suite, extended with Claude-layout coverage.

**No Spec Kit core, no templates, no Impeccable source, and no Impeccable internals were
touched.** Git state is unchanged from baseline (`.zcode/config.json` modification predates
this session).

## 4. Exact implementation change

A single authoritative data file defines layout discovery once:

```json
{ "order": [".agent/skills/impeccable", ".agents/skills/impeccable", ".claude/skills/impeccable"],
  "detectorEntryPoint": "scripts/detect.mjs", "skillFile": "SKILL.md" }
```

Both `check-compat.ps1` (capability) and `validate-detector.mjs` (detector invocation) read
**this same file** and iterate its `order` with first-match-wins. Version authority remains the
Impeccable skill's `SKILL.md` front-matter `version:` line (never the npm CLI version).

## 5. Supported layouts

1. `.agent/skills/impeccable/`
2. `.agents/skills/impeccable/`
3. `.claude/skills/impeccable/`

These are exactly the documented install layouts confirmed from Impeccable's own
documentation in this environment (`docs/Impeccable-README.md`: Claude Code →
`cp -r dist/claude-code/.claude your-project/`; `${CLAUDE_PROJECT_DIR}/.claude/skills/
impeccable/scripts/hook.mjs`; `--providers=claude`). No additional layouts were invented;
no arbitrary/recursive filesystem discovery was introduced.

## 6. Resolution preference order

Deterministic first-match-wins: **`.agent` → `.agents` → `.claude`** (`.agent` preferred).
Preserved from the original architecture; verified for every single- and multi-layout
combination (`TestLayoutConsistency`, clean-room matrix).

## 7. Tests added/changed

`tests/test_contract.py` (`110` tests, all passing):

- `TestCheckCompatScript` — Claude-only, `.agent`/`.agents`-only, and preference tests
  (`.agent` > `.agents`, `.agent` > `.claude`, `.agents` > `.claude`, all-three-prefers-`.agent`),
  plus `SUPPORTED` range/malformed/unsupported tests exercised through the `.claude` layout.
- `TestValidateDetectorExecutable` — validator resolves the `.claude` layout and detector path;
  `NOT_RUN` (never `PASS`) for missing Impeccable and for a missing detector script; detector
  mode matrix (clean/findings/advisory/malformed/non-array/empty/crash/timeout/degraded);
  tasks.md write/dedup/no-mutation.
- `TestLayoutConsistency` — proves `check-compat.ps1`'s `LAYOUT` equals the validator's
  selected layout for every single- and multi-layout combination (`.claude` included).
- `TestProseContract` — delegation, `NOT_RUN ≠ PASS`, no silent `none`, and layout coverage.

`tests/run_cleanroom.py` installs into fresh temp projects via the real native CLI and
records machine-parseable evidence to `docs/validation/cleanroom-evidence.json`.

## 8. Full test result

```
Ran 110 tests ... OK
```

Re-run on the current working tree immediately prior to this report. Clean-room evidence
(`docs/validation/cleanroom-evidence.json`), regenerated in this session, records the layout
matrix (missing / `.agent` / `.agents` / `.claude`+supported / `.claude`+5.0.0 /
`.claude`+malformed / `.claude`+no-detector / `.agent`-preferred-over-`.claude`) and the
detector-mode matrix, all through the **installed** extension path.

## 9. Claude-only real-world validation result

Clean-room proof in a fresh Spec Kit project (extension installed via `specify extension
add ./extension --dev`), a **real** Impeccable 4.1.1 skill (real `SKILL.md` + real
`scripts/detect.mjs`) placed **only** at `.claude/skills/impeccable/`, no `.agent`/`.agents`:

- Capability detection:
  ```
  IMPECCABLE=present|VERSION=4.1.1|DETECTOR=present|SUPPORTED=supported|LAYOUT=.claude/skills/impeccable
  ```
- Real validator (through the installed path) resolved the Claude detector and ran the real
  detector against a real HTML target:
  ```json
  {"status":"FAIL","reason":"findings","primaryFindingsCount":1,
   "degraded":1,"DEGRADED":1,
   "degradedNotice":"impeccable detect: DEGRADED - HTML parser modules unavailable ...",
   "layout":".claude/skills/impeccable",
   "detectorPath":"...\\.claude\\skills\\impeccable\\scripts\\detect.mjs"}
  ```
  The Claude-installed detector participated fully in deterministic validation (detected a
  real finding, `FAIL`, `DEGRADED=1` surfaced — not a spurious `NOT_RUN` from an old
  `.agents` hardcode, and not a masked clean `PASS`).
- `direct` routing: `UI_IMPACT=direct` (preserved) + `IMPECCABLE=present/SUPPORTED=supported`
  + design source present → **`ROUTE=design`**, not BLOCK.

## 10. `.agent` / `.agents` regression results

- `.agent`-only (repo root, real 4.1.1):
  ```
  IMPECCABLE=present|VERSION=4.1.1|DETECTOR=present|SUPPORTED=supported|LAYOUT=.agent/skills/impeccable
  ```
- `.agents`-only (clean-room): `present / supported / LAYOUT=.agents/skills/impeccable`;
  validator `PASS`, same layout.
- Preference preserved: when both `.agent` and `.claude` exist, `.agent` is selected.

## 11. Native Spec Kit installation result

Fresh project: `specify extension add D:\Speccable-kit\extension --dev` → exit 0;
`.specify/extensions/speccable/scripts/` contains all four artifacts
(`check-compat.ps1`, `ui-impact.ps1`, `validate-detector.mjs`, `impeccable-layouts.json`);
the three skills materialize; hooks register condition-free (`condition: null`):
`after_specify` optional, `before_plan` mandatory (`ui-gate`), `after_implement` mandatory
(`ui-validate`). The installed copy is in sync with source.

## 12. Boundary audit result

Scan of `extension/` found no prohibited coupling: no `.impeccable/` dependency (the only
references are negative guards "never writes inside"), no `live/`, no `hook.cache.json`, no
internal provider manifests, no provider-specific `if Claude/Cursor/...` branches, no
auto-install/auto-upgrade of Impeccable, no vendored Impeccable files, and no recursive
filesystem discovery (both scripts iterate the fixed layout list from the shared JSON).
Impeccable filesystem knowledge is limited to the verified public layouts and the already
approved public surfaces (`SKILL.md`, `scripts/detect.mjs`).

## 13. Architectural invariant result

- No replacement of the extension architecture; no Preset; no Spec Kit core/template change.
- Impeccable not vendored/modified; version authority stays the skill `SKILL.md` front-matter.
- No Speccable-owned design artifact; no provider-specific workflow logic introduced
  (the three roots are plain paths iterated by one shared loop).
- Same resolution logic used consistently by `check-compat.ps1` and `ui-validate`
  (validated by `TestLayoutConsistency` and the clean-room `LAYOUT` agreement).
- Fail-closed behavior intact: missing → `missing`; malformed/unsupported → `unsupported`
  (never silently `supported`); detector unavailable → `NOT_RUN` (never `PASS`).

## 14. Remaining F1-related limitation

- The repo workspace's own `.specify/extensions/speccable/` holds a **stale installed
  snapshot** (predates the F1/F2 work; lacks `validate-detector.mjs` and
  `impeccable-layouts.json`). This is an environment artifact of the repo copy, not a defect
  in the shipped extension or the F1 fix; a fresh native install (as documented) materializes
  the current artifacts. Users re-sync with `specify extension add ./extension --dev --force`.
- The real Impeccable detector's optional HTML-parser modules are unavailable in this
  environment, so real scans run in a regex fallback and are correctly surfaced as
  `DEGRADED=1` rather than a false clean `PASS`. This is orthogonal to F1 (F4 in the prior
  report) and is not an F1 limitation.

**Conclusion:** A real Claude Code-style Impeccable installation at `.claude/skills/
impeccable/` is detected and successfully participates in the `direct` UI workflow. F1 is
**FIXED**, with evidence regenerated from fresh native installs and the real detector, not
merely from passing tests.
