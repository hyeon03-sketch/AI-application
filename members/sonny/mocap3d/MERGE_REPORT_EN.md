# Experiment report: training on ASPset-510 + KERAAL G3 combined

2026-10-30 · Sonny · status: **exploratory**, single seed · 한국어: [`MERGE_REPORT_KR.md`](MERGE_REPORT_KR.md)

## 0. Summary

**The experiment worked.** A model trained on ASPset alone had a 220 mm joint-position error on rehab video (KERAAL). Training on ASPset plus two KERAAL participants cut this to **69 mm** on the third participant, who was never used in training. A calibration-independent angle metric also improved, and the model **beat the Kinect sensor in all 9 cells**. ASPset performance did not drop; it improved slightly.

| Training data | KERAAL position MPJPE (mm) | KERAAL angle r0 / RMSE (°) | RTK r0 | ASPset test MPJPE / PA (mm) |
|---|---|---|---|---|
| ASPset only (previous) | 220.0 | 0.59 / 20.0 | 0.24 | 84.8 / 49.8 |
| **ASPset + KERAAL (Vicon GT)** | **69.0** | **0.77 / 13.9** | **0.73** | **79.8 / 48.1** |
| ASPset + KERAAL (Kinect GT) | 77.5 | 0.71 / 16.0 | 0.63 | 81.7 / 48.6 |
| KERAAL only (Vicon GT) | 68.9 | 0.75 / 13.6 | 0.74 | 308.2 / 193.1 |
| *Reference: Kinect sensor* | – | *0.67 / 18.7* | *0.63* | – |

- Values are the mean over 3 leave-one-participant-out folds.
- KERAAL metrics are measured only on the held-out participant.
- What made this possible is the **KERAAL camera calibration**. Section 2 describes the method in detail.

---

## 1. Why we ran this

- With ASPset alone, the KERAAL angle error stayed near 20°. It did not change as training subjects went from 3 to 13 (learning curve, 10/30).
- Pose coverage showed why. 89% of KERAAL poses are seated, against 13% in ASPset, and 62% of KERAAL frames have no similar pose in ASPset.
- So we expected the fix to be **adding rehab poses to training, not adding more ASPset**, and merged the two datasets.
- Training on KERAAL needs 3D ground truth in the same format as ASPset: **camera coordinates, mm, pelvis-relative, the same 17-joint definition**. KERAAL has no camera calibration, so we built one first.

---

## 2. Camera calibration: which methods were used

### 2.1 How the ASPset authors did it (from the paper: Nibali et al. 2021, §4)

| Step | Method |
|---|---|
| Capture | 3 × Canon EOS C200, 24 mm lenses, 4K 50 fps, about 30° apart around the stage |
| Sync | Software. Aligned by hand on a light being switched off in view of all three cameras |
| Initial calibration | An **asymmetric circle-grid board** was moved around the stage with twists and tilts. **OpenCV** circle detection → K per camera → stereo calibration for E → gradient descent minimising reprojection error across all three cameras at once. **Lens distortion assumed zero.** Bad detections dropped by row/column collinearity (MSE 0.05); only frames differing by at least 50 px were kept (~100 per sequence) |
| Refinement | **Bundle adjustment**: camera parameters and 2D joint detections (Stacked Hourglass fine-tuned on human annotations) optimised jointly, on 5,000 frames with unbiased reprojection score U < 10 px, which tolerates a constant offset across joints |
| Coordinates | World = first (left) camera, mm, x right · y down · z forward. One calibration per subject (session) |
| Limitation | No GT accuracy in mm is reported |

### 2.2 What we did for KERAAL (`keraal_calib.py`)

With no calibration board, we used **post-hoc calibration with the Kinect as a bridge**. The structure is the same as ASPset: an initial estimate, then refinement with 2D joints.

```
Vicon targets (pos + quat) ──② offsets──▶ Vicon joint points ──③ R,t──▶ camera coords ──① K──▶ pixels
                                                    ▲
                                       Kinect joints (camera coords)
```

**① Intrinsics K: Kinect joints ↔ 2D detections in the video**
- Basis: KERAAL video (960×540) is exactly half the Kinect v2 colour resolution (1920×1080), and Kinect file rows match video frames 1:1. Kinect joints are already in camera space (m).
- Method: pinhole model `u = fx·X/Z + cx`. From 12 joint correspondences between Kinect joints and YOLO 2D (confidence > 0.5), we fitted fx, fy, cx, cy together with a **colour–depth sensor offset t0**. Robust least squares (soft-L1), every 5th frame of the 270 calibration recordings.
- Axes: Kinect (x left, y up) → OpenCV (x right, y down) by negating x and y.
- Result: **fx 502.3, fy 521.4, cx 476.0, cy 256.5, t0 = (4.8, −10.2, −19.6) cm**. Lens distortion assumed zero, as in ASPset.

