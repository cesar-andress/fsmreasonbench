# Paper reproduction supplements

Archived model submissions and table provenance for the v1.0.0 Zenodo release
(DOI [10.5281/zenodo.20836348](https://doi.org/10.5281/zenodo.20836348)).

Primary paper evidence is reproduced offline from frozen run directories documented in
[`docs/tmlr_empirical_package_v1/README.md`](../docs/tmlr_empirical_package_v1/README.md) and
[`docs/paper_results.md`](../docs/paper_results.md).

Target layout for extended submission archives:

```
paper_reproduction/
├── manifest.json           # links submissions to cohort item_ids
├── submissions/            # frozen LLM/agent outputs used in paper
└── table_provenance.json   # maps tables → scripts + input files
```

Regenerate paper tables without model APIs:

```bash
PYTHONPATH=src python -m fsmreasonbench.cli.export_tmlr_empirical_package
```

Manuscript source: [`../paper/`](../paper/) (sibling directory in the monorepo layout).

See [`docs/artifact/reproducibility_policy.md`](../docs/artifact/reproducibility_policy.md).
