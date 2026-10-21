#!/usr/bin/env bash
# Preparação somente: NÃO chama whisper-cli nem processa áudio.
set -euo pipefail
ROOT=/home/ubuntu/study-hub-models
mkdir -p "$ROOT"
exec 9>"$ROOT/prepare.lock"
flock -n 9
python3 - "$ROOT" <<'PY'
import shutil,sys
# Reserve 4 GiB + full-precision large-v3 + compilation headroom.
if shutil.disk_usage(sys.argv[1]).free < 8*1024**3:
    raise SystemExit('Insufficient safe free space; preparation blocked')
PY
if [ ! -d "$ROOT/whisper.cpp/.git" ]; then
  git clone --depth 1 https://github.com/ggml-org/whisper.cpp.git "$ROOT/whisper.cpp"
fi
cmake -S "$ROOT/whisper.cpp" -B "$ROOT/whisper.cpp/build" -DGGML_CUDA=OFF -DWHISPER_BUILD_TESTS=OFF
cmake --build "$ROOT/whisper.cpp/build" --target whisper-cli -j 1
MODEL="$ROOT/ggml-large-v3.bin"
EXPECTED=64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2
if [ ! -f "$MODEL" ]; then
  curl --fail --location --retry 5 --connect-timeout 30 --output "$MODEL.partial" https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin
  python3 - "$MODEL.partial" "$EXPECTED" <<'PY'
import hashlib,sys
h=hashlib.sha256()
with open(sys.argv[1],'rb') as f:
    for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
if h.hexdigest()!=sys.argv[2]:raise SystemExit('Model hash mismatch; NOT promoted')
PY
  mv "$MODEL.partial" "$MODEL"
fi
python3 - "$ROOT" "$EXPECTED" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(sys.argv[1]);h=hashlib.sha256()
with (root/'ggml-large-v3.bin').open('rb') as f:
    for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
assert h.hexdigest()==sys.argv[2]
result={'model':'whisper-large-v3-f16','sha256':h.hexdigest(),'bytes':(root/'ggml-large-v3.bin').stat().st_size,'runtime_commit':subprocess.check_output(['git','-C',str(root/'whisper.cpp'),'rev-parse','HEAD'],text=True).strip(),'inference_executed':False,'TRANSCRIPTION_ENABLED':False,'selection':'baseline_for_benchmark_not_final_quality_winner'}
(root/'preparation.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
PY
