## ASPset-510 test (official split), mean ± SD over seeds

| input | norm | seeds | val MPJPE | test MPJPE | test PA-MPJPE | test accel |
|---|---|---|---|---|---|---|
| det | root | 3 | 97.8 ± 0.6 | 83.4 ± 1.7 | 49.4 ± 0.4 | 10.6 ± 0.1 |
| det | screen | 3 | 100.6 ± 0.6 | 82.5 ± 0.9 | 54.6 ± 0.5 | 14.4 ± 0.1 |
| gt | root | 3 | 87.8 ± 0.4 | 77.1 ± 0.8 | 41.1 ± 0.8 | 7.0 ± 0.0 |
| gt | screen | 3 | 90.3 ± 0.6 | 73.0 ± 1.5 | 46.5 ± 0.3 | 6.9 ± 0.0 |
| mean pose | – | – | – | 227.1 | 161.2 | – |

All runs use the same test set: 60 views, 13708 frames. mm; accel = mm/frame².

## KERAAL G3: joint-angle agreement with Vicon

Primary metric: per-pair Pearson r at lag 0 (r0), median over pairs, mean over seeds. r(best lag) searches ±1 s for each source the same way and is optimistic. RMSE is in degrees after removing each series' mean. Vicon angles are relative segment rotations, not anatomical flexion (see limitations).

| model | seeds | pairs | ours r0 | raw 2D r0 | Kinect r0 | ours r (best lag) | raw 2D r | Kinect r | ours RMSE | raw 2D RMSE | Kinect RMSE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| det/root | 3 | 2053 | 0.596 | 0.552 | 0.667 | 0.618 | 0.580 | 0.706 | 20.4 | 28.9 | 18.6 |
| det/screen | 3 | 2053 | 0.501 | 0.552 | 0.667 | 0.524 | 0.580 | 0.706 | 26.9 | 28.9 | 18.6 |

### Paired tests at participant × exercise level (9 cells, 3 participants; seed-averaged)

| model | comparison | mean Δ over cells | cells where ours better | participants where ours better | Wilcoxon p (9 cells) |
|---|---|---|---|---|---|
| det/root | ours − raw_2d (r0) | +0.022 | 6/9 | 3/3 | 0.570 |
| det/root | ours − kinect (r0) | -0.100 | 3/9 | 0/3 | 0.250 |
| det/root | ours − raw_2d (rmse) | -7.955 | 9/9 | 3/3 | 0.004 |
| det/root | ours − kinect (rmse) | -0.958 | 4/9 | 2/3 | 1.000 |
| det/screen | ours − raw_2d (r0) | -0.028 | 4/9 | 0/3 | 0.496 |
| det/screen | ours − kinect (r0) | -0.150 | 1/9 | 0/3 | 0.012 |
| det/screen | ours − raw_2d (rmse) | -2.499 | 8/9 | 3/3 | 0.012 |
| det/screen | ours − kinect (rmse) | +4.498 | 3/9 | 0/3 | 0.055 |

### Per angle (r0; seed-mean of median over pairs; angles with < 10 moving pairs omitted)

| model | angle | pairs | ours r0 | raw 2D r0 | Kinect r0 |
|---|---|---|---|---|---|
| det/root | L_elbow | 499 | 0.362 | 0.387 | 0.560 |
| det/root | L_shoulder | 529 | 0.698 | 0.681 | 0.715 |
| det/root | R_elbow | 477 | 0.405 | 0.421 | 0.548 |
| det/root | R_shoulder | 538 | 0.679 | 0.647 | 0.771 |
| det/screen | L_elbow | 499 | 0.232 | 0.387 | 0.560 |
| det/screen | L_shoulder | 529 | 0.725 | 0.681 | 0.715 |
| det/screen | R_elbow | 477 | 0.282 | 0.421 | 0.548 |
| det/screen | R_shoulder | 538 | 0.718 | 0.647 | 0.771 |

### Per participant and per label (det/root, r0)

| group | pairs | ours r0 | raw 2D r0 | Kinect r0 |
|---|---|---|---|---|
| participant P1 | 688 | 0.779 | 0.695 | 0.782 |
| participant P2 | 695 | 0.592 | 0.526 | 0.639 |
| participant P3 | 670 | 0.412 | 0.433 | 0.588 |
| exercise CTK | 682 | 0.642 | 0.561 | 0.638 |
| exercise ELK | 727 | 0.703 | 0.715 | 0.709 |
| exercise RTK | 644 | 0.239 | 0.135 | 0.648 |
| label C | 523 | 0.552 | 0.515 | 0.620 |
| label E | 1530 | 0.612 | 0.573 | 0.682 |

### Per participant and per label (det/screen, r0)

