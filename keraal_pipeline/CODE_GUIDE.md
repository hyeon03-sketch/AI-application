# KERAAL 파이프라인 코드 해설 / Code Guide

각 절은 한국어 설명 다음에 영어 설명이 이어진다. 함수 이름과 파일 이름은 실제 코드 기준이다(2026-10-09).
Each section gives the Korean explanation first, then English. Function and file names match the code as of 2026-10-09.

---

## 0. 한눈에 보기 / Overview

이 파이프라인은 KERAAL 재활 운동 데이터에서 **녹화 하나가 정상인지, 어떤 오류인지**를 분류하고, 그 평가가 믿을 만한지 점검한다. 각 스크립트는 앞 단계가 만든 파일만 읽고 자기 결과를 파일로 남긴다. 모든 스크립트에 `--check` 옵션이 있어 스스로 결과를 검사하고, `src/verify.py`가 이 검사를 순서대로 모두 돌린다.

The pipeline classifies whether a KERAAL rehabilitation recording is correct or which error it shows, and checks whether that evaluation can be trusted. Each script reads only files produced by earlier stages and writes its own outputs. Every script has a `--check` mode that validates its result, and `src/verify.py` runs all of them in order.

```
raw/ (Kinect + 주석 annotations)
  │ index.py        → data/master_index.csv        녹화 목록 / recording index
  │ labels.py       → data/labels.csv              라벨 / labels
  │ preprocess.py   → data/skeleton_*.npz          정규화 골격 / normalized skeletons
  │ features.py     → data/features_T100.npz       표현 / representations
  │ splits.py       → data/splits.json             분할 / frozen splits
  ├─ evaluate.py    (지표 함수 / metric functions, majority baseline)
  ├─ rf_baseline.py / run_experiment.py → results/experiments/
  ├─ trial_confound.py · label_clustering.py · person_confound.py · permutation_null.py · compare_reps.py
  ├─ confirmatory.py → results/confirmatory_*.md   (사전 등록 / pre-registered)
  ├─ figures.py      → results/figures/, results/tables.md
  └─ inventory.py    (E:/KERAAL_data 전체 데이터 / full dataset)
verify.py = 모든 --check → pytest → manifest.py (결과 해시 / output hashes)
```

### 자주 나오는 용어 / Terms

| 용어 / Term | 뜻 / Meaning |
|---|---|
| RTK / ELK / CTK | 몸통 회전 / 옆구리 스트레칭 / 얼굴 가리기 운동 · torso rotation / flank stretch / hiding face |
| C, E1–E3, EXCL | 정상, 오류 1–3, 제외(Incomplete·Motionless·Other) · correct, errors 1–3, excluded |
| E13 | CTK의 E1과 E3를 합친 라벨 · CTK Error1 and Error3 merged |
| 주석자 A / B | 두 명의 전문가 라벨 · the two expert annotators |
| R0–R4, Rerr, Rerr_d | 표현 사다리(아래 3절) · representation ladder (section 3) |
| P1–P4 | 평가 프로토콜(아래 4절) · evaluation protocols (section 4) |
| participant_key | `그룹-참가자-장소`, 참가자 단위 분할의 기준 · `group-participant-site`, the unit of subject-independent splits |

---

## 1. 데이터 정리 / Data indexing

### `src/index.py`
- **하는 일**: `raw/`의 실제 파일명(`G1A-Kinect-CTK-R1-Brest-022.txt`, `G3-Kinect-CTK-P1T1-Unknown-E1B1-0.txt`)과 주석 파일(`.anvil`)을 읽어 녹화 하나당 한 행인 `data/master_index.csv`를 만든다.
- **핵심 함수**: `read_anvil`(BOM으로 UTF-16/UTF-8 판별), `parse_anvil`(Global evaluation, Global error, Temporal error 트랙 읽기), `collect_annotated`(1A·2A), `collect_group3`(파일명에서 C/E1–E3, B1–B3, trial 추출).
- **주의점**: 주석 폴더마다 이름이 `.anvil`뿐인 파일이 있어 무시 목록에 둔다. 2A의 S1은 장소가 두 곳이라 참가자 키에 장소를 넣어 분리한다.
- **검사**: 1A 250, 2A 51, G3 540개, 파싱 실패 0, G3 운동 × 클래스 45개씩.

