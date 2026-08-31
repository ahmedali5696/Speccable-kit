# UI Impact contract

The **UI Impact** marker is how a feature spec tells Speccable-kit whether the feature is UI
impacting, and therefore whether Impeccable design is involved.

## Where it lives

A single inline Markdown marker in `spec.md`, on its own line. It is **not** represented via
YAML front-matter and **not** in a separate file. It is **document metadata**, not arbitrary
example text: a `**UI Impact**:` line that appears *inside a Markdown fenced code block*
(```` ``` ```` ... ```` ``` ````) is an illustrative example and is **ignored**. Only a
marker outside any fence is recognized as metadata.

The fence detection recognizes backtick-delimited fenced code blocks (```` ``` ````), with
or without a language tag and with optional leading indentation. Tilde-delimited
fences (`~~~`) are **not** treated as fences: a marker inside one is currently read as
real metadata. This is a deliberate, minimal scope (see AR-004); marker authors should use
backtick fences for examples or place the real marker outside any fence.

```markdown
**UI Impact**: direct
```

## Valid values

Only two values are valid final classification outcomes:

| Value    | Meaning                                                        |
| -------- | -------------------------------------------------------------- |
| `none`   | No visible UI surface; native Spec Kit workflow, no design.    |
| `direct` | The feature creates or materially changes visible UI; design is required. |

`unclassified` and `invalid` are intermediate states the gate resolves; they are never stored
as final values.

## How the gate reads it

`ui-impact.ps1` locates the marker with a tolerant, case-insensitive, whitespace-tolerant,
line-by-line scan that skips Markdown fenced code blocks, and reports one of:

| Reported               | `MATCH`   | Meaning                                        | Action          |
| ---------------------- | --------- | ---------------------------------------------- | --------------- |
| `UI_IMPACT=none`       | `preserved` | valid human-authored `none`                    | preserve        |
| `UI_IMPACT=direct`     | `preserved` | valid human-authored `direct`                  | preserve        |
| `UI_IMPACT=unclassified` | `none`   | marker missing                                 | classify         |
| `UI_IMPACT=invalid`    | `empty` / `duplicate` / `mismatch` | marker present but malformed | classify |

A missing spec file is reported distinctly (not silently treated as any value).

## Classification

When the value is missing or invalid, the gate classifies it by reading the spec body:

- **`direct`** — the feature clearly creates or materially changes visible UI: user-facing
  screens, components, forms, dashboards, landing pages, layouts, navigation, responsive
  behavior, visual styling, or UX/interaction flows.
- **`none`** — purely backend, API, data, tooling, infrastructure, or non-visible logic with
  no UI surface.

When classification succeeds, the gate writes the normalized marker back into `spec.md`
(replacing a malformed one if present). A valid human-authored value is **never** overwritten;
`SOURCE=preserved` in the report.

## Hard rule: no silent default to `none`

If the gate cannot determine the classification safely (ambiguous, or classification would
require the user), it **fails explicitly**:

- At `before_plan`: stop and report `BLOCK` with the specific ambiguity and required input.
- At `after_specify`: report the `unclassified` state and continue; it never fabricates a value.

A missing or invalid value is **never** silently coerced to `none` — doing so would route a
UI-impacting feature away from design.
