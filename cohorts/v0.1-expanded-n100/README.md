# Exploratory cohort bundle `v0.1-expanded-n100`

Expanded frozen cohorts for powered local-matrix runs (`--max-items 100`).

| Family | Directory | cohort_id | item_count | fingerprint |
|--------|-----------|-----------|------------|-------------|
| C2 | `c2-reachability-level3/` | `c2-reachability-level3-v0.1-expanded-n100` | 100 | `ba0be6ae3895c9bc02bf74442d240cc02f42bfc53e3380d332b6a07e0742ee2b` |
| F1 | `f1-mixed-level3/` | `f1-mixed-level3-v0.1-expanded-n100` | 100 | `61f1ccaa4bf2927361e140b239ac5aaccf8a1c0ab2370f8f915e13e17b06af9b` |

The v0.1-exploratory 20-item cohorts remain immutable. These expanded snapshots use
disjoint generator seeds and item IDs.

## Validate

```bash
PYTHONPATH=src python -m fsmreasonbench.cli.validate_cohort --cohort-dir c2-reachability-level3
PYTHONPATH=src python -m fsmreasonbench.cli.validate_cohort --cohort-dir f1-mixed-level3
```

## Regenerate (deterministic)

```bash
PYTHONPATH=src python -m fsmreasonbench.cli.generate_expanded_cohort --repo-root .
```
