# FSMReasonBench — Quickstart (Zenodo tarball)

You downloaded **FSMReasonBench v1.0.0** from Zenodo.

**DOI:** [10.5281/zenodo.20836348](https://doi.org/10.5281/zenodo.20836348)

You do **not** need GitHub for citation or scoring.

## 1. Verify integrity

If the tarball includes checksums:

```bash
sha256sum -c SHA256SUMS
```

## 2. Check version pins

Open `releases/1.0.0/release_manifest.json` (or root `release_manifest.json` if flattened) and note:

- `benchmark_version`
- `cohort_version` (`v0.1-expanded-n100` for the paper cohort)
- `schema_version`
- `verifier_version`

Cite the Zenodo DOI and these pins in your paper.

## 3. Validate cohort

```bash
PYTHONPATH=src python -m fsmreasonbench.cli.validate_cohort \
  --cohort-dir cohorts/v0.1-expanded-n100/f1-mixed-level3
```

Legacy shell wrapper (if present):

```bash
./scripts/validate_cohort_integrity.sh --help
```

## 4. Score a submission

```bash
PYTHONPATH=src python -m fsmreasonbench.cli.score_submission \
  --item examples/item_F1_separation_seed42.json \
  --submission examples/submission_C2_correct.json
```

Or `scripts/verify_submission.py` when packaged in the tarball layout.

## 5. Reproduce TOSEM paper tables (offline)

```bash
pip install -e ".[dev,plot]"
./scripts/reproduce_tosem_tables.sh
```

Outputs: `../paper/tables/` (TOSEM manuscript) and `docs/tosem_empirical_package_v1/`.
Requires frozen run trees included in the tarball. **No model API calls.**

## Documentation

- TOSEM workflow: `docs/tosem/REPRODUCTION.md`
- Normative spec: `docs/specification/BENCHMARK_SPEC.md`
- Reproducibility: `docs/zenodo/REPRODUCIBILITY.md`
- Historical TMLR package: `docs/tmlr_empirical_package_v1/README.md`

## Citation

See `CITATION.cff`.
