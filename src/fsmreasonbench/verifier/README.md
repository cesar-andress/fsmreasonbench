# Verifier implementation

**Layer:** implementation (reference)  
**Version axis:** `verifier_version`  
**Normative authority:** `docs/specification/certificate_formats.md`

Independently checks submitted certificates and artefacts against item FSMs and questions.

## Status

Not implemented — **blocking for Zenodo v1.0.0**.

## Rules

- MUST NOT import `generator/` or oracle modules
- MUST declare `verifier_version` matching release manifest
- MUST pass `tests/golden/` before release

## Shipped in Zenodo

Primary tarball includes verifier — sufficient for scoring without generator.
