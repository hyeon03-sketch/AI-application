"""Before / after evaluation with the team's scripts: ASPset test (compute_metrics.py) and VIDIMU (vidimu_eval.py).

  python evaluate.py --mb MotionBERT --data Mocap3D_preprocessed_1118 --ckpt runs/seed0/best.pt --out runs/seed0/eval
Prints the section 6 table and writes the predictions and json results to --out."""
import argparse
import json
import os
import subprocess
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--mb", required=True); ap.add_argument("--data", required=True)
ap.add_argument("--ckpt", required=True); ap.add_argument("--out", required=True)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
here = os.path.dirname(os.path.abspath(__file__))
D = lambda f: os.path.join(a.data, f)


def run(cmd):
    subprocess.run([sys.executable] + cmd, check=True)


res = {}
for tag, ckpt in (("before", None), ("after", a.ckpt)):
    O = lambda f: os.path.join(a.out, f"{f}_{tag}")
    extra = ["--ckpt", ckpt] if ckpt else []
    run([os.path.join(here, "infer.py"), "--in", D("aspset_kp2d_h36m.npz"), "--out", O("aspset_pred3d") + ".npz",
         "--mb", a.mb, "--ids", "aspset:test"] + extra)
    run([os.path.join(here, "infer.py"), "--in", D("vidimu_kp2d_h36m.npz"), "--out", O("vidimu_pred3d") + ".npz",
         "--mb", a.mb] + extra)
    run([D("compute_metrics.py"), "--pred", O("aspset_pred3d") + ".npz", "--gt", D("aspset_gt3d.npz"),
         "--out", O("metrics_pos") + ".json"])
    run([D("vidimu_eval.py"), "--pred", O("vidimu_pred3d") + ".npz", "--imu", D("vidimu_imu_angles.npz"),
         "--out", O("vidimu_metrics") + ".json"])
    res[tag] = (json.load(open(O("metrics_pos") + ".json")), json.load(open(O("vidimu_metrics") + ".json")))

rows = [("ASPset MPJPE (mm)", lambda p, v: p["position"]["summary"]["mpjpe_mm"]["mean"]),
        ("ASPset PA-MPJPE (mm)", lambda p, v: p["position"]["summary"]["pa_mpjpe_mm"]["mean"]),
        ("VIDIMU r, no walking", lambda p, v: v["no_walking_A04_A13"]["r"]),
        ("VIDIMU mean-removed RMSE (deg), no walking", lambda p, v: v["no_walking_A04_A13"]["mean_removed_rmse_deg"]),
        ("VIDIMU r, all", lambda p, v: v["all_A01_A13"]["r"]),
        ("VIDIMU mean-removed RMSE (deg), all", lambda p, v: v["all_A01_A13"]["mean_removed_rmse_deg"]),
        ("ROM diff (deg), no walking", lambda p, v: v["no_walking_A04_A13"]["rom_diff_deg"]),
        ("Rep count same (%), no walking", lambda p, v: v["no_walking_A04_A13"]["reps_same_pct"]),
        ("Walking L-R knee r (IMU -0.30)", lambda p, v: v["walking_left_right_knee_r"]["model"])]
table = {name: {t: get(*res[t]) for t in res} for name, get in rows}
json.dump(table, open(os.path.join(a.out, "summary_table.json"), "w"), indent=1)
print(f"\n{'metric':45s}{'before':>10s}{'after':>10s}")
for name, v in table.items():
    print(f"{name:45s}{v['before']:10.2f}{v['after']:10.2f}")
