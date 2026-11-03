# 실험 성공 근거: 일반 카메라 1대로 재활 동작의 3D 모션캡처
# Evidence of success: 3D motion capture of rehab movements from one ordinary camera

2026-11-01 · Sonny (AI application 팀 / team) · 대상: 팀원, 교수님 / for: team members and the professor
자세한 보고서 / Full report: `Mocap3D_Research_Report_KR.pdf` · `Mocap3D_Research_Report_EN.pdf` · GitHub PR [#9](https://github.com/hyeon03-sketch/AI-application/pull/9)

---

## 한 줄 결론 / Bottom line

> **실험은 성공했고, 이 방향으로 계속 진행한다.** 스포츠 데이터(ASPset-510)에 재활 데이터(KERAAL)를 합쳐 학습하자, 학습에 쓰지 않은 새 참가자에서 일반 카메라 1대가 **Kinect 깊이 센서보다 정확한 관절 각도**를 냈다. 단, 학습과 시험이 같은 방·같은 카메라일 때의 결과다.
>
> **The experiment succeeded and we continue in this direction.** After merging rehab data (KERAAL) into sports training data (ASPset-510), one ordinary camera gave **more accurate joint angles than a Kinect depth sensor** on new participants never seen in training. This holds when training and testing share the same room and camera.

| | ASPset만 / ASPset only | **ASPset + KERAAL** | Kinect 센서 / sensor |
|---|---|---|---|
| 관절 위치 오차 / Joint-position error | 223 mm | **70 mm** | – |
| 관절 각도 상관 / Joint-angle correlation (r0) | 0.59 | **0.76** | 0.67 |
| 관절 각도 오차 / Joint-angle error (RMSE) | 20.3° | **13.9°** | 18.7° |
| 몸통 회전 운동 / Trunk rotation (RTK, r0) | 0.23 (실패 / fails) | **0.72** | 0.63 |

시드 3개 평균, 학습에 쓰지 않은 참가자에서 측정 / mean of 3 seeds, measured on held-out participants.

---

## 1. 실험의 흐름 / How we got here

| 단계 / Step | 한 일 / What we did | 알게 된 것 / What we learned |
|---|---|---|
| ① 목표 / Goal | 일반 카메라 영상(2D) → 3D 모션캡처, 재활 운동 평가에 사용 / 2D video → 3D motion capture for rehab assessment | – |
| ② 데이터 선정 / Datasets | 공개 데이터 12개를 조사 → **ASPset-510**(학습, CC0, 카메라 보정 있음)과 **KERAAL G3**(재활, Vicon 정답) 선택 / surveyed 12 datasets, chose ASPset-510 for training and KERAAL G3 for rehab testing | 학습 조건은 ASPset, 우리 주제는 KERAAL에 있음 / ASPset has what training needs; KERAAL has our domain |
| ③ 기준 모델 / Baseline | ASPset으로 2D→3D 모델 학습 / trained a 2D→3D model on ASPset | ASPset 안에서는 논문 수준 (PA-MPJPE 49 mm) / on par with the paper's baselines |
| ④ 재활 적용 / Apply to rehab | KERAAL에 그대로 적용 / applied it to KERAAL as is | **실패.** Kinect 수준에 머물렀고, 몸통 회전(RTK)은 안 됨 / **fails**: stuck at Kinect level, RTK fails |
| ⑤ 원인 찾기 / Diagnose | 학습 인원 3→13명 비교, 자세 분포 측정 / learning curve 3→13 subjects, pose coverage | 데이터 **양**이 아니라 **자세 종류**가 문제. KERAAL은 89%가 앉은 자세, ASPset은 13% / not data **volume** but pose **variety**: 89% seated in KERAAL vs 13% in ASPset |
| ⑥ 카메라 보정 / Calibrate | KERAAL에는 카메라 보정이 없어서 **Kinect를 다리로 사후 보정** / KERAAL has no calibration, so we **calibrated it post hoc through the Kinect** | 보정 오차 25 mm, 투영 오차 6 px. ASPset과 같은 형식의 3D 정답 확보 / 25 mm, 6 px; 3D GT in the ASPset format |
| ⑦ 합쳐 학습 / Merge | ASPset + KERAAL 참가자 2명으로 학습, 남은 1명으로 시험 (3번 반복, 시드 3개) / train on ASPset + 2 KERAAL participants, test on the 3rd (3 folds × 3 seeds) | **성공.** 위치 오차 223 → 70 mm, 각도에서 Kinect를 넘음 / **succeeds**: 223 → 70 mm, beats the Kinect on angles |

---

## 2. 성공이라고 말할 수 있는 근거 / Why we call it a success

1. **효과가 크다 / Large effect.** 위치 오차가 약 1/3로 줄었다 (223 → 70 mm). 가장 크게 좋아진 곳은 앉은 자세의 다리다 (발목 431 → 58 mm).
   *Position error drops to about a third; seated legs improved most (ankle 431 → 58 mm).*
2. **Kinect를 넘는다 / Beats the Kinect.** 관절 각도에서 참가자 3명 **모두** Kinect보다 좋았다. 모델은 같은 방·같은 카메라로 학습했고 Kinect는 그렇지 않으므로, 완전히 대등한 비교는 아니다.
   *Better than the Kinect on joint angles in **all** 3 participants. The model was trained in the same room with the same camera and the Kinect was not, so the comparison is not fully equal.*
3. **보정에 기대지 않는 지표로도 확인된다 / Confirmed by a calibration-independent metric.** 각도 지표는 우리가 만든 보정이 아니라 Vicon 마커의 회전(쿼터니언)에서 나온다. 보정이 틀렸어도 이 결과는 바뀌지 않는다.
   *The angle metric comes from Vicon marker rotations, not from our calibration, so it holds even if the calibration were off.*
4. **새 사람에게도 된다 / Works on new people.** 테스트 참가자는 학습에 한 번도 쓰지 않았다.
   *Test participants were never used in training.*
5. **우연이 아니다 / Not luck.** 시드 3개 × 참가자 3명 = 9번 모두에서 좋아졌다. 시드 간 차이는 0.8 mm로 작다.
   *Improved in all 9 seed × participant runs; between-seed SD is 0.8 mm.*
6. **원래 성능을 잃지 않는다 / No loss on the original domain.** ASPset 성능은 83.4 → 81.1 mm로 오히려 좋아졌다. KERAAL만으로 학습하면 ASPset에서 315 mm로 무너진다. 그래서 **합치는 것**이 답이다.
   *ASPset even improved (83.4 → 81.1 mm). KERAAL alone collapses on ASPset (315 mm), so **merging** is the answer.*
7. **이전의 실패를 설명한다 / Explains the earlier failure.** 몸통 회전(RTK) 실패는 단일 카메라의 한계가 아니라 학습 데이터에 그 동작이 없었기 때문이다 (r0 0.23 → 0.72).
   *The RTK failure was missing training data, not a single-camera limit.*

---

## 3. 아직 말할 수 없는 것 / What we cannot claim yet

| 한계 / Limit | 영향 / Effect | 확인 방법 / How we check |
|---|---|---|
| 테스트 참가자 3명, 건강인이 오류를 연기 / 3 healthy participants acting errors | 실제 환자에게도 되는지 모름 / unknown for real patients | **KERAAL 1A(환자) 영상에 적용해서 Kinect와 비교** / apply to KERAAL 1A patient videos |
| 학습과 시험이 같은 방·같은 카메라 / same room and camera | 다른 환경 일반화 미확인 / other settings untested | OpenCap 외부 데이터 / external data (OpenCap) |
| KERAAL 정답이 Kinect 관절 정의를 따름 / GT follows the Kinect joint definition | 위치 지표가 다소 유리할 수 있음 / position metric may be favoured | 기능적 관절 중심으로 정답 재구성 / rebuild GT with functional joint centres |
| 손목 오차가 큼 (약 150 mm) / wrist error still large | 손 동작 분석에 약함 / weak for hand movement | 위와 같음 / same as above |

이 한계들은 연구를 멈출 이유가 아니라 **주장의 범위**를 정하는 문제다. 결과가 나쁘게 나와도 범위를 좁혀 쓰면 된다.
*These limits set the **scope** of the claim; they are not reasons to stop. If a check fails, we narrow the claim.*

---

## 4. 다음 단계 / Next steps

| 순서 / Order | 할 일 / Task | 시기 / When |
|---|---|---|
| 1 | **KERAAL 1A(환자) 적용** — 가장 중요 / apply to 1A patients — top priority | 이번 주 / this week |
| 2 | 기능적 관절 중심으로 정답 재구성 / rebuild GT with functional joint centres | 다음 주 / next week |
| 3 | 합친 모델로 오류 판별 다시 실행 / rerun error detection with the merged model | 다음 주 / next week |
| 4 | OpenCap 외부 검증 / external check on OpenCap | 그다음 / after |
| 5 | 관절 → 회전(BVH) 출력 / joints → rotation (BVH) output | 그다음 / after |

---

## 5. 교수님께 여쭤볼 것 / Questions for the professor

1. 이 결과("재활 데이터를 사후 보정해서 합치면, 같은 환경에서 단일 카메라가 Kinect를 넘는다")를 논문의 핵심 주장으로 삼아도 될까요?
   *Can this, scoped to the same setting, be the paper's core claim?*
2. 1A에는 Vicon이 없어 환자의 3D 정확도는 잴 수 없고, 치료사 라벨에 대한 오류 판별로 평가합니다. 이 평가로 충분할까요?
   *1A has no Vicon, so patient 3D accuracy cannot be measured; we evaluate error detection against therapist labels. Is that sufficient?*
3. KERAAL 사후 보정 방법 자체를 기여로 넣어도 될까요?
   *Can the post-hoc KERAAL calibration count as a contribution?*

---

**재현 / Reproduce:** GitHub PR #9의 `members/sonny/mocap3d/pilot/` → `python run_pilot.py sample` (다운로드 없이 실행 / runs without downloads). KERAAL 데이터(CC BY-NC-SA)는 저장소에 없으므로, 합친 모델은 KERAAL을 받아 재현한다 / KERAAL is not in the repo; reproduce the merged model after obtaining it.
