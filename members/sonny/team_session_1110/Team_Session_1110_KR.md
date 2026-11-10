# 11/10 팀 시간 준비: Euijin 문서 평가, 이번 주 모델 완성 여부, 오늘 할 일

2026-11-10 · 작성: Sonny · 대상 문서: `mocap3d_verification_1110.md` (Euijin)

> KERAAL에서 나온 데이터·가중치는 CC BY-NC-SA라서 팀 안에서만 공유하고 GitHub에 올리지 않는다. 이 문서에는 집계 숫자만 있다.

---

## 0. 결론

1. **Euijin 문서는 오늘 회의의 뼈대로 쓸 만하다.** 우리에게 없던 두 가지, 즉 외부 공개 모델과의 비교 설계(MotionBERT)와 평가 매트릭스를 준다. 다만 11/6 공유 묶음 기준이라 최신 모델(REHAB24 포함)과 11/10 후속 실험이 빠져 있어, 매트릭스의 절반은 이미 숫자가 있다.
2. **모델은 이번 주에 "고정"할 수 있다.** 학습 방법은 정해졌고 가중치도 있다. 남은 것은 시드 3개 확인(오늘 15시경 끝남)뿐이다. 이번 주에 못 고치는 약점 3가지는 한계로 적는다(2절).
3. **오늘 팀 시간에는 결정 4개와 역할 분배를 한다**(3절). MotionBERT 비교는 오늘 시작하면 이번 주 안에 끝낼 수 있다.

---

## 1. Euijin 문서 평가

### 1.1 도움이 되는 점

| 내용 | 왜 도움이 되는가 |
|---|---|
| 핵심 결과를 원자료에서 다시 계산해 재현 (2절) | 만든 사람이 아닌 팀원이 확인했으므로 발표·논문에서 "독립 재현"이라고 쓸 수 있다 |
| 주장의 범위 정리 (3.3절) | "Kinect보다 낫다"는 Vicon 정답 학습일 때만, 각도 변화의 모양에 대해서만, 같은 방·같은 운동에서만 성립한다. 발표 문장을 이대로 쓰면 된다 |
| MotionBERT를 고른 이유 (4절) | 같은 2D→3D 방식이라 차이를 학습 데이터 효과로 읽을 수 있다. 지금까지 우리 비교 대상은 Kinect와 2D 각도뿐이었다 |
| 평가 매트릭스 (7절) | 정확도·안정성·오류 판별·비용을 한 표로 묶어 최종 결과 표의 틀이 된다 |

### 1.2 문서가 놓친 것 (이미 해 둔 일)

문서는 11/6 묶음(`share_merge_1106.zip`, `pr11_results.zip`)만 보고 썼다. 그 뒤에 나온 것:

| 매트릭스 축 | 이미 있는 결과 | 출처 |
|---|---|---|
| A 각도 정확도 | 최신 모델 참가자별: r0 0.68 / 0.74 / 0.84, RMSE 13.1 / 12.4 / 15.2° (Kinect 19.0 / 17.5 / 19.6°) | `km/kin_w_r24`, 시드 0 |
| B 위치 정확도 | G3 MPJPE 53 / 63 / 63 mm, REHAB24 시험 60 mm. 깊이 오차 38 mm (Kinect 23 mm) | 11/8 실행, 11/10 후속 E2 |
| C 시간 안정성 | 속도 오차 MPJVE 7.0 (Kinect 11.5), 떨림 5.1 (Vicon 4.0) | 11/10 후속 E1 |
| D 오류 판별 | 랜덤 포레스트 AUC 0.85 (Kinect 0.81, 10/27 모델). 학습 없는 DTW: CTK 0.73, RTK 0.70, ELK 0.52 | `keraal_errors.py`, 11/10 후속 E3 |
| E 계산 비용 | **없음** | 새로 재야 함 |
| MotionBERT, MediaPipe 행 | **없음** | 새로 해야 함 |

따라서 새로 할 일은 **MotionBERT(와 선택으로 MediaPipe)를 같은 절차로 돌리는 것**과 **계산 비용 측정** 두 가지다. 나머지 칸은 기존 숫자를 옮기면 된다.

### 1.3 "확인이 필요한 점"(3.5절)에 대한 답

