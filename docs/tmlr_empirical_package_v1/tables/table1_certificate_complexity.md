# Table 1: Certificate class complexity and Claude R1 success

| certificate_type | family | required_fields | canonical_hashing | multiple_valid_forms | complexity_score | Claude_R1_cert |
| --- | --- | --- | --- | --- | --- | --- |
| distinguishing_trace | F1 | 8 | False | True | 4.5 | 0.939 |
| equivalence_witness | F1 | 9 | True | False | 9.5 | 0.0 |
| trace_witness | C2 | 7 | False | True | 3.5 | 0.96 |
| unreachability_witness | C2 | 7 | False | False | 5.0 | 1.0 |