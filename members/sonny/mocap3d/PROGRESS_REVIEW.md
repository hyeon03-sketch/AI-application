# 2D 영상 → 3D 모션캡처: 진행 리뷰 / Progress review

작성 / Written: 2026-10-27 · Sonny (팀장 / team lead) · 모든 결과는 탐색(exploratory) / all results exploratory
자세한 결과 / Details: [`RESULTS.md`](RESULTS.md) · 설계 / Design: [`RESEARCH_DESIGN.md`](RESEARCH_DESIGN.md) · 표 / Tables: [`summary_tables.md`](summary_tables.md) · 데이터셋 조사 / Dataset survey: [`../3D_MOCAP_DATASETS.md`](../3D_MOCAP_DATASETS.md)

---

## 1. 한 줄 요약 / One-line summary

스포츠 영상(ASPset-510)으로 2D→3D 모델을 만들고 재활 운동(KERAAL)에 옮겨 Vicon·Kinect와 비교했다. 입력 정규화를 골반 기준으로 해야 분야 이동이 되고, 그렇게 만든 추정 3D는 각도 정확도와 오류 판별 모두 Kinect 수준이다.
*We trained a 2D→3D lifter on sports video (ASPset-510) and transferred it to rehab exercises (KERAAL) against Vicon and Kinect. Pelvis-based input normalisation is what makes transfer work, and the resulting 3D matches Kinect on angle accuracy and error detection.*

## 2. 내 역할과 이번 작업 / My role and this work

팀 역할 (README): 연구 방향, 발표 흐름, 저장소 관리, PR 리뷰. 새 목표(2026-10-26, "기존 데이터셋으로 2D 영상 → 3D 모션캡처 모델")에서 내가 맡은 일:
*Team role (README): research direction, presentation flow, repo owner, PR review. Under the new goal I took on:*

| 영역 / Area | 한 일 / Done | 산출물 / Output |
|---|---|---|
| 연구 방향 / direction | 데이터 점검만으로는 논문 거리가 약하다는 우려 → "스포츠 학습 모델의 재활 이전 + 오류 판별" 질문(RQ1–RQ4)으로 틀을 잡음 / framed RQ1–RQ4 | `RESEARCH_DESIGN.md` |
| 데이터셋 리뷰 / dataset review | Joshi·Hyeon Geon의 조사(10/23)와 팀원이 공유한 ASPset-510을 새 목표 8개 기준으로 검증 / checked the survey and ASPset-510 against 8 criteria | `../3D_MOCAP_DATASETS.md` 리뷰 메모 |
| 데이터 확보·점검 / data | ASPset-510 전체 다운로드(23 GB), KERAAL G3 Vicon 540개 확인, 품질 점검 / download and quality checks | 3절 |
| 실험 / experiments | 2D 검출, lifter 12개 학습, KERAAL 각도 평가, 오류 판별 / detection, 12 lifters, angle eval, error detection | 코드 6개, `RESULTS.md` |
| 리뷰 / review | 독립 리뷰로 통계·공정성 문제 수정 / independent review, fixes | 5절 |

## 3. 데이터셋 / Datasets

| | ASPset-510 | KERAAL G3 | KERAAL 1A / 2A (다음 / next) |
|---|---|---|---|
| 역할 / role | 학습·검증·테스트 / train · val · test | 분야 이동, 오류 판별 / transfer, error detection | 환자 데이터 판별 / patient detection |
| 내용 / content | 17명 × 30동작 = 510클립, 카메라 3대, 50fps, 4K | 건강인 3명, CTK/ELK/RTK, 정상 + 연기된 오류 1–3, 540녹화 | 1A 환자 250, 2A 건강인 51, 주석자 A·B |
| 3D 정답 / 3D GT | 마커 없는 복원, 17관절(mm) / markerless, 17 joints | Vicon 17개 마디 타깃 (위치 + 쿼터니언, 60fps) / segment targets | 없음, Kinect만 / none, Kinect only |
| 영상 / video | 있음 / yes | 960×540, 30fps | 있음 / yes (250 / 51) |
| 라이선스 / licence | CC0 | CC BY-NC-SA → 원본·파생 데이터 업로드 금지 / never upload raw or derived data | 같음 / same |
| 위치 / location | `E:\ASPset510_data` | `E:\KERAAL_data\extracted\group3` | `E:\KERAAL_data\extracted\group1A`, `group2A` |

점검 결과 / Checks (2026-10-26):
- ASPset: 결측 0 (109,901프레임), 영상 1,410개 모두 프레임 수 = 정답 프레임 수, 재투영 일치, 화면 밖 투영 0. 좌우 뼈 길이 비 ≈ 1.00, 뼈 길이 변동 다리 3–3.5%, 팔 5–6.6%. 정답 떨림 3.0mm (Vicon 1.5mm).
- KERAAL G3: 영상 540개 프레임 99.96% 사람 검출. Vicon 결측 프레임 평균 3.9%, 20% 넘는 녹화 49개 (RQ4 민감도 분석에서 제외해 봄).
- 다른 후보(UCOPhyRehab++, OpenCap, REHAB24-6, Fit3D, AIST++)는 RGB 미공개·받기 어려움·라이선스 문제로 이번에는 쓰지 않음.
- *Other candidates were not used: no raw RGB, hard to obtain, or licence limits.*

## 4. 진행 내역 / Timeline

| 날짜 / Date | 내용 / Item |
|---|---|
| 10/23 | Joshi·Hyeon Geon 데이터셋 조사 / dataset survey |
| 10/26 | 새 목표 기준 리뷰, ASPset-510 다운로드·점검, 연구 설계 / review, download, checks, design |
| 10/26 밤 / night | 2D 검출 → lifter 12개 학습 (정답/검출 2D × 화면/골반 정규화 × 시드 3) → KERAAL 각도 평가 → 독립 리뷰 → 수정 후 재실행 |
| 10/27 | RQ4 오류 판별 → Vicon 특징 이상 원인 조사 → 변형 추가 후 재실행, 진행 상황 zip |

