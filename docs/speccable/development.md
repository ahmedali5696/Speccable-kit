# Development guide

## Repository layout

```
├── extension/                  # source of truth (manifest, commands, scripts)
│   ├── extension.yml
│   ├── commands/
│   │   ├── speckit.speccable.ui-gate.md
│   │   ├── speckit.speccable.ui-design.md
│   │   └── speckit.speccable.ui-validate.md
│   └── scripts/
│       ├── ui-impact.ps1
│       ├── check-compat.ps1
│       ├── validate-detector.mjs
│       └── impeccable-layouts.json  # shared layout resolver (single source of truth)
├── tests/
│   ├── test_contract.py        # 113 contract tests
│   └── run_cleanroom.py        # clean-room install + layout-matrix evidence harness
├── docs/
│   ├── Impeccable-README.md    # vendored reference material (read-only)
│   ├── Spec kit-README.md      # vendored reference material (read-only)
│   └── speccable/              # Speccable-kit documentation
└── README.md
```

## Editing an extension command

Commands are plain Markdown skill files with YAML front-matter. The front-matter may declare
a `scripts:` map; the value of the `ps` (or `sh`/`py`) key is substituted for the `{SCRIPT}`
placeholder in the body, and `scripts/`-relative paths are rewritten at install time to
`.specify/extensions/speccable/scripts/`.

Keep these invariants when editing:

- Hook declarations stay condition-free; route inside the command.
- A valid human-authored UI Impact value is preserved, never overwritten.
- Classification failure blocks; `none` is never fabricated.
- `NOT_RUN` never equals `PASS`.
- Findings go to `tasks.md`, never `/speckit-converge`.
- Never write inside `.impeccable/` or Impeccable's namespace; never vendor Impeccable
  internals; never auto-install.

## Tests

The contract suite (`tests/test_contract.py`) is `unittest`-based and PyYAML-optional (it
degrades gracefully when `yaml` is unavailable via `skipUnless(HAS_YAML)` guards).

```bash
python -m unittest tests.test_contract -v
```

Coverage includes: the `ui-impact.ps1` classifier contract (valid/missing/empty/duplicate/
invalid, case-insensitivity, missing spec, fenced-code exclusion), the `check-compat.ps1`
contract (capability + the `SUPPORTED` version-range verdict across the documented layout
matrix: `.agent`, `.agents`, `.claude`, missing detector, unsupported/malformed version),
the layout-consistency proof (both `check-compat.ps1` and the executable validator resolve
the **same** layout from the shared `impeccable-layouts.json` for every layout combination),
the tolerant detector parser (clean/advisory-only/mixed-primary-and-advisory/empty/
non-array/malformed/unknown-field/missing-field), the manifest (fields, speckit version,
preset-shaped absence, command
namespace), the hooks (required events, condition-free, `before_plan` mandatory +
authoritative, `after_implement` mandatory), architectural boundaries (no core-template
fork, no Impeccable vendoring, condition-free runtime registry, native install
materialization), and **prose-contract regression tests** that read the shipped command
files and assert the agent-facing behavioral contract (no silent `none`, classification
failure blocks, `before_plan` authoritative routing, `direct` requires capability + design
source, `NOT_RUN` ≠ `PASS`, the delegation of `ui-validate` to the executable validator,
deterministic findings → `tasks.md` dedup, and the Impeccable-boundary prohibitions).

Crucially, the F2 deterministic validator is exercised as **executable logic, not a
parser copy**: `TestValidateDetectorExecutable` executes the shipped `validate-detector.mjs`
against a scratch fake detector and verifies parsing, execution (exit/timeout), status
classification (`PASS`/`FAIL`/`NOT_RUN`), `DEGRADED` exposure, layout resolution through the
validator, and `tasks.md` insertion/dedup/no-mutation — all through the real artifact. An
integration path is also exercised via the native-install test (below) executing the
validator through the same installed path the extension uses.

### Native install test

`test_native_install_validation` scaffolds a temporary `.specify/` project and runs
`specify extension add --dev` against it, asserting the skills and hook registry materialize,
then removes the temp directory. It is the authoritative proof that the extension installs
through the native mechanism.

### Clean-room evidence harness

`tests/run_cleanroom.py` installs the shipped extension into fresh isolated temp Spec Kit
projects via the real `specify extension add`, then exercises the real installed artifacts
(`check-compat.ps1`, `validate-detector.mjs`) across the documented layout matrix (missing,
`.agent`, `.agents`, `.claude`, unsupported/malformed version, missing detector, preference
order) and the detector execution modes (clean/findings/advisory/malformed/degraded/timeout).
It writes machine-parseable evidence to `docs/validation/cleanroom-evidence.json`:

```bash
python tests/run_cleanroom.py
```

## Runtime

The extension has no compiled dependencies, but its provided scripts need a runtime
present in the executing environment. Which runtime depends on the script:

| Script                  | Runtime      | Used by              |
| ----------------------- | ------------ | -------------------- |
| `ui-impact.ps1`         | PowerShell   | `ui-gate` (Step 1)   |
| `check-compat.ps1`      | PowerShell   | `ui-gate` (Step 3, `direct`) |
| `validate-detector.mjs` | Node.js      | `ui-validate` (`direct` at `after_implement`) |

- **PowerShell.** The two `.ps1` helpers are invoked with
  `-NoProfile -ExecutionPolicy Bypass`. On **Windows** this maps to the bundled
  `powershell.exe`; the suite is **tested against Windows PowerShell 5.1**. On
  **non-Windows** (Linux/macOS) the commands resolve to **PowerShell Core (`pwsh`)** and are
  only usable if `pwsh` is installed and on `PATH`. Non-Windows PowerShell execution is
  **supported by design but not yet verified by the project's CI** (the CI workflow does not
  yet exercise `pwsh` on a non-Windows runner); treat it as unverified until covered.
- **Node.js.** `validate-detector.mjs` is invoked via `node`; the suite is tested against
  the Node runtime available in CI. It uses only built-in modules (no `node_modules`).

A feature with `UI Impact = none` invokes none of the above — it runs natively.

## Re-syncing an installed copy

After changing `extension/`, re-sync the local install:

```bash
specify extension add ./extension --dev --force
```

## Reinstallable byproducts

`.specify/extensions.yml`, `.specify/extensions/speccable/`, and the materialized
`.zcode/skills/speckit-speccable-*` directories are generated by `specify extension add`.
They are git-ignored; `extension/` is the source of truth.
