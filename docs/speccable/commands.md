# Commands

Speccable-kit ships three commands. Each is declared in `extension.yml` under
`provides.commands[]` and materialized by Spec Kit as a skill.

## `speckit.speccable.ui-gate`

**Responsibility.** Enforce the UI Impact contract and route the workflow.

**Bindings.** Mandatory at `before_plan` (authoritative) and optional at `after_specify`
(eager, non-authoritative).

**Steps.**

1. **Read** — run the impact reader (`ui-impact.ps1`) and parse
   `UI_IMPACT` / `MATCH`. Preserve a valid human-authored `none`/`direct`.
2. **Classify** — for `unclassified`/`invalid`, determine `none` vs `direct` from the spec
   body; write the normalized marker. If it cannot classify safely, BLOCK (never default to
   `none`).
3. **Route** —
   - `none` → `ROUTE=native`; no Impeccable dependency (even if missing).
   - `direct` → verify Impeccable capability (`check-compat.ps1`: `IMPECCABLE=`/
     `VERSION=`/`DETECTOR=`/`SUPPORTED=`) and the design source of truth; then `ROUTE=design`.
     Missing Impeccable or missing design source → `BLOCK` with remediation.
     `SUPPORTED` not `supported` (unsupported, unknown, or fail-closed unreadable version)
     → `BLOCK` with the supported range.

**Output.**

```text
UI_GATE_EVENT=<after_specify|before_plan>
UI_IMPACT=<none|direct|unclassified|invalid>
ROUTE=<native|design|BLOCK>
SOURCE=<preserved|classified>
```

## `speckit.speccable.ui-design`

**Responsibility.** Orchestrate the Impeccable design workflow for a `direct` feature so a
design source of truth exists before planning.

**Boundary.** Never reimplements Impeccable's internal workflow, never fabricates a Surface
Brief filesystem path, never writes inside Impeccable's namespace, never depends on
Impeccable internals, never auto-installs.

**Steps.** Confirm Impeccable presence/version → load design context via Impeccable's
documented setup → shape UI/UX with Impeccable's planning command → produce the design
source of truth via the documented build/design command → add a spec reference to it →
report.

**Output.**

```text
UI_DESIGN=content
DESIGN_SOURCE=<what was produced / where the spec references it>
STATUS=<done|BLOCK>
```

## `speckit.speccable.ui-validate`

**Responsibility.** Deterministic validation of the implemented UI. Bound mandatory at
`after_implement`; also runnable manually. The command **delegates** all
deterministic work to the executable `validate-detector.mjs` and presents its result; it does
not reimplement detector execution, parsing, classification, or `tasks.md` insertion (single
source of truth).

**Steps.**

1. Read UI Impact (`none` → `NOT_RUN`, reason `no-ui`, do not run the validator; `direct` →
   proceed).
2. Delegate to `validate-detector.mjs`, which performs layout resolution (shared
   `impeccable-layouts.json`), detector execution with stdout/stderr/exit capture, tolerant
   JSON parsing, explicit status determination, DEGRADED detection, and `tasks.md` insertion.
3. Present the validator's reported status (`NOT_RUN` / `PASS` / `FAIL`). **`NOT_RUN` never
   equals `PASS`.**
4. On `FAIL`, the validator has already appended deduplicated findings to `tasks.md` (never
   `/speckit-converge`).

**Output.**

```text
UI_VALIDATE_STATUS=<NOT_RUN|PASS|FAIL>
FINDINGS=<count>
PRIMARY_FINDINGS=<count>
REASON=<no-ui|exec-unavailable|timeout|malformed-output|non-array|empty-output|clean|findings|layout-unavailable>
LAYER=<deterministic>
DEGRADED=<0|1>
LAYOUT=<selected layout root|none>
```

If the validator could not establish a valid deterministic result, the status is `NOT_RUN` —
never `PASS`. A degraded result is reported with `DEGRADED=1` and its notice, never promoted
to a clean `PASS` on that basis alone.
