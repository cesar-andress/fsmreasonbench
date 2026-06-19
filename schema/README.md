# JSON Schema — Versioning

**Current `schema_version`:** see [`VERSION`](VERSION)

Schemas in this directory define **contracts** between benchmark layers.
They are versioned independently of `benchmark_version` but pinned together in
`releases/<benchmark_version>/release_manifest.json`.

## Files

| Schema | Status |
|--------|--------|
| `fsm.schema.json` | draft (pre-F1–F4 alignment) |
| `question.schema.json` | draft (legacy T1–T7 enums) |
| `answer.schema.json` | draft |
| `cohort_manifest.schema.json` | not yet created |
| `certificate/*.schema.json` | not yet created |
| `release_manifest.schema.json` | not yet created |

## Rules

1. Breaking field changes → bump schema MAJOR
2. All releases pin exact `schema_version`
3. Verifier declares compatible schema range in release manifest

See [`docs/versioning_policy.md`](../docs/versioning_policy.md).
