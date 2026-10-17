# KERAAL 규칙 기반 기준선 (Kinect, 1주 rough 버전)

관절각 → 반복 동작의 정점 검출 → 정점 각도를 임계값과 비교 → 오류 유형·부위 표시.
임계값은 KERAAL 1A/2A 데이터로 보정하고, **보정할 때와 데모에서 똑같은 `RepEngine`을 사용**합니다.

## 설치 (Windows, Python 3.10+)
```
cd C:\EJ\Keraal\keraal_rule_baseline
pip install -r requirements.txt
```

## 파일 구성
| 파일 | 역할 |
|---|---|
| `config.py` | **유일하게 수정하는 파일.** 경로, 열 이름, 운동별 규칙, 엔진 파라미터 |
| `skeleton.py` | CSV 읽기, 열 자동 탐지, Kinect 관절 어댑터 (BlazePose 어댑터는 9주차에 추가) |
| `kinematics.py` | 팔 거상각, 측굴각, 체간 회전각, 전굴각, 좌우 비대칭 |
| `rule_engine.py` | 실시간 반복/정점 상태 머신 (REST → UP → 정점 판정 → DOWN) |
| `inspect_input.py` | 1일차: 열·라벨 확인, 골격 방향 확인 그림 |
| `extract_reps.py` | 2–3일차: 전 녹화 각도 계산, 반복 검출, `reps.csv` |
| `calibrate.py` | 4일차: 운동별 임계값, AUC, LOSO 평가, G3(연기) 별도 평가 |
| `replay_demo.py` | 5–6일차: Kinect 녹화를 15 fps로 흘리는 모의 실시간 데모 |
| `selftest_synthetic.py` | 설치 확인용 합성 데이터 (KERAAL 없이 전체 흐름 테스트) |

## 일정과 실행 순서

### 0) 설치 확인 (30분)
```
python selftest_synthetic.py
python inspect_input.py selftest\model_input_synthetic.csv
python extract_reps.py --csv selftest\model_input_synthetic.csv
python calibrate.py
python replay_demo.py --csv selftest\model_input_synthetic.csv --rec G1A_R2_RTK_0
```
합성 데이터는 일부러 쉽게 만들어서 AUC = 1.0이 나오는 게 정상입니다. 끝나면 `rule_baseline_out` 폴더를 지우고 실제 데이터로 넘어갑니다.

