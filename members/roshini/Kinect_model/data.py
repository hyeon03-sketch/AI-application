"""Steps 1-3: load the CSV, check the columns, filter, and make the yes/no target."""

from pathlib import Path

import pandas as pd

import config


def load_data(path=config.DATA_PATH):
    """Step 1: load the CSV and make 'group' all text (fixes the 3 vs "3" problem)."""
    print(f"Loading data from {path} ... (this can take 1-3 minutes)", flush=True)
    if not str(path).endswith(".parquet") and not Path(path).exists():
        raise FileNotFoundError(
            "model_input_kinect.csv not found. Put it in the Kinect_model folder "
            "or in the folder just above it (e.g. input_data).")
    if str(path).endswith(".parquet"):
        data = pd.read_parquet(path)
    else:
        data = pd.read_csv(path, low_memory=False)
    data["group"] = data["group"].astype(str)
    print(f"Loaded {len(data):,} rows x {data.shape[1]} columns", flush=True)
    return data


def check_columns(data):
    """Step 1: check that no label column slipped into the features (label leakage).

    Returns the 175 skeleton feature column names.
    """
    missing = [c for c in config.META_COLUMNS if c not in data.columns]
    feature_columns = [c for c in data.columns if c not in config.META_COLUMNS]
    endings = ("_x", "_y", "_z", "_qx", "_qy", "_qz", "_qw")
    strange = [c for c in feature_columns if not c.endswith(endings)]

    print("Missing meta columns:", missing)                 # expect []
    print("Number of features:", len(feature_columns))      # expect 175
    print("Unexpected feature names:", strange)             # expect []
    print(data.groupby("group")["participant_key"].nunique().to_string())   # 1A 6, 2A 6, 3 3

    assert not missing and not strange and len(feature_columns) == 175, "column check failed"
    return feature_columns


def keep_exercise_classes(df, label_col):
    """Per exercise, keep 'none' + that exercise's error types (e.g. drops CTK Error2)."""
    parts = []
    for exercise, errors in config.ERROR_CLASSES.items():
        parts.append(df[(df["exercise_code"] == exercise) & (df[label_col].isin(["none"] + errors))])
    return pd.concat(parts)


def make_train_test(data):
    """Steps 2-3: training frames (1A + 2A) and test frames (Group 3), each with target 0/1."""

    # ---------- Training data: 1A + 2A ----------
    train = data[data["group"].isin(config.TRAIN_GROUPS)].copy()
    train = train[train["in_annotated_span"] == "yes"]            # part the expert annotated
    train = train[train["sec_n_frames"] == 15]                    # complete seconds only
    train = train[~train["evaluation"].isin(["Incomplete", "Motionless"])]
    train = train[train["sec_error_type"] != "Other"]             # rare "Other" class

    # Keep only seconds that still have all 15 frames after filtering
    frames_per_second = train.groupby(["sample_id", "second_idx"])["frame_idx"].transform("count")
    train = train[frames_per_second == 15]

    train = keep_exercise_classes(train, "sec_error_type")
    train["target"] = (train["sec_error_type"] != "none").astype(int)   # 0 = correct, 1 = error

    # ---------- Test data: Group 3 (label = file name, whole recording) ----------
    test = data[data["group"] == config.TEST_GROUP].copy()
    test = keep_exercise_classes(test, "error_type")
    test["target"] = (test["error_type"] != "none").astype(int)
    test = test[test["sec_n_frames"] == 15]                        # complete seconds only

    # Counts, to check against the report
    train_seconds = train.drop_duplicates(subset=["sample_id", "second_idx"])
    test_recordings = test.drop_duplicates(subset="sample_id")
    print("\nTraining seconds (0 = correct, 1 = error):")
    print(pd.crosstab(train_seconds["exercise_code"], train_seconds["target"]).to_string())
    print("\nTest recordings (0 = correct, 1 = error):")
    print(pd.crosstab(test_recordings["exercise_code"], test_recordings["target"]).to_string())
    return train, test


if __name__ == "__main__":
    # Running this file does steps 1-3 and prints the checks and counts
    raw = load_data()
    check_columns(raw)
    make_train_test(raw)
