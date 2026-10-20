# L4 · RF와 logreg가 표현 비교에서 같은 결론을 내는가 (탐색) / model agreement (exploratory)

Macro-F1(P1 AUC는 L1) 차이 a − b의 부호를 두 모델에서 비교. |차이| < 0.02는 무승부. 새로 학습한 모델은 없다(기존 결과 표만 사용).

## 판정 개수 / verdict counts

| protocol | agree | tie | one-sided | flip | 합 |
|---|---|---|---|---|---|
| P1 | 2 | 0 | 1 | 3 | 6 |
| P1 (AUC) | 0 | 0 | 2 | 4 | 6 |
| P4 | 43 | 2 | 22 | 17 | 84 |

## 표현 순위의 일치 / ranking agreement

| protocol | task | reps | Spearman ρ | best RF | best logreg |
|---|---|---|---|---|---|
| P4 | ELK_C_vs_E2_A | 7 | +0.93 | R0 | R0 |
| P4 | ELK_C_vs_E2_B | 7 | +0.21 | R0 | Rerr |
| P4 | CTK_C_vs_E13_A | 7 | -0.43 | R1 | R0 |
| P4 | CTK_C_vs_E13_B | 7 | +0.76 | R1 | Rerr_d |
| P1 | CTK_C_vs_E13_A | 3 | -0.50 | R0 | R1 |
| P1 | CTK_C_vs_E13_B | 3 | +0.50 | R0 | R0 |
| P1 (AUC) | CTK_C_vs_E13_A | 3 | -1.00 | R0 | R1 |
| P1 (AUC) | CTK_C_vs_E13_B | 3 | -0.50 | R0 | Rerr |

## 주요 쌍 / key pairs (R0, R1, R4, Rerr)

| protocol | task | a | b | a−b RF | a−b logreg | verdict |
|---|---|---|---|---|---|---|
| P4 | ELK_C_vs_E2_A | R0 | R1 | +0.059 | +0.165 | agree |
| P4 | ELK_C_vs_E2_A | R0 | R4 | +0.399 | +0.330 | agree |
| P4 | ELK_C_vs_E2_A | R0 | Rerr | +0.364 | +0.388 | agree |
| P4 | ELK_C_vs_E2_A | R1 | Rerr | +0.305 | +0.222 | agree |
| P4 | ELK_C_vs_E2_B | R0 | R1 | +0.202 | -0.121 | flip |
| P4 | ELK_C_vs_E2_B | R0 | R4 | +0.228 | +0.025 | agree |
| P4 | ELK_C_vs_E2_B | R0 | Rerr | +0.208 | -0.283 | flip |
| P4 | ELK_C_vs_E2_B | R1 | Rerr | +0.006 | -0.162 | one-sided |
| P4 | CTK_C_vs_E13_A | R0 | R1 | -0.040 | +0.211 | flip |
| P4 | CTK_C_vs_E13_A | R0 | R4 | +0.138 | +0.170 | agree |
| P4 | CTK_C_vs_E13_A | R0 | Rerr | -0.028 | +0.181 | flip |
| P4 | CTK_C_vs_E13_A | R1 | Rerr | +0.011 | -0.030 | one-sided |
| P4 | CTK_C_vs_E13_B | R0 | R1 | -0.063 | +0.000 | one-sided |
| P4 | CTK_C_vs_E13_B | R0 | R4 | +0.220 | +0.108 | agree |
| P4 | CTK_C_vs_E13_B | R0 | Rerr | +0.108 | -0.002 | one-sided |
| P4 | CTK_C_vs_E13_B | R1 | Rerr | +0.171 | -0.002 | one-sided |
| P1 | CTK_C_vs_E13_A | R0 | R1 | +0.403 | -0.069 | flip |
| P1 | CTK_C_vs_E13_A | R0 | Rerr | +0.330 | +0.052 | agree |
| P1 | CTK_C_vs_E13_A | R1 | Rerr | -0.073 | +0.121 | flip |
| P1 | CTK_C_vs_E13_B | R0 | R1 | +0.425 | +0.015 | one-sided |
| P1 | CTK_C_vs_E13_B | R0 | Rerr | +0.351 | +0.077 | agree |
| P1 | CTK_C_vs_E13_B | R1 | Rerr | -0.075 | +0.061 | flip |
| P1 (AUC) | CTK_C_vs_E13_A | R0 | R1 | +0.206 | -0.150 | flip |
| P1 (AUC) | CTK_C_vs_E13_A | R0 | Rerr | +0.151 | -0.143 | flip |
| P1 (AUC) | CTK_C_vs_E13_A | R1 | Rerr | -0.055 | +0.007 | one-sided |
| P1 (AUC) | CTK_C_vs_E13_B | R0 | R1 | +0.214 | -0.133 | flip |
| P1 (AUC) | CTK_C_vs_E13_B | R0 | Rerr | +0.178 | -0.151 | flip |
| P1 (AUC) | CTK_C_vs_E13_B | R1 | Rerr | -0.036 | -0.018 | one-sided |