| Euijin의 질문 | 오늘 확인한 답 |
|---|---|
| 관절 가중치가 시험 참가자를 포함해 누수가 생기는가 | **누수 없음.** 교차검증 실행은 가중치를 학습 참가자 2명만으로 계산한다(`km_train.py` 170행, 실행 로그의 가중치가 폴드마다 다름). `kinect_joint_weights_P1P2P3.npy`는 전원으로 학습하는 배포용 모델에만 쓰인다. G3 58.5 mm는 깨끗한 값이다 |
| 최종 모델이 시드 1개뿐 | 시드 1·2를 오늘 돌리는 중(약 15시 완료). P1P2→P3는 시드 1이 이미 있다: 51.8 mm (시드 0은 53.1) |
| 1A 환자가 1B에 섞여 있는가 | **배제할 수 없고, 섞여 있을 가능성이 높다.** 같은 녹화 파일은 없다(내용이 같은 파일 0개). 하지만 Kinect 뼈 길이로 1A 환자를 90–93% 맞힐 수 있고(우연 33%), 학습에 쓴 1B 녹화 150개 중 102개가 1A 환자의 체격 범위 안에 든다. 체격만으로는 같은 사람이라고 단정할 수 없다 (`kinect_merge/overlap_1a_1b.py`) |
| 효과 크기 +0.11 / −7.9°와 +0.09 / −5.9°의 차이 | +0.11 / −7.9°는 `MERGE_REPORT` 146행의 시드 0 값이다. 계산 단위가 달라서 생긴 차이인지는 **아직 다시 계산하지 않았다.** 앞으로는 Euijin 방식(녹화×각도별 차이의 평균, 시드 3개)을 쓰고 방식을 함께 적는다 |

**1A에 대한 결론:** 최종 모델의 1A 숫자(Kinect와 61 mm)는 "처음 보는 환자" 결과라고 쓰면 안 된다. 1A는 Vicon도 없으므로, 주 평가는 G3 교차검증 하나로 한다.

### 1.4 비교 설계에서 보완할 점

- **기준 모델을 최신으로 바꾼다.** M5는 "ASPset + KERAAL Vicon"(11/6)이 아니라 현재 최종 방법(ASPset + KERAAL G3 + Kinect 그룹 + REHAB24)이어야 한다. 11/6 모델은 M5a로 남겨 둔다.
- **해석 문장을 미리 정한다.** MotionBERT는 KERAAL을 본 적이 없고 우리 모델은 같은 방의 다른 참가자를 봤다. 차이가 나도 "모델 구조가 낫다"가 아니라 "같은 환경의 재활 데이터가 필요하다"로만 읽는다.
- **위치 오차는 보조 지표로만 쓴다.** MotionBERT 관절 정의(Human3.6M)는 우리 정답(Kinect 정의)과 달라서 PA-MPJPE가 불리하게 나온다. 주 지표를 r0와 평균 제거 RMSE로 둔 문서의 선택이 맞다.
- **실행은 Sonny 컴퓨터에서 한다.** G3 영상과 검출 결과는 KERAAL 파생물이고 GPU도 여기 있다. Euijin은 변환 규칙과 각도 절차를 정하고, 결과 표를 검증한다.

---

## 2. 이번 주 안에 모델을 완성할 수 있는가

**"완성"을 "방법과 가중치를 고정하고 숫자를 확정하는 것"으로 정하면 가능하다.**

| 항목 | 상태 |
|---|---|
| 학습 방법 | 확정: ASPset + KERAAL G3(Vicon) + Kinect 그룹(2A, 2B, 1B) + REHAB24, 정의 표시 채널, 관절 가중치 |
| 가중치 | 있음: `km/final_r24/run_P1P2P3_s0/best.pt` |
| 처음 보는 참가자 정확도 | 53 / 63 / 63 mm, 각도 RMSE 12.4–15.2° (Kinect 17.5–19.6°) |
| 서 있는 사람 | 해결: REHAB24 시험 60 mm (이전 모델 220 mm) |
| 시드 3개 | 진행 중, 오늘 약 15시 완료 |
| 데모 | 있음: `demo_rehab.py`, 1A·G3·서 있는 사람 영상 |

**이번 주에 고치지 못하는 것 (한계로 적는다)**