| group | pairs | ours r0 | raw 2D r0 | Kinect r0 |
|---|---|---|---|---|
| participant P1 | 688 | 0.604 | 0.695 | 0.782 |
| participant P2 | 695 | 0.522 | 0.526 | 0.639 |
| participant P3 | 670 | 0.397 | 0.433 | 0.588 |
| exercise CTK | 682 | 0.563 | 0.561 | 0.638 |
| exercise ELK | 727 | 0.610 | 0.715 | 0.709 |
| exercise RTK | 644 | 0.200 | 0.135 | 0.648 |
| label C | 523 | 0.453 | 0.515 | 0.620 |
| label E | 1530 | 0.527 | 0.573 | 0.682 |


## RQ4: KERAAL G3 error detection by angle source (540 recordings, Vicon lost-frame fraction <= 1.0)

Random forest on joint-angle features, leave-one-participant-out within each exercise; mean over 9 participant × exercise cells and 3 classifier seeds. AUC = correct vs any error; F1 = macro-F1 over C/E1/E2/E3 (chance 0.25). `_d` = each angle minus its starting-posture mean.

| source | AUC | macro-F1 | CTK AUC | CTK F1 | ELK AUC | ELK F1 | RTK AUC | RTK F1 |
|---|---|---|---|---|---|---|---|---|
| vicon | 0.643 | 0.282 | 0.644 | 0.344 | 0.663 | 0.378 | 0.623 | 0.123 |
| vicon_pts | 0.766 | 0.530 | 0.732 | 0.526 | 0.680 | 0.403 | 0.886 | 0.663 |
| kinect | 0.809 | 0.567 | 0.977 | 0.823 | 0.577 | 0.298 | 0.873 | 0.579 |
| ours_root | 0.852 | 0.593 | 0.867 | 0.617 | 0.763 | 0.512 | 0.925 | 0.648 |
| ours_screen | 0.828 | 0.560 | 0.920 | 0.549 | 0.713 | 0.518 | 0.852 | 0.613 |
| raw_2d | 0.876 | 0.562 | 0.952 | 0.630 | 0.773 | 0.534 | 0.903 | 0.521 |
| vicon_d | 0.624 | 0.319 | 0.555 | 0.386 | 0.781 | 0.229 | 0.537 | 0.343 |
| vicon_pts_d | 0.796 | 0.462 | 0.776 | 0.408 | 0.753 | 0.417 | 0.859 | 0.561 |
| kinect_d | 0.806 | 0.492 | 0.868 | 0.636 | 0.711 | 0.338 | 0.837 | 0.500 |
| ours_root_d | 0.811 | 0.545 | 0.704 | 0.447 | 0.819 | 0.515 | 0.909 | 0.672 |
| ours_screen_d | 0.753 | 0.517 | 0.677 | 0.402 | 0.711 | 0.495 | 0.871 | 0.655 |
| raw_2d_d | 0.796 | 0.487 | 0.809 | 0.497 | 0.728 | 0.464 | 0.852 | 0.501 |

| comparison | metric | mean Δ | cells a better | Wilcoxon p (9 cells) |
|---|---|---|---|---|
| ours_root − vicon_pts | auc | +0.086 | 8/9 | 0.098 |
| ours_root − vicon_pts | f1 | +0.062 | 8/9 | 0.129 |
| ours_root − vicon | auc | +0.209 | 8/9 | 0.020 |
| ours_root − vicon | f1 | +0.311 | 9/9 | 0.004 |
| ours_root − kinect | auc | +0.043 | 7/9 | 0.250 |
| ours_root − kinect | f1 | +0.026 | 6/9 | 0.734 |
| ours_root − raw_2d | auc | -0.024 | 5/9 | 0.820 |
| ours_root − raw_2d | f1 | +0.031 | 5/9 | 0.496 |
| kinect − vicon_pts | auc | +0.043 | 6/9 | 0.652 |
| kinect − vicon_pts | f1 | +0.036 | 5/9 | 0.652 |
| ours_root − ours_screen | auc | +0.023 | 6/9 | 0.359 |
| ours_root − ours_screen | f1 | +0.033 | 6/9 | 0.496 |
| ours_root_d − vicon_pts_d | auc | +0.015 | 6/9 | 0.359 |
| ours_root_d − vicon_pts_d | f1 | +0.082 | 7/9 | 0.098 |
| ours_root_d − vicon_d | auc | +0.186 | 7/9 | 0.039 |
| ours_root_d − vicon_d | f1 | +0.225 | 8/9 | 0.008 |
| ours_root_d − kinect_d | auc | +0.005 | 5/9 | 0.652 |
| ours_root_d − kinect_d | f1 | +0.053 | 5/9 | 0.570 |
| ours_root_d − raw_2d_d | auc | +0.014 | 6/9 | 0.570 |
| ours_root_d − raw_2d_d | f1 | +0.057 | 5/9 | 0.250 |
| kinect_d − vicon_pts_d | auc | +0.009 | 5/9 | 1.000 |
| kinect_d − vicon_pts_d | f1 | +0.029 | 7/9 | 0.426 |
| ours_root_d − ours_screen_d | auc | +0.058 | 8/9 | 0.039 |
| ours_root_d − ours_screen_d | f1 | +0.027 | 5/9 | 0.496 |
## RQ4: KERAAL G3 error detection by angle source (491 recordings, Vicon lost-frame fraction <= 0.2)

