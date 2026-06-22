# Exploratory cohort `f1-mixed-level3-v0.1-expanded-n100`

**Release tier:** exploratory  
**Manifest version:** 0.1-exploratory  
**Created:** 2026-06-22T02:26:04Z  
**Item count:** 100  
**Families:** F1 (100)

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

Expanded exploratory F1 mixed cohort (distinguishing trace length level 3), n=100, seeds 203001–203100, equivalent_ratio=0.5, constructive_decoy. Disjoint from v0.1-exploratory item IDs.

## Fingerprint

`cohort_fingerprint`: `61f1ccaa4bf2927361e140b239ac5aaccf8a1c0ab2370f8f915e13e17b06af9b`
