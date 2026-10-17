# KERAAL 재활 운동 오류 분류 — 진행 상황과 발표 흐름 / Progress and Presentation Flow

작성일 / Written: 2026-10-16 (중간 발표 전 마지막 팀 회의일 / last team meeting before the midterm presentation)
팀 / Team: 팀장 (lead) · 의진 Uijin (데이터 / data) · 로시니 Roshini (프로그래밍 / programming) · 조시 Joshi (이해·영상 확인 / understanding & video checks)

---

## 1. 프로젝트 한 줄 요약 / One-line summary

**KR.** 집에서 혼자 하는 재활 운동은 틀려도 알려 줄 사람이 없다. KERAAL 데이터(Kinect 골격)로 운동 오류를 자동으로 찾는 모델을 만들고, **건강인이 연기한 오류로 배운 모델이 실제 사람에게도 통하는지** 시험한다.

**EN.** People doing rehab exercises at home have no one to tell them when they make a mistake. Using the KERAAL dataset (Kinect skeletons), we build models that detect exercise errors automatically, and test **whether a model trained on errors acted by healthy people works on real people**.

## 2. 데이터 / Data

| 그룹 / Group | 누구 / Who | 비고 / Notes |
|---|---|---|
| 1A | 환자 / patients | 로봇(Poppy) 코칭, 주석자 A·B / robot-coached, annotators A & B |
| 2A | **건강한 성인** / **healthy adults** | 로봇 코칭. "1A + 2A = 환자"라고 쓴 곳은 고칠 것 / robot-coached; fix anywhere that says "1A + 2A = patients" |
| 3 (G3) | 건강인이 오류를 연기 / healthy people acting errors | 540개 녹화, 운동 × 클래스 45개씩 균형 / 540 recordings, balanced 45 per exercise × class |

- 운동 3개 / 3 exercises: CTK, ELK, RTK
- 근거 / Source: 공식 readme `E:\KERAAL_data\extracted\group3\readme_files_format.txt`
- 라이선스 CC BY-NC-SA: 원본 데이터·영상은 외부에 올리지 않는다 / Licence CC BY-NC-SA: raw data and videos are never uploaded.

## 3. 처음 질문과 사전 등록 / Original question and pre-registration

**KR.** "정규화한 운동학 feature가 raw 좌표보다 참가자 독립 오류 분류를 개선하는가?" G3로 학습하고 1A·2A로 시험한다(P1). 과제는 CTK C vs E13, 지표는 Macro-F1이다. G3 데이터를 보기 전에 `PREREGISTRATION.md`에 가설 H1–H3와 판정 기준(참가자 순열 null, 짝지은 bootstrap, Holm 보정)을 고정했다. `configs/p1_confirmatory.json`은 해시로 잠겨 있다.

**EN.** "Do normalized kinematic features improve participant-independent error classification over raw coordinates?" We train on G3 and test on 1A/2A (protocol P1). The task is CTK C vs E13 and the metric is Macro-F1. Before looking at G3 data, we fixed hypotheses H1–H3 and the decision rules (participant permutation null, paired bootstrap, Holm correction) in `PREREGISTRATION.md`. `configs/p1_confirmatory.json` is hash-locked.

## 4. 진행 기록 / Progress timeline

| 날짜 / Date | 한 일 / What was done |
|---|---|
| 10/01 | 제안서·연구 계획 / proposal and research plan |
| 10/02–10/05 | 파이프라인 구축(회차 1–17): 전처리, feature 사다리 R0–Rerr, 라벨 군집도, 사람 특성 교란 점검, 순열 null, 단위 테스트 26개, JSON 실험 실행기, 사전 등록 / pipeline build (rounds 1–17): preprocessing, feature ladder R0–Rerr, label clustering, person-confound check, permutation null, 26 unit tests, JSON experiment runner, pre-registration |
| 10/06 | 그림·표 자동 생성, G3 Kinect 다운로드(540개) / auto figures & tables, G3 Kinect download (540 files) |
| 10/08 | G3 포함 검증 통과 → **확증 분석 실행** / verification with G3 passed → **confirmatory analysis run** |
| 10/08–10/09 | 2시간마다 재점검 14회 모두 통과(manifest 일치, 확증 결과 불변) / 14 two-hourly re-checks all passed (manifest match, confirmatory results unchanged) |
| 10/12–10/13 | 팀 역할 문서, 프로젝트 개요 PDF, 팀원 Kinect 모델 보고서, 영상 확인 / team roles, project overview PDF, teammate's Kinect model report, video check |
| 10/16 | 팀 회의: R1·R2·U1·U2 결과 받기, 연구 질문 확정, 슬라이드 분담 / team meeting: collect R1/R2/U1/U2, fix the research question, assign slides |
| 10/16–10/17 | GitHub 저장소 개설(공개, `main` 보호), 의진·로시니 진행 내용 업로드 / GitHub repo set up (public, `main` protected), Euijin's and Roshini's progress uploaded |