Random forest on joint-angle features, leave-one-participant-out within each exercise; mean over 9 participant × exercise cells and 3 classifier seeds. AUC = correct vs any error; F1 = macro-F1 over C/E1/E2/E3 (chance 0.25). `_d` = each angle minus its starting-posture mean.

| source | AUC | macro-F1 | CTK AUC | CTK F1 | ELK AUC | ELK F1 | RTK AUC | RTK F1 |
|---|---|---|---|---|---|---|---|---|
| vicon | 0.630 | 0.280 | 0.652 | 0.362 | 0.616 | 0.356 | 0.623 | 0.123 |
| vicon_pts | 0.768 | 0.548 | 0.748 | 0.562 | 0.671 | 0.420 | 0.886 | 0.663 |
| kinect | 0.796 | 0.546 | 0.959 | 0.771 | 0.555 | 0.287 | 0.873 | 0.579 |
| ours_root | 0.826 | 0.572 | 0.817 | 0.568 | 0.735 | 0.501 | 0.925 | 0.648 |
| ours_screen | 0.811 | 0.545 | 0.876 | 0.499 | 0.705 | 0.523 | 0.852 | 0.613 |
| raw_2d | 0.864 | 0.520 | 0.920 | 0.548 | 0.770 | 0.491 | 0.903 | 0.521 |
| vicon_d | 0.619 | 0.292 | 0.553 | 0.291 | 0.766 | 0.242 | 0.537 | 0.343 |
| vicon_pts_d | 0.782 | 0.445 | 0.765 | 0.396 | 0.722 | 0.377 | 0.859 | 0.561 |
| kinect_d | 0.809 | 0.498 | 0.898 | 0.682 | 0.692 | 0.313 | 0.837 | 0.500 |
| ours_root_d | 0.808 | 0.531 | 0.685 | 0.434 | 0.831 | 0.488 | 0.909 | 0.672 |
| ours_screen_d | 0.743 | 0.499 | 0.637 | 0.365 | 0.722 | 0.476 | 0.871 | 0.655 |
| raw_2d_d | 0.756 | 0.456 | 0.706 | 0.423 | 0.711 | 0.444 | 0.852 | 0.501 |

| comparison | metric | mean Δ | cells a better | Wilcoxon p (9 cells) |
|---|---|---|---|---|
| ours_root − vicon_pts | auc | +0.057 | 8/9 | 0.098 |
| ours_root − vicon_pts | f1 | +0.024 | 7/9 | 0.426 |
| ours_root − vicon | auc | +0.195 | 8/9 | 0.020 |
| ours_root − vicon | f1 | +0.292 | 8/9 | 0.008 |
| ours_root − kinect | auc | +0.030 | 6/9 | 0.496 |
| ours_root − kinect | f1 | +0.027 | 6/9 | 0.652 |
| ours_root − raw_2d | auc | -0.038 | 3/9 | 0.496 |
| ours_root − raw_2d | f1 | +0.052 | 6/9 | 0.250 |
| kinect − vicon_pts | auc | +0.027 | 4/9 | 1.000 |
| kinect − vicon_pts | f1 | -0.003 | 5/9 | 0.910 |
| ours_root − ours_screen | auc | +0.015 | 6/9 | 0.734 |
| ours_root − ours_screen | f1 | +0.028 | 6/9 | 0.359 |
| ours_root_d − vicon_pts_d | auc | +0.026 | 6/9 | 0.301 |
| ours_root_d − vicon_pts_d | f1 | +0.087 | 7/9 | 0.039 |
| ours_root_d − vicon_d | auc | +0.189 | 7/9 | 0.027 |
| ours_root_d − vicon_d | f1 | +0.239 | 8/9 | 0.008 |
| ours_root_d − kinect_d | auc | -0.001 | 5/9 | 0.820 |
| ours_root_d − kinect_d | f1 | +0.033 | 5/9 | 0.820 |
| ours_root_d − raw_2d_d | auc | +0.052 | 6/9 | 0.301 |
| ours_root_d − raw_2d_d | f1 | +0.075 | 7/9 | 0.074 |
| kinect_d − vicon_pts_d | auc | +0.027 | 5/9 | 0.496 |
| kinect_d − vicon_pts_d | f1 | +0.054 | 6/9 | 0.426 |
| ours_root_d − ours_screen_d | auc | +0.065 | 8/9 | 0.039 |
| ours_root_d − ours_screen_d | f1 | +0.033 | 6/9 | 0.359 |