1. 몸통 회전(RTK)의 깊이 오차가 44 mm로 가장 크다. 카메라 한 대의 한계에 가깝다.
2. ELK 운동의 오류 판별은 모든 방법이 우연 수준이다(AUC 0.52). 모델이 아니라 라벨과 운동 특성 문제다.
3. Vicon 정답이 있는 참가자가 3명뿐이고 모두 건강인이다. 환자 데이터(1A)는 깨끗한 평가가 안 된다(1.3절).

**이번 주 일정 제안**

| 날짜 | 할 일 |
|---|---|
| 11/10 (월, 오늘) | 결정 4개, 역할 분배. 시드 3개 결과 확인. 관절 대응표 확정 |
| 11/11–12 | 모델 고정. MotionBERT로 G3 540개 녹화 3D 추출, 같은 절차로 각도 계산 |
| 11/13–14 | 매트릭스 채우기(계산 비용 포함), 최신 모델로 오류 판별 다시 실행 |
| 11/15–16 | 결과 표·그림 정리, 본인 영상 데모, 발표 흐름 |

모델을 더 좋게 만드는 실험은 이번 주에 넣지 않는다. 11/3 실험에서 학습 설정 9가지를 바꿔도 2 mm 이하로만 움직였다. 남은 시간은 비교와 설명에 쓰는 편이 낫다.

---

## 3. 오늘 팀 시간에 할 일 (약 40분)

### 3.1 결정할 것

| 번호 | 결정 | 제안 |
|---|---|---|
| D0 | 최종 모델을 지금 방법으로 고정할까 | 예. 시드 3개가 ±2 mm 안이면 고정 |
| D1 | Euijin의 평가 매트릭스를 최종 결과 표로 채택할까 | 예. 주 지표는 r0와 평균 제거 RMSE, 나머지는 보조. 1.2절의 기존 숫자를 먼저 채운다 |
| D2 | 비교 모델 범위 | MotionBERT는 필수, MediaPipe 3D는 시간이 남으면, WHAM·NLF는 하지 않는다 |
| D3 | 1A를 어떻게 쓸까 | 정량 평가에서 빼고 데모와 정성 예시로만 쓴다 |

기존 회의 자료(`Team_Meeting_1111_EN.pdf`)의 결정 3개(매끄럽게 하는 필터, 반복 단위 피드백만 주장, UCO 데이터 요청)도 같이 정한다.

### 3.2 역할 제안

| 팀원 | 할 일 | 결과물 |
|---|---|---|
| Euijin (데이터) | COCO-17 → MotionBERT 입력 관절 대응표, 각도 정의 3개의 관절 번호 확정. 결과 표 검증 | 대응표 1장, 채운 매트릭스 검토 |
| Sonny | MotionBERT 설치·실행(G3 전체), 각도 계산, 시드 3개 정리, 계산 비용 측정 | 모델별 녹화×각도 원자료, 매트릭스 초안 |
| Roshini (프로그래밍) | 최신 가중치로 오류 판별(`keraal_errors.py`) 다시 실행, 본인 영상 데모 | AUC 표, 데모 영상 1개 |
| Joshi | 이 문서와 Euijin 문서를 읽고 이해 안 되는 표현 표시 (코딩 없음) | 표시한 목록 |

### 3.3 오늘 자리에서 바로 할 수 있는 작업

1. Euijin과 관절 대응표를 같이 확정한다(15분이면 된다). 이것만 정해지면 MotionBERT 실행을 시작할 수 있다.
2. 매트릭스 빈 표를 만들고 1.2절 숫자를 옮겨 적는다.
3. Roshini가 새 가중치로 데모를 한 번 돌려 본다.

---

## 4. Euijin이 Sonny에게 요청한 4가지

| 요청 | 상태 |
|---|---|
| G3 YOLO 검출 결과 (crop 포함) | 있음. `E:\KERAAL_mocap3d\share_1110_g3_det.zip`에 묶어 둠. 팀 안에서만 전달 |
| 1B 참가자 목록 | 데이터셋에 없음. 체격 비교 결과는 1.3절. 확실한 답은 KERAAL 저자에게 물어야 함 |
| 최종 모델 시드 3개 결과 | 오늘 약 15시 완료 후 이 문서에 추가 |
| 시험 참가자를 뺀 관절 가중치 | 교차검증에서 이미 그렇게 계산됨. 폴드별 값은 `km/kin_w_r24/*.log`에 있음 |

