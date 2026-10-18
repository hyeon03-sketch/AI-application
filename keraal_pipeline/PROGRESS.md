# KERAAL 파이프라인 진행 기록

설계 문서: `../KERAAL_Pipeline_KR.pdf`.

> **현재 상태 (2026-10-09): 확증 분석 완료, 재점검 중단(14회 모두 통과).** Group 3를 넣어 전체 검증을 통과했고, 사전 등록한 확증 분석을 실행했다(H1-H3 모두 지지되지 않음). 결과는 PREREGISTRATION.md "Results"와 아래 회차 기록에 있다. 재점검 루프는 사용자 요청으로 해제했다.
전체 검증 명령: `python src/verify.py` (모든 단계 `--check` → 단위 테스트 → 결과 해시 비교)
환경: `requirements.txt` (Python 3.12.3). 출력을 **의도적으로** 바꾼 회차에는 `python src/verify.py --no-manifest` 후 `python src/manifest.py --freeze`로 다시 고정하고, 이유를 회차 기록에 적는다.

## 데이터 (raw/)

| 경로 | 내용 | 비고 |
|---|---|---|
| raw/group1A | annotatorA, annotatorB, kinect 각 250개 | 2026-10-01 keraal.enstb.org에서 스트리밍(영상 제외) |
| raw/group2A | annotatorA, annotatorB, kinect 각 51개 | 같음 |
| **raw/group3/kinect** | **Group 3 Kinect 골격 540개 (188 MB)** | **2026-10-06 받음. 아래 절 참고** |
| ~~raw/group3.tar.xz.part~~ | (2026-10-06 E:\KERAAL_data\archives\group3.tar.xz 로 이동) | C 드라이브 공간 확보 |
| **E:\KERAAL_data\archives** | **공식 페이지의 9개 파일 원본 전부** (약 25.5 GB) | 2026-10-06 `tools/fetch_all.sh`로 받음, 서버 크기와 대조 |
| **E:\KERAAL_data\extracted** | **전 그룹 전부 해제**(Kinect, BlazePose, OpenPose, 영상, 주석, G3 Vicon, 샘플, Poppy) | 파이프라인은 `data_root.txt`로 이 경로를 읽는다 |
| raw/g3_list.txt | Group 3 파일명 목록 | group3.tar.xz 앞 250 MB에서 추출 |
| raw/sample | 공식 샘플(영상 제외) | G3 Kinect 6개 포함 |

원본은 CC BY-NC-SA. 외부에 올리지 않는다.

## 전체 데이터셋 (2026-10-06): 위치와 파이프라인 연결

- **왜 E 드라이브인가**: C 드라이브 여유가 4.5 GB까지 줄어(다른 프로그램 사용분) 전체를 받을 수 없었다. E(새 볼륨)에 244 GB 여유가 있어 원본 압축본까지 전부 그곳에 둔다. 다른 프로젝트 데이터는 지우지 않았다.
- **받는 방법**: `bash tools/fetch_all.sh /e/KERAAL_data` — 이어받기 가능, 각 파일 크기를 서버 값과 대조, 끝나면 전 그룹을 `extracted/<group>/`에 영상까지 해제. 로그 `E:\KERAAL_data\fetch.log`. 다시 실행해도 끝난 파일은 건너뛴다.
- **파이프라인 연결**: `src/inventory.py` → `data/inventory.csv`. 전 그룹 × 전 모달리티를 녹화 하나당 한 행으로 정리한다(키는 master_index와 같은 규칙, 1B·2B는 참가자 칸이 비어 있음).
  - 검사: 그룹별 녹화 수가 공식 값(1A 250, 1B 1631, 2A 51, 2B 151, 3 540)과 일치, 모든 파일명 해석, **raw/의 Kinect 사본이 전체 배포본과 바이트 단위로 동일**.
  - 데이터 경로: 환경변수 `KERAAL_DATA` → `data_root.txt` → 기본값 `E:/KERAAL_data/extracted`. 경로가 없는 PC(팀원)에서는 SKIPPED로 통과하고 raw/ 사본을 그대로 쓴다.
- **사전 등록과의 관계**: 확증 분석 경로(index.py 이하)는 계속 raw/의 Kinect 사본만 읽으므로 바뀌지 않는다. 전체 데이터는 RESEARCH_IDEAS.md와 팀 브리핑 8절의 탐색(Vicon 측정 오차, 2B 세션 분포, BlazePose, 영상 확인)에 쓴다.
- **1B의 한계(확인됨)**: 파일명에 환자 ID가 없다. 환자별 분석은 저자에게 대응표를 받기 전에는 불가.

