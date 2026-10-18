"""L11 (exploratory): one-page summary of loop results L1-L7 for the presentation and the report.

Reads only the saved outputs of L1-L7 (and, through L7, the confirmatory prediction files); no model is refit.
  l11_summary.png  four panels, annotator A, CTK C vs E13:
                   (a) acted -> real confusion matrix, Rerr RF (L7)        -> "it calls almost everything an error"
                   (b) AUC vs Macro-F1 at 0.5 per rep x model, P1 (L1)      -> "the ranking survives, the cut-off fails"
                   (c) P(E13) quartiles by set and class, Rerr RF (L2)      -> "real 'correct' sits where acted errors sit"
                   (d) Macro-F1 real -> real vs acted -> real (L7)          -> "only the acted -> real step breaks"
  l11_summary.md   the key messages with their numbers and caveats (KR / EN), plus every number in the figure.
Usage: python explore/loop/l11_summary.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from l7_figures import LR, REPS, confusion, ladder  # noqa: E402


def rows(name):
    with (HERE / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load():
    l1 = [r for r in rows("l1_acted_to_real_auc.csv") if r["annotator"] == "A"]
    l2 = [r for r in rows("l2_probability_shift.csv") if r["annotator"] == "A" and r["model"] == "rf" and r["rep"] == "Rerr"]
    cm = confusion(ROOT)[("A", "rf")]
    f1, null = ladder(ROOT)
    return l1, l2, cm, f1, null


def plot(l1, l2, cm, f1, null, out: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    fig, ax = plt.subplots(2, 2, figsize=(12, 8.6))
    # (a) confusion
    a = ax[0, 0]
    a.imshow(cm / cm.sum(1, keepdims=True), cmap="Blues", vmin=0, vmax=1)
    for i in range(2):
        for j in range(2):
            sh = cm[i, j] / cm[i].sum()
            a.text(j, i, f"{cm[i, j]}\n({sh:.0%})", ha="center", va="center", fontsize=12,
                   color="white" if sh > 0.6 else "black")
    a.set_xticks([0, 1], ["pred correct", "pred error"]); a.set_yticks([0, 1], ["true correct", "true error"])
    a.set_title(f"(a) Acted → real, Rerr RF: {cm[:, 1].sum() / cm.sum():.0%} flagged as error "
                f"(true {cm[1].sum() / cm.sum():.0%})", fontsize=10)
    # (b) AUC vs F1
    b = ax[0, 1]
    labels = [f"{r['rep']}\n{r['model'].split('(')[0]}" for r in l1]
    x = np.arange(len(l1)); w = 0.38
    auc = [float(r["auc_pooled"]) for r in l1]; f1s = [float(r["f1_at_0.5"]) for r in l1]
    nul = [float(r["null_p95"]) for r in l1]
    b.bar(x - w / 2, auc, w, label="AUC (ranking)", color="#3b6ea5")
    b.bar(x + w / 2, f1s, w, label="Macro-F1 at 0.5 (decision)", color="#e08a3c")
    b.scatter(x - w / 2, nul, marker="_", s=300, color="k", label="AUC null 95% (within-person shuffle)", zorder=3)
    b.axhline(0.5, color="grey", lw=0.8, ls=":")
    b.set_xticks(x, labels, fontsize=8); b.set_ylim(0.2, 0.95); b.legend(fontsize=7, loc="upper right")
    b.set_title("(b) Acted → real: ranking above chance, decisions poor", fontsize=10)
    # (c) probability quartiles
    c = ax[1, 0]
    order = [("G3 (OOF)", "C"), ("G3 (OOF)", "E13"), ("1A", "C"), ("1A", "E13"), ("2A", "C"), ("2A", "E13")]
    stats, cols = [], []
    for s, k in order:
        r = next(r for r in l2 if r["set"] == s and r["class"] == k)
        q1, med, q3 = float(r["q25"]), float(r["median_p"]), float(r["q75"])
        stats.append({"label": f"{s.replace(' (OOF)', '')} {'correct' if k == 'C' else 'error'} (n={r['n']})",
                      "q1": q1, "med": med, "q3": q3, "whislo": q1, "whishi": q3})
        cols.append("#3b6ea5" if k == "C" else "#c0392b")
    bp = c.bxp(stats, orientation="horizontal", showfliers=False, patch_artist=True, widths=0.6)
    for p, col in zip(bp["boxes"], cols):
        p.set_facecolor(col); p.set_alpha(0.45)
    tg, tr = float(l2[0]["thr_youden_G3"]), float(l2[0]["thr_youden_real_oracle"])
    c.axvline(0.5, color="k", ls="--", lw=1, label="0.5")
    c.axvline(tg, color="#2e7d32", lw=1.3, label=f"best cut-off on acted data {tg:.2f}")
    c.axvline(tr, color="#8e44ad", lw=1.3, ls=":", label=f"best cut-off on real data (oracle) {tr:.2f}")
    c.set_xlim(0, 1); c.set_xlabel("P(error), box = interquartile range"); c.legend(fontsize=7, loc="upper left")
    c.set_title("(c) Real 'correct' recordings sit where acted errors sit (Rerr RF)", fontsize=10)
    # (d) ladder
    d = ax[1, 1]
    xr = np.arange(len(REPS))
    for model, mk in (("rf", "o"), (LR, "s")):
        d.plot(xr, [f1[("P4", "A", model, r)] for r in REPS], "-" + mk, color="C0",
               label=f"real → real · {model.split('(')[0]}")
        d.plot(xr, [f1[("P1", "A", model, r)] for r in REPS], "--" + mk, color="C1",
               label=f"acted → real · {model.split('(')[0]}")
    d.axhline(f1[("P4", "A", "majority", "-")], color="C0", ls=":", lw=1)
    d.axhline(f1[("P1", "A", "majority", "-")], color="C1", ls=":", lw=1)
    d.set_xticks(xr, REPS); d.set_ylim(0.2, 0.85); d.set_ylabel("Macro-F1"); d.legend(fontsize=7, loc="lower left")
    d.set_title("(d) Real → real works; acted → real breaks (dotted = majority)", fontsize=10)
    fig.suptitle("KERAAL · CTK correct vs error (E1+E3), annotator A · exploratory results L1–L7 "
                 "(the pre-registered confirmatory test is unchanged)", fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=150)


MESSAGES = """# L11 · 루프 결과 한 장 요약 (탐색) / one-page summary of L1–L7 (exploratory)

