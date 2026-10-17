"""Steps 8, 13, 14: validation inside 1A + 2A, the Group 3 test, and the chance-level check."""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

import config
from features import feature_names


def new_model():
    """Random Forest with the settings from config.py."""
    return RandomForestClassifier(**config.RF_PARAMS)


def validate_within_person(table, exercise, verbose=True):
    """Step 8: leave-one-participant-out on 1A + 2A; ROC-AUC inside each held-out person.

    Pooling probabilities across folds is misleading when errors cluster in a few people
    (see report, step 7), so the AUC is computed per person and then averaged.
    """
    cols = feature_names(table)
    ex = table[table["exercise_code"] == exercise]
    rows = []
    for person in ex["participant_key"].unique():
        val = ex[ex["participant_key"] == person]
        if val["target"].nunique() < 2:              # AUC needs both correct and error seconds
            continue
        train = ex[ex["participant_key"] != person]
        model = new_model().fit(train[cols], train["target"])
        prob = model.predict_proba(val[cols])[:, 1]
        auc = roc_auc_score(val["target"], prob)
        rows.append(dict(exercise=exercise, participant=person, n_error=int(val["target"].sum()),
                         n_correct=int((val["target"] == 0).sum()), auc=auc))
        if verbose:
            print(f"   {person}: {rows[-1]['n_error']} error / {rows[-1]['n_correct']} correct seconds"
                  f" -> AUC {auc:.3f}")
    result = pd.DataFrame(rows)
    print(f"{exercise}: mean within-person AUC {result['auc'].mean():.3f} ({len(result)} people)")
    return result


def test_on_group3(train_table, test_table, exercise):
    """Step 13: train on all 1A + 2A seconds, predict Group 3, average per recording, ROC-AUC."""
    cols = feature_names(train_table)
    tr = train_table[train_table["exercise_code"] == exercise]
    te = test_table[test_table["exercise_code"] == exercise].copy()
    model = new_model().fit(tr[cols], tr["target"])
    te["prob"] = model.predict_proba(te[cols])[:, 1]                       # P(error) per second
    rec = te.groupby("sample_id").agg(participant_key=("participant_key", "first"),
                                      target=("target", "first"),
                                      prob=("prob", "mean")).reset_index()  # one row per recording
    auc = roc_auc_score(rec["target"], rec["prob"])
    print(f"{exercise}: {len(rec)} recordings | mean prob correct {rec[rec['target'] == 0]['prob'].mean():.3f}"
          f" | mean prob error {rec[rec['target'] == 1]['prob'].mean():.3f} | ROC-AUC {auc:.3f}")
    return rec


def chance_check(rec, error_types, exercise, n_perm=config.N_PERMUTATIONS, seed=0):
    """Step 14: shuffle labels within each person (n_perm times); per-person AUC; error types."""
    rng = np.random.default_rng(seed)
    rec = rec.join(error_types, on="sample_id")
    observed = roc_auc_score(rec["target"], rec["prob"])
    null = []
    for _ in range(n_perm):
        shuffled = rec.groupby("participant_key")["target"].transform(lambda s: rng.permutation(s.values))
        null.append(roc_auc_score(shuffled, rec["prob"]))
    null = np.array(null)
    p_value = (1 + (null >= observed).sum()) / (1 + len(null))
    print(f"{exercise}: AUC {observed:.3f} | chance 95th percentile {np.percentile(null, 95):.3f} | p = {p_value:.3f}")
    per_person = {}
    for person, part in rec.groupby("participant_key"):
        per_person[person] = roc_auc_score(part["target"], part["prob"])
        print(f"   {person}: AUC {per_person[person]:.3f}")
    by_type = rec.groupby("error_type")["prob"].mean().round(3).to_dict()
    print("   mean prob by error type:", by_type)
    return dict(exercise=exercise, auc=observed, chance_p95=np.percentile(null, 95), p_value=p_value,
                **{f"auc_{k}": v for k, v in per_person.items()},
                **{f"prob_{k}": v for k, v in by_type.items()})


if __name__ == "__main__":
    # Running this file evaluates the final model only (steps 8, 13, 14)
    import data as data_steps
    import features
    raw = data_steps.load_data()
    train_frames, test_frames = data_steps.make_train_test(raw)
    train_table = features.build(train_frames, "final")
    test_table = features.build(test_frames, "final")
    print("\n=== Validation inside 1A + 2A (final features) ===")
    for ex in config.EXERCISES:
        validate_within_person(train_table, ex)
    print("\n=== Test on Group 3 ===")
    g3 = {ex: test_on_group3(train_table, test_table, ex) for ex in config.EXERCISES}
    print("\n=== Chance level, per person, per error type ===")
    error_types = test_frames.drop_duplicates("sample_id").set_index("sample_id")[["error_type"]]
    for ex in config.EXERCISES:
        chance_check(g3[ex], error_types, ex)
