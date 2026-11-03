"""Aggregates E:/KERAAL_mocap3d/acc_loop into TABLE.md: inner pairs per condition, nested choice per outer participant.
Nested rule: for outer participant Pk, take the condition with the lowest unseen MPJPE over the two pairs that do not
involve Pk; it must beat base by at least 2 mm (about the seed noise), otherwise base stays.
Usage: python report.py    python report.py --check"""
import glob
import json
import os
import sys

import numpy as np

OUT = "E:/KERAAL_mocap3d/acc_loop"
PARTS = ("P1", "P2", "P3")
MIN_GAIN = 2.0


def load():
    res = {}
    for f in glob.glob(f"{OUT}/*/*/results.json"):
        cond, run = f.replace("\\", "/").split("/")[-3:-1]
        if not cond.startswith("_"):
            res.setdefault(cond, {})[run] = json.load(open(f))
    return res


def nested(mpjpe):
    """mpjpe: {cond: {(train, eval): mm}} on complete single-participant pairs -> {outer: chosen cond}."""
    out = {}
    for k in PARTS:
        pair = [(a, b) for a in PARTS for b in PARTS if a != b and k not in (a, b)]
        full = {c: np.mean([v[p] for p in pair]) for c, v in mpjpe.items() if all(p in v for p in pair)}
        if "base" not in full:
            continue
        c = min(full, key=full.get)
        out[k] = c if full["base"] - full[c] >= MIN_GAIN else "base"
    return out


def main():
    res = load()
    lines = ["| 조건 | 완료 | 새 참가자 MPJPE | base 대비 | 나아진 쌍 | 각도 r0 | 각도 RMSE | RTK r0 | ASPset MPJPE |",
             "|---|---|---|---|---|---|---|---|---|"]
    inner = {c: {tuple(r.split("_")[:2]): v for r, v in runs.items() if r.endswith("_s0") and len(r.split("_")[0]) == 2}
             for c, runs in res.items()}
    mp = {c: {p: v["unseen"]["mpjpe"] for p, v in runs.items()} for c, runs in inner.items()}
    for c in sorted(inner, key=lambda c: (c != "base", np.mean(list(mp[c].values())) if mp[c] else 1e9)):
        runs = inner[c]
        if not runs:
            continue
        shared = [p for p in runs if p in mp.get("base", {})]
        d = [mp[c][p] - mp["base"][p] for p in shared]
        avg = lambda f: np.mean([f(v) for v in runs.values()])
        lines.append(f"| {c} | {len(runs)}/6 | {np.mean(list(mp[c].values())):.1f} | "
                     f"{np.mean(d) if d else float('nan'):+.1f} | {sum(x < 0 for x in d)}/{len(d)} | "
                     f"{avg(lambda v: v['angles']['r0']):.3f} | {avg(lambda v: v['angles']['rmse']):.1f} | "
                     f"{avg(lambda v: v['angles']['rtk_r0']):.3f} | {avg(lambda v: v['aspset_test']['mpjpe']):.1f} |")
    choice = nested(mp)
    lines += ["", "중첩 선택 (바깥 참가자를 쓰지 않은 쌍으로만 고름): " + (json.dumps(choice) if choice else "아직 없음")]
    outer = sorted(f"{c}/{r}" for c, runs in res.items() for r in runs if len(r.split("_")[0]) == 4)
    lines += ["", "최종 재학습(참가자 2명 학습) 결과:", "", "| 조건/실행 | MPJPE | r0 | RMSE | RTK r0 | ASPset |", "|---|---|---|---|---|---|"]
    for o in outer:
        c, r = o.split("/")
        v = res[c][r]
        lines.append(f"| {o} | {v['unseen']['mpjpe']:.1f} | {v['angles']['r0']:.3f} | {v['angles']['rmse']:.1f} | "
                     f"{v['angles']['rtk_r0']:.3f} | {v['aspset_test']['mpjpe']:.1f} |")
    text = "\n".join(lines) + "\n"
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "TABLE.md"), "w", encoding="utf-8").write(text)
    print(text)


def _check():
    pairs = [(a, b) for a in PARTS for b in PARTS if a != b]
    base = {p: 100.0 for p in pairs}
    # "a" is 5 mm better only on pairs involving P1, so it may be chosen for outer P2/P3 but never for outer P1
    a = {p: (95.0 if "P1" in p else 100.0) for p in pairs}
    assert nested({"base": base, "a": a}) == {"P1": "base", "P2": "a", "P3": "a"}
    # a gain under the noise floor keeps base
    assert nested({"base": base, "b": {p: 99.0 for p in pairs}}) == {k: "base" for k in PARTS}
    print("report --check OK")


if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:
        _check()
    else:
        main()
