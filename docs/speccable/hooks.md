# Hooks & lifecycle

Speccable-kit registers three hook bindings. None carries a `condition:` — all conditional
behavior lives inside the command implementation (routing is internal, not declarative).

| Event            | Command                  | Mandatory | Effect                                    |
| ---------------- | ------------------------ | --------- | ----------------------------------------- |
| `after_specify`  | `speckit.speccable.ui-gate` | optional | eager early classification (never authoritative) |
| `before_plan`    | `speckit.speccable.ui-gate` | **yes**  | **sole authoritative routing point**      |
| `after_implement`| `speckit.speccable.ui-validate` | **yes** | **mandatory deterministic validation trigger** |

> **The `optional` flag is a *manifest declaration*, not an engine-enforced guarantee.**
> "Mandatory" means the extension declares that Spec Kit should invoke the hook at that
> lifecycle point, and that the workflow contract treats it as required. Whether the command
> actually executes — and how its outcome (`ROUTE=design`/`native`/`BLOCK`) is honored — is
> **agent-mediated**: the agent runs the command and is expected to honor it, but no runtime
> engine forcibly prevents completing a plan. Do not read "mandatory" as a hard enforcement
> barrier; read it as the extension's declared routing/validation contract for the agent to
> follow.

## `before_plan` — the authoritative gate

This is where routing is decided. A `direct` feature must never reach a completed plan
without an appropriate design source of truth, and must never silently fall back to the
native workflow just because Impeccable happens to be missing.

- `UI Impact = none` → `ROUTE=native`; continue.
- `UI Impact = direct` + Impeccable present + design source present/current → `ROUTE=design`;
  continue.
- `UI Impact = direct` + Impeccable missing → `BLOCK` + remediation (no auto-install).
- `UI Impact = direct` + design source missing → `BLOCK`.
- `UI Impact = unclassified`/`invalid` and classification fails → `BLOCK` (never default to
  `none`).

## `after_specify` — eager, non-authoritative

Performs the same read and, when safe, the classification, so the user sees the intended
classification as early as possible. It never blocks and never fabricates a value; `before_plan`
remains the authority.

## `after_implement` — mandatory validation

Runs `ui-validate`: deterministic detector output is parsed tolerantly and reported as an
explicit status (`NOT_RUN` / `PASS` / `FAIL`; `NOT_RUN` never equals `PASS`). Actionable
findings are appended to `tasks.md` so the trusted converge channel can consume them.

## Declaration vs behavior

The `extension.yml` hook entries are intentionally condition-free: they list a `command`, an
`optional` flag, a `priority` (default 10), and a description. Every branch — classification,
compat verification, routing, degraded-capability handling — lives inside the commands. This
keeps the manifest simple and makes the extension's behavior easy to reason about from one
place.
