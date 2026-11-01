# 결과 / Results — 2D 영상 → 3D 모션캡처

실행 / Run: 2026-10-26 (밤샘 / overnight) · Sonny · 모든 결과는 탐색(exploratory) / all results exploratory
전체 표 / Full tables: [`summary_tables.md`](summary_tables.md) · 설계 / Design: [`RESEARCH_DESIGN.md`](RESEARCH_DESIGN.md)

## 1. 핵심 결과 / Key findings

1. **ASPset 안에서 기준 성능 (RQ1).** 검출 2D → 3D, test MPJPE 83mm / PA-MPJPE 49mm (평균 자세 227 / 161mm). 정답 2D 입력이면 73–77 / 41–47mm.
   *In-domain baseline: detected 2D → 3D gives 83 / 49 mm (mean pose 227 / 161).*
2. **2D 품질의 영향 (RQ2).** 정답 2D → 검출 2D로 바꾸면 PA-MPJPE +8mm, 떨림(accel) +3.6~7.5. 단, 입력 관절 구성도 함께 바뀜 (한계 4).
   *Detected instead of GT 2D costs ~8 mm PA-MPJPE (joint set also differs; see limitation 4).*
3. **정규화가 분야 이동을 좌우함 (RQ3, 가장 큰 발견).** ASPset 안에서는 화면 정규화가 MPJPE에서 약간 나았지만 (82.5 vs 83.4), KERAAL로 옮기면 골반 정규화가 각도 RMSE에서 9개 단위 전부 우세 (−5.5°, p = 0.004). 팔꿈치 r0는 화면 정규화에서 2D보다도 나빠짐 (0.23–0.28 vs 0.39–0.42).
   *Normalisation decides transfer: screen-normalised looks fine in-domain but collapses on KERAAL; root-normalised wins on angle RMSE in 9/9 participant × exercise cells (p = 0.004).*
4. **3D로 올리는 의미 (RQ3).** 골반 정규화 모델은 2D 각도 대비 RMSE −8.0° (9/9 단위, p = 0.004), Kinect와는 차이 없음 (−1.0°, p = 1.0). 상관(r0)은 2D 대비 +0.02로 유의하지 않음 (p = 0.57).
   *Lifting cuts angle error by 8° vs raw 2D angles and matches Kinect on RMSE; correlation gain over 2D is not significant.*
5. **실패 지점: RTK 운동.** RTK에서 영상 기반 방식은 모두 약함 (ours 0.24, 2D 0.14) vs Kinect 0.65. 깊이 방향 회전이 많은 동작으로 보임 → 단일 카메라의 한계를 보여주는 사례.
   *Both video methods fail on RTK (r0 0.24 / 0.14 vs Kinect 0.65), likely rotation in depth.*
6. **오류 판별 (RQ4): 추정 3D로도 Kinect·Vicon 수준.** 같은 각도 특징 + RF, 운동별 참가자 1명 빼기(LOPO). 정상 vs 오류 AUC: ours(root) 0.85, Kinect 0.81, Vicon(마커 위치 각도) 0.77, 2D 0.88. 어느 쌍도 9개 단위에서 유의한 차이 없음 → **"추정 3D로 바꾸면 성능이 떨어진다"는 증거 없음**. 다만 2D 각도도 똑같이 잘 됨 → 이 운동·오류에서는 3D가 판별에 필수는 아님.
   *Error detection from estimated 3D matches Kinect and Vicon-position angles (AUC 0.85 / 0.81 / 0.77, no significant pairwise difference over 9 cells); raw 2D angles do as well (0.88), so 3D is not required for these acted errors.*
7. **"정답 센서"가 곧 좋은 특징은 아님.** Vicon 쿼터니언 상대각으로 만든 특징은 AUC 0.64, 4분류 F1 0.28 (우연 0.25)로 가장 나쁨. 마커를 붙인 방향이 참가자마다 달라 각도에 참가자별 오프셋이 생기고 (ELK 오른팔꿈치 평균: P3 75° vs P1·P2 약 40°), 참가자 빼기 검증에서 일반화가 안 됨. 같은 Vicon도 마커 위치로 각도를 만들면 0.77. 시작 자세 기준선을 빼도 회복되지 않음 (0.62).
   *A gold-standard sensor does not guarantee good features: Vicon quaternion angles carry per-participant mounting offsets and fail leave-one-participant-out (AUC 0.64); Vicon target positions give 0.77.*