---

## 5. 오늘 진행 가능한 일과 파일 위치

학습(시드 1·2)이 끝나기 전에도 아래는 모두 바로 할 수 있다. GPU는 학습이 쓰고 있으므로 MotionBERT 실행만 학습 뒤로 미룬다.

| 오늘 가능한 일 | 필요한 것 | 지금 가능한가 |
|---|---|---|
| 결정 D0–D3와 역할 분배 | 이 문서, 회의 자료 | 가능 |
| 관절 대응표 확정 (Euijin + Sonny) | Euijin 문서 6.1절 | 가능 |
| 매트릭스에 기존 숫자 옮겨 적기 | 1.2절 숫자 | 가능 |
| 새 가중치로 데모 실행 (Roshini) | 최종 가중치, `demo_rehab.py` | 가능 (Sonny 컴퓨터에서) |
| G3 검출 결과 전달 | 묶음 파일 | 가능 (팀 안에서만) |
| 시드 3개 결과 확인 | 학습 완료 | 약 15시 이후 |
| MotionBERT 실행 | 코드·가중치 내려받기, GPU | 학습이 끝난 뒤, 내려받기 승인 후 |

**파일 위치**

수업 폴더: `C:\Users\user\Desktop\SOn H.g\class materials\AI application\`

| 파일 | 경로 (수업 폴더 기준) |
|---|---|
| 이 문서 | `Team_Session_1110_KR.md` |
| Euijin 검증 문서 | `mocap3d_verification_1110.md` |
| 회의 자료 (안건, 결정 3개, 역할) | `Team_Meeting_1111_EN.pdf` |
| 후속 실험 보고서 | `Paper_Followup_Experiments_EN.pdf` |
| 학습 코드 | `members\sonny\mocap3d\kinect_merge\km_train.py` |
| 시드 1·2 실행 스크립트 | `members\sonny\mocap3d\kinect_merge\run_1110.ps1` |
| 1A/1B 체격 비교 | `members\sonny\mocap3d\kinect_merge\overlap_1a_1b.py` |
| 데모 코드 | `members\sonny\mocap3d\kinect_merge\demo_rehab.py` |
| 오류 판별 코드 | `members\sonny\mocap3d\keraal_errors.py` |

데이터와 결과 (GitHub에 올리지 않음): `E:\KERAAL_mocap3d\`

| 내용 | 경로 |
|---|---|
| 최종 가중치 | `E:\KERAAL_mocap3d\km\final_r24\run_P1P2P3_s0\best.pt` |
| 교차검증 결과 (시드 0, 시드 1·2는 완료되면 같은 폴더) | `E:\KERAAL_mocap3d\km\kin_w_r24\` |
| G3 YOLO 검출 결과 묶음 (일반 540개 + crop 540개, 48 MB) | `E:\KERAAL_mocap3d\share_1110_g3_det.zip` |
| 1A/1B 체격 비교 결과 | `E:\KERAAL_mocap3d\km\overlap_1a_1b.json` |
| Euijin이 확인한 11/6 묶음 | `E:\KERAAL_mocap3d\share_merge_1106.zip`, `E:\KERAAL_mocap3d\share_1106\pr11_results` |
| 데모 영상 | `E:\KERAAL_mocap3d\km\demo_r24_1a`, `demo_r24_g3_P3`, `demo_r24_standing` |

---

## 6. 팀에 보낼 문장 (영어)

> Thanks Euijin, the verification doc is very useful and I'd like to use it as the frame for today's session. Three updates: (1) No leak in the joint weights: every leave-one-out run computes them from the two training participants only; the P1P2P3 file is just for the deployment model. (2) The bundles you checked are from Nov 6. The current final model also uses REHAB24 (G3 53/63/63 mm, standing people fixed), and several cells of your matrix already have numbers from the Nov 10 follow-up (smoothness, depth error, error detection). (3) 1A/1B: no shared recordings, but body size suggests the 1A patients are probably in 1B too, so I propose we drop 1A from the quantitative evaluation. Today I'd like us to agree on: freezing the model, adopting your matrix as the final results table, and running MotionBERT this week. I can run it on my machine since the videos must stay local; could you fix the COCO-17 to MotionBERT joint mapping with me today?
