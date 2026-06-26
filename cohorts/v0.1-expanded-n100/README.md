# Frozen cohort bundle `v0.1-expanded-n100`

**Paper cohort** for the v1.0.0 Zenodo release (DOI [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937)).
Headline empirical analyses in the companion paper use this tier ($n{=}100$ per family, $T{=}0.2$).

| Family | Directory | cohort_id | item_count | fingerprint |
|--------|-----------|-----------|------------|-------------|
| C2 | `c2-reachability-level3/` | `c2-reachability-level3-v0.1-expanded-n100` | 100 | `ba0be6ae3895c9bc02bf74442d240cc02f42bfc53e3380d332b6a07e0742ee2b` |
| F1 | `f1-mixed-level3/` | `f1-mixed-level3-v0.1-expanded-n100` | 100 | `61f1ccaa4bf2927361e140b239ac5aaccf8a1c0ab2370f8f915e13e17b06af9b` |

The smaller `v0.1-exploratory` ($n{=}20$) snapshots remain for historical smoke testing; they
use disjoint seeds and item IDs.

## Validate

```bash
PYTHONPATH=src python -m fsmreasonbench.cli.validate_cohort --cohort-dir c2-reachability-level3
PYTHONPATH=src python -m fsmreasonbench.cli.validate_cohort --cohort-dir f1-mixed-level3
```

## Regenerate (deterministic)

```bash
PYTHONPATH=src python -m fsmreasonbench.cli.generate_expanded_cohort --repo-root .
```

Regeneration must reproduce manifest fingerprints above when using pinned generator defaults.
