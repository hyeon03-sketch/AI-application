"""Run the whole Direction 2 analysis (train on 1A + 2A, test on Group 3) from start to end.

Usage (from inside the Kinect_model folder):
    python run_all.py              # everything: compare feature versions + final test on Group 3
    python run_all.py --quick      # only the final model (skips the raw / norm / angles comparison)

Results are printed and saved in results/.
"""

import argparse
from pathlib import Path

import pandas as pd

import config
import data as data_steps
import evaluate
import features


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=config.DATA_PATH, help="path to model_input_kinect.csv")
    parser.add_argument("--quick", action="store_true", help="skip the feature-version comparison")
    args = parser.parse_args()
    out = Path(config.RESULTS_DIR)
    out.mkdir(exist_ok=True)

    # Steps 1-3: load, check, filter, target
    print("=== Steps 1-3: data ===", flush=True)
    raw = data_steps.load_data(args.data)
    data_steps.check_columns(raw)
    train_frames, test_frames = data_steps.make_train_test(raw)

    # Steps 4-12: compare feature versions inside 1A + 2A (within-person AUC)
    versions = ["final"] if args.quick else ["raw", "norm", "angles", "final"]
    summary = []
    tables = {}
    for version in versions:
        print(f"\n=== Validation inside 1A + 2A: {version} features ===")
        tables[version] = features.build(train_frames, version)
        for exercise in config.EXERCISES:
            res = evaluate.validate_within_person(tables[version], exercise, verbose=(version == "final"))
            summary.append(dict(version=version, exercise=exercise, mean_within_person_auc=res["auc"].mean(),
                                n_people=len(res)))
    validation = pd.DataFrame(summary).pivot(index="version", columns="exercise",
                                             values="mean_within_person_auc").reindex(versions)
    print("\nMean within-person AUC (rows = feature version):")
    print(validation.round(3).to_string())
    validation.to_csv(out / "validation_within_person_auc.csv")

    # Step 13: final model, train on all 1A + 2A, test once on Group 3
    print("\n=== Step 13: test on Group 3 (final features) ===")
    test_table = features.build(test_frames, "final")
    g3 = {ex: evaluate.test_on_group3(tables["final"], test_table, ex) for ex in config.EXERCISES}

    # Step 14: chance level, per person, per error type
    print("\n=== Step 14: chance level, per person, per error type ===")
    error_types = test_frames.drop_duplicates("sample_id").set_index("sample_id")[["error_type"]]
    rows = [evaluate.chance_check(g3[ex], error_types, ex) for ex in config.EXERCISES]
    pd.DataFrame(rows).to_csv(out / "group3_test.csv", index=False)
    pd.concat(g3.values()).to_csv(out / "group3_recording_probabilities.csv", index=False)
    print(f"\nSaved: {out}/validation_within_person_auc.csv, group3_test.csv, group3_recording_probabilities.csv")


if __name__ == "__main__":
    main()
