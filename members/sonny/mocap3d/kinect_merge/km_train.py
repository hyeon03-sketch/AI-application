"""Lifter trained on ASPset-510 + KERAAL G3 (Vicon) + KERAAL groups without Vicon (Kinect targets), fixing the merge problems
measured by audit.py:
  --flag       skeleton definitions differ (ASPset spine-neck 412 mm vs Kinect 190 mm, ...): one extra input channel says which
               definition to output (0 ASPset, 1 KERAAL/Kinect). At use time it is always 1.
  --kinect     groups whose 3D target is the Kinect skeleton (no Vicon), e.g. group2A,group2B,group1B
  --kweight    Kinect arms are noisy (wrist 122 mm vs Vicon): per-joint loss weight min(1, (30 mm / e_j)^2), e_j measured on the
               G3 training participants only
  1A/2A/1B/2B video is 1920x1080 squeezed to 480x360: x is stretched by 4/3 before normalisation (SQUEEZE).
  Those groups are 15 fps; 2D and targets are interpolated to the 30 fps of G3.
Tested on a G3 participant never trained on, against Vicon; same outputs as accuracy_loop/tune.py.
Usage: python km_train.py <run dir> --train-parts P1,P2 --eval-parts P3 [--flag] [--kinect group2A,group2B,group1B] [--kweight]
       python km_train.py --check
KERAAL is CC BY-NC-SA: run dirs stay on E:."""
import argparse
import glob
import json
import os
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "patients_1a"))
sys.path.insert(0, os.path.join(HERE, "..", "accuracy_loop"))
import aspset
import keraal_eval
import train_lift
from audit import kinect17
from merge_train import eval_keraal, keraal_seqs
from train_lift import TCN, COCO_HIPS, evaluate, load_split
from tune import ASP, ASP_DET, CALIB, G3, G3_DET, angle_summary

KROOT, DET = "E:/KERAAL_data/extracted", "E:/KERAAL_mocap3d/g1a"
SQUEEZE = 4 / 3   # 480x360 frames hold a 16:9 image: fitted fy/fx = 1.36 on 1A vs 1.04 on G3 (audit.py)


class FlagTCN(TCN):
    """TCN with one more input channel: the skeleton definition to output. Inputs without it get `flag` appended."""

    def __init__(self, in_joints, in_ch, flag=1.0, **kw):
        super().__init__(in_joints, in_ch + 1, **kw)
        self.in_ch, self.flag = in_ch + 1, flag

    def forward(self, x):
        if x.shape[-1] == self.in_ch - 1:
            x = torch.cat([x, torch.full_like(x[..., :1], self.flag)], -1)
        return super().forward(x)


def with_flags(seqs, definition, noisy, flag):
    """Append channels to x2d: [definition] if --flag, then [noisy target] (stripped before the model)."""
    for q in seqs:
        x = q["x2d"]
        extra = ([np.full(x.shape[:2] + (1,), definition, np.float32)] if flag else []) + [np.full(x.shape[:2] + (1,), noisy, np.float32)]
        q["x2d"] = np.concatenate([x] + extra, -1)
    return seqs


def resample_2x(x):
    idx = np.arange(len(x)); t = np.arange(2 * len(x) - 1) / 2
    flat = x.reshape(len(x), -1)
    return np.stack([np.interp(t, idx, flat[:, c]) for c in range(flat.shape[1])], 1).reshape(len(t), *x.shape[1:])


