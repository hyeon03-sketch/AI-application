"""
KERAAL rule-based baseline - configuration
==========================================
Edit this file only. All scripts read their settings from here.
Values marked  # <-- CHECK  should be confirmed after running inspect_input.py.
"""
from pathlib import Path

# ---------------------------------------------------------------- paths
DATA_CSV = Path(r"C:\EJ\Keraal\input_data\model_input_kinect.csv")
OUT_DIR = Path(r"C:\EJ\Keraal\rule_baseline_out")
VIDEO_ROOT = Path(r"C:\EJ\Keraal\data")   # replay_demo.py finds <group>/videos/*<recording>.mp4 here
FONT_PATH = r"C:\Windows\Fonts\malgun.ttf"   # Korean font for the demo overlay (falls back to English)

FPS = 15

# ---------------------------------------------------------------- column names
# None = auto-detect (see skeleton.py). Put the real column name here if auto-detect fails.
COLS = dict(
    recording="sample_id",
    participant="participant_key",
    exercise="exercise_code",
    group="group",
    frame="frame_idx",
    error_type="error_type",
    body_part="body_part",
    in_span="in_annotated_span",
    truncated="skeleton_truncated",
    evaluation="evaluation",   # whole-recording therapist evaluation: Correct / Incorrect / Incomplete ...
)
# Values of the per-frame error_type column that mean "no error"
NO_ERROR_VALUES = {"", "nan", "none", "0", "0.0", "c", "correct", "no", "noerror", "no_error", "normal", "ok"}

# Joint columns. None = auto-detect. Otherwise e.g.
# JOINT_COLUMNS = {"ShoulderLeft": ("ShoulderLeft_x", "ShoulderLeft_y", "ShoulderLeft_z"), ...}
JOINT_COLUMNS = None

# Kinect v2 joint order (used when columns are index-based such as j4_x / joint4_x / x4)
KINECT_V2_ORDER = [
    "SpineBase", "SpineMid", "Neck", "Head",
    "ShoulderLeft", "ElbowLeft", "WristLeft", "HandLeft",
    "ShoulderRight", "ElbowRight", "WristRight", "HandRight",
    "HipLeft", "KneeLeft", "AnkleLeft", "FootLeft",
    "HipRight", "KneeRight", "AnkleRight", "FootRight",
    "SpineShoulder", "HandTipLeft", "ThumbLeft", "HandTipRight", "ThumbRight",
]
KINECT_INDEX_BASE = 0   # set to 1 if columns are numbered 1..25                 # <-- CHECK

# Camera axes of the Kinect coordinates: which column is lateral / up / depth
AXES = dict(lateral=0, up=1, depth=2)   # x, y, z  (Kinect camera space: y up, z depth) # <-- CHECK
UP_SIGN = 1                             # set to -1 if the skeleton appears upside-down in inspect plot

# ---------------------------------------------------------------- data selection
CAL_GROUPS = ["1A", "2A"]   # groups used to calibrate thresholds
# Label used to calibrate the threshold:
#  "recording": whole-recording evaluation (Correct vs Incorrect) - recommended, every 1A/2A recording has it
#  "rep"      : error frames inside each detected repetition (few usable labels: annotations often stop early)
LABEL_MODE = "recording"
REC_FEATURE = "max_rep_value"   # recording value in "recording" mode: max_rep_value (best repetition peak,
                                 # same quantity the real-time demo judges) | value (worst rep) | exc_p95 (offline)
POSITIVE_EVAL = ["Incorrect"]   # evaluation values treated as error
NEGATIVE_EVAL = ["Correct"]     # values treated as correct (Incomplete / Motionless are left out)
EVAL_G3 = False             # metatable: do not evaluate on Group 3 until the team confirms the analysis plan
USE_GROUPS = ["1A", "2A"]   # groups loaded at all (None = all)
ONLY_IN_SPAN = True         # ignore frames with in_annotated_span == no when labelling reps
SKIP_TRUNCATED = True

# ---------------------------------------------------------------- rules per exercise
# signal: which angle drives repetition detection and the decision
#   arm_elev_min   : smaller of the two arm elevation angles (deg)
#   lat_bend       : lateral trunk bend, signed (deg)       -> symmetric
#   rotation       : shoulder line vs hip line, signed (deg) -> symmetric
# symmetric=True  -> |signal - rest| is used, so left/right sides both count.
# feature: "excursion" (peak - rest) or "raw" (absolute peak angle) used for the threshold.
EXERCISES = {
    "CTK": dict(signal="arm_elev_min", symmetric=False, feature="excursion", region="Arms",
                msg_ko="두 팔을 얼굴 높이까지 더 올리세요", msg_en="Raise both arms higher (to face level)",
                delta_start=15.0, delta_end=10.0),
    "ELK": dict(signal="lat_bend", symmetric=True, feature="excursion", region="Spine",
                msg_ko="몸통을 옆으로 더 굽히세요", msg_en="Bend the trunk further to the side",
                delta_start=6.0, delta_end=4.0),
    "RTK": dict(signal="rotation", symmetric=True, feature="excursion", region="Spine",
                msg_ko="상체를 더 돌리세요", msg_en="Rotate the upper body further",
                delta_start=8.0, delta_end=5.0),
}
# Error code shown on screen for each exercise once the taxonomy (step 0) is confirmed,
# e.g. {"CTK": "Error1", "ELK": "Error2", "RTK": "Error2"}. calibrate.py prints a suggestion.
ERROR_CODE_MAP = {}

# ---------------------------------------------------------------- repetition engine
ENGINE = dict(
    ema_alpha=0.4,        # smoothing (1 = none)
    calib_frames=15,      # first 1 s used to estimate the rest angle
    rest_beta=0.05,       # slow rest update while resting
    peak_confirm=3,       # frames of decreasing signal needed to confirm a peak
    peak_drop=1.0,        # deg below the running max needed to confirm a peak
    plateau_frames=6,     # a hold of this many frames also counts as a peak
    plateau_vel=0.4,      # deg/frame regarded as "still"
    min_rep_frames=6,
    max_rep_frames=15 * 20,
)
