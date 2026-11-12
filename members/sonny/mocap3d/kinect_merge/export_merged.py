"""Export the merged training data (ASPset + KERAAL) exactly as km_train builds it, one .npz per source.
Per file: x2d (N,17,3) root-normalised COCO 2D + confidence, y3d (N,17,3) pelvis-relative metres (aspset_17j order,
NaN = missing), ids / starts (sequence id and first row of each sequence). Kinect groups are already 4:3-stretched and
resampled 15 -> 30 fps. KERAAL-derived files are CC BY-NC-SA: share privately, never on GitHub.
Usage: python export_merged.py <out dir>      python export_merged.py --check"""
import os
import sys

import numpy as np

import km_train as km


def pack(seqs, path):
    starts = np.cumsum([0] + [len(q["y3d"]) for q in seqs[:-1]])
    np.savez_compressed(path, x2d=np.concatenate([q["x2d"] for q in seqs]), y3d=np.concatenate([q["y3d"] for q in seqs]),
                        ids=np.array([q["id"] for q in seqs]), starts=starts)
    return sum(len(q["y3d"]) for q in seqs)


def main(out):
    os.makedirs(out, exist_ok=True)
    keys = sorted(os.path.basename(f)[:-4] for f in km.glob.glob(os.path.join(km.CALIB, "gt3d", "*.npz")))
    src = {"keraal_g3_vicon": lambda: km.keraal_seqs(km.G3_DET, km.CALIB, keys, "vicon")}
    for g in ("group2A", "group2B", "group1B"):  # group1A = eval only, not trained on
        src[f"keraal_{g}_kinect"] = lambda g=g: km.kinect_seqs(g)
    for sp in ("train", "val", "test"):
        src[f"aspset_{sp}"] = lambda sp=sp: km.load_split(km.ASP, sp, "det", km.ASP_DET)
    for name, f in src.items():
        print(name, pack(f(), os.path.join(out, name + ".npz")), "frames", flush=True)
    np.save(os.path.join(out, "kinect_joint_weights_P1P2P3.npy"), km.kinect_joint_weights(keys))


def _check():
    import tempfile
    q = [{"id": "a", "x2d": np.zeros((3, 17, 3), np.float32), "y3d": np.ones((3, 17, 3), np.float32)},
         {"id": "b", "x2d": np.zeros((2, 17, 3), np.float32), "y3d": np.ones((2, 17, 3), np.float32)}]
    p = os.path.join(tempfile.mkdtemp(), "t.npz")
    assert pack(q, p) == 5
    d = np.load(p)
    assert d["starts"].tolist() == [0, 3] and d["ids"].tolist() == ["a", "b"] and d["x2d"].shape == (5, 17, 3)
    print("export_merged --check OK")


if __name__ == "__main__":
    _check() if sys.argv[1] == "--check" else main(sys.argv[1])
