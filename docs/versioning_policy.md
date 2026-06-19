# FSMReasonBench — Versioning Policy

**Status:** normative  
**Supersedes:** informal `docs/versioning_policy.md` (v1 draft)

This document defines the **four mandatory version axes** and bump rules for Zenodo releases.

---

## 1. Version axes (mandatory pins)

Every citable use of FSMReasonBench MUST declare:

| Axis | Format | Example | Governs |
|------|--------|---------|---------|
| `benchmark_version` | SemVer `MAJOR.MINOR.PATCH` | `1.0.0` | `docs/specification/*`, scoring rules, family definitions |
| `cohort_version` | `<major>.<minor>-<label>` | `1.0-public` | Frozen item set, manifest hashes |
| `schema_version` | SemVer | `1.0.0` | `schema/*.schema.json` |
| `verifier_version` | SemVer | `1.0.0` | `src/fsmreasonbench/verifier/` behaviour |

Optional for regeneration claims:

| Axis | Format | Example | Governs |
|------|--------|---------|---------|
| `generator_version` | SemVer | `1.0.0` | `src/fsmreasonbench/generator/` |

All pins are recorded in `releases/<benchmark_version>/release_manifest.json`.

---

## 2. SemVer rules — benchmark_version

| Bump | When | Cohort impact |
|------|------|---------------|
| **MAJOR** | Task family semantics change; scoring primary metric change; certificate type breaking change | New `cohort_version` major required |
| **MINOR** | New optional fields; new sub-variant; backward-compatible schema extension | New minor cohort optional |
| **PATCH** | Documentation clarifications; non-normative fixes; verifier bugfix with identical acceptance | Cohort unchanged |

**Draft suffix:** Pre-release specs use `-draft` (e.g., `2.0.0-draft`). Not citable on Zenodo.

---

## 3. Cohort version rules

Format: `<major>.<minor>-<label>`

| Component | Meaning |
|-----------|---------|
| `major` | Incompatible item set or manifest schema |
| `minor` | Additive items, same semantics |
| `label` | `public`, `holdout`, `dev` (dev NEVER on Zenodo) |

Examples:

- `1.0-public` — first public flagship+calibration cohort
- `1.1-public` — additive items, same benchmark_version minor bump
- `2.0-public` — new major benchmark, new item IDs

**Immutability:** Once deposited on Zenodo, a cohort manifest MUST NOT change.

---

## 4. Schema version rules

- Schemas live in `schema/` with `schema_version` in each file's `$id` or companion `schema/VERSION`.
- Schema MAJOR bump when required fields are added/removed or types change.
- Evaluator and verifier MUST declare compatible `schema_version` range in release manifest.

---

## 5. Verifier version rules

- Verifier is versioned independently because bugfixes MUST be traceable without conflating spec changes.
- **Acceptance test suite:** any verifier release MUST pass golden fixtures in `tests/golden/`.
- If verifier fix changes scores on frozen cohort without spec change → PATCH bump + errata note in release notes.

---

## 6. Generator version rules

- Generator changes that alter item output for same `(spec, seed)` → MINOR or MAJOR generator bump.
- Regeneration claim in paper: must pin `generator_version` + `spec/` snapshot hash.

---

## 7. Compatibility matrix (release manifest)

```json
{
  "benchmark_version": "1.0.0",
  "cohort_version": "1.0-public",
  "schema_version": "1.0.0",
  "verifier_version": "1.0.0",
  "generator_version": "1.0.0",
  "compatible": {
    "schema_version": ["1.0.0"],
    "verifier_version": ["1.0.0", "1.0.1"]
  }
}
```

---

## 8. Mapping: v2.0.0-draft (development) → v1.0.0 (first Zenodo)

The current development spec (`2.0.0-draft`, F1–F4 design) will be normalized to **`benchmark_version: 1.0.0`** at first Zenodo release unless a MAJOR semantic change occurs before freeze.

Development `-draft` versions MUST NOT receive DOIs.

---

## 9. Git tags

| Tag pattern | Meaning |
|-------------|---------|
| `v1.0.0` | Released benchmark (matches Zenodo) |
| `v1.0.0-rc.1` | Release candidate |
| `cohort-1.0-public` | Cohort freeze point (annotated tag) |

---

## 10. Related documents

- [`release_policy.md`](artifact/release_policy.md)
- [`reproducibility_policy.md`](artifact/reproducibility_policy.md)
