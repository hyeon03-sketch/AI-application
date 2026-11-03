"""KERAAL 1A (patients): no Vicon, so no 3D accuracy. See EVAL_PLAN.md for what is measured and why.
1A/2A videos carry a burned-in orange skeleton, G3 videos do not. `clean` removes it by inpainting, `raw` keeps it.
Usage: python g1a.py detect {raw|clean} [--group group1A]   YOLO 2D into <OUT>/det_<variant>/
       python g1a.py check-mask <out png>                   sample frames, original vs cleaned
       python g1a.py angles {raw|clean}                     angle series for every source into <OUT>/angles_<variant>.npz
       python g1a.py report                                 aggregates only, writes RESULTS_TABLES.md here
       python g1a.py --check
KERAAL is CC BY-NC-SA: everything under E:/KERAAL_mocap3d/g1a stays outside the repo; reports hold aggregates only."""
import glob
import json
import os
import re
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import aspset
from keraal_errors import EXERCISES, features, source_angles

ROOT = "E:/KERAAL_data/extracted"
OUT = "E:/KERAAL_mocap3d/g1a"
YOLO = "E:/KERAAL_mocap3d/yolo11x-pose.pt"
MERGED = [f"{OUT}/models/train_P1P2P3_s{s}" for s in (0, 1, 2)]
ASPSET = [f"E:/ASPset510_data/runs/det_root_s{s}" for s in (0, 1, 2)]
SRC_FPS, MODEL_FPS = 15, 30   # 1A Kinect rows / annotation seconds = 15.00; the lifter was trained on G3 at 30 fps
RE_KEY = re.compile(r"-(CTK|ELK|RTK)-([A-Z]\d+)-([A-Za-z]+)-(\d+)$")


