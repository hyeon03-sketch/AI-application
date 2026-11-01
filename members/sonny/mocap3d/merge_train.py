"""Merge experiment: train the 2D->3D lifter on ASPset-510 + KERAAL G3, leave one KERAAL participant out.
KERAAL 3D targets come from keraal_calib.py (camera mm, aspset_17j, NaN = missing; head_top always NaN).
Modes:  aspset_vicon   ASPset train + KERAAL (2 participants), Vicon-calibrated targets
        aspset_kinect  same, but Kinect joints as targets (no Vicon calibration needed)
        keraal_vicon   KERAAL (2 participants) only, Vicon-calibrated targets
Model selection: mean of ASPset-val MPJPE and KERAAL-val MPJPE (every 5th recording of the training participants);
the held-out participant is never used before the final evaluation.
Usage: python merge_train.py <ASPset root> <ASPset det dir> <KERAAL group3> <KERAAL det dir> <calib dir> <run dir>
           --hold P1 --mode aspset_vicon [--epochs 120] [--seed 0]
       python merge_train.py ... <run dir> --hold P1 --eval-only <existing run dir>   (ASPset-only baseline)
       python merge_train.py --check"""
import argparse
import glob
import json
import os
import sys
import time

import numpy as np
import torch

import aspset
from train_lift import TCN, COCO_HIPS, batches, evaluate, load_split, pa_mpjpe

VALID = [j for j in range(17) if aspset.JOINTS[j] != "head_top"]


def keraal_seqs(g3_det, calib, keys, target):
    seqs = []
    for k in keys:
        d = np.load(os.path.join(g3_det, f"G3-Anon-{k}.npz"))
        if d["found"].mean() < 0.5:
            continue
        gt = np.load(os.path.join(calib, "gt3d", f"{k}.npz"))
        y = gt[target].astype(np.float64)
        start = max(0, -int(gt["lag"]))          # gt index i <-> Kinect/video frame i + start
        kp, ok = d["kp"].copy(), d["found"]
        n = min(len(y), len(kp) - start)
        idx = np.arange(len(kp))
        for j in range(17):
            for c in range(2):
                kp[:, j, c] = np.interp(idx, idx[ok], kp[ok, j, c])
        x2d = np.concatenate([aspset.normalize_root(kp, COCO_HIPS), (d["conf"] * ok[:, None])[..., None]], -1)[start:start + n]
        y = y[:n] - y[:n, aspset.PELVIS:aspset.PELVIS + 1]
        seqs.append({"id": k, "x2d": x2d.astype(np.float32), "y3d": (y / 1000).astype(np.float32)})
    return seqs


@torch.no_grad()
def predict(model, q, dev):
    from train_lift import flip
    half = model.rf // 2
    n = len(q["x2d"])
    idx = np.clip(np.arange(-half, n + half), 0, n - 1)
    p = model(torch.from_numpy(q["x2d"][idx])[None].to(dev))[0].cpu().numpy()
    xf, _ = flip(q["x2d"][idx], np.zeros((n, 17, 3), np.float32), "det")
    pf = model(torch.from_numpy(xf)[None].to(dev))[0].cpu().numpy()
    pf[..., 0] *= -1
    p = (p + pf[:, aspset.FLIP]) / 2
    return (p - p[:, aspset.PELVIS:aspset.PELVIS + 1]) * 1000


def nan_metrics(P, G):
    """P, G (F, 17, 3) mm. MPJPE over valid joints; PA-MPJPE on frames with all 16 joints valid."""
    P, G = P[:, VALID], G[:, VALID]
    e = np.linalg.norm(P - G, axis=-1)
    full = np.isfinite(G).all((1, 2))
    pa = pa_mpjpe(P[full].copy(), G[full]) if full.any() else np.array([np.nan])
    return np.nanmean(e, 1), pa, np.nanmean(e, 0)


def eval_keraal(model, seqs, dev):
    model.eval()
    mp, pa, pj = [], [], []
    for q in seqs:
        a, b, c = nan_metrics(predict(model, q, dev), q["y3d"] * 1000)
        mp.append(a), pa.append(b), pj.append(c)
    mp, pa = np.concatenate(mp), np.concatenate(pa)
    per_joint = np.nanmean(np.stack(pj), 0)
    return {"mpjpe": float(np.nanmean(mp)), "pa_mpjpe": float(np.nanmean(pa)), "frames": int(np.isfinite(mp).sum()),
            "per_joint": {aspset.JOINTS[j]: round(float(v), 1) for j, v in zip(VALID, per_joint)}}


def train(model, train_seqs, val_fn, epochs, lr, rng, dev, run):
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.ExponentialLR(opt, 0.95 ** (60 / epochs))
    best, log, t0 = (1e9, -1), [], time.time()
    for ep in range(epochs):
        model.train()
        tot, cnt = 0.0, 0
        for X, Y in batches(train_seqs, model.rf, 128, 64, "det", rng):
            X, Y = X.to(dev), Y.to(dev)
            P = model(X)
            m = ~torch.isnan(Y[..., 0])                      # per-joint mask: KERAAL head_top / lost Vicon targets
            loss = torch.linalg.norm(P[m] - Y[m], dim=-1).mean()
            opt.zero_grad(); loss.backward(); opt.step()
            tot, cnt = tot + loss.item() * m.sum().item(), cnt + m.sum().item()
        sched.step()
        v = val_fn(model)
        log.append({"epoch": ep + 1, "train_mpjpe": tot / cnt * 1000, **v, "min": (time.time() - t0) / 60})
        print(json.dumps(log[-1]), flush=True)
        if v["val_score"] < best[0]:
            best = (v["val_score"], ep + 1)
            torch.save(model.state_dict(), os.path.join(run, "best.pt"))
    json.dump(log, open(os.path.join(run, "log.json"), "w"), indent=1)
    return best


