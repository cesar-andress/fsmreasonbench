# Exploratory cohort `c2-reachability-balanced-n100-v0.1-expanded`

**Release tier:** exploratory  
**Manifest version:** 0.1-exploratory  
**Created:** 2026-06-24T13:36:56Z  
**Item count:** 100  
**Families:** C2 (100)

This directory is a **non-final, pre-Zenodo cohort snapshot** for reproducible exploratory
studies. It is not version `v1.0-public`, has no DOI, and must not be cited as a final
benchmark result.

## Contents

| File | Purpose |
|------|---------|
| `items.jsonl` | Full benchmark items (including answer keys) |
| `manifest.json` | Cohort metadata, per-item SHA-256 digests, aggregate fingerprint |
| `sha256sums.txt` | Checksums for bundled files |
| `README.md` | This file |

## Validate integrity

```bash
python -m fsmreasonbench.cli.validate_cohort --cohort-dir .
```

## Generator notes

Balanced C2 reachability cohort: 50 reachable (trace_witness) + 50 unreachable (unreachability_witness), batch_seed=5001, generator config matches expanded-n100 level-3 slice.

## Fingerprint

`cohort_fingerprint`: `eece5190d80090fb3e4e231266200600b98c470e32c0a26f39898ad3c73a50b8`
