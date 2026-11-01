# Research report: adding rehab data to sports 3D data lets single-camera 3D motion capture beat the Kinect on rehab movements

2026-10-31 · Sonny (AI application team) · status: exploratory, 3 seeds × 3 participant folds · 한국어: [`RESEARCH_REPORT_KR.md`](RESEARCH_REPORT_KR.md)

---

## Conclusion (first page)

> **A 2D→3D model trained on sports data (ASPset-510) alone could not handle rehab movements. After post-hoc camera calibration of a rehab dataset (KERAAL) and mixing it into training, a single ordinary camera produced more accurate joint angles than a Kinect depth sensor on new participants never used in training.**

| | ASPset only | **ASPset + KERAAL** | Kinect sensor |
|---|---|---|---|
| KERAAL joint-position error (MPJPE) | 222.9 ± 3.0 mm | **69.5 ± 0.8 mm** | – |
| KERAAL joint-angle correlation (r0) | 0.59 | **0.76** | 0.67 |
| KERAAL joint-angle error (RMSE) | 20.3° | **13.9°** | 18.7° |
| Trunk-rotation exercise (RTK) angle correlation | 0.23 (fails) | **0.72** | 0.63 |
| ASPset test MPJPE (original domain) | 83.4 mm | **81.1 mm** (no loss) | – |

Values are means ± SD over 3 seeds; KERAAL values are measured only on participants never used in training.

**Five key findings**
1. **The problem was pose variety, not data volume.** Going from 3 to 13 ASPset training subjects left the KERAAL error unchanged. 89% of KERAAL poses are seated, against 13% in ASPset.
2. **The calibration-free KERAAL dataset can be calibrated post hoc.** Using the Kinect as a bridge, Vicon was moved into camera coordinates: 25 mm 3D residual and 6.2 px reprojection error on held-out recordings.
3. **Merged training cuts position error to about a third.** 222.9 → 69.5 mm, better in all 9 seed × participant runs.
4. **It beats the Kinect on angles too.** This angle metric is independent of the calibration. r0 is higher and RMSE lower than the Kinect in all 9 cells (participant × exercise), p = 0.004.
5. **The RTK failure came from missing data, not a single-camera limit.** After merging, r0 rose from 0.23 to 0.72, past the Kinect (0.63).

**Caveat:** only 3 test participants (healthy, acted errors), filmed in the same room with the same camera as the training data. Real patients and other locations are not yet tested (§7).

---

## 1. Background and questions

- **Goal:** turn single-camera 2D video into 3D motion-capture data, for use in rehab exercise assessment.
- **Earlier results (10/26–10/30):**
  - A model trained on ASPset-510 reached 49 mm PA-MPJPE within ASPset, on par with the paper's baselines.
  - On KERAAL, however, angle RMSE was 20°, similar to the Kinect, and it failed on the RTK exercise.
  - Training on 3/6/9/13 subjects left KERAAL performance unchanged.
- **Questions:**
  - Q1. Can KERAAL get 3D ground truth in the same format as ASPset? (camera calibration)
  - Q2. Does merged training help on new participants' rehab movements, and does it keep performance in the original domain (ASPset)?
  - Q3. Does it matter whether Vicon or the Kinect is used as ground truth?

## 2. Data

| | ASPset-510 | KERAAL Group 3 |
|---|---|---|
| Licence | CC0 | CC BY-NC-SA (no raw or derived files in public) |
| Setting | outdoor, standing full-body sports | indoor, 3 seated arm rehab exercises (CTK, ELK, RTK) |
| People | 17 (train 13 / val 2 / test 2) | 3 (healthy, acting errors), 540 recordings |
| Video | 4K 50 fps, 3 cameras | 960×540 30 fps, 1 camera (Kinect v2 colour) |
| 3D GT | markerless triangulation + bundle adjustment | Vicon optical markers at 60 fps, 17 rigid targets (position + quaternion) |
| Calibration | yes (§3.1) | **none → built by us (§3.2)** |
| Pose range (measured) | 13% seated | 89% seated; 62% of frames have no similar ASPset pose |

## 3. Camera calibration methods

### 3.1 ASPset: the authors' method (Nibali et al. 2021, §4)

1. **Capture:** 3 × Canon EOS C200, 24 mm lenses, 4K 50 fps, about 30° apart around the stage. Synchronised by hand on a light being switched off.
2. **Initial calibration:**
   - An **asymmetric circle-grid board** was moved around the stage with twists and tilts.
   - **OpenCV** detected the circles to give K per camera, stereo calibration gave E, and gradient descent then reduced the reprojection error of all three cameras at once.
   - **Lens distortion was assumed zero.**
   - Detections whose circle rows/columns were not straight (MSE > 0.05) were dropped, and only frames at least 50 px apart were kept (~100).