> **2026-10-16 실제 데이터로 1–4일차 실행 완료.** `config.py`는 `model_input_kinect.csv`의 실제 열 이름
> (`sample_id`, `exercise_code`, `frame_idx`, `evaluation` …)에 맞춰져 있고, 결과는 `C:\EJ\Keraal\rule_baseline_out\`에 있습니다
> (`RESULTS_KR.md` 참고). 아래는 다시 돌리거나 설정을 바꿀 때의 절차입니다.

### 1일차 — 데이터 확인과 설정
```
python inspect_input.py
```
- 출력된 열 목록을 보고 `config.COLS`를 채웁니다. 자동 탐지가 `None`인 항목 중 **recording, error_type, body_part**는 꼭 채워야 합니다. exercise는 녹화 id에 CTK/ELK/RTK가 있으면 자동으로 찾습니다.
- 관절 열을 못 찾으면 `config.JOINT_COLUMNS`를 직접 적습니다.
- `rule_baseline_out\inspect_skeleton.png`를 엽니다.
  - 머리가 위에 있어야 합니다. 거꾸로면 `UP_SIGN = -1`
  - 관절 이름이 한 칸씩 밀려 있으면 `KINECT_INDEX_BASE = 1`
  - 좌표축 순서가 다르면 `AXES`를 수정합니다.
- 오류가 아닌 프레임의 error_type 값이 `NO_ERROR_VALUES`에 들어 있는지 확인합니다.

### 2–3일차 — 각도와 반복 검출
```
python extract_reps.py --plots 4
```
- `plots\angles_*.png`에서 다음을 확인합니다.
  - 파형이 반복 동작처럼 보이는지
  - 파란 구간(검출된 반복)이 실제 반복과 맞는지
  - 빨간 음영(전문가 오류 구간)이 어디에 있는지
- 콘솔 표에서 `reps_per_rec`가 실제 반복 수와 비슷한지 봅니다. 조시에게 영상 20건 QA를 맡기면 좋습니다.
- 반복이 0건인 녹화가 많으면 해당 운동의 `delta_start`/`delta_end`를 낮춥니다. 반복이 쪼개지면 `peak_confirm`, `plateau_frames`를 올리고 `ema_alpha`를 낮춥니다.
- **각도 선택이 맞지 않아 보이면** `EXERCISES[ex]["signal"]`을 바꿉니다. 후보는 `arm_elev_L`, `arm_elev_R`, `arm_elev_min`, `lat_bend`, `rotation`, `trunk_flex`입니다.

### 4일차 — 임계값 보정과 평가
- 기본 라벨은 **녹화 단위 전문가 판정(`evaluation`: Correct vs Incorrect)** 입니다 (`LABEL_MODE = "recording"`).
  반복 단위 라벨은 주석이 오류 끝에서 멈추는 경우가 많아 쓸 수 있는 라벨이 거의 없었습니다.
- 녹화 대표값은 `REC_FEATURE = "max_rep_value"` (가장 잘 된 반복의 정점 진폭) — 실시간 데모가 반복마다 판정하는 값과 같습니다.
```
python calibrate.py
```
- `results.csv` 주요 열
  - `AUC`: 정점 값 하나로 오류를 구분하는 능력. 팀 AUC 0.71–0.77과 비교합니다.
  - `LOSO_*`: 참가자를 하나씩 빼고 평가한 결과
  - `G3_*`: 연기 데이터에 같은 임계값을 적용한 결과
  - `thr_per_participant_sd`, `thr_group_1A/2A`: 기준선이 사람·집단마다 얼마나 다른지 (팀 논문 이야기와 연결)
- `plots\dist_*.png`: 올바른 반복과 오류 반복의 분포, 그리고 임계값 위치
- 콘솔에 나온 오류코드 제안을 보고 `config.ERROR_CODE_MAP`을 채웁니다. 예: `{"CTK": "Error1", "ELK": "Error2", "RTK": "Error2"}`
- AUC가 0.5보다 낮으면 그 운동은 신호나 판정 방향이 틀린 것입니다. `feature`를 `"raw"`로 바꾸거나 다른 signal을 시도합니다.

### 5–6일차 — 모의 실시간 데모
```
python replay_demo.py --list
python replay_demo.py --rec <녹화id 일부>
python replay_demo.py --rec <id> --no-video        (원본 영상은 기본으로 data\group*\videos 에서 자동으로 찾음)
python replay_demo.py --rec <id> --save demo_ctk.mp4 --no-show
```
- 원본 영상은 `VIDEO_ROOT`에서 자동으로 찾아 왼쪽에 함께 나옵니다. `--video 경로`로 직접 지정할 수도 있습니다.
- `--save`로 발표용 영상을 저장합니다.
- 키: `q` 종료, `space` 일시정지, `f`/`s` 속도 조절
- 화면 구성
  - 정면 골격: 오류 부위가 빨간색으로 표시됨
  - 위에서 본 어깨·골반선: RTK 회전 확인용
  - 각도 게이지: 노란 선이 임계값
  - 타임라인: 빨강 = 전문가 주석, 주황 = 규칙 판정
- CTK는 팔을 앞으로 올리는 동작이라 정면 골격에서는 짧아 보입니다. 게이지 값으로 판단하세요.

### 7일차 — 정리
- 운동별로 판정이 전문가 주석과 맞는 장면 1개, 틀린 장면 1개를 캡처하고 원인을 메모합니다.
- `results.csv` 표와 분포 그래프 3장, 시연 영상 1–2개를 준비합니다.

## 9주차 이후 BlazePose로 옮길 때
`skeleton.py`에 BlazePose 어댑터를 추가합니다. BlazePose 점을 `ShoulderLeft`, `ElbowLeft`, `HipLeft`, `SpineBase`(=양 엉덩이 중점), `SpineShoulder`(=양 어깨 중점) 같은 같은 이름으로 바꿔 주기만 하면 됩니다. 나머지(각도, 엔진, 보정, 데모)는 그대로 쓰고 `calibrate.py`만 다시 돌려 임계값을 재보정합니다.

## 주의
- 규칙은 정점 각도로 드러나는 "진폭 부족형" 오류만 다룹니다. 보상 동작이나 타이밍 오류는 놓칩니다.
- 반복 라벨은 "반복 구간 안에 주석 오류 프레임이 하나라도 있으면 오류"로 정했습니다. `in_annotated_span = no` 프레임이 절반 이상인 반복은 라벨 미상으로 제외합니다.
- 결과는 KERAAL 참가자 기준이며 의료적 판단이 아닙니다.
