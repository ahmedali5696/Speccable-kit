# Compatibility

Speccable-kit declares and enforces compatibility against two downstream pieces.

## Spec Kit

`extension.yml` declares:

```yaml
requires:
  speckit_version: ">=1.0.1"
```

The Spec Kit CLI validates this at install time. The extension uses only the native
extension mechanism: manifest `schema_version: "1.0"`, `provides.commands[]`,
`provides.scripts[]`, `hooks{}`, front-matter `scripts:` substitution, and install-time path
rewriting. It does not rely on any Spec Kit internal or engine event.

## Impeccable

The supported range is **`>= 4.1 < 5.0`**. There are two distinct things, and the docs
keep them separate:

1. **Version measurement** — `check-compat.ps1` reads the installed skill's `SKILL.md`
   front-matter `version:` line. It inspects only Impeccable's public, documented surfaces:
   - the installed skill's `SKILL.md` front-matter line `version:`; and
   - the presence of the documented detector script `scripts/detect.mjs`.

2. **Supported-range enforcement** — the same script deterministically applies the approved
   range to the measured version and reports `SUPPORTED=<supported|unsupported|unknown|missing>`.
   It **fails closed**: a present-but-malformed or unreadable version is reported
   `unsupported` (never silently `supported`). The routing decision itself remains with the
   agent-mediated `ui-gate`, which BLOCKs a `direct` feature when `SUPPORTED` is not
   `supported`.

It reports:

```text
IMPECCABLE=<present|missing>|VERSION=<ver|unknown>|DETECTOR=<present|missing>|SUPPORTED=<supported|unsupported|unknown|missing>|LAYOUT=<selected root|none>
```

`LAYOUT` names which documented installation root was selected (`.agent/skills/impeccable`,
`.agents/skills/impeccable`, or `.claude/skills/impeccable`, in deterministic first-match-wins
order), resolved from the shared `impeccable-layouts.json` — the same single source of truth
the detector validator uses, so capability detection and detector invocation can never
disagree.

The runtime check is **authoritative** for capability (present/missing) and for the range
verdict used by the gate. Speccable-kit never upgrades Impeccable and never auto-installs it
— those remain Impeccable's own installers' responsibility.

### Why runtime detection

The Impeccable *skill* version (e.g. `4.1.1` in `SKILL.md`) and the Impeccable *npm CLI*
version (a distinct release line) are different things. Rather than assume which one is in
play, `ui-gate` asks `check-compat.ps1` what is actually installed in the project and treats
that as ground truth. If the measured version falls outside `>= 4.1 < 5.0`, the script
reports `SUPPORTED=unsupported` and the gate BLOCKs routing with the supported range and the
detected version rather than guessing.

### Version decision table

| Measured version          | `SUPPORTED`  |
| ------------------------- | ------------ |
| `4.1.x`                   | `supported`  |
| `4.x` (bare `4`, `4.x`)   | `supported`  |
| `4.0.x`                   | `unsupported`|
| `5.x` or higher           | `unsupported`|
| `3.x`                     | `unsupported`|
| malformed / unreadable    | `unsupported` (never silently supported) |
| Impeccable missing        | `missing`    |

## Runtime / PowerShell requirement

Two provided scripts (`ui-impact.ps1`, `check-compat.ps1`) run under **PowerShell**; the
validator (`validate-detector.mjs`) runs under **Node.js**. See
[Development → Runtime](./development.md#runtime) for the precise matrix and for the
distinction between what is **supported by design** and what is **tested**: Windows
PowerShell 5.1 is tested; non-Windows PowerShell Core (`pwsh`) is supported by design but
not yet verified by CI.

## What a "good" environment looks like

- Spec Kit `>= 1.0.1` project (`.specify/` present).
- For `direct` features only: Impeccable skill `>= 4.1 < 5.0` installed per its own
  installer, with a reachable `scripts/detect.mjs` and a design source of truth the spec can
  reference.
- For `none` features: Impeccable is not required at all.