그림: `l11_summary.png` (주석자 A, CTK 정상 vs 오류 E1+E3). 사전 등록 확증 결과(H1–H3 지지 안 됨)는 그대로이고, 아래는 모두 그 뒤의 **탐색** 결과다.

## 핵심 메시지 / key messages

1. **연기 데이터로 배운 모델은 실제 녹화를 거의 다 오류로 판정한다** (L7, 그림 a). Rerr RF: 실제 정상의 89%를 오류로, 오류 판정 비율 92% vs 실제 41%.
   *The acted-trained model calls almost every real recording an error (92 % flagged vs 41 % true).*
2. **그래도 순위는 우연보다 낫다** (L1, 그림 b). Rerr AUC RF 0.674 · logreg 0.722 (참가자 안 순열 null 95% 0.629·0.673, p ≤ 0.002)인데 기준점 0.5의 Macro-F1은 0.404·0.493. 주석자 B도 같다.
   *It still ranks errors above chance; the decision cut-off is what fails.*
3. **실패의 모양은 "분포 전체의 이동"이다** (L2, 그림 c). 실제 정상의 P(오류) 중앙값 0.88로 연기 오류(0.85)보다 높다. 연기 데이터의 최적 기준점 0.55 vs 실제(oracle) 0.93.
   *Real "correct" recordings get the probabilities that acted errors get.*
4. **실제 → 실제는 된다** (L7, 그림 d). Macro-F1 0.54–0.78 vs 다수 클래스 0.33–0.36. 무너지는 것은 연기 → 실제 단계다.
   *Real-to-real works; only the acted-to-real step breaks.*
5. **카메라 보정만으로는 안 된다** (L3). 손목 높이 feature를 빼면 과잉 판정은 줄지만(92% → 82%, logreg F1 0.49 → 0.64) 실제 → 실제 성능도 같이 떨어진다.
   *Removing camera-sensitive height features trades the shift for lost information.*
6. **놓치는 것은 작은 오류** (L5, CTK). 큰 오류 recall이 더 높다(28개 조합 중 25개, 중앙값 +0.36; 큰 오류 5개뿐). ELK는 차이 없음.
7. **조심할 단서들** (L4, L6). "raw(R0)가 가장 좋다"는 RF에서만 나온다(로시니 R2 대기). 길이 단서는 사람 차이였고, G3 녹화는 실제보다 1.3–2배 짧다.

## 발표에서 쓰는 법 / how to use it in the talk
- 슬라이드 4(확증 실패): 그림 a. 슬라이드 6(원인): 그림 b·c. 슬라이드 5·7 사이: 그림 d.
- 한 문장: "연기 데이터로 배운 모델은 오류를 구분하는 능력은 남아 있지만, 판정 기준점이 실제 사람에게 맞지 않는다."
- 꼭 함께 말할 한계: 결과를 본 뒤의 탐색 분석, 시험 참가자 11명(2A 오류 4–5개), G3 3명, 1A 서서·G3 앉아서, 기준점 보정(R1)은 아직 진행 중.
"""


def write_md(l1, l2, cm, out: Path):
    lines = [MESSAGES, "## 그림의 수치 / numbers in the figure", "",
             f"(a) confusion (Rerr RF, A): true C → C {cm[0, 0]}, C → E {cm[0, 1]}, E → C {cm[1, 0]}, E → E {cm[1, 1]}", "",
             "(b) | rep | model | AUC | null 95% | p | F1@0.5 |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['rep']} | {r['model']} | {r['auc_pooled']} | {r['null_p95']} | {r['p']} | {r['f1_at_0.5']} |" for r in l1]
    lines += ["", "(c) | set | class | n | q25 | median | q75 |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['set']} | {r['class']} | {r['n']} | {r['q25']} | {r['median_p']} | {r['q75']} |" for r in l2]
    lines += ["", "(d) 수치는 `l7_figures.md`의 사다리 표(주석자 A) / see the ladder table in `l7_figures.md`."]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    l1, l2, cm, f1, null = load()
    if a.check:
        fails = []
        if len(l1) != 6 or len(l2) != 6:
            fails.append(f"expected 6 L1 and 6 L2 rows, got {len(l1)}, {len(l2)}")
        rerr_rf = next(r for r in l1 if r["rep"] == "Rerr" and r["model"] == "rf")
        if abs(float(rerr_rf["f1_at_0.5"]) - 0.404) > 0.002 or abs(cm[:, 1].sum() / cm.sum() - 0.92) > 0.02:
            fails.append("summary numbers drifted from L1 / L7")
        print("CHECK", "PASSED" if not fails else f"FAILED {fails}")
        return 1 if fails else 0
    plot(l1, l2, cm, f1, null, HERE / "l11_summary.png")
    write_md(l1, l2, cm, HERE / "l11_summary.md")
    print("wrote explore/loop/l11_summary.png, l11_summary.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
