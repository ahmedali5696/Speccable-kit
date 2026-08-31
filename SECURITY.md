# Security

## Threat model

Speccable-kit is an **open-source, agent-supported workflow extension**. It is not a
security product and makes no security guarantees beyond what is stated here. It runs
inside your normal Spec Kit project environment with the permissions of the agent/CLI that
invokes it.

- The extension **reads** `spec.md` (UI Impact marker) and Impeccable's public layout
  surfaces (`SKILL.md`, `scripts/detect.mjs`), and **writes** only its own
  `## UI Validation Follow-ups` section of `tasks.md`. It never writes inside Impeccable's
  namespace (`.impeccable/`, `PRODUCT.md`, `DESIGN.md`, surface briefs) and never modifies
  `/speckit-converge`.
- It **never auto-installs** or **auto-upgrades** Impeccable; capability is measured from
  public surfaces and evaluated fail-closed (a present-but-unreadable version is reported
  `unsupported`, never silently `supported`).
- Prompt-injection is **out of scope** for a workflow extension: like any Spec Kit command,
  the agent interprets content from `spec.md` and detector output. Treat untrusted detector
  output as data, not instructions — the validator parses it tolerantly and does not execute
  finding content.

## Reporting a vulnerability

Do **not** open a public issue for a security concern. Report it privately via GitHub's
private vulnerability reporting on the repository, or email the maintainers. Please include:

- the affected version (`extension.version` in `extension/extension.yml`);
- the runtime (OS, PowerShell / Node versions);
- a minimal reproduction (project layout, `UI Impact`, steps);
- the impact you believe applies, and any supported fix.

We will acknowledge reports, and coordinate a fix and disclosure with you.