## 2. 주요 표 / Main tables (시드 3개 평균 / mean over 3 seeds)

ASPset-510 test (60 views, 13,708 frames, mm):

| 입력 / input | 정규화 / norm | MPJPE | PA-MPJPE | accel |
|---|---|---|---|---|
| 검출 / det | root | 83.4 ± 1.7 | 49.4 ± 0.4 | 10.6 |
| 검출 / det | screen | 82.5 ± 0.9 | 54.6 ± 0.5 | 14.4 |
| 정답 / gt | root | 77.1 ± 0.8 | 41.1 ± 0.8 | 7.0 |
| 정답 / gt | screen | 73.0 ± 1.5 | 46.5 ± 0.3 | 6.9 |
| 평균 자세 / mean pose | – | 227.1 | 161.2 | – |

KERAAL G3 vs Vicon (540 recordings, 2,053 moving angle pairs; r0 = Pearson r at lag 0, median; RMSE deg):

| 출처 / source | r0 | RMSE |
|---|---|---|
| ours (det/root) | 0.596 | 20.4 |
| ours (det/screen) | 0.501 | 26.9 |
| raw 2D angles | 0.552 | 28.9 |
| Kinect 3D | 0.667 | 18.6 |

검정은 참가자 × 운동 9개 단위의 Wilcoxon (참가자 3명) / tests: Wilcoxon over 9 participant × exercise cells (3 participants).

KERAAL G3 오류 판별 (RQ4; 540 녹화, 9개 단위 × 분류기 시드 3 평균; 전체 표는 summary_tables.md) / error detection:

| 각도 출처 / angle source | AUC (C vs E) | macro-F1 (4분류, 우연 0.25) |
|---|---|---|
| Vicon 쿼터니언 / quaternion | 0.643 | 0.282 |
| Vicon 마커 위치 / target positions | 0.766 | 0.530 |
| Kinect 3D | 0.809 | 0.567 |
| ours (det/root) | 0.852 | 0.593 |
| ours (det/screen) | 0.828 | 0.560 |
| raw 2D | 0.876 | 0.562 |

ours(root) vs Kinect AUC +0.04 (p = 0.25), vs Vicon 위치 +0.09 (p = 0.10), vs 2D −0.02 (p = 0.82), vs Vicon 쿼터니언 +0.21 (p = 0.02). 민감도: Vicon 결측 > 20% 녹화 49개 제외, 시작 자세 기준선 빼기 — 결론 같음.

## 3. 데이터 점검 / Data checks (2026-10-26)

- ASPset: 결측 0, 영상 1,410개 모두 프레임 수 = 정답 프레임 수, 재투영 일치, 화면 밖 투영 0. 정답 떨림 3.0mm (KERAAL Vicon 1.5mm).
- 검출 2D: 프레임 99.996% 검출, test 오차 중앙값 = 키의 1.5%.
- KERAAL: 영상 540개, 프레임 99.96% 검출 (최저 94.5%), (0,0) 키포인트 0개.

## 4. 한계 / Limitations (논문에 반드시 적을 것 / must go in the paper)