3. **Bundle adjustment:**
   - Camera parameters were optimised jointly with 2D joint detections (Stacked Hourglass fine-tuned on human annotations).
   - It used 5,000 frames with score U < 10 px, which tolerates a constant offset across joints.
4. **Coordinates:** world = first (left) camera; mm; x right · y down · z forward. Each subject has its own calibration.
5. **Limitation:** no GT accuracy in mm is reported.

### 3.2 KERAAL: our post-hoc calibration (`keraal_calib.py`)

With no calibration board, we used the **Kinect as a bridge**. The structure is the same as ASPset: an initial estimate, then refinement with correspondences.

```
Vicon targets ──② fixed offsets──▶ Vicon joint points ──③ R, t──▶ camera coords ──① K──▶ pixels
                                             ▲
                                  Kinect joints (camera coords)
```

**① Intrinsics K**
- Basis:
  - KERAAL video at 960×540 is exactly half of the Kinect v2 colour stream (1920×1080).
  - Kinect file rows match video frames 1:1.
  - Kinect joints are already stored in camera coordinates (m).
- Method:
  - A pinhole model. From 12 joint correspondences between Kinect joints and YOLO 2D (confidence > 0.5), we fitted fx, fy, cx, cy together with a colour–depth sensor offset t0.
  - soft-L1 robust least squares.
  - Kinect axes (x left, y up) were flipped to OpenCV axes (x right, y down).
- Result: **fx 502.3, fy 521.4, cx 476.0, cy 256.5, t0 = (4.8, −10.2, −19.6) cm**. Distortion assumed zero (same as ASPset).

**② Vicon targets → joint points**
- The 17 Vicon items are rigid targets on body segments, not joint centres. Matching them directly to the Kinect left about 12 cm of residual.
- So joint point = target position + target rotation × **fixed offset**, where the offset is a constant in the target's local frame.

**③ Vicon → camera rigid transform**
- Kinect joint ≈ R·(joint point) + t, with scale fixed in mm.
- R, t (Kabsch) and the offsets (closed-form median) were solved by **alternating least squares**, 30 iterations. Halfway through, frames with Kinect tracking failures (residual above 3× the median) were dropped once.
- Vicon was decimated from 60 to 30 fps, and a time lag of ±15 frames was searched per recording.
- **Session = participant × exercise.** With one session per participant, only P2 failed (111 mm); per exercise it gave 25–33 mm.
- Output: Vicon and Kinect joints per recording, **in ASPset `aspset_17j` order and camera mm**. head_top has no counterpart and is left empty.

**Calibration check (fitted on even-numbered recordings, checked on the 270 odd-numbered ones)**

| Check | Median |
|---|---|
| Vicon joint points ↔ Kinect joints (3D) | **25.0 mm** (P1 22, P2 29, P3 23) |
| Vicon projection ↔ YOLO 2D | **6.2 px** (5.9 px with the ASPset-style U score) |
| Kinect projection ↔ YOLO 2D | 6.8 px |
| Offset sizes | mostly 80–230 mm |
| Visual check | Vicon points sit on the body's joints in held-out frames |

## 4. Experiment design

| Item | Setting |
|---|---|
| Input | YOLO11x-pose 2D (COCO 17) + confidence, mid-hip + body-extent normalisation |
| Model | temporal conv net (VideoPose3D-style), 81-frame receptive field, output pelvis-relative 3D for 17 joints |
| Split | **leave-one-KERAAL-participant-out, 3 folds.** 1/5 of the training participants' recordings held out as KERAAL validation. The test participant is used only at the end |
| Model selection | epoch with the lowest (ASPset val + KERAAL val MPJPE) / 2 |
| Loss | per-joint masked MPJPE; joints without GT are left out |
| Conditions | ① ASPset only ② ASPset + KERAAL (Vicon GT) ③ ASPset + KERAAL (Kinect GT) ④ KERAAL only (Vicon GT, 457 epochs for the same number of updates) |
| Training | AdamW lr 1e-3, 120 epochs, left-right flip augmentation + flip TTA, **seeds 0, 1, 2** |
| Metrics | **Position:** MPJPE and PA-MPJPE against Vicon joint points (16 joints, no head_top). **Angles:** correlation r0 and RMSE against Vicon **quaternion** relative angles; the angle metric is independent of the calibration. **ASPset test:** checks the original domain is kept |
| Tests | Wilcoxon signed-rank over 9 test-participant × exercise cells (seed-averaged) |