def overlay_mask(img):
    """Thin saturated orange strokes. Large orange areas (a painted wall in one room) are not skeleton lines."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (3, 110, 110), (22, 255, 255))  # low V catches the compression halo over dark clothes
    blob = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    m[cv2.dilate(blob, np.ones((5, 5), np.uint8)) > 0] = 0
    return cv2.dilate(m, np.ones((5, 5), np.uint8))


def clean(img):
    return cv2.inpaint(img, overlay_mask(img), 2, cv2.INPAINT_TELEA)


def key_of(path):
    return re.sub(r"^G\w+?-(Anon|Kinect|BP|OP)-", "", os.path.basename(path).rsplit(".", 1)[0])


def videos(group):
    return sorted(glob.glob(f"{ROOT}/{group}/videos/*.mp4"))


def area(b):
    return (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])


def pick_person(boxes):
    """A therapist can briefly be the largest person. The patient stays put: take the largest person's median box centre
    over the recording, then in each frame the person nearest to it. -1 where a frame has nobody near it."""
    centre = lambda b: (b[:, :2] + b[:, 2:]) / 2
    big = [centre(b[[int(np.argmax(area(b)))]])[0] for b in boxes if len(b)]
    pick = np.full(len(boxes), -1)
    if not big:
        return pick
    c = np.median(big, 0)
    size = np.median([np.sqrt(area(b).max()) for b in boxes if len(b)])
    for i, b in enumerate(boxes):
        if len(b):
            d = np.linalg.norm(centre(b) - c, axis=1)
            if d.min() < 1.5 * size:                     # otherwise the patient was not detected in this frame
                pick[i] = int(np.argmin(d))
    return pick


def detect(variant, group="group1A"):
    import logging
    from ultralytics import YOLO as Y
    from ultralytics.utils import LOGGER
    LOGGER.setLevel(logging.ERROR)
    model = Y(YOLO)
    out = f"{OUT}/det_{variant}" + ("" if group == "group1A" else "_" + group)
    os.makedirs(out, exist_ok=True)
    for k, vid in enumerate(videos(group)):
        path = f"{out}/{key_of(vid)}.npz"
        if os.path.exists(path):
            continue
        cap = cv2.VideoCapture(vid)
        frames = []
        while True:
            ok, img = cap.read()
            if not ok:
                break
            frames.append(clean(img) if variant == "clean" else img)
        h, w = frames[0].shape[:2]
        boxes, kps, confs = [], [], []
        # imgsz 640 makes the person about 250 px tall on 480x360 video, the same as G3 at 960; batch 16 needs about 2 GB
        for s in range(0, len(frames), 16):
            for r in model(frames[s:s + 16], imgsz=640, half=True, verbose=False):
                if r.keypoints is None or len(r.boxes) == 0:
                    boxes.append(np.zeros((0, 4))), kps.append(np.zeros((0, 17, 2))), confs.append(np.zeros((0, 17)))
                    continue
                boxes.append(r.boxes.xyxy.cpu().numpy()), kps.append(r.keypoints.xy.cpu().numpy()), confs.append(r.keypoints.conf.cpu().numpy())
        pick = pick_person(boxes)
        kp, conf, found = np.zeros((len(frames), 17, 2)), np.zeros((len(frames), 17)), pick >= 0
        for i in np.flatnonzero(found):
            kp[i], conf[i] = kps[i][pick[i]], confs[i][pick[i]]
        largest = [int(np.argmax(area(b))) if len(b) else -1 for b in boxes]
        np.savez_compressed(path, kp=kp, conf=conf, found=found, wh=np.array([w, h]),
                            not_largest=float(np.mean(pick != np.array(largest))), n_people=np.array([len(b) for b in boxes]))
        print(f"{k + 1} {key_of(vid)} frames {len(frames)} found {found.mean():.3f} not_largest {np.mean(pick != np.array(largest)):.3f}", flush=True)


def check_mask(out_png):
    rows = []
    for s in ("CTK-R1-Brest", "CTK-R4-Roscoff", "CTK-R6-Roscoff"):
        f = [v for v in videos("group1A") if s in v][0]
        cap = cv2.VideoCapture(f)
        cap.set(1, int(cap.get(7)) // 2)
        _, img = cap.read()
        rows.append(np.hstack([img, clean(img)]))
    cv2.imwrite(out_png, np.vstack(rows))


def resample_2x(x):
    """(F, ...) -> (2F - 1, ...) by linear interpolation."""
    idx = np.arange(len(x))
    t = np.arange(2 * len(x) - 1) / 2
    flat = x.reshape(len(x), -1)
    return np.stack([np.interp(t, idx, flat[:, c]) for c in range(flat.shape[1])], 1).reshape(len(t), *x.shape[1:])


def lift_at_model_fps(model, d, dev):
    """Lift 15 fps detections at the 30 fps the lifter was trained on, then return the original frames."""
    import torch
    from train_lift import COCO_FLIP, COCO_HIPS
    kp, ok = d["kp"].copy(), d["found"]
    idx = np.arange(len(kp))
    for j in range(17):
        for c in range(2):
            kp[:, j, c] = np.interp(idx, idx[ok], kp[ok, j, c])
    conf = d["conf"] * ok[:, None]
    kp2, conf2 = resample_2x(kp), resample_2x(conf)
    x = np.concatenate([aspset.normalize_root(kp2, COCO_HIPS), conf2[..., None]], -1).astype(np.float32)
    half = model.rf // 2
    xi = x[np.clip(np.arange(-half, len(x) + half), 0, len(x) - 1)]
    xf = xi[:, COCO_FLIP].copy()
    xf[..., 0] *= -1
    with torch.no_grad():
        p = model(torch.from_numpy(xi)[None].to(dev))[0].cpu().numpy()
        pf = model(torch.from_numpy(xf)[None].to(dev))[0].cpu().numpy()
    pf[..., 0] *= -1
    p = (p + pf[:, aspset.FLIP]) / 2
    return (p - p[:, aspset.PELVIS:aspset.PELVIS + 1])[::2], kp


def bone_cv(P):
    """Median over bones of (std / mean) of a bone's length within one recording. A rigid body gives about 0."""
    bones = [(0, 1), (1, 2), (3, 4), (4, 5), (6, 7), (7, 8), (9, 10), (10, 11)]
    v = []
    for a, b in bones:
        L = np.linalg.norm(P[:, a] - P[:, b], axis=-1)
        v.append(np.nanstd(L) / np.nanmean(L))
    return float(np.median(v))


def hip_flexion(top, hip, knee):
    """Angle between the trunk (up) and the thigh: about 180 standing, about 90 seated."""
    u, v = top - hip, knee - hip
    c = (u * v).sum(-1) / (np.linalg.norm(u, axis=-1) * np.linalg.norm(v, axis=-1) + 1e-9)
    return np.degrees(np.arccos(np.clip(c, -1, 1)))


