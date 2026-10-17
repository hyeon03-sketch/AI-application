#!/usr/bin/env python3
"""
keraal_parse_annotations.py — KERAAL 데이터셋 Anvil XML 주석 파서 (초안)

목적
----
KERAAL 데이터셋(그룹 1A/2A의 Anvil XML 주석 + 그룹3의 파일명 라벨)을 파싱해
- 녹화 단위(one row per recording) master CSV
- 시간 구간(temporal segment) 단위 long-format CSV
- 오류유형 x 신체부위 교차표
- QC 리포트 (결측치, 클래스 불균형, 참가자 중복 등)
를 생성한다.

전제 / 주의
-----------
* 최초 초안(2026-09-28)은 실제 KERAAL zip 없이(샌드박스 egress 차단, HTTP 403)
  keraalSpec.xml / createAnvil.py / readme_files_format.txt만 보고 작성되었다.
* 2026-09-29, 공식 샘플 zip(keraal_sample_2022.zip, 팀원이 직접 다운로드해 업로드)을
  실제로 열어서 아래 [A][B][C][D] 가정을 재검증했다. 그 결과 [A]는 최초 가정이
  상당 부분 틀렸던 것으로 확인되어 정규식/디렉터리명을 실제 구조에 맞게 다시 썼다.
  다만 샘플에는 참가자가 그룹당 1명뿐이라 참가자ID 포맷의 전체 다양성(예: 두 자리
  숫자, 다른 site 이름 등)은 여전히 완전히 검증되지 않았다 — 전체 데이터셋을 받으면
  inspect로 다시 한번 확인할 것.

확인 상태 (2026-09-29 실제 샘플 기준)
------------------------------------------
  [A] 파일명 구조 — 검증 완료, 정규식 반영함:
      · 1A/2A: G{group}-{modality}-{exercise}-{participant}-{site}-{recording}
               예) G1A-Kinect-CTK-R1-Brest-022
      · 1B/2B: G{group}-{modality}-{exercise}-{site}-{recording}  (참가자 토큰 없음!)
               예) G1B-Kinect-CTK-Brest-007
      · 3    : G3-{modality}-{exercise}-{participant}{trial}-{site}-{label}-{recording}
               예) G3-Kinect-CTK-P1T1-Unknown-E1B1-0
      구분자는 실제로 '-'만 쓰인다 (readme_files_format.txt가 '_'라고 적은 건 오기).
      또한 주석 폴더명은 "annotations"가 아니라 "annotator", 확장자는 ".anvil"이었다
      (최초 가정 둘 다 틀렸었음 — 이번에 수정).
  [B] Group3 바디파트 인코딩 — 라벨 형식 자체는 확인됨('C' 또는 'E<n>B<m>', 예:
      'E2B1'), 정규식도 이에 맞게 수정함. 하지만 인덱스(B1, B2, ...)가 실제로
      LeftArm/RightArm/BothArms/Spine 중 무엇에 대응하는지는 **여전히 미확정** —
      샘플엔 참고할 만한 신체부위 XML 라벨이 없어서 LabellisationDesVideos_fr.pdf
      대조가 계속 필요하다.
  [C] "Temporal error" 트랙 — 샘플로 확인한 2개의 실제 .anvil 파일(G1A, G2A)에는
      이 트랙 자체가 아예 존재하지 않았다 (Global evaluation / Global error만 있음).
      즉 최소한 일부 녹화에서는 0개일 수 있다는 것은 확인됐지만, 표본이 2개뿐이라
      "여러 개 존재하는 경우가 있는지"는 여전히 미확정.
  [D] bodyPart/Evaluation(중요도) 결측 — 확인됨: evaluation=Correct/error type=none인
      경우 <attribute name="bodyPart">, <attribute name="Evaluation"> 태그 자체가
      통째로 없다(빈 문자열이 아니라 태그 부재). 이 스크립트의 MISSING 처리 방식과
      일치함 — 별도 수정 불필요.

사용법
------
  # 1) 먼저 파일명 패턴이 맞는지만 확인 (파싱 없이 목록만 출력)
  python keraal_parse_annotations.py inspect --root /path/to/keraal

  # 2) 실제 파싱 실행
  python keraal_parse_annotations.py parse --root /path/to/keraal --outdir ./keraal_parsed

  # 3) 합성 데이터로 자체 테스트 (실제 데이터 없이 스크립트 동작만 검증)
  python keraal_parse_annotations.py selftest --outdir ./keraal_selftest

디렉터리 구조 (2026-09-29 실제 샘플로 검증됨)
--------------------------------------
  <root>/
    group1A/
      annotator/*.anvil      <- Anvil XML, 확장자는 .anvil (Global evaluation, Global error)
      kinect/*.txt
      openpose/*.json, blazepose/*.json, videos/*.mp4
    group2A/
      annotator/*.anvil
      kinect/*.txt
    group3/
      kinect/*.txt           <- 파일명 자체에 라벨 포함('C' 또는 'E<n>B<m>'), XML 주석 없음
      vicon/*.txt, openpose/*.json, blazepose/*.json, videos/*.avi
    group1B/, group2B/       <- 라벨 없음, 참가자ID 토큰도 없음 (선택적으로 목록만 수집)

의존성
------
표준 라이브러리 + defusedxml (있으면 사용, 없으면 xml.etree로 폴백; 신뢰되지 않는
XML을 열 가능성을 감안해 defusedxml을 우선한다).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

try:
    from defusedxml import ElementTree as ET  # type: ignore
except ImportError:  # pragma: no cover - fallback only
    import xml.etree.ElementTree as ET  # nosec - fallback if defusedxml unavailable


# --------------------------------------------------------------------------
# 허용값 (keraalSpec.xml 기준) — QC에서 스펙 밖 값이 나오면 경고
# --------------------------------------------------------------------------

VALID_EVALUATION = {"Correct", "Incorrect", "Incomplete", "Motionless"}
VALID_ERROR_TYPE = {"none", "Error1", "Error2", "Error3", "Other"}
VALID_SEVERITY = {"SmallError", "LargeError"}
VALID_BODYPART = {"LeftArm", "RightArm", "BothArms", "Spine"}
MISSING = "MISSING"

EXERCISE_CODES = {"RTK": "torso_rotation", "ELK": "flank_stretch", "CTK": "hiding_face"}


# --------------------------------------------------------------------------
# 데이터 구조
# --------------------------------------------------------------------------

@dataclass
class TemporalSegment:
    recording_id: str
    start: str
    end: str
    error_type: str
    severity: str
    body_part: str


@dataclass
class LabelSegment:
    """.anvil <el start end> 한 개 = 시간 구간 라벨 한 개 (2026-10-05 추가).

    실제 샘플 확인: 시간 정보는 'Temporal error' 트랙이 아니라 'Global error' /
    'Global evaluation' 트랙의 <el start="0" end="20">에 들어 있다. (단위: 초)
    """
    recording_id: str
    group: str
    exercise_code: str
    participant_id: str
    track: str                 # "Global error" | "Global evaluation" | "Temporal error"
    start_sec: float
    end_sec: float
    evaluation: str            # Global evaluation 트랙일 때만 의미 있음
    error_type: str
    severity: str
    body_part: str


@dataclass
class RecordingRecord:
    recording_id: str          # 우리가 부여하는 고유 키 (source_file 기반)
    group: str                 # 1A / 2A / 3 / 1B / 2B
    exercise_code: str         # RTK / ELK / CTK / UNKNOWN
    exercise_name: str
    participant_id: str
    trial_id: str              # group3만 해당, 그 외는 ""
    source_file: str           # 원본 파일 경로 (문자열)
    label_source: str          # "xml" | "filename" | "none"
    global_evaluation: str
    global_error_type: str
    global_severity: str
    global_body_part: str
    n_temporal_segments: int
    raw_group3_label: str = ""  # group3 파일명에서 추출한 원본 라벨 문자열
    parse_warnings: str = ""
    # --- 프레임 단위 라벨링용 (2026-10-05 추가) ---
    n_frames: int = 0               # kinect 파일 줄 수 (= 프레임 수)
    duration_sec: float = 0.0       # n_frames / fps
    n_error_segments: int = 0       # Global error 트랙의 구간 수 (type != none)
    error_start_sec: str = ""       # 오류 구간 시작(최소)
    error_end_sec: str = ""         # 오류 구간 끝(최대)
    error_coverage: str = ""        # 오류 구간 길이 합 / 녹화 길이 (0~1)
    partial_error: str = ""         # "yes": 오류가 녹화 일부에만 걸림 / "no": 전체 또는 오류없음


# --------------------------------------------------------------------------
# 파일명 파싱 (그룹 1A/1B/2A/2B, 그룹 3)
# --------------------------------------------------------------------------

# 2026-09-29 keraal_sample_2022.zip 실제 샘플로 검증 완료 (더 이상 추정 아님):
#   1A/2A : G{group}-{modality}-{exercise}-{participant}-{site}-{recording}
#           예) G1A-Kinect-CTK-R1-Brest-022 , G2A-Kinect-CTK-S1-Brest-029
#   1B/2B : G{group}-{modality}-{exercise}-{site}-{recording}   (참가자 토큰 없음!)
#           예) G1B-Kinect-CTK-Brest-007
#   3     : G3-{modality}-{exercise}-{participant}{trial}-{site}-{label}-{recording}
#           예) G3-Kinect-CTK-P1T1-Unknown-C-0 , G3-Kinect-CTK-P1T2-Unknown-E2B1-0
#   - 구분자는 실제로 '-'만 사용됨 (readme_files_format.txt는 '_'라고 잘못 기술함).
#   - site 토큰은 1A/1B/2A/2B는 실제 지명("Brest"), group3는 문자 그대로 "Unknown".
#   - group3 라벨 형식은 'C'(Correct) 또는 'E<n>B<m>'(Error n, Bodypart 인덱스 m) —
#     이전 초안이 가정했던 'Error1Bodypart1' 형식이 아니었다.
#   - 다만 샘플은 참가자 1명(P1/R1/S1)뿐이라 여러 참가자 ID 포맷은 여전히 확인 필요.
_SEP = r"[-_]"  # 실제로는 '-'만 나오지만 하위호환을 위해 '_'도 허용

# modality 토큰은 kinect/openpose/blazepose/videos 파일에는 있지만(Kinect/OP/BP/Anon),
# .anvil 주석 파일에는 없다 (예: "G1A-CTK-R1-Brest-022.anvil" vs
# "G1A-Kinect-CTK-R1-Brest-022.txt") — 확인됨(2026-09-29). 그래서 modality는 알려진
# 값 목록으로 한정하고 통째로 옵셔널로 둬서 둘 다 매칭되게 한다.
_MODALITY = r"(?:Kinect|OP|BP|Anon|Vicon)"

RE_GROUP_1_2 = re.compile(
    rf"G(?P<group>1A|1B|2A|2B){_SEP}(?:(?P<modality>{_MODALITY}){_SEP})?"
    rf"(?P<exercise>RTK|ELK|CTK){_SEP}"
    rf"(?:(?P<participant>[A-Za-z]+\d+){_SEP})?"  # 1A/2A만 존재, 1B/2B는 없음
    rf"(?P<site>[A-Za-z]+){_SEP}(?P<recording>[A-Za-z0-9]+)",
    re.IGNORECASE,
)

RE_GROUP_3 = re.compile(
    rf"G3{_SEP}(?P<modality>\w+){_SEP}(?P<exercise>RTK|ELK|CTK){_SEP}"
    rf"(?P<participant>[A-Za-z]+\d+?)(?P<trial>T\d+)?{_SEP}"
    rf"(?P<site>[A-Za-z]+){_SEP}"
    rf"(?P<label>[A-Za-z0-9]+){_SEP}(?P<recording>[A-Za-z0-9]+)",
    re.IGNORECASE,
)

# group3 라벨: 'C' = Correct, 'E<n>' 또는 'E<n>B<m>' = ErrorN (+ BodyPart 인덱스 m)
RE_G3_LABEL = re.compile(r"^E(?P<err>\d+)(?:B(?P<bp>\d+))?$", re.IGNORECASE)


def parse_filename_group1_2(path: Path) -> Optional[dict]:
    m = RE_GROUP_1_2.search(path.stem)
    if not m:
        return None
    d = m.groupdict()
    return {
        "group": d["group"].upper(),
        "exercise_code": d["exercise"].upper(),
        "participant_id": d.get("participant") or "",  # 1B/2B는 빈 문자열
        "site_raw": d["site"],
        "recording_id_raw": d["recording"],
    }


def parse_filename_group3(path: Path) -> Optional[dict]:
    m = RE_GROUP_3.search(path.stem)
    if not m:
        return None
    d = m.groupdict()
    return {
        "group": "3",
        "exercise_code": d["exercise"].upper(),
        "participant_id": d["participant"],
        "trial_id": d.get("trial") or "",
        "site_raw": d["site"],
        "raw_label": d["label"],
        "recording_id_raw": d["recording"],
    }


def decode_group3_label(raw_label: str) -> dict:
    """Group3 파일명 라벨('C', 'E1', 'E2B1' 등)을 최대한 분해한다.

    2026-09-29 실제 샘플(keraal_sample_2022.zip)로 형식을 확인함: 'C' 또는
    'E<오류번호>[B<신체부위 인덱스>]'. 다만 신체부위 인덱스(B1, B2, ...)가
    실제로 LeftArm/RightArm/BothArms/Spine 중 무엇을 가리키는지는 여전히
    미확정이다 (확인 필요 [B]) — 라벨링 가이드(프랑스어 원본) 대조 필요.
    """
    out = {
        "global_evaluation": MISSING,
        "global_error_type": MISSING,
        "global_body_part": MISSING,
        "warning": "",
    }
    label = raw_label.strip()
    if label.upper() == "C":
        out["global_evaluation"] = "Correct"
        out["global_error_type"] = "none"
        return out

    m = RE_G3_LABEL.match(label)
    if m:
        out["global_evaluation"] = "Incorrect"
        out["global_error_type"] = f"Error{m.group('err')}"
        if m.group("bp"):
            # 인덱스만 기록하고 실제 이름 매핑은 미확정 상태로 남김 (확인 필요 [B])
            out["global_body_part"] = f"BodypartIndex{m.group('bp')}(매핑 미확인)"
    else:
        out["warning"] = f"라벨에서 오류유형을 추출하지 못함: '{raw_label}'"
    return out


# --------------------------------------------------------------------------
# Anvil XML 파싱 (그룹 1A / 2A)
# --------------------------------------------------------------------------

def _attr_value(el, name: str) -> str:
    """<el> 안의 <attribute name="...">value</attribute>를 찾아 텍스트 반환.

    속성 태그 자체가 없거나(예: 이 <el>에 bodyPart 속성이 아예 없음),
    있지만 내용이 빈 문자열인 경우(예: <attribute name="bodyPart"></attribute>,
    의사가 값을 비워둔 경우) 모두 MISSING으로 통일한다. 두 경우를 구분해야 할
    필요가 생기면 반환값을 (value, found_tag: bool) 튜플로 바꿀 것.
    """
    for attr in el.findall("attribute"):
        if attr.get("name") == name:
            text = (attr.text or "").strip()
            return text if text else MISSING
    return MISSING


def parse_anvil_xml(xml_path: Path) -> dict:
    """Anvil XML 한 개를 파싱해 global 평가/오류 + temporal 구간 리스트를 반환.

    createAnvil.py 기준 구조:
      <annotation>
        <head>...<video src="..."/></head>
        <body>
          <track name="Global evaluation">
            <el index="0" start="0" end="...">
              <attribute name="evaluation">Correct</attribute>
            </el>
          </track>
          <track name="Global error">
            <el index="0" start="0" end="...">
              <attribute name="type">Error1</attribute>
              <attribute name="Evaluation">SmallError</attribute>   (확인 필요 [D])
              <attribute name="bodyPart">LeftArm</attribute>        (확인 필요 [D])
            </el>
          </track>
          <track name="Temporal error">
            <el index="0" start="12.3" end="18.9">
              <attribute name="type">Error1</attribute>
              <attribute name="Evaluation">SmallError</attribute>
              <attribute name="bodyPart">LeftArm</attribute>
            </el>
            ... (확인 필요 [C]: 여러 개 존재 가능) ...
          </track>
        </body>
      </annotation>
    """
    result = {
        "global_evaluation": MISSING,
        "global_error_type": MISSING,
        "global_severity": MISSING,
        "global_body_part": MISSING,
        "temporal_segments": [],  # list[dict(start,end,error_type,severity,body_part)]
        # Global evaluation / Global error 트랙의 <el start end>를 구간으로 보존
        "label_segments": [],     # list[dict(track,start,end,evaluation,error_type,severity,body_part)]
        "warnings": [],
    }

    try:
        raw = xml_path.read_bytes()
        if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):          # UTF-16 (annotatorA 실제 파일)
            text = raw.decode("utf-16")
        else:
            text = raw.decode("utf-8-sig", errors="replace")
        text = re.sub(r"^\s*<\?xml[^>]*\?>", "", text)          # 인코딩 선언 제거 (str 파싱용)
        root = ET.fromstring(text.strip())
    except Exception as exc:  # noqa: BLE001 - 파싱 실패는 QC로 넘긴다
        result["warnings"].append(f"XML 파싱 실패: {exc}")
        return result

    body = root.find("body")
    if body is None:
        result["warnings"].append("<body> 태그를 찾지 못함")
        return result

    for track in body.findall("track"):
        track_name = track.get("name", "")
        els = track.findall("el")

        if track_name == "Global evaluation":
            if not els:
                result["warnings"].append("Global evaluation 트랙에 <el> 없음")
            for el in els:
                val = _attr_value(el, "evaluation")
                result["global_evaluation"] = val
                result["label_segments"].append({
                    "track": track_name, "start": el.get("start", ""), "end": el.get("end", ""),
                    "evaluation": val, "error_type": MISSING, "severity": MISSING, "body_part": MISSING,
                })
                if val not in VALID_EVALUATION and val != MISSING:
                    result["warnings"].append(f"스펙 밖 evaluation 값: '{val}'")

        elif track_name == "Global error":
            if not els:
                result["warnings"].append("Global error 트랙에 <el> 없음")
            for el in els:
                etype = _attr_value(el, "type")
                sev = _attr_value(el, "Evaluation")
                bpart = _attr_value(el, "bodyPart")
                result["global_error_type"] = etype
                result["global_severity"] = sev
                result["global_body_part"] = bpart
                result["label_segments"].append({
                    "track": track_name, "start": el.get("start", ""), "end": el.get("end", ""),
                    "evaluation": MISSING, "error_type": etype, "severity": sev, "body_part": bpart,
                })
                if etype not in VALID_ERROR_TYPE and etype != MISSING:
                    result["warnings"].append(f"스펙 밖 error type 값: '{etype}'")
                if sev not in VALID_SEVERITY and sev != MISSING:
                    result["warnings"].append(f"스펙 밖 severity 값: '{sev}'")
                if bpart not in VALID_BODYPART and bpart != MISSING:
                    result["warnings"].append(f"스펙 밖 bodyPart 값: '{bpart}'")

        elif track_name == "Temporal error":
            for el in els:
                seg = {
                    "start": el.get("start", ""),
                    "end": el.get("end", ""),
                    "error_type": _attr_value(el, "type"),
                    "severity": _attr_value(el, "Evaluation"),
                    "body_part": _attr_value(el, "bodyPart"),
                }
                result["temporal_segments"].append(seg)

    return result


# --------------------------------------------------------------------------
# 그룹별 수집 로직
# --------------------------------------------------------------------------

def find_annotator_dir(group_dir: Path) -> Path:
    """annotatorA/annotatorB (실제 데이터) 또는 annotator (공식 샘플) 폴더를 찾는다."""
    for name in (f"annotator{ANNOTATOR}", "annotator", "annotations"):
        d = group_dir / name
        if d.exists():
            return d
    return group_dir / f"annotator{ANNOTATOR}"


def list_anvil(ann_dir: Path) -> list[Path]:
    """숨김 파일(.anvil 등 '.'로 시작) 제외한 주석 파일 목록."""
    if not ann_dir.exists():
        return []
    files = list(ann_dir.glob("*.anvil")) + list(ann_dir.glob("*.xml"))
    return sorted(f for f in files if not f.name.startswith("."))


def collect_group_1_2(root: Path, group: str, warnings_out: list[str]) -> list[RecordingRecord]:
    """그룹 1A/2A (XML 주석 있음) 또는 1B/2B (주석 없음, kinect 파일만) 수집."""
    group_dir = root / f"group{group}"
    records: list[RecordingRecord] = []

    # 2026-09-29 실제 샘플 확인: 폴더명은 "annotations"가 아니라 "annotator"이고,
    # 확장자는 ".anvil"이다 (내용은 여전히 XML). 이전 초안의 가정이 둘 다 틀렸었음.
    ann_dir = find_annotator_dir(group_dir)
    kinect_dir = group_dir / "kinect"

    xml_files = list_anvil(ann_dir)
    kinect_files = sorted(kinect_dir.glob("*.txt")) if kinect_dir.exists() else []

    if not xml_files and not kinect_files:
        warnings_out.append(f"[group{group}] annotator/ 또는 kinect/ 폴더를 찾지 못함: {group_dir}")
        return records

    # XML이 있는 경우: XML을 기준으로, 같은 이름의 kinect 파일을 매칭 시도
    if xml_files:
        for xml_path in xml_files:
            meta = parse_filename_group1_2(xml_path)
            if meta is None:
                warnings_out.append(f"[group{group}] 파일명 패턴 불일치 (정규식 확인 필요 [A]): {xml_path.name}")
                continue

            parsed = parse_anvil_xml(xml_path)
            exercise_code = meta["exercise_code"]
            # 같은 녹화의 kinect 파일에서 프레임 수 확인 (.anvil 파일명엔 modality 토큰이 없다)
            prefix = f"G{group}-"
            k_name = f"{prefix}Kinect-{xml_path.stem[len(prefix):]}.txt"
            n_frames = count_lines(kinect_dir / k_name)
            rec = RecordingRecord(
                recording_id=xml_path.stem,
                group=group,
                exercise_code=exercise_code,
                exercise_name=EXERCISE_CODES.get(exercise_code, "UNKNOWN"),
                participant_id=meta["participant_id"],
                trial_id="",
                source_file=str(xml_path),
                label_source="xml",
                global_evaluation=parsed["global_evaluation"],
                global_error_type=parsed["global_error_type"],
                global_severity=parsed["global_severity"],
                global_body_part=parsed["global_body_part"],
                n_temporal_segments=len(parsed["temporal_segments"]),
                parse_warnings="; ".join(parsed["warnings"]),
                n_frames=n_frames,
            )
            records.append(rec)

            for seg in parsed["label_segments"] + [
                {**s, "track": "Temporal error", "evaluation": MISSING} for s in parsed["temporal_segments"]
            ]:
                try:
                    s_sec, e_sec = float(seg["start"]), float(seg["end"])
                except ValueError:
                    rec.parse_warnings += "; 구간 시간 파싱 실패"
                    continue
                LABEL_SEGMENTS.append(LabelSegment(
                    recording_id=rec.recording_id, group=group, exercise_code=exercise_code,
                    participant_id=rec.participant_id, track=seg["track"],
                    start_sec=s_sec, end_sec=e_sec, evaluation=seg["evaluation"],
                    error_type=seg["error_type"], severity=seg["severity"], body_part=seg["body_part"],
                ))

            for seg in parsed["temporal_segments"]:
                TEMPORAL_SEGMENTS.append(
                    TemporalSegment(
                        recording_id=rec.recording_id,
                        start=seg["start"],
                        end=seg["end"],
                        error_type=seg["error_type"],
                        severity=seg["severity"],
                        body_part=seg["body_part"],
                    )
                )
    else:
        # 1B/2B: 라벨 없이 존재 목록만 수집 (향후 semi-supervised 용도)
        for kfile in kinect_files:
            meta = parse_filename_group1_2(kfile)
            if meta is None:
                warnings_out.append(f"[group{group}] 파일명 패턴 불일치 (정규식 확인 필요 [A]): {kfile.name}")
                continue
            exercise_code = meta["exercise_code"]
            records.append(
                RecordingRecord(
                    recording_id=kfile.stem,
                    group=group,
                    exercise_code=exercise_code,
                    exercise_name=EXERCISE_CODES.get(exercise_code, "UNKNOWN"),
                    participant_id=meta["participant_id"],
                    trial_id="",
                    source_file=str(kfile),
                    label_source="none",
                    global_evaluation=MISSING,
                    global_error_type=MISSING,
                    global_severity=MISSING,
                    global_body_part=MISSING,
                    n_temporal_segments=0,
                )
            )

    return records


def collect_group_3(root: Path, warnings_out: list[str]) -> list[RecordingRecord]:
    """그룹3: XML 주석이 없고, 파일명 자체가 라벨이다 (확인 필요 [B])."""
    group_dir = root / "group3"
    kinect_dir = group_dir / "kinect"
    records: list[RecordingRecord] = []

    if not kinect_dir.exists():
        warnings_out.append(f"[group3] kinect/ 폴더를 찾지 못함: {group_dir}")
        return records

    for kfile in sorted(kinect_dir.glob("*.txt")):
        meta = parse_filename_group3(kfile)
        if meta is None:
            warnings_out.append(f"[group3] 파일명 패턴 불일치 (정규식 확인 필요 [A]): {kfile.name}")
            continue

        decoded = decode_group3_label(meta["raw_label"])
        exercise_code = meta["exercise_code"]
        rec = RecordingRecord(
            recording_id=kfile.stem,
            group="3",
            exercise_code=exercise_code,
            exercise_name=EXERCISE_CODES.get(exercise_code, "UNKNOWN"),
            participant_id=meta["participant_id"],
            trial_id=meta.get("trial_id", ""),
            source_file=str(kfile),
            label_source="filename",
            global_evaluation=decoded["global_evaluation"],
            global_error_type=decoded["global_error_type"],
            global_severity=MISSING,  # group3 파일명에는 severity 정보 없음 (확인 필요)
            global_body_part=decoded["global_body_part"],
            n_temporal_segments=0,
            raw_group3_label=meta["raw_label"],
            parse_warnings=decoded["warning"],
            n_frames=count_lines(kfile),
        )
        records.append(rec)

    return records


# 모듈 레벨 버퍼 (간단함을 위해; 큰 규모로 갈 경우 클래스로 리팩터링 권장)
TEMPORAL_SEGMENTS: list[TemporalSegment] = []
LABEL_SEGMENTS: list[LabelSegment] = []

# fps: 실제 데이터에서 Kinect 프레임수 / annotatorB 종료시각 = 15.00 (샘플 영상 ffprobe는 10fps) - 영상 fps는 별도 확인 필요.
# 다른 값이면 parse --fps 로 지정. fps를 가정하지 말고 QC의 duration을 확인할 것.
DEFAULT_FPS = 15.0   # 실제 1A 8개 녹화: Kinect 프레임 수 / annotatorB 종료시각 = 15.00 (샘플 확인값 10은 영상 fps)
ANNOTATOR = "A"          # --annotator A|B  (폴더 annotatorA / annotatorB, 없으면 annotator)
SKEL_TRUNC: dict = {}   # recording_id -> (BlazePose 프레임 수, 기준 프레임 수)
INTERVAL_TRACK = "global"  # --interval-track global|temporal|auto  (프레임 라벨에 쓸 구간 트랙)


def count_lines(path: Path) -> int:
    """파일의 비어있지 않은 줄 수 (= kinect 프레임 수). 파일이 없으면 0."""
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return sum(1 for line in f if line.strip())


def error_segments_for(segs: list) -> list:
    """INTERVAL_TRACK에 따라 프레임 라벨에 쓸 오류 구간 선택 (none 제외)."""
    def ok(s):
        return s.error_type not in ("none", MISSING)
    g = [s for s in segs if s.track == "Global error" and ok(s)]
    t = [s for s in segs if s.track == "Temporal error" and ok(s)]
    if INTERVAL_TRACK == "temporal":
        return t
    if INTERVAL_TRACK == "auto":
        return t or g
    return g


def fill_coverage(records: list[RecordingRecord], fps: float) -> None:
    """레코드별 duration, 오류 구간 요약, 부분 오류 여부를 채운다."""
    by_rec: dict[str, list[LabelSegment]] = defaultdict(list)
    for s in LABEL_SEGMENTS:
        by_rec[s.recording_id].append(s)
    for k in list(by_rec):
        by_rec[k] = error_segments_for(by_rec[k])
    ends: dict[str, float] = {}
    for s in LABEL_SEGMENTS:
        if s.track == "Global evaluation":
            ends[s.recording_id] = max(ends.get(s.recording_id, 0.0), s.end_sec)
    for r in records:
        r.duration_sec = round(r.n_frames / fps, 3) if r.n_frames else 0.0
        segs = by_rec.get(r.recording_id, [])
        r.n_error_segments = len(segs)
        e = ends.get(r.recording_id)
        if r.label_source == "xml" and e and r.duration_sec and e > r.duration_sec * 1.05:
            r.parse_warnings = (r.parse_warnings + "; " if r.parse_warnings else "") + (
                f"주석 종료 {e:g}s > 스켈레톤 길이 {r.duration_sec:g}s (fps={fps:g}) -> fps/시간축 확인 필요")
        if r.label_source == "xml":
            if segs and r.duration_sec:
                covered = sum(max(0.0, min(s.end_sec, r.duration_sec) - s.start_sec) for s in segs)
                r.error_start_sec = f"{min(s.start_sec for s in segs):g}"
                r.error_end_sec = f"{max(s.end_sec for s in segs):g}"
                ratio = min(1.0, covered / r.duration_sec)
                r.error_coverage = f"{ratio:.3f}"
                r.partial_error = "yes" if ratio < 0.98 else "no"
            else:
                r.partial_error = "no"


def build_frame_rows(records: list[RecordingRecord], fps: float):
    """프레임 단위 pseudo-label 행 생성 (generator).

    - 1A/2A (label_source=xml): 오류 구간(start<=t<end)이면 그 구간의 type/bodyPart, 아니면 none.
    - Group3 (label_source=filename): 파일명 라벨을 모든 프레임에 동일하게 부여 (약라벨).
    - 1B/2B: 라벨 없음 -> 제외.
    """
    seg_by_rec: dict[str, list[LabelSegment]] = defaultdict(list)
    for s in LABEL_SEGMENTS:
        seg_by_rec[s.recording_id].append(s)

    for r in records:
        if r.label_source not in ("xml", "filename") or r.n_frames == 0:
            continue
        err_segs = error_segments_for(seg_by_rec.get(r.recording_id, []))
        ev_segs = [s for s in seg_by_rec.get(r.recording_id, []) if s.track == "Global evaluation"]
        for i in range(r.n_frames):
            t = i / fps
            if r.label_source == "xml":
                hit = next((s for s in err_segs if s.start_sec <= t < s.end_sec), None)
                ev = next((s.evaluation for s in ev_segs if s.start_sec <= t < s.end_sec), MISSING)
                et, bp, sev = (hit.error_type, hit.body_part, hit.severity) if hit else ("none", "none", "none")
                src = "anvil_time"
            else:
                et = r.global_error_type
                bp = r.global_body_part if et not in ("none", MISSING) else "none"
                sev, ev, src = r.global_severity, r.global_evaluation, "filename_whole"
            yield [r.recording_id, r.group, r.exercise_code, r.participant_id,
                   i, f"{t:.3f}", ev, et, bp, sev, src]


def write_segments_csv(segments: list[LabelSegment], out_path: Path) -> None:
    fields = list(LabelSegment.__dataclass_fields__.keys())
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for s in segments:
            writer.writerow(asdict(s))


def write_frame_labels_csv(records: list[RecordingRecord], fps: float, out_path: Path) -> int:
    header = ["recording_id", "group", "exercise_code", "participant_id", "frame_idx", "time_sec",
              "evaluation", "error_type", "body_part", "severity", "label_source"]
    n = 0
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in build_frame_rows(records, fps):
            writer.writerow(row)
            n += 1
    return n


# --------------------------------------------------------------------------
# 출력 (CSV / 교차표 / QC 리포트)
# --------------------------------------------------------------------------

def write_master_csv(records: list[RecordingRecord], out_path: Path) -> None:
    fields = list(asdict(records[0]).keys()) if records else [f.name for f in RecordingRecord.__dataclass_fields__.values()]
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in records:
            writer.writerow(asdict(r))


def write_temporal_csv(segments: list[TemporalSegment], out_path: Path) -> None:
    fields = ["recording_id", "start", "end", "error_type", "severity", "body_part"]
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for s in segments:
            writer.writerow(asdict(s))


def write_crosstab(records: list[RecordingRecord], out_path: Path) -> None:
    """오류유형 x 신체부위 교차표 (전역 라벨 기준, XML 주석 있는 그룹1A/2A만)."""
    counter: Counter[tuple[str, str]] = Counter()
    for r in records:
        if r.label_source != "xml":
            continue
        if r.global_error_type in ("none", MISSING):
            continue
        counter[(r.global_error_type, r.global_body_part)] += 1

    body_parts = sorted(VALID_BODYPART | {MISSING})
    error_types = sorted({et for (et, _bp) in counter} | {"Error1", "Error2", "Error3", "Other"})

    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["error_type"] + body_parts)
        for et in error_types:
            row = [et] + [counter.get((et, bp), 0) for bp in body_parts]
            writer.writerow(row)


def build_qc_report(records: list[RecordingRecord], segments: list[TemporalSegment],
                     collection_warnings: list[str]) -> str:
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("KERAAL 주석 파싱 QC 리포트")
    lines.append("=" * 70)

    total = len(records)
    lines.append(f"\n총 녹화 수: {total}")

    by_group = Counter(r.group for r in records)
    lines.append("\n[그룹별 녹화 수]")
    for g, c in sorted(by_group.items()):
        lines.append(f"  group{g}: {c}")

    by_group_exercise = Counter((r.group, r.exercise_name) for r in records)
    lines.append("\n[그룹 x 운동별 녹화 수]")
    for (g, ex), c in sorted(by_group_exercise.items()):
        lines.append(f"  group{g} / {ex}: {c}")

    labeled = [r for r in records if r.label_source in ("xml", "filename")]
    lines.append(f"\n라벨이 있는 녹화 수: {len(labeled)} / {total}")

    by_eval = Counter(r.global_evaluation for r in labeled)
    lines.append("\n[전역 평가(Global evaluation) 분포]")
    for k, c in sorted(by_eval.items()):
        lines.append(f"  {k}: {c}")

    by_error = Counter(r.global_error_type for r in labeled)
    lines.append("\n[전역 오류유형 분포]")
    for k, c in sorted(by_error.items()):
        lines.append(f"  {k}: {c}")

    by_bp = Counter(r.global_body_part for r in labeled)
    lines.append("\n[전역 신체부위 분포]")
    for k, c in sorted(by_bp.items()):
        lines.append(f"  {k}: {c}")

    missing_bp = [r for r in labeled if r.global_error_type not in ("none", MISSING)
                  and r.global_body_part == MISSING]
    lines.append(f"\n오류가 있는데 신체부위가 결측인 녹화 수: {len(missing_bp)}")
    if missing_bp:
        lines.append("  예시(최대 5개): " + ", ".join(r.recording_id for r in missing_bp[:5]))

    # 참가자 중복 확인 (같은 participant_id가 서로 다른 group에 걸쳐 있으면 subject leakage 위험)
    participants_by_group: dict[str, set[str]] = defaultdict(set)
    for r in records:
        participants_by_group[r.group].add(r.participant_id)
    lines.append("\n[그룹별 고유 참가자 수 (참가자 ID 매핑 방식에 따라 다를 수 있음)]")
    for g, pset in sorted(participants_by_group.items()):
        lines.append(f"  group{g}: {len(pset)}명 -> {sorted(pset)}")

    overlap_1a_1b = participants_by_group.get("1A", set()) & participants_by_group.get("1B", set())
    if overlap_1a_1b:
        lines.append(f"\n참고: group1A/1B 참가자 ID가 겹침 (같은 환자의 주석/비주석 데이터로 정상): {sorted(overlap_1a_1b)}")

    n_temporal = len(segments)
    lines.append(f"\n'Temporal error' 트랙 구간 수: {n_temporal}")

    # --- 프레임 단위 라벨링 가능성 (2026-10-05) ---
    xml_recs = [r for r in records if r.label_source == "xml"]
    err_recs = [r for r in xml_recs if r.global_error_type not in ("none", MISSING)]
    partial = [r for r in err_recs if r.partial_error == "yes"]
    lines.append("\n[프레임 단위 라벨링 점검 - Global 트랙의 start/end 기준]")
    lines.append(f"  .anvil 라벨 녹화(1A/2A): {len(xml_recs)}, 그중 오류 녹화: {len(err_recs)}")
    lines.append(f"  오류가 일부 구간에만 걸린 녹화(coverage<0.98): {len(partial)}"
                 + (f" ({len(partial) / len(err_recs):.0%} of 오류 녹화)" if err_recs else ""))
    no_frames = [r for r in xml_recs if r.n_frames == 0]
    lines.append(f"  kinect 파일을 못 찾았거나 비어있는 .anvil 녹화: {len(no_frames)}")
    over = [r for r in err_recs if r.error_end_sec and r.duration_sec
            and float(r.error_end_sec) > r.duration_sec + 0.5]
    lines.append(f"  오류 end가 녹화 길이를 넘는 녹화: {len(over)}")
    g3 = [r for r in records if r.group == "3"]
    lines.append(f"  Group3 {len(g3)}건은 파일명 라벨 -> 모든 프레임 동일 라벨(약라벨), 시간 구간 정보 없음")

    g3_warn = [r for r in records if r.group == "3" and r.parse_warnings]
    if g3_warn:
        lines.append(f"\nGroup3 라벨 해석 경고 {len(g3_warn)}건 (확인 필요 [B]):")
        for r in g3_warn[:10]:
            lines.append(f"  {r.recording_id}: raw='{r.raw_group3_label}' warning='{r.parse_warnings}'")

    all_parse_warnings = [r for r in records if r.parse_warnings and r.group != "3"]
    if all_parse_warnings:
        lines.append(f"\nXML/스펙 관련 경고 {len(all_parse_warnings)}건:")
        for r in all_parse_warnings[:10]:
            lines.append(f"  {r.recording_id}: {r.parse_warnings}")

    if collection_warnings:
        lines.append(f"\n[파일 수집 단계 경고 {len(collection_warnings)}건]")
        for w in collection_warnings[:20]:
            lines.append(f"  - {w}")

    lines.append("\n" + "=" * 70)
    lines.append("확인 상태 요약 (2026-09-29 keraal_sample_2022.zip 검증 반영, 스크립트 상단 docstring 참고)")
    lines.append("  [A] 파일명 구조: 샘플로 검증 완료. 단, 참가자ID 포맷 다양성은 전체 데이터로 재확인 권장")
    lines.append("  [B] Group3 BodypartIndex(B1/B2/...) -> 실제 신체부위 매핑은 여전히 미확정, 대조 필요")
    lines.append("  [C] 시간 구간: 'Temporal error' 트랙은 없지만 Global error/evaluation <el start end>에 초 단위 구간 있음(확인). 전체 데이터에서 부분 구간 비율은 위 점검 참고")
    lines.append("  [D] bodyPart/Evaluation 결측 처리: 샘플로 확인됨 (태그 자체 부재 = MISSING), 수정 불필요")
    lines.append("=" * 70)

    return "\n".join(lines)


# --------------------------------------------------------------------------
# inspect 서브커맨드: 파싱 전에 파일명이 정규식과 맞는지만 빠르게 확인
# --------------------------------------------------------------------------

def cmd_inspect(root: Path) -> None:
    print(f"루트 디렉터리: {root}\n")
    for group in ["1A", "1B", "2A", "2B"]:
        group_dir = root / f"group{group}"
        if not group_dir.exists():
            print(f"[group{group}] 폴더 없음: {group_dir}")
            continue
        ann_dir = find_annotator_dir(group_dir)
        kinect_dir = group_dir / "kinect"
        xml_files = list_anvil(ann_dir)
        kinect_files = sorted(kinect_dir.glob("*.txt")) if kinect_dir.exists() else []

        print(f"[group{group}] {ann_dir.name}: {len(xml_files)}개, kinect: {len(kinect_files)}개")
        sample_files = xml_files[:3] or kinect_files[:3]
        for f in sample_files:
            meta = parse_filename_group1_2(f)
            status = "OK" if meta else "패턴 불일치!"
            print(f"    예시: {f.name}  ->  {status}  {meta}")
        print()

    group3_dir = root / "group3" / "kinect"
    if group3_dir.exists():
        g3_files = sorted(group3_dir.glob("*.txt"))
        print(f"[group3] kinect: {len(g3_files)}개")
        for f in g3_files[:5]:
            meta = parse_filename_group3(f)
            status = "OK" if meta else "패턴 불일치!"
            decoded = decode_group3_label(meta["raw_label"]) if meta else {}
            print(f"    예시: {f.name}  ->  {status}  {meta}  decoded={decoded}")
    else:
        print(f"[group3] 폴더 없음: {root / 'group3'}")


# --------------------------------------------------------------------------
# parse 서브커맨드: 실제 파싱 실행
# --------------------------------------------------------------------------

def cmd_parse(root: Path, outdir: Path, fps: float = DEFAULT_FPS) -> None:
    global TEMPORAL_SEGMENTS
    TEMPORAL_SEGMENTS = []
    LABEL_SEGMENTS.clear()
    SKEL_TRUNC.clear()

    outdir.mkdir(parents=True, exist_ok=True)
    collection_warnings: list[str] = []

    all_records: list[RecordingRecord] = []
    for group in ["1A", "1B", "2A", "2B"]:
        all_records.extend(collect_group_1_2(root, group, collection_warnings))
    all_records.extend(collect_group_3(root, collection_warnings))

    if not all_records:
        print("경고: 파싱된 녹화가 하나도 없습니다. --root 경로와 폴더 구조를 확인하세요.",
              file=sys.stderr)

    fill_coverage(all_records, fps)

    master_path = outdir / "master_annotations.csv"
    temporal_path = outdir / "temporal_segments_long.csv"
    segments_path = outdir / "segments_long.csv"
    frames_path = outdir / "frame_labels.csv"
    crosstab_path = outdir / "crosstab_error_bodypart.csv"
    qc_path = outdir / "qc_report.txt"

    if all_records:
        write_master_csv(all_records, master_path)
    write_temporal_csv(TEMPORAL_SEGMENTS, temporal_path)
    write_segments_csv(LABEL_SEGMENTS, segments_path)
    n_rows = write_frame_labels_csv(all_records, fps, frames_path)
    write_crosstab(all_records, crosstab_path)

    qc_text = build_qc_report(all_records, TEMPORAL_SEGMENTS, collection_warnings)
    qc_text += f"\n\n프레임 라벨 테이블: {n_rows}행 (fps={fps:g} 가정)"
    qc_path.write_text(qc_text, encoding="utf-8")

    print(qc_text)
    print(f"\n출력 파일:\n  {master_path}\n  {segments_path}\n  {frames_path}\n  "
          f"{temporal_path}\n  {crosstab_path}\n  {qc_path}")



# --------------------------------------------------------------------------
# build 서브커맨드: 모델 입력용 단일 CSV(프레임당 1행) + 단일 QC 리포트
# --------------------------------------------------------------------------

KINECT_JOINTS = [
    "SpineBase", "SpineMid", "Neck", "Head", "ShoulderLeft", "ElbowLeft", "WristLeft", "HandLeft",
    "ShoulderRight", "ElbowRight", "WristRight", "HandRight", "HipLeft", "KneeLeft", "AnkleLeft",
    "FootLeft", "HipRight", "KneeRight", "AnkleRight", "FootRight", "SpineShoulder",
    "HandTipLeft", "ThumbLeft", "HandTipRight", "ThumbRight",
]  # readme_files_format.txt 2.1 순서 (검증됨)
KINECT_FIELDS = ["x", "y", "z", "qx", "qy", "qz", "qw"]  # 관절당 7값 -> 25*7 = 175
KINECT_COLS = [f"{j}_{f}" for j in KINECT_JOINTS for f in KINECT_FIELDS]

LABEL_COLS = ["sample_id", "group", "exercise_code", "participant_key", "trial_id", "frame_idx",
              "time_sec", "evaluation", "error_type", "body_part", "severity",
              "label_source", "label_quality", "in_annotated_span", "skeleton_truncated",
              # 초 단위 라벨 (학습 타깃): 같은 초(second_idx)의 모든 프레임이 같은 값을 갖는다
              "second_idx", "sec_error_type", "sec_body_part", "sec_error_frac",
              "sec_n_frames", "sec_boundary"]


BLAZEPOSE_JOINTS = [
    "Nose", "Left_eye_inner", "Left_eye", "Left_eye_outer", "Right_eye_inner", "Right_eye",
    "Right_eye_outer", "Left_ear", "Right_ear", "Mouth_left", "Mouth_right", "Left_shoulder",
    "Right_shoulder", "Left_elbow", "Right_elbow", "Left_wrist", "Right_wrist", "Left_pinky",
    "Right_pinky", "Left_index", "Right_index", "Left_thumb", "Right_thumb", "Left_hip",
    "Right_hip", "Left_knee", "Right_knee", "Left_ankle", "Right_ankle", "Left_heel",
    "Right_heel", "Left_foot_index", "Right_foot_index",
]  # 샘플 JSON 첫 프레임의 키 순서 (1A, Group3 모두 동일 확인)
BLAZEPOSE_COLS = [f"{j}_{a}" for j in BLAZEPOSE_JOINTS for a in ("x", "y", "z")]  # 33*3 = 99


def blazepose_path_for(r: RecordingRecord, root: Path) -> Path:
    """레코드에 대응하는 BlazePose .json 경로.
    1A/2A: group{g}/blazepose/G{g}-BP-{rest}.json (.anvil 파일명엔 modality 토큰이 없음)
    Group3: kinect 파일명의 'Kinect' -> 'BP', 폴더 kinect -> blazepose, 확장자 .json."""
    if r.label_source == "xml":
        prefix = f"G{r.group}-"
        return root / f"group{r.group}" / "blazepose" / f"{prefix}BP-{r.recording_id[len(prefix):]}.json"
    k = Path(r.source_file)
    return k.parent.parent / "blazepose" / (k.stem.replace("-Kinect-", "-BP-") + ".json")


def load_blazepose_frames(path: Path, n_total: Optional[int] = None):
    """BlazePose JSON -> (frames: 프레임 번호-1 위치에 99값, 빠진 프레임은 None, 경고 문자열).
    프레임 키는 "1.0","2.0",... (영상 프레임 번호). 길이는 max(n_total, 마지막 프레임 번호)."""
    with path.open("r", encoding="utf-8") as f:
        pos = json.load(f)["positions"]
    nums = {int(float(k)): k for k in pos}
    last = max(nums) if nums else 0
    total = max(n_total or 0, last)
    warn = ""
    n_missing = sum(1 for i in range(1, last + 1) if i not in nums)
    if n_missing:
        warn = f"프레임 번호 중간 누락 {n_missing}개 (해당 프레임 행은 생략)"
    frames: list = [None] * total
    for num, k in nums.items():
        if num < 1:
            continue
        fr = pos[k]
        vals: list[str] = []
        for j in BLAZEPOSE_JOINTS:
            xyz = fr.get(j)
            vals.extend([repr(float(v)) for v in xyz[:3]] if xyz and len(xyz) >= 3 else ["nan"] * 3)
        frames[num - 1] = vals
    return frames, warn


def per_second_labels(label_rows: list, fps: float):
    """프레임 라벨 행 -> 프레임별 초 단위 라벨 + 초별 요약.

    규칙: 한 초 안에서 오류 프레임 비율(error_frac)이 0.5 이상이면 그 초를 오류로 하고,
    오류 프레임 중 가장 많은 error_type / body_part를 초 라벨로 한다. 미만이면 none.
    sec_boundary='yes'는 한 초 안에 정상/오류 프레임이 섞인 경우(0<frac<1) = 경계 초.
    sec_n_frames가 fps보다 작은 초는 녹화 끝의 불완전한 초이므로 학습에서 제외 가능.
    lab 열: [rec_id, group, ex, participant, frame_idx, time_sec, eval, et, bp, sev, src]
    """
    import math
    sec_of = [int(math.floor(int(l[4]) / fps + 1e-9)) for l in label_rows]
    by_sec: dict[int, list] = defaultdict(list)
    for l, sidx in zip(label_rows, sec_of):
        by_sec[sidx].append(l)

    info: dict[int, list] = {}
    summary = []
    for sidx, frames in by_sec.items():
        n = len(frames)
        err = [f for f in frames if f[7] not in ("none", MISSING)]
        frac = len(err) / n
        if frac >= 0.5 and err:
            et = Counter(f[7] for f in err).most_common(1)[0][0]
            bps = [f[8] for f in err if f[8] not in ("none", MISSING)]
            bp = Counter(bps).most_common(1)[0][0] if bps else MISSING
        else:
            et, bp = "none", "none"
        boundary = "yes" if 0 < frac < 1 else "no"
        info[sidx] = [sidx, et, bp, f"{frac:.3f}", n, boundary]
        summary.append((sidx, et, frac, n, boundary))
    return [info[sidx] for sidx in sec_of], summary


def kinect_path_for(r: RecordingRecord, root: Path) -> Path:
    """레코드에 대응하는 kinect .txt 경로. .anvil 파일명엔 modality 토큰이 없어 복원한다."""
    if r.label_source == "xml":
        prefix = f"G{r.group}-"
        return root / f"group{r.group}" / "kinect" / f"{prefix}Kinect-{r.recording_id[len(prefix):]}.txt"
    return Path(r.source_file)


def cmd_build(root: Path, outdir: Optional[Path], fps: float = DEFAULT_FPS, with_features: bool = True,
              modality: str = "kinect", out_csv: Optional[Path] = None) -> None:
    """라벨된 녹화(1A/2A/3)를 프레임당 1행의 단일 CSV로 합치고, QC 리포트 1개를 쓴다."""
    global TEMPORAL_SEGMENTS
    TEMPORAL_SEGMENTS = []
    LABEL_SEGMENTS.clear()

    # 출력 위치: --out 으로 CSV 파일 경로를 직접 주면 그 이름으로 저장하고,
    # QC 리포트는 같은 폴더에 "<CSV 이름>_qc_report.txt"로 둔다.
    # --out 이 없으면 --outdir 아래에 model_input_<modality>.csv / qc_report_<modality>.txt
    if out_csv is not None:
        csv_path = out_csv.expanduser()
        qc_path = csv_path.with_name(csv_path.stem + "_qc_report.txt")
    elif outdir is not None:
        outdir = outdir.expanduser()
        csv_path = outdir / f"model_input_{modality}.csv"
        qc_path = outdir / f"qc_report_{modality}.txt"
    else:
        raise SystemExit("오류: --out(CSV 파일 경로) 또는 --outdir(출력 폴더) 중 하나는 지정해야 합니다.")
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    warnings_: list[str] = []
    records: list[RecordingRecord] = []
    for group in ["1A", "1B", "2A", "2B"]:
        records.extend(collect_group_1_2(root, group, warnings_))
    records.extend(collect_group_3(root, warnings_))
    use_bp = modality == "blazepose"
    if use_bp:
        # BlazePose는 영상 프레임과 1:1이므로 프레임 수/라벨 길이를 BlazePose 기준으로 다시 맞춘다.
        for r in records:
            if r.label_source in ("xml", "filename"):
                bpath = blazepose_path_for(r, root)
                if bpath.exists():
                    try:
                        with bpath.open("r", encoding="utf-8") as bf:
                            n_bp = len(json.load(bf)["positions"])
                        n_ref = r.n_frames
                        if n_bp < round(fps):
                            warnings_.append(f"[build] BlazePose 거의 비어있음(프레임 {n_bp}개 < 1초), 제외: {bpath.name}")
                            r.n_frames = 0
                        else:
                            if n_ref and n_bp < 0.98 * n_ref:
                                SKEL_TRUNC[r.recording_id] = (n_bp, n_ref)
                                warnings_.append(f"[build] BlazePose 잘림, 있는 프레임만 사용({n_bp}/{n_ref}): {bpath.name}")
                            r.n_frames = max(n_ref, n_bp)
                    except Exception as exc:  # noqa: BLE001
                        warnings_.append(f"[build] BlazePose JSON 읽기 실패: {bpath.name}: {exc}")
                        r.n_frames = 0
                else:
                    r.n_frames = 0
    fill_coverage(records, fps)

    feat_cols = BLAZEPOSE_COLS if use_bp else KINECT_COLS
    header = LABEL_COLS + (feat_cols if with_features else [])

    n_rows = 0
    bad_width: list[str] = []
    nonfinite: list[str] = []
    frames_by_label: Counter = Counter()           # (group, label_source, error_type)
    frames_by_bp: Counter = Counter()              # (group, body_part) - 오류 프레임만
    frames_by_participant: Counter = Counter()
    secs_by_label: Counter = Counter()             # (group, label_source, sec_error_type) 초 수
    boundary_secs = 0                              # 1A/2A 경계 초 수
    partial_secs = 0                               # 길이가 fps 미만인 불완전한 초 수
    xml_secs = 0
    used = 0

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for r in records:
            if r.label_source not in ("xml", "filename") or r.n_frames == 0:
                continue
            kpath = blazepose_path_for(r, root) if use_bp else kinect_path_for(r, root)
            if not kpath.exists():
                warnings_.append(f"[build] {modality} 파일 없음, 건너뜀: {r.recording_id}")
                continue
            used += 1
            label_rows = list(build_frame_rows([r], fps))
            if use_bp:
                feats, jwarn = load_blazepose_frames(kpath, r.n_frames)
                if jwarn:
                    warnings_.append(f"[build] {r.recording_id}: {jwarn}")
            else:
                with kpath.open("r", encoding="utf-8", errors="ignore") as kf:
                    feats = [ln.split() for ln in kf if ln.strip()]
            if len(feats) != len(label_rows):
                warnings_.append(f"[build] 프레임 수 불일치: {r.recording_id}")
                continue
            pkey = f"{r.group}_{r.participant_id}"
            quality = f"interval_{INTERVAL_TRACK}_{ANNOTATOR}" if r.label_source == "xml" else "whole_recording"
            ann_end = max((s.end_sec for s in LABEL_SEGMENTS
                           if s.recording_id == r.recording_id and s.track == "Global evaluation"), default=None)
            sec_cols, sec_summary = per_second_labels(label_rows, fps)
            for sidx, sec_et, frac, n_in_sec, bnd in sec_summary:
                secs_by_label[(r.group, label_rows[0][10], sec_et)] += 1
                if r.label_source == "xml":
                    xml_secs += 1
                    boundary_secs += bnd == "yes"
                if n_in_sec < round(fps):
                    partial_secs += 1
            trunc = "yes" if r.recording_id in SKEL_TRUNC else "no"
            for lab, sec, vals in zip(label_rows, sec_cols, feats):
                if vals is None:      # BlazePose에 없는 프레임: 행 생략
                    continue
                # lab = [rec_id, group, ex, participant, frame_idx, time_sec, eval, et, bp, sev, src]
                span = "yes" if (r.label_source != "xml" or ann_end is None or float(lab[5]) < ann_end) else "no"
                row = [lab[0], lab[1], lab[2], pkey, r.trial_id, lab[4], lab[5],
                       lab[6], lab[7], lab[8], lab[9], lab[10], quality, span, trunc] + sec
                if with_features:
                    if len(vals) != len(feat_cols):
                        bad_width.append(r.recording_id)
                        break
                    if any(v.lower() in ("nan", "inf", "-inf") for v in vals):
                        nonfinite.append(r.recording_id)
                    row += vals
                writer.writerow(row)
                n_rows += 1
                frames_by_label[(lab[1], lab[10], lab[7])] += 1
                if lab[7] not in ("none", MISSING):
                    frames_by_bp[(lab[1], lab[8])] += 1
                frames_by_participant[pkey] += 1

    # ---- QC 리포트 (파싱 QC + 프레임 단위 요약을 한 파일로) ----
    qc = [build_qc_report(records, TEMPORAL_SEGMENTS, warnings_)]
    qc.append("\n" + "=" * 70)
    qc.append(f"모델 입력 테이블(model_input_{modality}.csv) 요약")
    qc.append("=" * 70)
    qc.append(f"사용한 녹화 수: {used} (1B/2B는 라벨 없어 제외), 총 프레임(행) 수: {n_rows}, fps 가정: {fps:g}")
    if not with_features:
        feat_desc = "없음(--no-features)"
    elif use_bp:
        feat_desc = "BlazePose 99열 (관절 33 x [x,y,z], 정규화 좌표 원본값 미가공, 프레임=영상 프레임)"
    else:
        feat_desc = "Kinect 175열 (관절 25 x [x,y,z,qx,qy,qz,qw], 원본값 미가공)"
    qc.append(f"입력 modality: {modality}, 특징 열: {feat_desc}")
    qc.append("\n[그룹 x 라벨출처 x 오류유형별 프레임 수]  (anvil_time=구간 라벨, filename_whole=녹화 전체 약라벨)")
    for (g, src, et), c in sorted(frames_by_label.items()):
        qc.append(f"  group{g:<3} {src:<15} {et:<8} {c}")
    qc.append("\n[초 단위 라벨 분포 (sec_error_type 기준, 단위=초)]  <- 학습 타깃")
    for (g, src, et), c in sorted(secs_by_label.items()):
        qc.append(f"  group{g:<3} {src:<15} {et:<8} {c}")
    if xml_secs:
        qc.append(f"  1A/2A 경계 초(정상/오류 혼합, sec_boundary=yes): {boundary_secs} / {xml_secs} ({boundary_secs / xml_secs:.1%})")
    qc.append(f"  불완전한 초(프레임 수 < {round(fps)}, 녹화 끝): {partial_secs}  -> sec_n_frames < {round(fps)} 로 걸러 쓸 것")
    qc.append("\n[오류 프레임의 신체부위 분포]")
    for (g, bp), c in sorted(frames_by_bp.items()):
        qc.append(f"  group{g:<3} {bp:<28} {c}")
    xml_frames = sum(c for (g, src, et), c in frames_by_label.items() if src == "anvil_time")
    xml_err = sum(c for (g, src, et), c in frames_by_label.items() if src == "anvil_time" and et != "none")
    if xml_frames:
        qc.append(f"\n1A/2A 프레임 중 오류 프레임 비율: {xml_err / xml_frames:.1%} (다수클래스=정상 비율 {1 - xml_err / xml_frames:.1%} = 단순 베이스라인)")
    qc.append("\n[참가자별 프레임 수] (split 시 participant_key 단위로 나눌 것)")
    for pk, c in sorted(frames_by_participant.items()):
        qc.append(f"  {pk}: {c}")
    if bad_width:
        qc.append(f"\n경고: 특징 열 수가 기대와 다른 녹화 {len(set(bad_width))}건: {sorted(set(bad_width))[:5]}")
    if nonfinite:
        qc.append(f"\n경고: NaN/inf 값이 있는 녹화 {len(set(nonfinite))}건: {sorted(set(nonfinite))[:5]}")
    qc.append("\n주의: (00) skeleton_truncated=yes 는 BlazePose 파일이 잘려 앞부분 프레임만 있는 녹화(뒤 프레임 행은 없음, 초 단위 라벨은 전체 길이로 계산). (0) in_annotated_span=no 는 주석자 A의 마지막 주석 시각 이후 프레임(오류 끝에서 주석이 끝나는 녹화가 많음). 정상으로 라벨됐지만 실제로는 미라벨일 수 있으니 필요하면 제외. (1) label_quality=whole_recording(Group3)은 구간 정보가 없는 약라벨이다. "
              "(2) Kinect 프레임 수는 영상 프레임 수와 1프레임 어긋날 수 있다(샘플 Group3에서 197 vs 196). BlazePose는 영상과 1:1. "
              "(3) 학습 타깃은 second_idx/sec_error_type(초 단위), 입력은 특징 열, 분할 키는 participant_key. "
              "(4) 특징은 원본 그대로이므로 정규화/각도/속도 계산은 모델 코드에서 한다(RQ1 ablation 유지).")
    text = "\n".join(qc)
    qc_path.write_text(text, encoding="utf-8")
    print(text)
    size_mb = csv_path.stat().st_size / 1e6
    print(f"\n출력 파일 (2개):\n  {csv_path}  ({size_mb:.1f} MB)\n  {qc_path}")


# --------------------------------------------------------------------------
# selftest 서브커맨드: 합성 데이터로 스크립트 자체 검증 (실제 데이터 불필요)
# --------------------------------------------------------------------------

_ANVIL_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<annotation>
  <head>
    <specification src="../keraalSpec.xml" />
    <video src="{video}" master="true" />
  </head>
  <body>
    <track name="Global evaluation">
      <el index="0" start="0" end="{dur}">
        <attribute name="evaluation">{evaluation}</attribute>
      </el>
    </track>
    <track name="Global error">
      <el index="0" start="0" end="{dur}">
        <attribute name="type">{error_type}</attribute>
        <attribute name="Evaluation">{severity}</attribute>
        <attribute name="bodyPart">{body_part}</attribute>
      </el>
    </track>
    <track name="Temporal error">
{temporal_els}
    </track>
  </body>
</annotation>
"""

