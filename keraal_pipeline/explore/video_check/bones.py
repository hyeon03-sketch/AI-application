"""Per-subject Kinect bone lengths in 2A (+1A): is S1-Brest the same person as S1-Roscoff?"""
import glob, os, re, numpy as np
from collections import defaultdict
R = "E:/KERAAL_data/extracted"
# upper-body bones only (lower-body Kinect joints were found unreliable)
BONES = {"spine": (0, 20), "neck": (20, 2), "head": (2, 3), "shoulderL": (20, 4), "shoulderR": (20, 8),
         "upperarmL": (4, 5), "upperarmR": (8, 9), "forearmL": (5, 6), "forearmR": (9, 10)}
rec = defaultdict(list)
for g in ["group1A", "group2A"]:
    for f in glob.glob(f"{R}/{g}/kinect/*.txt"):
        m = re.match(r"G(\w+)-Kinect-(\w+)-(\w+)-(\w+)-\d+\.txt", os.path.basename(f))
        if not m: continue
        X = np.loadtxt(f).reshape(-1, 25, 7)[:, :, :3]
        L = [np.median(np.linalg.norm(X[:, a] - X[:, b], axis=1)) for a, b in BONES.values()]
        rec[f"{m.group(1)}-{m.group(3)}-{m.group(4)}"].append(L)
names = sorted(rec)
M = {k: np.median(rec[k], axis=0) for k in names}
S = {k: np.std(rec[k], axis=0) for k in names}
print("subject              n  " + " ".join(f"{b:>9}" for b in BONES))
for k in names:
    print(f"{k:18} {len(rec[k]):3}  " + " ".join(f"{v*100:9.1f}" for v in M[k]))
# distance between subject profiles (cm, RMS over bones), relative to within-subject spread
D = lambda a, b: np.sqrt(np.mean((M[a] - M[b]) ** 2)) * 100
within = np.median([np.sqrt(np.mean(S[k] ** 2)) * 100 for k in names if len(rec[k]) > 3])
print(f"\nmedian within-subject spread (RMS SD across recordings): {within:.2f} cm")
for a in names:
    if a.startswith("2A-S1"):
        ds = sorted((D(a, b), b) for b in names if b != a)
        print(f"{a}: nearest = " + ", ".join(f"{b} {d:.2f}" for d, b in ds[:5]))
