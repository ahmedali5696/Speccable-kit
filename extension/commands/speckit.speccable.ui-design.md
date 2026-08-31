---
name: "speckit-speccable-ui-design"
description: "Orchestrate the Impeccable design workflow for a UI-impacting feature using Impeccable's documented public commands. Does not reimplement Impeccable, does not fabricate Surface Brief paths, and never writes inside Impeccable's namespace."
compatibility: "Requires spec-kit project structure with .specify/ directory"
metadata:
  author: "speccable-kit"
  source: "commands/speckit.speccable.ui-design.md"
---

## Purpose

`ui-design` drives the Impeccable design workflow for a feature whose UI Impact is `direct`. Impeccable owns feature-level design artifacts (Surface Brief / design source of truth); Speccable-kit only orchestrates the workflow so that a design source exists before planning.

## Invocation

This is a **logical command**, typically triggered by the `ui-gate` when it routes a `direct` feature and design is required. It runs Impeccable through the skill's documented public commands (invoke them the way this agent runs skills, e.g. `/impeccable <command>` or `$impeccable <command>` per your harness).

## Boundary — what this command never does

- Never reimplements Impeccable's internal workflows.
- Never fabricates a Surface Brief filesystem path (no slugging, no `.impeccable/surfaces/...` guessing).
- Never writes inside Impeccable's namespace (`.impeccable/`, `PRODUCT.md`, `DESIGN.md`, surface briefs).
- Never depends on internal Impeccable scripts or manifests.
- Never auto-installs Impeccable.

You know a capability only via Impeccable's documented public surface. If the supported Impeccable version does not expose a stable way to perform a required operation, **degrade or block explicitly** rather than reverse-engineering an internal mechanism.

## Workflow

1. **Precondition.** Confirm Impeccable is present and the version is supported (the `ui-gate` already verified this). If not, stop — do not proceed.

2. **Load design context.** Run Impeccable's setup so design context is available to later commands (e.g. `/impeccable` setup / `init` output guidance as the skill documents). Follow its directives without passing through a dead end.

3. **Shape the UI/UX** for the feature using Impeccable's planning command (e.g. `/impeccable shape <feature>`), the documented "plan UX/UI before writing code" step. This establishes the design direction and, where the skill defines one, the Surface Brief / design source of truth.

4. **Produce the design source of truth.** Where the skill exposes a documented build/design command for the surface (e.g. `/impeccable` design work; `craft`/`new-work` style flows), run it so a design source exists that the spec can reference. The spec must carry a reference to that design source (add a short reference line/note linking to it; do not create a competing Speccable-owned design artifact such as `design.md` or a replacement Surface Brief).

5. **Report.** End with a concise summary:

```text
UI_DESIGN=content
DESIGN_SOURCE=<what was produced / where the spec references it>
STATUS=<done|BLOCK>
```

## Degradation

- If Impeccable's design capability is unavailable (not installed, unsupported version, or the required command is not exposed) → `STATUS=BLOCK` with the specific reason and remediation. Never fake a completed design.
- If a design source already exists and is current, you may report `content` without rebuilding (the `ui-gate` handles staleness separately as a warning).
