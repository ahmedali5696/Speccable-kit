# Failure modes

Speccable-kit's failure behavior is explicit and never silently coercive. Every case maps to
a defined outcome. The cardinal rule across all of them: **a missing or failed capability is
never reported as a clean pass, and a `none` classification is never fabricated.**

## Case matrix

| # | Situation                                            | Behavior                                     |
| - | ---------------------------------------------------- | -------------------------------------------- |
| 1 | `UI Impact = none` + Impeccable missing              | **continue** native workflow. A non-UI feature must not depend on Impeccable. |
| 2 | `UI Impact = direct` + Impeccable missing            | **BLOCK** + remediation. No auto-install; user installs Impeccable then reruns the gate. |
| 3 | `UI Impact = direct` + design source of truth missing| **BLOCK**. The direct feature must not reach planning as if design happened. |
| 4 | Detector fails / times out / unusable output         | **NOT_RUN** — never `PASS`.                  |
| 5 | Design source stale                                 | **WARNING** — report, do not auto-repair.    |
| 6 | Hook cannot execute / capability unavailable         | **report the limitation**; never claim engine-level enforcement, never convert failure into `none`. |

## Case 2 — `direct` + Impeccable missing (BLOCK + remediation)

Remediation text is explicit: Impeccable must be installed to design this UI-impacting
feature; the user runs Impeccable's own installer (e.g. `npx impeccable install`) and reruns
the gate. Speccable-kit does not auto-install.

## Case 3 — `direct` + design source missing (BLOCK)

The gate verifies the design source of truth the spec references. If it is missing, the gate
reports specifically what is missing and does not fabricate a path and does not guess
Impeccable's internal surface-brief layout.

## Case 4 — detector failure (NOT_RUN, never PASS)

`ui-validate` distinguishes clean output from any kind of failure:

- process fails to start / times out / no usable output → `NOT_RUN`, reason
  `exec-unavailable` or `timeout`;
- output present but not a JSON array of objects → `NOT_RUN`, reason `malformed-output`;
- valid array, zero primary findings → `PASS`;
- valid array, ≥1 findings → `FAIL`.

The summary line reports `UI_VALIDATE_STATUS=NOT_RUN` with the reason. The detector also
emits a DEGRADED notice on `stderr` when HTML parsers are unavailable (undercount);
`ui-validate` records `DEGRADED=<0|1>` so the undercount is visible, but a degraded detector
result is still never promoted to `PASS` on that basis alone.

## Case 5 — stale design (WARNING, no auto-repair)

If the design source of truth exists but is stale, the gate reports a warning and does not
silently rebuild or repair it. The human (or Impeccable's own flow) decides whether to
regenerate.

## What each hook reports

- `after_specify` / `before_plan` → `UI_GATE_EVENT|UI_IMPACT|ROUTE|SOURCE`. On BLOCK,
  `ROUTE=BLOCK` with the reason in prose.
- `after_implement` → `UI_VALIDATE_STATUS|FINDINGS|REASON|LAYER|DEGRADED`.

These summary lines are machine-parseable and are the primary observable contract of the
failure behavior.
