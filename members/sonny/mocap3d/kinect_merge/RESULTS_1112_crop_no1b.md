# Two checks on the final model (2026-11-12)

Asked by Roshini. Final model = ASPset + KERAAL G3 (Vicon) + Kinect groups (2A, 2B, 1B) + REHAB24-6 (`km_train.py --flag --kweight`).
Both checks use seed 0 only. Only summary numbers are here: KERAAL is CC BY-NC-SA, so data, weights and per-recording outputs stay on Sonny's workstation.

## 1. Crop detection for the G3 2D input (PR #11, `keraal_detect_crop.py`)

Same data and settings; only the G3 2D files change (`--g3-det`). Each row tests on a participant the model never trained on.

| Test participant | Position error (mm), whole-frame → crop | Angle RMSE (°), whole-frame → crop | Angle correlation, whole-frame → crop |
|---|---|---|---|
| P1 | 62.8 → 63.1 | 15.2 → 15.3 | 0.84 → 0.86 |
| P2 | 62.6 → 62.9 | 12.4 → 13.0 | 0.74 → 0.73 |
| P3 | 53.1 → 51.5 | 13.1 → 12.2 | 0.68 → 0.72 |
| Mean | 59.5 → 59.2 | 13.6 → 13.5 | 0.76 → 0.77 |

**No real difference.** The gap (0.3 mm, 0.1°) is as large as the change from another seed (3-seed spread: ±0.3 mm, ±0.1°).
With the ASPset-only model (11/6) crop detection did lower angle RMSE in all 3 seeds (20.2 / 19.3 / 21.7° → 19.2 / 18.8 / 21.0°).
Decision proposed: keep the current 2D files for the final model.

## 2. Final model without 1B, tested on the 1A patients

Reason: 1A patients are probably among the 1B recordings (`overlap_1a_1b.py`: 102 of 150 training 1B recordings fit a 1A patient by body size).
1A has no Vicon, so the numbers are the median difference from Kinect over 1A recordings. Kinect is weak on arms; the leg numbers carry the weight.

| Model (trained on P1+P2+P3) | All joints (mm) | Legs (mm) | Hip angle (°) | Knee angle (°) |
|---|---|---|---|---|
| Final, with 1B | 61.3 | 42.6 | 4.5 | 5.1 |
| Final, without 1B | 74.1 | 65.0 | 7.7 | 7.3 |
| For reference (11/5): no Kinect groups | 124.4 | 101.3 | 6.4 | 15.1 |
| For reference (11/5): ASPset only | 209.3 | 266.6 | 51.3 | 43.9 |

Legs per patient, with → without 1B (mm): R1 40.6 → 49.7, R2 52.5 → 56.9, R3 64.0 → 80.5, R4 32.0 → 39.0, R5 34.8 → 78.1, R6 45.5 → 72.8.

- 1B helps the 1A numbers a lot; all 6 patients get worse without it.
- This run cannot say why. 1B gives two things at once: probably the same patients, and the only training videos from the hospital rooms.
- If 1A is called "unseen patients", the number to report is 74 mm (legs 65 mm), not 61 mm.
- Not done: G3 leave-one-participant-out for the no-1B model; removing only the 102 matched recordings (would separate the two reasons).

## Commands

```
# 1. one fold (repeat for P1,P3 -> P2 and P2,P3 -> P1)
python km_train.py <out>/run_P1P2_P3_s0 --train-parts P1,P2 --eval-parts P3 --seed 0 --flag --kweight \
  --kinect group2A,group2B,group1B --rehab24 <rehab24_det.npz> --g3-det <crop detection folder>
# 2. train without 1B, then compare on 1A
python km_train.py <out>/run_P1P2P3_s0 --train-parts P1,P2,P3 --eval-parts "" --flag --kweight \
  --kinect group2A,group2B --rehab24 <rehab24_det.npz>
python eval_1a.py <out>/eval_1a.json with_1b=<final best.pt>@flag no_1b=<new best.pt>@flag
```

## Files on Sonny's workstation (team-internal, not on GitHub)

| What | Path |
|---|---|
| Crop detections, G3 (540 files) | `E:\KERAAL_mocap3d\det2d_crop` |
| Crop runs: results per fold | `E:\KERAAL_mocap3d\km\kin_w_r24_crop\<fold>_s0\results.json` |
| Crop runs: weights and logs | `E:\KERAAL_mocap3d\km\kin_w_r24_crop\run_<fold>_s0\best.pt`, `<fold>_s0.log` |
| Baseline (whole-frame), 3 seeds | `E:\KERAAL_mocap3d\km\kin_w_r24` |
| No-1B model: weights | `E:\KERAAL_mocap3d\km\final_r24_no1b\run_P1P2P3_s0\best.pt` |
| No-1B model: 1A comparison | `E:\KERAAL_mocap3d\km\final_r24_no1b\eval_1a.json` |
| Final model with 1B: weights | `E:\KERAAL_mocap3d\km\final_r24\run_P1P2P3_s0\best.pt` |
