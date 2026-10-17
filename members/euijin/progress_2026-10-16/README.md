# KERAAL Rehab Exercise Feedback — Progress README (Uijin / EJ)

*As of 2026-10-16 (week 7). Prepared by Uijin (시의진) with AI assistance (Claude).*

> **요약 (KR)** — KERAAL 원천 데이터를 15 fps 프레임 단위 학습 표(Kinect·BlazePose CSV + QC 리포트)로 정제했습니다. 그 위에 Kinect 기반 규칙 파일럿(관절각 + 반복 정점 + 임계값)을 만들었습니다. 전문가 판정 대비 AUC는 CTK 0.72, ELK 0.74, RTK 0.88이고, 원본 영상과 함께 보는 모의 실시간 데모 영상 6개가 있습니다. 8–13주차에는 BlazePose로 옮기고, 특징 모델과 Causal TCN을 같은 기준으로 비교한 뒤 웹캠 데모를 만듭니다.

---

## 1. Goal

Home rehabilitation for low-back pain is done without a therapist present, so errors go uncorrected. Most skeleton-based assessment only says *correct / incorrect*.

**Target system:** a camera watches the user doing one of three KERAAL exercises (CTK, ELK, RTK). When an error occurs, the screen immediately shows the **error type + body region**.

- **Final input:** BlazePose skeleton, extracted from video.
- **Comparison only:** Kinect 3D skeleton.

## 2. What I did, week by week

Weeks are counted from 8/31 = week 1 (assumed).

| Week | Work | Output |
|---|---|---|
| 1–2 | Topic search across 12 domains | Selection criteria, candidate list |
| 3 | Topic fixed: rehab exercise error localization on KERAAL | Proposal (KR/EN), 5 related papers |
| 4–5 | Scope discussion. First annotation parser drafted from the KERAAL spec, then checked against the official sample zip (9/28–9/29) | Parser v1, confirmed file-name patterns |
| 6 | Parser v2 on the full dataset. **15 fps time axis verified.** Frame-level labels and QC built | `model_input_kinect.csv`, `model_input_blazepose.csv`, QC reports, metatable |
| 7 | Midterm report draft. **Kinect rule-based pilot**, evaluation and demo videos. 13-week plan | Pilot code + results, 6 demo videos, reports in `01_reports/` |

## 3. What is in this package

```
EJ_progress_2026-10-16/
├── README.md                          ← this file
├── 01_reports/
│   ├── Midterm_Report_Rehab_Error_Localization.docx / .pdf   midterm report draft (CVPR template, EN)
│   ├── KERAAL_Rule_Pilot_KR_EN.pdf                           pilot explained for the team (KR/EN)
│   └── Plan_Week1-13_BlazePose_KR.pdf                        full plan, weeks 1–13 (KR)
├── 02_data_cleaning/
│   ├── scripts/
│   │   ├── keraal_parse_annotations_v2.py   main builder: inspect / parse / build / selftest
│   │   ├── check_video_alignment.py         video length & fps vs annotations vs Kinect
│   │   └── summarize_model_input.py         CSV → summary_*.txt
│   └── qc/
│       ├── KERAAL_Metatable_EN_KO.pdf       every file and column explained (EN/KO)
│       ├── keraal_input_data_notes.md       confirmed facts + open questions
│       ├── model_input_{kinect,blazepose}_qc_report.txt
│       ├── summary_{kinect,blazepose}.txt
│       └── video_alignment.csv              evidence for the 15 fps time axis
├── 03_rule_baseline_code/                   Kinect rule-based pilot (Python)
│   └── README_KR.md, config.py, skeleton.py, kinematics.py, rule_engine.py,
│       extract_reps.py, calibrate.py, replay_demo.py, inspect_input.py, selftest_synthetic.py
└── 04_results/
    ├── RESULTS_KR.md                        results summary (KR)
    ├── results.csv, thresholds.json         per-exercise performance and thresholds
    ├── recs.csv, reps.csv                   per-recording / per-repetition peak values
    ├── plots/                               angle curves, Correct vs Incorrect distributions
    └── demo_videos/                         6 demos (Correct + Incorrect for each exercise)
```

**Not included (too large):**
- The cleaned CSVs `model_input_kinect.csv` (426 MB) and `model_input_blazepose.csv` (474 MB).
- The raw KERAAL data.

All of these are on Uijin's PC under `C:\EJ\Keraal\` (`input_data\` and `data\`). Ask if you need a copy.

## 4. Data cleaning (week 6)

**Input:** KERAAL raw folders for groups 1A, 2A and 3. They contain annotator A/B ANVIL files, Kinect, BlazePose, OpenPose and video.

**Output:** one row per frame, 15 fps, with labels and QC flags.

| File | Recordings | Rows (frames) | Error frames (1A/2A) |
|---|---|---|---|
| `model_input_kinect.csv` | 841 | 237,733 | 6.4% |
| `model_input_blazepose.csv` | 835 | 224,912 | 6.9% |

**Key facts found while cleaning:**
- **Time base is 15 fps.** Kinect frames ÷ annotator B end time = 15.00 for every recording. The video files say 10 fps, but that metadata is wrong.
- **Frame labels come from annotator A only.** Annotator B labels the whole recording as one segment.
- **Annotation often stops early.** Annotator A frequently stops where the error ends, so `in_annotated_span` marks frames after that point. Train on `yes`.
- **Some BlazePose files are broken.** 115 files are cut off part-way (`skeleton_truncated`), and 6 near-empty files were excluded.
- **Body part mostly follows error type.** Error2 is 97.7% Spine; Error1 and Error3 are mostly both arms. We therefore merge body parts into Spine / Arms.

