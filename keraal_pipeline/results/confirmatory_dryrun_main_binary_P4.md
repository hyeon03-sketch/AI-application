# Confirmatory analysis — main_binary / P4

**DRY RUN on exploratory predictions (not the pre-registered protocol). Do not cite as a result.**

| task | model | role | H | test | n | observed | reference | p | p (Holm) | supported |
|---|---|---|---|---|---|---|---|---|---|---|
| CTK_C_vs_E13_A | rf | confirmatory | H1 | Rerr > permutation null | 83 | +0.669 | null mean 0.485, p95 0.577 | 0.0099 | 0.0297 | yes |
| CTK_C_vs_E13_A | rf | confirmatory | H2 | R1 > R0 | 83 | +0.040 | 95% CI [-0.006, +0.091] | 0.0500 | 0.1000 | no |
| CTK_C_vs_E13_A | rf | confirmatory | H3 | Rerr > R1 | 83 | -0.011 | 95% CI [-0.133, +0.113] | 0.5350 | 0.5350 | no |
| CTK_C_vs_E13_A | logreg(C=0.1) | robustness | H1 | Rerr > permutation null | 83 | +0.572 | null mean 0.480, p95 0.572 | 0.0891 | 0.2673 | no |
| CTK_C_vs_E13_A | logreg(C=0.1) | robustness | H2 | R1 > R0 | 83 | -0.211 | 95% CI [-0.260, -0.122] | 1.0000 | 1.0000 | no |
| CTK_C_vs_E13_A | logreg(C=0.1) | robustness | H3 | Rerr > R1 | 83 | +0.030 | 95% CI [-0.027, +0.087] | 0.1350 | 0.2700 | no |
| CTK_C_vs_E13_B | rf | sensitivity | H1 | Rerr > permutation null | 79 | +0.609 | null mean 0.475, p95 0.560 | 0.0198 | 0.0594 | no |
| CTK_C_vs_E13_B | rf | sensitivity | H2 | R1 > R0 | 79 | +0.063 | 95% CI [-0.016, +0.137] | 0.0400 | 0.0800 | no |
| CTK_C_vs_E13_B | rf | sensitivity | H3 | Rerr > R1 | 79 | -0.171 | 95% CI [-0.303, +0.030] | 0.9650 | 0.9650 | no |
| CTK_C_vs_E13_B | logreg(C=0.1) | sensitivity+robustness | H1 | Rerr > permutation null | 79 | +0.728 | null mean 0.484, p95 0.596 | 0.0099 | 0.0297 | yes |
| CTK_C_vs_E13_B | logreg(C=0.1) | sensitivity+robustness | H2 | R1 > R0 | 79 | +0.000 | 95% CI [-0.110, +0.108] | 0.5550 | 0.6900 | no |
| CTK_C_vs_E13_B | logreg(C=0.1) | sensitivity+robustness | H3 | Rerr > R1 | 79 | +0.002 | 95% CI [-0.043, +0.117] | 0.3450 | 0.6900 | no |
