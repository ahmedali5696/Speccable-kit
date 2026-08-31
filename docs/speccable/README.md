# Speccable-kit documentation

Speccable-kit conditionally integrates Impeccable's design workflow into the native Spec Kit
workflow. These documents describe the extension in full.

## Index

| Document                | Covers                                                            |
| ----------------------- | ----------------------------------------------------------------- |
| [README](./README.md)   | Short orientation. Directs readers to the docs below.             |
| [Architecture](./architecture.md) | Extension model, boundaries, routing, validation layering. |
| [UI Impact](./ui-impact.md)      | The `**UI Impact**:` marker, valid values, classification, no-silent-`none` rule. |
| [Commands](./commands.md)        | `ui-gate`, `ui-design`, `ui-validate` responsibilities and outputs. |
| [Hooks & lifecycle](./hooks.md)  | The three hook bindings, mandatory/optional semantics, authoritative `before_plan`. |
| [Compatibility](./compatibility.md) | Spec Kit `>=1.0.1`, Impeccable `>=4.1 <5.0` runtime detection. |
| [Failure modes](./failure-modes.md) | The six-case explicit failure matrix.                        |
| [Development](./development.md)  | Repo layout, editing, tests, re-sync, byproducts.            |
| [Validation](./validation.md)    | The deterministic validation layer and its status contract.  |

## Source of truth

The extension source lives in [`extension/`](../extension/). Everything Speccable-kit
materializes (`.specify/extensions.yml`, `.specify/extensions/speccable/`, the
`.zcode/skills/speckit-speccable-*` skills) is a reinstallable byproduct of
`specify extension add ./extension --dev`.
