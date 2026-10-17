"""Day 4 - learn one threshold per exercise and evaluate it.

Rule: a repetition is an ERROR if its peak value < threshold.
 - threshold = value maximizing balanced accuracy on the calibration groups (config.CAL_GROUPS)
 - leave-one-participant-out (LOSO) evaluation: threshold from the other participants
 - AUC of the single peak value (threshold-free; comparable to the team's AUC)
 - Group 3 (acted) evaluated separately with the calibration threshold

Outputs: thresholds.json, results.csv, plots/dist_<EX>.png
    python calibrate.py
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score
import config as C


def best_threshold(v, y):
    """y=1 error. predict error if v < thr. returns thr, balanced accuracy"""
    v = np.asarray(v, float); y = np.asarray(y, int)
    if y.min() == y.max():
        return np.nan, np.nan
    u = np.unique(v)
    cands = np.concatenate([[u[0] - 1e-6], (u[:-1] + u[1:]) / 2, [u[-1] + 1e-6]])
    best = (-1, np.nan)
    for t in cands:
        p = v < t
        tpr = (p & (y == 1)).sum() / (y == 1).sum()
        tnr = (~p & (y == 0)).sum() / (y == 0).sum()
        ba = (tpr + tnr) / 2
        if ba > best[0]:
            best = (ba, t)
    return best[1], best[0]


def scores(y, p):
    y = np.asarray(y, int); p = np.asarray(p, bool)
    tp = (p & (y == 1)).sum(); tn = (~p & (y == 0)).sum(); fp = (p & (y == 0)).sum(); fn = (~p & (y == 1)).sum()
    sens = tp / max(tp + fn, 1); spec = tn / max(tn + fp, 1)
    prec = tp / max(tp + fp, 1); f1 = 2 * prec * sens / max(prec + sens, 1e-9)
    return dict(sens=sens, spec=spec, bal_acc=(sens + spec) / 2, f1=f1)


def auc(y, v):
    y = np.asarray(y, int)
    return roc_auc_score(y, -np.asarray(v)) if 0 < y.sum() < len(y) else np.nan


def main():
    out = C.OUT_DIR
    mode = getattr(C, "LABEL_MODE", "rep")
    if mode == "recording":
        lab = pd.read_csv(out / "recs.csv", dtype={"group": str})
        lab = lab[lab["evaluation"].isin(C.POSITIVE_EVAL + C.NEGATIVE_EVAL)].copy()
        lab["y"] = lab["evaluation"].isin(C.POSITIVE_EVAL).astype(int)
        lab["value_offline_p95"] = lab["exc_p95"]
        lab["value"] = lab[getattr(C, "REC_FEATURE", "max_rep_value")]
        lab["error_type"] = np.nan; lab["body_part"] = np.nan
        unit = "recordings"
    else:
        reps = pd.read_csv(out / "reps.csv", dtype={"group": str})
        lab = reps[reps["label_known"] == True].copy()
        lab["y"] = lab["label_error"].astype(float).astype(int)
        unit = "reps"
    print(f"label mode: {mode}  ({len(lab)} labelled {unit})")
    lab["group"] = lab["group"].astype(str)
    has_group = lab["group"].isin(C.CAL_GROUPS).any()
    cal = lab[lab["group"].isin(C.CAL_GROUPS)] if has_group else lab
    acted = lab[lab["group"].isin(["3", "G3"])] if (has_group and getattr(C, "EVAL_G3", False)) else lab.iloc[0:0]

    res, thr_out = [], {}
    for ex, d in cal.groupby("exercise"):
        thr, ba_in = best_threshold(d["value"], d["y"])
        # LOSO
        preds = pd.Series(index=d.index, dtype=bool)
        for p, dp in d.groupby("participant"):
            tr = d[d["participant"] != p]
            t, _ = best_threshold(tr["value"], tr["y"])
            preds.loc[dp.index] = dp["value"] < (t if np.isfinite(t) else thr)
        s = scores(d["y"], preds)
        row = dict(exercise=ex, participants=d["participant"].nunique(), n=len(d), n_error=int(d["y"].sum()),
                   AUC=auc(d["y"], d["value"]),
                   AUC_offline_p95=(auc(d["y"], d["value_offline_p95"]) if "value_offline_p95" in d else np.nan),
                   threshold=thr, bal_acc_in_sample=ba_in,
                   **{f"LOSO_{k}": v for k, v in s.items()})
        a = acted[acted["exercise"] == ex]
        if len(a):
            sa = scores(a["y"], a["value"] < thr)
            row.update(G3_reps=len(a), G3_AUC=auc(a["y"], a["value"]), G3_bal_acc=sa["bal_acc"])
        # per-participant optimal threshold spread (the "baseline differs" question)
        per_p = [best_threshold(dp["value"], dp["y"])[0] for _, dp in d.groupby("participant")]
        per_p = [t for t in per_p if np.isfinite(t)]
        row["thr_per_participant_sd"] = float(np.std(per_p)) if len(per_p) > 1 else np.nan
        if "group" in d:
            for gname, dg in d.groupby("group"):
                row[f"thr_group_{gname}"] = best_threshold(dg["value"], dg["y"])[0]
        res.append(row)

        err = d[d["y"] == 1]
        sugg_type = err["error_type"].dropna().astype(str).value_counts().head(3).to_dict()
        sugg_part = err["body_part"].dropna().astype(str).value_counts().head(3).to_dict()
        thr_out[ex] = dict(threshold=float(thr), label_mode=mode, feature=C.EXERCISES[ex].get("feature", "excursion"),
                           signal=C.EXERCISES[ex]["signal"], suggested_error_types=sugg_type, suggested_body_parts=sugg_part)

        fig, ax = plt.subplots(figsize=(5, 2.8))
        bins = np.linspace(d["value"].min(), d["value"].max(), 25)
        ax.hist(d.loc[d.y == 0, "value"], bins=bins, alpha=0.6, label=f"correct {unit}", color="#457b9d")
        ax.hist(d.loc[d.y == 1, "value"], bins=bins, alpha=0.6, label=f"error {unit}", color="#e63946")
        ax.axvline(thr, color="k", ls="--", lw=1, label=f"thr = {thr:.1f}")
        ax.set_title(f"{ex}: peak {C.EXERCISES[ex]['signal']} ({C.EXERCISES[ex].get('feature')})  AUC={row['AUC']:.2f}", fontsize=9)
        ax.set_xlabel("deg"); ax.legend(fontsize=7)
        fig.tight_layout(); (out / "plots").mkdir(exist_ok=True)
        fig.savefig(out / "plots" / f"dist_{ex}.png", dpi=130); plt.close(fig)

    r = pd.DataFrame(res)
    r.to_csv(out / "results.csv", index=False)
    (out / "thresholds.json").write_text(json.dumps(thr_out, indent=2, ensure_ascii=False), encoding="utf-8")
    pd.set_option("display.width", 200)
    print(r.round(3).T.to_string())
    print("\nSuggested error codes / body parts among error reps (fill config.ERROR_CODE_MAP):")
    for ex, v in thr_out.items():
        print(f"  {ex}: types={v['suggested_error_types']}  parts={v['suggested_body_parts']}")
    print(f"\nsaved thresholds.json, results.csv, plots/dist_*.png in {out}")
    print("AUC < 0.5 means errors have LARGER peaks -> the rule direction or signal choice is wrong for that exercise.")


if __name__ == "__main__":
    main()