- **What**: reads real file names and `.anvil` annotations in `raw/` and writes one row per recording to `data/master_index.csv`.
- **Key functions**: `read_anvil` (detects UTF-16/UTF-8 by BOM), `parse_anvil` (Global evaluation / Global error / Temporal error tracks), `collect_annotated` (1A, 2A), `collect_group3` (label, body-part code and trial from the file name).
- **Notes**: one nameless `.anvil` per annotation folder is ignored; 2A participant S1 appears at two sites, so the site is part of the participant key.
- **Check**: 1A 250, 2A 51, G3 540, zero parse failures, 45 per exercise × class in Group 3.

### `src/labels.py`
- **하는 일**: 인덱스에서 분류 라벨을 만든다(`data/labels.csv`). 주석자 A·B 각각, 둘이 일치할 때만 쓰는 `label_consensus`, CTK E1+E3 병합판 `*_ctk13`, 오류의 심각도.
- **핵심 함수**: `annotator_label`(Correct → C, Incorrect + Error1–3 → E1–E3, 나머지는 EXCL과 사유), `merge13`, `build`, `table`.
- **검사**: 테스트셋 클래스 개수가 설계 문서 표와 정확히 일치.

- **What**: derives labels (`data/labels.csv`): per annotator, a consensus label (only when A and B agree), a CTK E1+E3 merged version, and severity.
- **Key functions**: `annotator_label`, `merge13`, `build`, `table`.
- **Check**: test-set class counts match the design-document table exactly.

### `src/inventory.py`
- **하는 일**: E 드라이브의 전체 배포본(전 그룹, Kinect·BlazePose·OpenPose·영상·Vicon·주석)을 녹화 단위로 정리해 `data/inventory.csv`를 만든다. 확증 경로는 이 파일을 쓰지 않는다.
- **핵심 함수**: `data_root`(환경변수 `KERAAL_DATA` → `data_root.txt` → 기본 `E:/KERAAL_data/extracted`), `rec_key`, `scan`.
- **검사**: 그룹별 녹화 수(1A 250, 1B 1631, 2A 51, 2B 149, 3 540), 파일명 해석, `raw/` 사본이 원본과 바이트 단위로 같은지. 데이터 경로가 없으면 SKIPPED로 통과.

- **What**: indexes the full distribution on drive E (all groups and modalities) into `data/inventory.csv`; the confirmatory path does not use it.
- **Key functions**: `data_root` (env `KERAAL_DATA` → `data_root.txt` → default), `rec_key`, `scan`.
- **Check**: per-group counts, every name parses, `raw/` copies are byte-identical to the full distribution; skipped (passes) when the data root is absent.

---

## 2. 골격 정규화 / Skeleton normalization — `src/preprocess.py`

- **하는 일**: Kinect 파일(프레임당 175값 = 관절 25 × [x, y, z, 쿼터니언 4])에서 위치만 꺼내 `(T, 25, 3)`으로 만들고 정규화한다.
- **정규화 순서**(`normalize`): ① SpineBase를 원점으로 ② `heading_rotation`: 골반선(HipLeft→HipRight)의 프레임별 각도 중앙값으로 **녹화당 한 번** 수직축 회전 ③ 몸통 길이(SpineBase→SpineShoulder)로 나눔 ④ 5프레임 이동평균(`smooth`) ⑤ 100프레임 리샘플링(`resample`).
- **왜 녹화당 한 번인가**: 프레임마다 어깨선으로 정렬하면 RTK Error2(몸통 회전 부족) 신호가 지워진다.
- **출력**: `skeleton_raw.npz`(원본 길이), `skeleton_T100.npz`(`raw` = 길이만 맞춤, `norm` = 전체 정규화).
- **검사**: 비유한 값·0 프레임 없음, 원점·몸통 길이 1·골반선 방향 2° 이내.

