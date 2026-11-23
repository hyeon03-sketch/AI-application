"""Runs the whole comparison on a new machine (Windows or Linux, one NVIDIA GPU). Every step is skipped when its output
already exists, and training continues from last.pt, so the script can be stopped and started again.

  python run_all.py --stages check                 # 1 min: packages, GPU, data files
  python run_all.py --stages smoke                 # 2-3 min: 20 batches of each model, prints the speed
  python run_all.py                                # everything below, seeds 0 1 2
  python run_all.py --seeds 0 --m3d-epochs 30      # the short version that was run on the MacBook

Stages (in order):
  vp3d_public   VideoPose3D fine-tuned on ASPset + REHAB24-6, then ASPset test and VIDIMU, before and after
  vp3d_keraal   VideoPose3D, 3 KERAAL folds (test participant left out), prediction on the fold's test set
  m3d_keraal    Mocap3D from scratch, 3 KERAAL folds
  m3d_all       Mocap3D deployment model (all 3 participants) + ASPset test and VIDIMU; these are the demo weights
  summary       KERAAL metrics for every model and seed -> runs/SUMMARY.md and runs/summary.json
  demo          demo video with the deployment model (seed 0)

Layout expected (as in the zip): <root>/vp3d_public (this folder), <root>/code_1118, <root>/VideoPose3D, <root>/data."""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PUB = os.path.join(ROOT, "data", "Mocap3D_preprocessed_1118")
KER = os.path.join(ROOT, "data", "Mocap3D_preprocessed_KERAAL_1118")
RUNS = os.path.join(HERE, "runs")
PY = sys.executable
ENV = dict(os.environ, PYTHONUTF8="1", PYTORCH_ENABLE_MPS_FALLBACK="1")
FOLDS = ("P1", "P2", "P3")
ALL = ("check", "vp3d_public", "vp3d_keraal", "m3d_keraal", "m3d_all", "summary", "demo")


def run(args, log=None, cwd=HERE):
    print(">", " ".join(str(a) for a in args), flush=True)
    t0 = time.time()
    if log:
        with open(log, "a", encoding="utf-8") as f:
            rc = subprocess.call([PY, "-u"] + [str(a) for a in args], cwd=cwd, env=ENV, stdout=f, stderr=subprocess.STDOUT)
    else:
        rc = subprocess.call([PY, "-u"] + [str(a) for a in args], cwd=cwd, env=ENV)
    print(f"  {'ok' if rc == 0 else 'FAILED (' + str(rc) + ')'} in {(time.time() - t0) / 60:.1f} min" + (f", log {log}" if log else ""), flush=True)
    if rc != 0:
        sys.exit(rc)


def trained(out, epochs):
    h = os.path.join(out, "history.json")
    if not os.path.exists(h):
        return False
    return sum(1 for x in json.load(open(h)) if isinstance(x["epoch"], int)) >= epochs


def train(script, out, epochs, extra):
    os.makedirs(out, exist_ok=True)
    if trained(out, epochs):
        print("  already trained:", out)
        return
    run([script, "train", "--data", PUB, KER, "--out", out, "--epochs", epochs] + extra, log=os.path.join(out, "train.log"))


def infer(script, data, inp, out, ckpt=None, ids=None, extra=()):
    if os.path.exists(out):
        return
    a = [script, "infer", "--data", data, "--in", inp, "--out", out] + list(extra)
    a += ["--ckpt", ckpt] if ckpt else []
    a += ["--ids", ids] if ids else []
    run(a)


def public_eval(script, ckpt, ev, tag, flags=((), ())):
    """ASPset test + VIDIMU with the bundle's own scripts -> metrics_pos_<tag>.json, vidimu_metrics_<tag>.json"""
    os.makedirs(ev, exist_ok=True)
    a, v = os.path.join(ev, f"aspset_pred3d_{tag}.npz"), os.path.join(ev, f"vidimu_pred3d_{tag}.npz")
    infer(script, PUB, "aspset_kp2d_coco.npz", a, ckpt, "aspset:test", flags[0])
    infer(script, PUB, "vidimu_kp2d_coco.npz", v, ckpt, None, flags[1])
    if not os.path.exists(os.path.join(ev, f"metrics_pos_{tag}.json")):
        run([os.path.join(PUB, "compute_metrics.py"), "--pred", a, "--gt", os.path.join(PUB, "aspset_gt3d.npz"),
             "--out", os.path.join(ev, f"metrics_pos_{tag}.json")])
    if not os.path.exists(os.path.join(ev, f"vidimu_metrics_{tag}.json")):
        run([os.path.join(PUB, "vidimu_eval.py"), "--pred", v, "--imu", os.path.join(PUB, "vidimu_imu_angles.npz"),
             "--out", os.path.join(ev, f"vidimu_metrics_{tag}.json")])


