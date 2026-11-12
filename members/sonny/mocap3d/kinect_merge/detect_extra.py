"""2D detection (YOLO11x-pose, overlay removed) for the KERAAL groups without Vicon: 2A, 2B and a seeded subset of 1B.
Reuses patients_1a/g1a.py (same mask, person choice, imgsz). Output E:/KERAAL_mocap3d/g1a/det_clean_<group>/<key>.npz.
Usage: python detect_extra.py group2A group2B group1B:400 [group1B:400:rev in a second process]"""
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "patients_1a"))
import g1a

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        group, _, n = arg.partition(":")
        n, _, rev = n.partition(":")       # group1B:150:rev walks the same subset backwards, for a second process
        vids = sorted(glob.glob(f"{g1a.ROOT}/{group}/videos/*.mp4") + glob.glob(f"{g1a.ROOT}/{group}/videos/*.avi"))
        if n:  # shortcut: subset of 1B for time (1631 recordings ~ 6 h); upgrade by raising n
            vids = sorted(np.random.default_rng(0).choice(vids, int(n), replace=False))
        g1a.videos = lambda _g, v=(vids[::-1] if rev else vids): v
        print(group, len(vids), flush=True)
        g1a.detect("clean", group)
