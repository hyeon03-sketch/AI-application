# AI application — KERAAL 재활 운동 오류 분류 / KERAAL Rehabilitation Exercise Error Classification

AI application 수업 팀 프로젝트 저장소 / Team project repository for the AI application class.

**KR.** 집에서 혼자 하는 재활 운동은 틀려도 알려 줄 사람이 없다. KERAAL 데이터(Kinect 골격)로 운동 오류를 자동으로 찾는 모델을 만들고, 건강인이 연기한 오류로 배운 모델이 실제 사람에게도 통하는지 시험한다.

**EN.** People doing rehab exercises at home have no one to tell them when they make a mistake. Using the KERAAL dataset (Kinect skeletons), we build models that detect exercise errors automatically, and test whether a model trained on errors acted by healthy people works on real people.

- 진행 상황과 발표 흐름 / Progress and presentation flow → [`PROGRESS_AND_PRESENTATION.md`](PROGRESS_AND_PRESENTATION.md)
- 처음 볼 문서 / Start here → [`KERAAL_Project_Overview_KR.pdf`](KERAAL_Project_Overview_KR.pdf) · [`_EN.pdf`](KERAAL_Project_Overview_EN.pdf)
- 상세 진행 기록 / Detailed log → [`keraal_pipeline/PROGRESS.md`](keraal_pipeline/PROGRESS.md)

---

## 팀과 개인 폴더 / Team and personal folders

| 이름 / Name | 역할 / Role | 개인 폴더 / Folder | 브랜치 접두어 / Branch prefix |
|---|---|---|---|
| Sonny | 팀장, 저장소 관리 / lead, repo owner | [`members/sonny/`](members/sonny/) | `sonny/` |
| Euijin (의진) | 데이터 / data (U1–U4) | [`members/euijin/`](members/euijin/) | `euijin/` |
| Roshini (로시니) | 프로그래밍 / programming (R1–R4) | [`members/roshini/`](members/roshini/) | `roshini/` |
| Joshi (조시) | 관찰·이해 / observation & understanding | [`members/joshi/`](members/joshi/) | `joshi/` |

**KR.** 개인 폴더는 각자의 작업 공간이다(메모, 초안, 시험 코드). 팀이 함께 쓰는 코드는 `keraal_pipeline/`에 있다. 개인 폴더에서 다듬은 코드를 팀 코드로 옮길 때는 Pull Request로 올린다. 각 개인 폴더의 `README.md`에 이번 주 할 일과 결과 링크를 적는다.

**EN.** Personal folders are each member's workspace (notes, drafts, trial code). Shared team code lives in `keraal_pipeline/`. To move polished code from a personal folder into the shared code, open a Pull Request. Each personal `README.md` lists that member's tasks for the week and links to their results.

## 저장소 구성 / Repository layout

```
AI application/
├── README.md                       ← 이 파일: 소개 + 협업 규칙 / this file: intro + cowork rules
├── PROGRESS_AND_PRESENTATION.md    ← 진행 상황·발표 흐름 / progress & presentation flow
├── *.pdf, *.docx                   ← 제안서, 계획, 역할, 회의 안건, 보고서 / proposal, plan, roles, agendas, reports
├── The sixth video lecture/        ← 수업 과제 / class assignment
├── members/                        ← 개인 폴더 / personal folders
│   ├── sonny/  euijin/  roshini/  joshi/
└── keraal_pipeline/                ← 팀 공용 코드 / shared code
    ├── src/  tests/  configs/  tools/  explore/
    ├── results/                    ← 결과 표·그림 / result tables & figures
    └── PROGRESS.md  PREREGISTRATION.md  CODE_GUIDE.md  README.md
```

**GitHub에 없는 것 / Not on GitHub** (`.gitignore`): `keraal_pipeline/raw/`, `keraal_pipeline/data/`, 영상(`Joshi_videos/`), 영상 캡처 PNG, 모든 `.zip`, 각자의 `data_root.txt`. 데이터는 각자 받는다 → [`keraal_pipeline/README.md`](keraal_pipeline/README.md) / Everyone downloads the data themselves.

