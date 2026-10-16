"""Acted vs real CTK Error1, chosen by a fixed rule (first 3 by sorted rec_key per category).

Metric: peak (95th pct) mean wrist height above shoulders / trunk length, from Kinect.
Frame shown: the frame of maximum mean wrist height.
"""
import sys, cv2, numpy as np, pandas as pd
P = "C:/Users/user/Desktop/SOn H.g/class materials/AI application/keraal_pipeline/"
E = "E:/KERAAL_data/extracted/"
OUT = sys.argv[1]
d = pd.read_csv(P + "data/master_index.csv", dtype=str).fillna("-")
d = d[d.exercise == "CTK"].sort_values("rec_key")
A, B = d.evaluation_A + "|" + d.error_A, d.evaluation_B + "|" + d.error_B
CATS = {
    "G3 acted correct (C)": d[d.g3_label == "C"],
    "G3 acted E1 both arms (E1B3)": d[d.g3_label == "E1B3"],
    "1A agreed correct": d[(d.group == "1A") & (A == "Correct|-") & (B == "Correct|none")],
    "1A agreed Error1": d[(d.group == "1A") & (A == "Incorrect|Error1") & (B == "Incorrect|Error1")],
    "1A disagree (A ok, B Error1)": d[(d.group == "1A") & (A == "Correct|-") & (B == "Incorrect|Error1")],
    "2A agreed correct": d[(d.group == "2A") & (A == "Correct|-") & (B == "Correct|none")],
    "2A agreed Error1": d[(d.group == "2A") & (A == "Incorrect|Error1") & (B == "Incorrect|Error1")],
}

def load(row):
    X = np.loadtxt(P + row.kinect_path).reshape(-1, 25, 7)[:, :, :3]
    tr = np.median(np.linalg.norm(X[:, 20] - X[:, 0], axis=1))
    h = (X[:, [6, 10], 1] - X[:, [4, 8], 1]).mean(1) / tr
    return np.percentile(h, 95), int(np.argmax(h))

def video(row):
    g = {"1A": "group1A", "2A": "group2A", "3": "group3"}[row.group]
    name = row.kinect_path.split("/")[-1].replace("-Kinect-", "-Anon-").replace(".txt", "")
    return E + f"{g}/videos/{name}" + (".avi" if row.group == "3" else ".mp4")

print(f"{'category':32} {'n':>3}  peak wrist height (median [IQR])")
rows_img = []
for cat, sub in CATS.items():
    vals = [load(r) for r in sub.itertuples()]
    hs = np.array([v[0] for v in vals])
    q1, q2, q3 = np.percentile(hs, [25, 50, 75])
    print(f"{cat:32} {len(hs):3}  {q2:5.2f} [{q1:.2f}, {q3:.2f}]")
    if cat.startswith("2A"): continue
    pick = sub.drop_duplicates("participant_key").head(3) if cat.startswith("G3") else sub.head(3)
    tiles = []
    for r in pick.itertuples():
        h, k = load(r)
        cap = cv2.VideoCapture(video(r)); cap.set(cv2.CAP_PROP_POS_FRAMES, k); ok, im = cap.read()
        im = cv2.resize(im, (400, 300 if r.group != "3" else 225)); im = cv2.resize(im, (400, 260))
        cv2.putText(im, f"{r.rec_key}  h={h:.2f}", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        tiles.append(im)
    while len(tiles) < 3: tiles.append(np.zeros_like(tiles[0]))
    band = np.zeros((26, 1200, 3), np.uint8)
    cv2.putText(band, cat, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    rows_img += [band, np.hstack(tiles)]
cv2.imwrite(OUT, np.vstack(rows_img))
