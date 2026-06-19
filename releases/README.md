# FSMReasonBench Releases

**Citation target:** Zenodo DOI (not git branch `main`)

This directory records **frozen release manifests** for each citable benchmark version.

---

## Release index

| benchmark_version | cohort_version | Zenodo DOI | Status |
|-------------------|----------------|------------|--------|
| — | — | — | No release yet |

First target: **FSMReasonBench v1.0.0** with cohort **1.0-public**.

---

## Directory structure

```
releases/
├── README.md
└── <benchmark_version>/
    ├── release_manifest.json    # version pins + file inventory
    ├── RELEASE_NOTES.md
    ├── ERRATA.md                # post-release corrections
    └── SHA256SUMS.template      # filled at packaging time
```

---

## Development vs release

| State | Location | Citable? |
|-------|----------|----------|
| Development | `main` branch, `-draft` specs | **No** |
| Release candidate | git tag `v1.0.0-rc.1` | **No** |
| Published | Zenodo + git tag `v1.0.0` | **Yes** |

See [`docs/artifact/release_policy.md`](../docs/artifact/release_policy.md).
