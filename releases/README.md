# FSMReasonBench Releases

**Citation target:** Zenodo DOI [10.5281/zenodo.20836348](https://doi.org/10.5281/zenodo.20836348) — not git branch `main`.

This directory records **frozen release manifests** for each citable benchmark version.

---

## Release index

| benchmark_version | cohort_version | Zenodo DOI | Status |
|-------------------|----------------|------------|--------|
| **1.0.0** | `v0.1-expanded-n100` | [10.5281/zenodo.20836348](https://doi.org/10.5281/zenodo.20836348) | **Published** |

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
