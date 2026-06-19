# FSMReasonBench — Archival Policy

**Status:** normative  
**Horizon:** ≥ 5 years usable and citable

---

## 1. Archival objective

Each Zenodo release MUST remain sufficient for a future researcher to:

1. Understand what was measured (normative spec included or linked)
2. Validate data integrity
3. Score submissions consistently with the paper
4. Cite a stable DOI

---

## 2. Format choices (longevity)

| Choice | Requirement | Rationale |
|--------|-------------|-----------|
| Spec format | Markdown + optional PDF snapshot in release | Human-readable in 5+ years |
| Data format | JSON + JSON Schema | Language-agnostic |
| Code | Python 3.12+ reference impl | Declared in manifest |
| Binary deps | Minimize; prefer stdlib + small pinned set | Zenodo longevity |
| Documentation | Plain text/markdown in tarball | No wiki-only docs |

---

## 3. Zenodo metadata (required fields)

- **Title:** `FSMReasonBench v1.0.0 — Benchmark for Reasoning over Executable Finite-State Machines`
- **Creators:** ORCID-linked
- **License:** SPDX identifier (see PROJECT_STATUS U10)
- **Resource type:** Dataset + Software (dual upload if supported)
- **Version:** matches `benchmark_version`
- **Related identifiers:** companion paper DOI (when available)
- **Keywords:** finite-state machines, benchmark, formal verification, reasoning evaluation

---

## 4. License

License MUST be chosen before first DOI minted. Recommended: **Apache-2.0** or **MIT** for code; **CC-BY-4.0** for evaluatee JSON if dual-licensed.

License file MUST appear in tarball root.

---

## 5. Deprecation

| Status | Meaning |
|--------|---------|
| **Current** | Latest patch of current major |
| **Maintained** | Receives errata patches |
| **Frozen** | No updates; still citable |
| **Superseded** | New major released; old DOI remains valid |

Superseded releases MUST point forward in `README-RELEASE.md`, never delete old DOI.

---

## 6. Bit rot mitigation

Each release includes:

- `SHA256SUMS` for all bundled files
- Pinned `requirements-lock.txt`
- Golden verifier tests runnable offline
- Spec PDF snapshot (recommended)

Optional: OCI container digest for byte-identical environment.

---

## 7. What we do not archive in primary record

- Raw LLM API logs with secrets
- Author private notebooks
- Unbounded external URLs as sole spec reference

External links MAY appear as convenience; normative content MUST be in tarball.

---

## 8. GitHub vs Zenodo (archival view)

| Acceptable on GitHub only | Unacceptable for Zenodo citation |
|---------------------------|----------------------------------|
| Work-in-progress specs (`-draft`) | `-draft` as citable release |
| CI workflow definitions | CI as proof of reproducibility |
| Issue discussions | Informal design rationale without spec update |
| `main` branch drift | Unpinned dependencies |

See [`github_vs_zenodo.md`](github_vs_zenodo.md) for full review.

---

## 9. Related documents

- [`artifact_philosophy.md`](artifact_philosophy.md)
- [`release_policy.md`](release_policy.md)
- [`reproducibility_policy.md`](reproducibility_policy.md)
