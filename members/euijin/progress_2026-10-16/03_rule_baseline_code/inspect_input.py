"""Day 1 - check the CSV before anything else.
Prints the columns, what was auto-detected, label values, and saves a front-view skeleton plot
so you can confirm the Kinect joint order and the up-axis.

    python inspect_input.py            (uses config.DATA_CSV)
    python inspect_input.py path\\to\\model_input_kinect.csv
"""
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import config as C
import skeleton as S

csv = sys.argv[1] if len(sys.argv) > 1 else C.DATA_CSV
C.OUT_DIR.mkdir(parents=True, exist_ok=True)
df = pd.read_csv(csv, low_memory=False)
print(f"\n=== {csv}\nrows={len(df):,}  columns={df.shape[1]}\n")
for c in df.columns:
    s = df[c]
    ex = s.dropna().iloc[0] if s.notna().any() else None
    print(f"  {c:<35} {str(s.dtype):<8} nunique={s.nunique():<8} e.g. {str(ex)[:40]}")

cmap = S.resolve_columns(df.columns)
print("\n--- auto-detected label columns (set config.COLS if wrong / None)")
for k, v in cmap.items():
    print(f"  {k:<12} -> {v}")
jmap = S.detect_joint_columns(df.columns)
print("\n--- joint columns:", "NOT FOUND - fill config.JOINT_COLUMNS" if jmap is None else f"{len(jmap)} joints")
if jmap:
    for k, v in list(jmap.items())[:6]:
        print(f"  {k:<14} {v}")
    print("  ...")

for k in ("exercise", "group", "error_type", "body_part", "in_span", "truncated"):
    col = cmap.get(k)
    if col:
        print(f"\n--- values of {k} ({col})")
        print(df[col].astype(str).value_counts().head(15).to_string())
if cmap["recording"]:
    rec = df[cmap["recording"]]
    print(f"\n--- recordings: {rec.nunique()}   example ids: {list(rec.drop_duplicates().head(5))}")
    if not cmap["exercise"]:
        ex = rec.drop_duplicates().map(S.infer_exercise)
        print("  exercise parsed from recording id:", ex.value_counts(dropna=False).to_dict())

# ---------- skeleton sanity plot (one frame from the middle of the first recording)
if jmap and cmap["recording"]:
    first = df[df[cmap["recording"]] == df[cmap["recording"]].iloc[0]]
    row = first.iloc[len(first) // 2]
    a = C.AXES
    fig, ax = plt.subplots(figsize=(5, 6))
    for name, (cx, cy, cz) in jmap.items():
        p = np.array([row[cx], row[cy], row[cz]], float)
        x, y = p[a["lateral"]], C.UP_SIGN * p[a["up"]]
        ax.scatter(x, y, s=12)
        ax.text(x, y, name, fontsize=6)
    ax.set_aspect("equal"); ax.set_title("Front view: Head should be on top,\nShoulderLeft/Right on opposite sides")
    out = C.OUT_DIR / "inspect_skeleton.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"\nSaved {out}  -> open it and check joint names / orientation.")
    print("If upside-down: config.UP_SIGN = -1. If names look shifted by one: config.KINECT_INDEX_BASE = 1.")