## 5. 주요 결과 / Key results

### 5.1 확증 시험 (사전 등록) / Confirmatory test (pre-registered)

주석자 A, Random Forest, Holm 보정 / annotator A, Random Forest, Holm-adjusted:

| 가설 / H | 관측 / observed | 기준 / reference | p (Holm) | 지지 / supported |
|---|---|---|---|---|
| H1 Rerr > null | 0.407 | null 95% 0.428 | 0.286 | 아니오 / no |
| H2 R1 > R0 | −0.403 | 95% CI [−0.581, −0.210] | 1.000 | 아니오 (반대 방향, RF만) / no (opposite direction, RF only) |
| H3 Rerr > R1 | +0.073 | 95% CI [+0.000, +0.148] | 0.282 | 아니오 / no |

- 주석자 B, 로지스틱 회귀, 교란 feature 제거 분석도 모두 지지 안 됨 / Annotator B, logistic regression, and cue-removed analyses: none supported.
- 데이터 품질: 같은 참가자 안에서 trial을 맞힐 수 있음(세션 교란, 0.76–1.00). G3는 카메라 위치·자세가 다름(골반 높이 −0.51 m vs −0.19/−0.31 m) / Data quality: trials are identifiable within a participant (session confound, 0.76–1.00); G3 camera/posture differs (pelvis height −0.51 m vs −0.19/−0.31 m).

### 5.2 탐색 분석 (확증 이후, 모두 "탐색"으로 표시) / Exploratory (post-confirmatory, all labelled "exploratory")

- **KR.** 모델이 테스트 녹화의 **92–97%를 오류로 판정**했다(실제 오류 비율 41%).
  **EN.** The model labelled **92–97% of test recordings as errors** (true error rate 41%).
- **KR.** **반대 방향은 된다**: 1A·2A로 학습하고 G3로 시험하면(초 단위) AUC 0.71–0.77이다 (`KERAAL_Kinect_Model_Report.pdf`).
  **EN.** **The reverse direction works**: training on 1A/2A and testing on G3 (per second) gives AUC 0.71–0.77 (`KERAAL_Kinect_Model_Report.pdf`).
- **KR.** 기준점 이동 근거:
  - 어깨 거상 최대값은 G3 정상 126.9° / G3 오류 111.9° / 1A 정상 121.6° / 1A 오류 113.5°다.
  - CTK E1 손목 높이는 연기 정상 0.78 / 연기 오류 0.19 / 환자 정상 0.49 / 환자 오류 0.37이다.
  - 환자의 "정상"이 연기 데이터로 배운 경계 아래에 걸린다.
  - 주석자 A·B 사이에도 기준점 차이가 있다(RTK 약 12°).

  **EN.** Evidence for a threshold shift:
  - Max shoulder elevation is G3 normal 126.9° / G3 error 111.9° / 1A normal 121.6° / 1A error 113.5°.
  - CTK E1 wrist height is acted normal 0.78 / acted error 0.19 / patient normal 0.49 / patient error 0.37.
  - Patients' "normal" falls below the boundary learned from acted data.
  - The two annotators also differ in threshold (RTK about 12°).
- **KR.** 영상 확인(10/13): G3 B1/B2/B3 = 왼팔/오른팔/양팔이다(CTK·RTK E1에서 15/15, E2·E3·ELK는 미확인). 프레임 = 주석 시간 × 15이고, 실제 촬영 속도는 미확정이다. 2A S1은 장소별로 분리해 둔다.
  **EN.** Video check (10/13): G3 B1/B2/B3 = left/right/both arms (15/15 in CTK and RTK E1; E2, E3 and ELK unchecked). Frame = annotation time × 15; the true capture rate is unconfirmed. 2A S1 stays split by site.
- **한계 / Limits**:
  - 손목 높이는 결과를 본 뒤 고른 지표다 / Wrist height was chosen after seeing the results.
  - 1A는 서서, G3는 앉아서 운동했다 / 1A stood while G3 sat.
  - 표본이 작다 / The sample is small.
  - R0(raw) RF 0.737이 왜 높은지는 아직 설명되지 않았다(R2에서 점검) / Why R0 (raw) RF scores 0.737 is still unexplained (checked in R2).

