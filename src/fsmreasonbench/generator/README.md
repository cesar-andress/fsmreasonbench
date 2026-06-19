# Generator implementation

**Layer:** implementation (non-normative)  
**Version axis:** `generator_version`  
**Normative inputs:** `spec/generator/`, `spec/oracle/`

Regenerates benchmark items from declarative spec + deterministic seed.

## Status

Not implemented. Do not cite generator behaviour until pinned in a Zenodo release.

## Rules

- Output MUST match `docs/specification/` and `schema/`
- Same `(spec_snapshot, seed, generator_version)` → bit-identical items
- MUST NOT be required to score frozen cohort submissions

## Independence

Must not be imported by `verifier/`.