## 5. 진행 리뷰 / Progress review

### 5.1 질문별 상태 / Status by question

| 질문 / RQ | 상태 / Status | 결과 / Result | 믿을 만한가 / Confidence |
|---|---|---|---|
| RQ1 ASPset 기준 성능 | 완료 | 검출 2D → 3D: MPJPE 83mm, PA-MPJPE 49mm (평균 자세 227 / 161) | 높음. 공식 분할, 시드 3개 |
| RQ2 2D 품질 영향 | 완료 | 검출 2D면 PA-MPJPE +8mm | 중간. 관절 구성도 함께 바뀜 |
| RQ3 재활로 이전 | 완료 | 골반 정규화가 각도 RMSE −5.5° (9/9 단위, p = 0.004). 2D 각도 대비 −8°, Kinect와 차이 없음 | 중간. 참가자 3명 |
| RQ4 오류 판별 | 완료 | AUC: ours 0.85, Kinect 0.81, Vicon 위치 0.77, 2D 0.88 — 유의한 차이 없음. Vicon 쿼터니언 0.64 | 낮음–중간. 연기된 오류, 검정력 낮음 |

### 5.2 리뷰에서 고친 것 / Fixed after review

1. 통계 단위: 녹화 540개를 독립으로 본 검정 → 참가자 × 운동 9개 단위. 이 때문에 "상관에서 2D보다 낫다" 주장을 철회.
2. 동기화: 출처마다 같은 지연 탐색, 지연 없는 상관 r0를 주 지표로.
3. KERAAL 평가에도 ASPset과 같은 좌우 반전 TTA, Kinect 추적 실패 프레임은 NaN.
4. RQ4 첫 실행에서 Vicon 쿼터니언 특징이 우연 수준 → 원인 확인 (참가자별 마커 부착 오프셋, ELK 오른팔꿈치 평균 P3 75° vs P1·P2 약 40°) → Vicon 위치 각도, 시작 자세 기준선, 결측 필터 변형 추가. 결론 유지.

### 5.3 남은 위험 / Open risks (논문에 적을 것 / must go in the paper)

- 참가자 3명, 오류는 연기됨. "차이 없음" ≠ "동등함".
- Vicon 각도 정의가 해부학적 굽힘각이 아님 (쿼터니언 상대 회전 / 마커 위치 근사).
- 2D 검출 방식이 ASPset(데이터셋 박스 crop)과 KERAAL(전체 화면)에서 다름 → ASPset 수치는 다소 낙관적.
- RTK(몸통 회전)에서 영상 방식의 각도 추적이 약함 (r0 0.24 vs Kinect 0.65) — 그런데 오류 판별은 잘 됨 (AUC 0.93). 왜 그런지 설명 필요.
- 2D 각도만으로도 판별이 잘 됨 → "3D가 왜 필요한가"에 답해야 함.

## 6. 다음 작업 구상 / Planned next work (내 역할 기준 / for my role)

| 우선 / Priority | 작업 / Task | 왜 / Why | 규모 / Size |
|---|---|---|---|
| 1 | **1A 환자 데이터 판별**: 영상 250개 → ours vs Kinect 오류 판별, 주석자 A·B 각각 | 연기된 오류가 아닌 실제 환자에서도 되는지 = 논문의 핵심 주장 | 하루 / ~1 day |
| 2 | RTK 분석: 각도 추적은 약한데 판별은 잘 되는 이유 (어떤 특징이 쓰이는지) | 리뷰어가 물을 질문 | 반나절 |
| 3 | 3D의 쓸모 보여주기: 카메라 각도가 달라질 때 2D vs 3D 판별 (ASPset 다른 카메라 / 합성 회전) | "2D로 충분하다"는 반론에 대한 답 | 하루 |
| 4 | 한계 해소 실험: KERAAL도 박스 crop 검출, 정답 2D를 공통 12관절로 | 비교 공정성 | 반나절 |
| 5 | 논문 초안 구조, 그림 (정규화 비교, 출처별 AUC) | 발표·논문 | 하루 |
| 계속 / ongoing | 팀원 PR 리뷰, 코드는 `sonny/mocap3d` 브랜치로 PR (데이터·파생 테이블 제외) | 저장소 관리 | – |

팀원에게 나눌 수 있는 일 (제안) / Could be shared:
- 로시니 (코드) / Roshini (code): 4번 한계 해소 실험.
- 의진 (데이터) / Euijin (data): 1A·2A 영상과 Kinect·주석 짝 맞추기.
- Joshi: 그림 해석·발표 슬라이드 검토 (코딩 없음).

## 7. 파일 / Files

- 코드 / code: `aspset.py`, `detect2d.py`, `train_lift.py`, `keraal_eval.py`, `keraal_errors.py`, `summarize.py` (모두 `--check` 자체 시험 / all with `--check`)
- 문서 / docs: 이 파일, `RESULTS.md`, `RESEARCH_DESIGN.md`, `summary_tables.md`, `../3D_MOCAP_DATASETS.md`
- repo 밖 / outside the repo: `E:\ASPset510_data` (데이터, 검출, 학습 결과), `E:\KERAAL_mocap3d` (검출, 평가 json, RQ4), 환경 `E:\mocap3d_env`
- 묶음 / bundle: `mocap3d_progress_20261027.zip` (코드 + 문서 + 집계 표만 / code, docs, aggregate tables only)
- 커밋 안 함 / not committed yet.