## 5. Results

### 5.1 Main results (mean ± SD over 3 seeds, averaged over the 3 participant folds)

| Training data | KERAAL MPJPE | PA-MPJPE | Angle r0 | Angle RMSE (°) | RTK r0 | ASPset MPJPE / PA |
|---|---|---|---|---|---|---|
| ① ASPset only | 222.9 ± 3.0 | 102.9 ± 0.1 | 0.594 ± 0.017 | 20.3 ± 1.4 | 0.233 | 83.4 / 49.4 |
| ② **ASPset + KERAAL (Vicon)** | **69.5 ± 0.8** | **52.2 ± 0.2** | **0.764 ± 0.005** | **13.9 ± 0.3** | **0.724** | **81.1 / 48.5** |
| ③ ASPset + KERAAL (Kinect) | 77.7 ± 0.2 | 56.9 ± 0.2 | 0.712 ± 0.005 | 15.7 ± 0.4 | 0.616 | 81.9 / 48.8 |
| ④ KERAAL only (Vicon) | 68.4 ± 0.5 | 52.8 ± 0.5 | 0.746 ± 0.004 | 13.6 ± 0.1 | 0.739 | 315.4 / 212.1 |
| *Kinect sensor* | – | – | *0.670* | *18.7* | *0.634* | – |
| *Raw 2D angles* | – | – | *0.551* | *29.1* | – | – |

### 5.2 Per participant (seed-averaged)

| Training data | P1 MPJPE / r0 | P2 MPJPE / r0 | P3 MPJPE / r0 |
|---|---|---|---|
| ASPset only | 189.5 / 0.78 | 234.5 / 0.59 | 244.5 / 0.41 |
| ASPset + KERAAL (Vicon) | 82.4 / 0.88 | 70.2 / 0.72 | 55.9 / 0.69 |
| KERAAL only | 92.5 / 0.84 | 60.3 / 0.72 | 52.3 / 0.68 |

### 5.3 Position MPJPE per exercise (mm)

| Training data | CTK | ELK | RTK |
|---|---|---|---|
| ASPset only | 230.6 | 208.7 | 228.8 |
| ASPset + KERAAL (Vicon) | 70.3 | 61.1 | 77.5 |
| ASPset + KERAAL (Kinect) | 74.4 | 74.0 | 85.0 |
| KERAAL only | 70.7 | 58.3 | 76.3 |

### 5.4 Per-joint MPJPE (mm, ASPset only → ASPset + KERAAL Vicon)

| Joint | Before → after | Joint | Before → after |
|---|---|---|---|
| Ankle R / L | 431 → **58** / 434 → **65** | Wrist R / L | 298 → 147 / 287 → 150 |
| Knee R / L | 376 → **55** / 360 → **75** | Elbow R / L | 212 → 102 / 212 → 104 |
| Hip R / L | 83 → 12 / 83 → 11 | Shoulder R / L | 169 → 81 / 174 → 74 |
| Head / neck / spine | 154 → 70 / 170 → 67 / 120 → 44 | | |

### 5.5 Statistical tests (9 cells = participant × exercise, seed-averaged)

| Comparison | r0 diff, cells better, p | RMSE diff, cells better, p |
|---|---|---|
| ② vs ① ASPset only | +0.256, **9/9**, p = 0.004 | −6.1°, 8/9, p = 0.012 |
| ② vs Kinect | +0.103, **9/9**, p = 0.004 | −7.9°, **9/9**, p = 0.004 |
| ③ vs Kinect | +0.041, 6/9, p = 0.129 | −6.0°, 9/9, p = 0.004 |
| ④ vs Kinect | +0.088, 8/9, p = 0.020 | −8.1°, 9/9, p = 0.004 |
| ② Vicon GT vs ③ Kinect GT | +0.062, 7/9, p = 0.039 | −1.8°, 7/9, p = 0.055 |
| ② merged vs ④ KERAAL only | +0.015, 5/9, p = 0.43 | +0.3°, 2/9, p = 0.16 |

In all 9 seed × participant runs, ②, ③ and ④ had lower position error than ①.

## 6. Interpretation: why it worked

