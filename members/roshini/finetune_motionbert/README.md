# MotionBERT fine-tuning (Stage 1, public data)

Fine-tunes MotionBERT (DSTformer, 42.5M parameters) on ASPset-510 + REHAB24-6 and evaluates it before and after
fine-tuning with the team's `compute_metrics.py` and `vidimu_eval.py`.

## Files

| File | What it is |
|---|---|
| `download.sh` | Downloads MotionBERT, its pretrained weights and the public data bundle |
| `mb_common.py` | Shared parts: model loading, crop scaling, 243-frame clips, loss, whole-recording prediction |
| `finetune.py` | Fine-tuning; data paths and the dataset list are arguments |
| `infer.py` | `--in kp2d.npz --out pred3d.npz` -> (T, 17, 3), mm, H36M order, same T as the input |
| `evaluate.py` | Before / after: runs `infer.py`, `compute_metrics.py` and `vidimu_eval.py`, prints the section 6 table |
| `motionbert_finetune.ipynb` | The Colab notebook that produced the results below, with its outputs |
| `metrics_pos_*.json`, `vidimu_metrics_*.json` | Results from `compute_metrics.py` and `vidimu_eval.py`, before and after |

The fine-tuned weights (`best.pt`, ~170 MB) are on the team Google Drive, not on GitHub.

## Training note

1. Start: official "3D Pose, H36M-SH, finetuned" weights (`FT_MB_release_MB_ft_h36m/best_epoch.bin`), all layers trained.
2. Data: `aspset:train` + `rehab24:train` (4534 clips), epoch picked on `aspset:val` + `rehab24:val` (842 clips); VIDIMU never used for training or picking.
3. Input: `*_kp2d_h36m.npz` (x, y, confidence), **crop scaling** (one square box around all 2D joints of a recording, to [-1, 1]); 243-frame clips every 81 frames; targets in metres (gt3d / 1000), predictions saved in mm.
4. Settings: AdamW, lr 5e-5, weight decay 0.01, lr x0.99 per epoch, 20 epochs, seed 0, batch 4 x 8 gradient accumulation (32 clips per update), fp16; loss from `MB_ft_h36m.yaml` (MPJPE + 0.5 scale-aligned MPJPE + 20 velocity), padded frames masked.
5. Best epoch 15 (val MPJPE 212.6 mm before -> 70.5 mm); 20 epochs x 12.8 min = 4.26 GPU hours on a Colab Tesla T4.

Why crop scaling: with screen scaling (`x/w*2-1`) the person is very small in the 4K ASPset frames and the pretrained
model gave ~226 mm PA-MPJPE. The team agreed on crop scaling for all datasets; on KERAAL G3 crop and whole-frame gave
the same result (PR #14).

## Results (ASPset test, 60 recordings; VIDIMU, 205 recordings)

| Metric | Before | After | Mocap3D (`ours/`) |
|---|---|---|---|
| ASPset MPJPE (mm) | 179.29 | **73.51** | 79.5 |
| ASPset PA-MPJPE (mm) | 72.12 | **42.92** | 49.1 |
| VIDIMU r, no walking (A04–A13) | 0.90 | **0.93** | 0.91 |
| VIDIMU mean-removed RMSE (°), no walking | 11.01 | **7.58** | 8.84 |
| VIDIMU r, all (A01–A13) | 0.87 | **0.90** | 0.87 |
| VIDIMU mean-removed RMSE (°), all | 9.94 | **8.17** | 10.19 |
| ROM diff (°), no walking | -6.32 | -6.30 | |
| Repetition count same (%), no walking | 66.2 | 71.9 | |
| Walking L–R knee r (IMU -0.30) | 0.06 | -0.15 | +0.86 |
| Parameters (M) | 42.5 | 42.5 | 12.9 |
| Training GPU hours | – | 4.26 (T4) | |

MPJPE / PA-MPJPE = `position.summary.*.mean`; VIDIMU values are medians from `vidimu_eval.py`.

## How to run

```bash
bash download.sh                                   # MotionBERT + weights + Mocap3D_preprocessed_1118
pip install numpy scipy "scikit-learn>=1.4" timm easydict

# fine-tune (writes best.pt, last.pt, history.json to --out after every epoch; rerun to continue)
python finetune.py --mb MotionBERT --data Mocap3D_preprocessed_1118 --out runs/seed0 \
    --train aspset:train rehab24:train --val aspset:val rehab24:val --epochs 20 --seed 0

# predict any 2D file (leave out --ckpt for the pretrained model)
python infer.py --in Mocap3D_preprocessed_1118/aspset_kp2d_h36m.npz --out aspset_pred3d.npz \
    --mb MotionBERT --ckpt runs/seed0/best.pt --ids aspset:test

# before / after table with the team scripts
python evaluate.py --mb MotionBERT --data Mocap3D_preprocessed_1118 --ckpt runs/seed0/best.pt --out runs/seed0/eval
```

`--train` / `--val` take `dataset:split` items: the files `<dataset>_kp2d_h36m.npz` and `<dataset>_gt3d.npz` in
`--data`, with the ids from `splits.json[dataset][split]`.

## Stage 2 (KERAAL) notes

- Add KERAAL with `--train ... --val ...` items. If a KERAAL split is nested (e.g. `folds/test_P1/train`),
  `build()` in `mb_common.py` reads `sp[dataset][split]` and needs a small change.
- NaN targets (KERAAL Vicon) are already masked per joint in the loss and in the val MPJPE. The Kinect per-joint
  weights (`kinect_joint_loss_weight_h36m`) are not applied yet.
- The scripts are the notebook's code moved into files; the notebook is the version that produced the numbers above.
