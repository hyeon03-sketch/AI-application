"""Are the 1A patients (R1-R6) among the 1B recordings used for training? 1B file names carry no participant id, so the only
handle is body size: median Kinect bone lengths per recording.
Step 1 (is the handle any good?): leave-one-recording-out nearest-centroid patient id inside 1A, per hospital.
Step 2: each training 1B recording -> nearest 1A patient of the same hospital, distance in units of the within-patient spread.
Usage: python overlap_1a_1b.py [out.json]      python overlap_1a_1b.py --check
shortcut: body size cannot tell two people of the same build apart, so this can only show "no 1A-sized person" or "cannot
exclude"; ask the KERAAL authors for the 1B participant list if a hard answer is needed."""
import glob
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KROOT, DET = "E:/KERAAL_data/extracted", "E:/KERAAL_mocap3d/g1a"


def assign(F, C, S):
    """Rows F -> (index of nearest centroid, distance), distances scaled by the pooled within-class std S."""
    d = np.sqrt((((F[:, None] - C[None]) / S) ** 2).mean(-1))
    return d.argmin(1), d.min(1)


def loo_accuracy(F, y):
    """Nearest-centroid accuracy with the tested row left out of its own centroid; also returns own-centroid distances."""
    labs = sorted(set(y)); y = np.array(y); hit, own = [], []
    for i in range(len(F)):
        keep = np.arange(len(F)) != i
        C = np.stack([F[keep & (y == l)].mean(0) for l in labs])
        S = np.sqrt(np.mean([F[keep & (y == l)].var(0) for l in labs], 0))
        j, d = assign(F[i:i + 1], C, S)
        hit.append(labs[j[0]] == y[i])
        own.append(np.sqrt((((F[i] - C[labs.index(y[i])]) / S) ** 2).mean()))
    return float(np.mean(hit)), np.array(own)


def main(out):
    sys.path.insert(0, os.path.join(HERE, ".."))
    from audit import bone_lengths, kinect17
    feat = lambda f: np.array([np.nanmedian(v) for v in bone_lengths(kinect17(f)).values()])
    A = {}                                              # site -> [(patient, features)]
    for f in sorted(glob.glob(f"{KROOT}/group1A/kinect/*.txt")):
        m = re.match(r"G1A-Kinect-\w+-(R\d)-(\w+)-\d+", os.path.basename(f))
        A.setdefault(m[2], []).append((m[1], feat(f)))
    B = {}
    for d in sorted(glob.glob(f"{DET}/det_clean_group1B/*.npz")):
        key = os.path.basename(d)[:-4]
        B.setdefault(key.split("-")[1], []).append((key, feat(glob.glob(f"{KROOT}/group1B/kinect/*-Kinect-{key}.txt")[0])))
    res = {}
    for site, rows in A.items():
        y, F = [r[0] for r in rows], np.stack([r[1] for r in rows])
        ok = np.isfinite(F).all(1); y, F = [l for l, k in zip(y, ok) if k], F[ok]
        acc, own = loo_accuracy(F, y)
        labs = sorted(set(y)); ya = np.array(y)
        C = np.stack([F[ya == l].mean(0) for l in labs]); S = np.sqrt(np.mean([F[ya == l].var(0) for l in labs], 0))
        thr = float(np.percentile(own, 95))             # 95% of true 1A recordings sit this close to their own patient
        keys, FB = [r[0] for r in B.get(site, [])], np.stack([r[1] for r in B.get(site, [])])
        j, d = assign(FB, C, S)
        res[site] = {"patients": labs, "n_1a": len(y), "loo_accuracy": acc, "chance": 1 / len(labs), "own_dist_p95": thr,
                     "n_1b_train": len(keys), "n_1b_within_1a_range": int((d <= thr).sum()),
                     "nearest_patient_counts": {l: int(((j == i) & (d <= thr)).sum()) for i, l in enumerate(labs)},
                     "dist_1b_median": float(np.median(d)), "centroid_mm": {l: np.round(c).tolist() for l, c in zip(labs, C)}}
        print(site, json.dumps({k: v for k, v in res[site].items() if k != "centroid_mm"}), flush=True)
    json.dump(res, open(out, "w"), indent=1)


def _check():
    rng = np.random.default_rng(0)
    C = np.array([[300.0, 400], [330, 440], [360, 380]])
    y = [l for l in "abc" for _ in range(20)]
    F = np.concatenate([c + rng.normal(0, 3, (20, 2)) for c in C])
    acc, own = loo_accuracy(F, y)
    assert acc > 0.95 and own.max() < 4
    j, d = assign(np.array([[300.0, 400], [500, 500]]), C, np.full(2, 3.0))
    assert j[0] == 0 and d[0] < 0.1 and d[1] > 10
    print("overlap_1a_1b --check OK")


if __name__ == "__main__":
    _check() if sys.argv[1:] == ["--check"] else main(sys.argv[1] if sys.argv[1:] else "E:/KERAAL_mocap3d/km/overlap_1a_1b.json")