_TEMPORAL_EL_TEMPLATE = """      <el index="{idx}" start="{start}" end="{end}">
        <attribute name="type">{error_type}</attribute>
        <attribute name="Evaluation">{severity}</attribute>
        <attribute name="bodyPart">{body_part}</attribute>
      </el>"""


def _make_synthetic_xml(path: Path, evaluation: str, error_type: str, severity: str,
                         body_part: str, temporal: list[dict], missing_bp: bool = False) -> None:
    temporal_els = "\n".join(
        _TEMPORAL_EL_TEMPLATE.format(
            idx=i, start=seg["start"], end=seg["end"],
            error_type=seg["error_type"], severity=seg["severity"],
            body_part=seg["body_part"],
        )
        for i, seg in enumerate(temporal)
    )
    xml_text = _ANVIL_TEMPLATE.format(
        video=path.stem + ".mp4",
        dur="30.0",
        evaluation=evaluation,
        error_type=error_type,
        severity=severity,
        body_part="" if missing_bp else body_part,
        temporal_els=temporal_els,
    )
    path.write_text(xml_text, encoding="utf-8")


def cmd_selftest(outdir: Path) -> None:
    # 2026-09-29부터 keraal_sample_2022.zip 실제 샘플로 검증된 구조를 그대로 재현한다.
    # (폴더명 annotator/*.anvil, 파일명에 site 토큰 "Brest"/"Unknown", group3 라벨 "C"/"E<n>B<m>")
    root = outdir / "synthetic_dataset"
    for group in ["1A", "2A"]:
        (root / f"group{group}" / "annotator").mkdir(parents=True, exist_ok=True)
        (root / f"group{group}" / "kinect").mkdir(parents=True, exist_ok=True)
    (root / "group1B" / "kinect").mkdir(parents=True, exist_ok=True)
    (root / "group2B" / "kinect").mkdir(parents=True, exist_ok=True)
    (root / "group3" / "kinect").mkdir(parents=True, exist_ok=True)

    # group1A: 환자 2명, 3개 운동, 정상/오류 섞어서 (site="Brest")
    cases = [
        ("G1A-Kinect-RTK-R01-Brest-001", "Correct", "none", MISSING, MISSING, []),
        ("G1A-Kinect-RTK-R01-Brest-002", "Incorrect", "Error1", "SmallError", "BothArms",
         [{"start": "2.0", "end": "5.5", "error_type": "Error1", "severity": "SmallError", "body_part": "BothArms"}]),
        ("G1A-Kinect-ELK-R02-Brest-001", "Incorrect", "Error2", "LargeError", "Spine",
         [{"start": "1.0", "end": "9.0", "error_type": "Error2", "severity": "LargeError", "body_part": "Spine"}]),
        # 결측 bodyPart 케이스 (확인 필요 [D] 재현) — 실제 샘플도 Correct일 땐 bodyPart 속성 자체가 없었음
        ("G1A-Kinect-CTK-R02-Brest-002", "Incorrect", "Error3", "SmallError", MISSING, []),
    ]
    for stem, ev, et, sev, bp, temporal in cases:
        # 실제 샘플 확인: .anvil 파일명에는 modality 토큰("Kinect")이 없다
        anvil_stem = stem.replace("Kinect-", "")
        xml_path = root / "group1A" / "annotator" / f"{anvil_stem}.anvil"
        _make_synthetic_xml(xml_path, ev, et, sev, bp, temporal, missing_bp=(bp == MISSING))
        (root / "group1A" / "kinect" / f"{stem}.txt").write_text("0.0 0.0 0.0\n" * 300, encoding="utf-8")

    # group2A: 건강인 1명 (site="Brest")
    cases2 = [
        ("G2A-Kinect-RTK-S01-Brest-001", "Correct", "none", MISSING, MISSING, []),
        ("G2A-Kinect-ELK-S01-Brest-002", "Incorrect", "Error1", "SmallError", "LeftArm",
         [{"start": "0.5", "end": "3.0", "error_type": "Error1", "severity": "SmallError", "body_part": "LeftArm"},
          {"start": "10.0", "end": "12.0", "error_type": "Error1", "severity": "SmallError", "body_part": "LeftArm"}]),
    ]
    for stem, ev, et, sev, bp, temporal in cases2:
        anvil_stem = stem.replace("Kinect-", "")
        xml_path = root / "group2A" / "annotator" / f"{anvil_stem}.anvil"
        _make_synthetic_xml(xml_path, ev, et, sev, bp, temporal)
        (root / "group2A" / "kinect" / f"{stem}.txt").write_text("0.0 0.0 0.0\n" * 300, encoding="utf-8")

    # group1B / group2B: 라벨 없는 kinect 파일만, 참가자 토큰 자체가 없음 (site="Brest")
    (root / "group1B" / "kinect" / "G1B-Kinect-RTK-Brest-010.txt").write_text("0.0\n", encoding="utf-8")
    (root / "group2B" / "kinect" / "G2B-Kinect-ELK-Brest-010.txt").write_text("0.0\n", encoding="utf-8")

    # group3: 파일명 자체가 라벨. 실제 형식은 'C'(Correct) 또는 'E<n>B<m>', site 토큰은 "Unknown"
    g3_files = [
        "G3-Kinect-RTK-P1T1-Unknown-C-001.txt",
        "G3-Kinect-RTK-P1T2-Unknown-E1B1-002.txt",
        "G3-Kinect-ELK-P2T1-Unknown-E2B3-003.txt",
        "G3-Kinect-CTK-P2T2-Unknown-WeirdLabelXYZ-004.txt",  # 파싱 실패 유도 (경고 확인용)
    ]
    for name in g3_files:
        (root / "group3" / "kinect" / name).write_text("0.0\n" * 200, encoding="utf-8")

    print(">>> 1) inspect 실행 결과\n")
    cmd_inspect(root)

    print("\n>>> 2) parse 실행 결과\n")
    cmd_parse(root, outdir / "parsed_output")

    print("\n합성 데이터셋 위치:", root)
    print("파싱 결과 위치:", outdir / "parsed_output")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_inspect = sub.add_parser("inspect", help="파일명 패턴이 실제 데이터와 맞는지 미리보기")
    p_inspect.add_argument("--root", type=Path, required=True, help="KERAAL 데이터셋 루트 디렉터리")

    p_parse = sub.add_parser("parse", help="실제 파싱 실행")
    p_parse.add_argument("--root", type=Path, required=True, help="KERAAL 데이터셋 루트 디렉터리")
    p_parse.add_argument("--outdir", type=Path, required=True, help="결과 CSV/리포트 출력 폴더")
    p_parse.add_argument("--fps", type=float, default=DEFAULT_FPS,
                         help="스켈레톤/영상 FPS (기본 15: 실제 1A에서 Kinect 프레임수/annotatorB 종료시각=15)")

    p_build = sub.add_parser("build", help="모델 입력용 단일 CSV(프레임당 1행) + QC 리포트 1개 생성")
    p_build.add_argument("--root", type=Path, required=True, help="KERAAL 데이터셋 루트 디렉터리")
    p_build.add_argument("--outdir", type=Path, default=None,
                         help="출력 폴더 (model_input_<modality>.csv, qc_report_<modality>.txt 저장)")
    p_build.add_argument("--out", type=Path, default=None,
                         help="CSV를 저장할 파일 경로를 직접 지정 (예: ~/Desktop/model_input.csv). "
                              "QC 리포트는 같은 폴더에 <이름>_qc_report.txt로 저장")
    p_build.add_argument("--fps", type=float, default=DEFAULT_FPS, help="스켈레톤 FPS (기본 15)")
    p_build.add_argument("--modality", choices=["kinect", "blazepose"], default="kinect",
                         help="입력 스켈레톤 종류 (blazepose = 영상 기반, 기본 kinect)")
    p_build.add_argument("--no-features", action="store_true", help="Kinect 175열 없이 라벨 열만 출력(용량 절약)")

    for _p in (p_inspect, p_parse, p_build):
        _p.add_argument("--annotator", choices=["A", "B"], default="A",
                        help="사용할 주석자 폴더 annotatorA/annotatorB (기본 A)")
        _p.add_argument("--interval-track", choices=["global", "temporal", "auto"], default="global",
                        help="프레임 라벨에 쓸 구간 트랙 (Global error / Temporal error / 있으면 temporal)")

    p_selftest = sub.add_parser("selftest", help="합성 데이터로 스크립트 자체 검증")
    p_selftest.add_argument("--outdir", type=Path, default=Path("./keraal_selftest"))

    args = parser.parse_args()
    global ANNOTATOR, INTERVAL_TRACK
    ANNOTATOR = getattr(args, "annotator", "A")
    INTERVAL_TRACK = getattr(args, "interval_track", "global")

    if args.command == "inspect":
        cmd_inspect(args.root)
    elif args.command == "parse":
        cmd_parse(args.root, args.outdir, args.fps)
    elif args.command == "build":
        cmd_build(args.root, args.outdir, args.fps, with_features=not args.no_features,
                  modality=args.modality, out_csv=args.out)
    elif args.command == "selftest":
        cmd_selftest(args.outdir)


if __name__ == "__main__":
    main()
