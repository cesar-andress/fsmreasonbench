# Reference Submitter Report

Comparison of the symbolic **oracle baseline** and the **reference submitter** on
frozen exploratory cohorts (`v0.1-exploratory`).

## Interpretation

| Ceiling | Meaning |
|---------|---------|
| **Oracle** | The certificate contract is **satisfiable** on every item; the verifier
accepts oracle-built witnesses. |
| **Reference submitter** | The contract is **achievable without oracle certificate
injection**: an independent reasoning workflow computes verdicts from the supplied FSMs,
builds certificates through the public submission schema, and passes the same
parser/scorer path as models. |

This does **not** establish human performance or frontier-model performance.
It narrows the remaining construct-validity ambiguity: when models fail
`certificate_valid_rate` but both ceilings are 1.0, failures are unlikely to be
explained solely by contract unsatisfiability or by oracle-only certificate injection.

## Results

| cohort | family | system | n | extract | verdict | cert | full |
|--------|--------|--------|--:|--------:|--------:|-----:|-----:|
| `c2-reachability-level3-v0.1-exploratory` | C2 | oracle | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `c2-reachability-level3-v0.1-exploratory` | C2 | reference_submitter | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `f1-mixed-level3-v0.1-exploratory` | F1 | oracle | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `f1-mixed-level3-v0.1-exploratory` | F1 | reference_submitter | 20 | 1.000 | 1.000 | 1.000 | 1.000 |

## Contract achievability

On both frozen exploratory cohorts, `reference_submitter` achieves
`fully_correct_rate = 1.0`, matching the oracle ceiling.
The certificate contract is therefore achievable through a non-oracle workflow
that never reads `answer_key.certificate`.

## Suggested paper paragraph

The symbolic oracle ceiling establishes that the certificate contract is satisfiable
on every evaluated item and that the verifier accepts correct witnesses.
The reference submitter reproduces that outcome using only evaluatee-visible FSMs:
it computes verdicts with independent decision procedures, constructs certificates
through the same public submission schema used by models, and is scored by the
standard parser and verifier pipeline without reading gold certificates.
When oracle and reference submitter both reach `fully_correct_rate = 1.0` while
exploratory models do not, contract unsatisfiability and oracle certificate injection
are ruled out as explanations for model `certificate_invalid` outcomes; remaining
ambiguity concerns model-specific witness construction rather than benchmark
impossibility.
Neither ceiling establishes human or frontier-model performance.
