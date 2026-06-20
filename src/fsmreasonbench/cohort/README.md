# Cohort tooling

**Layer:** implementation  
**Version axis:** exploratory (`0.1-exploratory`) and future public release manifests

Validates exploratory cohort directories, computes per-item and aggregate fingerprints, and
checks self-verification at freeze time.

## Implemented

| Module | Role |
|--------|------|
| `cohort/freeze.py` | Seal JSONL into manifest + checksum bundle |
| `cohort/validate.py` | Verify files, checksums, manifest, self-verify |
| `cli/freeze_cohort.py` | Freeze exploratory cohort CLI |
| `cli/validate_cohort.py` | Validate exploratory cohort CLI |

## Exploratory freeze

```bash
python -m fsmreasonbench.cli.freeze_cohort \
  --items path/to/items.jsonl \
  --cohort-id my-study-v0.1-exploratory \
  --out-dir cohorts/v0.1-exploratory/my-study
```

Not a Zenodo release. No DOI. Not `v1.0-public`.

See `cohorts/MANIFEST_SPEC.md` for the future public manifest format.