---

## 처음 시작하기 / Getting started

```bash
# 1. 초대 수락 후 내려받기 / accept the invite, then clone
git clone https://github.com/hyeon03-sketch/AI-application.git
cd AI-application

# 2. 내 이름 설정 (이 저장소에만) / set your name (this repo only)
git config user.name  "<your GitHub username>"
git config user.email "<your GitHub email>"

# 3. 파이썬 패키지 / Python packages (Python 3.12)
python -m pip install -r keraal_pipeline/requirements.txt

# 4. 데이터 위치 지정 (각자 PC) / point to your data (per machine)
#    keraal_pipeline/data_root.txt 파일에 경로 한 줄, 예: E:/KERAAL_data/extracted
#    (이 파일은 GitHub에 올라가지 않는다 / this file is not committed)
```

## 매일 작업 순서 / Daily workflow

```bash
git checkout main
git pull                                   # 최신 받기 / get the latest
git checkout -b roshini/r1-threshold       # 내 브랜치 / your branch: <name>/<task>
# ... 작업 / work ...
git add members/roshini keraal_pipeline/src/threshold_calibration.py
git commit -m "R1: add threshold calibration script"
git push -u origin roshini/r1-threshold
# GitHub에서 Pull Request 열기 → 리뷰 → main에 merge
# Open a Pull Request on GitHub → review → merge into main
```

---

## 협업 규칙 / Cowork rules

### 1. 브랜치와 Pull Request / Branches and Pull Requests

- **KR.** `main`에 직접 push하지 않는다. 브랜치 이름은 `이름/작업` 형식이다(예: `euijin/u2-segments`, `sonny/slides`).
  **EN.** Do not push directly to `main`. Branch names follow `name/task` (e.g. `euijin/u2-segments`, `sonny/slides`).
- **KR.** 자기 개인 폴더(`members/<이름>/`)만 바꾼 PR은 본인이 바로 merge해도 된다.
  **EN.** A PR that only touches your own `members/<name>/` folder can be merged by yourself.
- **KR.** `keraal_pipeline/`이나 루트 문서를 바꾸는 PR은 **다른 한 명 이상이 승인**한 뒤 merge한다. 코드는 로시니나 Sonny가, 데이터 처리는 의진이 보는 것을 기본으로 한다.
  **EN.** A PR that changes `keraal_pipeline/` or root documents needs **approval from at least one other member** before merging. By default, Roshini or Sonny reviews code and Euijin reviews data processing.
- **KR.** 남의 개인 폴더는 고치지 않는다. 의견은 PR 댓글이나 Issue로 남긴다.
  **EN.** Don't edit someone else's personal folder; leave comments on the PR or open an Issue.

### 2. 커밋 / Commits

- **KR.** 커밋 메시지는 한 줄 요약으로, 과제 ID를 앞에 붙인다(예: `U2: add QC summary`, `R1: fix threshold refit`, `docs: update slide plan`).
  **EN.** Commit messages are one-line summaries prefixed with the task ID (e.g. `U2: add QC summary`, `R1: fix threshold refit`, `docs: update slide plan`).
- **KR.** 작게 자주 커밋한다. 하루 작업이 끝나면 push한다.
  **EN.** Commit small and often; push at the end of each working day.

### 3. 데이터와 영상 (가장 중요) / Data and videos (most important)

- **KR.** KERAAL은 CC BY-NC-SA다. **원본 데이터, 원본에서 만든 표(`model_input_*.csv`, `temporal_segments.csv` 등), 영상, 영상 캡처는 GitHub에 올리지 않는다.** 비공개 저장소여도 마찬가지다. 이런 파일은 팀 공유 드라이브나 직접 전달로 주고받는다.
  **EN.** KERAAL is CC BY-NC-SA. **Never commit raw data, tables derived from it (`model_input_*.csv`, `temporal_segments.csv`, …), videos, or video frames**, even though the repo is private. Share those through the team drive or hand them over directly.
