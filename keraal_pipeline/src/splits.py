"""Freeze evaluation splits → data/splits.json (lists of rec_key; models filter by exercise and label later).

Protocols
  P1        train Group 3 -> test 1A and 2A (reported separately as test_1A / test_2A). Main protocol,
            same setting as Paper 2's scenario S1. Needs Group 3 skeletons to run.
  P2        leave-one-participant-out inside Group 3 (3 folds). Needs Group 3 skeletons.
  P3_group  about 80:20 split of all labeled data with whole participants on one side. 5 seeds.
  P3_random random split of the same pool whose test set has exactly the same (group, exercise, label)
            counts as P3_group for that seed, ignoring participants (Paper 2's scenario S2).
            P3_random vs P3_group therefore differs only in participant leakage.
  P4        leave-one-patient-out inside 1A (6 folds). Runs now; used to smoke-test the pipeline
            before Group 3 skeletons arrive.

Participants are identified by participant_key (group-participant-site), see index.py.

Usage:  python src/splits.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

SEEDS = [0, 1, 2, 3, 4]
TEST_FRAC = 0.2


def load(root: Path) -> list[dict]:
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def matched_random(rows: list[dict], grouped: dict, seed: int) -> dict:
    """Random split whose test set has exactly the same (group, exercise, label) counts as the grouped split,
    so the two differ only in whether participants are shared between train and test."""
    rng = random.Random(seed)
    by_key = {r["rec_key"]: r for r in rows}
    stratum = lambda r: (r["group"], r["exercise"], r["label_A"])  # noqa: E731
    need = Counter(stratum(by_key[k]) for k in grouped["test"])
    pool = defaultdict(list)
    for r in rows:
        pool[stratum(r)].append(r["rec_key"])
    test = []
    for key in sorted(need):
        ks = sorted(pool[key])
        rng.shuffle(ks)
        test += ks[: need[key]]
    ts = set(test)
    return {"train": sorted(r["rec_key"] for r in rows if r["rec_key"] not in ts), "test": sorted(test)}


def grouped_random(rows: list[dict], seed: int) -> dict:
    """Whole participants go to test until it holds about TEST_FRAC of the recordings."""
    rng = random.Random(seed)
    size = Counter(r["participant_key"] for r in rows)
    people = sorted(size)
    rng.shuffle(people)
    target, test_people, n = TEST_FRAC * len(rows), [], 0
    for p in people:
        if n >= target:
            break
        # skip a participant that would overshoot badly (Group 3 people hold 180 recordings each)
        if n + size[p] > 1.5 * target and n > 0:
            continue
        test_people.append(p)
        n += size[p]
    tp = set(test_people)
    return {"train": sorted(r["rec_key"] for r in rows if r["participant_key"] not in tp),
            "test": sorted(r["rec_key"] for r in rows if r["participant_key"] in tp),
            "test_participants": sorted(tp)}


def leave_one_out(rows: list[dict]) -> list[dict]:
    folds = []
    for p in sorted({r["participant_key"] for r in rows}):
        folds.append({"held_out": p,
                      "train": sorted(r["rec_key"] for r in rows if r["participant_key"] != p),
                      "test": sorted(r["rec_key"] for r in rows if r["participant_key"] == p)})
    return folds


def build(rows: list[dict]) -> dict:
    g = lambda *gs: [r for r in rows if r["group"] in gs]  # noqa: E731
    labeled = [r for r in rows if r["label_A"] != "EXCL"]
    return {
        "_doc": "rec_key lists. Filter by exercise and by the chosen label column (EXCL rows) at training time.",
        "P1": {"train": sorted(r["rec_key"] for r in g("3")),
               "test_1A": sorted(r["rec_key"] for r in g("1A")),
               "test_2A": sorted(r["rec_key"] for r in g("2A"))},
        "P2": leave_one_out(g("3")),
        "P3_group": (grp := {str(s): grouped_random(labeled, s) for s in SEEDS}),
        "P3_random": {str(s): matched_random(labeled, grp[str(s)], s) for s in SEEDS},
        "P4": leave_one_out(g("1A")),
    }


def check(sp: dict, rows: list[dict]) -> list[str]:
    fails = []
    pk = {r["rec_key"]: r["participant_key"] for r in rows}
    people = lambda keys: {pk[k] for k in keys}  # noqa: E731

    def disjoint(name, train, test):
        if set(train) & set(test):
            fails.append(f"{name}: recordings in both train and test")
        if people(train) & people(test):
            fails.append(f"{name}: participants in both train and test: {sorted(people(train) & people(test))}")

    p1 = sp["P1"]
    disjoint("P1/1A", p1["train"], p1["test_1A"])
    disjoint("P1/2A", p1["train"], p1["test_2A"])
    if (len(p1["train"]), len(p1["test_1A"]), len(p1["test_2A"])) != (540, 250, 51):
        fails.append(f"P1 sizes {len(p1['train'])}/{len(p1['test_1A'])}/{len(p1['test_2A'])}, expected 540/250/51")
    for name, n_folds, n_total in (("P2", 3, 540), ("P4", 6, 250)):
        folds = sp[name]
        if len(folds) != n_folds:
            fails.append(f"{name}: {len(folds)} folds, expected {n_folds}")
        tested = [k for f in folds for k in f["test"]]
        if len(tested) != n_total or len(set(tested)) != n_total:
            fails.append(f"{name}: every recording must be tested exactly once ({len(tested)} / {len(set(tested))})")
        for f in folds:
            disjoint(f"{name}/{f['held_out']}", f["train"], f["test"])
    for s, d in sp["P3_group"].items():
        disjoint(f"P3_group/{s}", d["train"], d["test"])
    leaky = 0
    by_key = {r["rec_key"]: r for r in rows}
    stratum = lambda k: (by_key[k]["group"], by_key[k]["exercise"], by_key[k]["label_A"])  # noqa: E731
    for s, d in sp["P3_random"].items():
        g = sp["P3_group"][s]
        if set(d["train"]) & set(d["test"]):
            fails.append(f"P3_random/{s}: recordings in both train and test")
        if Counter(map(stratum, d["test"])) != Counter(map(stratum, g["test"])):
            fails.append(f"P3_random/{s}: test composition differs from P3_group/{s}")
        frac = len(g["test"]) / (len(g["test"]) + len(g["train"]))
        if not 0.15 <= frac <= 0.30:
            fails.append(f"P3_group/{s}: test fraction {frac:.3f} outside 0.15-0.30")
        leaky += bool(people(d["train"]) & people(d["test"]))
    if leaky != len(sp["P3_random"]):
        fails.append("P3_random is expected to share participants between train and test (that is its purpose)")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    rows = load(args.root)
    sp = build(rows)
    out = args.root / "data" / "splits.json"
    out.write_text(json.dumps(sp, indent=1), encoding="utf-8")

    print(f"wrote {out.relative_to(args.root).as_posix()}")
    print(f"P1: train {len(sp['P1']['train'])} (G3) -> test 1A {len(sp['P1']['test_1A'])}, 2A {len(sp['P1']['test_2A'])}")
    print("P2 folds (held out, n test):", [(f["held_out"], len(f["test"])) for f in sp["P2"]])
    print("P4 folds (held out, n test):", [(f["held_out"], len(f["test"])) for f in sp["P4"]])
    pk = {r["rec_key"]: r["participant_key"] for r in rows}
    for s in sp["P3_group"]:
        r, g = sp["P3_random"][s], sp["P3_group"][s]
        frac = len(g["test"]) / (len(g["test"]) + len(g["train"]))
        shared = len({pk[k] for k in r["test"]} & {pk[k] for k in r["train"]})
        print(f"P3 seed {s}: random test {len(r['test'])} (shares {shared} participants with train) | grouped test {len(g['test'])} ({frac:.0%}) "
              f"participants {g['test_participants']}")

    if args.check:
        fails = check(sp, rows)
        for x in fails:
            print("CHECK FAILED:", x)
        print("CHECK", "PASSED" if not fails else f"FAILED ({len(fails)})")
        return 1 if fails else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
