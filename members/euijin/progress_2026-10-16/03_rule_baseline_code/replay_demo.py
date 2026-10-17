"""Days 5-6 - simulated real-time demo on Kinect recordings.

Frames are streamed one by one at 15 fps through the same RepEngine used for calibration.
Screen: front-view skeleton (error region in red), top view (rotation), angle gauge with threshold,
repetition counter, feedback message, and a timeline with therapist-annotated error frames.

    python replay_demo.py --list                       # list recordings
    python replay_demo.py --rec CTK_R2                 # substring of a recording id
    python replay_demo.py --rec CTK_R2 --video path\\to\\video.mp4   # put the original video on the left
    python replay_demo.py --rec CTK_R2 --save out.mp4 --no-show
Keys: q = quit, space = pause, f = faster, s = slower
"""
import argparse
import json
import numpy as np
import cv2
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import config as C
import skeleton as S
from kinematics import compute_angles
from rule_engine import RepEngine

BONES = [("Head", "Neck"), ("Neck", "SpineShoulder"), ("SpineShoulder", "SpineMid"), ("SpineMid", "SpineBase"),
         ("SpineShoulder", "ShoulderLeft"), ("ShoulderLeft", "ElbowLeft"), ("ElbowLeft", "WristLeft"), ("WristLeft", "HandLeft"),
         ("SpineShoulder", "ShoulderRight"), ("ShoulderRight", "ElbowRight"), ("ElbowRight", "WristRight"), ("WristRight", "HandRight"),
         ("SpineBase", "HipLeft"), ("HipLeft", "KneeLeft"), ("KneeLeft", "AnkleLeft"), ("AnkleLeft", "FootLeft"),
         ("SpineBase", "HipRight"), ("HipRight", "KneeRight"), ("KneeRight", "AnkleRight"), ("AnkleRight", "FootRight")]
REGION_BONES = {
    "Arms": {b for b in BONES if any(k in b[0] + b[1] for k in ("Elbow", "Wrist", "Hand")) or b[1].startswith("Shoulder")},
    "Spine": {b for b in BONES if all(any(k in n for k in ("Spine", "Neck", "Head")) for n in b)} |
             {("SpineBase", "HipLeft"), ("SpineBase", "HipRight")},
}
W, H = 1100, 620
RED, GRN, GRY, WHT, BLU = (60, 60, 230), (90, 180, 90), (150, 150, 150), (240, 240, 240), (200, 140, 60)


