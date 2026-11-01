# 2D 영상 → 3D 모션캡처: 연구 설계 / 2D video → 3D motion capture: research design

작성 / Written: 2026-10-26 · Sonny · 상태 / Status: 초안, 탐색(exploratory) / draft, exploratory

## 1. 질문 / Question

**스포츠 영상으로 학습한 단일 카메라 2D→3D 모델은 재활 운동에서도 쓸 만한가? 그 정확도로 운동 오류를 판별할 수 있는가?**
**Does a monocular 2D→3D model trained on sports video hold up on rehab exercises, and is it accurate enough to detect exercise errors?**

- RQ1. ASPset-510 안에서 기준 성능 / in-domain baseline (MPJPE, PA-MPJPE on the official test split).
- RQ2. 2D 입력 품질의 영향: 정답 2D 투영 vs 검출기 2D / effect of 2D input quality: GT-projected 2D vs detected 2D.
- RQ3. 분야 이동: ASPset → KERAAL G3 (Vicon 마커 기준) / domain shift: ASPset → KERAAL G3, against Vicon.
- RQ4. 추정 3D로 KERAAL 오류 판별 시 성능 하락 (Vicon 3D 대비) / drop in KERAAL error detection when using estimated 3D instead of Vicon 3D.

## 2. 데이터 / Data

| | 역할 / Role | 정답 / GT | 비고 / Notes |
|---|---|---|---|
| ASPset-510 (CC0) | 학습·검증·테스트 / train · val · test | 17관절 3D, 마커 없음, 50fps / 17-joint 3D, markerless | 공식 분할 390/60/60, 테스트 영상은 클립당 카메라 1대 / official split; test has 1 camera per clip |
| KERAAL G3 (CC BY-NC-SA) | 분야 이동 평가 / domain-shift test | Vicon 17개 마디 마커, 60fps / 17 segment targets | 관절≠마커 → 매핑 필요, 원본 repo 업로드 금지 / joints ≠ targets; never commit raw |

점검 결과 (2026-10-26): 결측 0, 영상↔정답 프레임 일치, 재투영 일치. 정답 떨림 3.0mm (Vicon 1.5mm), 팔 뼈 길이 변동 5–7%. 자세한 내용은 `../3D_MOCAP_DATASETS.md` 리뷰 메모. / Checks: no missing data, frames match, reprojection matches; GT jitter 3.0 mm vs Vicon 1.5 mm, arm bone-length variation 5–7%.

## 3. 방법 / Method

- 2D 검출 / 2D detection: YOLO11-pose (COCO 17 keypoints), 모든 영상 프레임 / every frame.
- 2D→3D lifting: 시간 합성곱망 (VideoPose3D 방식), 81프레임 수용 영역, 골반 기준 카메라 좌표 3D(mm) 예측 / temporal conv net, 81-frame receptive field, pelvis-relative 3D in camera coordinates.
- 비교 조건 / Conditions: (a) 평균 자세 / mean pose, (b) 정답 2D 입력 / GT-projected 2D input, (c) 검출 2D 입력 / detected 2D input.
- 모델 선택은 val로만, test는 마지막에 한 번 / model selection on val only; test once at the end.

## 4. 지표 / Metrics

- MPJPE (mm), PA-MPJPE (mm), 관절별 오차 / per-joint error, 프레임 간 가속도 오차 / acceleration error.
- RQ3: 관절↔마커 매핑이 필요 없는 지표 우선 (예: 팔꿈치·무릎 굽힘 각도의 시계열 상관) / prefer mapping-free metrics, e.g. correlation of elbow/knee flexion over time.
- RQ4: KERAAL 기존 파이프라인의 AUC를 Vicon 3D vs 추정 3D로 비교, 참가자 단위 분할, RULES §4 보고 형식 / compare AUC from the existing KERAAL pipeline, participant-level split, RULES §4 reporting.

## 5. 위험 / Risks

- ASPset 정답 노이즈가 성능 하한 / GT noise sets an error floor.
- 스포츠(야외, 4K) ↔ 재활(실내, 960×540) 차이 / domain gap in scene and resolution.
- KERAAL에는 카메라 보정이 없음 → 절대 위치 비교 불가, 각도·상대 지표 사용 / no calibration in KERAAL → use angles and relative metrics.

## 6. 진행 / Progress

결과와 로그는 `RESULTS.md` / results and log in `RESULTS.md`. 2026-10-26: RQ1–RQ3 완료. 2026-10-27: RQ4 완료 — 기존 KERAAL 파이프라인(Kinect 전용) 대신 모든 출처에 같은 각도 특징 + RF, 운동별 LOPO를 씀 (출처만 바꾸는 공정 비교를 위해) / RQ4 done with one shared angle-feature + RF pipeline per source instead of the Kinect-only team pipeline.

변경 / Changes after the first run: 입력 정규화 두 가지 (screen, root) 비교 추가 — 화면 정규화는 ASPset(4K, 작은 사람)과 KERAAL(960×540, 큰 사람)의 입력 크기가 달라 분야 이동이 불가능하기 때문 / added screen vs root input normalisation, because screen normalisation cannot transfer across image sizes. KERAAL 지표는 lag 0 상관(r0)을 주 지표로, 검정은 참가자 × 운동 9개 단위로 / r0 is the primary KERAAL metric; tests use 9 participant × exercise cells.
