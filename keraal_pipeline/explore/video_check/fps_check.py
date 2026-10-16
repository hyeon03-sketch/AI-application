"""Compare video frame counts, Kinect frame counts and annotation end times."""
import re, subprocess, glob, os, statistics as st
R = "E:/KERAAL_data/extracted"

def nframes(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
                          "-show_entries", "stream=avg_frame_rate,nb_read_packets", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    fr, n = out.split(",")[:2]
    return eval(fr), int(n)

def read_anvil(p):
    b = open(p, "rb").read()
    t = b.decode("utf-16") if b[:2] in (b"\xff\xfe", b"\xfe\xff") else b.decode("utf-8", "ignore")
    ge = re.search(r'name="Global evaluation".*?<el[^>]*start="([\d.]+)" end="([\d.]+)"', t, re.S)
    return (float(ge.group(1)), float(ge.group(2))) if ge else None

rows = []
for g in ["group1A", "group2A"]:
    for v in sorted(glob.glob(f"{R}/{g}/videos/*.mp4")):
        name = os.path.basename(v).replace("-Anon-", "-").replace(".mp4", "")
        kin = f"{R}/{g}/kinect/" + os.path.basename(v).replace("-Anon-", "-Kinect-").replace(".mp4", ".txt")
        kn = sum(1 for _ in open(kin)) if os.path.exists(kin) else None
        fps, vn = nframes(v)
        ends = {}
        for a in ["annotatorA", "annotatorB"]:
            p = f"{R}/{g}/{a}/{name}.anvil"
            if os.path.exists(p):
                r = read_anvil(p)
                if r: ends[a] = r[1]
        rows.append((g, name, fps, vn, kn, ends))

for g in ["group1A", "group2A"]:
    rs = [r for r in rows if r[0] == g]
    print(f"== {g}: {len(rs)} videos, fps set={set(r[2] for r in rs)}")
    print("  video frames == kinect frames:", sum(r[3] == r[4] for r in rs), "/", len(rs),
          "| diffs:", sorted(set(r[3] - r[4] for r in rs if r[4] is not None)))
    for a in ["annotatorA", "annotatorB"]:
        ratio = [r[5][a] / (r[3] / r[2]) for r in rs if a in r[5]]
        implied = [r[3] / r[5][a] for r in rs if a in r[5]]
        print(f"  {a}: n={len(ratio)} end/duration median={st.median(ratio):.3f} "
              f"min={min(ratio):.3f} max={max(ratio):.3f} | implied fps median={st.median(implied):.2f} "
              f"IQR=({st.quantiles(implied, n=4)[0]:.2f},{st.quantiles(implied, n=4)[2]:.2f})")

g3 = sorted(glob.glob(f"{R}/group3/videos/*"))
s = [nframes(v) + (sum(1 for _ in open(f"{R}/group3/kinect/" + os.path.basename(v).replace("-Anon-", "-Kinect-").rsplit(".", 1)[0] + ".txt")),) for v in g3]
print(f"== group3: {len(s)} videos, fps set={set(x[0] for x in s)}, kinect-video diffs={sorted(set(x[2]-x[1] for x in s))}")
