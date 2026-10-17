"""Joint angles from a skeleton. Input: dict joint -> (T,3) with columns (lateral, up, depth)."""
import numpy as np
import pandas as pd


def _get(J, *names):
    for n in names:
        if n in J:
            return J[n]
    raise KeyError(f"none of {names} in skeleton")


def _angle(u, v):
    nu = np.linalg.norm(u, axis=1); nv = np.linalg.norm(v, axis=1)
    c = np.einsum("ij,ij->i", u, v) / np.maximum(nu * nv, 1e-9)
    return np.degrees(np.arccos(np.clip(c, -1, 1)))


def _signed_planar(u, v, i, j):
    """signed angle from u to v in the plane spanned by axes i, j (deg)."""
    a = np.arctan2(u[:, j], u[:, i]); b = np.arctan2(v[:, j], v[:, i])
    d = np.degrees(b - a)
    return (d + 180) % 360 - 180


def compute_angles(J):
    sh_l, sh_r = _get(J, "ShoulderLeft"), _get(J, "ShoulderRight")
    el_l, el_r = _get(J, "ElbowLeft"), _get(J, "ElbowRight")
    hip_l, hip_r = _get(J, "HipLeft"), _get(J, "HipRight")
    base = _get(J, "SpineBase")
    top = _get(J, "SpineShoulder", "Neck")

    # arm elevation: upper arm vs trunk-down direction at the shoulder (0 = arm hanging, 90 = horizontal)
    elev_l = _angle(el_l - sh_l, hip_l - sh_l)
    elev_r = _angle(el_r - sh_r, hip_r - sh_r)

    trunk = top - base
    # lateral bend: trunk vector in the frontal plane (lateral, up); 0 = upright
    lat = np.degrees(np.arctan2(trunk[:, 0], trunk[:, 1]))
    # forward flexion (sagittal plane), useful as a compensation check
    flex = np.degrees(np.arctan2(trunk[:, 2], trunk[:, 1]))
    # axial rotation: shoulder line vs hip line in the horizontal plane (lateral, depth)
    rot = _signed_planar(hip_r - hip_l, sh_r - sh_l, 0, 2)

    out = pd.DataFrame(dict(
        arm_elev_L=elev_l, arm_elev_R=elev_r, arm_elev_min=np.minimum(elev_l, elev_r),
        arm_asym=np.abs(elev_l - elev_r), lat_bend=lat, trunk_flex=flex, rotation=rot,
    ))
    return out.interpolate(limit_direction="both")