def check():
    import importlib
    ok = True
    for m in ("numpy", "scipy", "sklearn", "torch", "cv2", "ultralytics", "matplotlib"):
        try:
            v = getattr(importlib.import_module(m), "__version__", "?")
            print(f"  {m:12s} {v}")
        except Exception as e:                                     # noqa: BLE001
            ok = False
            print(f"  {m:12s} MISSING ({e})")
    import torch
    if torch.cuda.is_available():
        p = torch.cuda.get_device_properties(0)
        print(f"  GPU: {p.name}, {p.total_memory / 2**30:.0f} GB, CUDA {torch.version.cuda}")
    else:
        print("  GPU: CUDA NOT AVAILABLE -> training would run on the CPU. Install the CUDA build of torch (README step 2).")
        ok = ok and (torch.backends.mps.is_available() if hasattr(torch.backends, "mps") else False)
    need = [os.path.join(PUB, f) for f in ("splits.json", "aspset_kp2d_coco.npz", "aspset_gt3d.npz", "rehab24_kp2d_coco.npz",
                                           "rehab24_gt3d.npz", "vidimu_kp2d_coco.npz", "vidimu_imu_angles.npz",
                                           "compute_metrics.py", "vidimu_eval.py")]
    need += [os.path.join(KER, f) for f in ("splits.json", "keraal_g3_kp2d_coco.npz", "keraal_g3_gt3d.npz",
                                            "keraal_g3_kinect3d.npz", "keraal_kinect_kp2d_coco.npz", "keraal_kinect_gt3d.npz")]
    need += [os.path.join(ROOT, "VideoPose3D", "checkpoint", "pretrained_h36m_detectron_coco.bin"),
             os.path.join(ROOT, "VideoPose3D", "common", "model.py"), os.path.join(ROOT, "code_1118", "train_lift.py"),
             os.path.join(ROOT, "code_1118", "kinect_merge", "demo_rehab.py")]
    for f in need:
        if not os.path.exists(f):
            ok = False
            print("  MISSING FILE:", f)
    print("  files:", "all present" if all(os.path.exists(f) for f in need) else "see above")
    # the evaluation script must reproduce our model's published VIDIMU numbers (r 0.91, 8.84 deg)
    out = os.path.join(RUNS, "_check_vidimu.json")
    os.makedirs(RUNS, exist_ok=True)
    run([os.path.join(PUB, "vidimu_eval.py"), "--pred", os.path.join(PUB, "ours", "vidimu_pred3d.npz"),
         "--imu", os.path.join(PUB, "vidimu_imu_angles.npz"), "--out", out])
    v = json.load(open(out))["no_walking_A04_A13"]
    good = v["r"] == 0.91 and abs(v["mean_removed_rmse_deg"] - 8.84) < 0.01
    print(f"  VIDIMU check: r {v['r']}, {v['mean_removed_rmse_deg']} deg ->", "matches 0.91 / 8.84" if good else "DOES NOT MATCH 0.91 / 8.84")
    print("CHECK", "PASSED" if ok and good else "FAILED")
    if not (ok and good):
        sys.exit(1)


def smoke():
    for name, script, extra in (("VideoPose3D", "vp3d_ft.py", ["--train", "aspset:train", "rehab24:train", "--val", "rehab24:val"]),
                                ("Mocap3D", "mocap3d_ft.py", ["--fold", "P1"])):
        out = os.path.join(RUNS, "_smoke_" + name)
        if os.path.exists(os.path.join(out, "last.pt")):
            os.remove(os.path.join(out, "last.pt"))
        os.makedirs(out, exist_ok=True)
        t0 = time.time()
        run([script, "train", "--data", PUB, KER, "--out", out, "--epochs", 1, "--max-batches", 20] + extra,
            log=os.path.join(out, "train.log"))
        print(f"  {name}: 20 batches + validation in {time.time() - t0:.0f} s (includes loading the data)")
    print("Read runs/_smoke_*/train.log: the loss must be a number (not nan) and the device must be cuda.")


