# Validation

Speccable-kit adds a **deterministic validation layer** (`ui-validate`) that runs at
`after_implement`. This is deliberately distinct from agent-judgment layers.

## Two distinct layers

| Layer           | Tool                                 | Nature       | Feeds the status? |
| --------------- | ------------------------------------ | ------------ | ----------------- |
| Deterministic   | Impeccable **detector** (`detect`)   | mechanical, rule-based | yes |
| Agent judgment  | Impeccable `critique` / `audit`      | design/UX judgment | no |

The four-state status (`NOT_RUN` / `PASS` / `FAIL`) comes **only** from the deterministic
layer. An appealing-sounding critique is never represented as deterministic validation, and
vice versa.

## When validation applies

`ui-validate` reads UI Impact from `spec.md` first:

- `none` (or no UI impact) → `STATUS=NOT_RUN`, reason `no-ui`. The detector is **not** run.
- `direct` → proceed.

## Running the detector

`ui-validate` delegates to the **executable** `validate-detector.mjs` (a provided
Speccable-kit script), which is the single source of truth for deterministic validation. The
command does not reimplement detector execution, parsing, classification, or `tasks.md`
insertion — it presents the validator's result.

Detector layout discovery lives in one shared data file, `scripts/impeccable-layouts.json`,
read by both `check-compat.ps1` (for capability) and `validate-detector.mjs` (for detector
invocation), so the two can never disagree about where Impeccable lives. The documented
layouts, in deterministic first-match-wins order, are:

```text
.agent/skills/impeccable/scripts/detect.mjs   (Antigravity layout)
.agents/skills/impeccable/scripts/detect.mjs  (Codex layout)
.claude/skills/impeccable/scripts/detect.mjs  (Claude Code layout)
```

Only these documented layouts are used; no other paths are inferred, and no provider-specific
branch is introduced (they are plain filesystem roots in the shared data file). The validator
runs the first one found with JSON output:

```bash
node <resolved>/detect.mjs detect --json <target>
```

If none exists (or the detector script is missing), the detector is unavailable and
validation reports `NOT_RUN` (reason `exec-unavailable`), matching what the compatibility
check reports for a missing detector.

`<target>` is the implemented UI surface — a directory, HTML file, or route. Stdout (the
JSON findings array), stderr (which may carry a `DEGRADED` notice), and the exit code are
captured separately.

## Status decision (explicit)

| Output observed                      | Status  | Reason                  |
| ------------------------------------ | ------- | ----------------------- |
| Impeccable missing / detect missing / process failed to start / timeout / no usable output | `NOT_RUN` | `exec-unavailable` / `timeout` |
| Output not a JSON array of objects   | `NOT_RUN` | `malformed-output`     |
| Valid array, zero primary findings   | `PASS`   | `clean`                 |
| Valid array, ≥1 findings             | `FAIL`   | `findings`              |
| UI Impact `none`                     | `NOT_RUN`| `no-ui`                 |

**The cardinal rule: `NOT_RUN` ≠ `PASS`.** A detector that fails, times out, is unavailable,
or cannot produce usable results is `NOT_RUN`, never `PASS`.

### Degraded capability

The detector may print a `DEGRADED` notice to `stderr` when its HTML parsers are
unavailable, meaning HTML-heavy scans undercount. `ui-validate` records `DEGRADED=<0|1>` so
the undercount is visible in the report, but a degraded result is still not promoted to
`PASS` on that basis alone.

## Tolerant parsing

The detector JSON schema is not an immutable semantic API. `validate-detector.mjs` parses each
finding as follows (the command does not reimplement this — it is executable, shared logic):

- Ignore unknown fields.
- Tolerate unknown/new values (e.g. an unknown `severity` or `category`, a new
  `antipattern` id).
- Never crash solely because of additional fields or new severity values.
- Preserve useful information when fields are missing (e.g. missing `line`/`snippet` →
  still record the finding with `antipattern`, `file`, `description`).
- Treat `advisory: true` findings as non-blocking notes, not `FAIL` failures.
- Fail explicitly (`NOT_RUN`) only when the result is structurally unusable (not a JSON
  array of objects).

## Findings → tasks.md

On `FAIL`, `validate-detector.mjs` appends actionable findings to `tasks.md` — the trusted
converge channel — as concise, distinct follow-up tasks, each with id/description, location,
why it matters, and an acceptance criterion ("must not re-trigger this detector finding").
`/speckit-converge` is never modified.

### Deterministic insertion & deduplication

Insertion is anchored to a stable, explicit section heading so repeated runs converge instead
of pile up:

```markdown
## UI Validation Follow-ups
```

- If the section already exists, insert under it (append at its end, before the next heading).
- If it does not exist, create it at the end of `tasks.md`.
- Each task carries a **stable finding signature** derived from the detector finding (the
  finding `antipattern` id, plus primary file and line when present). On a later validation,
  a finding with an identical signature is **not** added again — it is treated as already
  surfaced.
- Equivalent findings (same signature) are never duplicated on repeated validation.
- Existing user-authored tasks outside the section are **never modified**.
- A partial/failed validation (`NOT_RUN` / `PASS`) never writes to `tasks.md`; only a `FAIL`
  with parseable findings touches the section. A failed run cannot corrupt the file.

The signature tolerates future detector schema changes: it relies only on the stable
`antipattern` identity and, when present, `file`/`line` — consistent with the tolerant-parser
philosophy (new fields are ignored, missing fields are preserved).

## Output contract

```text
UI_VALIDATE_STATUS=<NOT_RUN|PASS|FAIL>
FINDINGS=<count>
REASON=<exec-unavailable|malformed-output|timeout|clean|findings|no-ui>
LAYER=<deterministic>
DEGRADED=<0|1>
```

If detector execution failed, the reason is `exec-unavailable`, `timeout`, or
`malformed-output` and the status is `NOT_RUN` — never `PASS`.
