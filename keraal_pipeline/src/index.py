"""Build data/master_index.csv: one row per KERAAL recording.

Reads the real distribution layout under raw/:
  raw/group1A/{annotatorA,annotatorB,kinect}/   (annotator A = UTF-16, B = UTF-8)
  raw/group2A/{annotatorA,annotatorB,kinect}/
  raw/group3/kinect/                            (optional; labels are in the file name)
  raw/g3_list.txt                               (Group 3 file listing, used when kinect/ is absent)

File-name patterns observed in the real files:
  G1A-Kinect-CTK-R1-Brest-022.txt   /  G1A-CTK-R1-Brest-022.anvil
  G3-Kinect-CTK-P1T1-Unknown-E1B1-0.txt

Usage:  python src/index.py [--root .] [--check]
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ANNOTATORS = ("A", "B")
EXERCISES = {"RTK": "torso_rotation", "ELK": "flank_stretch", "CTK": "hiding_face"}

RE_G12_KINECT = re.compile(r"^G(?P<group>[12][AB])-Kinect-(?P<ex>RTK|ELK|CTK)-(?P<subj>[A-Z]\d+)-(?P<site>[A-Za-z]+)-(?P<rec>\d+)$")
RE_G12_ANVIL = re.compile(r"^G(?P<group>[12][AB])-(?P<ex>RTK|ELK|CTK)-(?P<subj>[A-Z]\d+)-(?P<site>[A-Za-z]+)-(?P<rec>\d+)$")
RE_G3 = re.compile(r"^G3-(?P<mod>[A-Za-z]+)-(?P<ex>RTK|ELK|CTK)-(?P<subj>P\d+)(?P<trial>T\d+)-Unknown-(?P<label>C|E\d+B\d+)-(?P<rep>\d+)$")

IGNORED: list[str] = []

# Expected counts in the real distribution (checked with --check).
EXPECTED = {"1A": 250, "2A": 51, "3": 540}

FIELDS = [
    "rec_key", "group", "exercise", "participant", "site", "participant_key", "trial", "rep", "rec_id",
    "g3_label", "g3_error", "g3_bcode", "kinect_path", "n_frames", "label_source",
] + [f"{k}_{a}" for a in ANNOTATORS for k in
     ("evaluation", "error", "severity", "bodypart", "n_global_error_el", "n_temporal", "ann_path")]


def read_anvil(path: Path) -> ET.Element:
    raw = path.read_bytes()
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8")
    text = re.sub(r"^\s*<\?xml[^>]*\?>", "", text, count=1)
    return ET.fromstring(text.strip())


def parse_anvil(path: Path) -> dict:
    root = read_anvil(path)
    out = {"evaluation": "", "error": "", "severity": "", "bodypart": "", "n_global_error_el": 0, "n_temporal": 0}
    for track in root.iter("track"):
        name = track.get("name")
        els = track.findall("el")
        if name == "Global evaluation" and els:
            out["evaluation"] = _attrs(els[0]).get("evaluation", "")
        elif name == "Global error":
            out["n_global_error_el"] = len(els)
            # Some files hold a second, mostly empty <el>; the first one carries the label.
            for el in els:
                a = _attrs(el)
                if a.get("type") or a.get("bodyPart"):
                    out["error"] = a.get("type", "")
                    out["severity"] = a.get("Evaluation", "")
                    out["bodypart"] = a.get("bodyPart", "")
                    break
        elif name == "Temporal error":
            out["n_temporal"] = len(els)
    return out


def _attrs(el: ET.Element) -> dict:
    return {a.get("name"): (a.text or "").strip() for a in el.findall("attribute")}


def count_frames(path: Path) -> int:
    with path.open("rb") as f:
        return sum(1 for line in f if line.strip())


def collect_annotated(root: Path, group: str, problems: list[str]) -> list[dict]:
    gdir = root / "raw" / f"group{group}"
    rows: dict[str, dict] = {}
    for kpath in sorted((gdir / "kinect").glob("*.txt")):
        m = RE_G12_KINECT.match(kpath.stem)
        if not m:
            problems.append(f"[{group}] kinect name not matched: {kpath.name}")
            continue
        d = m.groupdict()
        key = f"G{d['group']}-{d['ex']}-{d['subj']}-{d['site']}-{d['rec']}"
        rows[key] = {
            "rec_key": key, "group": group, "exercise": d["ex"], "participant": d["subj"], "site": d["site"],
            # S1 appears at both Brest and Roscoff in 2A; keep the site in the key until proven to be one person.
            "participant_key": f"G{group}-{d['subj']}-{d['site']}",
            "trial": "", "rep": "", "rec_id": d["rec"], "g3_label": "", "g3_error": "", "g3_bcode": "",
            "kinect_path": kpath.relative_to(root).as_posix(), "n_frames": count_frames(kpath),
            "label_source": "anvil",
        }
    for a in ANNOTATORS:
        adir = gdir / f"annotator{a}"
        seen = set()
        for apath in sorted(adir.glob("*.anvil")):
            if apath.name == ".anvil":
                # The distribution ships one nameless annotation per folder; it has no recording ID to match.
                IGNORED.append(apath.relative_to(root).as_posix())
                continue
            m = RE_G12_ANVIL.match(apath.stem)
            if not m:
                problems.append(f"[{group}/{a}] anvil name not matched: {apath.name}")
                continue
            key = apath.stem
            seen.add(key)
            if key not in rows:
                problems.append(f"[{group}/{a}] annotation without kinect: {apath.name}")
                continue
            try:
                parsed = parse_anvil(apath)
            except Exception as exc:  # noqa: BLE001 - reported, not swallowed
                problems.append(f"[{group}/{a}] parse failure {apath.name}: {exc}")
                continue
            for k, v in parsed.items():
                rows[key][f"{k}_{a}"] = v
            rows[key][f"ann_path_{a}"] = apath.relative_to(root).as_posix()
        for key in sorted(set(rows) - seen):
            problems.append(f"[{group}/{a}] kinect without annotation: {key}")
    return list(rows.values())


def collect_group3(root: Path, problems: list[str]) -> list[dict]:
    kdir = root / "raw" / "group3" / "kinect"
    if kdir.exists():
        stems = {p.stem: p for p in kdir.glob("*.txt")}
        source = "kinect"
    else:
        listing = root / "raw" / "g3_list.txt"
        if not listing.exists():
            problems.append("[3] neither raw/group3/kinect nor raw/g3_list.txt found")
            return []
        names = [Path(l.strip()).stem for l in listing.read_text(encoding="utf-8").splitlines()
                 if l.strip().startswith("blazepose/G3-")]
        stems = {n.replace("-BP-", "-Kinect-"): None for n in names}
        source = "filelist"
    rows = []
    for stem, kpath in sorted(stems.items()):
        m = RE_G3.match(stem)
        if not m:
            problems.append(f"[3] name not matched: {stem}")
            continue
        d = m.groupdict()
        label = d["label"]
        err, bcode = ("C", "") if label == "C" else re.match(r"(E\d+)(B\d+)", label).groups()
        key = f"G3-{d['ex']}-{d['subj']}{d['trial']}-{label}-{d['rep']}"
        row = {
            "rec_key": key, "group": "3", "exercise": d["ex"], "participant": d["subj"], "site": "",
            "participant_key": f"G3-{d['subj']}", "trial": d["trial"], "rep": d["rep"], "rec_id": "",
            "g3_label": label, "g3_error": err, "g3_bcode": bcode,
            "kinect_path": kpath.relative_to(root).as_posix() if kpath else "",
            "n_frames": count_frames(kpath) if kpath else "",
            "label_source": f"filename({source})",
        }
        rows.append(row)
    return rows


def check(rows: list[dict], problems: list[str]) -> list[str]:
    fails = list(problems)
    by_group = Counter(r["group"] for r in rows)
    for g, n in EXPECTED.items():
        if by_group.get(g, 0) != n:
            fails.append(f"group {g}: expected {n} recordings, found {by_group.get(g, 0)}")
    keys = [r["rec_key"] for r in rows]
    if len(keys) != len(set(keys)):
        fails.append("duplicate rec_key values")
    for r in rows:
        if r["group"] in ("1A", "2A"):
            for a in ANNOTATORS:
                if not r.get(f"evaluation_{a}"):
                    fails.append(f"{r['rec_key']}: missing evaluation from annotator {a}")
    g3 = [r for r in rows if r["group"] == "3"]
    if g3:
        per = Counter((r["exercise"], r["g3_error"]) for r in g3)
        bad = {k: v for k, v in per.items() if v != 45}
        if bad:
            fails.append(f"group 3 not balanced at 45 per exercise x class: {bad}")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--check", action="store_true", help="exit non-zero if the expected counts are not met")
    args = ap.parse_args()

    problems: list[str] = []
    rows = collect_annotated(args.root, "1A", problems) + collect_annotated(args.root, "2A", problems)
    rows += collect_group3(args.root, problems)

    out = args.root / "data" / "master_index.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})

    print(f"wrote {out} ({len(rows)} rows)")
    print("recordings per group:", dict(sorted(Counter(r["group"] for r in rows).items())))
    print("participants per group:",
          {g: sorted({r["participant_key"] for r in rows if r["group"] == g}) for g in ("1A", "2A", "3")})
    for p in IGNORED:
        print("IGNORED:", p)
    for p in problems:
        print("PROBLEM:", p)
    if args.check:
        fails = check(rows, problems)
        for f_ in fails:
            print("CHECK FAILED:", f_)
        print("CHECK", "PASSED" if not fails else f"FAILED ({len(fails)})")
        return 1 if fails else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