### 5.3 팀원별 완료 현황 (2026-10-17) / Completed work by member (as of 2026-10-17)

각자 폴더의 README에 자세히 정리했다 / Details are in each member's README.

**의진 / Euijin** → [`members/euijin/`](members/euijin/) · 브랜치 / branch `euijin/progress-1016`

| 완료 / Done | 결과 / Result |
|---|---|
| 데이터 정제 v1 (6주차) / data cleaning v1 (week 6) | 15 fps 프레임 단위 표: Kinect 841개 녹화·237,733프레임, BlazePose 835개·224,912프레임 + QC 리포트·메타테이블 / frame-level tables + QC reports and metatable |
| 15 fps 시간축 확인 / 15 fps time base verified | Kinect 프레임 ÷ 주석자 B 종료 시간 = 15.00 (전 녹화). 영상 메타데이터의 10 fps는 틀림 / for every recording; the 10 fps in video metadata is wrong |
| Kinect 규칙 기반 파일럿 (7주차, 탐색) / rule-based pilot (week 7, exploratory) | 관절각 1개 + 임계값, LOSO: AUC CTK 0.72 · ELK 0.74 · RTK 0.88 / one angle + one threshold |
| 보고서 / reports | 중간 보고서 초안(영문), 파일럿 설명(한/영), 1–13주 계획 / midterm draft, pilot explainer, 13-week plan |

**로시니 / Roshini** → [`members/roshini/`](members/roshini/) · 브랜치 / branch `roshini/kinect-model`

| 완료 / Done | 결과 / Result |
|---|---|
| Kinect 초 단위 오류 탐지 모델, 방향 2 (탐색) / per-second Kinect model, Direction 2 (exploratory) | 1A + 2A 학습 → G3 시험(녹화 단위) AUC CTK 0.71 · ELK 0.77 · RTK 0.77, 모두 p = 0.001 / train real → test acted |
| 코드 5개 + 보고서 25쪽 / 5 scripts + 25-page report | `members/roshini/Kinect_model/` |

**두 결과가 팀 가설에 주는 것 / What the two results add to the team hypothesis**
- 의진: CTK 최적 임계값이 환자 76.5° vs 건강인 45.5°로 약 30° 다르다 → 기준점이 데이터마다 다르다는 것을 각도로 보여 준다 / CTK best threshold differs by ~30° between patients and healthy adults.
- 의진: 프레임 단위 오류 구간은 진폭보다 몸통 전후 기울기와 관련 있다(RTK Error1 AUC 0.86) → 보상 동작 가능성 / frame-level error spans relate to trunk lean (compensation).
- 로시니: 실제 → 연기 방향은 오류를 구분한다 → 인식 능력은 있다 / real → acted works, so recognition ability is there.

**아직 받지 못한 것 / Not received yet**

| ID | 담당 / Owner | 내용 / Item | 상태 / Status |
|---|---|---|---|
| R1 | 로시니 / Roshini | 경계 보정 실험 / threshold calibration | 미제출 / not submitted |
| R2 | 로시니 / Roshini | P1 raw 우위 점검 / P1 raw-advantage check | 미제출 / not submitted |
| U1 | 의진 / Euijin | 정제본 v2 (2A S1 분리 등 변경 4개) / cleaned v2 (4 changes) | v1 완료, v2 반영 여부 확인 필요 / v1 done, v2 to be confirmed |
| U2 | 의진 / Euijin | `temporal_segments.csv` | 미제출 / not submitted |
| — | 조시 / Joshi | 캡처 10장 + 체크 답 / captures + answers | 미제출 / not submitted |

## 6. 발표 흐름 / Presentation flow

**팀장 제안 연구 질문 / Proposed message**
> **KR.** "연기 데이터로 배운 모델이 실패한 이유는 인식 능력이 아니라 판정 기준점의 차이다."
> **EN.** "The model trained on acted data failed not because it cannot recognise errors, but because its decision threshold differs."

흐름 / Flow: 처음 질문 → 사전 등록 시험(실패) → 원인 분석(기준점) → 보정 실험(R1)으로 확인 중. 실패를 숨기지 않고 사전 등록을 강점으로 보여 준다.
Original question → pre-registered test (failed) → cause analysis (threshold) → being checked with the calibration experiment (R1). We show the failure openly and present the pre-registration as a strength.

- R1에서 보정 후 성능이 회복되면 "기준점 차이가 주원인"이라고 말한다 / If performance recovers after calibration in R1 → "the threshold shift is the main cause".
- 회복이 약하면 "기준점 가설은 확인 중"으로 낮춘다 / If recovery is weak → "the threshold hypothesis is still being tested".

