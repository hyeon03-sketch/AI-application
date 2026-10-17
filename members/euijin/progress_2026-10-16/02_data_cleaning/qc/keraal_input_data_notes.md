# KERAAL 모델 입력 데이터 빌드 노트 (2026-10-07)

스크립트: `keraal_parse_annotations_v2.py` (build), `check_video_alignment.py`, `summarize_model_input.py` — 위치 `C:\EJ\Keraal\`
출력: `C:\EJ\Keraal\input_data\model_input_{blazepose,kinect}.csv` + QC txt (프레임당 1행, 프레임/초 라벨, `participant_key`)

## 실제 데이터에서 확인한 사실
- 폴더: group1A/2A = annotatorA, annotatorB, blazepose, kinect, openpose, videos. annotatorA는 UTF-16, B는 UTF-8. 숨김 `.anvil` 파일 있음.
- **fps = 15**: 모든 녹화에서 Kinect 프레임 수 ÷ annotatorB 종료 시각 = 15.00. 영상 컨테이너는 10fps로 표기되나 프레임 수는 Kinect와 동일(영상 파일 메타데이터가 틀린 값으로 보임; 2A 2건은 영상 프레임이 Kinect보다 적음).
- annotatorA 시간축 = 프레임/15 (오류 없는 녹화에서 A 종료 = B 종료, 소수 둘째 자리까지 일치). annotatorB는 녹화 전체(0~끝)를 한 구간으로 라벨링 → 프레임 라벨로 부적합.
- annotatorA는 오류가 끝나는 시점에서 주석이 끝나는 녹화가 많음 → CSV `in_annotated_span`(yes/no)로 구분. 학습은 `yes` 권장.
- BlazePose JSON 115개 녹화가 중간에서 잘림(주로 Roscoff R4/R6), 6개는 거의 빈 파일(제외). `skeleton_truncated` 열로 표시.

## 데이터 규모 (QC 리포트 기준)
- Kinect: 녹화 841, 237,733행 / BlazePose: 녹화 835, 224,912행. 1A/2A 오류 프레임 6.4%(Kinect)·6.9%(BlazePose).
- 주석 구간(yes) 1A/2A 오류유형 프레임(Kinect): Error1 2,149 (BothArms 1,877 / Left 140 / Right 132), Error2 3,559 (Spine 3,476 / RightArm 83), Error3 1,148 (BothArms). 초 단위 오류 비율 6.4%.
- 참가자: 1A R1–R6, 2A S1–S6, G3 P1–P3. 2A_S4, S5는 오류 프레임 0(정상만). Error3는 R2·R3·R6에만 존재.

## 미확정 / 주의
- Group3 `BodypartIndex1~3`의 실제 부위 매핑 미확인, G3는 시간 구간 없는 약라벨(녹화 전체 동일 라벨).
- Global error vs Temporal error 중 어느 쪽이 실제 오류 시점에 가까운지 미확인 (기본 global, `--interval-track temporal`로 변경 가능).
- `Error1/2/3`의 의미는 운동별로 다를 수 있음 → (exercise_code, error_type) 조합으로 다루는 것을 권장.
- 오류 클래스 희소(LeftArm/RightArm 수백 프레임) → 부위는 Spine / Arms로 합치는 것을 우선 고려.
- 사전등록 확증분석 계획(G3 결과를 보기 전)과의 충돌 여부는 팀 확인 필요.
