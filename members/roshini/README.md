# Roshini (로시니) — 프로그래밍 / Programming

**역할 / Role.** 실험과 통계 모형으로 "기준점 차이" 가설을 시험한다 / Test the threshold hypothesis with experiments and statistical models.

## 할 일 / Tasks

| ID | 마감 / Due | 내용 / Item | 결과물 / Deliverable |
|---|---|---|---|
| R1 | 10/16 | 경계 보정 실험 / threshold calibration | `keraal_pipeline/src/threshold_calibration.py`, 새 config, 결과 표 / new config, result table |
| R2 | 10/16 | P1 raw 우위 점검 / P1 raw-advantage check | P1 교란 표 / P1 confound table |
| R3 | 10/23 | 주석자 기준점 혼합 모형 / annotator-threshold mixed model | `keraal_pipeline/explore/annotator_thresholds_mixed.py` |
| R4 | 10/23 | 시간 구간 모델 (U2 이후) / temporal model (after U2) | `keraal_pipeline/src/temporal_baseline.py` |

## 규칙 / Rules

- 새 실험 = `keraal_pipeline/configs/`에 **새 설정 파일**. `p1_confirmatory.json`은 바꾸지 않는다.
  New experiment = **new config file**; never edit `p1_confirmatory.json`.
- 새 스크립트에 `--check`를 넣고 `src/verify.py`에 추가, merge 전에 `python src/verify.py` 통과.
  Add `--check` and register it in `src/verify.py`; it must pass before merging.
- 결과는 "탐색"으로 표시하고 `PROGRESS.md`에 기록 / Label results "exploratory" and log them in `PROGRESS.md`.

## 연결 / Links

- 시험용 코드는 여기서 시작 → 다듬어지면 `keraal_pipeline/`으로 PR / Start trial code here → PR into `keraal_pipeline/` once polished
- 받는 데이터 / Inputs from: [`../euijin/`](../euijin/) (U1, U2)
- 코드 안내 / Code guide: [`../../keraal_pipeline/CODE_GUIDE.md`](../../keraal_pipeline/CODE_GUIDE.md)

## 메모 / Notes

