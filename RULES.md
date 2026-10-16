# 협업 규칙 / Cowork Rules

KERAAL 팀 저장소의 협업 규칙 / Cowork rules for the KERAAL team repository.
처음 쓰는 사람은 사용법 PDF를 먼저 보세요 / New to GitHub? Read the guide first: [`KERAAL_GitHub_Guide_KR.pdf`](KERAAL_GitHub_Guide_KR.pdf) · [`_EN.pdf`](KERAAL_GitHub_Guide_EN.pdf)

> ⚠️ **이 저장소는 공개(public)다. 전 세계 누구나 모든 파일을 볼 수 있다.**
> ⚠️ **This repository is public. Anyone in the world can see every file.**

---

## 1. 데이터와 영상 (가장 중요) / Data and videos (most important)

- **KR.** KERAAL은 CC BY-NC-SA다. **원본 데이터, 원본에서 만든 표(`model_input_*.csv`, `temporal_segments.csv` 등), 영상, 영상 캡처는 절대 올리지 않는다.** 이런 파일은 카톡이나 팀 공유 드라이브로 주고받는다. `.gitignore`가 대부분 막지만, 이름을 바꾼 파일까지 막지는 못한다.
  **EN.** KERAAL is CC BY-NC-SA. **Never commit raw data, tables derived from it (`model_input_*.csv`, `temporal_segments.csv`, …), videos, or video captures.** Share those via KakaoTalk or the team drive. `.gitignore` blocks most of them, but not renamed copies.
- **KR.** 올려도 되는 것: 코드, 설정 파일, 결과 요약 표·그림(집계값), 문서.
  **EN.** OK to commit: code, configs, summary result tables and figures (aggregated values), documents.
- **KR.** 개인정보(전화번호, 학번, 이메일, 얼굴 사진)와 다른 수업 과제 답안은 올리지 않는다.
  **EN.** No personal information (phone numbers, student IDs, emails, face photos) and no answers to other class assignments.
- **KR.** 100 MB가 넘는 파일은 GitHub가 받지 않는다. 큰 파일은 올리기 전에 Sonny에게 묻는다.
  **EN.** GitHub rejects files over 100 MB; ask Sonny before committing anything large.
- **KR.** 실수로 올렸다면 지우지 말고 **바로 Sonny에게 알린다**. 기록에서까지 지워야 하기 때문이다.
  **EN.** If you upload something by mistake, **tell Sonny right away** instead of just deleting it, because it has to be removed from the history too.

## 2. `main` 브랜치는 보호되어 있다 / `main` is protected

- **KR.** `main`에는 직접 push할 수 없다. **모든 변경은 Pull Request(PR)로 들어간다.** 강제 push와 `main` 삭제도 막혀 있다.
  **EN.** You cannot push directly to `main`. **Every change goes in through a Pull Request (PR).** Force pushes and deleting `main` are blocked.
- **KR.** 브랜치 이름은 `이름/작업` 형식이다(예: `euijin/u2-segments`, `roshini/r1-threshold`, `joshi/notes`).
  **EN.** Branch names follow `name/task` (e.g. `euijin/u2-segments`, `roshini/r1-threshold`, `joshi/notes`).

| 무엇을 바꾸나 / What you change | 승인 / Approval | 누가 merge / Who merges |
|---|---|---|
| 자기 폴더 `members/<이름>/`만 / only your own `members/<name>/` | 필요 없음 / not needed | 본인 / yourself |
| `keraal_pipeline/`, `README.md`, `RULES.md`, `.github/` | **코드 담당자 승인 필수** (GitHub가 강제) / **code-owner approval required** (enforced by GitHub) | 승인 후 본인 / yourself, after approval |
| 루트의 PDF·문서 / root PDFs and documents | 다른 팀원 1명 (약속) / one other member (by agreement) | 승인 후 본인 / yourself, after approval |

- **KR.** 코드 담당자는 `.github/CODEOWNERS`에 적혀 있다. 지금은 Sonny이고, 팀원이 초대를 수락하면 로시니(코드)와 의진(데이터)을 추가한다.
  **EN.** Code owners are listed in `.github/CODEOWNERS`. For now it's Sonny; Roshini (code) and Euijin (data) are added once they accept their invites.
