# FSMReasonBench — Quickstart (Zenodo tarball)

You downloaded **FSMReasonBench** from Zenodo. You do **not** need GitHub.

## 1. Verify integrity

```bash
sha256sum -c SHA256SUMS
```

## 2. Check version pins

Open `release_manifest.json` and note:

- `benchmark_version`
- `cohort_version`
- `schema_version`
- `verifier_version`

Cite the Zenodo DOI and these pins in your paper.

## 3. Validate cohort

```bash
./scripts/validate_cohort_integrity.sh \
  --manifest cohorts/<cohort_version>.manifest.json \
  --items cohorts/evaluatee/
```

## 4. Score a submission

```bash
python scripts/verify_submission.py \
  --submission your_submission.json \
  --release release_manifest.json \
  --evaluator-bundle evaluator/
```

## 5. Reproduce paper tables

Requires the paper reproduction supplement (if published):

```bash
./scripts/reproduce_table.sh --table all
```

## Documentation

- Normative spec: `docs/specification/BENCHMARK_SPEC.md`
- Artifact policies: `docs/artifact/`

## Citation

See `CITATION.cff`.