def main():
    ap = argparse.ArgumentParser()
    for n in ("aspset_root", "aspset_det", "g3", "g3_det", "calib", "run"):
        ap.add_argument(n)
    ap.add_argument("--hold", required=True)
    ap.add_argument("--mode", choices=["aspset_vicon", "aspset_kinect", "keraal_vicon"])
    ap.add_argument("--eval-only")
    ap.add_argument("--epochs", type=int, default=120)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.run, exist_ok=True)
    json.dump({**vars(a), "input": "det", "norm": "root"}, open(os.path.join(a.run, "args.json"), "w"), indent=1)
    torch.manual_seed(a.seed)
    rng = np.random.default_rng(a.seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    keys = sorted(os.path.basename(f)[:-4] for f in glob.glob(os.path.join(a.calib, "gt3d", "*.npz")))
    part = lambda k: k.split("-")[1][:2]
    test_keys = [k for k in keys if part(k) == a.hold]
    tr_keys = [k for k in keys if part(k) != a.hold]
    kval_keys, ktr_keys = tr_keys[0::5], [k for i, k in enumerate(tr_keys) if i % 5]
    target = "kinect" if a.mode == "aspset_kinect" else "vicon"
    model = TCN(17, 3).to(dev)

    if a.eval_only:
        model.load_state_dict(torch.load(os.path.join(a.eval_only, "best.pt"), map_location=dev))
        best = (None, None)
    else:
        ktr = keraal_seqs(a.g3_det, a.calib, ktr_keys, target)
        kval = keraal_seqs(a.g3_det, a.calib, kval_keys, "vicon")
        aval = load_split(a.aspset_root, "val", "det", a.aspset_det) if a.mode != "keraal_vicon" else []
        tr = ktr + (load_split(a.aspset_root, "train", "det", a.aspset_det) if a.mode != "keraal_vicon" else [])
        print(f"train seqs {len(tr)} (KERAAL {len(ktr)}, frames {sum(len(q['y3d']) for q in ktr)}) | "
              f"all frames {sum(len(q['y3d']) for q in tr)}", flush=True)

        def val_fn(m):
            kv = eval_keraal(m, kval, dev)["mpjpe"]
            av = evaluate(m, aval, dev, "det", tta=False)[0]["mpjpe"] if aval else None
            return {"val_keraal": kv, "val_aspset": av, "val_score": kv if av is None else (kv + av) / 2}
        best = train(model, tr, val_fn, a.epochs, a.lr, rng, dev, a.run)
        model.load_state_dict(torch.load(os.path.join(a.run, "best.pt"), map_location=dev))
    if a.eval_only:
        torch.save(model.state_dict(), os.path.join(a.run, "best.pt"))
    test_v = keraal_seqs(a.g3_det, a.calib, test_keys, "vicon")
    test_k = keraal_seqs(a.g3_det, a.calib, test_keys, "kinect")
    asp_test = evaluate(model, load_split(a.aspset_root, "test", "det", a.aspset_det), dev, "det")[0]
    by_ex = {ex: eval_keraal(model, [q for q in test_v if q["id"].startswith(ex)], dev) for ex in ("CTK", "ELK", "RTK")}
    out = {"mode": a.mode or "aspset_only", "hold": a.hold, "best_epoch": best[1], "seed": a.seed,
           "keraal_test_vs_vicon": eval_keraal(model, test_v, dev), "keraal_test_vs_kinect": eval_keraal(model, test_k, dev),
           "keraal_test_vs_vicon_by_exercise": {k: {m: v[m] for m in ("mpjpe", "pa_mpjpe")} for k, v in by_ex.items()},
           "aspset_test": {k: asp_test[k] for k in ("mpjpe", "pa_mpjpe", "accel")},
           "n_test_recordings": len(test_v)}
    json.dump(out, open(os.path.join(a.run, "results.json"), "w"), indent=1)
    print("RESULT", json.dumps({k: out[k] for k in ("mode", "hold", "best_epoch", "aspset_test")}),
          json.dumps({k: out["keraal_test_vs_vicon"][k] for k in ("mpjpe", "pa_mpjpe")}), flush=True)


def _check():
    rng = np.random.default_rng(0)
    G = rng.normal(size=(20, 17, 3)) * 200
    G[:, aspset.JOINTS.index("head_top")] = np.nan
    G[3, 0] = np.nan
    mp, pa, pj = nan_metrics(G.copy(), G)
    assert np.allclose(mp, 0) and np.allclose(pa, 0, atol=1e-6) and len(pa) == 19 and np.isfinite(pj).all()
    mp, pa, _ = nan_metrics(G + 10, G)
    assert np.allclose(mp, np.sqrt(300)) and np.allclose(pa, 0, atol=1e-6)
    # per-joint mask ignores NaN targets in the loss
    P, Y = torch.zeros(2, 4, 17, 3), torch.ones(2, 4, 17, 3)
    Y[..., 12, :] = float("nan")
    m = ~torch.isnan(Y[..., 0])
    assert torch.isfinite(torch.linalg.norm(P[m] - Y[m], dim=-1).mean())
    print("merge_train --check OK")


if __name__ == "__main__":
    if sys.argv[1] == "--check":
        _check()
    else:
        main()