- **KR.** **웹사이트에서 고칠 때**: 연필 ✏️로 수정 → [Commit changes] → "Create a new branch for this commit and start a pull request" 선택 → [Propose changes] → [Create pull request] → 자기 폴더면 바로 [Merge pull request].
  **EN.** **Editing on the website**: pencil ✏️ → [Commit changes] → choose "Create a new branch for this commit and start a pull request" → [Propose changes] → [Create pull request] → if it's your own folder, [Merge pull request] right away.
- **KR.** 남의 개인 폴더는 고치지 않는다. 의견은 PR 댓글이나 Issue로 남긴다.
  **EN.** Don't edit someone else's personal folder; leave comments on the PR or open an Issue.

## 3. 커밋 / Commits

- **KR.** 커밋 메시지는 한 줄 요약으로, 과제 ID를 앞에 붙인다(예: `U2: add QC summary`, `R1: fix threshold refit`, `docs: update slide plan`).
  **EN.** Commit messages are one-line summaries prefixed with the task ID (e.g. `U2: add QC summary`, `R1: fix threshold refit`, `docs: update slide plan`).
- **KR.** 작업 전에는 항상 최신을 받는다(Pull). 작게 자주 커밋하고, 하루 작업이 끝나면 push한다.
  **EN.** Always pull the latest before you start. Commit small and often; push at the end of each working day.

## 4. 연구 규칙 / Research rules

- **KR.** `keraal_pipeline/configs/p1_confirmatory.json`은 사전 등록으로 잠겨 있다. **절대 바꾸지 않는다**(바꾸면 단위 테스트가 실패한다). 새 실험은 `configs/`에 새 설정 파일로 만든다.
  **EN.** `keraal_pipeline/configs/p1_confirmatory.json` is locked by the pre-registration. **Never edit it** (the unit tests fail if you do). New experiments get a new config file in `configs/`.
- **KR.** 확증 분석(2026-10-08) 이후 결과는 모두 **"탐색(exploratory)"**으로 표시한다.
  **EN.** Every result after the confirmatory run (2026-10-08) is labelled **"exploratory"**.
- **KR.** 평가는 항상 참가자 단위로 나눈다. 점수 옆에 다수 클래스 기준선, 순열 null 95%, 유효 N을 함께 적고, 주석자 A·B를 둘 다 보고한다.
  **EN.** Always split by participant. Report the majority baseline, the permutation-null 95th percentile and the effective N next to every score, for both annotators.
- **KR.** 새 스크립트에는 `--check` 자체 시험을 넣고 `src/verify.py`에 추가한다. 공용 코드에 merge하기 전에 `python src/verify.py`가 통과해야 한다.
  **EN.** New scripts get a `--check` self-test and are added to `src/verify.py`. `python src/verify.py` must pass before merging into the shared code.
- **KR.** 한 일과 찾은 것은 날짜와 함께 `keraal_pipeline/PROGRESS.md`에 한 단락으로 남긴다.
  **EN.** Log what you did and found, with the date, as one paragraph in `keraal_pipeline/PROGRESS.md`.

## 5. 소통 / Communication

- **KR.** 할 일, 버그, 질문은 GitHub **Issues**에 올리고 담당자를 지정한다. 제목 앞에 과제 ID를 붙인다(예: `[R4] 시간 구간 모델 지표 정하기`).
  **EN.** Put tasks, bugs and questions in GitHub **Issues** and assign an owner. Prefix the title with the task ID (e.g. `[R4] decide temporal-model metric`).
- **KR.** 막히면 혼자 오래 붙잡지 말고 Issue나 단톡방에 바로 물어본다. 디버깅은 회의 밖에서 한다.
  **EN.** If you're stuck, ask early in an Issue or the group chat. Debugging happens outside meetings.
- **KR.** 회의 결과는 Sonny가 `PROGRESS.md`에 한 단락으로 정리한다.
  **EN.** Sonny records each meeting's outcome as one paragraph in `PROGRESS.md`.

## 6. 데이터 출처 / Data attribution

이 프로젝트는 KERAAL 데이터셋을 사용한다. 데이터는 이 저장소에 포함되지 않으며, 저장소의 결과 표·그림은 KERAAL에서 파생된 집계값으로 **CC BY-NC-SA 4.0** 조건(비영리, 출처 표시, 동일 조건 변경 허락)을 따른다.
This project uses the KERAAL dataset (https://keraal.enstb.org). The data is not included here; result tables and figures in this repository are aggregates derived from KERAAL and follow **CC BY-NC-SA 4.0** (non-commercial, attribution, share-alike).
