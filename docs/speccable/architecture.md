# Architecture

Speccable-kit is an **extension-only** integration. This document describes how it fits
into Spec Kit's native extension model and how it respects both the Spec Kit and Impeccable
boundaries.

## Design posture

Three principles govern every artifact in this repository:

1. **Extension-only.** Speccable-kit uses Spec Kit's native extension mechanism and nothing
   else. There is no Preset, no core-template override, no replacement for
   `spec-template` / `plan-template` / `tasks-template`, no engine event, and no provider
   implementation.
2. **Spec Kit boundary.** Speccable-kit never modifies, forks, or vendors Spec Kit core,
   its templates, its native workflow, or its built-in commands. Files it ships live under
   `extension/`; files the CLI generates under `.specify/extensions/speccable/` are
   reinstallable byproducts, not source.
3. **Impeccable boundary.** Speccable-kit never vendors, forks, modifies, copies, or
   reimplements Impeccable internals; it never writes inside Impeccable's namespace
   (`.impeccable/`, `PRODUCT.md`, `DESIGN.md`, surface briefs); it never depends on
   `.impeccable/live`, `hook.cache.json`, internal scripts, subagents, manifests, slugs, or
   the detector-rule inventory; and it never auto-installs Impeccable.

## The Spec Kit extension model

Spec Kit (`>= 1.0.1`) lets an extension declare, in `extension.yml`:

- **`requires.speckit_version`** — a version specifier the CLI validates.
- **`provides.commands[]`** — named commands with extension-relative markdown files. Each
  command's front-matter may carry a `scripts:` map (`sh` / `ps` / `py`) whose value is
  substituted for the `{SCRIPT}` placeholder, and whose `scripts/`-relative paths are
  rewritten at install time to `.specify/extensions/<id>/scripts/`.
- **`provides.scripts[]`** — shared scripts the commands can call.
- **`hooks{}`** — lifecycle hook bindings. A hook entry names a `command` and may set
  `optional` (default true) and `priority` (default 10). **No `condition` field is used for
  routing**; the declaration is condition-free and all conditional behavior lives inside the
  command implementation.

At install (`specify extension add`), the CLI validates the manifest, writes hook bindings
to `.specify/extensions.yml`, copies the extension tree into
`.specify/extensions/speccable/`, and materializes each command as a runnable skill
(`speckit-speccable-<command>`).

## What Speccable-kit ships

```
extension/
  extension.yml
  commands/
    speckit.speccable.ui-gate.md
    speckit.speccable.ui-design.md
    speckit.speccable.ui-validate.md
  scripts/
    ui-impact.ps1
    check-compat.ps1
    validate-detector.mjs
    impeccable-layouts.json
```

- **`ui-impact.ps1`** reads or classifies the `**UI Impact**:` marker from `spec.md`.
  Output is a single `KEY=VALUE|...` line:
  `UI_IMPACT=<none|direct|unclassified|invalid>|MATCH=<preserved|none|empty|duplicate|mismatch>|FILE=...`.
- **`check-compat.ps1`** **measures** Impeccable capability by reading only public surfaces:
  the installed skill's `SKILL.md` front-matter `version:` and the presence of the documented
  `scripts/detect.mjs`. It **evaluates** the measured version against the approved range
  `>= 4.1 < 5.0` and reports `SUPPORTED=<supported|unsupported|missing>` (fail-closed).
  Output:
  `IMPECCABLE=<present|missing>|VERSION=<ver|unknown>|DETECTOR=<present|missing>|SUPPORTED=<supported|unsupported|unknown|missing>|LAYOUT=<selected root|none>`.
- **`impeccable-layouts.json`** is the single source of truth for Impeccable layout
  discovery (`.agent` → `.agents` → `.claude`, deterministic first-match-wins). Both
  `check-compat.ps1` and `validate-detector.mjs` read this same file, so capability
  detection and detector invocation can never disagree about where Impeccable lives.
- **`validate-detector.mjs`** is the executable deterministic validator: it resolves the
  detector layout (shared file), executes the detector capturing stdout/stderr/exit,
  parses findings tolerantly, reports `PASS`/`FAIL`/`NOT_RUN` (with `DEGRADED` exposure),
  and inserts deduplicated follow-ups into `tasks.md` on `FAIL`. It is the single source of
  truth for deterministic validation behavior.
- **`ui-gate`** is the routing entry point: read/classify UI Impact, verify Impeccable
  capability and design source of truth for `direct`, then route `native` or `design`.
- **`ui-design`** orchestrates Impeccable's documented public design workflow.
- **`ui-validate`** delegates to `validate-detector.mjs` and presents its result; it does
  not reimplement deterministic validation logic.

## Routing

The **sole authoritative pointer is `before_plan`** (bound to `ui-gate`, mandatory). The
same command is also bound at `after_specify` (optional) for eager early classification, but
that binding is never authoritative.

```
before_plan (:ui-gate)
  ├─ none    → native Spec Kit workflow (no Impeccable dep, even if missing)
  └─ direct  → verify Impeccable capability + design source of truth,
               then ui-design; design is required before planning is valid
```

## Validation layering

Speccable-kit keeps **deterministic validation** (`ui-validate`, the detector) strictly
separate from **agent judgment** (Impeccable's `critique` / `audit`). Only the deterministic
layer feeds the four-state status (`NOT_RUN` / `PASS` / `FAIL`); `NOT_RUN` never equals
`PASS`. Agent-judgment layers are never represented as equivalent to deterministic output.

## Boundary checklist

- [x] No Preset, no `provides.presets`.
- [x] No `spec-template` / `plan-template` / `tasks-template` in `extension/`.
- [x] No engine events, no provider implementations.
- [x] No auto-install / auto-upgrade of Impeccable; runtime detection is authoritative.
- [x] No writes into `.impeccable/`, no dependency on Impeccable internals.
- [x] No custom design system, no new design artifact owned by Speccable-kit.
- [x] Findings go to `tasks.md` (the trusted converge channel); `/speckit-converge` is never
  touched.
- [x] Hook declarations are condition-free; routing is internal.