def seated_fraction_kinect(K):
    a = (hip_flexion(K[:, 20], K[:, 0], K[:, 13]) + hip_flexion(K[:, 20], K[:, 0], K[:, 17])) / 2
    return float(np.nanmean(a[np.isfinite(a)] < 135))


def compute_angles(variant):
    import torch
    from train_lift import TCN
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    models = {}
    for name, runs in (("merged", MERGED), ("aspset", ASPSET)):
        for s, run in enumerate(runs):
            m = TCN(17, 3).to(dev)
            m.load_state_dict(torch.load(f"{run}/best.pt", map_location=dev))
            models[f"{name}_s{s}"] = m.eval()
    X, meta, series = {}, [], {}
    stats = []
    for vid in videos("group1A"):
        key = key_of(vid)
        ex, subj, site, _ = RE_KEY.search("-" + key).groups()
        K = np.loadtxt(f"{ROOT}/group1A/kinect/G1A-Kinect-{key}.txt").reshape(-1, 25, 7)[..., :3]
        K[(np.abs(K).sum(-1) == 0).any(1)] = np.nan
        d = np.load(f"{OUT}/det_{variant}/{key}.npz")
        if d["found"].mean() < 0.5:
            print("skip, person found in under half of frames:", key, flush=True)
            continue
        cur = {"kinect": source_angles(K, "kinect")}
        row = {"key": key, "exercise": ex, "subject": subj, "site": site, "seated_kinect": seated_fraction_kinect(K),
               "found": float(d["found"].mean()), "bone_cv_kinect": bone_cv(K[:, [18, 17, 16, 10, 9, 8, 14, 13, 12, 6, 5, 4]])}
        for name, m in models.items():
            p, kp = lift_at_model_fps(m, d, dev)
            cur[name] = source_angles(p, "aspset")
            row["bone_cv_" + name] = bone_cv(p)
        cur["raw_2d"] = source_angles(kp, "coco")
        for s, sr in cur.items():
            X.setdefault(s, []).append(features(sr))
            X.setdefault(s + "_d", []).append(features(sr, delta=True))
        # agreement with Kinect (not accuracy): per angle, pearson r and mean-centred RMSE, only where the angle moves
        for s in cur:
            if s == "kinect":
                continue
            rs, es = [], []
            for a, k in cur["kinect"].items():
                b = cur[s][a]
                n = min(len(k), len(b))
                ok = np.isfinite(k[:n]) & np.isfinite(b[:n])
                if ok.sum() < 30 or np.std(k[:n][ok]) < 5 or np.std(b[:n][ok]) < 1e-6:
                    continue
                rs.append(np.corrcoef(k[:n][ok], b[:n][ok])[0, 1])
                es.append(np.sqrt(np.mean(((k[:n][ok] - k[:n][ok].mean()) - (b[:n][ok] - b[:n][ok].mean())) ** 2)))
            row[f"agree_r_{s}"] = float(np.median(rs)) if rs else np.nan
            row[f"agree_rmse_{s}"] = float(np.median(es)) if es else np.nan
        stats.append(row)
        meta.append(key)
        print(len(meta), key, flush=True)
    np.savez_compressed(f"{OUT}/angles_{variant}.npz", keys=np.array(meta), **{k: np.stack(v) for k, v in X.items()})
    json.dump(stats, open(f"{OUT}/stats_{variant}.json", "w"), indent=1)


def labels():
    """{key: {"A": label, "B": label}} with the team's existing label rules; label is C, E1-E3 or excluded."""
    src = os.path.join(HERE, "..", "..", "..", "..", "keraal_pipeline", "src")
    sys.path.insert(0, src)
    from index import parse_anvil
    from labels import annotator_label
    out = {}
    for a in "AB":
        for f in glob.glob(f"{ROOT}/group1A/annotator{a}/*.anvil"):
            key = os.path.basename(f)[:-6].replace("G1A-", "")
            p = parse_anvil(Path(f))
            out.setdefault(key, {})[a] = annotator_label(p["evaluation"], p["error"])[0]
    return out