- **KR.** 올려도 되는 것: 코드, 설정 파일, 결과 요약 표·그림(집계값), 문서.
  **EN.** OK to commit: code, configs, summary result tables and figures (aggregated values), documents.
- **KR.** 100 MB가 넘는 파일은 GitHub가 받지 않는다. 큰 파일은 올리기 전에 물어본다.
  **EN.** GitHub rejects files over 100 MB; ask before committing anything large.

### 4. 연구 규칙 / Research rules

- **KR.** `keraal_pipeline/configs/p1_confirmatory.json`은 사전 등록으로 잠겨 있다. **절대 바꾸지 않는다**(바꾸면 단위 테스트가 실패한다). 새 실험은 `configs/`에 새 설정 파일로 만든다.
  **EN.** `keraal_pipeline/configs/p1_confirmatory.json` is locked by the pre-registration. **Never edit it** (the unit tests fail if you do). New experiments get a new config file in `configs/`.
- **KR.** 확증 분석(2026-10-08) 이후 결과는 모두 **"탐색(exploratory)"**으로 표시한다.
  **EN.** Every result after the confirmatory run (2026-10-08) is labelled **"exploratory"**.
- **KR.** 평가는 항상 참가자 단위로 나눈다. 점수 옆에 다수 클래스 기준선, 순열 null 95%, 유효 N을 함께 적고, 주석자 A·B를 둘 다 보고한다.
  **EN.** Always split by participant. Report the majority baseline, the permutation-null 95th percentile and the effective N next to every score, for both annotators.
- **KR.** 새 스크립트에는 `--check` 자체 시험을 넣고 `src/verify.py`에 추가한다. 팀 코드에 merge하기 전에 `python src/verify.py`가 통과해야 한다.
  **EN.** New scripts get a `--check` self-test and are added to `src/verify.py`. `python src/verify.py` must pass before merging into the shared code.
- **KR.** 한 일과 찾은 것은 날짜와 함께 `keraal_pipeline/PROGRESS.md`에 한 단락으로 남긴다.
  **EN.** Log what you did and found, with the date, as one paragraph in `keraal_pipeline/PROGRESS.md`.

### 5. 소통 / Communication

- **KR.** 할 일, 버그, 질문은 GitHub **Issues**에 올리고 담당자를 지정한다. 제목 앞에 과제 ID를 붙인다(예: `[R4] 시간 구간 모델 지표 정하기`).
  **EN.** Put tasks, bugs and questions in GitHub **Issues** and assign an owner. Prefix the title with the task ID (e.g. `[R4] decide temporal-model metric`).
- **KR.** 막히면 혼자 오래 붙잡지 말고 Issue나 단톡방에 바로 물어본다. 디버깅은 회의 밖에서 한다.
  **EN.** If you're stuck, ask early in an Issue or the group chat. Debugging happens outside meetings.
- **KR.** 회의 결과는 Sonny가 `PROGRESS.md`에 한 단락으로 정리한다.
  **EN.** Sonny records each meeting's outcome as one paragraph in `PROGRESS.md`.

---

## 마감 / Deadlines

| 날짜 / Date | 무엇 / What |
|---|---|
| 2026-10-16 (금 / Fri) | 중간 발표 전 팀 회의, R1·R2·U1·U2 결과 / pre-midterm meeting, R1/R2/U1/U2 results |
| 2026-10-23 (금 / Fri) | U3·U4 (Vicon 정렬, 2B 기준 분포 / Vicon alignment, 2B reference), R3·R4 (혼합 모형, 시간 구간 모델 / mixed model, temporal model) |

라이선스 / Licence: 코드는 팀 내부용. KERAAL 데이터는 CC BY-NC-SA이며 이 저장소에 포함되지 않는다.
Code is for team-internal use. KERAAL data is CC BY-NC-SA and is not included in this repository.
