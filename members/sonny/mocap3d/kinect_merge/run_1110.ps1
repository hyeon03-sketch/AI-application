# 11/10: Euijin asked for 3 seeds of the final recipe (kin_w_r24 = flag + kweight + Kinect groups + REHAB24).
# Seed 0 is in km/kin_w_r24; seed 1 of P1P2->P3 is in km/x1109_seed1 (not rerun). One job at a time. Outputs stay on E:.
$py = "E:\mocap3d_env\Scripts\python.exe"
$out = "E:/KERAAL_mocap3d/km/kin_w_r24"
foreach ($seed in 1, 2) {
    foreach ($f in @(@("P1,P2", "P3"), @("P1,P3", "P2"), @("P2,P3", "P1"))) {
        $name = ($f[0] -replace ",", "") + "_" + $f[1] + "_s$seed"
        if ((Test-Path "$out/$name/results.json") -or (Test-Path "E:/KERAAL_mocap3d/km/x1109_seed1/$name/results.json")) { "skip $name"; continue }
        & $py -u km_train.py "$out/run_$name" --train-parts $f[0] --eval-parts $f[1] --seed $seed --flag --kweight `
            --kinect group2A,group2B,group1B --rehab24 E:/REHAB24-6/aspset_format/rehab24_det.npz *> "$out/$name.log"
        "fold $name exit $LASTEXITCODE"
    }
}
