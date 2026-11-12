"""Recompute the G3 angle metrics of km_train.py runs (fix: runs before 11/5 00:40 lacked norm=root in args.json).
Usage: python reeval_angles.py <condition dir> ...   (e.g. E:/KERAAL_mocap3d/km/flag)"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "accuracy_loop"))
import keraal_eval
import train_lift
from km_train import FlagTCN
from train_lift import TCN as PLAIN
from tune import G3, G3_DET, angle_summary

for cond in sys.argv[1:]:
    for run in sorted(glob.glob(f"{cond}/run_*")):
        args = json.load(open(f"{run}/args.json"))
        if not os.path.exists(f"{run}/best.pt"):
            continue
        args.update(input="det", norm="root")
        json.dump(args, open(f"{run}/args.json", "w"), indent=1)
        train_lift.TCN = (lambda j, c: FlagTCN(j, c)) if args.get("flag") else PLAIN
        tmp = f"{run}/angles_all.json"
        keraal_eval.evaluate(G3, G3_DET, run, tmp)
        rows = json.load(open(tmp))["rows"]
        os.remove(tmp)
        ev = [p for p in args["eval_parts"].split(",") if p]
        for e in ev:
            res = f"{cond}/{''.join(args['train_parts'].split(','))}_{e}_s{args['seed']}/results.json"
            r = json.load(open(res))
            r["angles"] = angle_summary([x for x in rows if x["participant"] == e])
            json.dump(r, open(res, "w"), indent=1)
            print(res, round(r["unseen"]["mpjpe"], 1), json.dumps(r["angles"]), flush=True)
