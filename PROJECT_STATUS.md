# FSMReasonBench — Project Status

**Repository:** artifact (`fsmreasonbench`)  
**Last updated:** 2026-06-20  
**Published release:** **FSMReasonBench v1.0.0**  
**Zenodo DOI:** [10.5281/zenodo.20836348](https://doi.org/10.5281/zenodo.20836348)  
**Author:** César Andrés (ORCID [0009-0001-8968-3404](https://orcid.org/0009-0001-8968-3404))  
**Git branch:** `main` (development surface; cite Zenodo, not git)

---

## Released components (v1.0.0)

| Component | Status | Location |
|-----------|--------|----------|
| Zenodo archive | ✅ Published | DOI above; manifest [`releases/1.0.0/`](releases/1.0.0/) |
| Citation metadata | ✅ | [`CITATION.cff`](CITATION.cff) |
| License | ✅ Apache-2.0 | [`LICENSE`](LICENSE) |
| C2 + F1 end-to-end pipeline | ✅ | `generator/` → `verifier/` → `evaluator/` |
| Frozen paper cohort | ✅ | [`cohorts/v0.1-expanded-n100/`](cohorts/v0.1-expanded-n100/) |
| Verifier hostile audit | ✅ | [`docs/f1_equivalence_witness_verifier_audit.json`](docs/f1_equivalence_witness_verifier_audit.json) |
| Hash-mismatch decomposition | ✅ | [`docs/equivalence_hash_mismatch_decomposition.json`](docs/equivalence_hash_mismatch_decomposition.json) |
| Attribution ablation analyses | ✅ | `docs/ablation_*.md`, frozen runs under `runs/` (see paper package) |
| Certificate-class complexity | ✅ | [`docs/certificate_class_complexity_analysis.json`](docs/certificate_class_complexity_analysis.json) |
| Bootstrap / McNemar exports | ✅ | [`docs/tmlr_empirical_package_v1/uncertainty/`](docs/tmlr_empirical_package_v1/uncertainty/) |
| TMLR empirical package | ✅ | [`docs/tmlr_empirical_package_v1/`](docs/tmlr_empirical_package_v1/) |
| Paper result inventory | ✅ | [`docs/paper_results.md`](docs/paper_results.md) |
| Normative specification | ✅ (v2 design; v1.0.0 empirical slice) | [`docs/specification/BENCHMARK_SPEC.md`](docs/specification/BENCHMARK_SPEC.md) |

---

## Available artifacts

### Frozen cohort (`v0.1-expanded-n100`)

Paper headline analyses use this tier ($n{=}100$ per family, $T{=}0.2$).

| Family | Directory | `cohort_id` |
|--------|-----------|-------------|
| C2 | `cohorts/v0.1-expanded-n100/c2-reachability-level3/` | `c2-reachability-level3-v0.1-expanded-n100` |
| F1 | `cohorts/v0.1-expanded-n100/f1-mixed-level3/` | `f1-mixed-level3-v0.1-expanded-n100` |

Validate: `python -m fsmreasonbench.cli.validate_cohort --cohort-dir <path>`

### Primary frozen runs (paper evidence)

Documented in [`docs/tmlr_empirical_package_v1/README.md`](docs/tmlr_empirical_package_v1/README.md):

- `runs/frontier_claude_sonnet_tools_n100_v2` — primary Claude Sonnet R1/R2 campaign
- `runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1`
- `runs/ablations_f1_r2_attribution_claude_n100_v1`
- `runs/ablations_c2_existential_universal_claude_n100_v1`
- `runs/local_matrix_n100_t02_v2` — optional local-model context (not primary paper claims)

Run trees may be gitignored; they ship in the Zenodo tarball for v1.0.0.

### Historical exploratory tier

[`cohorts/v0.1-exploratory/`](cohorts/v0.1-exploratory/) ($n{=}20$ snapshots) and
[`docs/releases/v0.1-exploratory.md`](docs/releases/v0.1-exploratory.md) document an earlier
development milestone. **Not** the citable v1.0.0 release; retained for smoke testing only.

---

## Reproducibility assets

| Asset | Purpose |
|-------|---------|
| [`README-RELEASE.md`](README-RELEASE.md) | Tarball quickstart |
| [`docs/zenodo/REPRODUCIBILITY.md`](docs/zenodo/REPRODUCIBILITY.md) | Replication tiers (R1–R4) |
| [`docs/artifact/reproducibility_policy.md`](docs/artifact/reproducibility_policy.md) | Normative policy |
| `python -m fsmreasonbench.cli.export_tmlr_empirical_package` | Regenerate paper tables/figures offline |
| `python -m fsmreasonbench.cli.artifact_health` | Package integrity check |
| `pytest` | Unit and integration tests |

---

## Measurement model (unchanged)

Four independent layers per item: extractability, verdict accuracy, certificate validity,
full correctness. See [`docs/specification/evaluation_protocol.md`](docs/specification/evaluation_protocol.md).

---

## Implemented vs specified families

| Tier | Family | v1.0.0 empirical slice |
|------|--------|------------------------|
| Calibration | **C2** reachability | ✅ |
| Flagship | **F1** separation / equivalence witnesses | ✅ |
| Flagship | **F2–F4** | Specified; code partially present; not in v1.0.0 claims |
| Calibration | **C1** | Specified only |

---

## Future work (not in v1.0.0)

- Full **F2–F4** flagship implementation and evaluation
- Larger public cohort tier (`1.0-public` design target in spec)
- Hugging Face dataset mirror
- Complete `paper_reproduction/` submission archive layout
- `scripts/reproduce_table.sh` full automation (partial stub remains)

---

## Quick commands

```bash
pip install -e ".[dev,plot]"
pytest -q
PYTHONPATH=src python -m fsmreasonbench.cli.artifact_health
PYTHONPATH=src python -m fsmreasonbench.cli.validate_cohort \
  --cohort-dir cohorts/v0.1-expanded-n100/f1-mixed-level3
PYTHONPATH=src python -m fsmreasonbench.cli.export_tmlr_empirical_package
```

---

## Related audit documents

| Document | Role |
|----------|------|
| [`docs/release_v1_0_0_zenodo_audit.md`](docs/release_v1_0_0_zenodo_audit.md) | Pre-publication audit (superseded by published DOI) |
| [`docs/PAPER_FREEZE_AUDIT.md`](docs/PAPER_FREEZE_AUDIT.md) | Paper run freeze inventory |
