# Pre-registration: confirmatory analysis for protocol P1

Frozen 2026-10-05T11:17:17Z, **before any Group 3 skeleton data were available** (`raw/` held only Group 1A, 2A,
the official sample and the Group 3 file-name listing). Everything not listed under "Confirmatory analysis" is
exploratory and will be labelled as such.

## Why this task

Exploratory work on Group 1A (leave-one-patient-out, PROGRESS.md rounds 7–15) showed that only the hiding-face
exercise (CTK) carries movement information above a participant-level permutation null, and that it does so for
both annotators and both model families once Error1 and Error3 are merged (both are described as "Arms are not
raised enough" in the KERAAL papers, and annotators confuse them). The flank-stretch (ELK) and torso-rotation (RTK)
tasks did not; RTK also has only 10 annotator-A errors in the test groups.

## Data and protocol

- **Train:** Group 3 (3 healthy participants simulating errors), CTK recordings with label C or E1/E3.
  Expected: 45 C, 90 E13 (E2 recordings excluded by the class filter).
- **Test:** Groups 1A (6 patients) and 2A (healthy, robot-coached), CTK, label C or E13, Incomplete / Motionless /
  Other excluded. Annotator A: C 61, E13 43 (n = 104, 11 participants). Annotator B: C 63, E13 38 (n = 101).
- Splits: `data/splits.json`, protocol P1 (Group 3 → 1A and 2A). Results reported for 1A+2A pooled (primary) and
  for 1A and 2A separately (descriptive).
- Pipeline: `src/index.py → labels.py → preprocess.py → features.py`, summary statistics per feature
  (mean, sd, min, max, range, p10, p90), as in `src/rf_baseline.py`.
- Run: `python src/run_experiment.py --config configs/p1_confirmatory.json` (frozen; SHA-256 below).

## Confirmatory analysis

- **Primary label:** annotator A (comparable with Marusic et al. 2025, whose reported accuracies match annotator A
  counts). Annotator B is a pre-specified sensitivity analysis, not a separate confirmatory test.
- **Primary model:** Random Forest (300 trees, class_weight = balanced, min_samples_leaf = 2), Macro-F1 averaged
  over seeds 0–4. Logistic regression (C = 0.1) is a pre-specified robustness check: a conclusion is reported as
  robust only if both models agree in direction.
- **Metric:** Macro-F1 over the classes present in the test set (C, E13).

| | Hypothesis | Test |
|---|---|---|
| H1 | Error-specific features (Rerr) classify above chance | Rerr Macro-F1 vs participant-level permutation null: the model is trained once on Group 3; test labels are permuted between test participants (each receives another participant's label set, resized), 1000 permutations; one-sided p |
| H2 | Normalization helps under sim-to-real transfer (R1 > R0) | Paired participant bootstrap (2000 resamples, seeds averaged within each resample) of Macro-F1(R1) − Macro-F1(R0); one-sided p |
| H3 | Error-specific features are at least as good as normalized positions (Rerr > R1) | Same paired bootstrap for Rerr − R1; one-sided p |

- **Multiplicity:** Holm correction over H1–H3 at family-wise α = 0.05.
- **Direction expected:** H2 is expected because camera height and pitch differ between Group 3 and the robot
  sessions (round 3: SpineBase height −0.55 m vs −0.19 / −0.31 m; apparent spine tilt −8° vs −17/−18°). A
  null or reversed H2 will be reported as is.

## Pre-specified data-quality steps (run before the confirmatory models)

1. `python src/verify.py` must pass with Group 3 added (index: 540 Group 3 rows with skeletons, 45 per
   exercise × class).
2. **Trial confound** (`src/trial_confound.py`): if the shrinkage-LDA "within" accuracy on Group 3 correct
   recordings exceeds its permutation 95th percentile for R1 or Rerr, the confirmatory results are reported as
   planned **and** repeated with the features flagged by the per-feature ANOVA (FDR 5%) removed; both are shown.
3. Camera pitch for Group 3 is re-measured on all 540 recordings (round 3 used 6 sample files) and reported.

## Not changed after seeing Group 3 data

Task definition, label columns, class filter, representations, feature definitions, summary statistics, model
settings, seeds, metric, hypotheses, tests, and the multiplicity rule. Bug fixes that change outputs will be
documented in PROGRESS.md with before/after numbers.

## Exploratory (labelled as such)

All other tasks (ELK, RTK, 4-class CTK), representations (R2–R4, Rerr_d), models (LSTM, TCN), protocols (P2, P3),
annotator consensus labels, severity analyses, and any analysis designed after Group 3 data are seen.

## Frozen artefacts (SHA-256)

```
5c156db49dc9131e194fd70cb52d9e9cc97c0a2966856be6dee59677fb2ea281  configs/p1_confirmatory.json
84e8e1d0ae0191b77482030df5af97f983515abd0a90e77575e81824244e1323  src/index.py
c22d28a4e37129fc81faa65155e413076870d9ba400368987b9914b8152ad827  src/labels.py
c8d41ff8a21d412b65a323d69e893beed9f67c038ee555b50a782495234e609e  src/preprocess.py
991850f6d4c0206ed7ac1e224c286696b7fbfb80e4c3986ea0984f7a3ecc1fcc  src/features.py
9153b34721524b2423eb3005fefe38c415c499457cc753d292c11859087afa21  src/splits.py
41820d2fb579c678c9927dcd1f077d0dbff540eab7a704bc885c9dd13cc484da  src/evaluate.py
b24a8e80e5a12de7976f0c6f84923ec7424c9ec1496e662b85d93f29a850d601  src/rf_baseline.py
aaacc974c14abaf898b38dedb484732b1acf50d96229ee1fc7b010fb6d6dbe8f  src/run_experiment.py
bc09de940434c04a8498d4e4ef1d69d5be692f63280ef250a91df293ceb328a0  src/permutation_null.py
3f8e474585f43038c74d263e6f1d463f1d126bd35338654a127aa0d95831e162  src/trial_confound.py
```

Code files may still change for bug fixes or additions that do not alter the confirmatory computation; any such
change must be listed in PROGRESS.md. The config hash is enforced by `tests/test_core.py`.

## Analysis code added after the freeze (still before any Group 3 data)

`src/confirmatory.py` implements H1–H3 and the Holm rule exactly as described above (fixed-prediction participant
permutation null for H1; one-sided paired participant bootstrap for H2/H3). Added 2026-10-05, round 17;
verified by a dry run on exploratory Group 1A predictions and unit checks of the Holm procedure.

```
8c1949032c85caa3ec8a1245d62be77ea60a824563a732d39b6dbcd3eecf715e  src/confirmatory.py
```

## Changes after the freeze (none alter the confirmatory computation)

- 2026-10-06 — `src/run_experiment.py`: the `--check` smoke test no longer expects P1 to be on hold; instead it
  fails if the smoke config would run P1, and `configs/p4_smoke.json` now lists P4 only. Reason: Group 3 skeletons
  were added to `raw/`, and the old smoke config would otherwise have computed P1 test results before the
  confirmatory run. The experiment loop itself is unchanged. New hash:

```
957e74d7ea153552149a577cd571536596c1ac5a07ea11f27119261c679ea69e  src/run_experiment.py
```
- 2026-10-08 — `src/run_experiment.py`: option `drop_trial_cue_features` added to run the pre-specified secondary
  analysis (data-quality step 2) via `configs/p1_confirmatory_cue_removed.json`. The default path is unchanged:
  rerunning `configs/p1_confirmatory.json` reproduced byte-identical outputs. New hash:

```
64d6fd781962a24a2688cd5435be83e6825114eec317ab2b26c8f148953bc36f  src/run_experiment.py
```

- Disclosure: during the required full verification with Group 3 (data-quality step 1, 2026-10-08), `features.py`
  printed its usual descriptive class medians of four error-specific features, now pooled over Groups 1A, 2A and 3.
  No model was trained or evaluated on Group 3 before the confirmatory run.

## Results (run 2026-10-08)

Data-quality steps: verification passed with Group 3 (540 recordings). **Trial confound detected**: within-participant
shrinkage-LDA accuracy 0.76-1.00 vs permutation 95th percentile 0.47-0.49 for every representation and exercise;
across participants at chance. Camera geometry on all 540 Group 3 recordings: SpineBase height -0.51 m vs -0.19 /
-0.31 m (1A / 2A); sagittal spine tilt -4.3° vs -18.2° / -17.4°.

Confirmatory family (annotator A, Random Forest), Holm-adjusted:

| H | observed | reference | p (Holm) | supported |
|---|---|---|---|---|
| H1 Rerr > null | 0.407 | null 95th pct 0.428 | 0.286 | no |
| H2 R1 > R0 | -0.403 | 95% CI [-0.581, -0.210] | 1.000 | no (opposite direction, RF only; logistic regression +0.069 n.s.) |
| H3 Rerr > R1 | +0.073 | 95% CI [+0.000, +0.148] | 0.282 | no |

Pre-specified secondary analysis without flagged trial-cue features: none supported either
(H1 0.356 vs 0.397; H2 -0.357; H3 -0.008). Annotator B and logistic-regression families: none supported.
Full tables: `results/confirmatory_p1_confirmatory_P1.md`, `results/confirmatory_p1_confirmatory_cue_removed_P1.md`.