def kinect_seqs(group):
    seqs = []
    for det in sorted(glob.glob(f"{DET}/det_clean_{group}/*.npz")):
        key = os.path.basename(det)[:-4]
        d = np.load(det)
        Y = kinect17(glob.glob(f"{KROOT}/{group}/kinect/*-Kinect-{key}.txt")[0])
        n = min(len(Y), len(d["kp"]))
        ok = d["found"][:n]
        lost = np.isnan(Y[:n][:, [j for j in range(17) if j != 12]]).any((1, 2))   # head_top is always NaN
        if ok.mean() < 0.5 or lost.mean() > 0.5:
            continue
        kp = d["kp"][:n].copy()
        idx = np.arange(n)
        for j in range(17):
            for c in range(2):
                kp[:, j, c] = np.interp(idx, idx[ok], kp[ok, j, c])
        kp[..., 0] *= SQUEEZE
        conf = d["conf"][:n] * ok[:, None]
        Y = Y[:n] - Y[:n, aspset.PELVIS:aspset.PELVIS + 1]
        x2d = np.concatenate([aspset.normalize_root(resample_2x(kp), COCO_HIPS), resample_2x(conf)[..., None]], -1)
        seqs.append({"id": f"{group}-{key}", "x2d": x2d.astype(np.float32), "y3d": (resample_2x(Y) / 1000).astype(np.float32)})
    return seqs


def kinect_joint_weights(keys):
    """min(1, (30 / e_j)^2) with e_j the mean root-relative Kinect-vs-Vicon error of joint j on these G3 recordings."""
    E = []
    for k in keys:
        g = np.load(f"{CALIB}/gt3d/{k}.npz")
        v, c = g["vicon"], g["kinect"]
        E.append(np.linalg.norm((v - v[:, 16:17]) - (c - c[:, 16:17]), axis=-1))
    e = np.nanmean(np.concatenate(E), 0)
    w = np.where(np.isfinite(e), np.minimum(1, (30 / np.maximum(e, 1e-6)) ** 2), 1.0)
    return w.astype(np.float32)


def rehab_split(path, val, test):
    """REHAB24-6 npz -> (train, val, test) sequence lists, split by person (never by frame)."""
    d = np.load(path)
    ends = list(d["starts"][1:]) + [len(d["y3d"])]
    val, test = {int(p) for p in val.split(",")}, {int(p) for p in test.split(",")}
    out = ([], [], [])
    for s, e, i, p in zip(d["starts"], ends, d["ids"], d["person"]):
        q = {"id": str(i), "x2d": d["x2d"][s:e], "y3d": d["y3d"][s:e]}
        out[1 if p in val else 2 if p in test else 0].append(q)
    return out