- **What**: extracts joint positions from 175-value Kinect rows into `(T, 25, 3)` and normalizes them.
- **Order** (`normalize`): centre on SpineBase → one vertical-axis rotation per recording from the median per-frame hip-line angle (`heading_rotation`) → divide by torso length → 5-frame moving average → resample to 100 frames.
- **Why one rotation**: per-frame shoulder alignment would erase the RTK Error2 (insufficient trunk rotation) signal.
- **Outputs**: `skeleton_raw.npz`, `skeleton_T100.npz` (`raw` resampled only, `norm` fully normalized).

---

## 3. 표현(feature) / Representations — `src/features.py`

| 표현 / Rep | 내용 / Content | 차원 / Dim |
|---|---|---|
| R0 | 원본 카메라 좌표 · raw camera coordinates | 75 |
| R1 | 정규화 좌표 · normalized coordinates | 75 |
| R2 | 관절각 · joint angles (`joint_angles`) | 10 |
| R3 | R2 + 시간 미분 · + time derivatives | 20 |
| R4 | R3 + 좌우 차이 · + left-right differences | 24 |
| Rerr | 오류 정의별 feature · error-specific (`error_features`) | 9 |
| Rerr_d | Rerr − 녹화 첫 10% 평균 · relative to the starting posture | 9 |

- **관절각**: 팔꿈치 굴곡, 어깨 거상(몸통 아래 방향 대비), 팔 벌림(어깨선 대비), 몸통 회전(어깨선−골반선), 척추 기울기(정면·시상), 목 각도.
- **오류별 feature**: 어깨 거상·손목 높이("팔을 충분히 올리지 않음"), 몸통 회전("회전 부족"), 정면 척추 기울기("기울지 않음/옆으로 기욺"), 팔꿈치 굴곡("팔을 굽히지 않음"), 손목 간 거리/어깨 너비("팔을 충분히 벌리지 않음").
- **평면 태그**: invariant / frontal / horizontal / sagittal / vertical / camera. sagittal·vertical은 카메라 기울기(pitch)에 민감하다.
- **속도**: fps는 15로 확인됐지만, 코드는 리샘플링 후 "정규화 시간 기준"으로 계산한다.
- **검사**: 모양·NaN, 각도 범위, invariant feature가 임의 3D 회전에서 불변.

- **Angles**: elbow flexion, shoulder elevation, arm spread, trunk rotation, frontal and sagittal spine tilt, neck angle.
- **Error-specific features**: one or two per KERAAL error definition, fixed from the error wording before looking at results.
- **Plane tags** mark which features are sensitive to camera pitch (sagittal, vertical).
- **Velocity** is computed per normalized time step (frame rate is 15 fps, but recordings are resampled).
- **Check**: shapes, NaNs, angle ranges, rotation invariance of features tagged invariant.

---

## 4. 분할과 지표 / Splits and metrics

### `src/splits.py` → `data/splits.json`

| 프로토콜 / Protocol | 학습 → 테스트 / Train → test | 의미 / Purpose |
|---|---|---|
| P1 (주 / main) | Group 3 → 1A, 2A | sim-to-real 전이 · simulated → real errors |
| P2 | Group 3 안에서 참가자 1명씩 빼기 · leave-one-participant-out within G3 | 사람이 바뀌는 효과 · subject shift |
| P3_group / P3_random | 참가자 단위 vs 같은 구성의 무작위 · grouped vs composition-matched random | 누수로 인한 부풀림 · leakage inflation |
| P4 | 1A 안에서 환자 1명씩 빼기 · leave-one-patient-out within 1A | 시험 실행·탐색 · smoke test, exploration |

- **핵심 함수**: `grouped_random`, `matched_random`(P3_random의 테스트 구성을 P3_group과 같게 맞춰, 두 분할의 차이가 참가자 공유 여부뿐이게 함), `leave_one_out`.
- **검사**: 참가자 교집합 0, 모든 녹화가 한 번씩 테스트(P2, P4), 두 번 실행해도 같은 파일.

- **Key functions**: `grouped_random`, `matched_random` (random split with exactly the same group × exercise × label composition, so the two differ only in participant sharing), `leave_one_out`.

