# L7 · 발표용 그림의 표 쌍 / table twin of the L7 figures (탐색 그림, 확증 수치는 그대로)

## P1 confusion matrix (Rerr, 녹화별 seed 다수결) / rows = true, columns = predicted

| annotator | model | true C → C | true C → E13 | true E13 → C | true E13 → E13 | 오류 판정 비율 |
|---|---|---|---|---|---|---|
| A | logreg(C=0.1) | 20 | 41 | 11 | 32 | 0.70 |
| A | rf | 7 | 54 | 1 | 42 | 0.92 |
| B | logreg(C=0.1) | 21 | 42 | 8 | 30 | 0.71 |
| B | rf | 8 | 55 | 0 | 38 | 0.92 |

## Macro-F1 사다리 / ladder (seed 평균)

| annotator | model | protocol | R0 | R1 | Rerr | majority | P1 null 95% (Rerr) |
|---|---|---|---|---|---|---|---|
| A | rf | P4 | 0.640 | 0.680 | 0.669 | 0.328 | – |
| A | rf | P1 | 0.737 | 0.334 | 0.407 | 0.292 | 0.428 |
| A | logreg(C=0.1) | P4 | 0.753 | 0.542 | 0.572 | 0.328 | – |
| A | logreg(C=0.1) | P1 | 0.545 | 0.615 | 0.493 | 0.292 | 0.583 |
| B | rf | P4 | 0.718 | 0.781 | 0.609 | 0.363 | – |
| B | rf | P1 | 0.757 | 0.331 | 0.406 | 0.273 | 0.425 |
| B | logreg(C=0.1) | P4 | 0.726 | 0.726 | 0.728 | 0.363 | – |
| B | logreg(C=0.1) | P1 | 0.578 | 0.562 | 0.501 | 0.273 | 0.581 |
