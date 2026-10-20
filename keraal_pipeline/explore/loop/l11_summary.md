# L11 · 루프 결과 한 장 요약 (탐색) / one-page summary of L1–L7 (exploratory)

그림: `l11_summary.png` (주석자 A, CTK 정상 vs 오류 E1+E3). 사전 등록 확증 결과(H1–H3 지지 안 됨)는 그대로이고, 아래는 모두 그 뒤의 **탐색** 결과다.

## 핵심 메시지 / key messages

1. **연기 데이터로 배운 모델은 실제 녹화를 거의 다 오류로 판정한다** (L7, 그림 a). Rerr RF: 실제 정상의 89%를 오류로, 오류 판정 비율 92% vs 실제 41%.
   *The acted-trained model calls almost every real recording an error (92 % flagged vs 41 % true).*
2. **그래도 순위는 우연보다 낫다** (L1, 그림 b). Rerr AUC RF 0.674 · logreg 0.722 (참가자 안 순열 null 95% 0.629·0.673, p ≤ 0.002)인데 기준점 0.5의 Macro-F1은 0.404·0.493. 주석자 B도 같다.
   *It still ranks errors above chance; the decision cut-off is what fails.*
3. **실패의 모양은 "분포 전체의 이동"이다** (L2, 그림 c). 실제 정상의 P(오류) 중앙값 0.88로 연기 오류(0.85)보다 높다. 연기 데이터의 최적 기준점 0.55 vs 실제(oracle) 0.93.
   *Real "correct" recordings get the probabilities that acted errors get.*
4. **실제 → 실제는 된다** (L7, 그림 d). Macro-F1 0.54–0.78 vs 다수 클래스 0.33–0.36. 무너지는 것은 연기 → 실제 단계다.
   *Real-to-real works; only the acted-to-real step breaks.*
5. **카메라 보정만으로는 안 된다** (L3). 손목 높이 feature를 빼면 과잉 판정은 줄지만(92% → 82%, logreg F1 0.49 → 0.64) 실제 → 실제 성능도 같이 떨어진다.
   *Removing camera-sensitive height features trades the shift for lost information.*
6. **놓치는 것은 작은 오류** (L5, CTK). 큰 오류 recall이 더 높다(28개 조합 중 25개, 중앙값 +0.36; 큰 오류 5개뿐). ELK는 차이 없음.
7. **조심할 단서들** (L4, L6). "raw(R0)가 가장 좋다"는 RF에서만 나온다(로시니 R2 대기). 길이 단서는 사람 차이였고, G3 녹화는 실제보다 1.3–2배 짧다.

## 발표에서 쓰는 법 / how to use it in the talk
- 슬라이드 4(확증 실패): 그림 a. 슬라이드 6(원인): 그림 b·c. 슬라이드 5·7 사이: 그림 d.
- 한 문장: "연기 데이터로 배운 모델은 오류를 구분하는 능력은 남아 있지만, 판정 기준점이 실제 사람에게 맞지 않는다."
- 꼭 함께 말할 한계: 결과를 본 뒤의 탐색 분석, 시험 참가자 11명(2A 오류 4–5개), G3 3명, 1A 서서·G3 앉아서, 기준점 보정(R1)은 아직 진행 중.

## 그림의 수치 / numbers in the figure

(a) confusion (Rerr RF, A): true C → C 7, C → E 54, E → C 1, E → E 42

(b) | rep | model | AUC | null 95% | p | F1@0.5 |
|---|---|---|---|---|---|
| R0 | rf | 0.825 | 0.753 | 0.001 | 0.733 |
| R1 | rf | 0.619 | 0.642 | 0.189 | 0.340 |
| Rerr | rf | 0.674 | 0.629 | 0.002 | 0.404 |
| R0 | logreg(C=0.1) | 0.579 | 0.625 | 0.401 | 0.545 |
| R1 | logreg(C=0.1) | 0.729 | 0.686 | 0.001 | 0.615 |
| Rerr | logreg(C=0.1) | 0.722 | 0.673 | 0.001 | 0.493 |

(c) | set | class | n | q25 | median | q75 |
|---|---|---|---|---|---|
| G3 (OOF) | C | 45 | 0.271 | 0.326 | 0.378 |
| G3 (OOF) | E13 | 90 | 0.795 | 0.849 | 0.906 |
| 1A | C | 45 | 0.688 | 0.875 | 0.950 |
| 1A | E13 | 38 | 0.889 | 0.944 | 0.962 |
| 2A | C | 16 | 0.802 | 0.898 | 0.952 |
| 2A | E13 | 5 | 0.981 | 0.986 | 0.987 |

(d) 수치는 `l7_figures.md`의 사다리 표(주석자 A) / see the ladder table in `l7_figures.md`.