def lopo_scores(X, y, subj, seeds=(0, 1, 2)):
    """Out-of-fold P(error): each patient is scored by a forest trained on the other patients."""
    from sklearn.ensemble import RandomForestClassifier
    s = np.zeros(len(y))
    X = np.where(np.isfinite(X), X, np.nanmedian(X, 0))
    for p in np.unique(subj):
        tr, te = subj != p, subj == p
        if len(np.unique(y[tr])) < 2:
            s[te] = np.nan
            continue
        for seed in seeds:
            clf = RandomForestClassifier(500, class_weight="balanced", random_state=seed, n_jobs=-1).fit(X[tr], y[tr])
            s[te] += clf.predict_proba(X[te])[:, 1] / len(seeds)
    return s


def auc(y, s):
    from sklearn.metrics import roc_auc_score
    ok = np.isfinite(s)
    return float(roc_auc_score(y[ok], s[ok])) if 0 < y[ok].sum() < ok.sum() else np.nan


def permutation_p(X, y, subj, observed, n=200, seed=0):
    """Null: shuffle correct/error labels within each patient, repeat the whole leave-one-patient-out fit."""
    from sklearn.ensemble import RandomForestClassifier
    rng = np.random.default_rng(seed)
    X = np.where(np.isfinite(X), X, np.nanmedian(X, 0))
    null = []
    for _ in range(n):
        yp = y.copy()
        for p in np.unique(subj):
            i = np.flatnonzero(subj == p)
            yp[i] = rng.permutation(yp[i])
        s = np.full(len(y), np.nan)
        for p in np.unique(subj):
            tr, te = subj != p, subj == p
            if len(np.unique(yp[tr])) == 2:
                c = RandomForestClassifier(100, class_weight="balanced", random_state=0, n_jobs=-1).fit(X[tr], yp[tr])
                s[te] = c.predict_proba(X[te])[:, 1]
        null.append(auc(yp, s))
    null = np.array(null)
    return float((1 + (null >= observed).sum()) / (1 + np.isfinite(null).sum()))


SOURCES = ("merged", "aspset", "kinect", "raw_2d")


def source_auc(z, name, y, subj, idx):
    """AUC of one source; a lifter source is the mean over its 3 seeds."""
    return float(np.mean([auc(y, lopo_scores(z[k][idx], y, subj)) for k in source_keys(name)]))


def source_keys(name):
    base, d = (name[:-2], "_d") if name.endswith("_d") else (name, "")
    return [f"{base}_s{s}{d}" for s in range(3)] if base in ("merged", "aspset") else [name]


def per_patient(y, s, subj):
    return {p: auc(y[subj == p], s[subj == p]) for p in np.unique(subj)}


