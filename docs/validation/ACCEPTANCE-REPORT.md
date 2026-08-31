# Speccable-kit — Phase 2 Targeted Fix & Re-Validation: Acceptance Report

**Verdict: ACCEPTED**

This report re-validates Speccable-kit after the Phase 2 targeted fix for findings **F1**
(Impeccable's real Claude Code installation layout was not detected) and **F2**
(deterministic validation was expressed as agent-facing prose rather than executable logic).
It follows the Phase 2 acceptance contract (§1–§24 of the mission), preserving every approved
architectural invariant, and reports only what the evidence establishes. Evidence beats
assumptions; executable behavior beats prose; clean-room reproduction beats claims.

All evidence was regenerated in this session from fresh isolated temp projects (via the real
native CLI) and against the real Impeccable 4.1.1 installation. Machine-parseable evidence:
[`cleanroom-evidence.json`](./cleanroom-evidence.json).

---

## 1. Executive summary

| Item | Result |
| --- | --- |
| F1 — `.claude/skills/impeccable` detected | **Fixed & proven** |
| F1 — capability detection == detector invocation (never disagree) | **Proven** |
| F2 — deterministic validation executable, not prose | **Proven** |
| F2 — `PASS` / `FAIL` / `NOT_RUN` / `DEGRADED` contract | **Proven** |
| Tests exercise the real implementation (not a parser copy) | **Proven** |
| All 110 contract tests pass | **Yes** |
| All clean-room scenarios (layout matrix + detector modes + install) | **Pass** |
| Clean-room Claude validation (Section 17) | **Pass** |
| Architectural invariants intact | **Yes** |
| Verdict | **ACCEPTED** |

---

## 2. Repository & baseline discovery

Read at the start of this validation pass:

- `docs/Spec kit-README.md` — Spec Kit 1.0.1 extension model (`schema_version: "1.0"`,
  `provides.commands[]`, `provides.scripts[]`, `hooks{}`, front-matter `scripts:` substitution,
  install-time path rewriting).
- `docs/Impeccable-README.md` + Impeccable's own `hook-admin.mjs` — confirmed the three
  documented installation layouts below (authoritative, not assumed).
- Phase 1 Architecture & Integration Contract and Phase 1 Open Questions Resolution —
  treated as immutable; only the two targeted findings were addressed.

Working tree at start: `main` branch, prior work present under `extension/`, `tests/`,
`docs/speccable/`, `README.md`, `.gitignore` (all untracked), plus a modified
`.zcode/config.json`. **No `VALIDATION-REPORT.md` exists in this repository** — it was named
in the mission's baseline list but is not present on disk; that omission is documented here
and does not block re-validation, which was executed from source, tests, and clean-room runs.

---

## 3. F1 — Claude Code layout detection (the fix)

**Problem (from the earlier NOT ACCEPTED):** Impeccable's real Claude Code layout
(`.claude/skills/impeccable/`) was not recognized; a real install was reported
`IMPECCABLE=missing / SUPPORTED=missing`, which made the gate incorrectly **BLOCK** a
`direct` feature.

**Root cause:** the layout list was hardcoded to two roots (`.agent`, `.agents`) in the
compatibility script, omitting `.claude`.

**Fix:** introduced a single authoritative data file
`extension/scripts/impeccable-layouts.json`:

```json
{ "order": [".agent/skills/impeccable", ".agents/skills/impeccable", ".claude/skills/impeccable"],
  "detectorEntryPoint": "scripts/detect.mjs", "skillFile": "SKILL.md" }
```

Both `check-compat.ps1` (capability) and `validate-detector.mjs` (detector invocation) read
**this same file**, so they can never disagree about where Impeccable lives. The documented
deterministic preference order (`.agent` → `.agents` → `.claude`, first-match-wins) is listed
in the file and is preserved. No provider-specific branch (`if Claude` / `if Cursor` /
`if Codex` / `if Gemini`) was introduced — the roots are plain filesystem paths iterated by
one shared loop. The three roots are exactly the documented layouts; no additional layouts
were invented and none was inferred. **Fail-closed** behavior is retained: an unreadable or
malformed version is reported `unsupported`, and a missing capability is `missing`. Impeccable
is never auto-installed, auto-upgraded, or modified.

**Clean-room proof (Section 17 / Scenario B):** a fresh temp Spec Kit project with a real
`.claude/skills/impeccable/SKILL.md` (version 4.1.1) + `scripts/detect.mjs`, extension
installed via the real `specify extension add`:

```
IMPECCABLE=present|VERSION=4.1.1|DETECTOR=present|SUPPORTED=supported|LAYOUT=.claude/skills/impeccable
```

A `direct` UI-impact feature in that project is preserved, capability is verified as
`SUPPORTED=supported`, and a design source of truth exists → **`ROUTE=design`, NOT blocked**.

---

## 4. F1 layout matrix (checks + validator agree)

From [`cleanroom-evidence.json`](./cleanroom-evidence.json) (each case is a fresh install):

| Case | `check-compat` (IMPECCABLE/SUPPORTED/LAYOUT) | Validator |
| --- | --- | --- |
| no Impeccable | missing / missing / none | `NOT_RUN` (exec-unavailable), layout none |
| `.agent` + 4.1.1 | present / supported / `.agent` | `PASS`, layout `.agent` |
| `.agents` + 4.1.1 | present / supported / `.agents` | `PASS`, layout `.agents` |
| `.claude` + 4.1.1 | present / supported / `.claude` | `PASS`, layout `.claude` |
| `.claude` + 5.0.0 | present / **unsupported** / `.claude` | `PASS` (detector ran clean) |
| `.claude` + malformed version | present / **unsupported** / `.claude` | `PASS` (detector ran clean) |
| `.claude`, no detector script | present / supported / `.claude` | `NOT_RUN` (exec-unavailable) — **not PASS** |
| `.agent` + `.claude` both | present / supported / **`.agent`** | `PASS`, layout `.agent` (preference preserved) |

The two unsupported-version rows deserve a note: `check-compat` reports `SUPPORTED=unsupported`
(used by the gate to **BLOCK**), while the validator returns `PASS` because the installed
detector itself ran clean. These are intentionally separate responsibilities (§12): the gate
enforces the supported-range verdict; the validator only reports deterministic detector output.
**`check-compat.ps1` and the validator agree on `LAYOUT` in every case** — the consistency
guarantee.

---

## 5. F2 — executable deterministic validation (the fix)

**Problem (from the earlier NOT ACCEPTED):** deterministic validation was specified primarily
as prose in `ui-validate.md` (agent-facing instructions) rather than executable logic.

**Fix:**

- New executable validator `extension/scripts/validate-detector.mjs` (Node.js, using
  `node:child_process` `execFile`). It is the **single source of truth** for deterministic
  validation: layout resolution (shared file), detector execution with stdout/stderr/exit
  capture, a configurable timeout, tolerant JSON parsing, `PASS`/`FAIL`/`NOT_RUN`
  classification, `DEGRADED` detection, and findings → `tasks.md` insertion with dedup.
- `extension/commands/speckit.speccable.ui-validate.md` was rewritten to **delegate** to the
  validator and present its result. It does **not** contain a second implementation of detector
  parsing — single source of truth (per §12 and §15).
- `extension.yml` adds `validate-detector` and `impeccable-layouts` to `provides.scripts[]`,
  so both are copied into `.specify/extensions/speccable/scripts/` at install.

The command may remain a `.md` skill (that is the extension model), but all deterministic
behavior is executable. No package-manager dependency was introduced; the validator uses only
Node's built-ins.

---

## 6. F2 status contract (verified by real execution)

`validate-detector.mjs` returns exit `0` for every deterministic outcome (a valid result —
`PASS`, `FAIL`, or `NOT_RUN` — means the run happened) and exit `2` only for internal failure.
**`NOT_RUN` never equals `PASS`.** Verified outcomes from `cleanroom-evidence.json`:

| Detector mode | Status | Reason | Notes |
| --- | --- | --- | --- |
| clean | `PASS` | clean | exit 0 |
| findings | `FAIL` | findings | 1 primary finding |
| advisory-only | `PASS` | clean | `advisoryOnly=true`, 0 primary (non-blocking) |
| malformed output | `NOT_RUN` | malformed-output | not `PASS` |
| non-array / empty | `NOT_RUN` | non-array / empty-output | not `PASS` |
| timeout | `NOT_RUN` | timeout | not `PASS` |
| degraded | `PASS` + `DEGRADED=1` | clean | notice surfaced, not a false clean `PASS` |

**Parsing is tolerant:** unknown fields/values (e.g. a new `severity`/`category`, a new
`antipattern`) are ignored/tolerated; missing optional fields are preserved; non-object array
elements are skipped without crashing; the parser does not hardcode a severity vocabulary or
rule inventory. Only structurally unusable output (not a JSON array of objects) is `NOT_RUN`.

**Findings → tasks.md:** on `FAIL`, findings are appended under the stable heading
`## UI Validation Follow-ups` (created at EOF if absent, appended within if present), each
with a **stable signature** (`antipattern|file|line`) used for dedup. `PASS` / `NOT_RUN` /
failed runs never write. Verified: one finding → one task; a repeated FAIL run adds **no
duplicate**; the user-authored task outside the section is untouched; a crashed/failed run
cannot corrupt the file.

---

## 7. DEGRADED exposure (Section 18 — non-degraded attempt)

The mission required attempting a non-degraded detector validation and, if unavailable,
distinguishing infrastructure from correctness.

**Attempt:** ran the **real** Impeccable 4.1.1 detector (`.agent/skills/impeccable/scripts/
detect.mjs`) against a real HTML target through the **real** validator.

- The detector is still **infrastructure-degraded**: its optional HTML parser modules
  (`htmlparser2`, `css-select`, `css-tree`, `domutils`) are unavailable, and it prints an
  explicit `DEGRADED` notice on stderr ("findings are an undercount, not a clean bill of
  health").
- **It still produced a valid, parseable JSON result** — this is a correctness-level success,
  not a failure of the validator.

Real outputs through the real validator:

```text
# real HTML with a finding (Inter font):
{"status":"FAIL","reason":"findings","primaryFindingsCount":1,
 "degraded":1,"DEGRADED":1,
 "degradedNotice":"impeccable detect: DEGRADED - HTML parser modules unavailable ...",
 "layout":".agent/skills/impeccable", ...}   exit 0

# real HTML without a finding (Georgia font):
{"status":"PASS","reason":"clean","primaryFindingsCount":0,
 "degraded":1,"DEGRADED":1,"degradedNotice":"... DEGRADED ...", ...}   exit 0
```

**Conclusion on Section 18:** the detector is **infrastructure-degraded** (missing parser node
modules — an environment limitation, not a Speccable-kit correctness defect). The deterministic
validator handles it correctly: on the real `FAIL`-schema path it classifies `FAIL` and exposes
`DEGRADED=1` with the verbatim notice; on a clean real result it reports `PASS` but **still**
flags `DEGRADED=1` so a degraded undercount is never presented as a fully clean unconditional
`PASS`. No clean result was fabricated. The `DEGRADED` state is explicit in both the JSON
(`degraded`/`DEGRADED`) and the report line, exactly as required.

---

## 8. Section 12 — command responsibilities (single source of truth)

- **ui-gate**: reads UI Impact, verifies capability (delegates to `check-compat.ps1`) and the
  design source for `direct`, and routes `native`/`design` (or BLOCKs). It may invoke the
  compatibility helper — it does.
- **ui-design**: orchestrates only; never reimplements Impeccable internals.
- **ui-validate**: reads UI Impact (via `{SCRIPT}` = `ui-impact.ps1`), then **delegates** to
  `validate-detector.mjs` and presents the result. It does **not** contain a second
  implementation of detector parsing/classification/tasks-writing.

The `ui-validate.md` command text is explicit on this, and the prose-contract test
`test_validate_failed_run_cannot_corrupt_tasks` now asserts the delegation ("single source of
truth", "does **not** reimplement") rather than a duplicated parser.

---

## 9. Section 13 — UI Impact contract (unchanged)

The contract is unchanged and re-verified:

- `none` / `direct` valid human values → **preserved verbatim** (never overwritten).
- missing → `unclassified`; empty/duplicate/unknown → `invalid`; both are classified, never
  silently coerced to `none`.
- classification failure / ambiguity → **BLOCK** (never default to `none`).
- fenced code blocks in `spec.md` are excluded from UI Impact metadata (tested).
- `direct` + Impeccable missing → BLOCK + remediation (no auto-install); `direct` + design
  source missing → BLOCK.

Clean-room evidence: `UI_IMPACT=direct|MATCH=preserved` read correctly from a real spec.

---

## 10. Section 14 — hard constraints / invariants (audited clean)

Automated + manual audit of the shipped artifacts (`extension/`) confirms:

- **No** Spec Kit core/template/command modification or fork; no `provides.presets`, no
  template files in `extension/`.
- **No** vendoring/forking/modifying/copying of Impeccable; no dependency on Impeccable
  internals (no `hook.cache.json`, no `.impeccable/live`, no internal scripts/subagents,
  no detector-rule inventory, no provider hook manifests).
- **No** writes inside `.impeccable/` or any Speccable-owned design artifact. The validator's
  only `writeFile` targets the user-specified `--tasks` path (`tasks.md`).
- **No** provider-specific workflow logic (`if Claude/Cursor/Codex/Gemini` absent).
- **No** auto-install / auto-upgrade of Impeccable anywhere in `extension/`.
- **No** modification of `/speckit-converge` (referenced only as a "never modify" guard).
- **No** speculative features, no unrelated refactoring; changes are confined to the two
  targeted findings, their executable support, and documentation.

---

## 11. Section 15 — tests exercise the real implementation

The test suite does **not** test a reimplementation:

- `TestValidateDetectorExecutable` **executes** the shipped `validate-detector.mjs` against a
  scratch fake detector (a self-contained `.mjs` with deterministic modes) and verifies through
  the real artifact: parsing (clean/primary/advisory/unknown/missing-optional/malformed/
  non-array/empty/non-object/crash), execution (exit code, timeout via `Atomics.wait`),
  status (`PASS`/`FAIL`/`NOT_RUN`), `DEGRADED`, layout resolution through the validator,
  `NOT_RUN` for missing Impeccable and for a missing detector script, and tasks.md
  write/dedup/no-mutation.
- `TestLayoutConsistency` proves `check-compat.ps1`'s `LAYOUT` equals the validator's layout
  for every single- and multi-layout combination.
- `test_native_install_validation` runs real `specify extension add --dev` and asserts the
  skills, scripts, and hook registry materialize.
- `TestProseContract` reads the shipped command files and asserts the delegation-based
  behavioral contract (no silent `none`, `NOT_RUN ≠ PASS`, delegation, dedup, boundaries).
- `tests/run_cleanroom.py` installs into fresh temp projects via the native CLI and records
  machine-readable evidence to `docs/validation/cleanroom-evidence.json`.

**Full suite: 110 tests, all passing** (`python -m unittest tests.test_contract`).

---

## 12. Section 16/17 — clean-room real-world validation

- **Native install (clean room):** `specify extension add D:\Speccable-kit\extension --dev`
  in a fresh temp project → exit 0; `.specify/extensions/speccable/scripts/` contains all four
  scripts; the three skills materialize under `.zcode/skills/`; hooks register condition-free.
- **Claude clean-room (Scenario B / Section 17):** fresh project with real
  `.claude/skills/impeccable` (4.1.1) + detector, installed via native CLI →
  `IMPECCABLE=present, SUPPORTED=supported, DETECTOR=present, LAYOUT=.claude/...`, validator
  resolves the detector through the installed path, and a `direct` feature routes `design`
  (not blocked). The validator invoked through the **installed** path
  (`.specify/extensions/speccable/scripts/validate-detector.mjs`) returns correct results —
  not a mocked resolver.
- **Layout matrix + detector modes:** all cases in §4 and §6 pass.

---

## 13. Section 21 — acceptance criteria

| Criterion | Status |
| --- | --- |
| Claude layout detected (real `.claude` project) | ✅ Pass |
| F2 deterministic validation is executable | ✅ Pass |
| All tests pass (110) | ✅ Pass |
| All clean-room scenarios pass | ✅ Pass |
| Architectural invariants intact | ✅ Pass |
| `NOT_RUN` ≠ `PASS` | ✅ Pass |
| missing ≠ `none`; invalid ≠ `none`; ambiguous (unclassified/invalid) ≠ `none` | ✅ Pass |
| Impeccable owns design artifacts (none created by Speccable-kit) | ✅ Pass |
| Reproducible by a fresh user | ✅ Pass (clean-room harness + docs) |

---

## 14. Section 22 — stop conditions (none triggered)

- Claude layout still fails? **No** — proven in §3/§4.
- Validator remains prose-defined? **No** — it is executable (§5).
- Tests only test a reimplementation? **No** — they execute the shipped artifact (§11).
- Deterministic validation can't execute? **No** — it runs on Node's built-ins (§5).
- Architectural invariant violated? **No** (§10).
- Provider-specific dependency introduced? **No**.
- Impeccable modified/vendorized? **No**.
- Spec Kit core modified? **No**.
- `NOT_RUN` can become `PASS`? **No** — the code paths are distinct and tested.
- Findings can corrupt tasks.md? **No** — dedup + safe insertion + no-write on non-FAIL (§6).
- Clean-room install fails? **No**.

No blocking defect is downgraded or hidden.

---

## 15. Repro steps for a fresh user

```bash
# 1) In a Spec Kit project (>= 1.0.1, has .specify/)
specify extension add ./extension --dev

# 2) Run the full contract suite from the repo
python -m unittest tests.test_contract

# 3) Regenerate clean-room evidence (installs into fresh temp projects)
python tests/run_cleanroom.py          # writes docs/validation/cleanroom-evidence.json
```

Re-sync an installed copy after editing `extension/`:
`specify extension add ./extension --dev --force`.

---

## 16. Acceptance verdict

**ACCEPTED.**

Both Phase 2 findings are resolved with evidence:

- **F1 (HIGH)** — fixed and proven against a real `.claude/skills/impeccable` install in a
  clean room: capability detection and detector invocation agree via one shared layout file,
  and a `direct` feature no longer blocks.
- **F2 (MEDIUM)** — fixed: deterministic validation is executable logic
  (`validate-detector.mjs`) with a correct `PASS`/`FAIL`/`NOT_RUN`/`DEGRADED` contract,
  tolerant parsing, exit-code contract, and safe, deduplicated findings → `tasks.md`; the
  command delegates instead of reimplementing.

No approved architectural invariant was changed, no Spec Kit or Impeccable boundary was
crossed, and the whole system re-validates green through the real native installation path and
against the real Impeccable detector. The one honest limitation surfaced here is that the real
detector's optional HTML-parser modules are unavailable in this environment, so scans run in a
regex fallback mode — but Speccable-kit surfaces that as `DEGRADED=1` rather than hiding it,
which is exactly the required behavior.
