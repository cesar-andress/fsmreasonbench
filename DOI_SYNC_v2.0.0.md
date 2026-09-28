# DOI_SYNC_v2.0.0

Post-release DOI synchronization after Zenodo archival of FSMReasonBench v2.0.0.

## Verified Zenodo record

| Field | Value |
|-------|-------|
| Title | FSMReasonBench: Witness-Aware Evaluation for Verifier-Gated Reasoning Systems |
| Version | 2.0.0 |
| Version DOI | 10.5281/zenodo.23004350 |
| Concept DOI | 10.5281/zenodo.20836347 |
| Publication date | 2026-09-28 |
| License | Apache-2.0 (`apache2.0`) |
| Creator | Andrés, César (UCJC; ORCID 0009-0001-8968-3404) |
| Repository | https://github.com/cesar-andress/fsmreasonbench |

## Tag immutability

| Check | SHA |
|-------|-----|
| `v2.0.0` before sync | `040cbcea2bb34242e663b54c820e55140b3a40ca` |
| `v2.0.0` after sync | `040cbcea2bb34242e663b54c820e55140b3a40ca` |
| Unchanged | YES |

DOI sync commit (software): `33cbc73ee134198caf3c90fb2a47a41e0b933737` (after tagged commit).  
Paper monorepo commit: `2e46a3888c06dbab22f6ebdc8557d06ab3db5146` (local only; no push).

## Software updates

- README / ARTIFACT_VERSION / CITATION.cff / `.zenodo.json` / releases/2.0.0 / REVIEWER / release notes
- Version DOI preferred for current citation; concept DOI distinguished; v1 DOI retained as historical

## Paper updates (IST active tree)

- `bibliography/references.bib` → title/version/DOI v2.0.0
- Data availability, Artifact Availability, intro/design/threats/appendix pointers
- `\artifactname` macro synchronized
- Build: 60 pages; bbl shows 10.5281/zenodo.23004350

## GitHub Release body

`gh release edit` returned HTTP 403 (token lacks release write). Manual action:
add `https://doi.org/10.5281/zenodo.23004350` to the GitHub Release notes for `v2.0.0`.

## Historical retainers

- Software: CHANGELOG [1.0.0], `releases/1.0.0/`, prep docs naming v1 DOI
- Paper audit JSON/IST_* reports mentioning v1 (historical phase audits)
- Legacy manuscript trees untouched
