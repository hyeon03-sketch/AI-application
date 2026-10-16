# Confirmatory analysis — p1_confirmatory / P1

| task | model | role | H | test | n | observed | reference | p | p (Holm) | supported |
|---|---|---|---|---|---|---|---|---|---|---|
| CTK_C_vs_E13_A | rf | confirmatory | H1 | Rerr > permutation null | 104 | +0.407 | null mean 0.345, p95 0.428 | 0.1429 | 0.2857 | no |
| CTK_C_vs_E13_A | rf | confirmatory | H2 | R1 > R0 | 104 | -0.403 | 95% CI [-0.581, -0.210] | 1.0000 | 1.0000 | no |
| CTK_C_vs_E13_A | rf | confirmatory | H3 | Rerr > R1 | 104 | +0.073 | 95% CI [+0.000, +0.148] | 0.0940 | 0.2820 | no |
| CTK_C_vs_E13_A | logreg(C=0.1) | robustness | H1 | Rerr > permutation null | 104 | +0.493 | null mean 0.451, p95 0.583 | 0.3367 | 0.6733 | no |
| CTK_C_vs_E13_A | logreg(C=0.1) | robustness | H2 | R1 > R0 | 104 | +0.069 | 95% CI [-0.099, +0.206] | 0.2135 | 0.6405 | no |
| CTK_C_vs_E13_A | logreg(C=0.1) | robustness | H3 | Rerr > R1 | 104 | -0.122 | 95% CI [-0.234, -0.035] | 0.9975 | 0.9975 | no |
| CTK_C_vs_E13_B | rf | sensitivity | H1 | Rerr > permutation null | 101 | +0.406 | null mean 0.330, p95 0.425 | 0.1149 | 0.2820 | no |
| CTK_C_vs_E13_B | rf | sensitivity | H2 | R1 > R0 | 101 | -0.425 | 95% CI [-0.622, -0.222] | 1.0000 | 1.0000 | no |
| CTK_C_vs_E13_B | rf | sensitivity | H3 | Rerr > R1 | 101 | +0.074 | 95% CI [+0.000, +0.147] | 0.0940 | 0.2820 | no |
| CTK_C_vs_E13_B | logreg(C=0.1) | sensitivity+robustness | H1 | Rerr > permutation null | 101 | +0.501 | null mean 0.440, p95 0.581 | 0.2687 | 0.8062 | no |
| CTK_C_vs_E13_B | logreg(C=0.1) | sensitivity+robustness | H2 | R1 > R0 | 101 | -0.016 | 95% CI [-0.199, +0.117] | 0.6010 | 1.0000 | no |
| CTK_C_vs_E13_B | logreg(C=0.1) | sensitivity+robustness | H3 | Rerr > R1 | 101 | -0.061 | 95% CI [-0.174, +0.027] | 0.9055 | 1.0000 | no |
