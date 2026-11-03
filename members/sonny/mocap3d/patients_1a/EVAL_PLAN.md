# KERAAL 1A(환자) 평가 계획 / Evaluation plan

2026-11-03 · 1A 결과를 보기 전에 작성했다. 모든 결과는 탐색(exploratory)으로 표시한다.
Written before any 1A result was seen. All results are labelled exploratory.

## 1A로 말할 수 있는 것 / What 1A can and cannot show

- **1A에는 Vicon이 없다**(공식 readme, 폴더 확인). 따라서 환자의 **3D 정확도는 잴 수 없다.**
  *1A has no Vicon, so 3D accuracy on patients cannot be measured.*
- Kinect는 정답이 아니다. G3에서 Kinect 각도 오차는 18.7°로 우리 모델(13.9°)보다 크다. Kinect와의 일치도는 정확도가 아니라 참고값이다.
  *Kinect is not ground truth; agreement with it is not accuracy.*
- 그래서 **주 평가는 치료사 라벨에 대한 오류 판별**이다. *The primary evaluation is error detection against therapist labels.*

## 1A의 조건 차이 (확인됨) / Known differences from G3

| 항목 | G3 (학습) | 1A | 처리 |
|---|---|---|---|
| 영상 | 960×540, 깨끗함 | 480×360, **Kinect 골격선으로 보이는 주황색 선이 영상에 박혀 있음** | 선을 지운 영상(`clean`)을 주 입력으로, 원본(`raw`)을 비교 입력으로 쓴다 |
| 속도 | 30 fps | 15 fps(라벨 시간 기준, 메타데이터 10 fps는 틀림) | 2D를 30 fps로 보간한 뒤 모델에 넣는다 |
| 사람 | 건강인 3명, 연기한 오류 | 환자 6명(R1–R3 Brest, R4–R6 Roscoff), 실제 움직임 | 환자 단위로 나눈다 |
| 복장·방 | 마커 슈트, 모션캡처실 | 평상복, 작은 방 2곳 | 장소별로 따로 본다 |
| 자세 | 대부분 앉음 | 그림상 Brest는 서서, Roscoff는 앉아서로 보임 | Kinect로 측정하고 자세·장소별로 따로 본다 |

## 모델 / Models

- **merged:** ASPset + G3 3명 전원, KERAAL 비중 50%, 시드 3개. 1A는 학습에 쓰지 않는다.
- **aspset:** ASPset만 학습한 기존 모델, 시드 3개. 재활 데이터의 효과를 보기 위한 대조군이다.
- 비교 입력: **kinect**(Kinect 관절로 같은 각도 계산), **raw_2d**(2D 각도).

## 평가 / Evaluation

**E1. 주 평가: 오류 판별.** 치료사 라벨(정상 vs 오류), 기존 팀 라벨 규칙(`keraal_pipeline/src/labels.py`).
- 분류기: 기존 RQ4와 같은 각도 특징 + Random Forest. 운동별로 **환자 1명 빼기**.
- 주 지표: 주석자 A, `clean`, merged의 AUC vs kinect의 AUC. 주석자 B는 보조 지표다.
- 표는 운동별 AUC와 환자별 승패로 쓴다. 우연 수준인지는 환자 안에서 라벨을 섞는 순열 검정으로 본다.
- **녹화나 참가자 × 운동 단위를 독립 표본으로 p값을 내지 않는다.** 독립 단위는 환자 6명이다.
- 주석자 A·B의 일치도를 함께 적는다. 라벨 자체의 한계를 보여 주기 때문이다.

**E2. 골격선 영향.** `clean`과 `raw`의 차이를 E1과 E3에서 비교한다. 이 차이가 크면 `raw`의 결과는 영상 속 Kinect 선을 따라간 것일 수 있으므로 "일반 카메라 결과"로 쓰지 않는다.

**E3. Kinect 일치도(정확도 아님).** 같은 각도 정의로 r과 평균 제거 RMSE를 잰다. 값이 낮아도 어느 쪽이 틀렸는지는 알 수 없다.

**E4. 자세 분포와 내부 일관성.** Kinect로 앉은 자세 비율(몸통–넓적다리 각도 < 135°)을 G3와 비교하고, 환자·장소별로 나눈다. 정답 없이 볼 수 있는 값으로 녹화 내 뼈 길이 변동도 잰다.

## 결과별 해석 / Reading the outcome

| 결과 | 해석 |
|---|---|
| merged ≈ kinect 이상, 우연보다 높음 | 환자에서도 오류 판별에 쓸 수 있다는 근거. 3D 정확도 주장은 아니다 |
| merged < kinect | 재활 동작 일반화의 범위를 건강인·같은 방으로 좁힌다 |
| 전체가 우연 수준 | 환자 라벨을 이 특징과 표본으로 판별하지 못한다. 모델 비교 근거로 쓰지 않는다 |
| `raw`만 좋음 | 골격선 영향. 결과를 쓰지 않는다 |

## 한계 / Limits

- 환자 6명, 장소 2곳이다. 장소와 자세, 환자가 얽혀 있어 원인을 나누기 어렵다.
- 15 → 30 fps 보간과 골격선 제거는 학습 때 없던 처리다.
- 기존 사전 등록(`PREREGISTRATION.md`)과 별개의 탐색 분석이고, `configs/p1_confirmatory.json`은 건드리지 않는다.
