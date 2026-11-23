# Mocap3D 비교 실험 결과 (2026-11-23) / Mocap3D comparison results

영상 한 대로 찍은 재활 운동에서 3D 관절 위치와 관절 각도를 얼마나 정확히 얻을 수 있는지 비교했다. 비교 대상은 Kinect 깊이 센서, 공개 모델 VideoPose3D(fine-tuning 전·후), 우리 모델 Mocap3D다.
We compare how accurately 3D joints and joint angles can be recovered from a single ordinary video of rehab exercises: Kinect depth sensor, the public VideoPose3D model (before / after fine-tuning), and our Mocap3D model.

- 실행 환경 / Run: RTX A6000 × 2, torch 2.11 (CUDA 12.8), 시드 0·1·2, VideoPose3D 20 에폭, Mocap3D 120 에폭. 총 약 1시간 50분.
- 데이터 / Data: KERAAL 그룹 3 (건강인 3명, 540개 녹화, 참가자 한 명씩 빼고 평가), ASPset-510, REHAB24-6, VIDIMU.
- **데이터·예측값·가중치·데모 영상은 이 저장소에 없다** (KERAAL CC BY-NC-SA, `RULES.md` 1절). 여기 있는 숫자는 모두 집계값이다. / No data, predictions, weights or demo video here; all numbers are aggregates.

## 1. KERAAL 그룹 3 / KERAAL group 3

| 모델 / Model | MPJPE (mm) ↓ | PA-MPJPE (mm) ↓ | 관절 각도 RMSE / Angle RMSE (°) ↓ | 각도 상관 / Angle r ↑ |
|---|---|---|---|---|
| Kinect 깊이 센서 / depth sensor | **52.8** | **45.4** | 13.4 | 0.81 |
| VideoPose3D (사전학습 그대로 / pretrained) | 243.9 | 104.5 | 20.1 | 0.62 |
| VideoPose3D (fine-tuning) | 64.3 ± 0.4 | 50.7 ± 0.1 | 12.2 ± 0.1 | 0.85 |
| **Mocap3D (ours)** | 59.1 ± 0.5 | 47.0 ± 0.3 | **10.8 ± 0.1** | **0.91** |

평균 ± 표준편차는 시드 3개. 각도 RMSE와 r은 (녹화, 각도) 쌍의 중앙값. / Mean ± SD over 3 seeds; angle values are medians over (recording, angle) pairs.

참가자별 각도 RMSE (°) / Angle RMSE per participant:

| 모델 / Model | P1 | P2 | P3 |
|---|---|---|---|
| Kinect | 10.2 | 18.7 | 13.7 |
| VideoPose3D (fine-tuning) | **9.0** | 14.4 | 13.8 |
| Mocap3D (ours) | 9.5 | **12.8** | **10.7** |

> ⚠️ **각도 기준 / Angle reference.** 여기 각도는 공유 묶음의 **Vicon 관절 점**으로 계산했다. 이전 슬라이드의 13.5° / 18.7° / 16.2°는 원본 파일의 Vicon 세그먼트 회전 기준이라 정의가 다르다. 같은 표 안에서만 비교한다. / Computed from Vicon joint points; do not mix with the earlier 13.5 / 18.7 / 16.2° (Vicon segment rotations).

## 2. 공개 데이터 / Public data (시드 3개 평균 / mean of 3 seeds)

| 모델 / Model | ASPset MPJPE (mm) ↓ | ASPset PA-MPJPE (mm) ↓ | VIDIMU r ↑ | VIDIMU RMSE (°) ↓ |
|---|---|---|---|---|
| VideoPose3D (사전학습 그대로 / pretrained) | – | 84.6 | 0.89 | 11.5 |
| VideoPose3D (fine-tuning) | 95.5 | 53.2 | **0.93** | **8.2** |
| **Mocap3D (ours)** | **77.5** | **48.4** | 0.90 | 8.8 |

VIDIMU는 걷기 제외(A04–A13). / VIDIMU without walking.

## 3. 결론을 어디까지 말할 수 있나 / How far the results go

