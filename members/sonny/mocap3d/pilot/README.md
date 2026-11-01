# 파일럿: 일반 카메라 영상 → 3D 관절 / Pilot: single-camera video → 3D joints

연구 보고서 / Research report: [`../RESEARCH_REPORT_KR.md`](../RESEARCH_REPORT_KR.md) · [`../RESEARCH_REPORT_EN.md`](../RESEARCH_REPORT_EN.md)

ASPset-510(CC0)으로 학습한 2D→3D 모델을 바로 돌려 볼 수 있는 코드다. 데이터를 받지 않아도 1번은 실행된다.
*Code to try the 2D→3D lifter trained on ASPset-510 (CC0). Step 1 runs without downloading any data.*

## 설치 / Install

```
pip install -r requirements.txt      # numpy, torch, opencv-python, ultralytics, matplotlib, scipy
```

GPU가 있으면 빠르지만 CPU로도 된다. 처음 `video`를 실행하면 YOLO11x-pose 가중치(113 MB)를 자동으로 받는다.
*A GPU helps but CPU works. The first `video` run downloads the YOLO11x-pose weights (113 MB) automatically.*

## 1. 샘플 테스트 (다운로드 없음) / Sample test (no download)

```
python run_pilot.py sample
```

`sample/aspset_test_sample.npz`: ASPset-510 **test** 영상 4개(892프레임)의 YOLO 2D 검출과 3D 정답 / YOLO 2D detections and 3D GT for 4 ASPset-510 test views (892 frames).

기대 결과 / Expected: `ALL: 892 frames MPJPE 97.8 mm PA-MPJPE 59.3 mm`
(샘플 4개는 어려운 클립이 섞여 있어 전체 test 60개 평균 PA-MPJPE 49 mm보다 높다 / the 4 sample views include hard clips, so this is above the full-test PA-MPJPE of 49 mm.)

## 2. 내 영상으로 / Your own video

```
python run_pilot.py video my_video.mp4 out_dir
```

- 한 사람이 잘 보이는 영상 / one clearly visible person. 여러 명이면 가장 큰 사람 / with several, the largest one is used.
- 출력 / Outputs:
  - `pose3d.npz`: `joints_mm` (프레임, 17, 3), 골반 기준, 카메라 축(x 오른쪽, y 아래, z 앞), mm / pelvis-relative, camera axes, mm
  - `angles.csv`: 프레임별 팔꿈치·무릎·어깨 각도(°) / per-frame elbow, knee, shoulder angles
  - `preview.png`: 가운데 프레임의 2D 검출과 3D 골격 / 2D keypoints and 3D skeleton of the middle frame
- 관절 순서 / Joint order (`aspset_17j`): right_ankle, right_knee, right_hip, right_wrist, right_elbow, right_shoulder, left_ankle, left_knee, left_hip, left_wrist, left_elbow, left_shoulder, head_top, head, neck, spine, pelvis

## 3. 전체 ASPset-510 평가 / Full ASPset-510 evaluation

1. 데이터 받기 / Download: <https://archive.org/details/aspset510> (23.4 GB, CC0) → 압축 해제 / extract
2. 2D 검출 / 2D detection: `python ../detect2d.py <ASPset root> <det dir>`
3. 평가 / Evaluate: `python run_pilot.py aspset <ASPset root> <det dir>` → 기대값 / expected MPJPE ≈ 85 mm, PA-MPJPE ≈ 50 mm

## 4. 재활 데이터(KERAAL)와 합친 모델 / The merged rehab model (KERAAL)

보고서의 핵심 결과(KERAAL 관절 위치 오차 223 → 70 mm, Kinect보다 정확한 각도)는 KERAAL을 학습에 넣은 모델이다.
*The report's main result (KERAAL error 223 → 70 mm, angles better than the Kinect) comes from a model trained with KERAAL.*

- **KERAAL은 CC BY-NC-SA라서 원본, 보정 결과, KERAAL로 학습한 가중치는 이 저장소에 없다** / KERAAL is CC BY-NC-SA, so its raw data, calibration outputs and KERAAL-trained weights are **not** in this repo.
- 재현 / Reproduce: KERAAL 받기 / get KERAAL (<https://github.com/nguyensmai/KeraalDataset>) → `keraal_eval.py detect` → `keraal_calib.py` → `merge_train.py` (명령은 보고서 9절 / commands in report §9).

## 파일 / Files

| 파일 / File | 내용 / Content |
|---|---|
| `run_pilot.py` | 파일럿 실행 (`sample`, `video`, `aspset`, `--check`) / pilot entry point |
| `make_sample.py` | 샘플과 fp16 가중치를 만든 스크립트 / builds the sample and fp16 weights |
| `weights/lifter_aspset_fp16.pt` | ASPset만으로 학습한 모델 (det 입력, root 정규화, seed 0, 25 MB) / ASPset-only lifter |
| `sample/aspset_test_sample.npz` | ASPset test 샘플 (CC0) / ASPset test sample |
| `../aspset.py`, `../train_lift.py`, `../keraal_eval.py` | 파일럿이 쓰는 공통 코드 / shared code used by the pilot |

라이선스 / Licences: ASPset-510 CC0 1.0 (Nibali et al. 2021) · YOLO11 (Ultralytics, AGPL-3.0).
