# Paper reproduction supplements

Archived model submissions and table provenance for **FSMReasonBench: Evaluating Reasoning over Executable Finite-State Machines** v1.0.0
(DOI [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937)).

**Companion paper:** ACM TOSEM — [`../../paper/`](../../paper/)

Primary evidence is reproduced offline from frozen run directories listed in
[`../docs/EXPERIMENTAL_FREEZE_TOSEM.md`](../docs/EXPERIMENTAL_FREEZE_TOSEM.md).

Target layout for extended submission archives:

```
paper_reproduction/
├── manifest.json           # links submissions to cohort item_ids
├── submissions/            # frozen LLM/agent outputs used in paper
└── table_provenance.json   # maps tables → scripts + input files
```

Regenerate TOSEM manuscript tables without model APIs:

```bash
./scripts/reproduce_tosem_tables.sh
```

Manuscript source: [`../../paper/`](../../paper/) (sibling directory in the monorepo layout).

See [`../docs/tosem/REPRODUCTION.md`](../docs/tosem/REPRODUCTION.md) and
[`../docs/artifact/reproducibility_policy.md`](../docs/artifact/reproducibility_policy.md).
