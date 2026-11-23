#!/usr/bin/env python3
"""Read-only live Study Hub monitor over an existing SSH alias.

Run: python3 ops/study-hub/fo_monitor.py [--once | --check] [--interval 20] [--host oracle-vps]

No local or VPS service changes. Reads FO API, SQLite (mode=ro) and systemd.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from typing import Any

UNITS = ('transcription', 'catalog', 'materials', 'videos', 'index', 'onedrive', 'ocr')

REMOTE_SCRIPT = f'UNITS = {UNITS!r}\n' + r'''
import json, sqlite3, subprocess, shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

with urlopen("http://127.0.0.1:8780/fo/sync-status", timeout=7) as response:
    status = json.load(response)

root = Path('/home/ubuntu/study-hub-state/federal-online')
db = sqlite3.connect(f'file:{root}/hub.sqlite3?mode=ro', uri=True, timeout=5)
db.row_factory = sqlite3.Row
db.execute('BEGIN')
active = [
    dict(row) for row in db.execute(
        """SELECT j.lesson_id, j.version, j.progress, l.title, l.subject
           FROM transcription_jobs AS j
           LEFT JOIN lessons AS l ON j.lesson_id = l.lesson_id
           WHERE j.state = 'leased' LIMIT 2"""
    )
]
sources = db.execute(
    """SELECT COUNT(*) FROM lesson_video_sources s
       JOIN lessons l ON s.lesson_id = l.lesson_id
       WHERE s.available = 1 AND l.present = 1"""
).fetchone()[0]
canonical_lessons = db.execute('SELECT COUNT(*) FROM lessons WHERE present=1').fetchone()[0]
queue = dict(db.execute('SELECT j.state, COUNT(*) FROM transcription_jobs j JOIN lessons l USING(lesson_id) '
                        'WHERE l.present=1 AND l.version=j.version GROUP BY j.state').fetchall())
reviews = db.execute("SELECT COUNT(*), COUNT(DISTINCT lesson_id) FROM transcription_jobs WHERE state='review'").fetchone()
stale = db.execute("SELECT COUNT(*) FROM transcription_jobs WHERE state='leased' AND "
                   "(lease_until IS NULL OR lease_until <= ?)", (datetime.now(timezone.utc).timestamp(),)).fetchone()[0]
largest = db.execute('SELECT COALESCE(MAX(size),0) FROM lesson_video_sources WHERE available=1').fetchone()[0]
last_done = db.execute("SELECT MAX(CAST(updated_at AS REAL)) FROM transcription_jobs WHERE state='done'").fetchone()[0]
db.close()

units = {}
for name in UNITS:
    unit = "study-hub-fo-" + name + (".service" if name == "transcription" else ".timer")
    result = subprocess.run(
        ["systemctl", "is-active", unit],
        capture_output=True, text=True, timeout=5, check=False,
    )
    units[name] = result.stdout.strip() or "unknown"

def timestamp(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat() if seconds and seconds > 0 else None

def resources(unit):
    result = subprocess.run(['systemctl', 'show', unit, '-p', 'ActiveState', '-p', 'Result', '-p', 'CPUUsageNSec',
                             '-p', 'MemoryCurrent'], capture_output=True, text=True, timeout=5, check=False)
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)

worker_service = resources('study-hub-fo-transcription.service')

usage = shutil.disk_usage(root)
print(json.dumps({
    "time_utc": datetime.now(timezone.utc).isoformat(),
    "status": status,
    "active": active,
    "available_sources": sources,
    "canonical_lessons": canonical_lessons,
    "queue": queue,
    "reviews": {"all_jobs": reviews[0], "all_lessons": reviews[1], "current_jobs": queue.get("review", 0)},
    "stale_leases": stale,
    "last_done": timestamp(last_done),
    "resources": {"whisper": worker_service},
    "decoder_budget_margin": usage.free - largest - 100 * 2**20 - 4 * 2**30,
    "units": units,
    "disk_free": usage.free,
    "disk_total": usage.total,
}, ensure_ascii=False))
'''


def clamp(value: float, bottom: float = 0.0, top: float = 1.0) -> float:
    return max(bottom, min(top, value))


def progress_bar(done: float, total: float, width: int = 32) -> str:
    if total <= 0:
        return "░" * width
    fraction = clamp(done / total)
    exact = fraction * width
    filled = min(width, int(exact))
    fraction_blocks = "▏▎▍▌▋▊▉"
    part = min(7, int((exact - filled) * 8))
    if filled == width:
        return "█" * width
    return "█" * filled + (fraction_blocks[part - 1] if part else "") + "░" * (width - filled - (1 if part else 0))


def fetch(host: str, timeout: float) -> dict[str, Any]:
    command = [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host,
        "python3", "-",
    ]
    result = subprocess.run(
        command, input=REMOTE_SCRIPT, capture_output=True,
        text=True, timeout=timeout, check=False,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip()[-450:])
    return json.loads(result.stdout)


def health_issues(data: dict[str, Any]) -> list[str]:
    units = data['units']
    checks = (
        ('stale_transcription_lease', data.get('stale_leases', 0) > 0),
        ('multiple_transcription_leases', len(data.get('active', [])) > 1),
        ('decoder_storage_reserve', data.get('decoder_budget_margin', 0) < 0),
        ('whisper_service_failed', units.get('transcription') == 'failed'),
    )
    return [issue for issue, failed in checks if failed]


def render(data: dict[str, Any]) -> str:
    status = data["status"]
    jobs = data.get("queue", status.get("transcription_jobs", {}))
    pdf = status.get("pdf_privacy", {})
    units = data["units"]

    done = int(jobs.get("done", 0))
    queued = int(jobs.get("queued", 0))
    processing = int(jobs.get("leased", jobs.get("processing", 0)))
    reviews = int(jobs.get("review", 0))
    superseded = int(status.get("transcription_jobs", {}).get("superseded", 0))
    current = done + queued + processing + reviews

    total_pages = int(status.get("pdf_pages_total", 0))
    released = int(pdf.get("released_pages", 0))
    blocked = int(pdf.get("blocked_pages", 0))
    pending_sources = int(status.get("sources", {}).get("pending", 0))
    eligible = int(status.get("sources", {}).get("eligible", 0))

    def line(label: str, completed: int, total: int) -> str:
        pct = 100 * completed / total if total else 0
        return f"{label:<18} {progress_bar(completed, total)} {pct:5.1f}%  ({completed:,}/{total:,})"

    observed = datetime.fromisoformat(data["time_utc"])
    lines = [
        "STUDY HUB  /  FEDERAL ONLINE — MONITOR AO VIVO (somente leitura)",
        f"VPS: {observed.strftime('%Y-%m-%d %H:%M:%S')} UTC",
        "─" * 84,
        line("Transcrições OK", done, current),
        f"Fila: {queued:,} aguardando  |  {processing} ativa  |  {reviews} em revisão  |  {superseded} substituídas (excluídas da %)",
    ]
    if 'canonical_lessons' in data:
        counts = data['reviews']
        lines.append(f"{data['canonical_lessons']:,} aulas atuais | Revisão: {counts['all_jobs']} jobs / "
                     f"{counts['all_lessons']} aulas; {counts['current_jobs']} revisões atuais")
        lines.append(f"Última validação: {data.get('last_done') or '—'} | Leases vencidos: {data['stale_leases']}")
    if usage := data.get('resources', {}).get('whisper'):
        cpu, ram = usage.get('CPUUsageNSec', ''), usage.get('MemoryCurrent', '')
        cpu_s = f'{int(cpu) / 1e9:.1f} s' if cpu.isdecimal() and int(cpu) < 2**64 - 1 else '—'
        ram_gib = f'{int(ram) / 2**30:.2f} GiB' if ram.isdecimal() and int(ram) < 2**64 - 1 else '—'
        lines.append(f"whisper: CPU acumulada {cpu_s}, RAM atual {ram_gib} | resultado: {usage.get('Result', '—')}")

    for item in data.get("active", []):
        frac = clamp(float(item.get("progress", 0)))
        name = item.get("title") or item["lesson_id"]
        subject = item.get("subject") or "disciplina não informada"
        lines.append(
            f"AGORA: {subject} — {name} (v{item['version']})"
        )
        lines.append(f"       {progress_bar(frac, 1)} {100 * frac:5.1f}% da aula atual")

    lines.extend([
        "─" * 84,
        line("PDFs liberados", released, total_pages),
        f"PDFs: {status.get('materials_total', 0):,} materiais  |  {blocked:,} páginas bloqueadas",
        "─" * 84,
        f"Fontes de vídeo atuais disponíveis: {data['available_sources']:,}  |  pendentes na fila: {pending_sources:,}",
        f"Jobs com fonte elegível: {eligible:,}  |  objetos de vídeo no último índice: "
        f"{status.get('components', {}).get('index', {}).get('summary', {}).get('source_videos', '?')}",
        "Downloads em andamento/bytes: ainda não instrumentados; contagens acima NÃO são % de download.",
        "─" * 84,
        "Serviços: " + "  ".join(f"{key}={value}" for key, value in units.items() if key in UNITS),
        f"Transcrição permitida: {status.get('TRANSCRIPTION_ENABLED', False)}",
        f"Disco livre: {data['disk_free'] / (1024 ** 3):.1f} GiB "
        f"/ {data['disk_total'] / (1024 ** 3):.1f} GiB",
        "Ctrl+C encerra somente o monitor; os processos da VPS continuam.",
    ])
    if 'decoder_budget_margin' in data:
        lines.insert(-1, f"Disco: {data['decoder_budget_margin'] / 2**30:.1f} GiB acima da reserva Whisper")
    if issues := health_issues(data):
        lines.insert(-1, 'ATENÇÃO: ' + ', '.join(issues))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="Show one snapshot and exit.")
    mode.add_argument("--check", action="store_true", help="Emit only health codes: 0 healthy, 1 unavailable, 2 known issues.")
    parser.add_argument("--interval", type=int, default=20, help="Polling interval in seconds.")
    parser.add_argument("--host", default="oracle-vps", help="Existing SSH alias to the VPS.")
    args = parser.parse_args()
    if args.interval < 5:
        parser.error("Use --interval >= 5 to avoid excessive polling.")
    try:
        while True:
            try:
                snapshot = fetch(args.host, timeout=25)
                if args.check:
                    issues = health_issues(snapshot)
                    print('\n'.join(issues) if issues else 'healthy')
                    return 2 if issues else 0
                output = render(snapshot)
                if sys.stdout.isatty() and not args.once:
                    print("\033[2J\033[H", end="")
                print(output, flush=True)
            except (OSError, ValueError, json.JSONDecodeError, RuntimeError, subprocess.TimeoutExpired) as exc:
                if args.check:
                    print('monitor_unavailable', file=sys.stderr)
                    return 1
                print(f"Não foi possível consultar a VPS: {exc}", file=sys.stderr, flush=True)
                if args.once:
                    return 1
            if args.once:
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nMonitor encerrado. Serviços da VPS não foram alterados.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
