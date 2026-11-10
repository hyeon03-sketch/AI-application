"""External baseline: MotionBERT (Zhu et al., ICCV 2023; public H36M weights, never saw KERAAL) on KERAAL G3, scored exactly like
our lifter: same YOLO 2D detections, same angle definitions, same Vicon reference (keraal_eval.evaluate, with only the lifting
step swapped). In the output json the "ours_3d" columns therefore hold MotionBERT; kinect / raw_2d columns must equal ours.
Usage: python mb_eval.py <out dir>      python mb_eval.py --check
Needs E:/MotionBERT_ext (code clone + ckpt/best_epoch.bin = FT_MB_release_MB_ft_h36m). KERAAL is CC BY-NC-SA: outputs stay on E:."""
import json
import os
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "accuracy_loop"))
MB = "E:/MotionBERT_ext"
G3, G3_DET = "E:/KERAAL_data/extracted/group3", "E:/KERAAL_mocap3d/det2d"
PLAIN_RUN = "E:/KERAAL_mocap3d/merge/aspset_vicon_P1"   # keraal_eval.evaluate loads a TCN it then never uses (lift is swapped)
H36M_TO_ASPSET = [3, 2, 1, 16, 15, 14, 6, 5, 4, 13, 12, 11, 10, 9, 8, 7, 0]   # so keraal_eval's "aspset" angle indices apply
H36M_L, H36M_R = [4, 5, 6, 11, 12, 13], [1, 2, 3, 14, 15, 16]
CLIP = 243


def coco_to_h36m(x):
    """(T, 17, C) COCO -> H36M 17. Pelvis = mid-hip, thorax = mid-shoulder, spine = their middle; H36M 'head' (top of head) has
    no COCO joint and is set to the nose (Euijin's rule, mocap3d_verification_1110.md 6.1) -- the scored angles do not use it."""
    hip, neck = (x[:, 11] + x[:, 12]) / 2, (x[:, 5] + x[:, 6]) / 2
    return np.stack([hip, x[:, 12], x[:, 14], x[:, 16], x[:, 11], x[:, 13], x[:, 15], (hip + neck) / 2, neck, x[:, 0], x[:, 0],
                     x[:, 5], x[:, 7], x[:, 9], x[:, 6], x[:, 8], x[:, 10]], 1)


def crop_scale(m):
    """MotionBERT infer_wild default: one square box around the whole recording -> [-1, 1]."""
    lo, hi = m[..., :2].reshape(-1, 2).min(0), m[..., :2].reshape(-1, 2).max(0)
    s = (hi - lo).max()
    out = m.copy()
    out[..., :2] = ((m[..., :2] - (lo + hi - s) / 2) / s - 0.5) * 2
    return out


def flip(x):
    y = x.clone()
    y[..., 0] *= -1
    y[..., H36M_L + H36M_R, :] = y[..., H36M_R + H36M_L, :]
    return y


def load_model(dev):
    sys.path.insert(0, os.path.join(MB, "MotionBERT"))
    from functools import partial
    from lib.model.DSTformer import DSTformer            # configs/pose3d/MB_ft_h36m.yaml
    m = DSTformer(dim_in=3, dim_out=3, dim_feat=512, dim_rep=512, depth=5, num_heads=8, mlp_ratio=2,
                  norm_layer=partial(torch.nn.LayerNorm, eps=1e-6), maxlen=CLIP, num_joints=17)
    sd = torch.load(os.path.join(MB, "ckpt", "best_epoch.bin"), map_location="cpu", weights_only=True)["model_pos"]
    m.load_state_dict({k.replace("module.", "", 1): v for k, v in sd.items()}, strict=True)
    return m.to(dev).eval()


def make_lift(mb, save_dir):
    def lift(_tcn, d, dev, _norm):
        kp, ok = d["kp"].copy(), d["found"]
        idx = np.arange(len(kp))
        for j in range(17):
            for c in range(2):
                kp[:, j, c] = np.interp(idx, idx[ok], kp[ok, j, c])   # same gap filling as our lifter
        x = coco_to_h36m(np.concatenate([kp, (d["conf"] * ok[:, None])[..., None]], -1))
        x = torch.from_numpy(crop_scale(x).astype(np.float32)).to(dev)
        out = []
        with torch.no_grad():
            for s in range(0, len(x), CLIP):
                c = x[s:s + CLIP][None]
                out.append(((mb(c) + flip(mb(flip(c)))) / 2)[0].cpu().numpy())   # flip test-time augmentation, as infer_wild
        p = np.concatenate(out)
        p = (p - p[:, :1])[:, H36M_TO_ASPSET]            # root-relative, MotionBERT's own scale (not metres)
        if save_dir:
            np.save(os.path.join(save_dir, f"{lift.n:04d}.npy"), p.astype(np.float32))
        lift.n += 1
        return p, kp
    lift.n = 0
    return lift


def main(out):
    import keraal_eval
    from tune import angle_summary
    os.makedirs(os.path.join(out, "pred3d"), exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    mb = load_model(dev)
    print("MotionBERT parameters (M):", round(sum(p.numel() for p in mb.parameters()) / 1e6, 1), flush=True)
    keraal_eval.lift = make_lift(mb, os.path.join(out, "pred3d"))
    tmp = os.path.join(out, "angles_all.json")
    keraal_eval.evaluate(G3, G3_DET, PLAIN_RUN, tmp)
    rows = json.load(open(tmp))["rows"]
    res = {p: angle_summary([r for r in rows if r["participant"] == p]) for p in ("P1", "P2", "P3")}
    json.dump(res, open(os.path.join(out, "summary.json"), "w"), indent=1)
    for p, v in res.items():
        print("RESULT", p, json.dumps(v), flush=True)


def _check():
    x = np.zeros((2, 17, 3)); x[:, 5], x[:, 6], x[:, 11], x[:, 12] = [0, 0, 1], [2, 0, 1], [0, 4, 1], [2, 4, 1]
    h = coco_to_h36m(x)
    assert h.shape == (2, 17, 3) and h[0, 0].tolist() == [1, 4, 1] and h[0, 8].tolist() == [1, 0, 1] and h[0, 7].tolist() == [1, 2, 1]
    assert (h[:, 14] == x[:, 6]).all() and (h[:, 1] == x[:, 12]).all()          # right shoulder / right hip
    c = crop_scale(np.array([[[0., 0, 1], [10, 20, 1]]]))
    assert np.allclose(c[0, :, 1], [-1, 1]) and np.allclose(c[0, :, 0], [-0.5, 0.5])
    t = torch.arange(17 * 3.).reshape(1, 1, 17, 3)
    assert torch.equal(flip(flip(t)), t) and flip(t)[0, 0, 4, 0] == -t[0, 0, 1, 0]
    names = ["pelvis", "rhip", "rknee", "rank", "lhip", "lknee", "lank", "spine", "neck", "nose", "head",
             "lsho", "lelb", "lwri", "rsho", "relb", "rwri"]
    asp = [names[i] for i in H36M_TO_ASPSET]
    assert asp[:6] == ["rank", "rknee", "rhip", "rwri", "relb", "rsho"] and asp[6:12] == ["lank", "lknee", "lhip", "lwri", "lelb", "lsho"]
    assert asp[14] == "neck" and asp[16] == "pelvis"
    print("mb_eval --check OK")


if __name__ == "__main__":
    _check() if sys.argv[1:] == ["--check"] else main(sys.argv[1])
