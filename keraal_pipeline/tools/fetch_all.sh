#!/usr/bin/env bash
# Download every file on https://keraal.enstb.org/KeraalDataset.html to $ROOT/archives (resumable),
# verify each size against the server, then extract everything (videos included) to $ROOT/extracted/<group>/.
# Run detached; progress goes to $ROOT/fetch.log. Re-running is safe: finished files are skipped.
#   bash tools/fetch_all.sh /e/KERAAL_data
set -u
ROOT="${1:-/e/KERAAL_data}"
BASE="https://keraal.enstb.org/data"
LOG="$ROOT/fetch.log"
mkdir -p "$ROOT/archives" "$ROOT/extracted"
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }

# name expected_bytes (server Content-Length on 2026-10-06)
FILES="readme_files_format.txt 5437
poppyMovements.tar.xz 11048
keraal_sample_2022.zip 118502233
pose_model.pth 209266467
group2A.tar.xz 354174988
group1A.tar.xz 1470137152
group2B.tar.xz 1379017648
group1B.tar.xz 13236477836
group3.tar.xz 8714472496"

# 1) Group 3 was already downloaded to the C: pipeline folder: move it instead of downloading again.
SRC="/c/Users/user/Desktop/SOn H.g/class materials/AI application/keraal_pipeline/raw/group3.tar.xz.part"
DST="$ROOT/archives/group3.tar.xz"
if [ -f "$SRC" ] && [ ! -f "$DST" ]; then
  log "moving local group3 archive to $DST"
  cp "$SRC" "$DST.copying" && [ "$(stat -c %s "$DST.copying")" = "8714472496" ] \
    && mv "$DST.copying" "$DST" && rm "$SRC" && log "group3 archive moved (C: copy removed)" \
    || log "ERROR moving group3 archive; C: copy left in place"
fi

# 2) Download the rest (resumable), verify size.
echo "$FILES" | while read -r name size; do
  out="$ROOT/archives/$name"
  if [ -f "$out" ] && [ "$(stat -c %s "$out")" = "$size" ]; then log "ok (present) $name"; continue; fi
  log "downloading $name ($size bytes)"
  for attempt in 1 2 3 4 5; do
    curl -sL -C - -o "$out" "$BASE/$name"
    [ "$(stat -c %s "$out" 2>/dev/null || echo 0)" = "$size" ] && break
    log "  retry $attempt for $name (have $(stat -c %s "$out" 2>/dev/null || echo 0))"; sleep 10
  done
  if [ "$(stat -c %s "$out" 2>/dev/null || echo 0)" = "$size" ]; then log "ok (downloaded) $name"; else log "ERROR size mismatch $name"; fi
done

# 3) Extract everything (videos included). Archive members have no group prefix, so extract per group folder.
for g in group1A group1B group2A group2B group3; do
  a="$ROOT/archives/$g.tar.xz"; d="$ROOT/extracted/$g"
  if [ -f "$d/.extracted" ]; then log "ok (extracted) $g"; continue; fi
  mkdir -p "$d"; log "extracting $g"
  if tar -xJf "$a" -C "$d" --exclude='._*'; then touch "$d/.extracted"; log "ok (extracted) $g"; else log "ERROR extracting $g"; fi
done
if [ ! -f "$ROOT/extracted/sample/.extracted" ]; then
  mkdir -p "$ROOT/extracted/sample"
  unzip -oq "$ROOT/archives/keraal_sample_2022.zip" -d "$ROOT/extracted/sample" -x "__MACOSX/*" && touch "$ROOT/extracted/sample/.extracted" && log "ok (extracted) sample"
fi
if [ ! -f "$ROOT/extracted/poppyMovements/.extracted" ]; then
  mkdir -p "$ROOT/extracted/poppyMovements"
  tar -xJf "$ROOT/archives/poppyMovements.tar.xz" -C "$ROOT/extracted/poppyMovements" && touch "$ROOT/extracted/poppyMovements/.extracted" && log "ok (extracted) poppyMovements"
fi
log "ALL DONE"