**Rebuild:** `python keraal_parse_annotations_v2.py build --root <KERAAL folder> --outdir <out> --modality kinect` (or `blazepose`). Options: `--annotator A|B` and `--interval-track global|temporal|auto`.

Column meanings are in `KERAAL_Metatable_EN_KO.pdf`.

## 5. Rule-based pilot (week 7, Kinect)

**Method — no neural network:**
1. Compute one joint angle per exercise:
   - CTK: elevation of the lower arm
   - ELK: lateral trunk bend
   - RTK: shoulder-line vs hip-line rotation
2. Smooth the angle (EMA). The rest angle is taken from the first second.
3. A state machine finds each repetition and its peak: REST → UP → PEAK → DOWN.
4. **Decision:** if the peak excursion is below a threshold, the repetition is flagged as an error. In ML terms this is a *decision stump* (one feature, one split).
5. **Threshold:** one per exercise, chosen by maximum balanced accuracy against the therapist's **whole-recording evaluation** (Correct / Incorrect).
6. **Evaluation:** leave-one-participant-out (LOSO). Group 3 is excluded until the team confirms the pre-registration plan.

**Results** (Kinect, groups 1A/2A, 264 labelled recordings):

| Exercise | Recordings (Incorrect) | AUC | Threshold | LOSO sensitivity | LOSO specificity | LOSO balanced acc |
|---|---|---|---|---|---|---|
| CTK | 102 (41) | 0.72 | 76.5° | 0.61 | 0.66 | 0.63 |
| ELK | 78 (42) | 0.74 | 7.9° | 0.52 | 0.86 | 0.69 |
| RTK | 84 (11) | 0.88 | 17.0° | 0.82 | 0.74 | 0.78 |

**Findings:**
- **One angle already matches the team's earlier models.** AUC is similar to or above the team's earlier AUC (0.71–0.77). RTK has only 11 Incorrect recordings, so its numbers are uncertain.
- **The cut-off differs by group.** For CTK the best threshold is 76.5° for patients (1A) and 45.5° for healthy adults (2A); the per-participant spread (SD) is 22.3°. This supports the team's point that "where an error starts" depends on the data.
- **Annotated error spans relate to trunk lean, not range.** Frame-level spans relate more to forward/backward trunk lean than to range. For example, trunk flexion alone gives AUC 0.86 for RTK Error1.
- **Few repetitions per recording.** Each recording has only 1–2 repetitions: CTK holds the arms up for 10+ s, RTK turns once to each side.

## 6. Demo

`04_results/demo_videos/` contains one Correct and one Incorrect recording per exercise. Each recording is streamed frame by frame at 15 fps through the same code used for calibration. The screen shows:
- the original video
- the skeleton, with the error region in red
- the correction message and an angle gauge (yellow line = threshold)
- a timeline: red = therapist-annotated error, orange = rule decision

This is a **simulated** real-time demo from recordings. Webcam input comes after the BlazePose port (week 11).

## 7. How to run the pilot

```
cd C:\EJ\Keraal
.venv\Scripts\activate
cd keraal_rule_baseline
pip install -r requirements.txt
python extract_reps.py        # angles + repetitions  → recs.csv, reps.csv
python calibrate.py           # thresholds + LOSO     → results.csv, thresholds.json
python replay_demo.py --rec G1A-RTK-R1-Brest-019    # demo (q quit, space pause)
```
On another PC, edit only the paths at the top of `config.py`. Details are in `03_rule_baseline_code/README_KR.md`.

## 8. Next steps (weeks 8–13)

**Principles:**
- BlazePose only.
- Work from the cleaned CSV, not raw files.
- Every model uses the same LOSO split and the same metrics.

| Week | Step | Done when |
|---|---|---|
| 8 | Midterm. BlazePose QC (missing joints, aspect-ratio fix), BlazePose adapter, angle agreement vs Kinect, fixed `splits.csv` | Angles for ≥95% of 1A/2A recordings; error vs Kinect reported |
| 9 | Re-calibrate the rule baseline on BlazePose; feature model (logistic regression / GBM) | LOSO table for 3 exercises, compared with Kinect |
| 10 | Causal TCN v1: per-frame error yes/no + type + region | All folds trained; compared in the same table |
| 11 | Ablations and failure analysis; **live webcam demo** (MediaPipe) | Stable 15 fps; type + region on screen |
| 12 | Freeze evaluation (3 seeds, participant bootstrap CI), final figures, report draft | Numbers final |
| 13 | Final report, presentation, code clean-up | Reproducible from README |

## 9. Open questions for the team

1. **Group 3:** can it be used, at least for pre-training, given the pre-registered analysis plan?
2. **Error types:** what do Error1–3 mean for each exercise? Needed for the on-screen messages.
3. **Primary metric:** whole-recording AUC or frame-level segment F1?
4. **Annotation track:** global or temporal — which matches the real error timing better?
5. **Video resolution:** needed for the BlazePose aspect-ratio fix; probably read once from the video metadata.

## 10. Limitations

- Thresholds were calibrated and evaluated on the same groups (1A/2A). LOSO prevents participant leakage, but each exercise has only 8–11 participants.
- The rule covers only "too little range" errors; it misses compensation and timing errors.
- Kinect thresholds do not transfer to BlazePose and must be re-calibrated.
- Research feedback support only — not a medical judgement.

**References:**
- KERAAL dataset: Nguyen et al., IJCNN 2024 — https://arxiv.org/abs/2407.00521 · https://github.com/nguyensmai/KeraalDataset
- MediaPipe Pose Landmarker — https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker
