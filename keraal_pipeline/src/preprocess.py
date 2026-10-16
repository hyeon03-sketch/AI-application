"""Load Kinect skeletons and normalize them → data/skeleton_raw.npz, data/skeleton_T{T}.npz.

Kinect V2 files: one row per frame, 175 values = 25 joints x (x, y, z, qx, qy, qz, qw).
Camera space: metres, y up, z = depth from the sensor. Only the 3D positions are used.

Normalization (per recording, in this order):
  1. centre   : subtract SpineBase (joint 0) in every frame
  2. heading  : ONE rotation about the vertical (y) axis per recording, chosen so the median
                hip line (HipLeft -> HipRight) points along +x.
                The hips are used, not the shoulders, and the rotation is constant over time:
                a per-frame shoulder alignment would erase the very torso rotation that
                RTK Error2 ("torso rotation not sufficient") is about.
  3. scale    : divide by the median torso length (SpineBase -> SpineShoulder)
  4. smooth   : centred moving average over 5 frames (Kinect jitter)
  5. resample : linear interpolation to T frames (default 100)

Outputs:
  skeleton_raw.npz   one (T_i, 25, 3) float32 array per rec_key, untouched positions
  skeleton_T100.npz  keys (N,), raw (N, T, 25, 3) resampled only, norm (N, T, 25, 3) fully normalized,
                     n_frames (N,), heading_deg (N,), torso_len_m (N,)

Usage:  python src/preprocess.py [--T 100] [--check]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

J = {"SpineBase": 0, "SpineMid": 1, "Neck": 2, "Head": 3,
     "ShoulderLeft": 4, "ElbowLeft": 5, "WristLeft": 6, "HandLeft": 7,
     "ShoulderRight": 8, "ElbowRight": 9, "WristRight": 10, "HandRight": 11,
     "HipLeft": 12, "KneeLeft": 13, "AnkleLeft": 14, "FootLeft": 15,
     "HipRight": 16, "KneeRight": 17, "AnkleRight": 18, "FootRight": 19,
     "SpineShoulder": 20, "HandTipLeft": 21, "ThumbLeft": 22, "HandTipRight": 23, "ThumbRight": 24}
N_JOINTS, N_COLS = 25, 175
SMOOTH_WIN = 5


def load_kinect(path: Path) -> np.ndarray:
    a = np.loadtxt(path, dtype=np.float64, ndmin=2)
    if a.shape[1] != N_COLS:
        raise ValueError(f"{path.name}: expected {N_COLS} columns, got {a.shape[1]}")
    return a.reshape(len(a), N_JOINTS, 7)[:, :, :3]


def heading_rotation(pos: np.ndarray) -> tuple[np.ndarray, float]:
    """Rotation about y that maps the median hip-line direction onto +x. Returns (3x3 matrix, angle in degrees).

    The median is taken over per-frame ANGLES (around their circular mean), not over vector components:
    a component-wise median does not commute with rotation, which left ~0.1 deg of residual heading when the
    same skeleton was fed in rotated (caught by tests/test_core.py).
    """
    hip = pos[:, J["HipRight"]] - pos[:, J["HipLeft"]]
    ang = np.arctan2(hip[:, 2], hip[:, 0])  # angle of the hip line in the x-z plane, per frame
    ref = np.arctan2(np.sin(ang).mean(), np.cos(ang).mean())
    theta = ref + np.median((ang - ref + np.pi) % (2 * np.pi) - np.pi)
    c, s = np.cos(theta), np.sin(theta)
    # rotate by +theta about y: (x, z) -> (x c + z s, -x s + z c) sends (cos t, sin t) to (1, 0)
    R = np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])
    return R, float(np.degrees(theta))


def smooth(x: np.ndarray, win: int = SMOOTH_WIN) -> np.ndarray:
    if len(x) < win:
        return x.copy()
    pad = win // 2
    xp = np.concatenate([np.repeat(x[:1], pad, 0), x, np.repeat(x[-1:], pad, 0)], axis=0)
    k = np.ones(win) / win
    flat = xp.reshape(len(xp), -1)
    out = np.stack([np.convolve(flat[:, i], k, mode="valid") for i in range(flat.shape[1])], axis=1)
    return out.reshape(x.shape)


def resample(x: np.ndarray, T: int) -> np.ndarray:
    src = np.linspace(0.0, 1.0, len(x))
    dst = np.linspace(0.0, 1.0, T)
    flat = x.reshape(len(x), -1)
    out = np.stack([np.interp(dst, src, flat[:, i]) for i in range(flat.shape[1])], axis=1)
    return out.reshape((T,) + x.shape[1:])


def normalize(pos: np.ndarray) -> tuple[np.ndarray, float, float]:
    centred = pos - pos[:, J["SpineBase"]:J["SpineBase"] + 1]
    R, heading = heading_rotation(centred)
    rotated = centred @ R.T
    torso = float(np.median(np.linalg.norm(rotated[:, J["SpineShoulder"]] - rotated[:, J["SpineBase"]], axis=1)))
    return smooth(rotated / torso), heading, torso


def check(raw: dict, keys, R0, N, n_frames, headings, torsos, expected_n: int) -> list[str]:
    fails = []
    if len(keys) != expected_n:
        fails.append(f"expected {expected_n} recordings with skeletons, processed {len(keys)}")
    for k, a in raw.items():
        if not np.isfinite(a).all():
            fails.append(f"{k}: non-finite values")
        if (np.abs(a).sum(axis=(1, 2)) == 0).any():
            fails.append(f"{k}: all-zero frame")
    if not (np.isfinite(N).all() and np.isfinite(R0).all()):
        fails.append("non-finite values after normalization")
    if np.abs(N[:, :, J["SpineBase"]]).max() > 1e-6:
        fails.append("SpineBase not at origin after normalization")
    tl = np.median(np.linalg.norm(N[:, :, J["SpineShoulder"]] - N[:, :, J["SpineBase"]], axis=2), axis=1)
    if np.abs(tl - 1).max() > 0.05:
        fails.append(f"normalized torso length off 1 by up to {np.abs(tl - 1).max():.3f}")
    hip = np.median(N[:, :, J["HipRight"]] - N[:, :, J["HipLeft"]], axis=1)
    ang = np.degrees(np.arctan2(hip[:, 2], hip[:, 0]))
    if np.abs(ang).max() > 2.0:
        fails.append(f"hip line not aligned with +x (max {np.abs(ang).max():.2f} deg)")
    if (torsos < 0.25).any() or (torsos > 0.8).any():
        fails.append(f"implausible torso length (m): min {torsos.min():.3f}, max {torsos.max():.3f}")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--T", type=int, default=100)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    root = args.root

    with (root / "data" / "master_index.csv").open(encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["kinect_path"]]
    pending = None
    with (root / "data" / "master_index.csv").open(encoding="utf-8") as f:
        pending = sum(1 for r in csv.DictReader(f) if not r["kinect_path"])

    raw, keys, R0, N, n_frames, headings, torsos, groups = {}, [], [], [], [], [], [], []
    for r in rows:
        pos = load_kinect(root / r["kinect_path"])
        raw[r["rec_key"]] = pos.astype(np.float32)
        norm, heading, torso = normalize(pos)
        keys.append(r["rec_key"]); groups.append(r["group"])
        R0.append(resample(pos, args.T)); N.append(resample(norm, args.T))
        n_frames.append(len(pos)); headings.append(heading); torsos.append(torso)

    keys = np.array(keys); R0 = np.stack(R0).astype(np.float32); N = np.stack(N).astype(np.float32)
    n_frames = np.array(n_frames); headings = np.array(headings); torsos = np.array(torsos); groups = np.array(groups)

    np.savez_compressed(root / "data" / "skeleton_raw.npz", **raw)
    out = root / "data" / f"skeleton_T{args.T}.npz"
    np.savez_compressed(out, keys=keys, raw=R0, norm=N, n_frames=n_frames, heading_deg=headings,
                        torso_len_m=torsos, group=groups)
    print(f"wrote data/skeleton_raw.npz and {out.relative_to(root).as_posix()}: raw/norm {N.shape}")
    print(f"Group 3 recordings pending (no skeleton yet): {pending}")

    # Camera set-up differs between sessions; this is the shift that normalization has to remove.
    sample = sorted((root / "raw" / "sample" / "group3" / "kinect").glob("*.txt"))
    sb = {g: np.stack([raw[k][:, 0].mean(0) for k, gg in zip(keys, groups) if gg == g]) for g in ("1A", "2A")}
    if sample:
        sb["3 (sample)"] = np.stack([load_kinect(p)[:, 0].mean(0) for p in sample])
    print("mean SpineBase position in camera space (x, y, z) m:")
    for g, v in sb.items():
        print(f"  group {g:10s} n={len(v):3d}  {np.round(v.mean(0), 2)}  sd {np.round(v.std(0), 2)}")
    for g in ("1A", "2A"):
        m = groups == g
        print(f"  group {g}: heading {headings[m].mean():+.1f} deg (sd {headings[m].std():.1f}), "
              f"torso {torsos[m].mean():.3f} m (sd {torsos[m].std():.3f}), frames {n_frames[m].min()}-{n_frames[m].max()}")
    if sample:
        hs = [normalize(load_kinect(p))[1:] for p in sample]
        print(f"  group 3 (sample, n={len(sample)}): heading {np.mean([h for h, _ in hs]):+.1f} deg, "
              f"torso {np.mean([t for _, t in hs]):.3f} m")

    if args.check:
        fails = check(raw, keys, R0, N, n_frames, headings, torsos, expected_n=len(rows))
        if sample:  # the Group 3 format must also go through the same code
            for p in sample:
                n, _, _ = normalize(load_kinect(p))
                if not np.isfinite(n).all():
                    fails.append(f"sample {p.name}: non-finite after normalization")
        for x in fails:
            print("CHECK FAILED:", x)
        print("CHECK", "PASSED" if not fails else f"FAILED ({len(fails)})")
        return 1 if fails else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
