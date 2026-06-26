# FSMReasonBench Releases

**Artifact:** **FSMReasonBench: Evaluating Reasoning over Executable Finite-State Machines** v1.0.0  
**Citation target:** Zenodo DOI [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937) — not git branch `main`.  
**GitHub release:** FSMReasonBench v1.0.0

This directory records **frozen release manifests** for each citable benchmark version.

---

## Release index

| benchmark_version | cohort_version | Zenodo DOI | Status |
|-------------------|----------------|------------|--------|
| **1.0.0** | `v0.1-expanded-n100` | [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937) | **Published** |

Manifest and notes: [`1.0.0/`](1.0.0/)

---

## Directory structure

```
releases/
├── README.md
└── <benchmark_version>/
    ├── release_manifest.json
    ├── RELEASE_NOTES.md
    └── ERRATA.md                (if post-release corrections)
```

Template for future versions: [`TEMPLATE/`](TEMPLATE/)

---

## Development vs release

| State | Location | Citable? |
|-------|----------|----------|
| Development | `main` branch | **No** — cite Zenodo |
| Published | Zenodo tarball + [`1.0.0/release_manifest.json`](1.0.0/release_manifest.json) | **Yes** |

See [`docs/artifact/release_policy.md`](../docs/artifact/release_policy.md).
