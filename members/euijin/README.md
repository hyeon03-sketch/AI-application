# Euijin (의진) — 데이터 / Data

**역할 / Role.** 데이터를 믿을 수 있게 만들고, 로시니에게 분석용 표를 넘긴다 / Make the data trustworthy and hand Roshini the tables the analyses need.

## 지금까지 완료한 것 / Completed so far (2026-10-16 기준 / as of)

전체 내용 / Full details → [`progress_2026-10-16/README.md`](progress_2026-10-16/README.md) · 브랜치 / branch `euijin/progress-1016`

| 주차 / Week | 완료 / Done | 결과물 / Output |
|---|---|---|
| 1–3 | 주제 탐색(12개 분야) → KERAAL 재활 운동 오류 위치 찾기로 확정, 제안서·관련 논문 5편 / topic search (12 domains) → fixed on KERAAL error localization, proposal, 5 related papers | 제안서 / proposal |
| 4–5 | 주석 파서 v1, 공식 샘플로 파일 이름 규칙 확인 / annotation parser v1, file-name patterns checked on the official sample | `keraal_parse_annotations_v2.py`의 전신 / predecessor |
| 6 | **데이터 정제**: 15 fps 프레임 단위 학습 표(Kinect 841개 녹화·237,733프레임, BlazePose 835개·224,912프레임) + QC. **15 fps 시간축 확인**(Kinect 프레임 ÷ 주석자 B 종료 시간 = 15.00, 전 녹화) / **data cleaning**: frame-level tables + QC; **15 fps time base verified** | [`02_data_cleaning/`](progress_2026-10-16/02_data_cleaning/), 메타테이블 PDF / metatable |
| 7 | **Kinect 규칙 기반 파일럿**(관절각 1개 + 반복 정점 + 임계값, LOSO): AUC CTK 0.72 · ELK 0.74 · RTK 0.88 / **rule-based pilot** | [`03_rule_baseline_code/`](progress_2026-10-16/03_rule_baseline_code/), [`04_results/RESULTS_KR.md`](progress_2026-10-16/04_results/RESULTS_KR.md) |
| 7 | 중간 보고서 초안(CVPR 양식, 영문), 파일럿 설명(한/영), 1–13주 계획 / midterm report draft, pilot explainer, 13-week plan | [`01_reports/`](progress_2026-10-16/01_reports/) |

**팀 가설과 연결되는 발견 / Findings linked to the team hypothesis (탐색 / exploratory)**
- CTK 최적 임계값이 환자(1A) 76.5° vs 건강인(2A) 45.5°로 약 30° 차이 → "기준점이 데이터마다 다르다"를 각도로 보여 줌 / The best CTK threshold differs by ~30° between patients and healthy adults, which shows the threshold shift in degrees.
- 프레임 단위 오류 구간은 진폭보다 **몸통 전후 기울기**와 관련(RTK Error1 AUC 0.86) → 보상 동작 가능성 / Frame-level error spans relate to **trunk lean** rather than range, suggesting compensation.

**GitHub에 올리지 않은 것 / Not on GitHub**
- `04_results/demo_videos/*.mp4` 6개: 원본 녹화 영상이 들어 있어 팀 규칙(CC BY-NC-SA, 영상 비공개)에 따라 제외. 발표에서만 사용 / contain original recording footage, excluded under the team rule; use only in the presentation.
- 정제 CSV(`model_input_kinect.csv` 426 MB, `model_input_blazepose.csv` 474 MB)와 원본 데이터: 의진 PC `C:\EJ\Keraal\` / cleaned CSVs and raw data stay on Euijin's PC.

## 할 일 / Tasks

| ID | 마감 / Due | 내용 / Item | 상태 / Status |
|---|---|---|---|
| U1 | 10/14 | 정제본 v2 (2A S1 장소별 분리, 주석자 B 녹화 라벨, 학습 필터 열, Temporal error 메모 정정) / cleaned dataset v2 | v1 완료, v2 변경 4개는 확인 필요 / v1 done, the 4 v2 changes to be confirmed |
| U2 | 10/16 | 시간 구간 표 `temporal_segments.csv` / temporal-segment table | 이번 묶음에 없음 / not in this package |
| U3 | 10/23 | G3 Vicon–Kinect 정렬 / alignment | 예정 / planned |
| U4 | 10/23 | 2B 기준 분포 / reference distribution | 예정 / planned |
| — | 8–13주 | BlazePose 이식 → 특징 모델·Causal TCN → 웹캠 데모 (자세한 계획은 `01_reports/Plan_Week1-13_BlazePose_KR.pdf`) / BlazePose port → feature model & causal TCN → webcam demo | 계획 / planned |

## 팀에 묻는 것 / Open questions for the team

1. Group 3를 사전 학습에라도 써도 되는가(사전 등록과의 관계)? / Can Group 3 be used, at least for pre-training, given the pre-registration?
2. 운동별 Error1–3의 뜻은? (화면 메시지에 필요) / What do Error1–3 mean per exercise?
3. 주 지표: 녹화 단위 AUC vs 프레임 단위 구간 F1? / Primary metric: recording AUC or frame-level segment F1?
4. 주석 트랙: global vs temporal? / Annotation track: global or temporal?

## 주의 / Important

- 정제 CSV와 `temporal_segments.csv`는 원본에서 만든 데이터라 GitHub에 올리지 않는다. 팀 공유 드라이브로 전달한다 / Derived tables are never committed; share via the team drive.
- 넘겨줄 곳 / Hand-off to: [`../roshini/`](../roshini/)
