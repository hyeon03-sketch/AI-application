"""model_input CSV의 라벨 열만 읽어 학습 전 점검 요약(txt)을 만든다 (특징 열은 읽지 않아 가볍다).
사용: python summarize_model_input.py --csv "C:\\EJ\\Keraal\\input_data\\model_input_blazepose.csv" --out "C:\\EJ\\Keraal\\input_data\\summary_blazepose.txt"
필요: pip install pandas
"""
import argparse
import pandas as pd

LAB = ["sample_id", "group", "exercise_code", "participant_key", "frame_idx", "error_type", "body_part",
       "label_source", "in_annotated_span", "skeleton_truncated", "second_idx", "sec_error_type",
       "sec_body_part", "sec_n_frames", "sec_boundary"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = pd.read_csv(a.csv, usecols=LAB, dtype=str)
    d["frame_idx"] = d["frame_idx"].astype(int)
    L = []
    p = L.append
    p(f"파일: {a.csv}\n행 수: {len(d)}, 녹화 수: {d.sample_id.nunique()}")
    x = d[d.label_source == "anvil_time"]
    p(f"\n[1A/2A] 프레임 {len(x)}, 녹화 {x.sample_id.nunique()}")
    p("in_annotated_span 별 프레임 수 / 오류 프레임 비율")
    for k, g in x.groupby("in_annotated_span"):
        p(f"  span={k}: {len(g)} 프레임, 오류 비율 {(g.error_type != 'none').mean():.1%}")
    y = x[x.in_annotated_span == "yes"]
    p("\n[1A/2A, 주석 구간(yes)만] 오류유형 x 신체부위 프레임 수")
    p(y.groupby(["error_type", "body_part"]).size().to_string())
    p("\n[1A/2A, 주석 구간(yes)만] 참가자 x 오류유형 프레임 수")
    p(y.pivot_table(index="participant_key", columns="error_type", values="frame_idx", aggfunc="count", fill_value=0).to_string())
    p("\n[1A/2A] 운동 x 오류유형 프레임 수 (yes만)")
    p(y.pivot_table(index="exercise_code", columns="error_type", values="frame_idx", aggfunc="count", fill_value=0).to_string())
    t = d.drop_duplicates("sample_id")
    p(f"\n[잘린 스켈레톤] skeleton_truncated=yes 녹화 {int((t.skeleton_truncated == 'yes').sum())} / {len(t)}")
    p(t.groupby(["group", "skeleton_truncated"]).size().to_string())
    s = x[x.sec_n_frames.astype(int) >= x.sec_n_frames.astype(int).max()]
    s = s.drop_duplicates(["sample_id", "second_idx"])
    p(f"\n[1A/2A 초 단위(완전한 초만)] {len(s)}초, 오류 초 비율 {(s.sec_error_type != 'none').mean():.1%}")
    p(s.groupby(["sec_error_type", "sec_body_part"]).size().to_string())
    g3 = d[d.label_source != "anvil_time"]
    if len(g3):
        p("\n[Group3 약라벨] 참가자 x 오류유형 프레임 수")
        p(g3.pivot_table(index="participant_key", columns="error_type", values="frame_idx", aggfunc="count", fill_value=0).to_string())
    open(a.out, "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))
    print("\n저장:", a.out)

if __name__ == "__main__":
    main()
