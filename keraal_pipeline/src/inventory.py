"""Inventory of the FULL KERAAL distribution (every group, every modality) → data/inventory.csv

The confirmatory pipeline (index.py ...) keeps reading the small Kinect/annotation copies in raw/ so that the
pre-registered computation does not change. The full dataset (videos, BlazePose, OpenPose, Vicon, unlabeled
Groups 1B/2B) lives outside the repository, at the data root:

  1. environment variable KERAAL_DATA, else
  2. the path in data_root.txt (repository root), else
  3. E:/KERAAL_data/extracted

Expected layout (as produced by tools/fetch_all.sh):
  <root>/group1A/{annotatorA,annotatorB,kinect,blazepose,openpose,videos}
  <root>/group1B/{kinect,blazepose,openpose,videos}           (no labels, no patient IDs in file names)
  <root>/group2A/..., <root>/group2B/..., <root>/group3/{kinect,blazepose,openpose,vicon,videos}

One row per recording: rec_key (same key as data/master_index.csv for 1A/2A/3), group, exercise, site,
participant (empty for 1B/2B), and the path of each modality that exists.

Checks: recordings per group match the distributed counts (1A 250, 1B 1631, 2A 51, 2B 149 [docs: 151], 3 540), every file
name parses, and the Kinect copies in raw/ are byte-identical to the full distribution.
If the data root is missing (e.g. on a teammate's machine) the check reports SKIPPED and passes.

Usage:  python src/inventory.py [--root PATH] [--check]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# Official documentation says 2B = 151; the distributed archive holds 149 recordings (checked 2026-10-06).
EXPECTED = {"1A": 250, "1B": 1631, "2A": 51, "2B": 149, "3": 540}
IGNORED_NAMES = {"readme_files_format.txt", "res_res.txt"}  # per-group copies of the format readme; empty file
MODALITIES = {"Kinect": "kinect", "BP": "blazepose", "OP": "openpose", "Anon": "video", "Vicon": "vicon"}
RE_FILE = re.compile(r"^G(?P<group>1A|1B|2A|2B|3)-(?P<mod>Kinect|BP|OP|Anon|Vicon)-(?P<ex>RTK|ELK|CTK)-(?P<rest>.+)$")
RE_ANVIL = re.compile(r"^G(?P<group>1A|2A)-(?P<ex>RTK|ELK|CTK)-(?P<rest>.+)$")
COLUMNS = ["kinect", "blazepose", "openpose", "video", "vicon", "annotatorA", "annotatorB", "baseline_result"]
# baseline_result: group1B/kinect/results/<rec>_res.txt, per-recording score files shipped with 1B
# (global / per-segment / per-keypoint scores, apparently from the original GMM benchmark); not a recording.


IGNORED: list[str] = []


def data_root(cli: str | None) -> Path:
    if cli:
        return Path(cli)
    if os.environ.get("KERAAL_DATA"):
        return Path(os.environ["KERAAL_DATA"])
    cfg = REPO / "data_root.txt"
    if cfg.exists() and cfg.read_text(encoding="utf-8").strip():
        return Path(cfg.read_text(encoding="utf-8").strip())
    return Path("E:/KERAAL_data/extracted")


def rec_key(group: str, ex: str, rest: str) -> tuple[str, str, str]:
    """Key compatible with master_index.csv; returns (key, site, participant)."""
    parts = rest.split("-")
    if group == "3":                       # P1T1-Unknown-E1B1-0
        subj_trial, _unknown, label, rep = parts
        return f"G3-{ex}-{subj_trial}-{label}-{rep}", "", re.match(r"P\d+", subj_trial).group(0)
    if group in ("1A", "2A"):              # R1-Brest-022
        subj, site, rec = parts
        return f"G{group}-{ex}-{subj}-{site}-{rec}", site, subj
    site, rec = parts                      # 1B / 2B: Brest-007 (no participant)
    return f"G{group}-{ex}-{site}-{rec}", site, ""


def scan(root: Path) -> tuple[dict, list[str]]:
    rows: dict[str, dict] = {}
    problems: list[str] = []
    for gdir in sorted(p for p in root.glob("group*") if p.is_dir()):
        for f in sorted(gdir.rglob("*")):
            if not f.is_file() or f.name.startswith(".") or f.name.startswith("._"):
                continue
            if f.name in IGNORED_NAMES:
                IGNORED.append(f.relative_to(root).as_posix())
                continue
            stem = f.stem
            is_result = stem.endswith("_res") and f.parent.name == "results"
            m = RE_FILE.match(stem[:-4] if is_result else stem)
            if m:
                col = "baseline_result" if is_result else MODALITIES[m["mod"]]
            else:
                m = RE_ANVIL.match(stem)
                if not (m and f.suffix == ".anvil"):
                    problems.append(f"unparsed: {f.relative_to(root).as_posix()}")
                    continue
                col = "annotatorA" if "annotatorA" in f.parts else "annotatorB"
            try:
                key, site, subj = rec_key(m["group"], m["ex"], m["rest"])
            except (ValueError, AttributeError):
                problems.append(f"unexpected name structure: {f.name}")
                continue
            r = rows.setdefault(key, {"rec_key": key, "group": m["group"], "exercise": m["ex"], "site": site,
                                      "participant": subj, **{c: "" for c in COLUMNS}})
            if r[col]:
                problems.append(f"duplicate {col} for {key}: {f.name}")
            r[col] = f.relative_to(root).as_posix()
    return rows, problems


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check(root: Path, rows: dict, problems: list[str]) -> list[str]:
    fails = list(problems)
    by_group = Counter(r["group"] for r in rows.values())
    for g, n in EXPECTED.items():
        if by_group.get(g, 0) != n:
            fails.append(f"group {g}: {by_group.get(g, 0)} recordings, expected {n}")
    for r in rows.values():
        if not r["kinect"]:
            fails.append(f"{r['rec_key']}: no Kinect file")
    # the repository's Kinect copies must equal the full distribution
    compared = 0
    for local in sorted((REPO / "raw").glob("group*/kinect/*.txt")):
        full = root / local.relative_to(REPO / "raw")
        if full.exists():
            compared += 1
            if sha(local) != sha(full):
                fails.append(f"raw/ copy differs from the full distribution: {local.name}")
    print(f"Kinect copies in raw/ compared with the full distribution: {compared}")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    root = data_root(args.root)
    if not root.exists():
        print(f"SKIPPED: data root {root} not found (set KERAAL_DATA or data_root.txt). raw/ copies are still used.")
        print("CHECK PASSED (skipped)" if args.check else "")
        return 0
    rows, problems = scan(root)
    out = REPO / "data" / "inventory.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["rec_key", "group", "exercise", "site", "participant"] + COLUMNS)
        w.writeheader()
        for k in sorted(rows):
            w.writerow(rows[k])
    print(f"data root: {root}")
    print(f"wrote {out.relative_to(REPO).as_posix()} ({len(rows)} recordings)")
    table = defaultdict(Counter)
    for r in rows.values():
        for c in COLUMNS:
            table[r["group"]][c] += bool(r[c])
    print("files per group and modality:")
    for g in sorted(table):
        print(f"  group {g:2s}: " + ", ".join(f"{c} {table[g][c]}" for c in COLUMNS if table[g][c]))
    print(f"ignored non-data files: {len(IGNORED)} ({', '.join(sorted(set(Path(x).name for x in IGNORED)))})")
    for p in problems[:20]:
        print("PROBLEM:", p)
    if args.check:
        fails = check(root, rows, problems)
        for x in fails[:30]:
            print("CHECK FAILED:", x)
        print("CHECK", "PASSED" if not fails else f"FAILED ({len(fails)})")
        return 1 if fails else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
