# Roshini (로시니) — 프로그래밍 / Programming

**역할 / Role.** 실험과 통계 모형으로 "기준점 차이" 가설을 시험한다 / Test the threshold hypothesis with experiments and statistical models.

## 지금까지 완료한 것 / Completed so far

전체 내용 / Full details → [`Kinect_model/README.md`](Kinect_model/README.md), [`Kinect_model/KERAAL_Kinect_Model_Report.pdf`](Kinect_model/KERAAL_Kinect_Model_Report.pdf) · 브랜치 / branch `roshini/kinect-model`

### Kinect 초 단위 오류 탐지 모델 (방향 2) / Per-second Kinect error-detection model (Direction 2) — 탐색 / exploratory

- **질문 / Question.** 실제 전문가 라벨(1A + 2A)로 학습한 모델이 새 사람의 오류를 알아보는가? 시험은 G3(연기 오류) / Does a model trained on real expert labels (1A + 2A) recognise errors in new people? Tested on G3 (acted errors).
- **방법 / Method.**
  - 운동별 예/아니오 Random Forest (300 trees, balanced) / one yes/no RF per exercise
  - 프레임 → 1초 단위 행, feature 4종(raw 위치, 정규화 위치, 각도, 최종 = 각도 + 절댓값 + 앞뒤 5초 문맥) / frames → one row per second, 4 feature sets
  - 참가자 하나씩 빼는 검증(사람 안 AUC), G3는 한 번만 시험(녹화 단위 평균), 1,000회 라벨 섞기 우연 검정 / leave-one-participant-out (within-person AUC), G3 tested once (recording level), 1,000-shuffle chance test

| Feature | CTK | ELK | RTK |
|---|---|---|---|
| raw positions | 0.57 | 0.55 | 0.67 |
| normalized positions | 0.55 | 0.50 | 0.51 |
| angles | 0.72 | 0.53 | 0.47 |
| **final** | **0.73** | **0.58** | **0.60** |

1A + 2A 안 검증, 사람 안 평균 AUC / validation within 1A + 2A, mean within-person AUC.

**G3 시험 (녹화 단위) / G3 test (recording level): CTK 0.71 · ELK 0.77 · RTK 0.77**, 모두 p = 0.001 (1,000회 섞기) / all p = 0.001 vs 1,000 shuffles.

- **의미 / Meaning.** 사전 등록 방향(G3 → 실제)은 실패했지만, 반대 방향(실제 → G3)은 오류를 순위대로 구분한다 → 모델의 인식 능력은 있고 **판정 기준점이 다르다**는 팀 해석의 근거 / The pre-registered direction (G3 → real) failed, but the reverse ranks errors well, which supports the team's view that the model can recognise errors and **the decision threshold differs**.
- **한계 / Limits.**
  - 학습·검증 12명, 시험 3명 / 12 people for training and validation, 3 for testing.
  - G3 오류는 연기이고 물리치료사가 확인하지 않았다 / G3 errors are acted and were not checked by physiotherapists.
  - G3 세션 교란은 아직 점검하지 않았다 / The G3 session confound has not been checked yet.
  - 모델 1종, seed 1개 / One model type, one seed.

**실행 / Run**
- 데이터는 저장소에 없다 / The data is not in the repo.
- `model_input_kinect.csv`(의진 정제본)가 있는 폴더에 `Kinect_model/`을 두고 `python3 Kinect_model/run_all.py`를 실행한다 / Put `Kinect_model/` next to Euijin's `model_input_kinect.csv` and run `python3 Kinect_model/run_all.py`.

## 할 일 / Tasks

| ID | 마감 / Due | 내용 / Item | 상태 / Status |
|---|---|---|---|
| — | 10/13 | Kinect 초 단위 모델 (방향 2) / per-second Kinect model (Direction 2) | **완료 / done** (위 / above) |
| R1 | 10/16 | 경계 보정 실험 / threshold calibration (`keraal_pipeline/src/threshold_calibration.py`) | 이번 묶음에 없음 / not in this package |
| R2 | 10/16 | P1 raw 우위 점검 / P1 raw-advantage check | 이번 묶음에 없음 / not in this package |
| R3 | 10/23 | 주석자 기준점 혼합 모형 / annotator-threshold mixed model | 예정 / planned |
| R4 | 10/23 | 시간 구간 모델 (U2 이후) / temporal model (after U2) | 예정 / planned |

## 규칙 / Rules

- 새 실험 = `keraal_pipeline/configs/`에 **새 설정 파일**. `p1_confirmatory.json`은 바꾸지 않는다 / New experiment = **new config file**; never edit `p1_confirmatory.json`.
- 새 스크립트에 `--check`를 넣고 `src/verify.py`에 추가한다. merge 전에 `python src/verify.py`가 통과해야 한다 / Add `--check`, register it in `src/verify.py`, and make sure it passes before merging.
- 결과는 "탐색"으로 표시하고 `PROGRESS.md`에 기록 / Label results "exploratory" and log them in `PROGRESS.md`.
- 받는 데이터 / Inputs from: [`../euijin/`](../euijin/) (U1, U2) · 코드 안내 / Code guide: [`../../keraal_pipeline/CODE_GUIDE.md`](../../keraal_pipeline/CODE_GUIDE.md)
