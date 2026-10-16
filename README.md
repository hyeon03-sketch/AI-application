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
├── RULES.md                        ← 협업 규칙 전체 / full cowork rules
├── KERAAL_GitHub_Guide_KR/EN.pdf   ← GitHub 사용법 / how to use GitHub
├── .github/CODEOWNERS              ← 승인 담당자 / required reviewers
├── *.pdf, *.docx                   ← 제안서, 계획, 역할, 회의 안건, 보고서 / proposal, plan, roles, agendas, reports
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
# 0. 처음이면 사용법 PDF 먼저 / new to GitHub? read the guide PDF first
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
# GitHub에서 Pull Request 열기 → (공용 코드면 승인) → main에 merge
# Open a Pull Request on GitHub → (approval for shared code) → merge into main
```

---

## 협업 규칙 / Cowork rules

**전체 규칙 → [`RULES.md`](RULES.md)** · 처음 쓰는 사람 → [`KERAAL_GitHub_Guide_KR.pdf`](KERAAL_GitHub_Guide_KR.pdf) / [`_EN.pdf`](KERAAL_GitHub_Guide_EN.pdf)
**Full rules → [`RULES.md`](RULES.md)** · New to GitHub → the guide PDFs above.

> ⚠️ 이 저장소는 **공개(public)**다. 원본 데이터·파생 표·영상·영상 캡처·개인정보는 절대 올리지 않는다.
> ⚠️ This repository is **public**. Never commit raw data, derived tables, videos, video captures or personal information.

| 핵심 규칙 / Key rule | 내용 / Detail |
|---|---|
| `main` 보호 / protected | 직접 push 불가, 모든 변경은 PR로 / no direct pushes, every change via PR |
| 자기 폴더 / own folder | `members/<이름>/`만 바꾼 PR은 승인 없이 본인이 merge (웹 수정도 OK) / PRs touching only your folder: merge yourself, no approval (web edits OK) |
| 공용 코드·규칙 문서 / shared code & rule docs | `keraal_pipeline/`, `README.md`, `RULES.md`는 코드 담당자 승인 필수 / code-owner approval required |
| 브랜치 / branch | `이름/작업` (예 `roshini/r1-threshold`) / `name/task` |
| 커밋 / commit | 과제 ID로 시작 (예 `U2: add QC summary`) / start with the task ID |
| 확증 설정 / confirmatory config | `configs/p1_confirmatory.json` 수정 금지 / never edit |
| 결과 / results | 확증 이후는 모두 "탐색", `PROGRESS.md`에 날짜와 기록 / post-confirmatory = "exploratory", log in `PROGRESS.md` |
| 소통 / communication | Issues에 `[과제ID]`로, 막히면 바로 단톡 / Issues with `[taskID]`, ask early in the group chat |

---

## 마감 / Deadlines

| 날짜 / Date | 무엇 / What |
|---|---|
| 2026-10-16 (금 / Fri) | 중간 발표 전 팀 회의, R1·R2·U1·U2 결과 / pre-midterm meeting, R1/R2/U1/U2 results |
| 2026-10-23 (금 / Fri) | U3·U4 (Vicon 정렬, 2B 기준 분포 / Vicon alignment, 2B reference), R3·R4 (혼합 모형, 시간 구간 모델 / mixed model, temporal model) |

## 데이터 출처와 라이선스 / Data attribution and licence

- **KR.** 이 프로젝트는 KERAAL 데이터셋(https://keraal.enstb.org)을 사용한다. 데이터는 이 저장소에 포함되지 않는다. 저장소의 결과 표·그림은 KERAAL에서 파생된 집계값으로 **CC BY-NC-SA 4.0**(비영리, 출처 표시, 동일 조건) 조건을 따른다.
- **EN.** This project uses the KERAAL dataset (https://keraal.enstb.org). The data is not included in this repository. Result tables and figures here are aggregates derived from KERAAL and are shared under **CC BY-NC-SA 4.0** (non-commercial, attribution, share-alike).
- 코드는 수업 팀 프로젝트용이다 / Code is for the class team project.
