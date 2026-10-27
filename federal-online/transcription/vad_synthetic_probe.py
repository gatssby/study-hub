"""Probe installed VAD on zeros only; never opens audio or loads Whisper ASR."""
import ctypes as C
import hashlib,json,math
from pathlib import Path
root=Path('/home/ubuntu/study-hub-models/whisper.cpp')
weights=root/'models/for-tests-silero-v6.2.0-ggml.bin'
expected='2aa269b785eeb53a82983a20501ddf7c1d9c48e33ab63a41391ac6c9f7fb6987'
assert hashlib.sha256(weights.read_bytes()).hexdigest()==expected
class Params(C.Structure):
 _fields_=[('n_threads',C.c_int),('use_gpu',C.c_bool),('gpu_device',C.c_int)]
lib=C.CDLL(str(root/'build/bin/libwhisper.so'))
lib.whisper_vad_default_context_params.argtypes=[]
lib.whisper_vad_default_context_params.restype=Params
lib.whisper_vad_init_from_file_with_params.argtypes=[C.c_char_p,Params]
lib.whisper_vad_init_from_file_with_params.restype=C.c_void_p
lib.whisper_vad_detect_speech.argtypes=[C.c_void_p,C.POINTER(C.c_float),C.c_int]
lib.whisper_vad_detect_speech.restype=C.c_bool
lib.whisper_vad_n_probs.argtypes=[C.c_void_p]
lib.whisper_vad_n_probs.restype=C.c_int
lib.whisper_vad_probs.argtypes=[C.c_void_p]
lib.whisper_vad_probs.restype=C.POINTER(C.c_float)
lib.whisper_vad_free.argtypes=[C.c_void_p]
lib.whisper_vad_free.restype=None
params=lib.whisper_vad_default_context_params();params.n_threads=1;params.use_gpu=False
ctx=lib.whisper_vad_init_from_file_with_params(str(weights).encode(),params)
assert ctx,'VAD weights could not be loaded'
try:
 samples=(C.c_float*(2*16000))()
 assert lib.whisper_vad_detect_speech(ctx,samples,len(samples)),'VAD operation failed'
 n=lib.whisper_vad_n_probs(ctx)
 assert n>0
 probs=[lib.whisper_vad_probs(ctx)[i] for i in range(n)]
 assert all(math.isfinite(x) and 0<=x<=1 for x in probs)
 assert max(probs)<0.5,'Zeros unexpectedly marked as speech'
 print(json.dumps({'vad_weights_sha256':expected,'official_lfs_match':True,'runtime_load':'passed','synthetic_input':'2 seconds of in-memory zero PCM at 16 kHz','frames':n,'maximum_speech_probability':max(probs),'real_audio_opened':False,'asr_model_loaded':False,'asr_inference_executed':False,'vad_synthetic_inference_executed':True,'production_vad_enabled':False},indent=2))
finally:lib.whisper_vad_free(ctx)
