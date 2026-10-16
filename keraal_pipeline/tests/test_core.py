"""Unit tests for the pipeline's core functions (fast; no full data runs).

Run:  python -m pytest -q tests
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import evaluate as ev  # noqa: E402
import features as ft  # noqa: E402
import label_clustering as lc  # noqa: E402
import labels as lb  # noqa: E402
import permutation_null as pn  # noqa: E402
import preprocess as pp  # noqa: E402
import splits as spl  # noqa: E402
from index import RE_G12_ANVIL, RE_G12_KINECT, RE_G3  # noqa: E402


# ----- file names (real patterns from the distribution)
@pytest.mark.parametrize("name,ok", [
    ("G1A-Kinect-CTK-R1-Brest-022", True), ("G2A-Kinect-RTK-S5-Brest-003", True),
    ("G1A-CTK-R1-Brest-022", False), ("G1A_Kinect_CTK_R1_Brest_022", False)])
def test_kinect_name(name, ok):
    assert bool(RE_G12_KINECT.match(name)) is ok


def test_anvil_and_g3_names():
    assert RE_G12_ANVIL.match("G2A-ELK-S1-Roscoff-017")
    m = RE_G3.match("G3-Kinect-CTK-P1T2-Unknown-E2B3-4")
    assert (m["subj"], m["trial"], m["label"], m["rep"]) == ("P1", "T2", "E2B3", "4")
    assert RE_G3.match("G3-Kinect-RTK-P3T1-Unknown-C-0")


# ----- label rules
@pytest.mark.parametrize("ev_,err,expected", [
    ("Correct", "none", ("C", "")), ("Correct", "", ("C", "")),
    ("Incorrect", "Error2", ("E2", "")), ("Incorrect", "Other", ("EXCL", "other_error")),
    ("Incorrect", "", ("EXCL", "incorrect_without_type")), ("Incomplete", "Error2", ("EXCL", "incomplete")),
    ("Motionless", "none", ("EXCL", "motionless"))])
def test_annotator_label(ev_, err, expected):
    assert lb.annotator_label(ev_, err) == expected


def test_ctk_merge_only_touches_ctk():
    assert lb.merge13("E3", "CTK") == "E13" and lb.merge13("E1", "CTK") == "E13"
    assert lb.merge13("E3", "RTK") == "E3" and lb.merge13("C", "CTK") == "C"


# ----- preprocessing
def _toy_skeleton(T=40, seed=0):
    rng = np.random.default_rng(seed)
    base = rng.normal(scale=0.3, size=(25, 3))
    base[pp.J["HipLeft"]] = [-0.1, 0, 0]; base[pp.J["HipRight"]] = [0.1, 0, 0]
    base[pp.J["SpineBase"]] = [0, 0, 0]; base[pp.J["SpineShoulder"]] = [0, 0.5, 0]
    return np.repeat(base[None], T, 0) + rng.normal(scale=0.01, size=(T, 25, 3))


def test_normalize_removes_position_heading_and_scale():
    P = _toy_skeleton()
    c, s = np.cos(0.7), np.sin(0.7)
    R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    moved = 2.0 * (P @ R.T) + np.array([0.4, -0.2, 3.0])
    n1, _, t1 = pp.normalize(P)
    n2, _, t2 = pp.normalize(moved)
    assert np.allclose(n1, n2, atol=1e-6)
    assert np.isclose(t2, 2 * t1)


def test_resample_keeps_endpoints():
    x = np.linspace(0, 1, 37)[:, None, None] * np.ones((1, 25, 3))
    y = pp.resample(x, 100)
    assert y.shape == (100, 25, 3) and np.allclose(y[0], 0) and np.allclose(y[-1], 1)


# ----- features
def test_invariant_angles_survive_any_rotation():
    P = _toy_skeleton(T=10)
    R = ft._random_rotation(np.random.default_rng(3))
    a1, a2 = ft.joint_angles(P), ft.joint_angles(1.3 * (P @ R.T) + 1.0)
    for name, (v, plane) in a1.items():
        if plane == "invariant":
            assert np.allclose(v, a2[name][0], atol=1e-6), name


def test_elbow_angle_known_value():
    P = np.zeros((1, 25, 3))
    P[0, pp.J["ShoulderLeft"]] = [0, 0, 0]; P[0, pp.J["ElbowLeft"]] = [0, -1, 0]
    P[0, pp.J["WristLeft"]] = [1, -1, 0]  # forearm at a right angle to the upper arm
    P[0, pp.J["SpineShoulder"]] = [0, 1, 0]; P[0, pp.J["SpineBase"]] = [0, -2, 0]
    P[0, pp.J["ShoulderRight"]] = [1, 0, 0]
    a = ft.joint_angles(P)
    assert np.isclose(a["elbow_flex_L"][0][0], 90.0, atol=1e-2)  # 1e-9 guard in the denominator
    assert np.isclose(a["shoulder_elev_L"][0][0], 0.0, atol=1e-2)  # arm hanging along the trunk


# ----- metrics
def test_metrics_hand_example():
    yt, yp = ["C", "C", "C", "E1", "E1"], ["C", "C", "E1", "E1", "E2"]
    assert np.isclose(ev.macro_f1(yt, yp), 0.65)
    assert np.isclose(ev.balanced_accuracy(yt, yp), (2 / 3 + 0.5) / 2)


def test_bootstrap_is_reproducible_and_degenerate_on_perfect():
    g = list("aaabbbccc"); t = ["C", "E1"] * 4 + ["C"]
    assert ev.bootstrap_ci(t, t, g, ev.macro_f1, 100) == (1.0, 1.0)
    p = ["C"] * 9
    assert ev.bootstrap_ci(t, p, g, ev.macro_f1, 100, 5) == ev.bootstrap_ci(t, p, g, ev.macro_f1, 100, 5)


# ----- splits
def test_matched_random_copies_group_split_composition():
    rows = [{"rec_key": f"k{i}", "group": "1A" if i < 60 else "3", "exercise": "CTK",
             "label_A": "C" if i % 3 else "E1", "participant_key": f"p{i // 10}"} for i in range(120)]
    grp = spl.grouped_random(rows, 0)
    rnd = spl.matched_random(rows, grp, 0)
    strat = {r["rec_key"]: (r["group"], r["label_A"]) for r in rows}
    from collections import Counter
    assert Counter(strat[k] for k in rnd["test"]) == Counter(strat[k] for k in grp["test"])
    pk = {r["rec_key"]: r["participant_key"] for r in rows}
    assert not ({pk[k] for k in grp["train"]} & {pk[k] for k in grp["test"]})


# ----- clustering and permutation null
def test_icc_bounds():
    g = np.repeat(np.arange(6), 10)
    assert np.isclose(lc.icc1((g % 2).astype(float), g)[0], 1.0)


def test_participant_permutation_keeps_counts():
    rng = np.random.default_rng(0)
    g = np.repeat(["a", "b", "c"], [4, 2, 3])
    y = np.array(["C"] * 4 + ["E2"] * 2 + ["C", "E2", "C"])
    yp, mapping = pn.permute_by_participant(y, g, rng, return_mapping=True)
    assert len(yp) == len(y) and sorted(mapping) == sorted(mapping.values())
    for dst, src in mapping.items():
        assert set(yp[g == dst]) <= set(y[g == src])


# ----- paired comparison
def test_paired_bootstrap_identical_models_give_zero():
    g = list("aaabbbcccddd"); y = ["C", "E1"] * 6
    p = ["C"] * 12
    r = ev.paired_bootstrap_diff(y, [p], [p], g, ev.macro_f1, n_boot=200)
    assert r["diff"] == 0 and r["lo"] == 0 and r["hi"] == 0


def test_paired_bootstrap_detects_a_clearly_better_model():
    g = [f"p{i // 4}" for i in range(40)]; y = ["C", "E1"] * 20
    good, bad = list(y), ["C"] * 40
    r = ev.paired_bootstrap_diff(y, [good], [bad], g, ev.macro_f1, n_boot=300)
    assert r["diff"] > 0.5 and r["lo"] > 0 and r["p"] < 0.05


# ----- pre-registration guard
def test_confirmatory_config_is_frozen():
    import hashlib
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256((root / "configs" / "p1_confirmatory.json").read_bytes()).hexdigest()
    prereg = (root / "PREREGISTRATION.md").read_text(encoding="utf-8")
    assert f"{digest}  configs/p1_confirmatory.json" in prereg, \
        "configs/p1_confirmatory.json changed after pre-registration; put exploratory variants in a new config"


# ----- full-distribution inventory
def test_inventory_keys_match_master_index_convention():
    import inventory as inv
    assert inv.rec_key("1A", "CTK", "R1-Brest-022") == ("G1A-CTK-R1-Brest-022", "Brest", "R1")
    assert inv.rec_key("3", "CTK", "P1T2-Unknown-E2B3-4") == ("G3-CTK-P1T2-E2B3-4", "", "P1")
    assert inv.rec_key("1B", "ELK", "Roscoff-223") == ("G1B-ELK-Roscoff-223", "Roscoff", "")
    assert inv.RE_FILE.match("G1B-BP-ELK-Roscoff-223") and inv.RE_FILE.match("G3-Vicon-CTK-P1T1-Unknown-C-0")
    assert inv.RE_FILE.match("G2B-Anon-CTK-Brest-001")
