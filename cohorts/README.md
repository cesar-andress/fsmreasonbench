# Frozen cohort manifests

Cohort item data for the **published v1.0.0 release** is archived on Zenodo (DOI
[10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937)).

This directory holds committed manifests and JSONL snapshots used for validation and development.

- [`MANIFEST_SPEC.md`](MANIFEST_SPEC.md) — normative manifest format
- [`v0.1-expanded-n100/`](v0.1-expanded-n100/) — **paper cohort** ($n{=}100$ per family)
- [`v0.1-exploratory/`](v0.1-exploratory/) — historical $n{=}20$ smoke snapshots (not citable release)

## Paper cohort (`v0.1-expanded-n100`)

| Property | Value |
|----------|-------|
| cohort_version | `v0.1-expanded-n100` |
| benchmark_version | `1.0.0` (Zenodo release) |
| Families | C2 reachability + F1 mixed |
| Items | 100 per family directory |
| Zenodo DOI | [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937) |

Validate:

```bash
PYTHONPATH=src python -m fsmreasonbench.cli.validate_cohort \
  --cohort-dir cohorts/v0.1-expanded-n100/f1-mixed-level3
```

## Future cohort tiers

A larger `1.0-public` cohort remains a **design target** in the normative specification; it is
not the cohort used by the published v1.0.0 paper analyses.

See `docs/specification/BENCHMARK_SPEC.md` §11 and `docs/artifact/release_policy.md`.
