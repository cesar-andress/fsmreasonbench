# Uncertainty summary (bootstrap 95% CI + paired tests)

## F1 R1 subtype rates (descriptive; disjoint item subsets)

- Note: distinguishing_trace (n=49) and equivalence_witness (n=51) are disjoint item subsets; rates are reported with independent bootstrap CIs (descriptive).
- **distinguishing_trace_cert**: 0.939 [0.857, 1.000] (k=46/49)
- **equivalence_witness_cert**: 0.000 [0.000, 0.000] (k=0/51)

## C2 R1 subtype rates (descriptive)

- Note: trace_witness and unreachability_witness are disjoint balanced subsets (50+50); independent bootstrap CIs (descriptive).
- **trace_witness_cert**: 0.960 [0.900, 1.000] (k=48/50)
- **unreachability_witness_cert**: 1.000 [1.000, 1.000] (k=50/50)

## Paired condition comparisons (same item IDs)

### F1 R1 vs R2C (overall, n=100)
- McNemar p-value: 2.220446049250313e-16
- Cert rate diff CI: -0.530 [-0.630, -0.430]

### F1 R2A vs R2C (overall, n=100)
- McNemar p-value: 1.7763568394002505e-15
- Cert rate diff CI: -0.500 [-0.600, -0.400]

### F1 R2B vs R2C (overall, n=100)
- McNemar p-value: 8.881784197001252e-16
- Cert rate diff CI: -0.510 [-0.620, -0.420]

### F1 eq-witness R1 vs R2C (n=51 paired items)
- McNemar p-value: 1.7763568394002505e-15
- Cert rate diff CI: -0.980 [-1.000, -0.941]
