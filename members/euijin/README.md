# Euijin (의진) — 데이터 / Data

**역할 / Role.** 데이터를 믿을 수 있게 만들고, 로시니에게 분석용 표를 넘긴다 / Make the data trustworthy and hand Roshini the tables the analyses need.

## 할 일 / Tasks

| ID | 마감 / Due | 내용 / Item | 완료 기준 / Done when |
|---|---|---|---|
| U1 | 10/14 | 정제본 v2 / cleaned dataset v2 | Kinect 값 원본 일치, 2A S1 장소별 분리 / values match originals, 2A S1 split by site |
| U2 | 10/16 | 시간 구간 표 / temporal-segment table | Temporal error 98구간, 프레임 = 주석 시간 × 15 / all 98 segments, frame = time × 15 |
| U3 | 10/23 | G3 Vicon–Kinect 정렬 / alignment | 540쌍 정렬, 마커–관절 대응표 / 540 pairs, marker-to-joint map |
| U4 | 10/23 | 2B 기준 분포 / reference distribution | 149개 포함, `explore/camera_geometry.py`와 같은 형식 / all 149, same format |

## 주의 / Important

- `model_input_*_v2.csv`, `temporal_segments.csv`는 **원본에서 만든 데이터라 GitHub에 올리지 않는다**(`.gitignore`가 막는다). 팀 공유 드라이브로 전달한다.
  These tables are derived from the raw data, so **they are not committed** (`.gitignore` blocks them). Share them via the team drive.
- 여기에는 **코드, QC 요약(집계값), 변경 노트**만 올린다 / Commit only code, QC summaries (aggregates) and change notes here.

## 연결 / Links

- 팀 코드로 옮길 스크립트는 `keraal_pipeline/src/`로 PR / Scripts that become shared code → PR into `keraal_pipeline/src/`
- 데이터 기준 / Data keys: `keraal_pipeline/data/master_index.csv` (각자 PC에서 생성 / generated locally)
- 넘겨줄 곳 / Hand-off to: [`../roshini/`](../roshini/)

## 메모 / Notes

