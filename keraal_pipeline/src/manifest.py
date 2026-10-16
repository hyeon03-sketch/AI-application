"""Reproducibility manifest: environment + SHA-256 of every pipeline output → results/MANIFEST.json

  --freeze  record the current environment and hashes of data/* and results/* (do this after a deliberate
            change to the outputs, and say why in PROGRESS.md)
  --check   recompute and compare with the frozen manifest. Any changed, missing or new output fails the
            check, so a code change that silently alters results is caught by `python src/verify.py`.
            Environment differences (package versions) are printed as warnings.

Raw data are not hashed file by file (large, and never modified); their file counts are recorded instead.

Usage:  python src/manifest.py --freeze | --check
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as md
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKED = ["data", "results"]
SKIP = {"MANIFEST.json"}
PACKAGES = ["numpy", "scipy", "scikit-learn", "joblib", "pytest", "matplotlib"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot() -> dict:
    files = {}
    for d in TRACKED:
        for p in sorted((ROOT / d).rglob("*")):
            if p.is_file() and p.name not in SKIP:
                files[p.relative_to(ROOT).as_posix()] = sha256(p)
    raw_counts = {p.relative_to(ROOT).as_posix(): sum(1 for q in p.iterdir() if q.is_file())
                  for p in sorted((ROOT / "raw").rglob("*")) if p.is_dir()}
    env = {"python": sys.version.split()[0], "platform": platform.platform(),
           "packages": {k: _version(k) for k in PACKAGES}}
    return {"environment": env, "raw_file_counts": raw_counts, "outputs": files}


def _version(pkg: str) -> str:
    try:
        return md.version(pkg)
    except md.PackageNotFoundError:
        return "not installed"


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--freeze", action="store_true")
    g.add_argument("--check", action="store_true")
    args = ap.parse_args()
    path = ROOT / "results" / "MANIFEST.json"
    now = snapshot()

    if args.freeze:
        path.write_text(json.dumps(now, indent=1), encoding="utf-8")
        print(f"froze {len(now['outputs'])} outputs and the environment into results/MANIFEST.json")
        return 0

    if not path.exists():
        print("CHECK FAILED: no results/MANIFEST.json; run with --freeze first")
        return 1
    old = json.loads(path.read_text(encoding="utf-8"))
    fails = []
    for k in sorted(set(old["outputs"]) | set(now["outputs"])):
        a, b = old["outputs"].get(k), now["outputs"].get(k)
        if a is None:
            fails.append(f"new output not in manifest: {k}")
        elif b is None:
            fails.append(f"output missing: {k}")
        elif a != b:
            fails.append(f"output changed: {k}")
    if old["raw_file_counts"] != now["raw_file_counts"]:
        fails.append("raw data file counts changed")
    for k, v in old["environment"]["packages"].items():
        if now["environment"]["packages"].get(k) != v:
            print(f"WARNING: {k} {v} at freeze, {now['environment']['packages'].get(k)} now")
    if old["environment"]["python"] != now["environment"]["python"]:
        print(f"WARNING: python {old['environment']['python']} at freeze, {now['environment']['python']} now")
    for x in fails:
        print("CHECK FAILED:", x)
    print(f"{len(now['outputs'])} outputs compared with the frozen manifest")
    print("CHECK", "PASSED" if not fails else f"FAILED ({len(fails)})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