### 다운로드 결과 (2026-10-06 16:24–18:30, 로그 `E:\KERAAL_data\fetch.log`, 오류 0건)
- `archives\` 24 GB: 9개 파일 모두 서버 크기와 일치(group3는 C에서 옮김).
- `extracted\` 35 GB: 전 그룹 해제. `python src/inventory.py --check` 통과:

  | 그룹 | 녹화 | Kinect | BlazePose | OpenPose | 영상 | 기타 |
  |---|---|---|---|---|---|---|
  | 1A | 250 | 250 | 250 | 250 | 250 | 주석 A·B 각 250 |
  | 1B | 1,631 | 1,631 | 1,631 | 1,631 | 1,631 | 녹화별 점수 파일 391개 |
  | 2A | 51 | 51 | 51 | 51 | 51 | 주석 A·B 각 51 |
  | 2B | **149** | 149 | 149 | 149 | 149 | |
  | 3 | 540 | 540 | 540 | 540 | 540 | Vicon 540 |

- 공식 문서와 다른 점: **2B는 151개가 아니라 149개.** 1B의 `kinect/results/*_res.txt` 391개는 녹화가 아니라 녹화별 점수 기록(전체·구간·관절별 점수, 원 논문의 GMM 기준선 출력으로 보임) → `baseline_result` 열로 연결. 그룹마다 들어 있는 `readme_files_format.txt`와 빈 `res_res.txt`는 무시 목록.
- raw/의 Kinect 사본 841개가 전체 배포본과 바이트 단위로 동일.
- C 드라이브는 Group 3 압축본을 옮기면서 여유 13 GB로 늘었다.

### 전체 검증을 다시 돌리기 전에 (중요)
- Group 3가 raw/에 들어와 있으므로 `python src/verify.py`를 돌리면 index·preprocess·features가 G3를 포함해 다시 만들어지고, trial 교란 점검이 G3로 실제 실행된다(사전 등록에서 확증 분석 전에 하기로 한 단계라 문제없음).
- 시험용 설정 `configs/p4_smoke.json`은 P4만 돌도록 바꿨다. P1 결과를 확증 분석보다 먼저 계산하지 않기 위해서다(PREREGISTRATION.md 변경 기록에 남김).
- `configs/main_binary.json`은 P1을 포함하므로 **확증 분석 뒤에만** 실행한다.
- 출력이 의도적으로 바뀌므로 `--no-manifest`로 검증한 뒤 `manifest.py --freeze`로 다시 고정한다.

## 팀 정제본 리뷰 (input_data.zip, 2026-10-08)

- 내용: 팀이 만든 프레임 단위 모델 입력 표(`model_input_kinect.csv` 841녹화·237,733행, `model_input_blazepose.csv` 835녹화·224,912행), QC 리포트, 영상 정렬표. 1B·2B는 라벨이 없어 제외.
- 원본 대조(직접 확인): Kinect 값은 가공하지 않은 원본 그대로이고 841녹화 모두 프레임 수·첫/끝 프레임 값이 우리 raw/와 일치. 프레임 라벨은 주석자 A의 Global error 구간에서 만들어졌다(118,588프레임 중 21개만 경계에서 다름).
- **fps = 15 확인**: 프레임 수 ÷ 주석자 B 종료 시각 = 15.00(판독 가능한 299개 전부). 우리가 미확정으로 두었던 값이다. 우리 비율이 들쭉날쭉했던 이유는 주석자 A가 녹화 끝까지 주석하지 않는 경우가 많기 때문이었다. 주석자 B 파일 2개(G2A-RTK-S1-Roscoff-050, G2A-RTK-S6-Roscoff-077)는 종료 시각이 깨져 있다("tart:").
- 우리 파이프라인과 다른 점: (1) 2A의 S1을 Brest·Roscoff 구분 없이 한 사람(2A_S1)으로 묶음 — 동일인 확인 필요. (2) 주석자 B 라벨이 없다(A/B 기준점 분석에는 쓸 수 없음). (3) 과제가 프레임·초 단위 위치 찾기라 녹화 단위 확증 분석과 다르다. (4) Incomplete·Motionless 녹화와 Other 오류 프레임이 들어 있어 학습 전에 걸러야 한다.
- 활용: 확증 분석은 기존 경로 유지. 이 표는 시간 구간 분석(RESEARCH_IDEAS B)과 BlazePose 비교(D)의 출발점으로 쓴다.

## Group 3 데이터: 위치와 활용 계획

### 어디에 받았나
- **Kinect 골격**: `keraal_pipeline/raw/group3/kinect/` — 540개 파일, 188 MB. 파일명 그대로(`G3-Kinect-CTK-P1T1-Unknown-C-0.txt` 형식).
- **원본 압축본**: `keraal_pipeline/raw/group3.tar.xz.part` — 8.71 GB. 서버가 알려준 크기(8,714,472,496 B)와 정확히 같아 완전한 파일이다. 영상·OpenPose·BlazePose·Vicon이 들어 있지만 풀지 않았다.
  - 이 파일은 지금 연구에 필요 없다. C 드라이브 여유가 21 GB(98% 사용)뿐이라 지우는 것을 권하지만, 영상으로 B1–B3 의미나 fps를 확인할 계획(백로그 10)이 있으면 그 전까지 둔다. **삭제 여부는 사용자가 결정.**
- 받는 방법: `curl -C -`(이어받기 가능)로 압축본 저장 → `tar -xJf group3.tar.xz.part -C group3 --wildcards 'kinect/*'`. 다운로드 약 28분, Kinect 압축 해제 약 7분.

### 받은 직후 확인한 것 (결과는 보지 않은 데이터 품질 확인만)
- 파일 540개, 이름이 모두 `G3-Kinect-(RTK|ELK|CTK)-P[1-3]T[1-3]-Unknown-(C|E[1-3]B[1-3])-[0-4].txt` 규칙에 맞음(불일치 0개).
- 운동 × 클래스마다 정확히 45개(C·E1·E2·E3 × RTK·ELK·CTK) — `g3_list.txt` 목록과 일치.
- 표본 파일 모두 프레임당 175열(Kinect V2 관절 25개 × 7값).
- **골격 값으로 어떤 feature·모델·점수도 계산하지 않았다.** 사전 등록(PREREGISTRATION.md)의 "Group 3를 보기 전" 조건이 확증 분석에 대해 여전히 유지된다.

### 이 데이터로 할 일 (재개할 때 이 순서로)
Group 3는 **학습용**이다. 테스트용 1A·2A는 이미 있으므로, 이것으로 주 프로토콜 P1(건강인이 연기한 오류로 학습 → 환자·건강인의 실제 오류로 테스트)에 필요한 라벨 데이터가 모두 갖춰졌다. 1B·2B는 라벨이 없어 받지 않는다.

1. **파이프라인에 넣기**: `python src/verify.py --no-manifest`
   - index가 `raw/group3/kinect/`를 자동으로 찾아 540행에 Kinect 경로를 채우고, preprocess·features·splits가 G3를 포함해 다시 만든다.
   - 출력이 의도적으로 바뀌므로 그 뒤 `python src/manifest.py --freeze`로 다시 고정하고 이유를 회차 기록에 적는다.
   - preprocess `--check`의 몸통 길이·heading 기준이 G3에서도 통과하는지 확인한다(G3 샘플 6개는 통과했었음).
2. **사전에 정한 데이터 품질 점검** (PREREGISTRATION.md, 확증 모델 전에):
   - `python src/trial_confound.py` — G3는 trial k에 C와 Ek만 있어 세션 차이가 오류 라벨로 샐 수 있다. Correct 녹화만으로 trial을 맞히는지 본다. 교란이 보이면 계획대로 보고 **하고**, 플래그된 feature를 뺀 결과도 함께 낸다.
   - G3 전체 540개로 카메라 높이·pitch를 다시 잰다(회차 3은 샘플 6개 기준: 골반 높이 −0.55 m, 척추 기울기 −8°로 테스트 세션과 달랐다).
3. **확증 분석 (사전 등록, 설정·코드 변경 금지)**:
   - `python src/run_experiment.py --config configs/p1_confirmatory.json`
   - `python src/confirmatory.py` → `results/confirmatory_p1_confirmatory_P1.md`
   - 과제 CTK 정상 vs E1+E3, 주 라벨 주석자 A, 주 모델 Random Forest. H1 오류별 feature > 참가자 순열 null, H2 정규화 > 원본, H3 오류별 > 정규화, Holm 보정.
4. **탐색 분석 (결과에 "탐색"으로 표시)**:
   - `python src/run_experiment.py --config configs/main_binary.json` (P4에 P1이 추가됨), `python src/permutation_null.py --config configs/main_binary.json --protocol P1 ...`(P1용 null은 고정 예측 방식이 맞으므로 confirmatory.py의 함수를 쓰도록 확장 필요)
   - `python src/rf_baseline.py --protocol P2`(G3 안에서 참가자 1명씩 빼기), `--protocol P3_group`, `--protocol P3_random`(참가자 누수가 성능을 얼마나 부풀리는지)
   - `python src/figures.py` — P1 그림(fig2_main_binary_P1)이 자동으로 추가된다. 혼동 행렬·P4 vs P1 비교 그림은 백로그 26.
5. 결과를 PROGRESS.md 회차 기록과 PREREGISTRATION.md 기준에 맞춰 정리한다.

### 주의
- 다음에 `python src/verify.py`(manifest 포함)를 그냥 돌리면 **manifest 검사가 실패한다.** G3가 들어오면서 master_index·features 등이 바뀌기 때문이며 정상이다. 위 1번 순서(`--no-manifest` → `--freeze`)를 따른다.
- 팀의 정제본이 따로 오면, 원본과 파일 수·라벨 분포가 같은지 먼저 비교하고 어느 쪽을 쓸지 정한 뒤 진행한다.

## 1단계 체크리스트

- [x] (1) index.py → data/master_index.csv
- [x] (2) labels.py → data/labels.csv
- [x] (3) preprocess.py → data/skeleton_raw.npz, data/skeleton_T100.npz
- [x] (4) features.py → data/features_T100.npz, data/feature_names.json
- [x] (5) splits.py → data/splits.json
- [x] (6) evaluate.py → results/baseline_majority_P1.csv
- [x] (7) RF 기준선, 1A leave-one-patient-out 시험 실행 → src/rf_baseline.py, results/rf_P4_*.csv
- [x] (8) G3 인덱스 + trial 교란 점검 코드 → src/trial_confound.py (G3 골격 데이터 도착 전까지 실제 실행 보류)

**1단계 완료(2026-10-05).** 다음 회차부터 업그레이드 백로그를 진행한다.

### G3 골격 데이터가 도착하면 할 일
(2026-10-06 도착 — 최신 계획은 위 "Group 3 데이터: 위치와 활용 계획" 절이 우선한다.)
1. Kinect 파일을 `raw/group3/kinect/`에 넣는다(파일명 그대로). → 완료
2. `python src/verify.py` — index가 자동으로 G3 Kinect 경로를 채우고 preprocess·features가 G3를 포함한다. (preprocess `--check`의 기대 개수는 경로가 있는 행 수를 따르므로 그대로 동작해야 한다.)
3. `python src/trial_confound.py` — 세션 교란 결과 확인. 교란이 보이면 정규화 강화 후 재확인.
4. **확증 분석(사전 등록)**: `python src/run_experiment.py --config configs/p1_confirmatory.json` → `python src/confirmatory.py`. 이 단계 전에 설정·코드를 바꾸지 않는다(PREREGISTRATION.md).
5. 탐색 분석: `python src/run_experiment.py --config configs/main_binary.json`(P1 포함), `python src/rf_baseline.py --protocol P2`, `--protocol P3_group`, `--protocol P3_random`.

## 회차 기록

### 회차 1 — 2026-10-04 · (1) index.py 완료

- `src/index.py` 작성. 실제 파일명 규칙(`G1A-Kinect-CTK-R1-Brest-022.txt`, `G1A-CTK-R1-Brest-022.anvil`, `G3-Kinect-CTK-P1T1-Unknown-E1B1-0.txt`)과 주석자별 인코딩(A=UTF-16, B=UTF-8)을 처리한다.
- Group 3는 `raw/group3/kinect/`가 생기면 그 파일을, 없으면 `raw/g3_list.txt`의 파일명을 쓴다(`label_source` 열에 표시). 지금은 파일명만 있어 `kinect_path`가 비어 있다.
- 참가자 키는 `그룹-참가자-장소`. 2A의 S1이 Brest와 Roscoff에 따로 있어 동일인 여부가 확인될 때까지 분리해 둔다.
- 검증 출력:
  ```
  wrote data/master_index.csv (841 rows)
  recordings per group: {'1A': 250, '2A': 51, '3': 540}
  IGNORED: raw/group1A/annotatorA/.anvil (외 3개)
  CHECK PASSED
  ```
- 발견: 배포본의 주석 폴더 4곳에 이름이 `.anvil`뿐인 파일이 하나씩 있다. 녹화 ID가 없어 매칭 불가 → 무시 목록으로 기록. 문서의 1A "249개"와 실제 250개의 차이와는 별개다.
- 발견: 주석자 A 파일 3개(`G1A-CTK-R3-Brest-072`, `-083`, `G1A-CTK-R4-Roscoff-053`)는 Global error 트랙에 `<el>`이 2개다. 라벨이 있는 첫 번째 것을 쓴다.
- 다음: (2) labels.py

### 회차 2 — 2026-10-04 · (2) labels.py 완료

- `src/labels.py` 작성 → `data/labels.csv`. 클래스는 운동별 C/E1/E2/E3, 그 외는 `EXCL`과 제외 사유(incomplete, motionless, other_error, incorrect_without_type)를 남긴다.
- 열: `label_A`, `label_B`, `label_consensus`(A와 B가 같고 둘 다 제외가 아닐 때만), 각각의 CTK E1+E3 병합판 `*_ctk13`(라벨 `E13`), 오류 라벨의 `severity_A/B`.
- Group 3는 파일명 라벨 하나뿐이라 세 열에 같은 값을 넣는다.
- `src/verify.py` 추가: 단계별 `--check`를 순서대로 돌리는 전체 검증 스크립트. 새 단계가 생기면 `STAGES`에 추가한다.
- 검증 출력(설계 PDF 1절 표와 일치):
  ```
  label_A: RTK (73,4,6,0 | 제외 18)  ELK (36,0,43,0 | 13)  CTK (61,26,1,17 | 3)
  label_B: RTK (58,5,27,0 | 11)      ELK (17,0,60,0 | 15)  CTK (63,32,4,6 | 3)
  label_consensus: RTK (53,3,6,0 | 39)  ELK (15,0,41,0 | 36)  CTK (55,21,1,6 | 25)
  CTK E1+E3 병합(A): C 61, E13 43, E2 1
  VERIFY PASSED: index.py, labels.py
  ```
- 발견: consensus를 쓰면 테스트셋이 크게 줄어든다(RTK 83→62, ELK 79→56, CTK 105→83). 특히 CTK E3는 17→6. consensus는 "깨끗한 라벨" 보조 분석으로 두고, 주 결과는 A와 B 각각으로 내는 편이 낫다.
- 발견: CTK에서 E1+E3를 합치면 오류 클래스가 43개가 되어, CTK가 사실상 Correct vs "팔을 충분히 올리지 않음" 이진 문제(61 vs 43)가 된다. ELK(36 vs 43)와 함께 검정력이 가장 좋은 두 비교다.
- 다음: (3) preprocess.py

### 회차 3 — 2026-10-04 · (3) preprocess.py 완료

- `src/preprocess.py` 작성(numpy만 사용). Kinect 175열 → 관절 위치 `(T, 25, 3)`.
- 정규화 순서: SpineBase 중심 이동 → 수직축 회전 → 몸통 길이로 스케일 → 5프레임 이동평균 → T=100 리샘플링.
- **설계 변경(의도적)**: 설계 PDF의 "어깨선 정렬" 대신 **골반선(HipLeft→HipRight) 중앙값 기준, 녹화당 한 번의 고정 회전**을 쓴다. 프레임마다 어깨선으로 정렬하면 RTK Error2("몸통 회전 부족")의 신호 자체가 지워지기 때문이다. 논문 Methods에 이 이유를 적어야 한다.
- 저장: `skeleton_raw.npz`(녹화별 원본 길이), `skeleton_T100.npz`(`raw`=리샘플링만, `norm`=전체 정규화, 둘 다 `(301, 100, 25, 3)`; heading, 몸통 길이, 프레임 수 포함). R0(raw)와 R1(정규화)을 같은 길이로 비교할 수 있다.
- 검증(`--check`): 비유한 값 0, 전부 0인 프레임 0, 정규화 후 SpineBase 원점, 몸통 길이 1±0.05, 골반선이 +x와 2° 이내, 몸통 길이 0.25–0.8 m. 샘플의 G3 Kinect 6개도 같은 코드로 통과.
- 검증 출력:
  ```
  raw/norm (301, 100, 25, 3), Group 3 pending 540
  카메라 좌표의 평균 SpineBase (x, y, z) m:
    1A  [0.10 -0.19 3.20]   2A  [0.03 -0.31 2.91]   G3 샘플  [0.31 -0.55 3.06]
  heading: 1A -2.5° (sd 4.4)  2A -1.7° (sd 2.9)  G3 샘플 -6.6°
  몸통 길이: 1A 0.464 m  2A 0.475 m  G3 샘플 0.448 m
  VERIFY PASSED: index.py, labels.py, preprocess.py
  ```
- 발견: **세션마다 카메라 위치가 다르다.** G3 샘플의 SpineBase 높이(y)는 -0.55 m로, 1A(-0.19)·2A(-0.31)보다 25–35 cm 낮다. raw 좌표(R0)는 학습(G3)과 테스트(1A·2A) 사이에 이 차이를 그대로 안고 있으므로, R0 vs R1 비교가 논문의 핵심 근거가 될 수 있다.
- 발견: **카메라 pitch는 보정하지 못했다.** 척추 벡터의 y-z 평면 기울기가 1A -18°, 2A -17°, G3 샘플 -8°로 약 10° 다르다. 카메라 pitch인지 자세 차이인지 분리하려고 다리 벡터(발목 중점→SpineBase)를 봤으나, 척추와 다리 사이 각이 -32~-39°로 해부학적으로 맞지 않아 Kinect 하체 관절은 기준으로 쓸 수 없다. G3 샘플은 P1 한 명 6개뿐이라 G3 전체 데이터로 재확인이 필요하다.
- 다음: (4) features.py

### 회차 4 — 2026-10-04 · (4) features.py 완료

- `src/features.py` 작성 → `data/features_T100.npz`(표현별 `(301, 100, F)`), `data/feature_names.json`(feature 이름과 평면 태그).
- 표현: R0 raw 75 · R1 정규화 75 · R2 관절각 10 · R3 +속도 20 · R4 +좌우 차이 24 · Rerr 오류별 9 · Rerr_d(Rerr에서 녹화 첫 10% 평균을 뺀 것) 9.
- R2 관절각: 팔꿈치 굴곡 L/R, 어깨 거상 L/R(몸통 아래 방향 대비), 팔 벌림 L/R(어깨선 대비), 몸통 회전(어깨선-골반선, 수평면), 척추 기울기 정면·시상, 목 각도.
- 백로그 12 반영: feature마다 평면 태그(invariant / frontal / horizontal / sagittal / vertical / camera). R4는 invariant 17, frontal 2, horizontal 2, sagittal 2, vertical 1. 카메라 pitch에 민감한 것은 sagittal과 vertical이다.
- 속도는 fps를 모르므로 "정규화 시간 기준"(리샘플링 후 차분 × T).
- 검증(`--check`): 표현별 shape·이름 수, 비유한 값 0, 각도 [0, 180], **임의 3D 회전 + 이동 + 스케일을 가해도 invariant 태그 feature가 1e-3° 이내로 불변**.
- 검증 출력과 기술 통계(주석자 A, 녹화별 요약의 클래스 중앙값). feature 정의는 오류 문구만 보고 먼저 고정했고, 이 숫자는 테스트 데이터이므로 feature 조정에 쓰지 않는다:
  ```
  RTK 몸통 회전 범위:          C 45.1° (n=73)  vs  E2 21.2° (n=6)
  ELK 정면 척추 기울기 범위:   C 30.5° (n=36)  vs  E2 21.1° (n=43)
  CTK 왼쪽 어깨 거상 최대:     C 124.3° (n=61) vs  E1 107.9° (n=26), E3 113.0° (n=17)
  CTK 손목 간 거리/어깨 너비:  C 2.53 vs E2 2.58 (n=1, 판단 불가)
  VERIFY PASSED: index.py, labels.py, preprocess.py, features.py
  ```
- 발견: 오류 정의에 맞춘 feature가 모두 예상한 방향으로 차이를 보인다(회전 부족 → 회전 범위 절반, 기울기 부족 → 기울기 범위 감소, 팔 덜 올림 → 거상각 감소). 단, ELK와 CTK는 분포가 겹치므로 실제 분류 성능은 (7)에서 확인해야 한다.
- 발견: CTK의 E1과 E3는 같은 feature에서 비슷한 값(108° vs 113°)을 보여, 두 오류를 합치는 `ctk13` 설정의 근거가 하나 더 생겼다.
- 다음: (5) splits.py

### 회차 5 — 2026-10-04 · (5) splits.py 완료

- `src/splits.py` 작성 → `data/splits.json`(녹화 키 목록. 운동과 라벨 열 선택은 학습 시점에 거른다).
- 프로토콜:
  - **P1**: G3 540 학습 → 1A 250, 2A 51 테스트(따로 보고). G3 골격 도착 전까지 실행 보류.
  - **P2**: G3 안에서 참가자 1명씩 빼는 3-fold(각 180개). 실행 보류.
  - **P3_group**: 라벨 있는 전체 데이터에서 참가자 단위로 약 20%를 테스트로. seed 0–4.
  - **P3_random**: 같은 seed의 P3_group과 **(그룹, 운동, 라벨) 층별 개수가 정확히 같은** 테스트셋을 참가자 무시하고 무작위로 뽑는다.
  - **P4**(추가): 1A 안에서 환자 1명씩 빼는 6-fold. 지금 바로 돌릴 수 있어 (7)의 시험 실행에 쓴다.
- **설계 수정**: 처음엔 P3_random을 단순 층화 80:20으로 만들었는데, P3_group의 테스트 비율이 seed마다 21–29%로 흔들리고 G3 참가자 포함 여부도 달라서 둘을 비교하면 누수 효과와 테스트 구성 차이가 섞인다. 그래서 P3_random을 P3_group의 층별 구성에 맞추도록 바꿨다. 이제 두 분할의 차이는 "같은 참가자가 train과 test에 함께 있는가" 하나뿐이다. 논문 RQ3의 공정한 비교 근거로 쓸 수 있다.
- 검증(`--check`): P1·P2·P4·P3_group의 참가자 교집합 0, P2와 P4는 모든 녹화가 정확히 한 번씩 테스트됨, P3_random은 반드시 참가자를 공유하고 층별 구성이 P3_group과 동일, P3_group 테스트 비율 15–30%. 두 번 실행해 `splits.json`의 해시가 같음(재현성).
- 검증 출력:
  ```
  P1: train 540 (G3) -> test 1A 250, 2A 51
  P2: G3-P1/P2/P3 각 180      P4: R1–R6 각 41–42
  P3 seed 0: random 185 (train과 공유 참가자 7명) | grouped 185 (23%) [G2A-S4-Roscoff, G3-P2]
  ... seed 4: random 234 (공유 16명) | grouped 234 (29%)
  VERIFY PASSED: index.py, labels.py, preprocess.py, features.py, splits.py
  ```
- 주의: P3는 G3 참가자 한 명이 180개를 차지해 seed마다 테스트 구성이 크게 다르다(G3가 들어간 seed와 아닌 seed). 결과는 seed별로도 보고하고, 평균만 내지 않는다.
- 다음: (6) evaluate.py

### 회차 6 — 2026-10-05 · (6) evaluate.py 완료

- `src/evaluate.py` 작성(numpy만 사용). `evaluate(y_true, y_pred, groups)`가 정확도, Macro-F1(테스트에 존재하는 클래스만 평균; 없는 클래스로 예측하면 오답으로 처리), balanced accuracy, 클래스별 recall/precision/F1, 참가자 단위 bootstrap 95% 신뢰구간(2000회)을 한 번에 돌려준다. 다수 클래스 기준선 함수 포함(동률이면 이름순으로 결정).
- scikit-learn 1.9.1 설치(지표 교차검증과 (7)의 Random Forest용).
- 검증(`--check`): 손으로 계산한 예제(Macro-F1 0.65), 다수 클래스 예측의 닫힌 식(Macro-F1 = F1/K, balanced acc = 1/K), Paper 2의 RTK 개수로 87.8%, 무작위 데이터 50회에서 scikit-learn과 일치, 완벽한 예측의 bootstrap이 [1, 1], 같은 seed면 bootstrap 재현. 다수 클래스 정확도가 설계 PDF 1절 표와 일치.
- 결과 `results/baseline_majority_P1.csv` — 논문 결과표의 기준선 행으로 바로 쓸 수 있다(1A+2A, 테스트 다수 클래스를 전부 예측):
  ```
  A RTK n=83   acc 88.0%  macro-F1 0.312 [0.285, 0.494]  bal-acc 0.333
  A ELK n=79   acc 54.4%  macro-F1 0.352 [0.161, 0.453]  bal-acc 0.500
  A CTK n=105  acc 58.1%  macro-F1 0.184 [0.152, 0.399]  bal-acc 0.250
  B RTK n=90   acc 64.4%  macro-F1 0.261 [0.201, 0.413]  bal-acc 0.333
  B ELK n=77   acc 77.9%  macro-F1 0.438 [0.343, 0.485]  bal-acc 0.500
  B CTK n=105  acc 60.0%  macro-F1 0.187 [0.151, 0.306]  bal-acc 0.250
  VERIFY PASSED: index.py … evaluate.py
  ```
- 발견: 아무것도 배우지 않는 기준선조차 참가자 bootstrap 구간이 넓다(A ELK 0.16–0.45). 참가자 13명 안팎에 오류가 몰려 있어서, 모델 간 Macro-F1 차이가 0.1 이하면 이 구간 안에 묻힐 가능성이 크다. 논문에서 "개선"을 주장하려면 같은 bootstrap 표본에서 두 모델의 **차이**에 대한 구간을 내야 한다(백로그 14).
- 발견: "존재 클래스만" Macro-F1은 bootstrap 표본마다 존재하는 클래스 수가 달라져(희귀 클래스를 가진 참가자가 빠지면 K가 줄어듦) 상한이 점추정보다 높게 튄다(A RTK 0.312 → 상한 0.494). 해석 시 주의하고, 전체 테스트셋 기준으로 K를 고정한 변형을 함께 보고하는 방안을 백로그 15에 넣었다.
- 다음: (7) Random Forest 기준선, 1A leave-one-patient-out(P4) 시험 실행

### 회차 7 — 2026-10-05 · (7) RF 기준선 P4 시험 실행 완료

- `src/rf_baseline.py` 작성. 각 feature 시계열을 평균·표준편차·최소·최대·범위·10/90 백분위로 요약(7F차원)하고, 운동별 Random Forest(300그루, class_weight=balanced, min_samples_leaf=2)를 학습한다. `--protocol`로 splits.json의 어떤 프로토콜이든 돌릴 수 있고, 골격이 없는 녹화가 섞이면(P1, P2) 이유를 출력하고 멈춘다.
- 실행: P4(1A 환자 1명씩 빼기, 6-fold) × 표현 7종 × 주석자 A·B × seed 5 + fold 내 학습 다수 클래스 기준선. 5분 33초.
- 검증(`--check`, 전체 검증에 포함): 표현 2종 × seed 2로 끝까지 실행, out-of-fold 예측 수가 라벨 있는 테스트 녹화 수와 정확히 같고 중복 없음, Macro-F1 유한, 같은 seed 재실행 시 결과 동일. `VERIFY PASSED` (7단계 전부).
- 결과 요약(Macro-F1, seed 5개 평균, 괄호는 seed 0의 참가자 bootstrap 95% 구간):

  | | RTK | ELK | CTK |
  |---|---|---|---|
  | A 다수 클래스 | 0.314 | 0.041 | 0.174 |
  | A R0 raw | **0.540** [0.30, 1.00] | **0.573** [0.42, 0.66] | 0.301 |
  | A R1 정규화 | 0.482 | 0.506 | 0.309 |
  | A R2 관절각 | 0.314 | 0.342 | 0.282 |
  | A Rerr 오류별 | 0.314 | 0.206 | **0.335** [0.29, 0.52] |
  | B R0 raw | **0.525** | **0.711** [0.48, 0.85] | 0.360 |
  | B Rerr_d | 0.412 | 0.521 | **0.417** [0.28, 0.66] |

  전체 표: `results/rf_P4_summary.csv`, 회차별 값: `results/rf_P4_runs.csv`.

- **이 결과는 표현 비교로 해석하면 안 된다.** 이유가 데이터에서 바로 보인다:
  - 1A에서 라벨이 거의 **환자 단위 속성**이다. 주석자 A의 ELK는 환자 6명 중 5명이 92% 이상 한 클래스다(R1: E2 13/14, R2: C 8/8, R4: E2 14/14, R6: C 11/11 …). 그래서 P4의 ELK는 사실상 "이 환자가 기울이지 못하는 사람인가"를 6개 표본으로 맞히는 문제다.
  - 같은 이유로 학습 다수 클래스 기준선이 ELK에서 0.041까지 떨어진다. 나머지 5명의 다수 클래스가 빠진 환자의 클래스와 거의 항상 반대이기 때문이다.
  - RTK(A)는 오류가 10개뿐이라 관절각 계열(R2–Rerr)이 전부 다수 클래스 예측으로 무너졌다(0.314 = 다수 클래스와 같음).
- **R0(raw)가 가장 좋게 나온 것은 경고 신호다.** 정규화로 지운 정보(카메라 기준 절대 위치, 키, 서 있는 자세)가 "오류를 보이는 환자"를 구별하는 데 쓰였을 수 있다. 즉 동작의 질이 아니라 사람의 특성을 배웠을 가능성이다. 장소(Brest/Roscoff)를 맞히는지 확인해 보니 R0 57%, R1 61%, R2 43%로 6명 기준 우연 수준과 구분되지 않아 장소 교란은 아니다. 사람 특성 가설은 백로그 17로 검증한다.
- R3, R4(속도·대칭 추가)가 R2보다 나쁜 경우가 많다(A ELK 0.342 → 0.241 → 0.177). 학습 표본이 fold당 약 60개인데 feature가 168개라 과적합이 의심된다. 표현 사다리 비교 때 feature 수를 맞춘 비교나 feature 선택이 필요하다(백로그 18).
- 결론: 파이프라인은 끝까지 돈다. 다만 1A 내부 평가는 사실상 "환자 6명"짜리 실험이라, 표현 비교의 근거는 P1(G3 → 1A·2A)과 P2에서 나와야 한다.
- 다음: (8) G3 인덱스 + trial 교란 점검 코드

### 회차 8 — 2026-10-05 · (8) trial 교란 점검 코드 완료 (1단계 끝)

- G3 인덱스 파싱은 회차 1의 `index.py`에서 이미 완료(540개, 운동 × 클래스당 45개 균형 검사 포함). 이번 회차는 교란 점검 코드.
- `src/trial_confound.py` 작성. G3는 T1 = C+E1, T2 = C+E2, T3 = C+E3로 묶여 있으므로, **Correct 녹화만으로 trial을 맞힐 수 있으면** 그 정보는 세션 신호이고 오류 라벨로 새어 들어간다.
  - 검사 1(분류기): 표준화 + 축소 LDA. within(참가자별 5-fold)과 across(참가자 1명씩 빼기). 우연 1/3, trial 라벨을 참가자 안에서 섞은 permutation null의 95백분위와 비교.
  - 검사 2(feature별): 참가자 평균을 뺀 뒤 trial 간 일원 분산분석, Benjamini–Hochberg FDR 5%. 어느 feature가 세션 정보를 담는지 알려준다.
- **탐지기 선택 과정(논문 Methods에 적을 것)**: 처음 쓴 Random Forest는 fold당 학습 녹화가 12개뿐이라 강하게 주입한 신호도 못 잡았다(60%). L2 로지스틱 회귀도 20차원에서 33%로 실패. 합성 데이터 비교에서 축소 LDA가 가장 민감했지만, 수백 차원 중 1개 feature에만 있는 신호는 어떤 분류기로도 안 잡힌다(500차원에서 0.44). 그래서 feature별 분산분석을 함께 쓴다. 약한 탐지기로 "교란 없음"이라 결론 내리는 것을 막기 위해서다.
- 검증(`--check`, 전체 검증에 포함):
  ```
  self-test: 여러 feature에 퍼진 신호 acc 0.93, 순수 잡음 acc 0.24,
             한 feature 신호를 분산분석이 찾음 True, 잡음에서 FDR 통과 feature 0개, 잡음의 permutation p95 0.51
  G3 파일명: 샘플 6개와 전체 목록 540개 모두 "Tk에는 C와 Ek만" 구조를 만족
  1A 시험 실행(녹화 순서 3등분을 가짜 trial로, CTK, R2): within 0.32, across 0.31, FDR feature 1개
  VERIFY PASSED (8단계 전부)
  ```
- 1A 시험 실행은 실제 데이터 경로 코드를 끝까지 돌려보기 위한 것이다. 덤으로, 1A에서는 환자 안에서 녹화 순서에 따른 뚜렷한 변화(세션 드리프트)가 보이지 않았다.
- G3 골격이 없으므로 실제 점검은 보류. 도착 시 할 일은 위 체크리스트 아래에 적어 두었다.
- 다음: 업그레이드 백로그 — 가치 순으로 판단해 **16(라벨의 환자 군집도 정량화)과 17(사람 특성 교란 점검)**을 먼저 한다. 회차 7의 결과 해석이 이 두 가지에 달려 있고, 논문 Dataset·Limitations 절에 바로 들어가기 때문이다. 그다음 1(테스트·재현성), 14(짝지은 bootstrap), 2(실험 실행기) 순.

### 회차 9 — 2026-10-05 · 백로그 16 (라벨의 환자 군집도 정량화) 완료

- `src/label_clustering.py` 작성 → `results/label_clustering.csv`, `results/label_clustering.md`(논문 표 초안).
- 테스트 그룹(1A, 2A, 1A+2A) × 주석자(A, B, consensus) × 운동마다: 참가자별 클래스 개수, "오류 여부"(E vs C)의 ICC(1)(크기가 다른 군집용 일원 분산분석 추정), 설계효과 DEFF = 1 + (k0−1)·ICC, 유효 표본 수 N/DEFF, 90% 이상 한 클래스인 참가자 비율.
- 검증(`--check`, 전체 검증에 포함): 군집 없는 무작위 데이터 ICC ≈ 0(200회 평균 |ICC| < 0.03), 완전 군집 ICC = 1, 군집 크기가 같으면 k0 = 군집 크기, 표의 N이 labels.csv와 일치. `VERIFY PASSED` (9단계).
- 결과(1A+2A):

  | 주석자 | 운동 | N | 참가자 | 오류율 | ICC | DEFF | **유효 N** | 90%↑ 한 클래스 |
  |---|---|---|---|---|---|---|---|---|
  | A | RTK | 83 | 11 | 0.12 | 0.29 | 2.8 | **29** | 6/10 |
  | A | ELK | 79 | 8 | 0.54 | **0.81** | 8.0 | **10** | 6/7 |
  | A | CTK | 105 | 11 | 0.42 | 0.27 | 3.2 | **33** | 2/10 |
  | B | RTK | 90 | 11 | 0.36 | 0.47 | 4.2 | 21 | 5/10 |
  | B | ELK | 77 | 8 | 0.78 | 0.51 | 5.3 | 15 | 3/7 |
  | B | CTK | 105 | 11 | 0.40 | 0.32 | 3.6 | 29 | 2/10 |

  1A만 보면 주석자 A의 ELK는 ICC 0.86, 유효 N 7.0, 환자 6명 전원이 90% 이상 한 클래스.

- 발견(논문 Dataset·Limitations용): **테스트셋 79–105개 녹화의 정보량은 독립 표본 10–33개 수준이다.** 특히 ELK는 라벨이 거의 사람 단위로 정해진다(ICC 0.81). 회차 7에서 P4의 ELK 결과를 표현 비교로 읽으면 안 된다고 한 판단을 수치로 뒷받침한다.
- 발견: **주석자 A가 B보다 사람 단위로 더 일관되게 판정한다**(ELK ICC A 0.81 vs B 0.51, RTK는 반대로 A 0.29 vs B 0.47). 주석자마다 "이 환자는 못 기울인다"처럼 사람 단위로 판단하는 정도가 다를 수 있고, 주석자 간 불일치(κ≈0.60)의 한 원인일 수 있다. 백로그 5(주석자 비교 실험)에서 함께 다룬다.
- 시사점: 모델 간 비교는 참가자 단위 bootstrap(이미 구현)과 짝지은 bootstrap(백로그 14)으로 해야 하고, 결과표에 유효 N을 같이 적는다.
- 다음: 백로그 17(사람 특성 교란 점검)

### 회차 10 — 2026-10-05 · 백로그 17 (사람 특성 교란 점검) 완료

- `src/person_confound.py` 작성 → `results/person_confound_P4.csv`. 동작 방식과 무관한 정적 feature만으로 보지 못한 환자의 오류 라벨을 맞히는지 본다. rf_baseline과 같은 프로토콜·fold·모델·seed 5개.
  - anthropometry(체격): 몸통 길이, 어깨 너비, 좌우 팔 길이, SpineBase–Head 거리
  - camera(카메라 기준 위치): SpineBase x·y·z 중앙값, 골반선 heading
  - duration: 프레임 수
- 검증(`--check`, 전체 검증에 포함): 정적 feature 유한·체격 값 타당, 골격 전체를 강체 이동시키면 체격 feature는 그대로이고 카메라 feature는 변함, seed 1개로 끝까지 실행. `VERIFY PASSED` (10단계).
- 결과(P4, Macro-F1 seed 5개 평균):

  | | 체격 | 카메라 위치 | 길이 | 정적 전부 | **R0** | Rerr_d | 다수 클래스 |
  |---|---|---|---|---|---|---|---|
  | A RTK | 0.311 | 0.276 | 0.317 | 0.303 | **0.540** | 0.314 | 0.314 |
  | A ELK | 0.273 | **0.629** | 0.463 | 0.376 | 0.573 | 0.307 | 0.041 |
  | A CTK | 0.204 | 0.247 | **0.339** | 0.175 | 0.301 | 0.300 | 0.174 |
  | B RTK | 0.292 | 0.346 | 0.305 | 0.237 | **0.525** | 0.412 | 0.252 |
  | B ELK | 0.301 | **0.736** | 0.413 | 0.454 | 0.711 | 0.521 | 0.450 |
  | B CTK | 0.170 | 0.289 | 0.269 | 0.257 | 0.360 | **0.417** | 0.176 |

- **핵심 발견: ELK에서는 동작 정보가 전혀 없는 카메라 위치 숫자 4개가 R0와 같거나 더 높다**(A 0.629 vs 0.573, B 0.736 vs 0.711). 따라서 회차 7에서 R0가 ELK 1위였던 것은 동작 정보 때문이라고 말할 수 없다.
  - 환자별로 보면 카메라 위치와 오류율 사이에 단순한 단조 관계는 보이지 않는다(예: E2 비율 1.00인 R4와 0.00인 R6의 위치가 가깝다). 환자 6명이라 4개 숫자의 조합이 우연히 "일반화"하는 것처럼 보일 수 있다. 진짜 관계인지 우연인지는 이 데이터로 구분할 수 없고, 둘 중 어느 쪽이든 결론은 같다: **P4로는 표현을 비교할 수 없다.**
  - 체격은 어디서도 다수 클래스 수준을 넘지 못했다 → "키 큰 사람이 오류" 같은 체격 교란은 없다.
  - RTK에서는 정적 feature가 모두 기준선 수준인데 R0만 0.53–0.54다. RTK의 R0 우위는 정적 정보로 설명되지 않으므로, 회전 동작이 카메라 좌표에 그대로 담긴 결과일 수 있다(정규화는 녹화당 고정 회전이라 시간에 따른 회전은 R1에도 남아 있으며, R1도 0.48–0.52로 비슷하다).
  - CTK(A)는 녹화 길이만으로 0.339로 R0(0.301)보다 높다. 오류가 있는 반복이 더 길거나 짧은 것일 수 있다(정당한 동작 정보일 수도 있음). 백로그 20에 기록.
- 논문 시사점: "raw 좌표가 정규화보다 좋다"는 결과가 나오면 반드시 이 교란 점검과 함께 보고해야 한다. P1(G3 → 환자)에서는 반대로 G3와 테스트 세션의 카메라 위치가 체계적으로 달라(회차 3) R0가 불리할 것으로 예상된다.
- 다음: 백로그 19(참가자 단위 라벨 섞기로 "의미 없는 feature가 얼마나 높게 나올 수 있는지" 기준 만들기) — 이번 결과를 정량적으로 마무리하는 데 필요하다. 그다음 1, 14, 2.

### 회차 11 — 2026-10-05 · 백로그 19 (참가자 단위 permutation null) 완료

- `src/permutation_null.py` 작성 → `results/permutation_null_P4.csv`. 순열마다 각 참가자에게 다른 참가자의 라벨 묶음(섞은 뒤 자기 녹화 수에 맞춤)을 준다. 사람 안의 군집 구조(ICC)는 그대로 두고 동작과 라벨의 연결만 끊는 null이다. 순열 100회, RF 100그루·seed 1개(관측값도 같은 설정으로 재계산), 24코어 병렬로 1분 57초.
- 검증(`--check`, 전체 검증에 포함): 순열이 참가자의 일대일 재배정이고 각 참가자가 받은 라벨이 자기 기증자에게 있는 라벨뿐인지(50회), 라벨을 담은 feature는 0.96으로 잡히고 순수 잡음은 null 대비 유의하지 않음, 실제 데이터 한 칸 끝까지 실행. `VERIFY PASSED` (11단계).
- 결과(P4, Macro-F1; null은 같은 feature에 섞은 라벨을 준 분포):

  | | feature | 관측 | null 평균 | null 95% | p |
  |---|---|---|---|---|---|
  | A RTK | R0 / R1 | 0.536 / 0.544 | 0.32 | 0.48 | **0.02 / 0.01** |
  | A RTK | Rerr / 카메라 | 0.314 / 0.283 | 0.33 / 0.31 | 0.48 | 0.33 / 0.58 |
  | A ELK | R0 / R1 / Rerr / 카메라 | 0.479 / 0.520 / 0.204 / 0.583 | 0.33–0.40 | 0.54–0.63 | 0.12 / 0.11 / 0.89 / 0.10 |
  | A CTK | R0 / R1 / **Rerr** / 카메라 | 0.314 / 0.311 / **0.350** / 0.230 | 0.21 | 0.28–0.31 | **0.05 / 0.03 / 0.02** / 0.45 |
  | B RTK | R0 / R1 / Rerr / 카메라 | 0.509 / 0.509 / 0.474 / 0.440 | 0.30–0.31 | 0.48–0.57 | **0.04** / 0.06 / 0.07 / 0.12 |
  | B ELK | R0 / R1 / Rerr / **카메라** | 0.699 / 0.499 / 0.484 / **0.733** | 0.44–0.46 | 0.53–0.65 | **0.02** / 0.15 / 0.19 / **0.01** |
  | B CTK | R0 / R1 / **Rerr** / 카메라 | 0.356 / 0.357 / **0.384** / 0.302 | 0.20–0.21 | 0.28–0.31 | **0.01 / 0.03 / 0.01 / 0.02** |

- **우연의 기준선이 높다.** 사람 단위 군집 때문에 의미 없는 라벨로도 Macro-F1이 평균 0.30–0.46, 95백분위 0.48–0.65까지 나온다. P4에서 0.6 미만은 그 자체로 증거가 아니다.
- **CTK는 동작 정보가 우연을 넘는다.** 두 주석자 모두 R0·R1·Rerr가 유의하고, 오류별 feature(Rerr)가 가장 높다(A 0.350, B 0.384). 카메라 위치는 A에서 우연 수준이다. 현재 데이터에서 "동작을 보고 오류를 맞힌다"는 근거가 가장 깨끗한 과제다.
- **ELK는 주석자 A 기준으로 어떤 feature도 우연과 구분되지 않는다**(회차 10에서 카메라 0.629·R0 0.573이 높아 보였던 것도 null 95% 0.60–0.63 안이다). 주석자 B 기준으로는 R0와 **카메라 위치만으로도** 유의하다. B의 ELK에서 대부분 Correct로 판정된 환자는 R6뿐인데, R6는 카메라 기준 가장 옆(x = 0.39 m)에 서 있었다. 환자 한 명이 결과를 좌우하는 구조이므로 "카메라 위치가 B의 판정과 관련 있다"는 주장은 하지 않고, 사실로만 기록한다.
- **RTK는 A 기준 R0·R1이 유의하지만 오류가 10개뿐**이고, Rerr는 우연 수준이다. 회차 10의 해석(회전 동작이 좌표에 담김)과 맞지만 근거는 약하다.
- 논문 시사점: (1) 참가자 군집이 강한 데이터에서는 참가자 단위 permutation null을 기준선으로 함께 보고해야 하며, 이 절차 자체가 방법론적 기여가 될 수 있다. (2) 주 과제 후보는 CTK(E1+E3 병합 시 C 61 vs E13 43) → 백로그 11과 연결.
- 다음: 백로그 1(단위 테스트·재현성: requirements.txt, 환경 기록, 결과 파일 해시). 지금까지 분석이 많아져 재현성 장치를 먼저 갖춘다. 그다음 14(짝지은 bootstrap), 2(실험 실행기).

### 회차 12 — 2026-10-05 · 백로그 1 (단위 테스트·재현성) 완료

- `requirements.txt`: numpy 2.2.6, scipy 1.18.1, scikit-learn 1.9.1, joblib 1.6.0, pytest 9.1.1 (Python 3.12.3, Windows 11).
- `tests/test_core.py`: 단위 테스트 22개 — 실제 파일명 정규식, 라벨 규칙 7가지, CTK 병합, 정규화가 위치·방향·크기를 지우는지, 리샘플링 끝점, invariant 각도의 회전 불변성, 알려진 팔꿈치 각도(90°), 지표 손계산 예제, bootstrap 재현성, P3 분할의 층별 구성 일치, ICC 경계, 참가자 순열의 일대일 재배정.
- `src/manifest.py`: 환경(파이썬·패키지 버전)과 `data/`·`results/` 출력 14개의 SHA-256을 `results/MANIFEST.json`에 고정(`--freeze`)하고 비교(`--check`). 원본은 파일 수만 기록. 결과 파일 하나에 공백 한 칸을 덧붙이자 `CHECK FAILED`, 다시 생성하자 `PASSED`로 돌아오는 것을 확인. (npz 파일도 다시 써도 바이트가 같음을 미리 확인했다.)
- `src/verify.py` 확장: 모든 단계 `--check` → `pytest` → 해시 비교. 이제 코드 수정이 결과를 몰래 바꾸면 전체 검증에서 걸린다.
- **테스트가 실제 결함을 하나 찾았다.** `preprocess.heading_rotation`이 골반 벡터의 **성분별** 중앙값으로 방향을 잡고 있었는데, 성분별 중앙값은 회전과 교환되지 않아 같은 골격을 돌려 넣으면 약 0.1°의 방향 잔차가 남았다. 프레임별 각도의 중앙값(원형 평균 기준)으로 바꿔 정확히 회전 등변이 되게 고쳤다.
  - 의도적인 출력 변경이므로 하류 분석을 모두 다시 돌렸다: rf_baseline(P4) Macro-F1 최대 변화 0.012(B ELK R3 0.514 → 0.502), 나머지는 0.01 미만. person_confound의 카메라 feature는 A ELK 0.629 → 0.636, B ELK 0.736 → 0.749. permutation_null의 유의성 판단은 하나도 바뀌지 않았다. **회차 7·10·11의 결론은 그대로다**(표의 숫자는 각 회차 당시 값, 최신 값은 results/ 파일).
  - 그 뒤 manifest를 고정했다.
- 검증 출력: `22 passed` · `14 outputs compared with the frozen manifest` · `VERIFY PASSED` (11단계 + 단위 테스트 + manifest).
- 다음: 백로그 14(짝지은 bootstrap — 두 표현의 Macro-F1 차이 구간). 논문의 "개선" 주장을 위한 통계 도구다.

### 회차 13 — 2026-10-05 · 백로그 14 (짝지은 bootstrap) 완료

- `evaluate.paired_bootstrap_diff`: 같은 참가자 재표본에서 Macro-F1(A) − Macro-F1(B)를 계산하고, 재표본마다 학습 seed 5개를 평균해 참가자 표집과 seed 잡음을 함께 반영한다. 관측 차이, 95% 백분위 구간, 양측 bootstrap p 반환.
- `rf_baseline.py`가 전체 실행 시 out-of-fold 예측을 `results/rf_<P>_preds.csv`로 저장하도록 확장(P4 재실행 5분 33초). **재실행 후 기존 rf_P4_runs/summary 해시가 manifest와 정확히 같았다** → RF 결과가 완전히 결정적임을 확인.
- `src/compare_reps.py` → `results/compare_reps_P4.csv`. 표현 사다리 쌍(R1−R0, R2−R1, R3−R2, R4−R3), Rerr−R1, Rerr_d−Rerr, 기준선 대비 2개.
- 검증: 단위 테스트 2개 추가(같은 모델 → 차이 0·구간 [0, 0], 확실히 나은 모델 → 구간 > 0, p < 0.05; 총 24개 통과). `compare_reps --check`: 저장된 예측 216세트를 다시 채점해 runs 파일의 Macro-F1과 일치, 관측 차이가 자기 구간 안. 새 출력 2개를 manifest에 반영해 재고정(16개). `VERIFY PASSED`.
- 결과(P4, 차이 [95% 구간], 0을 포함하지 않는 것만 판정):
  - **사다리 비교에서 "개선"으로 판정된 쌍은 하나도 없다.** 차이가 확인된 것은 대부분 **악화**다: A ELK R4−R3 −0.072 [−0.096, −0.031], A ELK Rerr−R1 −0.305 [−0.486, −0.076], A CTK R4−R3 −0.017 [−0.040, −0.001].
  - 예외적 개선: B RTK R3−R2 +0.095 [+0.028, +0.261](속도 추가), B ELK Rerr_d−Rerr +0.018 [+0.002, +0.081](크기는 미미).
  - R1−R0(정규화의 효과)은 6개 칸 모두 "차이를 보이지 못함".
  - 기준선 대비: CTK는 두 주석자 모두 R0와 Rerr가 다수 클래스를 확실히 넘는다(Rerr: A +0.159 [+0.134, +0.237], B +0.218 [+0.138, +0.342]). 회차 11의 permutation null 결과와 같은 방향이다.
- **주의(논문 Methods에 적을 것)**: 참가자가 6명뿐인 P4에서는 군집 bootstrap이 서로 다른 재표본을 많이 만들지 못해 구간이 실제보다 좁게 나올 수 있다(군집 수가 적을 때 알려진 과소 포함 문제). 예: A ELK에서 "R0가 다수 클래스보다 낫다"는 구간 [+0.39, +0.63]이 나오지만, 이 다수 클래스 기준선은 LOPO에서 정답과 반대가 되는 특수한 경우(0.041)이고 permutation null로 보면 유의하지 않았다. **P4에서는 permutation null(회차 11)을 1차 판단 기준으로, 짝지은 bootstrap은 보조로 쓴다.** 참가자가 11–13명인 P1 테스트셋에서는 bootstrap이 더 믿을 만하다.
- 다음: 백로그 2(설정 파일 기반 실험 실행기). 지금까지 스크립트가 많아져, 표현 × 모델 × 프로토콜 × 라벨 열 조합을 설정 하나로 돌리는 진입점을 만든다. G3 데이터가 오면 이것으로 P1·P2·P3를 한 번에 돌린다.

### 회차 14 — 2026-10-05 · 백로그 2 (설정 파일 기반 실험 실행기) 완료, 백로그 11·18 일부 반영

- `src/run_experiment.py --config configs/<이름>.json` → `results/experiments/<이름>/`(config 사본, runs.csv, summary.csv, preds.csv). JSON 하나로 프로토콜 × 과제 × 표현 × 모델 × seed 격자를 정의한다(YAML 대신 JSON: 의존성 추가 없음).
  - 과제는 `{exercise, label_col, classes}`로 정의. labels.csv의 어떤 열이든 쓸 수 있고, `classes`로 이진 과제를 만든다(예: CTK `["C", "E13"]`).
  - 모델: `rf`, `logreg`(표준화 + L2, class_weight=balanced; 백로그 18의 "정규화가 강한 선형 기준선"), `majority`.
  - 골격이 없는 프로토콜은 `ON HOLD`로 표시하고 건너뛴다 → **G3가 도착하면 같은 config가 P1까지 그대로 돈다.**
- 설정 파일 2개:
  - `configs/p4_smoke.json`: 전체 검증용(8초).
  - `configs/main_binary.json`: **백로그 11의 주 과제 고정** — ELK C vs E2, CTK C vs E13, 각각 주석자 A·B. 표현 7종 × RF·logreg·majority × seed 5. 프로토콜 P1(보류), P4.
- 검증(`--check`, 전체 검증에 포함): 같은 설정에서 실행기 결과가 rf_baseline의 Macro-F1과 **정확히 일치**, P1은 ON HOLD로 표시, 클래스 필터가 C vs E13 과제를 만듦. 새 출력 4개를 반영해 manifest 재고정(20개). `VERIFY PASSED` (13단계 + 단위 테스트 + manifest).
- 결과(`main_binary`, P4, Macro-F1 seed 평균 [seed 0의 참가자 bootstrap 95% 구간]):

  | 과제 | 다수 클래스 | RF 최고 | logreg 최고 |
  |---|---|---|---|
  | ELK C vs E2 (A) | 0.041 | R0 0.573 [0.42, 0.66] | R0 0.670 [0.44, 0.86] |
  | ELK C vs E2 (B) | 0.450 | R0 0.711 [0.48, 0.85] | Rerr 0.749 [0.46, 0.84] |
  | **CTK C vs E13 (A)** | 0.328 | R1 0.680 [0.52, 0.79] | R0 0.753 [0.58, 0.90] |
  | **CTK C vs E13 (B)** | 0.363 | R1 0.781 [0.64, 0.87] | Rerr_d 0.731 [0.64, 0.81] |

- 발견: **CTK를 E1+E3 병합 이진 과제로 바꾸자 성능이 크게 오른다.** 4-class에서 0.30–0.42였던 것이 0.68–0.78이고, 여러 표현에서 구간 하한이 0.5를 넘는다. 회차 11에서 동작 정보가 우연을 넘은 유일한 운동이 CTK였던 것과 맞물려, CTK 이진 과제가 현재 가장 유망한 주 과제다. 다만 이진 과제에서의 우연 기준선은 아직 재지 않았다(백로그 23).
- 발견: **표현의 순위가 모델에 따라 크게 뒤집힌다.** 예: ELK(B)에서 Rerr는 RF 0.503, logreg 0.749. CTK(A)에서 R1은 RF 0.680, logreg 0.542. 유효 표본이 10–30개 수준이라 표현 비교 결론이 모델 선택에 민감하다. 논문에서 표현을 비교할 때는 모델 2종 이상에서 같은 방향인지 함께 보고해야 한다.
- 발견: R3·R4(속도·대칭 추가)는 두 모델 모두에서 R2보다 낮은 경우가 대부분이다 → 회차 7의 과적합 해석과 일치.
- 다음: 백로그 23(이진 주 과제에 대한 참가자 permutation null). CTK 이진 결과가 우연을 넘는지 확인해야 주 과제로 확정할 수 있다.

### 회차 15 — 2026-10-05 · 백로그 23 (이진 주 과제의 참가자 permutation null) 완료

- `permutation_null.py` 확장: `--config`로 run_experiment 설정의 과제 정의(label_col + classes)와 모델(rf, logreg)을 그대로 받는다. logreg는 실험과 동일하게 재학습, rf는 100그루. 순열 후 학습 쪽에 한 클래스만 남는 fold는 그 클래스로 예측(이진 과제에서 생길 수 있음). 기존 다중 클래스 경로와 출력은 그대로(manifest 해시 불변 확인).
- 실행: `main_binary` 4과제 × 표현 5종(R0, R1, R2, Rerr, Rerr_d) × 모델 2종 × 순열 100회, 1분 41초 → `results/permutation_null_main_binary_P4.csv`.
- 검증: `--check`에 이진 CTK 과제의 rf·logreg 경로 추가. 새 출력 1개 반영해 manifest 재고정(21개). `VERIFY PASSED`.
- 결과(P4, p < 0.05인 칸 / 전체):

  | 과제 | 유의한 칸 | 두 모델 모두 유의한 표현 | null 95% 범위 |
  |---|---|---|---|
  | **CTK C vs E13 (B)** | **8/10** | **R0, R1, Rerr, Rerr_d** | 0.62–0.67 |
  | **CTK C vs E13 (A)** | **5/10** | **R0** (Rerr은 RF만, R2는 logreg만) | 0.58–0.66 |
  | ELK C vs E2 (B) | 2/10 | 없음(R0는 RF만, Rerr은 logreg만) | 0.53–0.72 |
  | ELK C vs E2 (A) | 0/10 | 없음 | 0.52–0.82 |

  예: CTK(B) R1 — RF 0.752(null 95% 0.624, p = 0.01), logreg 0.726(0.658, p = 0.02). CTK(A) R0 — RF 0.673(0.603, p = 0.01), logreg 0.753(0.599, p = 0.01).

- **결론: CTK C vs E13을 주 과제로 확정한다.** 40개 검정에서 우연이라면 약 2개가 유의하게 나와야 하는데, CTK에서만 13개가 나왔고 그중 여러 표현이 두 모델 모두에서 유의하다. ELK는 두 주석자 모두 모델 간 일관된 결과가 없다.
- 발견: 이진 과제의 우연 기준선이 매우 높다(null 95%가 0.52–0.82, ELK(A) logreg는 0.822). 1A 내부 평가에서 Macro-F1 0.7은 그 자체로 아무 의미가 없을 수 있다. 결과표에 null 95%를 나란히 적어야 한다.
- 발견: CTK에서 R0(원본 좌표)가 네 칸 모두 유의하다. 회차 10에서 카메라 위치는 CTK(A)에서 우연 수준이었으므로, CTK의 R0 성능은 카메라 교란보다는 동작 정보로 보는 편이 맞다.
- 주의: 검정을 40개 했으므로 개별 p = 0.01–0.04는 다중비교 보정 전 값이다. 논문에서는 과제 단위로 사전에 정한 비교(예: R1 vs null, Rerr vs null)만 확증 검정으로 쓰고 나머지는 탐색으로 표시한다(백로그 25).
- 다음: 백로그 7(그림·표 자동 생성). 지금까지의 결과(표현 사다리, null 기준선, 군집도)를 논문용 그림·표로 한 번에 다시 만드는 스크립트. G3 데이터가 오면 같은 스크립트로 P1 그림이 나오게 한다.

### 회차 16 — 2026-10-05 · 백로그 25 (사전 등록) 완료 — 순서 변경

- **순서를 바꾼 이유**: 회차 15에서 다음 항목을 7(그림·표)로 적었지만, 사전 등록은 G3 데이터를 보기 **전에만** 의미가 있고 데이터가 언제 올지 모른다. 놓치면 되돌릴 수 없으므로 먼저 했다. 7은 다음 회차에 한다.
- `PREREGISTRATION.md`(영문, 논문 부록용) 작성, 2026-10-05T11:17Z 고정. 당시 `raw/`에는 1A·2A·샘플·G3 파일명 목록만 있었다.
  - 과제: **CTK C vs E13**, P1(G3 → 1A+2A). 주 라벨 주석자 A(Paper 2와 비교 가능), B는 사전에 정한 민감도 분석.
  - 테스트셋(A): C 61, E13 43, n = 104, 참가자 11명. 학습(G3): C 45, E13 90.
  - 주 모델 RF(300그루), 강건성 확인 logreg(C = 0.1) — 두 모델 방향이 같을 때만 "강건"이라고 말한다.
  - 확증 가설 3개 + Holm 보정(α = 0.05):
    - H1 Rerr가 참가자 순열 null을 넘는다(G3로 한 번 학습, 테스트 참가자 사이에서 라벨 묶음 섞기 1000회)
    - H2 R1 > R0 (정규화가 sim-to-real에서 도움; 회차 3의 카메라 높이·pitch 차이 근거)
    - H3 Rerr > R1
    - H2·H3는 짝지은 참가자 bootstrap 2000회
  - 사전에 정한 데이터 품질 단계: 전체 검증 통과, trial 교란 점검(교란이 보이면 계획대로 보고 **하고** 플래그된 feature를 뺀 결과도 함께), G3 전체로 pitch 재측정.
  - 나머지(ELK, RTK, 4-class, R2–R4, Rerr_d, LSTM/TCN, P2, P3, consensus, 심각도)는 탐색 분석으로 표시.
- `configs/p1_confirmatory.json` 고정. SHA-256을 PREREGISTRATION.md에 적고, **`tests/test_core.py`가 해시를 검사**한다(설정을 고치면 단위 테스트가 실패). 의존 코드 10개의 해시도 기록.
- 결함 수정: 모든 프로토콜이 보류일 때 `run_experiment.py`가 빈 결과를 쓰다 `IndexError`로 멈추고 불완전한 폴더(빈 runs.csv)를 남겼다. "실행할 것 없음"을 출력하고 정상 종료하도록 고쳤고, 남은 폴더는 내용 확인(빈 runs.csv, config 사본뿐) 후 삭제했다. 수정은 사전 등록 고정 절차 안에서 이뤄졌으므로 PREREGISTRATION.md의 해당 해시를 수정본으로 갱신했다.
- 검증: 단위 테스트 25개 통과(사전 등록 해시 검사 추가), manifest 21개 일치, `VERIFY PASSED`.
- 다음: 백로그 21의 P1용 순열 null(H1에 필요: G3로 한 번 학습하고 테스트 라벨만 참가자 단위로 섞기). 사전 등록이 이 절차를 전제로 하므로 G3 도착 전에 구현·검증해 둬야 한다. 그다음 7(그림·표).

### 회차 17 — 2026-10-05 · 백로그 21 (P1 순열 null) + 확증 분석 스크립트 완료

- `src/confirmatory.py`: 사전 등록의 H1–H3와 Holm 규칙을 그대로 구현.
  - H1: **고정 예측 순열 null** — G3로 한 번 학습한 예측은 그대로 두고, 테스트 라벨만 테스트 참가자 사이에서 섞는다(1000회, seed 평균 Macro-F1, 단측 p). 백로그 21의 P1용 null이다.
  - H2(R1 > R0), H3(Rerr > R1): 짝지은 참가자 bootstrap 2000회, 단측 p = 차이 ≤ 0인 재표본 비율.
  - Holm 보정 후 지지 여부. 주(주석자 A × RF) 외에 사전에 정한 강건성(logreg)과 민감도(주석자 B) 가족도 같은 표로 낸다.
  - 출력: `results/confirmatory_<실험>_<프로토콜>.csv/.md`. G3가 없으면 ON HOLD.
- PREREGISTRATION.md에 이 스크립트의 해시를 "고정 후 추가된 분석 코드(G3 데이터 전)"로 기록.
- 검증(`--check`, 전체 검증에 포함): Holm 손계산 예제 2개, 완벽한 고정 예측은 유의하고 무작위 예측은 유의하지 않음, **탐색용 main_binary/P4 예측으로 끝까지 시험 실행**(12행 = 4가족 × 3가설). manifest 재고정(23개). `VERIFY PASSED` (14단계 + 단위 테스트 + manifest).
- 시험 실행 결과(`results/confirmatory_dryrun_main_binary_P4.md`; **사전 등록된 프로토콜이 아니므로 결과로 인용 금지**, 순열 100회·bootstrap 200회):
  - 주 가족(A, RF): H1 +0.669, Holm p 0.030 → 지지 / H2 +0.040 [−0.006, +0.091], Holm p 0.10 → 기각 못 함 / H3 −0.011 → 기각 못 함.
  - logreg에서는 H2 방향이 반대(−0.211). 1A 내부에서는 정규화 효과가 모델에 따라 갈린다는 회차 14의 관찰과 같다.
- 의미: G3가 도착하면 `run_experiment.py --config configs/p1_confirmatory.json` → `confirmatory.py` 두 줄로 사전 등록된 확증 결과표가 나온다. 이 경로는 한 번도 G3를 본 적 없이 코드·해시·테스트로 고정돼 있다.
- 다음: 백로그 7(그림·표 자동 생성).

### 회차 18 — 2026-10-06 · 백로그 7 (그림·표 자동 생성) 완료

- `src/figures.py` → `results/figures/`(PNG 200 dpi + PDF), `results/tables.md`. results의 CSV만 읽어 다시 만든다. matplotlib 3.11.2 설치(requirements.txt·manifest 환경 기록에 추가).
  - 그림 1 `fig1_label_clustering`: 과제별 녹화 수 대 유효 N(덤벨), ICC 표기. → 논문 Dataset/Limitations.
  - 그림 2 `fig2_main_binary_P4`: 이진 주 과제 4개 × 표현 7종, RF·logreg(seed 평균 점, seed 0 참가자 bootstrap 구간), **permutation null 95백분위(검은 짧은 선)**, 다수 클래스 기준선. G3 결과가 생기면 같은 코드가 `fig2_main_binary_P1`도 만든다.
  - 그림 3 `fig3_person_confound`: 과제별 카메라 위치만 vs R0 vs 다수 클래스. → 교란 점검 근거.
  - 표 `tables.md`: T1 테스트셋 클래스 개수, T2 군집도, T3 이진 주 과제 결과 + null 95%·p, T4 사람 특성 교란. 그림의 모든 값이 표에도 있다(표 쌍둥이).
- 디자인: dataviz 스킬 절차를 따랐다. 두 계열은 참조 팔레트 1·2번(파랑 #2a78d6, 주황 #eb6834)을 쓰고 **검증 스크립트로 확인**(밝은 배경 #fcfcfb: 명도 대역·채도·색각 이상 분리 ΔE 24.7·일반 시각 ΔE 33.6·대비 모두 통과). 기준선·null은 회색 잉크, 격자는 실선 헤어라인, 이중 축 없음. 정적 인쇄용이라 hover 층은 해당 없음.
- **렌더링해서 눈으로 확인**: 첫 판에서 그림 1·3의 범례가 데이터 행 라벨과 겹치고, 그림 2의 기준선 라벨이 오차 막대와 겹치며 x축 라벨이 붙어 있었다 → 범례를 축 밖 아래로, 라벨을 오른쪽 여백으로, x축 라벨을 두 줄로 고쳐 재확인. 그림 3 제목은 데이터가 말하는 만큼("카메라 위치만으로 ELK에서 raw 골격과 같은 수준")으로 다듬었다(주석자 A에서는 permutation null 안이므로 "예측한다"는 과장).
- 검증(`--check`, 전체 검증에 포함): 그림 6개 파일 존재·크기, 표 4개 존재, T1의 CTK(A) 행이 설계 PDF 개수와 일치. 두 번 생성해 PNG·PDF·표가 **바이트 단위로 동일**(메타데이터의 생성 시각 제거). manifest 재고정(30개). `VERIFY PASSED` (15단계 + 단위 테스트 + manifest).
- 다음: 백로그 8(논문 Methods·Dataset 절 초안). 지금까지의 설계 결정(골반선 고정 회전, 평면 태그, 참가자 단위 분할·null, 사전 등록)과 수치를 근거와 함께 문서화한다.

### 2026-10-06 (수동) · Group 3 Kinect 다운로드, 자동 업데이트 중단

- 사용자 요청으로 Group 3를 받았다: `raw/group3/kinect/` 540개(188 MB), 원본 압축본 `raw/group3.tar.xz.part`(8.71 GB, 삭제 여부 미정).
- 파일 수·이름 규칙·운동 × 클래스 45개 균형·175열만 확인했고, 골격 값으로는 아무것도 계산하지 않았다(사전 등록 유지).
- 사용자 요청으로 2시간 루프(0e152203)를 해제했다. 재개 순서는 상단 "Group 3 데이터: 위치와 활용 계획" 절에 있다.

### 2026-10-08 · Group 3 반영 검증 + 사전 등록 확증 분석

- `python src/verify.py --no-manifest`: Group 3 540개 포함 전 단계 통과(26분, 로그 `logs/verify_with_G3.log`). 단위 테스트 26개 통과.
- **데이터 품질 1 — 세션 교란 확인**: Correct 녹화만으로 같은 참가자 안에서 trial을 맞히는 정확도 0.76-1.00(순열 95% 0.47-0.49), 모든 운동·표현. 참가자 간에는 우연 수준. 플래그된 feature는 발·발목 좌표, 척추 기울기 평균 등(`results/trial_confound_features.csv`).
- **데이터 품질 2 — 카메라 재측정**(`explore/camera_geometry.py`, G3 540개): 골반 높이 -0.51 m(1A -0.19, 2A -0.31), 척추 앞뒤 기울기 -4.3°(1A -18.2°, 2A -17.4°). 샘플 6개 때보다 차이가 더 크다.
- manifest 재고정(34개) 후 **확증 분석**:
  - `run_experiment.py --config configs/p1_confirmatory.json` → `confirmatory.py`
  - 주 가족(주석자 A, RF): **H1 0.407 vs null 95% 0.428 (Holm p 0.29), H2 R1-R0 = -0.403 [-0.581, -0.210] (반대 방향), H3 +0.073 (Holm p 0.28) → 모두 지지 안 됨.**
  - logreg·주석자 B 가족도 모두 지지 안 됨. H2의 반대 방향은 RF에서만 나타나 강건하지 않다(logreg +0.069).
  - 사전 등록대로 교란 feature를 뺀 반복 분석(`configs/p1_confirmatory_cue_removed.json`, `run_experiment.py`에 `drop_trial_cue_features` 옵션 추가): 역시 모두 지지 안 됨.
- **탐색 분석(확증 이후)**:
  - RF가 정규화 좌표·오류별 feature로 학습하면 테스트 녹화의 92-97%를 오류로 판정(실제 41%).
  - 핵심 feature(어깨 거상 최대): G3 정상 126.9°·오류 111.9°, 1A 정상 121.6°·오류 113.5°. 환자의 "정상"이 건강인보다 5° 낮아 G3에서 배운 경계 근처에 걸린다. 연기 오류는 실제 오류와 비슷한 위치. RESEARCH_IDEAS의 "기준점 이동" 가설과 같은 방향.
  - R0(raw) RF가 0.737로 가장 높지만 logreg R0는 0.545이고, 세션·카메라 차이가 큰 상황에서 raw가 나은 이유는 설명되지 않았다 → 추가 점검 필요(백로그 27).
- 공개: 검증 중 features.py가 G3 포함 클래스별 기술 통계(중앙값)를 출력했다. 확증 분석 전 G3로 학습·평가한 모델은 없다.
- 다음: 2시간마다 재점검. 탐색은 백로그 27(R0 우위 원인), 28(경계 보정: 테스트 참가자 일부로 기준점만 다시 맞추는 실험).

### 2026-10-13 (수동) · 영상 확인 (탐색, 백로그 10)

자세한 내용과 그림: `explore/video_check/README.md`. 확증 경로·manifest는 바꾸지 않았다.
- 공식 readme(`E:\KERAAL_data\extracted\group3\readme_files_format.txt`): 1A = 환자, **2A = 건강한 성인**(둘 다 Poppy 코칭), 3 = 건강인이 오류를 연기. 영상은 얼굴 블러(`Anon`)에 골격 오버레이가 그려져 있다.
- **fps**: 영상 10 fps = Kinect 프레임과 1:1. 주석 시간은 15 fps 기준이다(주석자 B 종료 = 영상 길이 × 2/3, 전 녹화). 프레임 = 주석 시간 × 15. 실제 촬영 속도(10 vs 15 fps)는 미확정(10/15 정정: 처음에 "실제 초 = × 1.5"라고 적은 것은 근거 없음).
- **G3 B 코드**: CTK·RTK E1에서 B1 = 왼팔(15/15), B2 = 오른팔(15/15), B3 = 양팔. 주석 bodyPart와 대응한다. E2·E3·ELK는 미확인.
- **2A S1**: 뼈 길이·영상 모두 판정 불가 → 분리 유지.
- **CTK E1 손목 높이**: G3 정상 0.78 / G3 E1B3 0.19 / 1A 정상 0.49 / 1A Error1 0.37 / 1A A·B 불일치 0.42. 연기는 양 끝이 극단적이고 환자 정상은 G3 경계 아래에 있다 → 기준점 이동 해석과 같은 방향. 다만 결과를 본 뒤 고른 지표이고, 1A(Brest)는 서서, G3는 앉아서 했다는 자세 차이가 섞여 있다.

### 2026-10-17 (루프 L1) · 연기 → 실제 방향 AUC (탐색)

`explore/loop/l1_acted_to_real_auc.py`, 결과 `explore/loop/l1_acted_to_real_auc.md`. 확증 설정은 읽기만 했다(같은 과제·표현·모델·seed, 확률 출력, RF는 5 seed 평균 확률). 시험 1A 83개(E13 38, 6명) + 2A 21개(E13 5, 5명), 주석자 A 기준. 기준선 AUC 0.5, 순열 null = 참가자 안 라벨 섞기 1,000회.
- **기준점 가설과 맞는 결과**: Rerr RF는 기준점 0.5에서 92%를 오류로 판정해 Macro-F1 0.404(확증 결과 재현)지만, AUC는 0.674(null 95% 0.629, p = 0.002)로 순위는 우연보다 낫다. 시험셋에서 고른 기준점의 F1 상한은 0.661. logreg R1·Rerr도 AUC 0.72–0.74(p = 0.001)인데 F1은 0.49–0.62. 주석자 B도 같은 방향(Rerr RF 0.693, logreg Rerr 0.739).
- **반대 증거·주의**: RF R1은 AUC 0.619로 null 아래(p = 0.19). R0(raw) RF가 AUC 0.825·0.871로 가장 높아 R2(교란 점검) 전에는 해석 보류. 2A AUC 0.95–1.00은 오류 4–5개뿐이라 믿기 어렵다. 1A만 보면 Rerr RF 0.645, logreg Rerr 0.701. 사람 안 평균 AUC(0.61–0.84)가 pooled와 비슷해 사람 간 차이만으로 나온 순위는 아니다.
- 의미: 오류를 순위로 구분하는 능력은 약하게나마 남아 있고, 실패의 큰 부분은 기준점 위치다. R1(경계 보정)이 이 상한(0.66–0.79)에 얼마나 다가가는지가 다음 확인점이다.

### 2026-10-17 (루프 L2) · 확률 분포와 기준점 위치 (탐색)

`explore/loop/l2_probability_shift.py`, 결과 `explore/loop/l2_probability_shift.{md,png}`. 시험셋으로 아무것도 다시 맞추지 않은 기술 분석이다(기준점 재조정은 로시니의 R1). G3는 참가자 하나씩 뺀 out-of-fold(3명, C 45·E13 90), 1A(6명)·2A(5명)는 G3 전체로 학습한 P1 모델. P(E13)의 중앙값, 주석자 A.
- **실제 "정상"이 연기 "오류" 자리로 밀려 있다**: Rerr RF는 G3 정상 0.33 / G3 오류 0.85인데, 1A 정상 0.88 / 1A 오류 0.94, 2A 정상 0.90. 실제 정상 녹화가 G3 오류의 중앙값보다 높다. 그래서 0.5에서 1A 정상의 84%가 오류로 판정된다. 기준점으로 보면 G3에서 고른 Youden 0.55와 실제에서 고른 값(oracle) 0.93의 차이가 0.38이다. logreg Rerr도 같다(G3 정상 0.13 → 1A 정상 0.62, 기준점 0.31 vs 0.94).
- **이동이 작은 경우**: logreg R1은 1A 정상 0.36으로 G3 정상 0.34와 비슷해 이동이 작다. 이 모델의 F1(0.615)이 가장 높았던 것과 맞는다. RF R1은 1A 정상 0.91·오류 0.90으로 겹쳐서 이동이 아니라 구분 자체가 안 된다(L1의 AUC 0.508과 일치).
- 주석자 B도 같은 모양이다(Rerr RF 1A 정상 0.87 / 오류 0.95, 기준점 0.55 vs 0.91).
- 의미: 실패의 주된 모양은 "분포 전체가 오류 쪽으로 이동"이다. 정규화·오류별 feature(R1, Rerr)에서 RF가 특히 크게 이동하고, 선형 모델·R1에서는 작다. 실제 데이터 일부로 기준점만 옮기는 R1 실험이 효과를 볼 조건(이동 + 순위 유지)은 Rerr에서 갖춰져 있다. 한계: 2A 오류 4–5개, G3는 3명, oracle 기준점은 측정용일 뿐이다.

### 2026-10-17 (루프 L3) · pitch에 강한 feature만 쓰면 격차가 줄어드는가 (탐색, 백로그 13)

`explore/loop/l3_pitch_robust.py`, 결과 `explore/loop/l3_pitch_robust.md`. CTK C vs E13, R4·Rerr에서 feature를 full / robust(invariant + frontal + horizontal, sagittal·vertical 제외) / invariant만으로 나눠 P1(G3 → 1A·2A, 11명, n = 104)과 P4(1A·2A 참가자 하나씩 빼기, 11명)를 비교했다. 다수 클래스 기준 Macro-F1 0.370(A)·0.384(B). P1 AUC는 모든 조합에서 참가자 안 순열 null 95%를 넘는다(p ≤ 0.01).
- **Rerr에서는 과잉 오류 판정이 줄었다**: vertical 2개(손목 높이)를 빼면 P1 오류 판정 비율이 RF 0.92 → 0.82, logreg 0.70 → 0.48로 줄고, P1 Macro-F1이 RF 0.404 → 0.452(B 0.403 → 0.491), logreg 0.493 → 0.640(B 0.501 → 0.597)으로 오른다. AUC 변화는 작고 방향이 섞인다(RF 0.674 → 0.700, logreg 0.722 → 0.676).
- **하지만 격차 축소의 절반은 P4 하락 때문이다**: 같은 feature를 빼면 실제 → 실제(P4) 성능도 떨어진다(Rerr RF F1 0.650 → 0.552, AUC 0.742 → 0.545). 손목 높이는 실제 데이터 안에서는 쓸모 있는 정보이고, 연기 → 실제로 옮길 때만 기준점을 어긋나게 한다.
- **R4에서는 거의 변화가 없다**: sagittal·vertical 3개를 빼도 P1 F1 +0.02, 오류 판정 비율 0.83 그대로.
- 해석 주의: 손목 높이는 CTK 오류(팔을 덜 올림)의 핵심 단서이기도 하고, 10/13 영상 확인에서 환자 정상의 손목 높이가 낮았다(0.49 vs G3 정상 0.78). 그래서 이 결과는 "카메라 pitch" 효과와 "환자는 원래 덜 올린다(기준점 차이)"를 구분하지 못한다. 서서(1A) vs 앉아서(G3) 차이도 섞여 있다. 사후 선택, 다중 비교, 표본 작음.
- 의미: 높이 계열 feature가 기준점 이동의 주된 통로다. 발표에서는 "카메라 보정만으로는 해결되지 않는다(실제 → 실제 성능도 같이 잃는다)"로 말할 수 있다.

### 2026-10-17 (루프 L4) · RF와 logreg가 표현 비교에서 같은 결론을 내는가 (탐색, 백로그 24)

`explore/loop/l4_model_agreement.py`, 결과 `explore/loop/l4_model_agreement.md`. 새 학습 없이 기존 결과(main_binary P4: ELK C vs E2·CTK C vs E13, 주석자 A·B, 6명씩 / p1_confirmatory P1 / L1의 P1 AUC)에서 표현 쌍 a − b의 seed 평균 차이 부호를 두 모델에서 비교했다(|차이| < 0.02는 무승부). CI 없이 방향만 본 기술 요약이다.
- **표현 비교는 대체로 모델에 따라 바뀐다**: P4 84쌍 중 같은 방향 43, 한쪽만 차이 22, 반대 17, 무승부 2. 표현 순위의 Spearman ρ는 −0.43 ~ +0.93(과제마다 다름).
- **P1의 R0(raw) 우위는 RF에서만 나온다**: P1 Macro-F1 R0 − R1은 RF +0.403, logreg −0.069. AUC로 보면 R0 − R1이 RF +0.206, logreg −0.150(A), B도 같은 모양. AUC 6쌍 중 4쌍이 반대 방향이다. 즉 "raw가 가장 좋다"는 RF가 raw 좌표에서 무언가(세션·카메라 단서 의심)를 잡은 결과일 가능성이 크다. 로시니의 R2(P1 raw 우위 점검)와 같은 질문이므로 해석은 R2를 기다린다.
- **모델과 무관하게 일관된 것**: P4에서 R0 > R4는 4개 과제 모두 같은 방향(+0.03 ~ +0.40). L1에서 Rerr AUC가 순열 null을 넘는 것도 RF·logreg 둘 다(0.674, 0.722).
- 의미: 발표에서 "어떤 표현이 더 낫다"는 주장은 피하고, 두 모델에서 함께 성립하는 "순위는 남고 기준점이 이동한다"(L1·L2)를 중심에 둔다.

### 2026-10-18 (루프 L5) · 심각도별 recall: 작은 오류를 더 놓치는가 (탐색, 백로그 6)

`explore/loop/l5_severity_recall.py`, 결과 `explore/loop/l5_severity_recall.md`. 저장된 out-of-fold 예측만 썼다(새 학습 없음, 녹화는 seed 다수결로 '탐지'). 심각도는 라벨과 같은 주석자의 SmallError / LargeError(1A·2A만). 기준(우연) = Small과 Large recall이 같음, Fisher 정확 검정, 68개 조합 다중 비교 보정 없음(우연히 p < 0.05가 ~3개 기대).
- **CTK는 큰 오류를 더 잘 잡는다**: P4(실제 → 실제) 28개 조합 중 25개에서 Large recall > Small, 중앙값 차이 +0.36, p < 0.05 5개. 예: 주석자 B logreg R2 Small 0.41 vs Large 1.00(p = 0.044). P1(연기 → 실제)도 12개 중 10개(중앙값 +0.27). 다만 **Large 오류는 5개(참가자 2–3명)뿐**이라 개별 수치는 약하다.
- **ELK는 차이가 없다**: 28개 중 8개만 Large > Small, 중앙값 −0.03, p < 0.05 없음. ELK는 Small 16–19개·Large 22–42개로 표본이 고르다.
- P1의 RF R1·Rerr는 Small·Large 모두 recall 0.97–1.00인데, 거의 전부를 오류로 판정해서 나온 값이다(L1·L2). logreg에서는 Large 1.00 vs Small 0.57–0.73.
- 의미: CTK에서 놓치는 오류는 주로 "작은" 오류, 즉 경계 근처의 녹화다. 기준점 위치가 결과를 크게 좌우한다는 L1·L2와 같은 방향이다. ELK에서는 심각도가 탐지에 영향을 주지 않는다.

### 2026-10-18 (루프 L6) · 녹화 길이와 오류 (탐색, 백로그 20)

`explore/loop/l6_length.py`, 결과 `explore/loop/l6_length.md`. 길이 = `master_index.csv`의 프레임 수. 모든 표현은 T = 100으로 리샘플링되어 모델은 길이를 직접 보지 않는다. 과제 ELK C vs E2·CTK C vs E13, 주석자 A·B. 길이만 쓴 logistic 회귀(log 프레임)를 P4(1A·2A 6명)·P1(G3 → 1A·2A 8–11명)로 평가, AUC null = 참가자 안 라벨 섞기 1,000회.
- **G3 녹화는 훨씬 짧다**: 중앙값 G3 224–251프레임 vs 1A 318–532, 2A 362–489. 실제 녹화가 1.3–2배 길다. G3 안에서는 정상·오류 길이 차이가 없다(CTK 251 vs 247). 연기 데이터는 동작 속도·녹화 구성부터 실제와 다르다는 또 하나의 근거다.
- **CTK의 길이 단서는 사람 차이에서 나온다**: 1A에서 오류 녹화가 더 짧다(A 322 vs 365, B 318 vs 369). 길이만으로 P4 Macro-F1 0.733(A)·0.769(B)로 다수 클래스(0.35)보다 훨씬 높다. 그러나 AUC 0.677·0.752는 참가자 안 순열 null 95%(0.723·0.782)를 넘지 못하고(p = 0.56·0.34), 같은 사람 안에서는 오히려 오류가 약간 길다(사람 안 AUC 0.60·0.53). 즉 "오류가 많은 사람이 원래 빨리 한다"는 사람 수준 교란이고, 오류 동작 자체의 정보로 보기 어렵다. 회차 10의 "길이만으로 0.339"도 같은 원인일 가능성이 크다.
- **연기 → 실제에서는 길이가 쓸모없다**: P1 길이 모델 F1 = 다수 클래스(0.370·0.384). G3가 모두 짧아서 실제 녹화가 전부 한쪽에 몰린다.
- ELK: 길이 단서 없음. P4 AUC 0.08·0.42는 LOPO에서 참가자별 클래스 비율이 달라 생기는 역학습 효과이고 null(0.10·0.50)도 같이 낮아 의미가 없다.
- 의미: T = 100 리샘플링으로 길이를 버린 설계는 정당하다(버린 것은 주로 사람 교란). 다만 G3와 실제의 속도 차이는 sim-to-real 이동의 또 다른 후보다. 한계: 2A 오류 4–5개, 사람 안 AUC는 6–8명만.

### 2026-10-18 (루프 L7) · 발표용 그림: P1 confusion matrix와 sim-to-real 사다리 (탐색, 백로그 26)

`explore/loop/l7_figures.py`, 그림 `explore/loop/l7_confusion_P1.png`·`l7_ladder.png`, 표 쌍 `l7_figures.md`. 새 학습 없이 확증 결과 파일을 읽기만 했고, `--check`가 P1 Rerr RF Macro-F1 0.4066(확증 값)과 오류 판정 비율 85–99%를 재현하는지 확인한다. 공용 `src/figures.py`는 건드리지 않았다(코드 담당자 리뷰 대상).
- confusion matrix(Rerr, 녹화별 seed 다수결): RF는 실제 정상 61개 중 54개(89%)를 오류로 판정하고 오류 43개 중 42개를 잡는다(주석자 B 55/63, 38/38). logreg는 정상의 67%를 오류로, 오류의 74–79%를 탐지. 오류 판정 비율 RF 92%·logreg 70–71%, 실제 오류 비율 38–41%.
- 사다리(Macro-F1, seed 평균): 실제 → 실제(P4)는 RF 0.61–0.78·logreg 0.54–0.75로 다수 클래스(0.33–0.36)보다 높다. 연기 → 실제(P1)에서 R1·Rerr RF는 0.33–0.41로 무너지고(다수 클래스 0.27–0.29, Rerr null 95% 0.43), logreg는 0.49–0.62로 덜 떨어진다. R0 RF만 P1에서 0.74–0.76으로 오히려 높다(L4: RF에서만 나오는 현상, R2 대기).
- 발표 슬라이드 4(확증 실패)에 confusion matrix, 슬라이드 6(원인)에 L2 그림과 사다리를 쓸 수 있다.

### 2026-10-18 (루프 L11) · L1–L7 한 장 요약 (탐색)

`explore/loop/l11_summary.py`, 그림 `explore/loop/l11_summary.png`, 핵심 메시지와 수치 `explore/loop/l11_summary.md`. L1–L7 결과 파일만 읽었다(새 학습 없음, `--check`가 L1 F1 0.404와 L7 오류 판정 92%를 재확인). 주석자 A, CTK 정상 vs E1+E3의 4칸 그림: (a) 연기 → 실제 confusion matrix(Rerr RF, 실제 정상의 89%를 오류로) (b) AUC vs 기준점 0.5의 Macro-F1(순위는 null 이상, 판정은 낮음) (c) P(오류) 사분위(실제 정상 0.88 ≈ 연기 오류 0.85, 기준점 0.55 vs 0.93) (d) 실제 → 실제 vs 연기 → 실제 Macro-F1. 발표 한 문장: "연기 데이터로 배운 모델은 오류를 구분하는 능력은 남아 있지만, 판정 기준점이 실제 사람에게 맞지 않는다." 한계(탐색, 11명, G3 3명, 자세 차이, R1 진행 중)는 md에 함께 적었다.

### 2026-10-18 (루프 L8) · 연기 → 실제 AUC를 ELK·RTK로 확장 (탐색)

`explore/loop/l8_other_exercises.py`, 결과 `explore/loop/l8_other_exercises.md`. L1과 같은 방법(P1, R0·R1·Rerr, RF 5 seed 평균 확률·logreg, 참가자 안 순열 null 1,000회)으로 ELK C vs E2(시험 8명, n 77–79), RTK C vs E1+E2(11명, n 83–90; 오류를 합친 정의는 로시니 모델과 같음).
- **RTK는 CTK와 같은 모양이다**: 순위는 우연 이상(Rerr RF AUC 0.922, null 95% 0.856, p = 0.001 / logreg R1 0.886·0.934, p ≤ 0.008)인데 0.5에서 과잉 판정한다. 실제 오류 12%(A)·36%(B)에 오류 판정 47–86%. R1 RF가 가장 심하다(86%, F1 0.265 < 다수 클래스 0.468, oracle 상한 0.700). 기준점 이동이 CTK만의 일이 아니다.
- **ELK는 다르다**: 과잉 판정이 없다(오류 판정 27–76% vs 실제 54%·78%). 주석자 A에서 R0·R1의 F1이 0.78–0.85로 oracle 상한(0.80–0.91)에 가깝다. 주석자 B(오류 78%)에서는 오히려 덜 판정한다. pooled AUC는 0.82–0.94로 높지만 참가자 안 순열 null도 0.85–0.95로 높아서(오류가 사람별로 몰림) 넘는 조합이 적다(R0 RF·logreg A, R1 logreg B).
- 의미: "연기로 배운 기준점이 실제를 오류 쪽으로 밀어낸다"는 팔을 드는 CTK와 몸통을 돌리는 RTK에서 나타나고, 몸통을 옆으로 굽히는 ELK에서는 나타나지 않는다. 발표에서는 "3개 운동 중 2개"로 말할 수 있다. 한계: RTK 주석자 A 오류 10개, ELK 2A 참가자 2명, 사후 분석.

## 업그레이드 백로그
 (1단계 이후, 가치 높은 순으로 진행)

1. ~~단위 테스트(pytest)와 재현성: 고정 seed, requirements.txt, 전체 검증 스크립트 하나로 묶기~~ → 회차 12 완료
2. ~~설정 파일(YAML) 기반 실험 실행기: 표현 × 모델 × 분할 × seed~~ → 회차 14 완료(JSON)
3. LSTM, TCN 구현(작은 모델, 강한 정규화)
4. augmentation: 좌우 반전, 수직축 회전, 스케일, 시간 왜곡 — "feature로 넣은 불변성 vs augmentation" 비교
5. 주석자 A / B / consensus 비교 실험
6. 심각도(Small/Large)별 recall 분석
7. ~~그림·표 자동 생성(논문용 confusion matrix, 표현 사다리 그래프)~~ → 회차 18 완료(confusion matrix는 P1 결과가 생기면 추가: 백로그 26)
8. 논문 Methods·Dataset 절 초안용 문서화
9. Paper 2의 hyperphysio 코드를 P1 설정으로 돌려 Macro-F1 직접 비교(가능하면)
10. ~~2A의 S1 동일인 여부, G3 B1–B3 의미, fps 확인(영상 필요)~~ → 2026-10-13 영상 확인: fps 확정, B1–B3 = 왼팔/오른팔/양팔(E1에서 확인), S1은 판정 불가로 분리 유지. `explore/video_check/README.md`
11. (회차 2에서 추가) 주 비교를 "ELK: C vs E2"와 "CTK: C vs E13" 두 이진 과제로 고정하는 설정 추가, RTK는 참고용 4-class
12. (회차 3에서 추가) pitch 대응: 정면(x-y) 평면 feature는 pitch 영향이 작고 시상(y-z) 평면 feature는 크다. features.py에서 (a) 각 녹화의 첫 구간(준비 자세) 대비 변화량 feature를 함께 만들고 (b) feature마다 평면을 표시해, pitch 차이에 강한 feature를 따로 비교할 것. G3 골격 데이터가 오면 G3 전체로 pitch 차이를 재측정 — (회차 4: 평면 태그와 Rerr_d 구현 완료, 비교 실험은 남음)
13. (회차 4에서 추가) "pitch에 강한 feature만"(invariant + frontal + horizontal) vs 전체 R4 비교 실험 — sim-to-real 격차가 줄어드는지
14. ~~(회차 6에서 추가) 짝지은 bootstrap~~ → 회차 13 완료: 같은 참가자 재표본에서 두 모델(예: R1 vs R4)의 Macro-F1 차이 구간 — 논문의 "개선" 주장 근거
15. (회차 6에서 추가) Macro-F1의 K를 전체 테스트셋의 존재 클래스로 고정한 변형(재표본에 없는 클래스는 제외 대신 표시)과 비교
16. ~~(회차 7에서 추가) 라벨의 환자 군집도 정량화~~ → 회차 9 완료: 환자별 클래스 비율, 군집 내 상관(ICC)과 유효 표본 수 — 논문 Dataset 절과 Limitations에 들어갈 표
17. ~~(회차 7에서 추가) "사람 특성" 교란 점검~~ → 회차 10 완료: 동작과 무관한 정적 feature(키, 몸통 길이, 카메라 거리, 준비 자세)만으로 환자의 오류 여부를 맞히는지. 맞히면 R0의 우위는 교란이다
18. (회차 7에서 추가) 표현 사다리를 feature 수에 덜 민감하게: 오류별 소수 feature만 쓴 모델, 차원 맞춘 비교, 또는 RF 대신 정규화가 강한 로지스틱 회귀 기준선 추가
19. ~~(회차 10에서 추가) 참가자 단위 permutation null~~ → 회차 11 완료: 환자별 라벨 묶음을 환자끼리 섞어(환자 안의 라벨 구성은 유지) P4를 반복, 아무 feature나 넣었을 때 Macro-F1이 우연히 얼마나 높게 나오는지의 95백분위. 표현별 결과가 이 선을 넘는지로 판단
20. (회차 10에서 추가) 녹화 길이와 오류의 관계: CTK에서 길이만으로 0.339. 오류 반복이 실제로 길거나 짧은지(정당한 동작 정보인지) 확인하고, 리샘플링으로 길이 정보가 사라지는 표현과의 차이를 논의
21. ~~(회차 11에서 추가) 순열 null을 P1~~ → 회차 17 완료(confirmatory.py의 고정 예측 null). 원문: 순열 null을 P1(G3 → 1A·2A)에도 적용: 테스트 참가자 사이에서 라벨 묶음을 섞어, sim-to-real 결과가 우연을 넘는지 판단(G3 데이터 도착 후)
22. (회차 13에서 추가) 군집 수가 적을 때의 bootstrap 보정: wild cluster bootstrap 또는 참가자 수가 적은 칸에서는 permutation 기반 차이 검정(두 표현의 예측을 참가자 단위로 맞바꾸는 순열)으로 대체
23. ~~(회차 14에서 추가) permutation_null을~~ → 회차 15 완료. 원문: permutation_null을 run_experiment의 과제 정의(label_col + classes)와 모델(rf, logreg)을 받도록 일반화하고, main_binary의 4개 과제에 적용 — CTK C vs E13이 우연을 넘는지 확인
24. (회차 14에서 추가) "모델 2종에서 같은 방향인가"를 자동으로 표시하는 요약(표현 쌍별로 RF·logreg 차이의 부호 일치 여부)
25. ~~(회차 15에서 추가) 사전 등록 문서~~ → 회차 16 완료. 원문: G3 데이터를 보기 전에 P1의 확증 비교(과제 = CTK C vs E13, 주 비교 = R1 vs R0와 Rerr vs R1, 지표 = Macro-F1, 기준 = 참가자 permutation null + 짝지은 bootstrap, 다중비교 보정 방법)를 고정해 PREREGISTRATION.md로 남긴다. 나머지는 탐색 분석으로 표시
26. (회차 18에서 추가) P1 결과가 생기면 figures.py에 confusion matrix(주 과제, 주석자 A·B)와 sim-to-real 사다리(P4 vs P1 나란히) 그림 추가
27. (2026-10-08 추가) P1에서 R0(raw) RF가 0.737로 높은 이유: 세션 교란·카메라 위치 feature가 우연히 테스트에 맞았는지(사람 특성 교란 점검을 P1에 적용), 순열 null 대비 유의성
28. (2026-10-08 추가) 경계 보정 실험: G3로 학습한 모델의 결정 기준점만 테스트 참가자 일부(예: leave-one-participant-out의 나머지)로 다시 맞추면 sim-to-real 성능이 회복되는지 — "기준점 이동" 가설의 직접 검증

## 재점검 기록

- 2026-10-08 19:07 · 통과 — VERIFY PASSED(전 단계 + 단위 테스트 26), manifest 46개 일치(확증 결과 불변), 사전 등록 해시 보호 유지, C 12 GB·E 187 GB, E 데이터 폴더 정상.
- 2026-10-08 21:07 · 통과 — VERIFY PASSED(전 단계 + 단위 테스트 26), manifest 46개 일치(확증 결과 불변), 사전 등록 해시 보호 유지, C 12 GB·E 187 GB, E 데이터 폴더 정상.
- 2026-10-08 23:07 · 통과 — VERIFY PASSED(전 단계 + 단위 테스트 26), manifest 46개 일치(확증 결과 불변), 사전 등록 해시 보호 유지, C 12 GB·E 187 GB, E 데이터 폴더 정상.
- 2026-10-09 01:07 · 통과 — VERIFY PASSED(전 단계 + 단위 테스트 26), manifest 46개 일치(확증 결과 불변), 사전 등록 해시 보호 유지, C 12 GB·E 187 GB, E 데이터 폴더 정상.
- 2026-10-09 03:07 · 통과 — VERIFY PASSED(전 단계 + 단위 테스트 26), manifest 46개 일치(확증 결과 불변), 사전 등록 해시 보호 유지, C 12 GB·E 187 GB, E 데이터 폴더 정상.
- 2026-10-09 05:07 · 통과 — VERIFY PASSED(전 단계 + 단위 테스트 26), manifest 46개 일치(확증 결과 불변), 사전 등록 해시 보호 유지, C 12 GB·E 187 GB, E 데이터 폴더 정상.
- 2026-10-09 07:07 · 통과 — VERIFY PASSED(전 단계 + 단위 테스트 26), manifest 46개 일치(확증 결과 불변), 사전 등록 해시 보호 유지, C 12 GB·E 187 GB, E 데이터 폴더 정상.
- 2026-10-09 09:10 · 통과 — VERIFY PASSED(전 단계 + 단위 테스트 26), manifest 46개 일치(확증 결과 불변), 사전 등록 해시 보호 유지, C 12 GB·E 187 GB, E 데이터 폴더 정상.
- 2026-10-09 11:07 · 통과 — VERIFY PASSED(전 단계 + 단위 테스트 26), manifest 46개 일치(확증 결과 불변), 사전 등록 해시 보호 유지, C 12 GB·E 187 GB, E 데이터 폴더 정상.
- 2026-10-09 13:07 · 통과 — VERIFY PASSED(전 단계 + 단위 테스트 26), manifest 46개 일치(확증 결과 불변), 사전 등록 해시 보호 유지, C 12 GB·E 187 GB, E 데이터 폴더 정상.
- 2026-10-09 15:09 · 통과 — VERIFY PASSED(전 단계 + 단위 테스트 26), manifest 46개 일치(확증 결과 불변), 사전 등록 해시 보호 유지, C 12 GB·E 187 GB, E 데이터 폴더 정상.
- 2026-10-09 17:43 · 통과 — VERIFY PASSED(전 단계 + 단위 테스트 26), manifest 46개 일치(확증 결과 불변), 사전 등록 해시 보호 유지, C 12 GB·E 187 GB, E 데이터 폴더 정상. 참고: 검증에 62분 걸림(평소 26분, PC 부하로 추정).
- 2026-10-09 19:38 · 통과 — VERIFY PASSED(전 단계 + 단위 테스트 26), manifest 46개 일치(확증 결과 불변), 사전 등록 해시 보호 유지, C 12 GB·E 187 GB, E 데이터 폴더 정상. 참고: 검증 58분(직전 회차부터 느려짐).
- 2026-10-09 21:33 · 통과 — VERIFY PASSED(전 단계 + 단위 테스트 26), manifest 46개 일치(확증 결과 불변), 사전 등록 해시 보호 유지, C 12 GB·E 187 GB, E 데이터 폴더 정상. 참고: 검증 53분, 점검 시작 시 전체 CPU 19%.
- 2026-10-09 · 재점검 중단(사용자 요청). 14회 모두 통과.
