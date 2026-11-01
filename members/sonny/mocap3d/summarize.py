"""Aggregate all runs into markdown tables (mean ± SD over seeds) plus KERAAL cluster-level tests.
Usage: python summarize.py <runs dir> <KERAAL eval dir>"""
import glob
import json
import os
import re
import sys
from collections import defaultdict

import numpy as np
from scipy.stats import wilcoxon

RUNS, KEV = sys.argv[1:3]
sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp949
SEED = re.compile(r"_s\d+$")


def ms(v):
    return f"{np.mean(v):.1f} ± {np.std(v, ddof=1):.1f}" if len(v) > 1 else f"{v[0]:.1f}"


# ---------------- ASPset ----------------
print("## ASPset-510 test (official split), mean ± SD over seeds\n")
print("| input | norm | seeds | val MPJPE | test MPJPE | test PA-MPJPE | test accel |\n|---|---|---|---|---|---|---|")
groups = defaultdict(list)
for d in sorted(glob.glob(os.path.join(RUNS, "*"))):
    if SEED.search(d) and os.path.exists(os.path.join(d, "results.json")):
        r = json.load(open(os.path.join(d, "results.json")))
        groups[(r["input"], r.get("norm", "screen"))].append(r)
all_runs = [r for rs in groups.values() for r in rs]
views = {(r["n_test_views"], r["n_test_frames"]) for r in all_runs}
assert len(views) == 1, f"test sets differ between runs: {views}"
for (inp, norm), rs in sorted(groups.items()):
    print(f"| {inp} | {norm} | {len(rs)} | {ms([r['val']['mpjpe'] for r in rs])} | {ms([r['test']['mpjpe'] for r in rs])}"
          f" | {ms([r['test']['pa_mpjpe'] for r in rs])} | {ms([r['test']['accel'] for r in rs])} |")
mp = all_runs[0]["mean_pose_test"]
print(f"| mean pose | – | – | – | {mp['mpjpe']:.1f} | {mp['pa_mpjpe']:.1f} | – |")
n_views, n_frames = views.pop()
print(f"\nAll runs use the same test set: {n_views} views, {n_frames} frames. mm; accel = mm/frame².\n")

# ---------------- KERAAL ----------------
by_norm = defaultdict(list)
for f in sorted(glob.glob(os.path.join(KEV, "eval_det_*_s*.json"))):
    by_norm[os.path.basename(f).split("_")[2]].append(json.load(open(f)))
if not by_norm:
    sys.exit()
SRC = ("ours_3d", "raw_2d", "kinect")


def cell_means(rows, key):
    """Mean of a per-pair value within each participant × exercise cell (the unit of the test)."""
    c = defaultdict(list)
    for r in rows:
        if np.isfinite(r[key]):
            c[(r["participant"], r["exercise"])].append(r[key])
    return {k: np.mean(v) for k, v in c.items()}


def diff_rows(rows, a, b, m):
    return [{**r, "d": r[f"{a}_{m}"] - r[f"{b}_{m}"]} for r in rows]


print("## KERAAL G3: joint-angle agreement with Vicon\n")
print("Primary metric: per-pair Pearson r at lag 0 (r0), median over pairs, mean over seeds. "
      "r(best lag) searches ±1 s for each source the same way and is optimistic. RMSE is in degrees after removing "
      "each series' mean. Vicon angles are relative segment rotations, not anatomical flexion (see limitations).\n")
print("| model | seeds | pairs | ours r0 | raw 2D r0 | Kinect r0 | ours r (best lag) | raw 2D r | Kinect r |"
      " ours RMSE | raw 2D RMSE | Kinect RMSE |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
for norm, evs in sorted(by_norm.items()):
    s = [e["summary"]["all"]["all"] for e in evs]
    f = lambda k: f"{np.mean([x[k] for x in s]):.3f}"
    g = lambda k: f"{np.mean([x[k] for x in s]):.1f}"
    print(f"| det/{norm} | {len(evs)} | {s[0]['n']} | {f('ours_3d_r0')} | {f('raw_2d_r0')} | {f('kinect_r0')}"
          f" | {f('ours_3d_r')} | {f('raw_2d_r')} | {f('kinect_r')} | {g('ours_3d_rmse')} | {g('raw_2d_rmse')}"
          f" | {g('kinect_rmse')} |")

print("\n### Paired tests at participant × exercise level (9 cells, 3 participants; seed-averaged)\n")
print("| model | comparison | mean Δ over cells | cells where ours better | participants where ours better |"
      " Wilcoxon p (9 cells) |\n|---|---|---|---|---|---|")
for norm, evs in sorted(by_norm.items()):
    for m, sign in (("r0", 1), ("rmse", -1)):  # for RMSE, lower is better
        for other in ("raw_2d", "kinect"):
            cells = defaultdict(list)
            for e in evs:
                for k, v in cell_means(diff_rows(e["rows"], "ours_3d", other, m), "d").items():
                    cells[k].append(v)
            cm = {k: np.mean(v) for k, v in cells.items()}
            parts = defaultdict(list)
            for (p, _), v in cm.items():
                parts[p].append(v)
            pv = wilcoxon(list(cm.values())).pvalue
            print(f"| det/{norm} | ours − {other} ({m}) | {np.mean(list(cm.values())):+.3f} | "
                  f"{sum(sign * v > 0 for v in cm.values())}/{len(cm)} | "
                  f"{sum(sign * np.mean(v) > 0 for v in parts.values())}/{len(parts)} | {pv:.3f} |")

print("\n### Per angle (r0; seed-mean of median over pairs; angles with < 10 moving pairs omitted)\n")
print("| model | angle | pairs | ours r0 | raw 2D r0 | Kinect r0 |\n|---|---|---|---|---|---|")
for norm, evs in sorted(by_norm.items()):
    for a in evs[0]["summary"]["angle"]:
        v = [e["summary"]["angle"][a] for e in evs]
        if v[0]["n"] < 10:
            continue
        print(f"| det/{norm} | {a} | {v[0]['n']} | " + " | ".join(
            f"{np.mean([x[s + '_r0'] for x in v]):.3f}" for s in SRC) + " |")

for norm in sorted(by_norm):
    print(f"\n### Per participant and per label (det/{norm}, r0)\n")
    print("| group | pairs | ours r0 | raw 2D r0 | Kinect r0 |\n|---|---|---|---|---|")
    for grp in ("participant", "exercise", "label"):
        for k in by_norm[norm][0]["summary"][grp]:
            v = [e["summary"][grp][k] for e in by_norm[norm]]
            print(f"| {grp} {k} | {v[0]['n']} | " + " | ".join(
                f"{np.mean([x[s + '_r0'] for x in v]):.3f}" for s in SRC) + " |")
