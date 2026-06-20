# Exploratory cohort `f1-mixed-level3-v0.1-exploratory`

**Release tier:** exploratory  
**Manifest version:** 0.1-exploratory  
**Created:** 2026-06-20T07:34:04Z  
**Item count:** 20  
**Families:** F1 (20)

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

Exploratory F1 mixed cohort, distinguishing trace length level 3, equivalent_ratio=0.5, constructive_decoy enabled for non-equivalent pairs.

## Fingerprint

`cohort_fingerprint`: `4e1e662307456c871ed8c424a4ba493ab041b3d32530feecdef7c19ffe634a67`
