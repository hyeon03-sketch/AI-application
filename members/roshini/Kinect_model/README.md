# Kinect_model — per-second error detection on the Kinect CSV (Direction 2)

**Question:** does a model trained on real, expert-labelled data (Groups 1A + 2A) recognise errors in new people,
tested on the acted errors of Group 3?
**Status:** exploratory (not part of the pre-registered analysis).
**Full explanation with every step, output and meaning:** `KERAAL_Kinect_Model_Report.pdf`.

## Setup
```
pip install -r requirements.txt
```
The data is not included. Put this `Kinect_model` folder inside the folder that has `model_input_kinect.csv`
(e.g. `input_data/`), open that folder in VS Code, and run from its terminal:
```
input_data/
├── model_input_kinect.csv
└── Kinect_model/
```
If the terminal is somewhere else, set the full path of the CSV in `config.py` (`DATA_PATH`).

## Run
```
python3 Kinect_model/run_all.py           # everything (about 2–5 minutes)
python3 Kinect_model/run_all.py --quick   # final model only
```
Results are printed and saved in `results/`.

Every file can also be run on its own (VS Code: open it and press ▶, or `python3 <file>.py`):

| File | What you see when you run it |
|---|---|
| `config.py` | the current settings |
| `data.py` | steps 1–3: column checks and class counts |
| `features.py` | the size of each feature table |
| `evaluate.py` | the final model only: validation, Group 3 test, chance check |
| `run_all.py` | everything, and saves the result tables |

Loading the CSV takes 1–3 minutes; the message "Loading data…" appears first, so the screen is not stuck.

## Files
| File | What it does | Report steps |
|---|---|---|
| `config.py` | Data path, label columns, error classes per exercise, model settings | – |
| `data.py` | Load the CSV, check columns (no label leakage), filter, make target 0 = correct / 1 = error | 1–3 |
| `features.py` | Frames → one row per second. Four versions: raw positions, normalized positions, angles, final (angles + absolute angles + 5-second context) | 4, 6, 9–12 |
| `evaluate.py` | Leave-one-participant-out validation (AUC inside each person), Group 3 test (AUC per recording), chance check (1,000 label shuffles) | 8, 13, 14 |
| `run_all.py` | Runs everything in order and saves the tables | all |

## Design in short
- **One yes/no model per exercise** (Random Forest, 300 trees, `class_weight="balanced"`).
  - CTK: correct vs Error1 + Error3 · ELK: correct vs Error2 · RTK: correct vs Error1 + Error2
- **Training / validation:** 1A + 2A, per second, filters `in_annotated_span == "yes"` and complete seconds (15 frames).
  Validation holds out one participant at a time and computes the AUC **inside** that person
  (pooling across folds is misleading when errors cluster in a few people).
- **Test:** Group 3, used once. Its labels come from the file name and cover the whole recording,
  so per-second probabilities are **averaged per recording** before computing the AUC.
- **Angles** use the same formulas as `features.py` in `keraal_pipeline`, after rotating each recording so the hips face the camera.

## Expected results (Kinect)
Mean within-person AUC inside 1A + 2A:

| Features | CTK | ELK | RTK |
|---|---|---|---|
| raw positions | 0.57 | 0.55 | 0.67 |
| normalized positions | 0.55 | 0.50 | 0.51 |
| angles | 0.72 | 0.53 | 0.47 |
| **final** | **0.73** | **0.58** | **0.60** |

Group 3 test (recording level): **CTK 0.71 · ELK 0.77 · RTK 0.77**, all p = 0.001 against 1,000 within-person label shuffles.
Small differences in the third decimal can appear with other library versions.

## Limitations
12 people for training/validation, 3 for testing · Group 3 errors are acted (and not checked by physiotherapists) ·
the Group 3 trial (session) confound has not been checked yet · one model type, one random seed.
