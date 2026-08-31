---
name: "speckit-speccable-ui-gate"
description: "Read the feature spec's UI Impact value, preserve a valid human-authored classification, classify missing/invalid values, verify required Impeccable capability and design source of truth, and route the Spec Kit workflow. Acts as the authoritative gate at before_plan and as an eager (non-authoritative) classifier at after_specify."
compatibility: "Requires spec-kit project structure with .specify/ directory"
metadata:
  author: "speccable-kit"
  source: "commands/speckit.speccable.ui-gate.md"
scripts:
  ps: scripts/ui-impact.ps1 -SpecFile $SPEC_FILE
---

## Purpose

`ui-gate` enforces the Speccable-kit UI Impact contract. It is invoked:

- as a **mandatory hook at `before_plan`** — the sole authoritative routing point; and
- as an **optional hook at `after_specify`** — an eager early classification for ergonomics only, never authoritative.

All conditional behavior lives here (internal routing); the hook declaration itself is condition-free.

## Inputs

Set these before invoking the gate:

- `$SPEC_FILE` — absolute path to `spec.md` (resolved like core commands do via `.specify/feature.json` → `feature_directory`; fall back to the newest `specs/*/spec.md` if unavailable).
- `$HOOK_EVENT` — the triggering lifecycle name: `after_specify` or `before_plan`.

## Step 1 — Read the classification

Run the impact reader:

{SCRIPT}

Parse the single output line, splitting on `|` into `KEY=VALUE` pairs.

- `UI_IMPACT=none|direct` with `MATCH=preserved` → a **valid human-authored value**. Preserve it verbatim. Never overwrite.
- `UI_IMPACT=unclassified` with `MATCH=none` → the marker is missing. Classify (Step 2).
- `UI_IMPACT=invalid` → the marker is present but malformed/empty/duplicate or an unknown value. Classify (Step 2).

## Step 2 — Classify missing/invalid values

Determine `none` vs `direct` by reading the spec body:

- **`direct`** if the feature clearly creates or materially changes visible UI: user-facing screens, components, forms, dashboards, landing pages, layouts, navigation, responsive behavior, visual styling, or UX/interaction flows.
- **`none`** if the feature is purely backend, API, data, tooling, infrastructure, or non-visible logic with no UI surface.

If you cannot safely determine the classification (ambiguous, or classification would require the user), **fail explicitly**:

- At `before_plan`: stop and report `BLOCK` with the specific ambiguity and what input is required. Never silently default a missing/invalid value to `none`.
- At `after_specify`: report the `unclassified` state and continue; do not fabricate a value.

When you do classify, write the marker into `spec.md`:

```markdown
**UI Impact**: direct
```

(If a malformed marker exists, replace it with the correctly formatted one; if the file already carries a valid value you never touch it.)

## Step 3 — Route

### `UI Impact = none`

Behavior: **continue the native Spec Kit workflow.**

- Do not invoke Impeccable design.
- Do not create UI design artifacts.
- Do not add UI tasks.
- Report: `ROUTE = native` (the feature proceeds as a normal Spec Kit feature).

This is the case even if Impeccable is missing — a non-UI feature must not depend on Impeccable.

### `UI Impact = direct`

Behavior: **enforce the design gate before planning is considered valid.**

1. **Verify Impeccable capability.** Run the compatibility check:

   `scripts/check-compat.ps1`

   (This path is rewritten at install time to your installed location under `.specify/extensions/speccable/scripts/`.) Parse `IMPECCABLE=`/`VERSION=`/`DETECTOR=`/`SUPPORTED=`.
   - Missing Impeccable (`IMPECCABLE=missing`) → **BLOCK** with remediation: "Impeccable must be installed to design this UI-impacting feature. Run `npx impeccable install` in the project root (or via the skill's documented installer), then rerun this gate. Speccable-kit does not auto-install it." Never continue as if design happened.
   - `SUPPORTED=unsupported` (Impeccable present but outside the supported range `>= 4.1 < 5.0`, or an unreadable/malformed version that must fail closed) → **BLOCK** with the supported range and the detected version. Never treat an unsupported version as if design happened.
   - `SUPPORTED=unknown` (should not occur in normal operation; the script fails closed to `unsupported` when it cannot read the version) → **BLOCK** for the same reason.
   - `SUPPORTED=supported` → capability is present and in range; proceed to verify the design source of truth.
2. **Verify design source of truth.** Confirm a design source exists and is current — the Impeccable-owned Surface Brief / design context the spec references (the spec should already reference it under an appropriate section, e.g. the environment/context or a design-reference note). 
   - Missing or stale design source → **BLOCK**: the direct feature must not silently proceed through planning as if design work had happened. Report specifically what is missing; do not fabricate a path and do not guess Impeccable's internal surface-brief layout.
3. **Allow planning.** When Impeccable capability and design source of truth are both present/current, report `ROUTE = design` and continue to planning.

## Hook event context

- At `after_specify` (eager): you may perform Step 1 and, when safe, Step 2 classification, but you must not block. Report the state; let `before_plan` remain authoritative.
- At `before_plan` (authoritative): run all steps; a `direct` feature must never reach completed planning without an appropriate design source of truth.

## Failure behavior

- `UI Impact = none` + Impeccable missing → `continue` (native workflow), no dependency.
- `UI Impact = direct` + Impeccable missing → `BLOCK` + remediation. No auto-install.
- `UI Impact = direct` + design source missing → `BLOCK`.
- Hook cannot execute / required capability unavailable → report the limitation clearly; never claim engine-level enforcement; never convert failure into `none`.

## Report

End with a concise, parsable summary line:

```text
UI_GATE_EVENT=<after_specify|before_plan>
UI_IMPACT=<none|direct|unclassified|invalid>
ROUTE=<native|design|BLOCK>
SOURCE=<preserved|classified>
```
