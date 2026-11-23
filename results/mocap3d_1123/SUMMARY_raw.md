# KERAAL group 3 (540 recordings, each participant tested by the model that never saw them)

Angle reference: Vicon JOINT POINTS from the shared bundle. Do not mix with 13.5 / 18.7 / 16.2 deg, which use
Vicon segment rotations from the raw files (keraal_eval.py on the old workstation).

| Model | Seeds | MPJPE (mm) | PA-MPJPE (mm) | Angle RMSE (deg) | Angle RMSE per participant P1 / P2 / P3 |
|---|---|---|---|---|---|
| Kinect depth sensor | 1 | 52.8 | 45.4 | 13.4 | 10.2 / 18.7 / 13.7 |
| VideoPose3D, before fine-tuning | 1 | 243.9 | 104.5 | 20.1 | 15.5 / 19.6 / 23.9 |
| VideoPose3D, fine-tuned | 3 | 64.3 ± 0.4 | 50.7 ± 0.1 | 12.2 ± 0.1 | 9.0 ± 0.1 / 14.4 ± 0.2 / 13.8 ± 0.2 |
| Mocap3D (ours), trained here | 3 | 59.1 ± 0.5 | 47.0 ± 0.3 | 10.8 ± 0.1 | 9.5 ± 0.1 / 12.8 ± 0.2 / 10.7 ± 0.2 |

# Public data (ASPset test MPJPE / PA-MPJPE mm; VIDIMU without walking r / mean-removed RMSE deg)

| Model | Run | ASPset MPJPE | ASPset PA-MPJPE | VIDIMU r | VIDIMU RMSE | ROM diff | Reps same % | Walking L-R knee r |
|---|---|---|---|---|---|---|---|---|
| VideoPose3D, before | seed0 | – | 84.6 | 0.89 | 11.47 | -10.0 | 67.5 | 0.06 |
| VideoPose3D, fine-tuned | seed0 | 96.7 | 53.7 | 0.93 | 8.28 | -10.12 | 68.1 | 0.07 |
| VideoPose3D, fine-tuned | seed1 | 96.2 | 53.2 | 0.93 | 8.17 | -10.21 | 69.4 | 0.07 |
| VideoPose3D, fine-tuned | seed2 | 93.7 | 52.7 | 0.92 | 8.21 | -8.85 | 67.5 | 0.06 |
| Mocap3D (ours), trained here | m3d_all_s0 | 76.9 | 48.4 | 0.9 | 8.98 | -12.2 | 68.1 | 0.87 |
| Mocap3D (ours), trained here | m3d_all_s1 | 77.8 | 48.2 | 0.9 | 8.73 | -12.75 | 70.0 | 0.83 |
| Mocap3D (ours), trained here | m3d_all_s2 | 77.7 | 48.6 | 0.9 | 8.79 | -11.68 | 70.6 | 0.74 |

Reference values of the original workstation model: ASPset 79.5 / 49.1 mm, VIDIMU 0.91 / 8.84 deg; KERAAL 59.9 ± 0.3 mm (3 seeds, 120 epochs).