class Text:
    def __init__(self):
        try:
            self.f = {s: ImageFont.truetype(C.FONT_PATH, s) for s in (16, 20, 26)}
            self.ko = True
        except Exception:
            try:
                self.f = {s: ImageFont.load_default(size=s) for s in (16, 20, 26)}
            except TypeError:
                self.f = {s: ImageFont.load_default() for s in (16, 20, 26)}
            self.ko = False

    def draw(self, img, items):
        pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)); d = ImageDraw.Draw(pil)
        for txt, xy, col, size in items:
            d.text(xy, txt, fill=col[::-1], font=self.f[size])
        return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def projector(J, i, j, box):
    """map axes (i, j) of all joints into box=(x0,y0,w,h), equal aspect, j pointing up."""
    P = np.concatenate([v for v in J.values()])
    P = P[np.isfinite(P).all(1)]
    lo = np.percentile(P[:, [i, j]], 1, axis=0); hi = np.percentile(P[:, [i, j]], 99, axis=0)
    c = (lo + hi) / 2; span = max((hi - lo).max(), 1e-6) * 1.25
    x0, y0, w, h = box; sc = min(w, h) / span
    return lambda p: (int(x0 + w / 2 + (p[i] - c[0]) * sc), int(y0 + h / 2 - (p[j] - c[1]) * sc))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rec"); ap.add_argument("--list", action="store_true")
    ap.add_argument("--video"); ap.add_argument("--save"); ap.add_argument("--no-show", action="store_true")
    ap.add_argument("--speed", type=float, default=1.0); ap.add_argument("--csv")
    ap.add_argument("--no-video", action="store_true", help="do not look up the original video")
    args = ap.parse_args()

    df, jmap = S.load(args.csv)
    recs = df["recording"].astype(str).unique()
    if args.list or not args.rec:
        for r in recs:
            print(r)
        return
    hit = [r for r in recs if args.rec in r]
    if not hit:
        raise SystemExit(f"no recording contains '{args.rec}'")
    rec = hit[0]; g = df[df["recording"].astype(str) == rec]
    g = g.sort_values("frame").reset_index(drop=True) if g["frame"].notna().all() else g.reset_index(drop=True)
    ex = g["exercise"].iloc[0]; spec = C.EXERCISES[ex]
    J = S.joints(g, jmap); A = compute_angles(J); sig = A[spec["signal"]].to_numpy()
    try:
        thr = json.loads((C.OUT_DIR / "thresholds.json").read_text(encoding="utf-8"))[ex]["threshold"]
    except Exception:
        thr = None; print("thresholds.json not found -> running without decisions (run calibrate.py first)")
    eng = RepEngine(ex, threshold=thr)
    T = len(g); err_gt = g["is_error"].to_numpy()
    txt = Text()
    vpath = args.video
    if not vpath and not args.no_video:
        key = rec.split("-", 1)[1] if "-" in rec else rec
        hits = sorted(Path(C.VIDEO_ROOT).glob(f"*/videos/*{key}.mp4")) if Path(C.VIDEO_ROOT).exists() else []
        vpath = str(hits[0]) if hits else None
        print("video:", vpath or "not found (skeleton only)")
    vid = cv2.VideoCapture(vpath) if vpath else None
    left = (20, 20, 420, 500) if vid is None else (20, 20, 300, 500)
    front = projector(J, 0, 1, left if vid is None else (430, 20, 220, 500))
    top = projector(J, 0, 2, (660, 330, 200, 190))
    writer = cv2.VideoWriter(args.save, cv2.VideoWriter_fourcc(*"mp4v"), C.FPS, (W, H)) if args.save else None
    msg, msg_until, msg_col = "", -1, WHT
    pred_spans = []
    delay = int(1000 / C.FPS); t = 0; paused = False
    code = C.ERROR_CODE_MAP.get(ex, "")

    while t < T:
        if not paused:
            for e in eng.update(sig[t]):
                if e["type"] == "start":
                    msg_until = -1
                if e["type"] == "peak" and e["is_error"] is not None:
                    if e["is_error"]:
                        m = spec["msg_ko"] if txt.ko else spec["msg_en"]
                        msg = f"[{code + ' · ' if code else ''}{spec['region']}]\n{m}"; msg_col = RED
                    else:
                        msg = "좋아요! 정확한 동작입니다" if txt.ko else "Good repetition"; msg_col = GRN
                    msg_until = T + 1          # keep the verdict on screen until the next repetition starts
                if e["type"] == "end" and e["rep"]["is_error"]:
                    pred_spans.append((e["rep"]["start"], e["rep"]["end"]))
        img = np.full((H, W, 3), 30, np.uint8)
        if vid is not None:
            vid.set(cv2.CAP_PROP_POS_FRAMES, t); ok, fr = vid.read()
            if ok:
                fr = cv2.resize(fr, (400, int(400 * fr.shape[0] / fr.shape[1])))
                img[20:20 + min(fr.shape[0], 500), 20:420] = fr[:500]
        hot = REGION_BONES[spec["region"]] if (msg_col == RED and t <= msg_until) else set()
        for a, b in BONES:
            if a in J and b in J and np.isfinite(J[a][t]).all() and np.isfinite(J[b][t]).all():
                cv2.line(img, front(J[a][t]), front(J[b][t]), RED if (a, b) in hot else WHT, 4 if (a, b) in hot else 2, cv2.LINE_AA)
                if a in ("ShoulderLeft", "SpineShoulder") or b in ("ShoulderRight", "HipLeft", "HipRight"):
                    cv2.line(img, top(J[a][t]), top(J[b][t]), GRY, 1, cv2.LINE_AA)
        for n in ("ShoulderLeft", "ShoulderRight", "HipLeft", "HipRight"):
            if n in J and np.isfinite(J[n][t]).all():
                cv2.circle(img, top(J[n][t]), 4, BLU if "Shoulder" in n else GRY, -1)
        cv2.rectangle(img, (660, 330), (860, 520), (70, 70, 70), 1)

        # gauge
        gx, gy, gw, gh = 1045, 60, 30, 420
        cv2.rectangle(img, (gx, gy), (gx + gw, gy + gh), (80, 80, 80), 1)
        vmax = max(np.nanpercentile(np.abs(sig - (eng.rest or 0)), 99) * 1.2, (thr or 0) * 1.3, 10)
        fill = int(np.clip(eng.s / vmax, 0, 1) * gh)
        cv2.rectangle(img, (gx + 1, gy + gh - fill), (gx + gw - 1, gy + gh), BLU, -1)
        if thr is not None:
            ty = gy + gh - int(np.clip(thr / vmax, 0, 1) * gh)
            cv2.line(img, (gx - 10, ty), (gx + gw + 10, ty), (0, 200, 255), 2)

        # timeline
        tx0, ty0, tw = 20, 560, W - 40
        cv2.rectangle(img, (tx0, ty0), (tx0 + tw, ty0 + 14), (60, 60, 60), -1)
        for i in np.flatnonzero(err_gt):
            x = tx0 + int(i / T * tw); cv2.line(img, (x, ty0), (x, ty0 + 6), RED, 1)
        for s0, s1 in pred_spans:
            cv2.rectangle(img, (tx0 + int(s0 / T * tw), ty0 + 8), (tx0 + int(s1 / T * tw), ty0 + 14), (0, 165, 255), -1)
        cx = tx0 + int(t / T * tw); cv2.line(img, (cx, ty0 - 4), (cx, ty0 + 18), WHT, 2)

        items = [(f"{rec}   [{ex}]", (660, 20), WHT, 20),
                 (f"state: {eng.state}    reps: {len(eng.reps)}    t = {t / C.FPS:5.1f} s", (660, 55), GRY, 16),
                 (f"{spec['signal']}: {eng.s:5.1f}°  (thr {thr:.1f}°)" if thr is not None else f"{spec['signal']}: {eng.s:5.1f}°", (660, 80), GRY, 16),
                 ("top view (rotation)", (660, 305), GRY, 16),
                 (f"therapist evaluation (whole recording): {g['evaluation'].iloc[0]}", (660, 260), GRY, 16),
                 ("timeline: red = therapist error, orange = rule error", (20, 585), GRY, 16)]
        if t <= msg_until:
            for li, line in enumerate(msg.split("\n")):
                items.append((line, (660, 125 + 34 * li), msg_col, 26 if li == 0 else 20))
        img = txt.draw(img, items)
        if writer is not None:
            writer.write(img)
        if not args.no_show:
            cv2.imshow("KERAAL rule demo", img)
            k = cv2.waitKey(max(1, int(delay / args.speed))) & 0xFF
            if k == ord("q"):
                break
            if k == ord(" "):
                paused = not paused
            if k == ord("f"):
                args.speed *= 1.5
            if k == ord("s"):
                args.speed /= 1.5
        if not paused:
            t += 1
    if writer is not None:
        writer.release(); print("saved", args.save)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
