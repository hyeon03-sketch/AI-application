"""Days 2-3 - angles + repetition/peak extraction for every recording.

Outputs (in config.OUT_DIR):
  angles.csv                  : per-frame angles with labels
  reps.csv                    : one row per detected repetition with peak value and label
  plots/angles_<rec>.png      : angle curve, detected reps and annotated error frames (a few per exercise)

    python extract_reps.py [--plots 4]
"""
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import config as C
import skeleton as S
from kinematics import compute_angles
from rule_engine import RepEngine, feature_value


def mode(s):
    s = s.dropna().astype(str)
    s = s[s.str.strip() != ""]
    s = s[~s.str.lower().isin(C.NO_ERROR_VALUES)]
    return s.mode().iloc[0] if len(s) else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plots", type=int, default=4, help="plots per exercise")
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()

    out = C.OUT_DIR; (out / "plots").mkdir(parents=True, exist_ok=True)
    df, jmap = S.load(args.csv)
    print(f"loaded {len(df):,} frames, {df['recording'].nunique()} recordings, {len(jmap)} joints")

    ang_all, reps_all, recs_all, n_plot = [], [], [], {}
    for rec, g in S.iter_recordings(df):
        ex = g["exercise"].iloc[0]
        if ex not in C.EXERCISES:
            continue
        if C.SKIP_TRUNCATED and g["trunc_flag"].any():
            continue
        A = compute_angles(S.joints(g, jmap))
        spec = C.EXERCISES[ex]
        eng = RepEngine(ex)
        for v in A[spec["signal"]].to_numpy():
            eng.update(v)
        reps = eng.flush()

        lab = g[["participant", "group", "is_error", "in_span_ok", "error_type", "body_part"]]
        A = pd.concat([g[["recording", "participant", "exercise", "group"]], A, lab[["is_error", "in_span_ok", "error_type", "body_part"]]], axis=1)
        A["frame_i"] = np.arange(len(A))
        ang_all.append(A)

        for k, r in enumerate(reps):
            w = lab.iloc[r["start"]:r["end"] + 1]
            ws = w[w["in_span_ok"]] if C.ONLY_IN_SPAN else w
            known = len(ws) >= 0.5 * len(w)
            reps_all.append(dict(
                recording=rec, participant=g["participant"].iloc[0], group=g["group"].iloc[0], exercise=ex,
                rep=k, start=r["start"], peak_t=r["peak_t"], end=r["end"], dur_s=(r["end"] - r["start"]) / C.FPS,
                peak_exc=r["peak"], peak_raw=r["raw_peak"], rest=r["rest"], value=feature_value(r, ex),
                label_known=known, label_error=(bool(ws["is_error"].any()) if known else np.nan),
                err_frac=(ws["is_error"].mean() if known and len(ws) else np.nan),
                error_type=mode(ws["error_type"]), body_part=mode(ws.loc[ws["is_error"], "body_part"]),
                rec_has_error=bool(g["is_error"].any()),
            ))

        sig = A[spec["signal"]].to_numpy(float)
        rest0 = np.nanmedian(sig[:C.ENGINE["calib_frames"]])
        exc = np.abs(sig - rest0) if spec["symmetric"] else sig - rest0
        vals = [feature_value(r, ex) for r in reps]
        recs_all.append(dict(recording=rec, participant=g["participant"].iloc[0], group=g["group"].iloc[0], exercise=ex,
                             evaluation=str(g["evaluation"].iloc[0]), n_reps=len(reps),
                             value=(min(vals) if vals else 0.0), max_rep_value=(max(vals) if vals else 0.0),
                             exc_p95=float(np.nanpercentile(exc, 95)), dur_s=len(g) / C.FPS,
                             has_error_frames=bool(g["is_error"].any())))

        if n_plot.get(ex, 0) < args.plots:
            n_plot[ex] = n_plot.get(ex, 0) + 1
            fig, ax = plt.subplots(figsize=(9, 2.6))
            t = np.arange(len(A)) / C.FPS
            ax.plot(t, A[spec["signal"]], lw=1, color="#1d3557", label=spec["signal"])
            err = g["is_error"].to_numpy()
            ax.fill_between(t, 0, 1, where=err, transform=ax.get_xaxis_transform(), color="#e63946", alpha=0.18, label="annotated error")
            for r in reps:
                ax.axvspan(r["start"] / C.FPS, r["end"] / C.FPS, color="#a8dadc", alpha=0.35)
                ax.plot(r["peak_t"] / C.FPS, A[spec["signal"]].iloc[r["peak_t"]], "v", color="#e76f51")
            ax.set_title(f"{rec} ({ex}) - {len(reps)} reps detected", fontsize=9)
            ax.set_xlabel("time [s]"); ax.set_ylabel("deg"); ax.legend(fontsize=7, loc="upper right")
            fig.tight_layout(); fig.savefig(out / "plots" / f"angles_{str(rec).replace('/', '_')}.png", dpi=120); plt.close(fig)

    ang = pd.concat(ang_all, ignore_index=True)
    reps = pd.DataFrame(reps_all)
    ang.to_csv(out / "angles.csv", index=False)
    reps.to_csv(out / "reps.csv", index=False)
    pd.DataFrame(recs_all).to_csv(out / "recs.csv", index=False)
    print(f"saved angles.csv ({len(ang):,} rows), reps.csv ({len(reps)} reps), recs.csv ({len(recs_all)} recordings)")
    if len(reps):
        s = reps.groupby(["exercise", "group"]).agg(recordings=("recording", "nunique"), reps=("rep", "size"),
                                                   reps_per_rec=("rep", lambda x: len(x) / max(1, reps.loc[x.index, "recording"].nunique())),
                                                   labelled=("label_known", "sum"), error_reps=("label_error", "sum"))
        print(s.round(2).to_string())
        zero = set(ang["recording"].unique()) - set(reps["recording"].unique())
        print(f"recordings with 0 detected reps: {len(zero)}  (if many -> lower delta_start for that exercise)")


if __name__ == "__main__":
    main()
