"""Loading the frame-level CSV and turning it into per-recording joint arrays (Kinect adapter)."""
import re
import numpy as np
import pandas as pd
import config as C

_CANDIDATES = dict(
    recording=["recording_id", "recording", "rec_id", "rec", "file", "filename", "file_name", "sequence", "video", "record"],
    exercise=["exercise", "exercise_code", "exo", "movement", "exercise_name"],
    group=["group", "grp", "dataset_group"],
    frame=["frame", "frame_idx", "frame_index", "frame_id", "t_frame"],
    error_type=["error_type", "frame_error_type", "error", "error_label", "label_error", "err_type", "error_class"],
    evaluation=["evaluation", "global_evaluation"],
    body_part=["body_part", "bodypart", "frame_body_part", "region", "body_region", "error_body_part"],
)
STD = ["recording", "participant", "exercise", "group", "frame", "error_type", "body_part", "in_span", "truncated", "evaluation"]


def _find(columns, key):
    lower = {c.lower(): c for c in columns}
    for cand in _CANDIDATES.get(key, []):
        if cand in lower:
            return lower[cand]
    return None


def resolve_columns(columns):
    out = {}
    for k in STD:
        v = C.COLS.get(k)
        if v is not None and v not in columns:
            raise KeyError(f"config.COLS['{k}'] = '{v}' is not a column of the CSV")
        out[k] = v if v is not None else _find(columns, k)
    return out


def detect_joint_columns(columns):
    """Return {joint_name: (cx, cy, cz)} or None."""
    if C.JOINT_COLUMNS:
        return dict(C.JOINT_COLUMNS)
    cols = list(columns)
    # 1) name based: ShoulderLeft_x, shoulderleft.x, ShoulderLeft_X ...
    m = {}
    for name in C.KINECT_V2_ORDER:
        trip = []
        for ax in "xyz":
            hit = [c for c in cols if re.fullmatch(rf"(kinect[_\.]?)?{name}[_\.\s]?{ax}", c, re.I)]
            trip.append(hit[0] if hit else None)
        if all(trip):
            m[name] = tuple(trip)
    if len(m) >= 12:
        return m
    # 2) index based: j4_x, joint_4_x, x4, x_4, kinect_j4_x ...
    idx = {}
    for c in cols:
        r = re.fullmatch(r"(?:kinect[_\.]?)?(?:j|joint|jt|k)?[_\.]?(\d{1,2})[_\.]?([xyz])", c, re.I) \
            or re.fullmatch(r"(?:kinect[_\.]?)?([xyz])[_\.]?(\d{1,2})", c, re.I)
        if not r:
            continue
        a, b = r.groups()
        i, ax = (int(a), b.lower()) if a.isdigit() else (int(b), a.lower())
        idx.setdefault(i, {})[ax] = c
    full = {i: v for i, v in idx.items() if len(v) == 3}
    if len(full) >= 20:
        base = C.KINECT_INDEX_BASE
        out = {}
        for i, v in full.items():
            k = i - base
            if 0 <= k < len(C.KINECT_V2_ORDER):
                out[C.KINECT_V2_ORDER[k]] = (v["x"], v["y"], v["z"])
        return out
    return None


def infer_exercise(text):
    m = re.search(r"(CTK|ELK|RTK)", str(text).upper())
    return m.group(1) if m else None


def load(csv_path=None, usecols_extra=()):
    csv_path = csv_path or C.DATA_CSV
    head = pd.read_csv(csv_path, nrows=5)
    cmap = resolve_columns(head.columns)
    jmap = detect_joint_columns(head.columns)
    if jmap is None:
        raise RuntimeError("Joint columns not detected. Run inspect_input.py and fill config.JOINT_COLUMNS.")
    if cmap["recording"] is None:
        raise RuntimeError("Recording-id column not detected. Set config.COLS['recording'].")
    need = [c for c in cmap.values() if c] + [c for t in jmap.values() for c in t] + list(usecols_extra)
    df = pd.read_csv(csv_path, usecols=sorted(set(need)), low_memory=False, dtype={cmap["group"]: str} if cmap["group"] else None)
    if getattr(C, "USE_GROUPS", None) and cmap["group"]:
        df = df[df[cmap["group"]].astype(str).str.upper().isin([g.upper() for g in C.USE_GROUPS])]
    ren = {v: k for k, v in cmap.items() if v}
    df = df.rename(columns=ren)
    for k in STD:
        if k not in df.columns:
            df[k] = np.nan
    if df["exercise"].isna().all():
        df["exercise"] = df["recording"].map(infer_exercise)
    df["exercise"] = df["exercise"].astype(str).str.upper().map(lambda s: infer_exercise(s) or s)
    df["group"] = df["group"].astype(str).str.upper().str.replace("GROUP", "", regex=False).str.strip()
    df["is_error"] = ~df["error_type"].fillna("").astype(str).str.strip().str.lower().isin(C.NO_ERROR_VALUES)
    df["in_span_ok"] = _yes(df["in_span"], default=True)
    df["trunc_flag"] = _yes(df["truncated"], default=False)
    return df, jmap


def _yes(s, default):
    if s.isna().all():
        return pd.Series(default, index=s.index)
    v = s.fillna("").astype(str).str.strip().str.lower()
    return v.isin({"yes", "y", "true", "1", "1.0"})


def iter_recordings(df):
    for rec, g in df.groupby("recording", sort=True):
        if g["frame"].notna().all():
            g = g.sort_values("frame")
        yield rec, g.reset_index(drop=True)


def joints(g, jmap):
    """dict joint -> (T,3) array in (lateral, up, depth) order."""
    a = C.AXES
    out = {}
    for name, (cx, cy, cz) in jmap.items():
        xyz = g[[cx, cy, cz]].to_numpy(float)
        out[name] = np.stack([xyz[:, a["lateral"]], C.UP_SIGN * xyz[:, a["up"]], xyz[:, a["depth"]]], 1)
    return out
