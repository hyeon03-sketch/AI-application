# 2시간 연구 루프 작업표 / 2-hour research loop queue

Sonny가 요청한 자동 탐색 분석. 회차마다 아래 대기열에서 맨 위 "대기" 항목 하나를 진행한다.
Automated exploratory analyses requested by Sonny. Each tick takes the top "queued" item.

- 모든 결과는 **탐색(exploratory)**. 확증 설정 `configs/p1_confirmatory.json`은 건드리지 않는다.
- 팀원 과제(R1–R4, U1–U4)는 하지 않는다. 겹치면 건너뛴다.
- 결과는 `keraal_pipeline/explore/loop/`와 `PROGRESS.md`에, 커밋은 브랜치 `sonny/research-loop`의 PR 하나에 쌓는다. merge는 팀원 승인 후.

## 대기열 / Queue

| # | 상태 / Status | 과제 / Item | 왜 / Why |
|---|---|---|---|
| L1 | 완료 / done | 연기 → 실제 방향의 AUC (G3로 학습한 RF·logreg의 확률로 1A·2A AUC, 주석자 A·B) / AUC for the acted → real direction | 기준점 가설: AUC가 높고 F1만 낮으면 "구분은 되고 기준점만 다르다" / threshold story: high AUC with low F1 = ranking works, threshold differs |
| L2 | 완료 / done | 확률 분포 비교: G3 학습 모델이 1A·2A 정상/오류에 주는 확률 분포와 최적 기준점 위치 / predicted-probability distributions and best threshold | L1의 그림 근거 / figure for L1 |
| L3 | 완료 / done | 백로그 13: pitch에 강한 feature만 vs 전체 R4, sim-to-real 격차 / pitch-robust features vs full R4 | 카메라 자세 차이가 원인인지 / is camera pose the cause? |
| L4 | 대기 / queued | 백로그 24: 표현 쌍별 RF·logreg 차이의 부호 일치 요약 / sign agreement across models | 결론의 강건성 / robustness |
| L5 | 대기 / queued | 백로그 6: 심각도(Small/Large)별 recall / recall by severity | 작은 오류를 놓치는지 / are small errors missed? |
| L6 | 대기 / queued | 백로그 20: 녹화 길이와 오류의 관계 / recording length vs error | 길이 단서 점검 / length cue check |
| L7 | 대기 / queued | 백로그 26: P1 confusion matrix와 sim-to-real 사다리 그림 / P1 confusion matrix and ladder figure | 발표·논문 그림 / figures |

## 회차 기록 / Tick log

- 2026-10-17 · L1 완료: Rerr RF AUC 0.674 (null 0.629, p 0.002) vs F1@0.5 0.404, 오류 판정 92% → 순위는 우연 이상, 기준점이 문제. RF R1은 null 미만, 2A는 오류 5개뿐. 결과 `keraal_pipeline/explore/loop/l1_acted_to_real_auc.md`
- 2026-10-17 · L2 완료: Rerr RF에서 실제 정상의 P(E13) 중앙값 0.88(G3 정상 0.33, G3 오류 0.85), 기준점 G3 0.55 vs 실제(oracle) 0.93. logreg R1은 이동 작음, RF R1은 구분 실패. 팀원 새 결과 없음. 결과 `keraal_pipeline/explore/loop/l2_probability_shift.{md,png}`
- 2026-10-17 · L3 완료: Rerr에서 손목 높이(vertical) 2개를 빼면 P1 오류 판정 0.92 → 0.82(RF), 0.70 → 0.48(logreg), F1 logreg 0.493 → 0.640. 하지만 P4도 떨어져(F1 0.650 → 0.552) 격차 축소의 절반은 성능 손실. R4는 변화 거의 없음. 팀원 새 결과 없음. 결과 `keraal_pipeline/explore/loop/l3_pitch_robust.md`