def summary(seeds):
    sys.path.insert(0, HERE)
    import numpy as np
    from keraal_metrics import evaluate
    rows, lines = {}, []

    def one(name, files):
        pred = {}
        for f in files:
            z = np.load(f)
            pred.update({k: z[k] for k in z.files})
        return evaluate(pred, name)[0]

    rows["Kinect depth sensor"] = [one("Kinect", [os.path.join(KER, "keraal_g3_kinect3d.npz")])]
    b = os.path.join(RUNS, "keraal_before_pred3d.npz")
    if os.path.exists(b):
        rows["VideoPose3D, before fine-tuning"] = [one("VP3D_before", [b])]
    for label, pat in (("VideoPose3D, fine-tuned", "keraal_test_{}_s{}"), ("Mocap3D (ours), trained here", "m3d_test_{}_s{}")):
        for s in seeds:
            fs = [os.path.join(RUNS, pat.format(p, s), "pred_test.npz") for p in FOLDS]
            if all(os.path.exists(f) for f in fs):
                rows.setdefault(label, []).append(dict(one(label, fs), seed=s))
    lines += ["# KERAAL group 3 (540 recordings, each participant tested by the model that never saw them)", "",
              "Angle reference: Vicon JOINT POINTS from the shared bundle. Do not mix with 13.5 / 18.7 / 16.2 deg, which use",
              "Vicon segment rotations from the raw files (keraal_eval.py on the old workstation).", "",
              "| Model | Seeds | MPJPE (mm) | PA-MPJPE (mm) | Angle RMSE (deg) | Angle RMSE per participant P1 / P2 / P3 |", "|---|---|---|---|---|---|"]

    def ms(v):
        return f"{np.mean(v):.1f}" + (f" ± {np.std(v, ddof=1):.1f}" if len(v) > 1 else "")
    for label, rs in rows.items():
        bp = " / ".join(ms([r["by_participant"][p] for r in rs]) for p in FOLDS)
        lines.append(f"| {label} | {len(rs)} | {ms([r['mpjpe_mm'] for r in rs])} | {ms([r['pa_mpjpe_mm'] for r in rs])} | "
                     f"{ms([r['angle_rmse_median_deg'] for r in rs])} | {bp} |")
    lines += ["", "# Public data (ASPset test MPJPE / PA-MPJPE mm; VIDIMU without walking r / mean-removed RMSE deg)", "",
              "| Model | Run | ASPset MPJPE | ASPset PA-MPJPE | VIDIMU r | VIDIMU RMSE | ROM diff | Reps same % | Walking L-R knee r |", "|---|---|---|---|---|---|---|---|---|"]
    pub = {}
    for label, d, tag in ([("VideoPose3D, before", f"seed{seeds[0]}", "before")] + [("VideoPose3D, fine-tuned", f"seed{s}", "after") for s in seeds]
                          + [("Mocap3D (ours), trained here", f"m3d_all_s{s}", "after") for s in seeds]):
        ev = os.path.join(RUNS, d, "eval")
        a, v = os.path.join(ev, f"metrics_pos_{tag}.json"), os.path.join(ev, f"vidimu_metrics_{tag}.json")
        if not os.path.exists(a):                                # files written by the MacBook run of Mocap3D have no tag
            a, v = os.path.join(ev, "metrics_pos.json"), os.path.join(ev, "vidimu_metrics.json")
        if not (os.path.exists(a) and os.path.exists(v)):
            continue
        p, w = json.load(open(a))["position"]["summary"], json.load(open(v))
        nw = w["no_walking_A04_A13"]
        mp = "–" if tag == "before" else f"{p['mpjpe_mm']['mean']:.1f}"
        lines.append(f"| {label} | {d} | {mp} | {p['pa_mpjpe_mm']['mean']:.1f} | {nw['r']} | {nw['mean_removed_rmse_deg']} | "
                     f"{nw['rom_diff_deg']} | {nw['reps_same_pct']} | {w['walking_left_right_knee_r']['model']} |")
        pub[f"{label} / {d}"] = {"aspset": p, "vidimu_no_walking": nw, "vidimu_all": w["all_A01_A13"], "knee": w["walking_left_right_knee_r"]}
    lines += ["", "Reference values of the original workstation model: ASPset 79.5 / 49.1 mm, VIDIMU 0.91 / 8.84 deg; "
              "KERAAL 59.9 ± 0.3 mm (3 seeds, 120 epochs)."]
    open(os.path.join(RUNS, "SUMMARY.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump({"keraal": rows, "public": pub}, open(os.path.join(RUNS, "summary.json"), "w"), indent=1)
    print("\n".join(lines))
    print("\nwritten:", os.path.join(RUNS, "SUMMARY.md"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", nargs="+", default=list(ALL), choices=ALL + ("smoke",))
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    ap.add_argument("--vp3d-epochs", type=int, default=20)
    ap.add_argument("--m3d-epochs", type=int, default=120, help="120 = original recipe; the MacBook run used 30")
    ap.add_argument("--video", default=os.path.join(ROOT, "videos", "keraal_1A_RTK_crop.mp4"))
    ap.add_argument("--video-flags", nargs="*", default=["--clean", "--squeeze", "--fps", "15"],
                    help="for your own phone / webcam video pass --video-flags with nothing after it")
    a = ap.parse_args()
    os.makedirs(RUNS, exist_ok=True)
    for st in a.stages:
        print(f"\n===== {st} ({time.strftime('%H:%M')}) =====", flush=True)
        if st == "check":
            check()
        elif st == "smoke":
            smoke()
        elif st == "vp3d_public":
            for s in a.seeds:
                out = os.path.join(RUNS, f"seed{s}")
                train("vp3d_ft.py", out, a.vp3d_epochs, ["--seed", s])
                public_eval("vp3d_ft.py", os.path.join(out, "best.pt"), os.path.join(out, "eval"), "after")
            public_eval("vp3d_ft.py", None, os.path.join(RUNS, f"seed{a.seeds[0]}", "eval"), "before")
            infer("vp3d_ft.py", KER, "keraal_g3_kp2d_coco.npz", os.path.join(RUNS, "keraal_before_pred3d.npz"))
        elif st == "vp3d_keraal":
            for s in a.seeds:
                for p in FOLDS:
                    out, f = os.path.join(RUNS, f"keraal_test_{p}_s{s}"), f"keraal_g3:folds/test_{p}"
                    train("vp3d_ft.py", out, a.vp3d_epochs, ["--seed", s, "--train", "aspset:train", "rehab24:train", "keraal_kinect:train",
                          f + "/train", "--val", "aspset:val", "rehab24:val", f + "/val", "--kinect-weights", f + "/kinect_joint_loss_weight_h36m"])
                    infer("vp3d_ft.py", KER, "keraal_g3_kp2d_coco.npz", os.path.join(out, "pred_test.npz"), os.path.join(out, "best.pt"), f + "/test")
        elif st == "m3d_keraal":
            for s in a.seeds:
                for p in FOLDS:
                    out = os.path.join(RUNS, f"m3d_test_{p}_s{s}")
                    train("mocap3d_ft.py", out, a.m3d_epochs, ["--seed", s, "--fold", p])
                    infer("mocap3d_ft.py", KER, "keraal_g3_kp2d_coco.npz", os.path.join(out, "pred_test.npz"), os.path.join(out, "best.pt"),
                          f"keraal_g3:folds/test_{p}/test", ["--flag", 1])
        elif st == "m3d_all":
            for s in a.seeds:
                out = os.path.join(RUNS, f"m3d_all_s{s}")
                train("mocap3d_ft.py", out, a.m3d_epochs, ["--seed", s, "--fold", "P1", "--all"])
                if not os.path.exists(os.path.join(out, "eval", "metrics_pos.json")):
                    public_eval("mocap3d_ft.py", os.path.join(out, "best.pt"), os.path.join(out, "eval"), "after", (["--flag", 0], ["--flag", 1]))
        elif st == "summary":
            summary(a.seeds)
        elif st == "demo":
            w = os.path.join(RUNS, f"m3d_all_s{a.seeds[0]}", "best.pt")
            out = os.path.join(ROOT, "demo_out")
            run(["demo_rehab.py", a.video, out, "--weights", w, "--flag"] + a.video_flags, cwd=os.path.join(ROOT, "code_1118", "kinect_merge"))
            print("demo video:", os.path.join(out, "demo.mp4"))
    print("\nall requested stages finished", time.strftime("%H:%M"))
