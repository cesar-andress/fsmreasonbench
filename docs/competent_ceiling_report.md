# Competent Ceiling Report

Comparison of **oracle**, **reference submitter**, and **competent submitter**
on frozen exploratory cohorts (`v0.1-exploratory`).

## System definitions

| System | Role |
|--------|------|
| **oracle** | Symbolic ceiling via oracle procedures and certificate builders. |
| **reference_submitter** | Non-oracle workflow using oracle decision procedures and public
certificate builders; no `answer_key.certificate` access. |
| **competent_submitter** | R1-style step-simulator agent: bounded runtime simulation only
(`simulate`, `reachable_states`, `accepts_trace`, `minimized_dfa_hash`); explicit
reasoning logs; public submission schema; no `fsmreasonbench.oracle` imports. |

## Results

| cohort | family | system | n | extract | verdict | cert | full |
|--------|--------|--------|--:|--------:|--------:|-----:|-----:|
| `c2-reachability-level3-v0.1-exploratory` | C2 | oracle | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `c2-reachability-level3-v0.1-exploratory` | C2 | reference_submitter | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `c2-reachability-level3-v0.1-exploratory` | C2 | competent_submitter | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `f1-mixed-level3-v0.1-exploratory` | F1 | oracle | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `f1-mixed-level3-v0.1-exploratory` | F1 | reference_submitter | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `f1-mixed-level3-v0.1-exploratory` | F1 | competent_submitter | 20 | 1.000 | 1.000 | 1.000 | 1.000 |

## Interpretation

**Does `competent_submitter` add evidence beyond `reference_submitter`?**
Partially, but not on contract satisfiability. Both reach `fully_correct_rate = 1.0`
on the frozen exploratory C2/F1 cohorts, so M2 contract-unsatisfiability and
oracle-certificate-injection threats remain equally ruled out.

The incremental value is **process coverage**, not a higher ceiling:
`competent_submitter` shows an auditable R1-style step-simulator workflow
(logged BFS / product exploration / trace replay) can assemble verifier-valid
certificates without importing oracle modules. That narrows the remaining gap
toward tool-augmented human or model behaviour, but does not substitute for
human-expert or frontier-model evaluation.

**M2 impact:** unchanged on contract impossibility; slightly strengthened on
encoding-only explanations when models fail despite all three ceilings at 1.0.

**Still missing for Q1 construct-validity closure:**
- human-expert ceiling on a stratified public sample;
- frontier-model panel on frozen `v1.0-public` cohorts with adequate power;
- R1/R2 track runners and F2 non-materialized composition (separate milestones).

## Suggested paper paragraph

We report three evaluator-facing ceilings on frozen exploratory cohorts.
The oracle baseline establishes contract satisfiability.
The reference submitter reproduces full correctness without reading gold certificates,
ruling out oracle-only certificate injection.
The competent submitter adds an R1-style step-simulator workflow with auditable
reasoning logs and no oracle-module imports; it matches the other ceilings on C2 and F1
exploratory slices.
When exploratory models fail `certificate_valid_rate` while all three ceilings remain
at 1.0, remaining construct-validity concern shifts toward model-specific witness
construction rather than benchmark impossibility or hidden gold-certificate dependence.
Neither ceiling establishes human performance or frontier-model capability.
