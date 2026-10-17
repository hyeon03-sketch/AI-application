"""KERAAL: 영상 길이 vs 주석 종료시각 vs Kinect/BlazePose 길이 일괄 비교 (영상을 열어볼 필요 없음).

사용:  python check_video_alignment.py --root "C:\\EJ\\Keraal\\data" --out "C:\\EJ\\Keraal\\input_data\\video_alignment.csv"
필요:  pip install opencv-python   (없으면 ffprobe가 있을 때 그걸 사용)
"""
import argparse, csv, json, re, subprocess, sys
from pathlib import Path

def video_info(p: Path):
    try:
        import cv2
        c = cv2.VideoCapture(str(p))
        fps, n = c.get(cv2.CAP_PROP_FPS), int(c.get(cv2.CAP_PROP_FRAME_COUNT))
        c.release()
        if fps and n:
            return fps, n, n / fps
    except ImportError:
        pass
    try:
        o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
                            "-show_entries", "stream=r_frame_rate,nb_read_packets", "-of", "json", str(p)],
                           capture_output=True, text=True, check=True).stdout
        s = json.loads(o)["streams"][0]
        a, b = s["r_frame_rate"].split("/")
        fps, n = float(a) / float(b), int(s["nb_read_packets"])
        return fps, n, n / fps
    except Exception:
        return None, None, None

def anvil_end(p: Path):
    if not p.exists():
        return None
    raw = p.read_bytes()
    t = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig", "replace")
    e = [float(x) for x in re.findall(r'end="([\d.]+)"', t)]
    return max(e) if e else None

def nlines(p: Path):
    if not p.exists():
        return None
    with p.open("r", errors="ignore") as f:
        return sum(1 for l in f if l.strip())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--groups", default="1A,2A")
    a = ap.parse_args()
    rows = []
    for g in a.groups.split(","):
        gd = a.root / f"group{g}"
        vids = sorted((gd / "videos").glob("*.mp4"))
        for i, v in enumerate(vids, 1):
            rest = v.stem.split("-Anon-", 1)[-1]          # CTK-R1-Brest-022
            fps, nfr, dur = video_info(v)
            kin = nlines(gd / "kinect" / f"G{g}-Kinect-{rest}.txt")
            ea = anvil_end(gd / "annotatorA" / f"G{g}-{rest}.anvil")
            eb = anvil_end(gd / "annotatorB" / f"G{g}-{rest}.anvil")
            rows.append(dict(group=g, recording=f"G{g}-{rest}", video_fps=fps, video_frames=nfr,
                             video_sec=None if dur is None else round(dur, 2), kinect_frames=kin,
                             kinect_sec_at15=None if kin is None else round(kin / 15, 2),
                             annotA_end=ea, annotB_end=eb,
                             A_over_video=None if not (ea and dur) else round(ea / dur, 3),
                             B_over_video=None if not (eb and dur) else round(eb / dur, 3)))
            if i % 25 == 0:
                print(f"group{g}: {i}/{len(vids)}", flush=True)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    def stat(key):
        v = sorted(r[key] for r in rows if r[key] is not None)
        return f"n={len(v)} min={v[0]} median={v[len(v)//2]} max={v[-1]}" if v else "없음"
    print("\n영상 fps :", stat("video_fps"))
    print("annotatorA 종료/영상길이 :", stat("A_over_video"))
    print("annotatorB 종료/영상길이 :", stat("B_over_video"))
    near = sum(1 for r in rows if r["A_over_video"] and abs(r["A_over_video"] - 1) < 0.05)
    print(f"A 종료가 영상 길이와 5% 이내로 일치: {near}/{len(rows)}")
    print("저장:", a.out)

if __name__ == "__main__":
    main()