**② Vicon targets → joint points: a fixed offset per target**
- Problem: the 17 Vicon items are **rigid targets** on body segments, not joint centres. Matching targets directly to Kinect joints left about 12 cm of residual.
- Model: joint point = target position + target rotation (quaternion) × **fixed offset o_j**, i.e. one constant for where the joint sits in each target's local frame.
- The quaternion convention (as given or conjugated) is chosen by residual. It came out "as given" in every session.

**③ Vicon → camera: one rigid R, t per session**
- Model: Kinect joint (camera mm) ≈ R·(joint point) + t, with scale fixed (mm).
- Solver: **alternating least squares** between R, t (Kabsch) and the offsets o_j (closed form, median), for 30 iterations. Halfway through, frames with residual above 3× the median (Kinect tracking failures) were dropped once.
- Timing: Vicon (60 fps) decimated to 30 fps; a lag of ±15 frames searched per recording.
- **Session = participant × exercise.** We first used one session per participant. Only P2 failed (111 mm residual); split by exercise it gave 25–33 mm (§4.1). The camera or the Vicon frame apparently changed between exercises.
- Output: Vicon and Kinect joints for every recording, **in ASPset `aspset_17j` order and camera mm** (`E:\KERAAL_mocap3d\calib\gt3d\`). head_top has no counterpart and is NaN.

**Validation: fitted on even-numbered recordings, checked on the 270 odd-numbered ones**

| Check | Result (median) |
|---|---|
| 3D distance, Vicon joint points ↔ Kinect joints | **25.0 mm** (down from 12 cm). Per participant P1 22, P2 29, P3 23 |
| Vicon projection ↔ YOLO 2D | **6.2 px** (5.9 px with the ASPset-style U, which tolerates a constant offset) |
| Kinect projection ↔ YOLO 2D | 6.8 px |
| Offset sizes | mostly 80–230 mm (plausible distances from target to joint) |
| Visual check | On held-out frames, projected Vicon points sit on the body's joints (`E:\KERAAL_mocap3d\calib\overlay_check.png`, never publish) |

> **Note:** each offset is set to "the position that best matches the Kinect joint". So KERAAL's 3D GT **follows the Kinect joint definition**, not a pure anatomical joint centre. §6 item 5 covers the effect on evaluation.

---

## 3. Merge experiment design

| Item | Setting |
|---|---|
| Input | YOLO11x-pose 2D (COCO 17) + confidence, mid-hip + body-extent normalisation (unchanged) |
| Model | temporal conv net (VideoPose3D-style), 81-frame receptive field, output `aspset_17j` pelvis-relative 3D |
| Split | **leave-one-participant-out, 3 folds.** One in five recordings of the two training participants held out as KERAAL validation. The test participant is never touched before the final evaluation |
| Model selection | epoch with the lowest (ASPset val MPJPE + KERAAL val MPJPE) / 2 |
| Loss | per-joint masked MPJPE. KERAAL head_top and missing Vicon are left out of the loss |
| Conditions | ① ASPset only (re-evaluated existing det/root seed 0 model) ② ASPset + KERAAL (Vicon GT) ③ ASPset + KERAAL (Kinect GT, possible without calibration steps ②③) ④ KERAAL only (Vicon GT, 457 epochs for the same number of updates) |
| Training | AdamW lr 1e-3, 120 epochs, left-right flip augmentation + flip TTA, seed 0 |
| Data volume | KERAAL training ~288 recordings (~64k frames); ASPset training 1,170 views (243k frames) |
| Metrics | **Position**: MPJPE and PA-MPJPE against Vicon joint points (16 joints, no head_top) · **Angles**: existing `keraal_eval.py`, correlation r0 and RMSE against Vicon **quaternion** relative angles; **independent of the calibration** · ASPset test |
| Tests | Wilcoxon signed-rank over 9 test-participant × exercise cells |

---

## 4. Results

### 4.1 Calibration

- One R, t per participant: P1 25 mm and P3 30 mm, but **P2 failed at 111 mm**.
- Diagnosing P2: fitted per exercise it gave CTK 25, ELK 34, RTK 28 mm. Swapping left/right or the quaternion convention made it worse (57–266 mm). So **sessions became participant × exercise**.
- Final held-out result: 3D 25.0 mm, reprojection 6.2 px.

### 4.2 KERAAL held-out participant: position (vs Vicon joint points, mm)

| Training data | P1 | P2 | P3 | Mean MPJPE | Mean PA-MPJPE | CTK | ELK | RTK |
|---|---|---|---|---|---|---|---|---|
| ASPset only | 189.9 | 229.3 | 240.8 | 220.0 | 102.9 | 223.4 | 205.2 | 231.4 |
| ASPset + KERAAL (Vicon) | 82.5 | 69.0 | 55.5 | **69.0** | **52.1** | 69.3 | 60.8 | 77.3 |
| ASPset + KERAAL (Kinect) | 86.3 | 78.7 | 67.6 | 77.5 | 57.0 | 73.6 | 74.2 | 85.3 |
| KERAAL only (Vicon) | 93.3 | 60.6 | 52.8 | 68.9 | 53.4 | 71.3 | 58.1 | 77.7 |

Per-joint MPJPE (mean over 3 folds, ASPset only → ASPset + KERAAL Vicon):

| Joint | Before | After | | Joint | Before | After |
|---|---|---|---|---|---|---|
| Ankle R/L | 430 / 429 | **56 / 65** | | Wrist R/L | 297 / 288 | 146 / 149 |
| Knee R/L | 376 / 359 | **54 / 75** | | Elbow R/L | 209 / 209 | 101 / 104 |
| Hip R/L | 82 / 82 | 12 / 11 | | Shoulder R/L | 161 / 166 | 81 / 74 |
| Head / neck / spine | 143 / 163 / 125 | 70 / 67 / 44 | | | | |

### 4.3 KERAAL held-out participant: angles (vs Vicon quaternions, calibration-independent)

| Training data | r0 (P1/P2/P3) | Mean r0 | Mean RMSE (°) | RTK r0 |
|---|---|---|---|---|
| ASPset only | 0.76 / 0.59 / 0.43 | 0.59 | 20.0 | 0.24 |
| ASPset + KERAAL (Vicon) | 0.89 / 0.72 / 0.70 | **0.77** | **13.9** | **0.73** |
| ASPset + KERAAL (Kinect) | 0.83 / 0.67 / 0.63 | 0.71 | 16.0 | 0.63 |
| KERAAL only (Vicon) | 0.83 / 0.72 / 0.68 | 0.75 | 13.6 | 0.74 |
| *Kinect sensor* | | *0.67* | *18.7* | *0.63* |
| *Raw 2D angles* | | *0.55* | *29.1* | |

Tests over 9 cells (participant × exercise):

| Comparison | r0 | RMSE |
|---|---|---|
| ASPset + KERAAL (Vicon) vs ASPset only | +0.26, 8/9 better, p = 0.008 | −5.7°, 8/9, p = 0.008 |
| ASPset + KERAAL (Vicon) vs **Kinect** | +0.11, **9/9**, p = 0.004 | −7.9°, **9/9**, p = 0.004 |
| ASPset + KERAAL (Kinect) vs Kinect | +0.04, 6/9, p = 0.055 | −5.6°, 8/9, p = 0.012 |
| KERAAL only vs Kinect | +0.09, 8/9, p = 0.020 | −8.2°, 9/9, p = 0.004 |

### 4.4 ASPset test (what happens to the original domain)

| Training data | MPJPE | PA-MPJPE |
|---|---|---|
| ASPset only | 84.8 | 49.8 |
| ASPset + KERAAL (Vicon) | **79.8** | **48.1** |
| ASPset + KERAAL (Kinect) | 81.7 | 48.6 |
| KERAAL only | 308.2 | 193.1 |

---

## 5. Why it worked

1. **It filled the missing poses.** ASPset has only 13% seated poses. Adding KERAAL helped the lower body most: ankle 430 → 56 mm, knee 376 → 54 mm. The ASPset-only model apparently straightened seated legs into standing poses.
2. **The RTK failure is gone.** The trunk-rotation exercise went from r0 0.24 to 0.73, past the Kinect (0.63). So the failure came from **missing training data, not from a basic single-camera limit**. Our earlier reading ("rotation in depth = single-camera limit") must be corrected.
3. **The GT format matched ASPset exactly.** The §2 calibration put KERAAL GT into the same camera frame (OpenCV axes, mm, pelvis-relative, same 17-joint order). That let us mix the data without changing the model or the loss.
4. **The calibration was accurate enough.** Held-out 3D residual is 25 mm and reprojection is 6 px, well below our model error (69 mm), so GT noise did not spoil training.
5. **The two datasets complement each other.** KERAAL alone matched the merged model on KERAAL but collapsed on ASPset (308 mm). Merged training was good on both, and ASPset itself improved (85 → 80 mm), probably because seeing another camera and other people helps generalisation. The paper (§6.2) saw the same effect when mixing MPI-INF-3DHP with ASPset, which improved even indoor results.
6. **Vicon GT beats Kinect GT.** The Kinect-GT model also improved, but the Vicon-GT model led on every metric, including the calibration-independent angle r0 (0.77 vs 0.71). Cleaner GT makes a real difference, so §2 steps ②③ (moving Vicon into the camera frame) were worth doing.
7. **It generalises across participants.** On participants never used in training, it beat the Kinect in all 9 cells. It did not just memorise the same people.

---

## 6. What failed or remains, and why

1. **P2 failed in the first calibration (111 mm).**
   - Why: P2's camera or Vicon frame apparently changed between exercises. Per-exercise fitting gives 25–33 mm.
   - Not yet checked: whether the camera actually moved (compare video backgrounds), and whether this relates to P2's unusually high Vicon missing rate (42 recordings over 20% missing).
2. **The ASPset-only model had a very large KERAAL position error (220 mm).**
   - Reason 1: seated leg poses were absent from training (§5 item 1).
   - Reason 2: joint definitions differ. KERAAL GT follows the Kinect definition; ASPset follows human-annotated anatomical landmarks. So part of the 220 mm is **definition mismatch**, not pose error, and the merged models gain by learning the KERAAL definition. The angle metric (§4.3) separates this out, and it improved a lot too, so the conclusion holds.
3. **The KERAAL-only model collapsed on ASPset (308 mm).**
   - Why: two participants, indoors, three seated arm exercises — far too narrow a pose range. KERAAL alone cannot make a general model.
4. **Wrist error is still large (~147 mm).**
   - Why: wrist GT is the Vicon forearm target plus an offset. The offset is fitted to the Kinect wrist, and Kinect wrist tracking is unstable.
   - Fix: also use the hand target, or the functional joint centre (SCoRE) of the two targets.
5. **GT follows the Kinect joint definition.**
   - Why: the offsets were fitted to Kinect joints.
   - Effect: the position metric favours "predicting like a Kinect". The angle metric comes from Vicon quaternions and is unaffected.
   - Fix: switch to Kinect-free functional joint centres and re-check.
6. **Statistical power is weak.**
   - 3 participants, 1 seed. The 9-cell tests give p < 0.01, but the cells are not independent (three exercises from the same person).
   - Fix: 3 seeds (~3 h), and an external check on other groups' videos (1A patients, 2A healthy). Those groups have Kinect but no Vicon, so only angles can be compared.
7. **KERAAL training and test data share the same room and camera.**
   - Why: G3 was recorded in one place.
   - Effect: we showed generalisation to new people, not to new places or cameras. External data such as OpenCap is needed.
8. **Only acted errors (G3) were tested.**
   - Whether this holds for real patient movement (1A) is unknown.

---

## 7. What it means for the research

- **Candidate paper claim:** "Sports 3D data lacks rehab poses (13% vs 89% seated coverage; more of it does not help). Calibrating a calibration-free rehab dataset post hoc through its Kinect and mixing it in lets single-camera video beat the Kinect on joint angles for unseen participants (9/9 cells)."
- **Changed interpretation:** the RTK failure was missing data, not a single-camera limit. Finding 5 in `RESULTS.md` needs correcting.
- **Next steps:**
  1. Rerun with 3 seeds.
  2. Improve wrist GT (functional joint centres).
  3. Apply to 1A/2A videos and compare angles with the Kinect (after check E2).
  4. Rerun error detection (RQ4) with the merged model.
  5. External check on OpenCap.

## 8. Reproduce

```
python keraal_calib.py --check
python keraal_calib.py E:/KERAAL_data/extracted/group3 E:/KERAAL_mocap3d/det2d E:/KERAAL_mocap3d/calib
python merge_train.py --check
python merge_train.py <ASPset root> <ASPset det> <G3> <G3 det> E:/KERAAL_mocap3d/calib <run> --hold P1 --mode aspset_vicon --epochs 120 --seed 0
python merge_train.py ... <run> --hold P1 --eval-only E:/ASPset510_data/runs/det_root_s0     # ASPset-only baseline
python keraal_eval.py eval <G3> <G3 det> <run> <run>/angles.json
```

- Results: `E:\KERAAL_mocap3d\merge\` (`summary.json`, `angles_heldout.json`, per-fold `results.json`)
- Calibration: `E:\KERAAL_mocap3d\calib\calib.json`
- **Anything derived from KERAAL (GT, overlay images) is CC BY-NC-SA and must not go on GitHub.**
