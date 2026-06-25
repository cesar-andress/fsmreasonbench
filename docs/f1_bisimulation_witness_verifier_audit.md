# F1 bisimulation_witness Verifier Audit

Hostile audit of the constructible equivalence witness path (Experiment A1).

| ID | Title | Result | Detail |
|----|-------|--------|--------|
| A | Oracle bisimulation_witness passes | PASS | passed |
| B | Independently rebuilt witness passes | PASS | passed |
| C | Missing initial state pair fails | PASS | passed |
| D | Non-equivalent DFAs fail semantically | PASS | passed |
| E | Acceptance mismatch in pair fails | PASS | passed |
| F | Incomplete relation fails | PASS | passed |
| G | Swapped fsm_ids fails | PASS | passed |
| H | Malformed pairs payload fails | PASS | passed |
| I | Extra invalid unreachable pair fails | PASS | passed |
| J | Wrong certificate_type fails | PASS | passed |

**Summary:** 10/10 checks passed.

## Paper validity sentence

> An F1 bisimulation_witness is valid iff the benchmark DFAs are semantically equivalent and the submitter supplies a state-pair relation containing the initial pair, preserving acceptance on every pair, and closed under paired transitions on the shared alphabet — with no hash digest required.
