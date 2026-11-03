# 팀 역할 분배 (11/3 – 11/8) / Team tasks

작성 Sonny, 2026-11-03. 배경: [`patients_1a/RESULTS.md`](patients_1a/RESULTS.md) (1A 첫 결과), [`accuracy_loop/REPORT.md`](accuracy_loop/REPORT.md) (정확도 점검).
기존 역할표(`Dataset Review_KR.md` 9절)보다 **이 문서가 우선**이다. 기존 과제 중 겹치거나 밀리는 것은 표에 적었다.

## 지금 알게 된 것 (3줄)

1. 1A는 Vicon이 없고, 녹화 단위 오류 라벨이 환자마다 한쪽으로 몰려 있어 **오류 판별로는 모델 비교가 안 된다.** CTK에서만 비교 가능했고 우리 ≈ Kinect.
2. 재활 데이터(G3)로 학습하면 환자 영상에서도 Kinect와 더 잘 맞는다 (r 0.46 → 0.58).
3. 1A·2A 영상의 주황색 골격선은 반드시 지워야 한다 (`g1a.py`의 `clean`). 1A 환자 6명은 모두 **앉아서** 운동했다.

## 역할 / Tasks

| 사람 | 과제 | 결과물 | 기한 |
|---|---|---|---|
| **Roshini** (프로그래밍) | **R1. 2A 실행.** `g1a.py`의 `compute_angles`·`labels`는 지금 `group1A`와 `G1A-Kinect-` 파일 이름에 고정돼 있다 → group 인자로 바꾸고 2A에 `detect clean group2A` → `angles` → `report`. 1A와 Kinect 일치(r, RMSE)를 나란히 비교 (환자 효과 vs 방·카메라 효과) | PR + 표 | 11/6 |
| | **R2. 오류 구간 분석.** 녹화 단위 대신, 주석자 A가 표시한 오류 구간(temporal error)과 같은 녹화의 정상 구간을 비교. 네 초 단위 Kinect 모델(`roshini/kinect-model`) 방식을 그대로 쓰고, 입력만 Kinect 각도 vs 우리 3D 각도로 바꿔 AUC 비교. 환자 간 차이를 피할 수 있는 유일한 방법 | PR + 표 | 11/8 |
| | 기존 R-a(무릎–목 스케일 MPJPE), R-b(공정 비교 재실행)는 R1·R2 뒤로 미룬다 | | |
| **Euijin** (데이터) | **E3. 오류 구간 표.** 1A·2A 녹화마다 주석자 A·B의 오류 구간 수, 총 길이(초), 오류 종류. R2의 입력이 된다. 녹화 단위 라벨이 환자마다 한쪽으로 몰린 것(RESULTS.md 1절 표)도 원본 주석으로 한 번 확인 | `temporal_errors.csv` (**로컬, GitHub 금지**) + 요약 메모 | 11/5 |
| | **E4. 골격선 제거 품질 확인.** `python g1a.py check-mask <png>`로 나온 원본/제거 비교 그림을 녹화 20개 정도 눈으로 보고, 흔적이 많이 남은 녹화 목록 작성 | 메모 (그림은 로컬만) | 11/6 |
| | **E5. 팀 문서 수정.** "1A는 서서 운동"이라고 쓴 곳(`keraal_pipeline/explore/video_check/README.md`, `PROGRESS_AND_PRESENTATION.md`)을 RESULTS.md 4절의 자세 표에 맞게 고치기 | PR | 11/6 |
| | 기존 E2(1A/2A 해상도·Kinect 프레임 1:1)는 1A 부분이 확인됨: 1A Kinect·주석은 **15 fps**. 2A만 확인 | 메모 | 11/6 |
| **Joshi** (코딩 없음) | **J2. OpenCap 조사** (기존 과제 유지). 피드백의 "일반화 주장 전에 OpenCap 필요"에 바로 답하는 과제다 | 1쪽 메모 | 11/6 |
| | **J3. 영어 보고서 읽기.** `Mocap3D_Research_Report_EN.pdf`와 `patients_1a/RESULTS.md`의 영어 부분을 읽고, 어색한 영어와 이해 안 되는 점 5개 | 질문·수정 목록 | 11/6 |
| **Sonny** | 피드백 아이디어 1 (재활 데이터 10/25/50% 곡선), 아이디어 3 (BlazePose 3D vs Vicon), 공유 파일 전달, PR 리뷰 | 표 | 11/8 |

## Roshini: 실행 방법 / How to run

1. Sonny가 드라이브로 보내는 `share_roshini_1a.zip`(290 MB: 1A 모델 가중치 3개, ASPset 모델 3개, 1A 2D 검출 결과)을 받는다. **KERAAL 파생물이라 GitHub에 올리지 않는다.**
   - `g1a/…` → `E:/KERAAL_mocap3d/g1a/…`
   - `aspset_runs/det_root_s*/best.pt` → `E:/ASPset510_data/runs/det_root_s*/best.pt`
   - 다른 경로를 쓰면 `g1a.py` 맨 위 `ROOT`, `OUT`, `YOLO`, `ASPSET`만 바꾸면 된다.
2. KERAAL 원본은 `E:/KERAAL_data/extracted` (`group1A`, `group2A` 폴더). YOLO 가중치 `yolo11x-pose.pt`는 ultralytics에서 받는다.
3. 패키지: `torch`, `ultralytics`, `opencv-python`, `scikit-learn`, `numpy`.
4. `cd members/sonny/mocap3d/patients_1a` → `python g1a.py --check` (데이터 없이 도는 자체 검사) → 그다음 위 명령.
5. 2D 검출은 RTX 3090에서 녹화 250개에 약 30분 (입력 640, fp16). 학습과 동시에 돌리면 GPU 메모리가 모자라 멈춘다.

## 규칙 (그대로)

- KERAAL 원본·영상·프레임 그림·모델 가중치·검출 결과는 GitHub 금지 (CC BY-NC-SA). 저장소에는 코드와 집계 표만.
- 방법 선택은 검증 점수로만. 1A 수치는 탐색 결과로 표시하고, 녹화나 칸 단위 p-value는 쓰지 않는다 (독립 단위 = 사람).
- `configs/p1_confirmatory.json` 수정 금지.

---

*English summary.* Roshini: (R1) generalise `g1a.py` to group2A and compare Kinect agreement 1A vs 2A, due 11/6; (R2) temporal-error segment analysis within recordings, our 3D angles vs Kinect angles, reusing the per-second Kinect model, due 11/8. Euijin: (E3) per-recording temporal-error table (local only), 11/5; (E4) visual check of skeleton-overlay removal, 11/6; (E5) fix team docs that say 1A patients stood (they were all seated), 11/6. Joshi (no coding): (J2) OpenCap survey, (J3) read the English report and list unclear points, 11/6. Data for Roshini comes as a private zip, never via GitHub.