def loss_fn(P, Y, noisy, w):
    """Mean joint error; samples with a Kinect target weigh joint j by w[j]."""
    m = (~torch.isnan(Y[..., 0])).float()
    W = torch.where(noisy[:, None, None] > 0.5, w[None, None], torch.ones_like(w)[None, None]) * m
    e = torch.linalg.norm(P - torch.nan_to_num(Y), dim=-1)
    return (e * W).sum() / W.sum().clamp(min=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--train-parts", required=True)
    ap.add_argument("--eval-parts", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--epochs", type=int, default=120)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--keraal-share", type=float, default=0.5)
    ap.add_argument("--flag", action="store_true")
    ap.add_argument("--kinect", default="")
    ap.add_argument("--kweight", action="store_true")
    ap.add_argument("--no-keraal", action="store_true", help="train/select without any KERAAL data (G3 only used as test)")
    ap.add_argument("--rehab24", default="", help="REHAB24-6 npz from rehab24/export.py")
    ap.add_argument("--rehab-val", default="3")
    ap.add_argument("--rehab-test", default="1,2")
    ap.add_argument("--g3-det", default=G3_DET, help="folder with the G3 2D detections (e.g. the crop detections)")
    ap.add_argument("--rehab-frac", type=float, default=1.0, help="keep this share of REHAB24 training recordings")
    a = ap.parse_args()
    os.makedirs(a.run, exist_ok=True)
    json.dump({**vars(a), "input": "det", "norm": "root"}, open(os.path.join(a.run, "args.json"), "w"), indent=1)  # keraal_eval reads norm
    torch.manual_seed(a.seed)
    rng = np.random.default_rng(a.seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    make = (lambda j, c: FlagTCN(j, c)) if a.flag else (lambda j, c: TCN(j, c))
    model = make(17, 3).to(dev)

    keys = sorted(os.path.basename(f)[:-4] for f in glob.glob(os.path.join(CALIB, "gt3d", "*.npz")))
    part = lambda k: k.split("-")[1][:2]
    tr_parts, ev_parts = a.train_parts.split(","), [p for p in a.eval_parts.split(",") if p]
    assert not set(tr_parts) & set(ev_parts), "evaluation participant must never be trained on"
    tr_keys = [k for k in keys if part(k) in tr_parts]
    F = lambda s, d, n: with_flags(s, d, n, a.flag)
    ktr = F(keraal_seqs(a.g3_det, CALIB, [k for i, k in enumerate(tr_keys) if i % 5], "vicon"), 1, 0)
    kval = F(keraal_seqs(a.g3_det, CALIB, tr_keys[0::5], "vicon"), 1, 0)
    atr = F(load_split(ASP, "train", "det", ASP_DET), 0, 0)
    aval = F(load_split(ASP, "val", "det", ASP_DET), 0, 0)
    kin = F(sum((kinect_seqs(g) for g in a.kinect.split(",") if g), []), 1, 1)
    if a.no_keraal:
        assert not kin, "--no-keraal with --kinect makes no sense"
        ktr, kval = [], []
    r_tr, r_val, r_test = rehab_split(a.rehab24, a.rehab_val, a.rehab_test) if a.rehab24 else ([], [], [])
    r_tr = r_tr[::max(1, round(1 / a.rehab_frac))] if a.rehab_frac < 1 else r_tr
    r_tr, r_val, r_test = (F(s, 1, 0) for s in (r_tr, r_val, r_test))   # REHAB24 has its own skeleton; flag 1 = "not ASPset"
    nk, na, nn = (sum(len(q["y3d"]) for q in s) for s in (ktr, atr, kin))
    rep = max(1, round(a.keraal_share * na / ((1 - a.keraal_share) * nk))) if a.keraal_share and nk else 1
    tr = ktr * rep + atr + kin + r_tr
    print(f"REHAB24 train {sum(len(q['y3d']) for q in r_tr)} frames / val {len(r_val)} / test {len(r_test)} views", flush=True)
    w = torch.from_numpy(kinect_joint_weights(tr_keys) if a.kweight else np.ones(17, np.float32)).to(dev)
    print(f"G3 frames {nk} x{rep}, ASPset {na}, Kinect-target {nn} ({len(kin)} recordings); joint weights {np.round(w.cpu().numpy(), 2).tolist()}", flush=True)
    strip = lambda X: X[..., :-1]                       # drop the noisy-target channel before the model
    for s in (kval, aval, r_val, r_test):
        for q in s:
            q["x2d"] = strip(q["x2d"])

    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.ExponentialLR(opt, 0.95 ** (60 / a.epochs))
    best, log = (1e9, -1), []
    for ep in range(a.epochs):
        model.train()
        for X, Y in train_lift.batches(tr, model.rf, 128, 64, "det", rng):
            X, Y = X.to(dev), Y.to(dev)
            loss = loss_fn(model(strip(X)), Y, X[:, 0, 0, -1], w)
            opt.zero_grad(); loss.backward(); opt.step()
        sched.step()
        av = evaluate(model, aval, dev, "det", tta=False)[0]["mpjpe"]
        log.append({"epoch": ep + 1, "val_aspset": av})
        if kval:
            log[-1]["val_keraal"] = eval_keraal(model, kval, dev)["mpjpe"]
        if r_val:
            log[-1]["val_rehab24"] = eval_keraal(model, r_val, dev)["mpjpe"]
        if (ep + 1) % 20 == 0:
            print(json.dumps(log[-1]), flush=True)
        score = float(np.mean([v for k, v in log[-1].items() if k.startswith("val_")]))
        if score < best[0]:
            best = (score, ep + 1)
            torch.save(model.state_dict(), os.path.join(a.run, "best.pt"))
    json.dump(log, open(os.path.join(a.run, "log.json"), "w"))
    model.load_state_dict(torch.load(os.path.join(a.run, "best.pt"), map_location=dev))
    model.eval()
    if not ev_parts:
        return

    atest = F(load_split(ASP, "test", "det", ASP_DET), 0, 0)
    for q in atest:
        q["x2d"] = strip(q["x2d"])
    asp = {k: v for k, v in evaluate(model, atest, dev, "det")[0].items() if k in ("mpjpe", "pa_mpjpe")}
    rehab = {k: v for k, v in eval_keraal(model, r_test, dev).items() if k in ("mpjpe", "pa_mpjpe")} if r_test else None
    print("REHAB24 test", rehab, flush=True)
    train_lift.TCN = make                               # keraal_eval builds TCN(17, 3) itself; FlagTCN appends flag 1
    tmp = os.path.join(a.run, "angles_all.json")
    keraal_eval.evaluate(G3, a.g3_det, a.run, tmp)
    rows = json.load(open(tmp))["rows"]
    os.remove(tmp)
    for ev in ev_parts:
        test = keraal_seqs(a.g3_det, CALIB, [k for k in keys if part(k) == ev], "vicon")
        if a.flag:
            test = [dict(q, x2d=np.concatenate([q["x2d"], np.ones(q["x2d"].shape[:2] + (1,), np.float32)], -1)) for q in test]
        out = {"args": vars(a), "best_epoch": best[1], "val_keraal_same_people": log[best[1] - 1].get("val_keraal"),
               "unseen": eval_keraal(model, test, dev), "aspset_test": asp, "rehab24_test": rehab,
               "angles": angle_summary([r for r in rows if r["participant"] == ev])}
        res = os.path.join(os.path.dirname(a.run), f"{''.join(tr_parts)}_{ev}_s{a.seed}")
        os.makedirs(res, exist_ok=True)
        json.dump(out, open(os.path.join(res, "results.json"), "w"), indent=1)
        print("RESULT", ev, json.dumps({"mpjpe": out["unseen"]["mpjpe"], **out["angles"]}), flush=True)


def _check():
    m = FlagTCN(17, 3, widths=(3, 3), ch=32).eval()
    x = torch.rand(2, 9, 17, 3)
    p1 = m(x)
    p2 = m(torch.cat([x, torch.ones_like(x[..., :1])], -1))
    assert torch.allclose(p1, p2) and p1.shape == (2, 1, 17, 3)
    assert not torch.allclose(p1, m(torch.cat([x, torch.zeros_like(x[..., :1])], -1)))
    assert set(m.state_dict()) == set(TCN(17, 4, widths=(3, 3), ch=32).state_dict())
    P, Y = torch.zeros(2, 4, 17, 3), torch.zeros(2, 4, 17, 3)
    Y[..., 0] = 1.0                                      # every joint 1 m off
    Y[0, :, 12] = float("nan")
    w = torch.full((17,), 0.1)
    assert abs(loss_fn(P, Y, torch.tensor([0.0, 1.0]), w).item() - 1.0) < 1e-6   # uniform error: weights do not change the mean
    Y[1, :, 3] = 11.0                                    # big error on a down-weighted Kinect joint barely counts
    assert loss_fn(P, Y, torch.tensor([0.0, 1.0]), w) < loss_fn(P, Y, torch.tensor([0.0, 0.0]), w)
    assert resample_2x(np.arange(3.0)[:, None]).ravel().tolist() == [0, .5, 1, 1.5, 2]
    s = with_flags([{"x2d": np.zeros((4, 17, 3), np.float32)}], 1, 1, True)
    assert s[0]["x2d"].shape == (4, 17, 5) and s[0]["x2d"][..., 3:].min() == 1
    print("km_train --check OK")


if __name__ == "__main__":
    _check() if sys.argv[1:] == ["--check"] else main()
