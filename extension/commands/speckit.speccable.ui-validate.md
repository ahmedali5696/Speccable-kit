---
name: "speckit-speccable-ui-validate"
description: "Invoke the executable deterministic validator (validate-detector.mjs) for a UI-impacting feature, present its status (NOT_RUN / PASS / FAIL — NOT_RUN never equals PASS, with DEGRADED exposure) and surface actionable findings into tasks.md. The command only delegates and presents; the executable validator is the single source of truth for deterministic validation. Normally triggered after_implement; also runnable manually."
compatibility: "Requires spec-kit project structure with .specify/ directory and a Node.js runtime (the same runtime the Impeccable detector requires)."
metadata:
  author: "speccable-kit"
  source: "commands/speckit.speccable.ui-validate.md"
scripts:
  ps: scripts/ui-impact.ps1 -SpecFile $SPEC_FILE
---

## Purpose

`ui-validate` runs the **executable** `validate-detector.mjs` (a provided Speccable-kit script) and presents its result. It does **not** reimplement detector parsing, classification, or `tasks.md` insertion — all deterministic validation logic lives in the validator so it is executable and independently testable, and there is exactly one source of truth. It is deliberately distinct from agent-judgment layers (Impeccable `critique` / `audit` are design/UX judgment and are never represented as equivalent to deterministic detector output).

## Context

- `$SPEC_FILE` — absolute path to `spec.md`.
- `$TASKS_FILE` — absolute path to `tasks.md` (resolved like core commands do; under the feature directory, e.g. `tasks.md`). Passed to the validator so it can append only deduplicated actionable findings — **never modify `/speckit-converge`** and never replace the convergence engine.
- `$PROJECT_ROOT` — the Spec Kit project root (directory above `.specify/`). Resolved like the core commands do.
- `$TARGET` — the implemented UI surface to validate: a directory, HTML file, or route that the detector should scan.

## Step 1 — Determine whether validation applies

Read `UI Impact` from `$SPEC_FILE` using the impact reader (same marker as the gate):

{SCRIPT}

Parse the single output line for `UI_IMPACT=`:

- If `UI_IMPACT=none` (or the marker is unclassified/missing with no UI surface): validation does not apply. Report `STATUS=NOT_RUN` with reason `no-ui` and stop. **Do not run the validator or the detector.**
- If `UI_IMPACT=direct`: proceed to Step 2.

## Step 2 — Delegate to the executable validator

Invoke the provided deterministic validator, which performs all remaining work (layout resolution, detector execution, stdout/stderr/exit capture, tolerant JSON parsing, PASS/FAIL/NOT_RUN classification, DEGRADED detection, and findings → `tasks.md` insertion):

```
node .specify/extensions/speccable/scripts/validate-detector.mjs \
  --project "$PROJECT_ROOT" \
  --target "$TARGET" \
  --tasks "$TASKS_FILE"
```

(Install-time path rewriting resolves `scripts/validate-detector.mjs` to your installed location under `.specify/extensions/speccable/scripts/`.) Capture the JSON result the validator writes to stdout.

The validator shares its layout discovery (`.agent`, `.agents`, `.claude`, in deterministic order) with `check-compat.ps1` via a single shared data file, so capability discovery and detector invocation can never disagree about where Impeccable exists.

## Step 3 — Present the result

Read the validator's JSON result and report its fields:

- `status` → `PASS | FAIL | NOT_RUN`
- `reason` → `clean | findings | no-ui | exec-unavailable | timeout | malformed-output | non-array | empty-output | layout-unavailable`
- `findingsCount` / `primaryFindingsCount`
- `advisoryOnly`
- `degraded` (and `DEGRADED` alias) → `0 | 1`, with `degradedNotice` verbatim
- `layout` → the selected Impeccable installation root

**The cardinal rule: `NOT_RUN ≠ PASS`.** The validator returns `NOT_RUN` (never `PASS`) for any inability to establish a valid deterministic result: detector unavailable, execution failure, timeout, malformed/non-array/empty output, or a missing required capability. A `degraded` result is never presented as a fully clean unconditional `PASS` — report `DEGRADED=1` with the notice.

## Step 4 — Report

End with the parsable report line derived from the validator result:

```text
UI_VALIDATE_STATUS=<NOT_RUN|PASS|FAIL>
FINDINGS=<findingsCount>
PRIMARY_FINDINGS=<primaryFindingsCount>
REASON=<clean|findings|no-ui|exec-unavailable|timeout|malformed-output|non-array|empty-output|layout-unavailable>
LAYER=<deterministic>
DEGRADED=<0|1>
LAYOUT=<selected layout root>
```

If the validator could not establish a valid result, the status is `NOT_RUN` — never `PASS`. If `FAIL`, the validator has already appended deduplicated follow-up tasks under the `## UI Validation Follow-ups` section of `$TASKS_FILE` for the trusted converge channel.
