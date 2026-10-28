"""Private real-audio ASR configuration comparison (VPS only, resource-capped unit).

Downloads one verified source once, extracts exact WAV spans (same ffmpeg
arguments as the worker), deletes the video, then decodes each span under each
requested configuration sequentially. Raw decoder JSON, stderr and /usr/bin/time
logs are preserved; a QA summary (repetition, duplicates, timestamps, measured
silence) is written per run. No queue lease, no publication.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from .worker import Config, file_sha256, parse_whisper, silence_intervals
from .transcription import qa_segments

CONFIGS = {
    # baseline = pilot configuration (fallback disabled)
    'baseline': {'bs': 5, 'fallback': False, 'mc': -1, 'extra': []},
    'fallback': {'bs': 5, 'fallback': True, 'mc': -1, 'extra': []},
    'no-context': {'bs': 5, 'fallback': False, 'mc': 0, 'extra': []},
    'fallback-no-context': {'bs': 5, 'fallback': True, 'mc': 0, 'extra': []},
    'fallback-no-context-sns': {'bs': 5, 'fallback': True, 'mc': 0, 'extra': ['-sns']},
    'beam8-fallback-no-context': {'bs': 8, 'fallback': True, 'mc': 0, 'extra': []},
}


def decoder_args(cfg: Config, name: str, audio: Path, prefix: Path, threads: int = 3) -> list[str]:
    c = CONFIGS[name]
    args = [str(cfg.binary), '-m', str(cfg.model), '-f', str(audio), '-l', 'pt', '-t', str(threads),
            '-bs', str(c['bs']), '-bo', '5', '-mc', str(c['mc']), '-tp', '0',
            '-tpi', '0.2' if c['fallback'] else '0', '-nth', '0.6', '-et', '2.4', '-lpt', '-1',
            '-ng', '-ojf', '-of', str(prefix), *c['extra']]
    if not c['fallback']:
        args.append('-nf')
    return args


def summarize(raw: dict, offset: float, length: float, silence: list) -> dict:
    segs = parse_whisper(raw, offset)
    rel = [{**s, 'start': s['start'] - offset, 'end': s['end'] - offset} for s in segs]
    qa = qa_segments(rel, length)
    kinds: dict[str, int] = {}
    for f in qa['flags']:
        kinds[f['kind']] = kinds.get(f['kind'], 0) + 1
    in_silence = sum(1 for s in rel if s['text'] and any(s['start'] >= a and s['end'] <= b for a, b in silence))
    texts = [s['text'] for s in rel if s['text']]
    from collections import Counter
    top = Counter(texts).most_common(1)
    covered = 0.0
    last = 0.0
    for s in sorted(rel, key=lambda x: x['start']):
        st, en = max(s['start'], last), s['end']
        if en > st:
            covered += en - st
            last = en
    return {'segments': len(rel), 'words': qa['metrics']['words'], 'flag_kinds': kinds,
            'repetition_ratio': qa['metrics']['repetition_ratio'],
            'max_identical_segment_count': top[0][1] if top else 0,
            'text_in_measured_silence': in_silence, 'timestamp_union_s': round(covered, 3),
            'coverage_pct': round(100 * covered / length, 2) if length else None,
            'qa_passed': qa['passed']}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--lesson-id', required=True)
    p.add_argument('--expected-sha256')
    p.add_argument('--span', action='append', default=[], help='offset:length seconds')
    p.add_argument('--wav', action='append', default=[],
                   help='offset:length:path:sha256 of an already verified window WAV (no video download)')
    p.add_argument('--config', action='append', required=True, choices=tuple(CONFIGS))
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args(argv)
    cfg = Config.from_env()
    out = a.out
    out.mkdir(mode=0o700, parents=True, exist_ok=True)
    locks = cfg.state / 'locks'
    with (locks / 'transcription.lock').open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('transcription lock busy', file=sys.stderr)
            return 4
        import sqlite3
        conn = sqlite3.connect(f'file:{cfg.db}?mode=ro', uri=True)
        row = conn.execute('SELECT remote_path,size FROM lesson_video_sources WHERE lesson_id=? AND available=1',
                           (a.lesson_id,)).fetchone()
        conn.close()
        if not row or not str(row[0]).startswith('onedrive:Federal Online/'):
            raise SystemExit('source unavailable')
        spans = [tuple(float(x) for x in s.split(':')) for s in a.span]
        wavs = {}
        for spec in a.wav:
            off, length, path, expected = spec.split(':')
            path = Path(path)
            if file_sha256(path) != expected:
                raise SystemExit('window WAV identity mismatch')
            sil = subprocess.run(['ffmpeg', '-nostdin', '-threads', '1', '-i', str(path), '-af',
                                  'silencedetect=noise=-40dB:d=1', '-f', 'null', '-'],
                                 check=True, capture_output=True, text=True)
            wavs[(float(off), float(length))] = (path, expected, silence_intervals(sil.stderr, float(length)))
        if spans and not a.expected_sha256:
            p.error('--span requires --expected-sha256')
        missing = [s for s in spans if not (out / f'span-{s[0]:.0f}-{s[1]:.0f}.wav').is_file()]
        if missing:
            work = out / 'source-tmp'
            work.mkdir(mode=0o700, exist_ok=True)
            video = work / 'source.mp4'
            subprocess.run(['rclone', 'copyto', row[0], str(video), '--retries', '3', '--transfers', '1',
                            '--max-transfer', f'{row[1] + 1024**2}B', '--cutoff-mode', 'HARD'], check=True)
            if video.stat().st_size != row[1] or file_sha256(video) != a.expected_sha256:
                raise SystemExit('source identity mismatch')
            for off, length in missing:
                wav = out / f'span-{off:.0f}-{length:.0f}.wav'
                subprocess.run(['ffmpeg', '-nostdin', '-y', '-threads', '1', '-ss', str(off), '-i', str(video),
                                '-t', str(length), '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le',
                                '-threads', '1', str(wav)], check=True, capture_output=True)
            shutil.rmtree(work)
        for off, length in spans:
            wav = out / f'span-{off:.0f}-{length:.0f}.wav'
            sil = subprocess.run(['ffmpeg', '-nostdin', '-threads', '1', '-i', str(wav), '-af',
                                  'silencedetect=noise=-40dB:d=1', '-f', 'null', '-'],
                                 check=True, capture_output=True, text=True)
            wavs[(off, length)] = (wav, file_sha256(wav), silence_intervals(sil.stderr, length))
        results_path = out / 'results.jsonl'
        done = set()
        if results_path.exists():
            for line in results_path.read_text().splitlines():
                r = json.loads(line)
                done.add((r['offset_s'], r['length_s'], r['config']))
        for name in a.config:
            for (off, length), (wav, wav_sha, silence) in wavs.items():
                if (off, length, name) in done:
                    continue
                prefix = out / f'{name}-{off:.0f}-{length:.0f}'
                timing = Path(str(prefix) + '.time.txt')
                args = ['/usr/bin/time', '-v', '-o', str(timing), *decoder_args(cfg, name, wav, prefix)]
                t0 = time.monotonic()
                proc = subprocess.run(args, capture_output=True, text=True)
                wall = time.monotonic() - t0
                Path(str(prefix) + '.stderr.txt').write_text(proc.stderr)
                rec = {'config': name, 'offset_s': off, 'length_s': length, 'wav_sha256': wav_sha,
                       'returncode': proc.returncode, 'wall_s': round(wall, 3), 'rtf': round(wall / length, 4),
                       'command': args[4:], 'silence_intervals': silence}
                try:
                    maxrss = [l for l in timing.read_text().splitlines() if 'Maximum resident' in l]
                    rec['max_rss_kib'] = int(maxrss[0].split(':')[1]) if maxrss else None
                except OSError:
                    rec['max_rss_kib'] = None
                raw_path = Path(str(prefix) + '.json')
                if proc.returncode == 0 and raw_path.is_file():
                    rec['raw_sha256'] = file_sha256(raw_path)
                    rec['summary'] = summarize(json.loads(raw_path.read_text()), off, length, silence)
                with results_path.open('a') as h:
                    h.write(json.dumps(rec) + '\n')
                    h.flush()
                    os.fsync(h.fileno())
                print(json.dumps({k: rec.get(k) for k in ('config', 'offset_s', 'returncode', 'wall_s', 'summary')}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
