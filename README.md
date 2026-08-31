# Speccable-kit

Conditionally integrates [Impeccable](https://github.com/impeccable)'s design workflow
into the native [Spec Kit](https://github.com/specify) workflow. Speccable-kit is an
**open-source Spec Kit extension** (`1.0.0`) that:

- reads a **UI Impact** classification from the feature spec;
- routes `none` features through the **native Spec Kit workflow** untouched; and
- for `direct` (UI-impacting) features, verifies Impeccable capability and its
  **design source of truth** before planning, runs Impeccable's design workflow, and
  validates the implemented UI with Impeccable's **deterministic detector**.

It is **extension-only**: it ships no Preset, replaces no Spec Kit template, forks no
core command, and vendors none of Impeccable. All integration happens through Spec Kit's
native extension mechanism and Impeccable's documented public surfaces.

---

## Contents

- [Installation](#installation)
- [How it works](#how-it-works)
- [UI Impact contract](#ui-impact-contract)
- [Commands](#commands)
- [Hooks](#hooks)
- [Compatibility](#compatibility)
- [Failure behavior](#failure-behavior)
- [Validation](#validation)
- [Development](#development)
- [Architecture & boundaries](#architecture--boundaries)
- [Detailed docs](#detailed-docs)
- [Contributing & license](#contributing--license)

---

## Installation

Prerequisites:

- A **Spec Kit** project (`≥ 1.0.1`) — a directory with a `.specify/` structure.
- (Only for `direct` features) **Impeccable** skill `≥ 4.1 < 5.0`, installed per
  Impeccable's own installer. Speccable-kit **never auto-installs** Impeccable.

Install from this repository's `extension/` directory:

```bash
specify extension add ./extension --dev
```

Or, once published, by its extension identifier. The Spec Kit CLI validates the manifest,
registers the three hooks in `.specify/extensions.yml`, and materializes the three commands
as skills (`speckit-speccable-ui-gate`, `speckit-speccable-ui-design`,
`speckit-speccable-ui-validate`).

> The source of truth is `extension/`. Files that `specify extension add` generates
> (`.specify/extensions.yml`, `.specify/extensions/speccable/`, and the materialized
> `.zcode/skills/speckit-speccable-*` dirs) are reinstallable byproducts and are git-ignored.

---

## How it works

The single authoritative routing point is the **`before_plan`** hook (`ui-gate`). The same
command is also wired at `after_specify` as an optional, non-authoritative early classifier
for ergonomics. All conditional behavior lives inside the command implementation; the hook
declarations are condition-free.

```
spec.md  --UI Impact?-->  ui-gate (before_plan, authoritative)
                              |
                      +-------+-------+
                      |               |
                 none (native)   direct (design)
                      |               |
            native Spec Kit    1. verify Impeccable capability (compat check)
            workflow (no UI)   2. verify design source of truth
                      |        3. ui-design: orchestrate Impeccable
                      |               |
                      +-------+-------+
                              |
                      planning / implement
                              |
                      after_implement: ui-validate (deterministic detector)
```

---

## UI Impact contract

The spec carries a single inline marker (not YAML front-matter, not a separate file):

```markdown
**UI Impact**: direct
```

Only `none` and `direct` are valid final values. The classification rules:

| Encountered              | Meaning                          | Action                                   |
| ------------------------ | -------------------------------- | ---------------------------------------- |
| `none` / `direct`        | valid human-authored value       | **preserved verbatim**, never overwritten |
| marker missing           | `unclassified`                   | classify (gate, Step 2)                   |
| marker empty/duplicate/unknown | `invalid`                  | classify (gate, Step 2)                   |
| cannot classify safely   | —                                | **BLOCK**; never silently default to `none` |

Classification guidance: `direct` if the feature creates or materially changes visible UI
(screens, components, forms, dashboards, layouts, navigation, responsive behavior, styling,
UX/flow); `none` if purely backend/API/data/tooling/infrastructure with no UI surface.

---

## Commands

| Command                          | Responsibility                                                        |
| -------------------------------- | --------------------------------------------------------------------- |
| `speckit.speccable.ui-gate`      | Read/classify UI Impact; verify Impeccable capability + design source; route. |
| `speckit.speccable.ui-design`    | Orchestrate Impeccable's design workflow (design source of truth before planning). |
| `speckit.speccable.ui-validate`  | Delegates to the executable validator (deterministic status + findings → tasks.md). |

---

## Hooks

| Event          | Command        | Mandatory | Notes                                   |
| -------------- | -------------- | --------- | --------------------------------------- |
| `after_specify`| `ui-gate`      | optional  | eager early classification (never authoritative) |
| `before_plan`  | `ui-gate`      | **yes**   | sole authoritative routing point        |
| `after_implement` | `ui-validate` | **yes** | mandatory deterministic validation trigger |

All declarations are condition-free; routing is internal to the command.

---

## Compatibility

- **Spec Kit**: `>= 1.0.1` (declared in `extension.yml`).
- **Impeccable**: `>= 4.1 < 5.0`. `check-compat.ps1` **measures** the installed skill version
  from public surfaces only (the skill's `SKILL.md` `version:` and the documented
  `scripts/detect.mjs`) and reports `SUPPORTED=<supported|unsupported|missing>` by applying
  that range to the measurement (fail-closed: an unreadable version is never reported
  supported). The `ui-gate` then blocks a `direct` feature unless `SUPPORTED=supported`.
  Speccable-kit never upgrades or auto-installs Impeccable.

---

## Runtime requirements

A Spec Kit project **`>= 1.0.1`** is always required (declared in `extension.yml`). In
addition, the two provided **PowerShell** helper scripts need a PowerShell runtime on `PATH`
(`powershell.exe` on Windows), and the deterministic validator needs **Node.js**:

| Script                | Runtime          | Used by                        | When                          |
| --------------------- | ---------------- | ------------------------------ | ----------------------------- |
| `ui-impact.ps1`       | PowerShell       | `ui-gate` (Step 1)             | every `before_plan` / `after_specify` |
| `check-compat.ps1`    | PowerShell       | `ui-gate` (Step 3, `direct`)   | `direct` features only        |
| `validate-detector.mjs` | Node.js        | `ui-validate`                  | `direct` features at `after_implement` |

- **Windows**: tested against **Windows PowerShell 5.1**. The `.ps1` scripts run with the
  documented `-NoProfile -ExecutionPolicy Bypass` invocation.
- **Non-Windows (Linux/macOS)**: the `.ps1` scripts require **PowerShell Core (`pwsh`)**
  installed and on `PATH`. This is supported by design but is **not yet verified by the
  project's CI** — see [Development → Runtime](./docs/speccable/development.md#runtime). Do
  not assume a non-Windows host is tested.
- **`none` features** never invoke PowerShell or Node; the native Spec Kit workflow runs
  unchanged.

---

## Failure behavior

| # | Situation                                   | Behavior                                        |
| - | ------------------------------------------- | ----------------------------------------------- |
| 1 | `none` + Impeccable missing                 | **continue** native workflow (no dependency)     |
| 2 | `direct` + Impeccable missing               | **BLOCK** + remediation (no auto-install)        |
| 3 | `direct` + design source missing            | **BLOCK**                                       |
| 4 | detector fails / unusable output            | **NOT_RUN**, never PASS                         |
| 5 | stale design source                         | **WARNING** (no auto-repair)                    |
| 6 | hook cannot execute                         | report the limitation; never claim engine enforcement |

---

## Validation

`ui-validate` runs at `after_implement`. It **delegates** to the executable
`validate-detector.mjs` (the single source of truth for deterministic validation), which
resolves Impeccable's documented detector from the shared `impeccable-layouts.json`
(`.agent` → `.agents` → `.claude`, deterministic first-match-wins), runs the first one found
with JSON output, parses the JSON findings tolerantly (ignores unknown fields, tolerates
unknown severities, preserves missing info), and reports an explicit four-state status with
`DEGRADED` exposure.

The cardinal rule: **`NOT_RUN` ≠ `PASS`**. A detector that is unavailable, times out, or
produces unusable output is `NOT_RUN`, never `PASS`.

On `FAIL`, findings are surfaced into `tasks.md` (the trusted converge channel) as
deduplicated, actionable validation follow-ups. This is separate from Impeccable's
agent-judgment layers (`critique` / `audit`), which are never equated to deterministic
output.

---

## Development

Source layout:

```
extension/
  extension.yml                     # manifest (schema_version "1.0")
  commands/
    speckit.speccable.ui-gate.md
    speckit.speccable.ui-design.md
    speckit.speccable.ui-validate.md
  scripts/
    ui-impact.ps1                   # read/classify UI Impact from spec.md
    check-compat.ps1                # report Impeccable capability from public surfaces
    validate-detector.mjs           # executable deterministic validator (single source of truth)
    impeccable-layouts.json         # shared layout resolver (read by both of the above)
tests/
  test_contract.py                  # 113 contract tests (unittest, PyYAML-optional)
  run_cleanroom.py                  # clean-room install + layout-matrix evidence harness
```

Run the contract suite:

```bash
python -m unittest tests.test_contract -v
```

Re-sync an installed copy after editing `extension/`:

```bash
specify extension add ./extension --dev --force
```

CI runs the suite on **Windows** (PowerShell 5.1, Node, native install + clean-room) and on
**Linux** (PowerShell Core `pwsh`, Node) — see [.github/workflows/ci.yml](./.github/workflows/ci.yml).


---

## Architecture & boundaries

- **Extension-only v1.** No Preset, no core-template replacement, no engine events, no
  provider implementations, no auto-install/upgrade, no custom design system, no new design
  artifact, no convergence engine.
- **Spec Kit boundary.** Never forks/vendors/modifies Spec Kit core, its templates, its
  native workflow, or its built-in commands.
- **Impeccable boundary.** Never vendors/forks/copies/reimplements Impeccable internals;
  never writes inside Impeccable's namespace (`.impeccable/`, `PRODUCT.md`, `DESIGN.md`,
  surface briefs); never depends on `.impeccable/live`, `hook.cache.json`, internal
  scripts/subagents/manifests/slugs, or the detector-rule inventory; never auto-installs.

---

## Detailed docs

- [README](./docs/speccable/README.md)
- [Architecture](./docs/speccable/architecture.md)
- [UI Impact contract](./docs/speccable/ui-impact.md)
- [Commands](./docs/speccable/commands.md)
- [Hooks & lifecycle](./docs/speccable/hooks.md)
- [Compatibility](./docs/speccable/compatibility.md)
- [Failure modes](./docs/speccable/failure-modes.md)
- [Development guide](./docs/speccable/development.md)

## Contributing & license

- [Contributing](./CONTRIBUTING.md) — development workflow, boundaries, and testing.
- [Security](./SECURITY.md) — threat model and how to report a vulnerability.
- [Changelog](./CHANGELOG.md) — version history.
- **Code of conduct**: none is adopted yet; behavior is governed by the maintainer's
  discretion and standard open-source etiquette.
- **License**: [MIT](./LICENSE). The extension manifest declares `license: MIT`.
- The version is the single `extension.version` value in [`extension/extension.yml`](./extension/extension.yml),
  kept in sync with `CHANGELOG.md`; releases are tagged `v<version>`.