1. **It filled the missing poses.** The lower body improved most: ankle 431 → 58 mm, knee 376 → 55 mm. The ASPset-only model predicted seated legs as if standing, which matches the measured pose range (13% vs 89% seated).
2. **The RTK failure was a data problem.** r0 rose from 0.23 to 0.72. The earlier reading "rotation in depth = single-camera limit" was wrong.
3. **The GT format matched ASPset exactly.** The §3.2 calibration put KERAAL GT into the same frame (OpenCV axes, mm, pelvis-relative, same 17-joint order), so the data could be mixed without changing the model or the loss.
4. **Calibration error is below model error.** Calibration 25 mm vs model 69 mm, so GT noise did not spoil training.
5. **The two datasets protect each other.**
   - On KERAAL, ② and ④ are statistically the same (p = 0.43).
   - But ④ collapsed on ASPset (315 mm), while ② even improved on ASPset (83.4 → 81.1 mm).
   - So **one model for both domains needs the merge**. The paper's §6.2 (MPI-INF-3DHP + ASPset) shows the same effect.
6. **GT quality matters.** Vicon GT (②) beat Kinect GT (③) even on the calibration-independent angle r0 (p = 0.039), so §3.2 steps ②③ (moving Vicon into the camera frame) were worth doing.
7. **The results are stable.** Between-seed SD is 0.8 mm for MPJPE and 0.005 for r0, and all 9 seed × participant runs improved.

## 7. Limitations, failures, and why

1. **P2 failed in the first calibration (111 mm).**
   - P2's camera or Vicon frame apparently changed between exercises; per-exercise calibration fixed it.
   - Whether the camera actually moved is unchecked. P2 also has many Vicon dropouts (42 recordings over 20% missing).
2. **The ASPset-only position error (223 mm) includes a joint-definition mismatch.**
   - KERAAL GT follows the Kinect definition because the offsets were fitted to Kinect joints; ASPset follows anatomical annotation.
   - So part of the position gain is "learning the definition". The angle metric is definition-free and also improved a lot, so the conclusion holds.
3. **Wrist error is still large (~150 mm).** Wrist GT is a forearm-target offset fitted to the Kinect wrist, whose tracking is unstable. Functional joint centres (SCoRE) or the hand targets could fix this.
4. **A KERAAL-only model does not generalise.** Two people, indoors, three exercises — too narrow a pose range.
5. **The sample is small.** 3 test participants; the 9 cells are three exercises from the same person each, so they are not fully independent.
6. **Same room, same camera.** We showed generalisation to new people, not to new places or cameras.
7. **Only acted errors were tested.** Real patients (1A) may move differently.
8. **ASPset's own GT accuracy is unreported.** The paper gives no validation in mm.

## 8. Next steps

| Order | Task | Purpose |
|---|---|---|
| 1 | Apply the merged model to 1A (patients) and 2A (healthy) videos and compare angles with the Kinect | generalisation to real patients and other sessions (no Vicon → angles only) |
| 2 | Rebuild GT with functional joint centres | better wrists, no dependence on the Kinect definition |
| 3 | Rerun error detection (RQ4) with the merged model | link to the application goal |
| 4 | External check on OpenCap | different place and camera |
| 5 | Joint centres + IK → BVH | complete the "motion-capture data" goal |

## 9. Reproduce

```
python keraal_calib.py --check
python keraal_calib.py E:/KERAAL_data/extracted/group3 E:/KERAAL_mocap3d/det2d E:/KERAAL_mocap3d/calib
python merge_train.py --check
python merge_train.py <ASPset root> <ASPset det> <G3> <G3 det> E:/KERAAL_mocap3d/calib <run> --hold P1 --mode aspset_vicon --epochs 120 --seed 0
python merge_train.py ... <run> --hold P1 --seed 0 --eval-only E:/ASPset510_data/runs/det_root_s0   # ① ASPset only
python keraal_eval.py eval <G3> <G3 det> <run> <run>/angles.json
```

- Environment: `E:\mocap3d_env` (Python 3.12, PyTorch, ultralytics), RTX 3090.
- Results: `E:\KERAAL_mocap3d\merge\summary_3seeds.json`, per fold/seed `results.json` and `angles.json`.
- Calibration: `E:\KERAAL_mocap3d\calib\calib.json`.
- **Anything derived from KERAAL (GT, figures) is CC BY-NC-SA and must not go on GitHub.**
- Earlier records: [`RESULTS.md`](RESULTS.md) (baseline), [`MERGE_REPORT_EN.md`](MERGE_REPORT_EN.md) (single-seed first report).

## References

- Nibali, Millward, He, Morgan. ASPset: An outdoor sports pose video dataset with 3D keypoint annotations. *Image and Vision Computing* 111 (2021) 104196.
- Nguyen et al. KERAAL dataset. arXiv 2407.00521.
- Pavllo et al. 3D human pose estimation in video with temporal convolutions and semi-supervised training (VideoPose3D). CVPR 2019.
