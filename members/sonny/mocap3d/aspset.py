"""ASPset-510 loading: C3D joints, cameras, boxes, splits. `python aspset.py --check <root>` runs a self-test."""
import csv
import glob
import json
import os
import struct
import sys

import numpy as np

JOINTS = ["right_ankle", "right_knee", "right_hip", "right_wrist", "right_elbow", "right_shoulder",
          "left_ankle", "left_knee", "left_hip", "left_wrist", "left_elbow", "left_shoulder",
          "head_top", "head", "neck", "spine", "pelvis"]
PELVIS = 16
FLIP = [6, 7, 8, 9, 10, 11, 0, 1, 2, 3, 4, 5, 12, 13, 14, 15, 16]  # left<->right
W, H = 3840, 2160


def read_c3d(path):
    """Return (frames, 17, 3) joint positions in mm (world coordinates)."""
    with open(path, "rb") as f:
        h = f.read(512)
        n_pts, _, first, last = struct.unpack("<4H", h[2:10])
        assert struct.unpack("<f", h[12:16])[0] < 0, "integer C3D not supported"
        start = struct.unpack("<H", h[16:18])[0]
        f.seek((start - 1) * 512)
        n = last - first + 1
        data = np.frombuffer(f.read(n * n_pts * 16), dtype="<f4").reshape(n, n_pts, 4)
    return data[..., :3].astype(np.float64)


def read_camera(path):
    cal = json.load(open(path))
    K = np.array(cal["intrinsic_matrix"]).reshape(3, 4)[:, :3]
    E = np.array(cal["extrinsic_matrix"]).reshape(4, 4)
    return K, E[:3, :3], E[:3, 3]


def read_boxes(path):
    with open(path) as f:
        return np.array([[float(v) for v in r] for r in list(csv.reader(f))[1:]])


def to_camera(x_world, R, t):
    return x_world @ R.T + t


def project(x_cam, K):
    uvw = x_cam @ K.T
    return uvw[..., :2] / uvw[..., 2:]


def normalize_2d(uv):
    """VideoPose3D screen normalisation: x in [-1, 1], aspect ratio kept."""
    return uv / W * 2 - np.array([1, H / W])


def normalize_root(uv, hips):
    """Centre each frame on the mid-hip and divide by the sequence's median 2D body extent.
    Removes image size and subject distance, so the input scale matches across datasets."""
    c = uv[:, list(hips)].mean(1, keepdims=True)
    extent = np.ptp(uv, axis=1).max(-1)
    return (uv - c) / np.median(extent)


def splits(root):
    """{'train'|'val'|'test': [(subject, clip), ...]} from splits.csv."""
    out = {}
    with open(os.path.join(root, "splits.csv")) as f:
        for subj, clip, split, _ in csv.reader(f):
            out.setdefault(split, []).append((subj, clip))
    return out


def part(split):
    return "test" if split == "test" else "trainval"


def clip_views(root, split):
    """Yield (subject, clip, camera) for every view that has a video file."""
    for subj, clip in splits(root)[split]:
        for vid in sorted(glob.glob(os.path.join(root, part(split), "videos", subj, f"{subj}-{clip}-*.mkv"))):
            yield subj, clip, os.path.basename(vid)[:-4].split("-")[2]


def load_view(root, split, subj, clip, cam):
    """Pelvis-relative 3D in camera coords (mm), GT 2D (px), boxes (px)."""
    p = part(split)
    xw = read_c3d(os.path.join(root, p, "joints_3d", subj, f"{subj}-{clip}.c3d"))
    K, R, t = read_camera(os.path.join(root, p, "cameras", subj, f"{subj}-{cam}.json"))
    xc = to_camera(xw, R, t)
    return {"x3d": xc - xc[:, PELVIS:PELVIS + 1], "uv": project(xc, K),
            "boxes": read_boxes(os.path.join(root, p, "boxes", subj, f"{subj}-{clip}-{cam}.csv"))}


def _check(root):
    sp = splits(root)
    assert {k: len(v) for k, v in sp.items()} == {"train": 390, "val": 60, "test": 60}, sp.keys()
    views = list(clip_views(root, "val"))
    assert len(views) == 180, len(views)
    v = load_view(root, "val", *views[0])
    assert v["x3d"].shape[1:] == (17, 3) and np.allclose(v["x3d"][:, PELVIS], 0)
    assert len(v["uv"]) == len(v["boxes"]), (len(v["uv"]), len(v["boxes"]))
    inside = ((v["uv"] >= v["boxes"][:, None, :2] - 50) & (v["uv"] <= v["boxes"][:, None, 2:] + 50)).all(-1).mean()
    assert inside > 0.95, f"projected joints inside box only {inside:.2f}"
    thigh = np.linalg.norm(v["x3d"][:, 1] - v["x3d"][:, 2], axis=1).mean()
    assert 300 < thigh < 600, thigh
    assert [JOINTS[i].replace("left", "L").replace("right", "left").replace("L", "right") for i in FLIP] == JOINTS
    print(f"aspset --check OK (val views {len(views)}, joints-in-box {inside:.3f}, thigh {thigh:.0f} mm)")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--check"]:
        _check(sys.argv[2])
