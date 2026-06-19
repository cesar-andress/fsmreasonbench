# Environment pins for Zenodo releases

Populated at release time:

- `requirements-lock.txt` — exact Python dependencies for verifier/evaluator
- `CONTAINER.md` — optional OCI image digest

Development may use `pyproject.toml` (future); **releases MUST use lock file**.

See `docs/artifact/reproducibility_policy.md`.
