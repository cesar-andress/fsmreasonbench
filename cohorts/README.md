# Frozen cohort manifests

Cohort **item data** ships in the **Zenodo release tarball**, not in git at full scale.

This directory holds:

- [`MANIFEST_SPEC.md`](MANIFEST_SPEC.md) — normative manifest format
- `<cohort_version>.manifest.json` — added at cohort freeze (e.g., `1.0-public.manifest.json`)
- `evaluatee/` — small fixtures only in git; full set in Zenodo

## 1.0-public (planned)

| Property | Value |
|----------|-------|
| cohort_version | `1.0-public` |
| benchmark_version | `1.0.0` (at release) |
| Target size | 2,500–5,000 items (TBD) |
| Flagship | F1–F4 (≥ 85%) |
| Calibration | C1–C2 (≤ 15%) |
| Zenodo DOI | not yet deposited |

Integrity validation:

```bash
./scripts/validate_cohort_integrity.sh \
  --manifest cohorts/1.0-public.manifest.json \
  --items cohorts/evaluatee/
```

See `docs/artifact/release_policy.md` and `docs/specification/BENCHMARK_SPEC.md` §11.
