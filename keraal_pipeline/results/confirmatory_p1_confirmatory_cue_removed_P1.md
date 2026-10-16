# Confirmatory analysis — p1_confirmatory_cue_removed / P1

| task | model | role | H | test | n | observed | reference | p | p (Holm) | supported |
|---|---|---|---|---|---|---|---|---|---|---|
| CTK_C_vs_E13_A | rf | confirmatory | H1 | Rerr > permutation null | 104 | +0.356 | null mean 0.324, p95 0.397 | 0.2627 | 0.7882 | no |
| CTK_C_vs_E13_A | rf | confirmatory | H2 | R1 > R0 | 104 | -0.357 | 95% CI [-0.512, -0.213] | 1.0000 | 1.0000 | no |
| CTK_C_vs_E13_A | rf | confirmatory | H3 | Rerr > R1 | 104 | -0.008 | 95% CI [-0.043, +0.011] | 0.7360 | 1.0000 | no |
| CTK_C_vs_E13_A | logreg(C=0.1) | robustness | H1 | Rerr > permutation null | 104 | +0.501 | null mean 0.423, p95 0.553 | 0.2038 | 0.4076 | no |
| CTK_C_vs_E13_A | logreg(C=0.1) | robustness | H2 | R1 > R0 | 104 | +0.108 | 95% CI [-0.023, +0.214] | 0.0495 | 0.1485 | no |
| CTK_C_vs_E13_A | logreg(C=0.1) | robustness | H3 | Rerr > R1 | 104 | -0.153 | 95% CI [-0.359, +0.000] | 0.9760 | 0.9760 | no |
| CTK_C_vs_E13_B | rf | sensitivity | H1 | Rerr > permutation null | 101 | +0.357 | null mean 0.306, p95 0.384 | 0.1828 | 0.5485 | no |
| CTK_C_vs_E13_B | rf | sensitivity | H2 | R1 > R0 | 101 | -0.378 | 95% CI [-0.514, -0.236] | 1.0000 | 1.0000 | no |
| CTK_C_vs_E13_B | rf | sensitivity | H3 | Rerr > R1 | 101 | -0.003 | 95% CI [-0.042, +0.020] | 0.6535 | 1.0000 | no |
| CTK_C_vs_E13_B | logreg(C=0.1) | sensitivity+robustness | H1 | Rerr > permutation null | 101 | +0.531 | null mean 0.407, p95 0.543 | 0.0749 | 0.2248 | no |
| CTK_C_vs_E13_B | logreg(C=0.1) | sensitivity+robustness | H2 | R1 > R0 | 101 | +0.065 | 95% CI [-0.107, +0.192] | 0.2210 | 0.4420 | no |
| CTK_C_vs_E13_B | logreg(C=0.1) | sensitivity+robustness | H3 | Rerr > R1 | 101 | -0.112 | 95% CI [-0.296, +0.037] | 0.9370 | 0.9370 | no |
