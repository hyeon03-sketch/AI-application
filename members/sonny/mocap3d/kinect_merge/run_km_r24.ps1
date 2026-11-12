# KERAAL + REHAB24 together: final recipe (flag_kin_w) + --rehab24, 3 LOPO folds, one at a time (parallel was ~10x slower).
# REHAB24 gets flag 1 (its skeleton is closer to Kinect than ASPset: spine-neck 213 vs 190 vs 412 mm). Outputs stay on E:.
$py = "E:\mocap3d_env\Scripts\python.exe"
$out = "E:/KERAAL_mocap3d/km/kin_w_r24"
New-Item -ItemType Directory -Force $out | Out-Null
foreach ($f in @(@("P1,P2", "P3"), @("P1,P3", "P2"), @("P2,P3", "P1"))) {
    $name = ($f[0] -replace ",", "") + "_" + $f[1]
    & $py -u km_train.py "$out/run_${name}_s0" --train-parts $f[0] --eval-parts $f[1] --flag --kweight `
        --kinect group2A,group2B,group1B --rehab24 E:/REHAB24-6/aspset_format/rehab24_det.npz *> "$out/$name.log"
    "fold $name exit $LASTEXITCODE"
}
