"""L10 (exploratory): annotator A-B agreement as a ceiling for model scores.

The models are scored against one annotator. If the two physiotherapists (A, B) do not agree with each other,
no model can be expected to agree with either of them much better. So we treat annotator B as a "predictor" of
annotator A (and the reverse) on the same recordings and the same metric as the models, and put the model scores
next to it.

Recordings: the P4 set (Group 1A patients, the rec_keys in results/rf_P4_preds.csv), both labels not EXCL.
Context row: all 1A + 2A recordings with both labels.
Per exercise (CTK, ELK, RTK):
  multi-class   Cohen kappa(A, B), % agreement, Macro-F1 of B judged against A and of A judged against B
                (evaluate.macro_f1, classes of the reference annotator), participant bootstrap 95% CI for kappa,
                within-participant shuffle null 95% for kappa (B labels shuffled inside each person),
                majority-class Macro-F1;
                RF P4 models from rf_P4_preds.csv (5 seeds): Macro-F1 and kappa against the annotator they were
                trained on and kappa against the OTHER annotator, per representation.
  binary        CTK C vs E1+E3, ELK C vs E2, RTK C vs E1+E2: kappa(A, B), Macro-F1 B->A and A->B;
                model P4 Macro-F1 (Rerr): CTK from results/confirmatory_dryrun_main_binary_P4.csv (H1 rows),
                ELK and RTK from explore/loop/l12_binary_elk_rtk.csv (loop L12).
Aggregates only. Outputs: explore/loop/l10_annotator_ceiling.{csv,md}
Usage: python explore/loop/l10_annotator_ceiling.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.metrics import cohen_kappa_score

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from evaluate import bootstrap_ci, macro_f1  # noqa: E402

EXERCISES = ["CTK", "ELK", "RTK"]
BINARY = {"CTK": ("_ctk13", {"C": "C", "E13": "E"}), "ELK": ("", {"C": "C", "E2": "E"}),
          "RTK": ("", {"C": "C", "E1": "E", "E2": "E"})}
N_PERM = 2000


def kappa(a, b) -> float:
    a, b = np.asarray(a), np.asarray(b)
    if len(set(a.tolist()) | set(b.tolist())) < 2:
        return float("nan")
    return float(cohen_kappa_score(a, b))


def shuffle_null(a, b, g, n: int, seed: int = 0) -> float:
    """95th percentile of kappa(A, shuffled B), B shuffled inside each participant."""
    a, b, g = map(np.asarray, (a, b, g))
    rng = np.random.default_rng(seed)
    idx = [np.flatnonzero(g == p) for p in np.unique(g)]
    vals = []
    for _ in range(n):
        bs = b.copy()
        for i in idx:
            bs[i] = b[rng.permutation(i)]
        vals.append(kappa(a, bs))
    return float(np.nanpercentile(vals, 95))


def majority_f1(y) -> float:
    vals, cnt = np.unique(y, return_counts=True)
    return macro_f1(y, [vals[cnt.argmax()]] * len(y))


def human_rows(lab, keys, scope):
    rows = []
    for ex in EXERCISES:
        ks = [k for k in keys if lab[k]["exercise"] == ex and "EXCL" not in (lab[k]["label_A"], lab[k]["label_B"])]
        g = [lab[k]["participant_key"] for k in ks]
        for task in ("multi", "binary"):
            if task == "multi":
                a = [lab[k]["label_A"] for k in ks]
                b = [lab[k]["label_B"] for k in ks]
                kk, gg = ks, g
            else:
                suf, cmap = BINARY[ex]
                sel = [i for i, k in enumerate(ks) if lab[k]["label_A" + suf] in cmap and lab[k]["label_B" + suf] in cmap]
                kk = [ks[i] for i in sel]
                gg = [g[i] for i in sel]
                a = [cmap[lab[k]["label_A" + suf]] for k in kk]
                b = [cmap[lab[k]["label_B" + suf]] for k in kk]
            lo, hi = bootstrap_ci(a, b, gg, kappa)
            rows.append({"scope": scope, "exercise": ex, "task": task, "n": len(kk), "participants": len(set(gg)),
                         "classes_A": " ".join(f"{c}:{a.count(c)}" for c in sorted(set(a))),
                         "kappa_AB": kappa(a, b), "kappa_lo": lo, "kappa_hi": hi,
                         "kappa_null_p95": shuffle_null(a, b, gg, N_PERM),
                         "agree": float(np.mean(np.array(a) == np.array(b))),
                         "f1_B_vs_A": macro_f1(a, b), "f1_A_vs_B": macro_f1(b, a),
                         "majority_f1_A": majority_f1(a), "majority_f1_B": majority_f1(b)})
    return rows


def model_rows(root: Path, lab):
    preds = defaultdict(list)
    with (root / "results" / "rf_P4_preds.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            preds[(r["annotator"], r["exercise"], r["rep"], r["seed"])].append(r)
    rows = []
    agg = defaultdict(lambda: defaultdict(list))
    for (ann, ex, rep, seed), rs in preds.items():
        other = "B" if ann == "A" else "A"
        y = [r["y_true"] for r in rs]
        p = [r["y_pred"] for r in rs]
        ko = [(lab[r["rec_key"]]["label_" + other], r["y_pred"]) for r in rs
              if lab[r["rec_key"]]["label_" + other] != "EXCL"]
        d = agg[(ann, ex, rep)]
        d["f1"].append(macro_f1(y, p))
        d["kappa_own"].append(kappa(y, p))
        d["kappa_other"].append(kappa([t for t, _ in ko], [q for _, q in ko]))
        d["n"] = len(rs)
        d["participants"] = len({lab[r["rec_key"]]["participant_key"] for r in rs})
    for (ann, ex, rep), d in sorted(agg.items()):
        rows.append({"annotator": ann, "exercise": ex, "rep": rep, "n": d["n"], "participants": d["participants"],
                     "macro_f1": float(np.mean(d["f1"])), "kappa_own": float(np.nanmean(d["kappa_own"])),
                     "kappa_other": float(np.nanmean(d["kappa_other"])), "seeds": len(d["f1"])})
    return rows


def binary_model(root: Path):
    out = {}
    with (root / "results" / "confirmatory_dryrun_main_binary_P4.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["hypothesis"] == "H1":
                ex, _, _, _, ann = r["task"].split("_")
                out[(ex, ann, r["model"])] = (float(r["observed"]), float(r["null_p95"]), int(r["participants"]))
    l12 = HERE / "l12_binary_elk_rtk.csv"  # ELK and RTK binary P4 scores (loop L12), Rerr rows
    if l12.exists():
        with l12.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["rep"] == "Rerr":
                    out[(r["exercise"], r["annotator"], r["model"])] = (float(r["macro_f1"]), float(r["null_p95"]),
                                                                        int(r["participants"]))
    return out


def run(root: Path):
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        lab = {r["rec_key"]: r for r in csv.DictReader(f)}
    with (root / "results" / "rf_P4_preds.csv").open(encoding="utf-8") as f:
        p4 = sorted({r["rec_key"] for r in csv.DictReader(f)})
    allk = sorted(k for k in lab if lab[k]["group"] in ("1A", "2A"))
    return human_rows(lab, p4, "P4 (1A)") + human_rows(lab, allk, "1A+2A"), model_rows(root, lab), binary_model(root)


def f(x, d=2):
    return "—" if x != x else f"{x:.{d}f}"


def write(human, models, binm, out: Path):
    with (out.with_suffix(".csv")).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(human[0]))
        w.writeheader(); w.writerows(human)
    with (out.parent / (out.name + "_models.csv")).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(models[0]))
        w.writeheader(); w.writerows(models)
    L = ["# L10 · 주석자 A·B 일치도를 모델 성능 상한으로 (탐색) / annotator agreement as a ceiling (exploratory)", "",
         "주석자 B를 A의 \"예측\"으로 보고(반대도) 모델과 같은 녹화·같은 지표로 채점했다. 모델 점수가 이 값에 가까우면 "
         "더 올릴 여지가 작다. κ 95% CI = 참가자 bootstrap, null p95 = 참가자 안에서 B 라벨 섞기 2000회.",
         "Annotator B is scored as a \"prediction\" of A (and vice versa) on the same recordings and metric as the models.",
         "", "## 1. 사람 사이 일치 / human agreement", "",
         "| 범위 scope | 운동 | 과제 | n (사람) | A 클래스 | κ(A,B) [95% CI] | κ null p95 | 일치율 | Macro-F1 B→A | Macro-F1 A→B | 다수 클래스 F1 (A / B) |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in human:
        L.append(f"| {r['scope']} | {r['exercise']} | {r['task']} | {r['n']} ({r['participants']}) | {r['classes_A']} | "
                 f"**{f(r['kappa_AB'])}** [{f(r['kappa_lo'])}, {f(r['kappa_hi'])}] | {f(r['kappa_null_p95'])} | "
                 f"{f(r['agree'])} | **{f(r['f1_B_vs_A'])}** | {f(r['f1_A_vs_B'])} | "
                 f"{f(r['majority_f1_A'])} / {f(r['majority_f1_B'])} |")
    L += ["", "## 2. 다중 클래스: 모델(RF, P4, 5 seed) vs 사람 상한 / multi-class model vs human ceiling", "",
          "모델은 그 주석자의 라벨로 학습·채점(Macro-F1, κ own). κ other = 같은 예측을 다른 주석자 라벨과 비교.",
          "", "| 운동 | 주석자 | 사람 상한 Macro-F1 (다른 주석자→이 주석자) | 다수 클래스(학습 fold) | 최고 표현 | 모델 Macro-F1 | 모델 κ own | 모델 κ other | Rerr Macro-F1 | n (사람) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    hum = {(r["exercise"], r["task"]): r for r in human if r["scope"] == "P4 (1A)"}
    for ex in EXERCISES:
        for ann in ("A", "B"):
            ms = [m for m in models if m["exercise"] == ex and m["annotator"] == ann]
            best = max((m for m in ms if m["rep"] != "majority"), key=lambda m: m["macro_f1"])
            maj = next(m for m in ms if m["rep"] == "majority")
            rerr = next(m for m in ms if m["rep"] == "Rerr")
            h = hum[(ex, "multi")]
            ceil = h["f1_B_vs_A"] if ann == "A" else h["f1_A_vs_B"]
            L.append(f"| {ex} | {ann} | **{f(ceil)}** | {f(maj['macro_f1'])} | {best['rep']} | **{f(best['macro_f1'])}** | "
                     f"{f(best['kappa_own'])} | {f(best['kappa_other'])} | {f(rerr['macro_f1'])} | {best['n']} ({best['participants']}) |")
    L += ["", "## 3. 이진 과제: 모델(P4 Rerr) vs 사람 상한 / binary task", "",
          "CTK는 확증 dry-run(main_binary), ELK·RTK는 루프 L12(`l12_binary_elk_rtk.md`, 모든 표현은 그 파일)의 Rerr 값.", "",
          "| 운동 과제 | 주석자 | 사람 상한 Macro-F1 | κ(A,B) | 다수 클래스 | RF Rerr (null p95) | logreg Rerr (null p95) | 사람 수 |",
          "|---|---|---|---|---|---|---|---|"]
    for ex in EXERCISES:
        h = hum[(ex, "binary")]
        for ann in ("A", "B"):
            ceil = h["f1_B_vs_A"] if ann == "A" else h["f1_A_vs_B"]
            maj = h["majority_f1_A"] if ann == "A" else h["majority_f1_B"]
            rf = binm.get((ex, ann, "rf"))
            lg = binm.get((ex, ann, "logreg(C=0.1)"))
            fm = lambda t: "—" if t is None else f"{t[0]:.2f} ({t[1]:.2f})"  # noqa: E731
            L.append(f"| {ex} {'C vs E13' if ex == 'CTK' else 'C vs E2' if ex == 'ELK' else 'C vs E1+E2'} | {ann} | "
                     f"**{f(ceil)}** | {f(h['kappa_AB'])} | {f(maj)} | {fm(rf)} | {fm(lg)} | {h['participants']} |")
    L += ["", "*탐색 결과. 확증 설정·결과는 바꾸지 않았다. 집계값만 저장.* / *Exploratory; aggregates only.*", ""]
    out.with_suffix(".md").write_text("\n".join(L), encoding="utf-8")


def check() -> list[str]:
    errs = []
    if abs(kappa(list("aabb"), list("aabb")) - 1) > 1e-9:
        errs.append("kappa identical != 1")
    if abs(kappa(list("abab"), list("baba")) + 1) > 1e-9:
        errs.append("kappa reversed != -1")
    a = list("aaaabbbbcc") * 5
    g = [str(i // 10) for i in range(50)]
    if shuffle_null(a, a, g, 200) >= 0.6:
        errs.append("shuffle null too high for unclustered labels")
    if abs(majority_f1(list("aaab")) - (2 * 0.75 / 1.75) / 2) > 1e-9:
        errs.append("majority F1 wrong")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        e = check()
        print("CHECK FAILED: " + "; ".join(e) if e else "CHECK PASSED")
        return 1 if e else 0
    human, models, binm = run(ROOT)
    write(human, models, binm, HERE / "l10_annotator_ceiling")
    sys.stdout.reconfigure(encoding="utf-8")
    print((HERE / "l10_annotator_ceiling.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
