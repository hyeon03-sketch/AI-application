# 11/9 morning: is the 1A drop (57 -> 61 mm) from REHAB24 or seed noise? One job per call:
#   .\run_1109.ps1 frac33  -> P1P2->P3 fold, 1/3 of REHAB24 training recordings, seed 0
#   .\run_1109.ps1 seed1   -> P1P2->P3 fold, full REHAB24, seed 1
# Each then scores its weights on 1A against Kinect (eval_1a.py). Outputs stay on E:.
param([string]$job)
$py = "E:\mocap3d_env\Scripts\python.exe"
$out = "E:/KERAAL_mocap3d/km/x1109_$job"
New-Item -ItemType Directory -Force $out | Out-Null
$extra = @{ frac33 = @("--rehab-frac", "0.33", "--seed", "0"); seed1 = @("--seed", "1") }[$job]
$seed = if ($job -eq "seed1") { 1 } else { 0 }
& $py -u km_train.py "$out/run_P1P2_P3_s$seed" --train-parts P1,P2 --eval-parts P3 --flag --kweight `
    --kinect group2A,group2B,group1B --rehab24 E:/REHAB24-6/aspset_format/rehab24_det.npz @extra *> "$out/train.log"
"train exit $LASTEXITCODE"
& $py eval_1a.py "$out/eval_1a.json" "m=$out/run_P1P2_P3_s$seed/best.pt@flag" *> "$out/eval_1a.log"
"eval_1a exit $LASTEXITCODE"