**슬라이드 구성 (15분 가정) / Slide plan (assuming 15 min)**

| # | 내용 / Content | 근거 / Source |
|---|---|---|
| 1 | 문제: 집에서 하는 재활, 틀려도 알려 줄 사람이 없음 / Problem: home rehab, no one to correct you | Project Overview §1 |
| 2 | 데이터: 그룹 표(2A = 건강인), 운동 3개, 오류 정의 / Data: groups (2A = healthy), 3 exercises, error definitions | 공식 readme, 숙제 §2 / official readme, homework §2 |
| 3 | 질문과 사전 등록 설계(G3 → 1A·2A) / Question and pre-registered design | `PREREGISTRATION.md` |
| 4 | 결과 1: 확증 시험 실패(92–97% 오류 판정) / Result 1: confirmatory test failed | PREREGISTRATION Results, PROGRESS 10/08 |
| 5 | 결과 2: 반대 방향은 됨(AUC 0.71–0.77) / Result 2: reverse direction works | `KERAAL_Kinect_Model_Report.pdf` |
| 6 | 원인: 기준점 차이(연기 vs 실제 그림, 주석자 12°, 조시 캡처) / Cause: threshold shift (acted vs real figure, annotators 12°, Joshi captures) | `explore/video_check/` |
| 7 | 진행 중: 경계 보정(R1), 시간 구간 모델(R4) / In progress: calibration (R1), temporal-segment model (R4) | 10/16 결과 / 10/16 results |
| 8 | 남은 계획과 한계 / Next steps and limits | `PROGRESS.md` 백로그 / backlog |

사용할 그림 / Figures: `keraal_pipeline/explore/video_check/CTK_acted_vs_real.png`, `G3_CTK_E1_B1-B3.png`, `keraal_pipeline/results/figures/`

## 7. 규칙 / Rules

- 확증 분석 이후 결과는 모두 "탐색"으로 표시한다 / Label every post-confirmatory result "exploratory".
- 평가는 참가자 단위로 나눈다 / Split evaluation by participant.
- `configs/p1_confirmatory.json`은 바꾸지 않는다 / Never edit `configs/p1_confirmatory.json`.
- 영상·캡처는 수업 발표 안에서만 쓴다(CC BY-NC-SA) / Use videos and captures only inside the class presentation.
- 회의 결과는 `PROGRESS.md`에 한 단락으로 남긴다 / Record the meeting outcome as one paragraph in `PROGRESS.md`.

## 8. 파일 안내 / Where things are

| 파일 / File | 내용 / Content |
|---|---|
| `KERAAL_Project_Overview_KR.pdf` / `_EN.pdf` | 처음 볼 문서 / start here |
| `KERAAL_Team_Meeting_Agenda_1016_KR.pdf` / `_EN.pdf` | 10/16 회의 안건 / meeting agenda |
| `KERAAL_Team_Roles_KR.pdf` / `_EN.pdf` | 역할과 과제 / roles and tasks |
| `KERAAL_Kinect_Model_Report.pdf` | 반대 방향 실험 보고서 / reverse-direction report |
| `keraal_pipeline/PROGRESS.md` | 전체 진행 기록·백로그 / full log and backlog |
| `keraal_pipeline/PREREGISTRATION.md` | 사전 등록과 확증 결과 / pre-registration and results |
| `keraal_pipeline/CODE_GUIDE.md`, `README.md` | 코드 설명·실행 방법 / code guide and how to run |
| `keraal_pipeline/results/` | 결과 표·그림 / result tables and figures |
| `keraal_pipeline/explore/video_check/README.md` | 영상 확인 상세 / video check details |

GitHub 저장소와 압축본 `KERAAL_progress_2026-10-16.zip`에는 원본 데이터(`raw/`, `data/`), 영상(`Joshi_videos/`), 예전 대용량 압축본이 **들어 있지 않다**(라이선스·용량). 영상 캡처 PNG(`explore/video_check/*.png`)도 GitHub에는 올리지 않는다. 데이터 받는 방법은 `keraal_pipeline/README.md` 참고.
The GitHub repository and the `KERAAL_progress_2026-10-16.zip` bundle **do not include** raw data (`raw/`, `data/`), videos (`Joshi_videos/`), or the old large archives (licence and size); video-frame PNGs (`explore/video_check/*.png`) are not on GitHub either. See `keraal_pipeline/README.md` for how to get the data.