### `src/evaluate.py`
- **지표**: `macro_f1`(테스트에 있는 클래스만 평균), `balanced_accuracy`, `per_class`, `accuracy`, `majority_baseline`.
- **불확실성**: `bootstrap_ci`(참가자를 통째로 재표본), `paired_bootstrap_diff`(같은 재표본에서 두 모델 차이, seed 평균 포함).
- **검사**: 손계산 예제, scikit-learn과 일치, bootstrap 재현성.

- **Metrics**: Macro-F1 over classes present in the test set, balanced accuracy, per-class recall, majority baseline.
- **Uncertainty**: participant (cluster) bootstrap and paired bootstrap of model differences.

---

## 5. 모델과 실험 / Models and experiments

### `src/rf_baseline.py`
- `summarize`: feature 시계열을 feature마다 평균·표준편차·최소·최대·범위·10/90 백분위로 요약(7F).
- `folds_of`: splits.json의 어떤 프로토콜이든 (fold 이름, 학습 키, 테스트 키)로 바꿈.
- 운동별 Random Forest(300그루, class_weight=balanced). 전체 실행 시 out-of-fold 예측을 `results/rf_<P>_preds.csv`로 저장.

- `summarize` turns each feature sequence into 7 summary statistics; `folds_of` converts any protocol into folds; one Random Forest per exercise.

### `src/run_experiment.py`
- JSON 설정 하나로 프로토콜 × 과제 × 표현 × 모델 × seed를 돌린다. 과제 = `{exercise, label_col, classes}`(예: CTK `["C", "E13"]` 이진 과제).
- `make_model`: `rf`, `logreg`(표준화 + L2), `majority`. 골격이 없는 프로토콜은 ON HOLD로 건너뜀.
- `drop_trial_cue_features`: 세션 교란 점검에서 플래그된 feature를 빼는 옵션(사전 등록된 2차 분석용).
- 출력: `results/experiments/<이름>/`(config, runs, summary, preds).

- One JSON config defines the grid; tasks are `{exercise, label_col, classes}`; models `rf`, `logreg`, `majority`; protocols without skeletons are skipped; `drop_trial_cue_features` removes flagged trial-cue features.

### `configs/`
| 파일 / File | 용도 / Use |
|---|---|
| `p1_confirmatory.json` | 사전 등록 확증 실험(해시 고정, 수정 금지) · pre-registered, hash-locked |
| `p1_confirmatory_cue_removed.json` | 교란 feature 제거 2차 분석 · secondary analysis without trial-cue features |
| `main_binary.json` | 이진 주 과제 탐색(ELK C vs E2, CTK C vs E13) · exploratory binary tasks |
| `p4_smoke.json` | 검증용 빠른 실행(P4만) · quick smoke test, P4 only |

---

## 6. 평가 함정 점검 / Checks for evaluation pitfalls

| 파일 / File | 질문 / Question | 방법 / Method |
|---|---|---|
| `trial_confound.py` | G3에서 촬영 세션이 오류 라벨로 새는가 · does the session leak into G3 labels? | Correct 녹화만으로 trial 맞히기: 축소 LDA(`within_acc`, `across_acc`) + feature별 분산분석·FDR(`feature_anova`), 순열 95백분위 |
| `label_clustering.py` | 라벨이 사람 단위로 묶였는가 · are labels clustered within people? | ICC(1)(`icc1`), 설계효과, 유효 N |
| `person_confound.py` | 동작과 무관한 정보로 맞혀지는가 · do movement-free features predict labels? | 체격·카메라 위치·길이(`static_features`)만으로 RF |
| `permutation_null.py` | 우연히 얼마나 높게 나오는가 · how high can chance go? | 참가자에게 다른 참가자의 라벨 묶음 배정(`permute_by_participant`) 후 재평가(`loo_score`, `cell_task`) |
| `compare_reps.py` | 두 표현의 차이가 실제인가 · is a representation difference real? | 짝지은 참가자 bootstrap(`compare`) |

