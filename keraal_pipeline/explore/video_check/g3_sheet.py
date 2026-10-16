"""Contact sheet: G3 participant P1, C vs E?B1/B2/B3, frame at peak arm height (from Kinect)."""
import sys, cv2, numpy as np
R = "E:/KERAAL_data/extracted/group3"
OUT = sys.argv[1]
ex, err = sys.argv[2], sys.argv[3]          # e.g. CTK E1
labels = ["C"] + [f"{err}B{b}" for b in (1, 2, 3)]
tiles = []
for p in ("P1", "P2"):
    row = []
    for lab in labels:
        stem = f"{ex}-{p}T1-Unknown-{lab}-0"
        X = np.loadtxt(f"{R}/kinect/G3-Kinect-{stem}.txt").reshape(-1, 25, 7)[:, :, :3]
        k = int(np.argmax(X[:, [6, 10], 1].mean(1)))      # highest mean wrist y
        cap = cv2.VideoCapture(f"{R}/videos/G3-Anon-{stem}.avi")
        cap.set(cv2.CAP_PROP_POS_FRAMES, k)
        ok, im = cap.read()
        im = cv2.resize(im, (480, 270))
        cv2.putText(im, f"{p} {lab} f{k}", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        row.append(im)
    tiles.append(np.hstack(row))
cv2.imwrite(OUT, np.vstack(tiles))