def report():
    from sklearn.metrics import cohen_kappa_score
    lab = labels()
    L = ["# KERAAL 1A 결과 표 (탐색, 자동 생성)", ""]
    usable = [(v["A"], v["B"]) for v in lab.values() if v["A"] in ("C", "E1", "E2", "E3") and v["B"] in ("C", "E1", "E2", "E3")]
    a, b = zip(*usable)
    ya, yb = np.array(a) != "C", np.array(b) != "C"
    L += [f"주석자 A·B 일치 (정상 vs 오류, {len(usable)}개 녹화): 일치율 {np.mean(ya == yb):.2f}, kappa {cohen_kappa_score(ya, yb):.2f}", ""]
    st = {v: json.load(open(f"{OUT}/stats_{v}.json")) for v in ("clean", "raw")}
    zs = {v: np.load(f"{OUT}/angles_{v}.npz") for v in ("clean", "raw")}

    L += ["## E1. 오류 판별 AUC (환자 1명 빼기, 운동별)", "",
          "| 입력 | 주석자 | 운동 | n (오류) | merged | aspset | kinect | raw_2d | merged 시작자세 보정 | kinect 시작자세 보정 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    patient_rows = []
    for v in ("clean", "raw"):
        z = zs[v]
        keys = z["keys"]
        for ann in "AB":
            mean = {s: [] for s in SOURCES}
            for ex in EXERCISES:
                idx = np.array([i for i, k in enumerate(keys) if k.startswith(ex) and lab.get(k, {}).get(ann) in ("C", "E1", "E2", "E3")])
                y = np.array([lab[keys[i]][ann] != "C" for i in idx]).astype(int)
                subj = np.array([keys[i].split("-")[1] for i in idx])
                row = {}
                for s in SOURCES + ("merged_d", "kinect_d"):
                    row[s] = source_auc(z, s, y, subj, idx)
                for s in SOURCES:
                    mean[s].append(row[s])
                L.append(f"| {v} | {ann} | {ex} | {len(y)} ({y.sum()}) | " + " | ".join(f"{row[s]:.3f}" for s in SOURCES + ("merged_d", "kinect_d")) + " |")
                if v == "clean":
                    sm = lopo_scores(z["merged_s0"][idx], y, subj)
                    sk = lopo_scores(z["kinect"][idx], y, subj)
                    pm, pk = per_patient(y, sm, subj), per_patient(y, sk, subj)
                    patient_rows += [(ann, ex, p, pm[p], pk[p]) for p in pm]
            L.append(f"| {v} | {ann} | 평균 | | " + " | ".join(f"{np.nanmean(mean[s]):.3f}" for s in SOURCES) + " | | |")
    L += ["", "## E1. 환자별 평균 AUC (clean, merged 시드 0 vs kinect; 환자가 독립 단위)", "", "| 주석자 | 환자 | merged | kinect | 더 나은 쪽 |", "|---|---|---|---|---|"]
    for ann in "AB":
        for p in sorted({r[2] for r in patient_rows}):
            r = [x for x in patient_rows if x[0] == ann and x[2] == p]
            m, k = np.nanmean([x[3] for x in r]), np.nanmean([x[4] for x in r])
            L.append(f"| {ann} | {p} | {m:.3f} | {k:.3f} | {'merged' if m > k + 1e-3 else 'kinect' if k > m + 1e-3 else '같음'} |")

    L += ["", "## E1. 우연 수준 점검 (clean, 주석자 A, 환자 안에서 라벨을 섞은 순열 100회)", "", "| 운동 | source | AUC | 순열 p |", "|---|---|---|---|"]
    z = zs["clean"]
    keys = z["keys"]
    for ex in EXERCISES:
        idx = np.array([i for i, k in enumerate(keys) if k.startswith(ex) and lab.get(k, {}).get("A") in ("C", "E1", "E2", "E3")])
        y = np.array([lab[keys[i]]["A"] != "C" for i in idx]).astype(int)
        subj = np.array([keys[i].split("-")[1] for i in idx])
        for s, k in (("merged", "merged_s0"), ("kinect", "kinect")):
            obs = auc(y, lopo_scores(z[k][idx], y, subj))
            L.append(f"| {ex} | {s} | {obs:.3f} | {permutation_p(z[k][idx], y, subj, obs, n=100):.3f} |")

    L += ["", "## E3. Kinect와의 각도 일치 (정확도 아님, 녹화별 중앙값의 중앙값)", "", "| 입력 | 묶음 | merged r | merged RMSE | aspset r | aspset RMSE | raw_2d r | raw_2d RMSE |", "|---|---|---|---|---|---|---|---|"]
    med = lambda rows, k: np.nanmedian([np.nanmean([r[c] for c in r if c.startswith(k)]) for r in rows])
    for v in ("clean", "raw"):
        groups = {"전체": st[v], **{g: [r for r in st[v] if r["site"] == g] for g in ("Brest", "Roscoff")}, **{g: [r for r in st[v] if r["exercise"] == g] for g in EXERCISES}}
        for g, rows in groups.items():
            vals = [med(rows, "agree_r_merged"), med(rows, "agree_rmse_merged"), med(rows, "agree_r_aspset"), med(rows, "agree_rmse_aspset"),
                    np.nanmedian([r["agree_r_raw_2d"] for r in rows]), np.nanmedian([r["agree_rmse_raw_2d"] for r in rows])]
            L.append(f"| {v} | {g} | " + " | ".join(f"{x:.3f}" if i % 2 == 0 else f"{x:.1f}" for i, x in enumerate(vals)) + " |")

    g3 = []
    for f in sorted(glob.glob(f"{ROOT}/group3/kinect/*.txt"))[::3]:
        K = np.loadtxt(f).reshape(-1, 25, 7)[..., :3]
        K[(np.abs(K).sum(-1) == 0).any(1)] = np.nan
        g3.append(seated_fraction_kinect(K))
    L += ["", "## E4. 자세와 내부 일관성", "", f"G3 앉은 자세 비율(Kinect, 몸통–넓적다리 < 135°, 180개 녹화): 평균 {np.mean(g3):.2f}", "",
          "| 환자 | 장소 | 녹화 | 앉은 자세 비율(Kinect) | 사람 검출 비율 | 뼈 길이 변동 merged | 뼈 길이 변동 aspset | 뼈 길이 변동 Kinect |", "|---|---|---|---|---|---|---|---|"]
    for p in sorted({r["subject"] for r in st["clean"]}):
        rows = [r for r in st["clean"] if r["subject"] == p]
        cv = lambda k: np.nanmedian([np.nanmean([r[c] for c in r if c.startswith(k)]) for r in rows])
        L.append(f"| {p} | {rows[0]['site']} | {len(rows)} | {np.mean([r['seated_kinect'] for r in rows]):.2f} | {np.mean([r['found'] for r in rows]):.3f} | "
                 f"{cv('bone_cv_merged'):.3f} | {cv('bone_cv_aspset'):.3f} | {np.nanmedian([r['bone_cv_kinect'] for r in rows]):.3f} |")
    text = "\n".join(L) + "\n"
    open(os.path.join(HERE, "RESULTS_TABLES.md"), "w", encoding="utf-8").write(text)
    print(text)


def _check():
    img = np.full((120, 160, 3), 90, np.uint8)
    cv2.line(img, (20, 20), (20, 100), (0, 120, 255), 2)      # thin orange stroke: skeleton
    cv2.rectangle(img, (90, 20), (150, 100), (0, 120, 255), -1)  # large orange area: wall
    m = overlay_mask(img)
    assert m[60, 20] > 0 and m[60, 120] == 0
    assert clean(img)[60, 20].tolist() != [0, 120, 255] and clean(img)[60, 120].tolist() == [0, 120, 255]
    x = np.arange(10.0)[:, None, None] * np.ones((10, 17, 2))
    r = resample_2x(x)
    assert len(r) == 19 and np.allclose(r[::2], x) and np.isclose(r[1, 0, 0], 0.5)
    P = np.zeros((20, 25, 3)); P[:, 20] = [0, 1, 0]; P[:, 13] = [0, -1, 0]; P[:, 17] = [0, -1, 0]
    assert seated_fraction_kinect(P) == 0                     # thigh in line with trunk: standing
    P[:, 13] = [0, 0, 1]; P[:, 17] = [0, 0, 1]
    assert seated_fraction_kinect(P) == 1                     # thigh at 90 degrees: seated
    assert RE_KEY.search("-CTK-R1-Brest-022").groups() == ("CTK", "R1", "Brest", "022")
    assert key_of("x/G1A-Anon-CTK-R1-Brest-022.mp4") == "CTK-R1-Brest-022" and key_of("G1A-Kinect-RTK-R4-Roscoff-081.txt") == "RTK-R4-Roscoff-081"
    patient = np.array([[100., 100, 200, 300]])
    other = np.array([[0., 50, 60, 350]])                      # a bigger person near the door, a few frames only
    bs = [patient] * 8 + [np.vstack([other * [1, 1, 3, 1], patient])] * 2 + [other] + [np.zeros((0, 4))]
    p = pick_person(bs)
    assert p[:8].tolist() == [0] * 8 and p[8:10].tolist() == [1, 1]     # patient kept although the other is larger
    assert p[-1] == -1 and pick_person([np.zeros((0, 4))]).tolist() == [-1]
    assert p[-2] == 0 or p[-2] == -1
    assert source_keys("merged_d") == ["merged_s0_d", "merged_s1_d", "merged_s2_d"] and source_keys("raw_2d") == ["raw_2d"]
    assert source_keys("kinect_d") == ["kinect_d"] and source_keys("aspset") == ["aspset_s0", "aspset_s1", "aspset_s2"]
    # chance-level and perfect separation behave
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 120); subj = np.repeat(np.arange(6), 20)
    assert lopo_scores(np.c_[y + rng.normal(0, .05, 120)], y, subj, seeds=(0,)).round(2).size == 120
    assert auc(y, lopo_scores(np.c_[y + rng.normal(0, .05, 120)], y, subj, seeds=(0,))) > 0.95
    assert abs(auc(y, lopo_scores(rng.normal(size=(120, 4)), y, subj, seeds=(0,))) - 0.5) < 0.2
    print("g1a --check OK")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "--check":
        _check()
    elif cmd == "detect":
        detect(sys.argv[2], *sys.argv[4:5])
    elif cmd == "check-mask":
        check_mask(sys.argv[2])
    elif cmd == "angles":
        compute_angles(sys.argv[2])
    elif cmd == "report":
        report()
