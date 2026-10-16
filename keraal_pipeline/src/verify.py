"""Run every pipeline stage with --check, then the unit tests, then the reproducibility manifest check.
Exit non-zero on the first failure.

Usage:  python src/verify.py                 (full verification)
        python src/verify.py --no-manifest   (skip the hash comparison, e.g. right before re-freezing)
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = ["index.py", "labels.py", "preprocess.py", "features.py", "splits.py", "evaluate.py", "rf_baseline.py",
          "trial_confound.py", "label_clustering.py", "person_confound.py", "permutation_null.py", "compare_reps.py", "run_experiment.py", "confirmatory.py", "figures.py", "inventory.py"]

steps = [(s, [sys.executable, str(ROOT / "src" / s), "--check"]) for s in STAGES]
steps.append(("unit tests", [sys.executable, "-m", "pytest", "-q", str(ROOT / "tests")]))
if "--no-manifest" not in sys.argv:
    steps.append(("manifest.py", [sys.executable, str(ROOT / "src" / "manifest.py"), "--check"]))

for name, cmd in steps:
    print(f"=== {name}", flush=True)
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        print(f"VERIFY FAILED at {name}")
        sys.exit(r.returncode)
print("VERIFY PASSED:", ", ".join(n for n, _ in steps))
