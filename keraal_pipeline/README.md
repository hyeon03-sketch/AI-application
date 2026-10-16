# KERAAL pipeline / KERAAL 파이프라인

참가자 독립 재활 운동 오류 분류 파이프라인. 진행 기록은 `PROGRESS.md`, 사전 등록과 확증 결과는 `PREREGISTRATION.md`,
저널급 연구 방향은 `RESEARCH_IDEAS.md`.
Subject-independent rehabilitation exercise error classification. See `PROGRESS.md` (log), `PREREGISTRATION.md`
(pre-registration and confirmatory results), `RESEARCH_IDEAS.md` (directions).

## 설치 / Setup
```
python -m pip install -r requirements.txt      # Python 3.12
```

## 데이터 / Data (공유 묶음에는 들어 있지 않음 / not included in the shared bundle)
KERAAL은 CC BY-NC-SA이므로 원본은 각자 받는다. / Download the data yourself (licence CC BY-NC-SA).

1. 확증 경로용 작은 사본 / small copies for the confirmatory path → `raw/`
   ```
   raw/group1A/{annotatorA,annotatorB,kinect}
   raw/group2A/{annotatorA,annotatorB,kinect}
   raw/group3/kinect
   raw/sample            (keraal_sample_2022.zip, optional)
   raw/g3_list.txt       (optional; Group 3 file listing)
   ```
   예 / e.g. `curl -sL https://keraal.enstb.org/data/group2A.tar.xz | tar -xJ -C raw/group2A --exclude='*videos*' --exclude='*openpose*' --exclude='*blazepose*'`
2. 전체 데이터(선택) / full dataset (optional): `bash tools/fetch_all.sh <dir>` then put `<dir>/extracted` in
   `data_root.txt` or `KERAAL_DATA`. 없으면 `inventory.py`는 SKIPPED로 통과한다. / Without it, inventory is skipped.

## 실행 / Run
```
python src/verify.py --no-manifest   # 데이터에서 전 단계 재생성 + 검사 + 단위 테스트 / rebuild everything, checks, tests
python src/manifest.py --freeze      # 자기 PC의 출력 해시 고정 / freeze hashes on your machine
python src/verify.py                 # 이후 재점검 / later re-checks
```
확증 분석 / confirmatory analysis:
```
python src/run_experiment.py --config configs/p1_confirmatory.json
python src/confirmatory.py
```
`configs/p1_confirmatory.json`은 사전 등록으로 고정되어 있다(바꾸면 단위 테스트 실패). 다른 실험은 새 설정 파일로.
The confirmatory config is hash-locked by a unit test; use a new config file for anything else.

## 구성 / Layout
- `src/` 단계별 스크립트 / stage scripts (index → labels → preprocess → features → splits → evaluate → models → analyses → figures)
- `tests/` 단위 테스트 / unit tests · `configs/` 실험 설정 / experiment configs · `explore/` 탐색 스크립트 · `tools/` 데이터 수집
