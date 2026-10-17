"""Settings for the per-second CSV model (Direction 2: train on 1A + 2A, test on Group 3)."""

# The CSV is in the folder open in VS Code (the folder that contains model_input_kinect.csv)
DATA_PATH = "model_input_kinect.csv"

# Folder where result tables are saved
RESULTS_DIR = "results"

# The 21 label/meta columns from the metatable PDF (never used as model input)
META_COLUMNS = [
    "sample_id", "group", "exercise_code", "participant_key", "trial_id",
    "frame_idx", "time_sec", "evaluation", "error_type", "body_part",
    "severity", "label_source", "label_quality", "in_annotated_span",
    "skeleton_truncated", "second_idx", "sec_error_type", "sec_body_part",
    "sec_error_frac", "sec_n_frames", "sec_boundary",
]

# Which error types count as "error" for each exercise (one yes/no model per exercise)
ERROR_CLASSES = {
    "CTK": ["Error1", "Error3"],   # arms not raised enough (merged)
    "ELK": ["Error2"],             # body not bent sideways enough
    "RTK": ["Error1", "Error2"],   # any error (each alone is too small)
}

EXERCISES = ["CTK", "ELK", "RTK"]

# Training groups (expert labels per second) and test group (whole-recording labels)
TRAIN_GROUPS = ["1A", "2A"]
TEST_GROUP = "3"

# Random Forest settings (same in validation and test)
RF_PARAMS = dict(n_estimators=300, class_weight="balanced", min_samples_leaf=2,
                 random_state=0, n_jobs=-1)

# Context window (seconds) around each second: 2 before, itself, 2 after
CONTEXT_WINDOW = 5

# Number of label shuffles for the chance-level test on Group 3
N_PERMUTATIONS = 1000


if __name__ == "__main__":
    # Running this file shows the current settings
    print("Data path:", DATA_PATH)
    print("Exercises and their error classes:", ERROR_CLASSES)
    print("Train groups:", TRAIN_GROUPS, "| Test group:", TEST_GROUP)
    print("Random Forest settings:", RF_PARAMS)