시드 표준편차는 학습을 다시 돌렸을 때의 흔들림일 뿐, 사람이 바뀌어도 같은지는 보여 주지 않는다. 그래서 통계 단위(참가자 3명 × 운동 3개 = 9개)마다 시드를 평균한 뒤 짝지어 비교했다 (`unit_compare.json`).
Seed SD only reflects training noise. We therefore compared models over the 9 statistical units (participant × exercise), seeds averaged within each unit.

| 비교 (Mocap3D 기준) / Comparison | Mocap3D가 낮은 단위 / units lower | 평균 차이 / mean diff | Wilcoxon p |
|---|---|---|---|
| 각도 RMSE vs VideoPose3D | 8 / 9 | −1.5° | 0.074 |
| 각도 RMSE vs Kinect | 7 / 9 | −2.9° | 0.020 |
| MPJPE vs VideoPose3D | 6 / 9 | −4.7 mm | 0.20 |
| MPJPE vs Kinect | 3 / 9 | +7.0 mm | 0.36 |

- **말할 수 있다 / Supported:** 관절 각도 오차는 Mocap3D가 가장 낮고, 대부분의 참가자·운동에서 일관되게 낮다.
- **말할 수 없다 / Not supported:** 위치 정확도에서 VideoPose3D보다 확실히 낫다는 주장. P1의 운동 3개에서는 VideoPose3D가 더 낮다. 위치 오차는 Kinect가 가장 낮다.
- **한계 / Limits:** 건강인 3명, 비교 4개에 다중비교 보정 없음. 학습 조건이 다르다(Mocap3D는 처음부터 120 에폭, VideoPose3D는 사전학습 후 20 에폭). VIDIMU에서는 VideoPose3D가 약간 낫다.

옛 워크스테이션 기록(KERAAL 59.9 ± 0.3 mm, ASPset 79.5 / 49.1 mm, VIDIMU 0.91 / 8.84°)과 같은 수준으로 재현되었다. / Reproduces the original workstation results.

## 4. 파일 / Files

| 파일 / File | 내용 / Content |
|---|---|
| `SUMMARY_raw.md`, `summary.json` | `run_all.py`가 만든 원래 표와 원본 값 / raw tables and values from `run_all.py` |
| `unit_compare.json` | 3절의 단위별 값과 검정 / per-unit values and tests |
| `code/run_all.py` | 전체 실행 (check → 학습 → 평가 → summary → demo) |
| `code/vp3d_ft.py`, `code/mocap3d_ft.py` | VideoPose3D fine-tuning, Mocap3D 학습·추론 |
| `code/keraal_metrics.py` | KERAAL 지표 (모든 모델에 같은 방식) |
| `code/unit_compare.py` | 참가자 × 운동 단위 비교 (3절) |

## 5. 다시 돌리기 / Reproduce

코드는 팀 드라이브의 `Mocap3D_demo` 묶음(데이터, `VideoPose3D/`, `code_1118/` 포함) 안의 `vp3d_public/`에 넣어 실행한다. 자세한 순서는 묶음의 `README_WORKSTATION_KR.md`.
Put `code/` into `vp3d_public/` of the team-drive `Mocap3D_demo` bundle (it holds the data, `VideoPose3D/`, `code_1118/`).

```bash
python run_all.py --stages check      # CHECK PASSED
python run_all.py                     # seeds 0 1 2
python unit_compare.py                # section 3
```

**설치 주의 / Install note.** `pip install -r requirements.txt`를 할 때 ultralytics가 최신 torch(CUDA 13)로 바꿔 깔 수 있다. 드라이버가 CUDA 12.x면 GPU를 못 쓰므로 그 뒤에 드라이버에 맞는 torch와 torchvision을 함께 다시 설치한다(예: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128`). / ultralytics may pull a CUDA 13 torch; reinstall a torch + torchvision pair that matches your driver afterwards.

## 데이터 출처 / Attribution

KERAAL (https://keraal.enstb.org), CC BY-NC-SA 4.0 · ASPset-510, CC0 · REHAB24-6, CC BY-NC 4.0 · VIDIMU, CC BY 4.0. 이 폴더의 결과는 이 데이터에서 파생된 집계값으로 비영리·동일조건 조건을 따른다. / Results here are aggregates derived from these datasets and follow their non-commercial / share-alike terms.
