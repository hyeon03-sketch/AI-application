"""Steps 4, 6, 9-12: turn frames into one row per second.

Four feature versions (for the raw vs normalized vs angles comparison):
  "raw"     raw joint positions (camera coordinates)          75 columns x 4 stats = 300
  "norm"    positions centred on the pelvis, scaled by torso   300
  "angles"  4 error-specific angles, heading aligned           16
  "final"   angles + absolute angles + 5-second context        48   <- final model
"""

import numpy as np
import pandas as pd

import config

INFO_COLUMNS = ["sample_id", "second_idx", "participant_key", "exercise_code", "target"]

ANGLE_COLUMNS = ["shoulder_elev_left", "shoulder_elev_right", "trunk_side_tilt", "torso_rotation"]
ANGLE_COLUMNS_ABS = ANGLE_COLUMNS + ["trunk_side_tilt_abs", "torso_rotation_abs"]


def position_columns(df):
    """The 75 position columns: 25 joints x (x, y, z)."""
    return [c for c in df.columns if c not in config.META_COLUMNS and c.endswith(("_x", "_y", "_z"))
            and c != "target"]


def joint_names(df):
    """The 25 joint names, e.g. 'SpineBase' (remove the '_x' ending)."""
    return [c[:-2] for c in position_columns(df) if c.endswith("_x")]


def make_second_features(df, cols):
    """Step 4: 15 frames per second -> 1 row with mean, std, min, max of each column."""
    grouped = df.groupby(["sample_id", "second_idx"])
    stats = grouped[cols].agg(["mean", "std", "min", "max"])
    stats.columns = [f"{col}_{stat}" for col, stat in stats.columns]   # e.g. SpineBase_x_mean
    info = grouped[["participant_key", "exercise_code", "target"]].first()
    return info.join(stats).reset_index()


def normalize(df):
    """Step 6: centre every joint on the pelvis (SpineBase) and divide by torso length."""
    df = df.copy()
    pelvis = df[["SpineBase_x", "SpineBase_y", "SpineBase_z"]].values
    shoulder = df[["SpineShoulder_x", "SpineShoulder_y", "SpineShoulder_z"]].values
    df["torso"] = np.sqrt(((shoulder - pelvis) ** 2).sum(axis=1))
    torso_per_recording = df.groupby("sample_id")["torso"].transform("median")
    for joint in joint_names(df):
        for i, axis in enumerate(["x", "y", "z"]):
            col = f"{joint}_{axis}"
            df[col] = (df[col] - pelvis[:, i]) / torso_per_recording
    return df


def align_heading(df):
    """Step 10: rotate each recording around the vertical axis so the hips face the camera."""
    df = df.copy()
    hip_x = df["HipRight_x"] - df["HipLeft_x"]
    hip_z = df["HipRight_z"] - df["HipLeft_z"]
    hip_angle = np.arctan2(hip_z, hip_x)                                   # hip line seen from above
    mean_sin = np.sin(hip_angle).groupby(df["sample_id"]).transform("mean")
    mean_cos = np.cos(hip_angle).groupby(df["sample_id"]).transform("mean")
    theta = np.arctan2(mean_sin, mean_cos)                                 # one angle per recording
    c, s = np.cos(theta), np.sin(theta)
    for joint in joint_names(df):
        x = df[f"{joint}_x"].copy()
        z = df[f"{joint}_z"].copy()
        df[f"{joint}_x"] = x * c + z * s
        df[f"{joint}_z"] = -x * s + z * c
    return df


def angle_between(v1, v2):
    """Angle in degrees between two sets of 3D vectors (one pair per frame)."""
    cos = (v1 * v2).sum(axis=1) / (np.linalg.norm(v1, axis=1) * np.linalg.norm(v2, axis=1))
    return np.degrees(np.arccos(np.clip(cos, -1, 1)))


def add_angles(df):
    """Step 9: the 4 error-specific angles (same formulas as features.py in keraal_pipeline)."""
    df = df.copy()

    def get(joint):
        return df[[f"{joint}_x", f"{joint}_y", f"{joint}_z"]].values

    trunk_down = get("SpineBase") - get("SpineShoulder")
    df["shoulder_elev_left"] = angle_between(get("ElbowLeft") - get("ShoulderLeft"), trunk_down)    # CTK
    df["shoulder_elev_right"] = angle_between(get("ElbowRight") - get("ShoulderRight"), trunk_down)
    trunk_up = get("SpineShoulder") - get("SpineBase")
    df["trunk_side_tilt"] = np.degrees(np.arctan2(trunk_up[:, 0], trunk_up[:, 1]))                   # ELK
    shoulders = get("ShoulderRight") - get("ShoulderLeft")
    hips = get("HipRight") - get("HipLeft")
    rotation = np.degrees(np.arctan2(shoulders[:, 2], shoulders[:, 0]) - np.arctan2(hips[:, 2], hips[:, 0]))
    df["torso_rotation"] = (rotation + 180) % 360 - 180                                               # RTK
    return df


def add_angles_abs(df):
    """Step 12: angles + absolute tilt and rotation (how far, regardless of direction)."""
    df = add_angles(df)
    df["trunk_side_tilt_abs"] = df["trunk_side_tilt"].abs()
    df["torso_rotation_abs"] = df["torso_rotation"].abs()
    return df


def add_context(sec_table, window=config.CONTEXT_WINDOW):
    """Step 12: for each second, also summarise the seconds around it (same recording only)."""
    t = sec_table.sort_values(["sample_id", "second_idx"]).copy()
    cols = [c for c in t.columns if c not in INFO_COLUMNS]
    g = t.groupby("sample_id")
    for c in cols:
        if c.endswith("_max"):
            t[c + "_ctx"] = g[c].transform(lambda s: s.rolling(window, center=True, min_periods=1).max())
        elif c.endswith("_min"):
            t[c + "_ctx"] = g[c].transform(lambda s: s.rolling(window, center=True, min_periods=1).min())
        else:
            t[c + "_ctx"] = g[c].transform(lambda s: s.rolling(window, center=True, min_periods=1).mean())
    return t


def build(frames, version="final"):
    """Build the per-second table for one feature version: 'raw', 'norm', 'angles' or 'final'."""
    if version == "raw":
        return make_second_features(frames, position_columns(frames))
    if version == "norm":
        return make_second_features(normalize(frames), position_columns(frames))
    if version == "angles":
        return make_second_features(add_angles(align_heading(frames)), ANGLE_COLUMNS)
    if version == "final":
        return add_context(make_second_features(add_angles_abs(align_heading(frames)), ANGLE_COLUMNS_ABS))
    raise ValueError(f"unknown version: {version}")


def feature_names(table):
    """All columns except the 5 info columns."""
    return [c for c in table.columns if c not in INFO_COLUMNS]


if __name__ == "__main__":
    # Running this file builds the four feature tables and prints their sizes
    import data as data_steps
    raw = data_steps.load_data()
    train_frames, test_frames = data_steps.make_train_test(raw)
    for version in ["raw", "norm", "angles", "final"]:
        table = build(train_frames, version)
        print(f"{version:>6} features: {table.shape[0]} seconds x {len(feature_names(table))} features")
    test_table = build(test_frames, "final")
    print(f" final features (Group 3 test): {test_table.shape[0]} seconds")
