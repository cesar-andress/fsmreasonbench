# Cohort Manifest Specification

**Status:** normative  
**Schema:** `schema/cohort_manifest.schema.json` (future)  
**Versioned by:** `cohort_version`

---

## 1. Purpose

The cohort manifest is the **integrity anchor** for a frozen benchmark cohort.
Every Zenodo release MUST include a manifest listing all items with content hashes.

---

## 2. File naming

```
cohorts/<cohort_version>.manifest.json
```

Example: `cohorts/1.0-public.manifest.json`

---

## 3. Manifest structure

```json
{
  "manifest_version": "1.0",
  "cohort_version": "1.0-public",
  "benchmark_version": "1.0.0",
  "schema_version": "1.0.0",
  "created_at": "2026-01-15T00:00:00Z",
  "item_count": 2500,
  "quotas": {
    "flagship": { "F1": 625, "F2": 625, "F3": 500, "F4": 500 },
    "calibration": { "C1": 188, "C2": 187 }
  },
  "items": [
    {
      "item_id": "uuid",
      "family": "F1",
      "family_tier": "flagship",
      "track_stratum": "R1-S1",
      "sha256": "hex digest of canonical evaluatee item JSON",
      "public_fingerprint": "hex digest for contamination detection",
      "evaluatee_path": "evaluatee/items/<item_id>.json"
    }
  ],
  "manifest_sha256": "digest of canonical manifest without this field"
}
```

---

## 4. Canonical item serialization (for hashing)

1. JSON object with evaluatee fields only (no answer keys, no hidden probes)
2. Keys sorted lexicographically
3. UTF-8 encoding, no insignificant whitespace (canonical JSON)
4. SHA-256 of resulting bytes

---

## 5. Validation

`scripts/validate_cohort_integrity.sh` MUST verify:

1. Every `items[].sha256` matches file on disk
2. `item_count` matches `len(items)`
3. Quotas match family counts
4. All `public_fingerprint` values unique within cohort
5. `benchmark_version` compatible with release manifest

---

## 6. Immutability

Once published on Zenodo:

- Manifest MUST NOT change
- Item files MUST NOT change
- Errata → new `cohort_version` or new `benchmark_version`

---

## 7. Related documents

- [`../artifact/release_policy.md`](../artifact/release_policy.md)
- [`../artifact/reproducibility_policy.md`](../artifact/reproducibility_policy.md)