1. **참가자 3명.** 검정 단위는 9개 (참가자 × 운동). 녹화 540개를 독립으로 보면 p가 과대평가됨 → 그렇게 하지 않음.
2. **Vicon 각도는 해부학적 굽힘각이 아님.** 두 마디 쿼터니언의 상대 회전량이라 팔꿈치는 회내·회외, 어깨는 상완 회전까지 포함. "relative segment rotation angle"로 표기. r은 고정 오프셋에 영향 없지만 RMSE는 정의 차이를 일부 포함.
3. **검출 파이프라인이 두 데이터셋에서 다름.** ASPset은 데이터셋 박스 주변 crop (test 포함) → "YOLO keypoints on dataset-box crops"로 표기, ASPset 검출 결과는 다소 낙관적. KERAAL은 전체 화면에서 가장 큰 사람.
4. **gt vs det은 2D 품질만 다른 게 아님.** 관절 구성 (ASPset 17 vs COCO 17)과 신뢰도 채널도 다름.
5. **최적 지연(best lag) r은 낙관적.** 그래서 r0를 주 지표로 씀.
6. 무릎은 KERAAL G3에서 거의 움직이지 않아 (Vicon 표준편차 < 5°) 분석에서 빠짐. 4개 각도 (좌우 팔꿈치·어깨)만 남음.
7. **RQ4는 연기된 오류 (G3, 건강한 3명).** 실제 환자(1A)에서의 판별은 아님. 분류기 학습 참가자가 2명뿐. 9개 단위 검정은 다중 비교 보정 안 함, 검정력 낮음 → "차이 없음"은 "동등함"의 증명이 아님.
8. Vicon 마커 위치 각도는 근사 (팔꿈치 = 상완·전완 마커 중점, 몸통 = 가슴·골반 마커). Vicon 60fps라 속도 특징 스케일이 다른 출처와 다르지만 분류기는 출처마다 따로 학습.

## 5. 다음 단계 / Next steps

- RQ4 확장: 환자 데이터(1A, Kinect만 있음)로 ours vs Kinect 판별 비교 — 영상이 있으면 가능한지 확인.
- 한계 3 해소: KERAAL에도 사람 박스 crop 방식 적용하거나 ASPset을 전체 화면 검출로 다시.
- 한계 4 해소: 정답 2D를 COCO와 공통인 12관절로만 넣는 추가 실험.
- RTK 실패 분석: 운동별 카메라 대비 움직임 방향.

## 6. 재현 / Reproduce

환경 / env: `E:\mocap3d_env` (Python 3.12, torch 2.14.1+cu130, ultralytics 8.4.189), GPU RTX 3090.
데이터·결과 / data & outputs (repo 밖 / outside the repo): `E:\ASPset510_data` (extracted, det2d, runs), `E:\KERAAL_mocap3d` (det2d, eval json).

```
python aspset.py --check <ASPset root>
python detect2d.py <ASPset root> E:/ASPset510_data/det2d/yolo11x --workers 3
python train_lift.py <ASPset root> <run dir> --input {gt,det} --norm {root,screen} --epochs 120 --seed {0,1,2} [--det-dir ...]
python keraal_eval.py detect <KERAAL group3> E:/KERAAL_mocap3d/det2d
python keraal_eval.py eval <KERAAL group3> E:/KERAAL_mocap3d/det2d <run dir> <out json>
python summarize.py E:/ASPset510_data/runs E:/KERAAL_mocap3d
python keraal_errors.py angles <KERAAL group3> E:/KERAAL_mocap3d/det2d E:/ASPset510_data/runs E:/KERAAL_mocap3d/rq4_angles.npz
python keraal_errors.py classify E:/KERAAL_mocap3d/rq4_angles.npz <out json> [0.2]
```
모든 스크립트에 `--check` 자체 시험 있음 / every script has a `--check` self-test.

## 7. 로그 / Log

- 2026-10-26: 데이터 점검 → 2D 검출 → 정답/검출 × 화면/골반 × 시드 3 = 12개 학습 → KERAAL 평가 6개. 독립 리뷰에서 핵심 계산 버그 없음, 통계(녹화 단위 → 9개 단위), 지연 탐색 공정성, 반전 TTA 일치, Kinect 추적 실패 처리를 수정하고 다시 실행.
- 2026-10-30: KERAAL 사후 보정(`keraal_calib.py`) + ASPset·KERAAL 합쳐 학습(`merge_train.py`) → [`MERGE_REPORT_KR.md`](MERGE_REPORT_KR.md). RTK 실패는 단일 카메라 한계가 아니라 학습 데이터 부족이었음 → 위 결과 5의 해석을 고쳐야 함 / KERAAL post-hoc calibration + merged training; the RTK failure was missing data, so finding 5's reading needs correcting.
- 2026-10-27: RQ4 (keraal_errors.py). 첫 실행에서 Vicon 쿼터니언 특징이 우연 수준 → 원인 확인 (참가자별 마커 오프셋, 결측 녹화 49개) 후 Vicon 위치 각도, 시작 자세 기준선, 결측 필터 변형 추가.
