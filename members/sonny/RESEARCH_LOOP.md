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
| L4 | 완료 / done | 백로그 24: 표현 쌍별 RF·logreg 차이의 부호 일치 요약 / sign agreement across models | 결론의 강건성 / robustness |
| L5 | 완료 / done | 백로그 6: 심각도(Small/Large)별 recall / recall by severity | 작은 오류를 놓치는지 / are small errors missed? |
| L6 | 완료 / done | 백로그 20: 녹화 길이와 오류의 관계 / recording length vs error | 길이 단서 점검 / length cue check |
| L7 | 완료 / done | 백로그 26: P1 confusion matrix와 sim-to-real 사다리 그림 / P1 confusion matrix and ladder figure | 발표·논문 그림 / figures |
| L11 | 완료 / done | L1–L7 결과 한 장 요약(발표·보고서용 그림 묶음) / one-page summary of L1–L7 | 발표 준비 / presentation |
| L8 | 완료 / done | ELK·RTK로 L1 확장: 연기 → 실제 AUC와 오류 판정 비율 / extend L1 to ELK and RTK | 기준점 이동이 CTK만의 일인지 / is the shift CTK-only? |
| L9 | 완료 / done | 환자(1A) vs 건강인(2A) 확률 이동 비교: 같은 P1 모델에서 두 집단 정상의 P(E13) 차이 / patient vs healthy shift | 이동이 "환자라서"인지 "세션·장소 차이"인지 / patient effect or session effect? |
| L10 | 완료 / done | 주석자 A·B 일치도(Cohen κ, 운동별)를 성능 상한으로 / annotator agreement as a ceiling | 모델 점수를 어디까지 기대할 수 있나 / how high can a model go? |

## 회차 기록 / Tick log

- 2026-10-17 · L1 완료: Rerr RF AUC 0.674 (null 0.629, p 0.002) vs F1@0.5 0.404, 오류 판정 92% → 순위는 우연 이상, 기준점이 문제. RF R1은 null 미만, 2A는 오류 5개뿐. 결과 `keraal_pipeline/explore/loop/l1_acted_to_real_auc.md`
- 2026-10-17 · L2 완료: Rerr RF에서 실제 정상의 P(E13) 중앙값 0.88(G3 정상 0.33, G3 오류 0.85), 기준점 G3 0.55 vs 실제(oracle) 0.93. logreg R1은 이동 작음, RF R1은 구분 실패. 팀원 새 결과 없음. 결과 `keraal_pipeline/explore/loop/l2_probability_shift.{md,png}`
- 2026-10-17 · L3 완료: Rerr에서 손목 높이(vertical) 2개를 빼면 P1 오류 판정 0.92 → 0.82(RF), 0.70 → 0.48(logreg), F1 logreg 0.493 → 0.640. 하지만 P4도 떨어져(F1 0.650 → 0.552) 격차 축소의 절반은 성능 손실. R4는 변화 거의 없음. 팀원 새 결과 없음. 결과 `keraal_pipeline/explore/loop/l3_pitch_robust.md`
- 2026-10-17 · L4 완료: P4 표현 쌍 84개 중 두 모델 같은 방향 43, 반대 17. P1 R0 우위는 RF에서만(AUC R0−R1 RF +0.21, logreg −0.15) → R2 결과 대기. R0 > R4는 일관. 팀원 새 결과 없음. 결과 `keraal_pipeline/explore/loop/l4_model_agreement.md`
- 2026-10-18 · L5 완료: CTK는 Large recall > Small(P4 28개 중 25, 중앙값 +0.36; 단 Large 5개), ELK는 차이 없음(중앙값 −0.03). 팀원 새 결과 없음, 조시 초대 대기. 결과 `keraal_pipeline/explore/loop/l5_severity_recall.md`
- 2026-10-18 · L6 완료: G3 녹화가 실제보다 1.3–2배 짧음. CTK 길이만 P4 F1 0.73–0.77이지만 AUC가 사람 안 순열 null 미달 → 사람 수준 교란. P1에서는 길이 무용. 팀원 새 결과 없음. 결과 `keraal_pipeline/explore/loop/l6_length.md`
- 2026-10-18 · L7 완료: P1 confusion matrix(RF가 실제 정상 89%를 오류로)와 P4 vs P1 사다리 그림. 대기열 비었음 → L8–L11 제안(Sonny 승인 후 '대기'로). 팀원 새 결과 없음. 결과 `keraal_pipeline/explore/loop/l7_*`
- 2026-10-18 · Sonny 승인: L11 → L8 순서로 대기. L9·L10은 제안 유지.
- 2026-10-18 · L11 완료: 4칸 요약 그림 + 핵심 메시지 7개(한/영)와 발표 사용법. 다음은 L8. 결과 `keraal_pipeline/explore/loop/l11_summary.{png,md}`
- 2026-10-18 · L8 완료: RTK도 CTK처럼 순위는 null 이상(Rerr RF AUC 0.922)·과잉 판정(47–86% vs 12–36%). ELK는 과잉 판정 없음. → 기준점 이동은 3개 운동 중 2개. 대기열 비었음(L9·L10 제안 유지). 결과 `keraal_pipeline/explore/loop/l8_other_exercises.md`
- 2026-10-18 · L9 완료(Sonny 승인): CTK는 건강인 2A 정상도 환자만큼 밀림(Rerr RF 0.90 vs 0.88, G3 0.33, p ≥ 0.42) → 세션 효과. RTK는 일부 환자 효과(Rerr RF A p 0.039)지만 장소와 구분 불가. 한계 6개 명시. 결과 `keraal_pipeline/explore/loop/l9_patient_vs_session.md`
- 2026-10-19 · L10 완료(Sonny 승인): κ(A,B) CTK 0.60·ELK 0.41·RTK 0.28, 사람 상한 Macro-F1 0.62·0.68·0.40. CTK는 모델이 한참 아래(0.33–0.42), ELK·RTK는 모델이 상한에 닿지만 다른 주석자 기준 κ 급락 → 주석자 습관 학습. ELK·RTK의 A·B 일치는 사람 단위(null과 같음). 팀원 새 결과 없음. 결과 `keraal_pipeline/explore/loop/l10_annotator_ceiling.md`
