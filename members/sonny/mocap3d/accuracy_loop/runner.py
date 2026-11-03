"""Runs queue.json with at most N parallel trainings until the queue is empty or the deadline passes.
The queue is re-read before each start, so conditions can be added while it runs. Finished runs are skipped.
queue.json: [{"name": "bone", "args": ["--bone", "0.1"], "pairs": "inner"|"outer", "seeds": [0]}, ...]
Usage: python runner.py <parallel> <deadline yyyy-mm-ddThh:mm>"""
import datetime as dt
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = "E:/KERAAL_mocap3d/acc_loop"
PARTS = ("P1", "P2", "P3")


def trainings(kind):
    """(train participants, evaluation participants); the same training is never repeated per evaluation participant."""
    if kind == "inner":
        return [(a, [b for b in PARTS if b != a]) for a in PARTS]
    return [(",".join(p for p in PARTS if p != b), [b]) for b in PARTS]


def todo():
    for c in json.load(open(os.path.join(HERE, "queue.json"))):
        for s in c.get("seeds", [0]):
            for tr, evs in trainings(c.get("pairs", "inner")):
                t = tr.replace(",", "")
                if not all(os.path.exists(f"{OUT}/{c['name']}/{t}_{ev}_s{s}/results.json") for ev in evs):
                    yield f"{OUT}/{c['name']}/train_{t}_s{s}", ["--train-parts", tr, "--eval-parts", ",".join(evs),
                                                               "--seed", str(s)] + c.get("args", [])


def main(n, deadline):
    deadline = dt.datetime.fromisoformat(deadline)
    live = {}
    failed = set()
    while True:
        failed |= {r for r, p in live.items() if p.poll() not in (None, 0)}  # a crash is not retried
        live = {r: p for r, p in live.items() if p.poll() is None}
        pending = [t for t in todo() if t[0] not in live and t[0] not in failed]
        if dt.datetime.now() < deadline:
            for run, args in pending[:n - len(live)]:
                os.makedirs(os.path.dirname(run), exist_ok=True)
                log = open(run + ".log", "w", encoding="utf-8")
                live[run] = subprocess.Popen([sys.executable, os.path.join(HERE, "tune.py"), run] + args, stdout=log,
                                             stderr=subprocess.STDOUT, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                print(dt.datetime.now().strftime("%H:%M"), "start", run, flush=True)
        elif not live:
            break
        if not live and not pending:
            break
        time.sleep(20)
    print("runner done; failed:", sorted(failed), flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2])