- 탐지기 선택 이유: 학습 표본이 fold당 12개뿐이라 Random Forest·로지스틱 회귀는 강하게 넣은 신호도 놓쳤다. 그래서 축소 LDA와 feature별 분산분석을 함께 쓴다.
- Detector choice: with ~12 training recordings per fold a Random Forest or logistic regression missed even a strong injected cue, so shrinkage LDA plus a per-feature ANOVA is used.

---

## 7. 사전 등록 확증 분석 / Pre-registered confirmatory analysis — `src/confirmatory.py`

- **H1** Rerr가 우연을 넘는가: `fixed_prediction_null` — G3로 한 번 학습한 예측은 고정하고 테스트 라벨만 참가자 단위로 1000번 섞음.
- **H2** R1 > R0, **H3** Rerr > R1: `paired_one_sided` — 짝지은 참가자 bootstrap 2000회, 단측 p.
- `holm`: 세 가설 Holm 보정. `family`: 한 과제·모델의 H1–H3. 주 분석(주석자 A × RF) 외에 강건성(logreg)·민감도(주석자 B)도 같은 표로.
- 출력: `results/confirmatory_<실험>_<프로토콜>.md/.csv`. 결과는 `PREREGISTRATION.md` "Results" 참조(2026-10-08 실행, 세 가설 모두 지지되지 않음).

- H1 uses a fixed-prediction participant permutation null; H2/H3 use a one-sided paired participant bootstrap; Holm correction over H1–H3; robustness (logistic regression) and sensitivity (annotator B) families are reported alongside. Results: see `PREREGISTRATION.md` (run 2026-10-08, none supported).

---

## 8. 결과물과 재현성 / Outputs and reproducibility

| 파일 / File | 하는 일 / What it does |
|---|---|
| `figures.py` | 결과 CSV에서 그림 3개(군집도, 이진 과제, 사람 특성 교란)와 `results/tables.md`(표 4개)를 다시 만듦. 바이트 단위로 재현 · regenerates 3 figures and 4 tables, byte-reproducible |
| `manifest.py` | `data/`·`results/` 출력의 SHA-256과 패키지 버전을 `results/MANIFEST.json`에 고정(`--freeze`)·비교(`--check`) · freezes and compares output hashes |
| `verify.py` | 모든 단계 `--check` → `pytest` → manifest 비교. `--no-manifest`는 출력이 의도적으로 바뀐 뒤에 · runs every check, tests and the hash comparison |
| `tests/test_core.py` | 단위 테스트 26개. 파일명 규칙, 라벨 규칙, 정규화 불변성, 각도, 지표, 분할, ICC, 순열, 인벤토리 키, **사전 등록 설정 해시 보호** · 26 unit tests incl. the pre-registration hash guard |

---

## 9. 탐색·도구 / Exploration and tools

| 파일 / File | 하는 일 / What it does |
|---|---|
| `explore/annotator_continuum.py` | 각 오류의 핵심 feature에서 주석자 A·B의 판정 기준점과 차이(참가자 bootstrap), 심각도 순서, 시간 구간 비율 · expert thresholds, severity ordering, temporal-segment coverage |
| `explore/camera_geometry.py` | 그룹별 카메라 기준 위치·방향·몸통 길이·시상 기울기(사전 등록 품질 점검 3) · camera geometry per group |
| `tools/fetch_all.sh` | 공식 페이지 9개 파일을 이어받기로 받고 크기 대조 후 전부 해제 · downloads, verifies and extracts the full dataset |

---

## 10. 실행 순서 / How to run

```
python -m pip install -r requirements.txt
python src/verify.py --no-manifest      # 전 단계 재생성 + 검사 + 테스트 / rebuild, check, test
python src/manifest.py --freeze         # 이 PC의 결과 해시 고정 / freeze hashes on this machine
python src/run_experiment.py --config configs/p1_confirmatory.json
python src/confirmatory.py
python src/figures.py
```

새 실험은 **새 설정 파일**로 만든다. `configs/p1_confirmatory.json`을 고치면 단위 테스트가 실패한다(사전 등록 보호).
Create a **new config file** for any new experiment; editing `configs/p1_confirmatory.json` fails the unit tests (pre-registration guard).
