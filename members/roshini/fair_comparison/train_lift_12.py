"""Task 4, fix 2 (fair comparison): train Sonny's 2D->3D lifter on ASPset-510 with ONLY the
12 joints that the true 2D (ASPset) and the detected 2D (YOLO / COCO) both have.

Why: in RQ2 the true-2D input used ASPset's 17 joints and the detected-2D input used COCO's 17
joints. They share only 12 (ankles, knees, hips, wrists, elbows, shoulders), so the "+8 mm"
difference mixed two things: 2D quality AND a different set of body points. Here both inputs use
the same 12 joints in the same order, so the only difference left is the 2D quality.
The model still predicts all 17 ASPset joints in 3D; only the INPUT shrinks from 17 to 12.

Usage (on the workstation with the GPU), the same arguments as train_lift.py:
    python train_lift_12.py <ASPset-510 root> <run dir> --input gt  --seed 0
    python train_lift_12.py <ASPset-510 root> <run dir> --input det --det-dir <det dir> --seed 0
    python train_lift_12.py --self-test     (checks the joint selection; no GPU, data or torch needed)
"""

import os   # works with file and folder paths
import sys  # reads the command-line arguments and tells Python where to find Sonny's code

import numpy as np  # numbers and arrays

# --- Find Sonny's code so we can reuse it (same as keraal_detect_crop.py) ---
HERE = os.path.dirname(os.path.abspath(__file__))
SONNY = os.path.join(HERE, "..", "..", "sonny", "mocap3d")
sys.path.insert(0, SONNY)

# --- The 12 shared joints, written in ASPset's order ---
# ASPset numbers 0-11 = right ankle, right knee, right hip, right wrist, right elbow, right shoulder,
#                       left ankle,  left knee,  left hip,  left wrist,  left elbow,  left shoulder
ASPSET_12 = list(range(12))                          # true 2D: ASPset joints 0..11
COCO_12 = [16, 14, 12, 10, 8, 6, 15, 13, 11, 9, 7, 5]  # detected 2D: the same body points in COCO
# (this is the same mapping Sonny's detect2d.py uses in its self-test)

# Left/right swap for the 12 joints (used when the training data is mirrored):
# position 0 (right ankle) <-> 6 (left ankle), 1 <-> 7, ... 5 <-> 11
FLIP_12 = [6, 7, 8, 9, 10, 11, 0, 1, 2, 3, 4, 5]


def keep_12(x2d, inp):
    """Keep only the 12 shared joints of one clip's 2D input, in ASPset order.

    x2d: (frames, 17, channels) 2D input from Sonny's load_split
         channels = x, y for true 2D; x, y, confidence for detected 2D
    inp: "gt" (true 2D, ASPset order) or "det" (detected 2D, COCO order)
    Returns (frames, 12, channels)
    """
    return x2d[:, ASPSET_12 if inp == "gt" else COCO_12]


def run():
    """Change three things in Sonny's train_lift.py, then run it exactly as before."""
    import train_lift as tl       # Sonny's training code (needs torch, so imported only here)
    import aspset                 # Sonny's ASPset helper (gives the 17-joint 3D flip)

    original_load = tl.load_split
    original_tcn = tl.TCN

    # 1) Loading: load the data as usual, then keep only the 12 shared joints of the 2D input
    def load_split_12(root, split, inp, det_dir, limit=None, norm="root"):
        seqs = original_load(root, split, inp, det_dir, limit, norm)
        for q in seqs:
            q["x2d"] = np.ascontiguousarray(keep_12(q["x2d"], inp))
        return seqs

    # 2) Mirroring (data augmentation and test-time flip): the 2D input now has 12 joints,
    #    so it needs the 12-joint left/right swap; the 3D target still has 17 joints
    def flip_12(x2d, y3d, inp):
        x2d, y3d = x2d.copy(), y3d.copy()
        x2d[..., 0] *= -1            # mirror left-right: x becomes -x
        y3d[..., 0] *= -1
        return x2d[:, FLIP_12], y3d[:, aspset.FLIP]

    # 3) Model: Sonny's main() builds TCN(17, ...); make the first layer expect 12 joints instead
    def tcn_12(in_joints, in_ch, **kw):
        return original_tcn(12, in_ch, **kw)

    tl.load_split, tl.flip, tl.TCN = load_split_12, flip_12, tcn_12
    tl.main()                      # Sonny's training, evaluation and saving, unchanged


def self_test():
    """Check the joint selection with fake data (no GPU, no data, no torch needed)."""
    # fake detected 2D: COCO joint k has x = k, so we can see which joints were kept
    det = np.zeros((5, 17, 3))
    det[..., 0] = np.arange(17)
    assert keep_12(det, "det")[0, :, 0].tolist() == COCO_12
    # fake true 2D: ASPset joint k has x = k
    gt = np.zeros((5, 17, 2))
    gt[..., 0] = np.arange(17)
    assert keep_12(gt, "gt")[0, :, 0].tolist() == ASPSET_12
    # both inputs now have 12 joints, so the model sees the same body points
    assert keep_12(det, "det").shape[1] == keep_12(gt, "gt").shape[1] == 12
    # the 12-joint flip swaps right and left, and doing it twice gives back the original
    assert [FLIP_12[i] for i in FLIP_12] == list(range(12))
    print("train_lift_12 --self-test OK")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        self_test()
    else:
        run()                       # passes all arguments straight to Sonny's train_lift.py
