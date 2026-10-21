#!/usr/bin/env python3
"""Install independently managed FO units. Never enables/starts transcription."""
from pathlib import Path
import argparse

ROOT='/home/ubuntu/study-hub/federal-online'
STATE='/home/ubuntu/study-hub-state/federal-online'
PY='/home/ubuntu/study-hub-venv/bin/python'
COMMON=f'''[Unit]
After=network-online.target
Wants=network-online.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory={ROOT}
EnvironmentFile=/home/ubuntu/.config/study-hub/runtime.env
Environment=TRANSCRIPTION_ENABLED=false
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=PYTHONUNBUFFERED=1
Environment=TMPDIR={STATE}/tmp
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths={STATE} /home/ubuntu/.config/study-hub /home/ubuntu/.config/rclone
CPUQuota=100%
MemoryMax=2G
TasksMax=512
'''


def render(directory):
    directory.mkdir(parents=True,exist_ok=True)
    jobs={
        'catalog':('portal/runtime.py catalog','*-*-* 03,09,15,21:00:00'),
        'materials':('portal/runtime.py materials','*-*-* 04:45:00'),
        'videos':('portal/video_runtime.py','hourly'),
        'index':('-m fo_hub.ingest','*:0/10'),
        'onedrive':('-m fo_hub.onedrive','*-*-* *:25:00'),
        'ocr':('-m fo_hub.ocr','*:05/10'),
    }
    for name,(command,calendar) in jobs.items():
        unit=f'study-hub-fo-{name}'
        text=COMMON+f'Type=oneshot\nExecStart=/usr/bin/flock -n {STATE}/locks/{name}.lock {PY} {command}\nTimeoutStartSec=12h\n'
        if name == 'ocr':
            text=(COMMON.replace('CPUQuota=100%', 'CPUQuota=25%')
                  .replace('MemoryMax=2G', 'MemoryMax=512M').replace('TasksMax=512', 'TasksMax=32')
                  +f'Type=oneshot\nExecStart=/usr/bin/flock -n -E 75 {STATE}/locks/index.lock {PY} {command}\n'
                  +'SuccessExitStatus=75\nTimeoutStartSec=5min\nNice=15\nIOSchedulingClass=idle\n')
        if name in ('catalog','materials'):
            text+='Restart=on-failure\nRestartSec=900\nRestartPreventExitStatus=2\n'
        (directory/(unit+'.service')).write_text(text)
        (directory/(unit+'.timer')).write_text(f'''[Unit]
Description=Study Hub FO {name} periodic check
[Timer]
OnCalendar={calendar}
RandomizedDelaySec=120
Persistent=true
Unit={unit}.service
[Install]
WantedBy=timers.target
''')
    (directory/'study-hub-fo-api.service').write_text(COMMON+f'''Type=simple
ExecStart={PY} -m uvicorn fo_hub.api:app_from_env --factory --host 127.0.0.1 --port 8780
Restart=on-failure
RestartSec=10
[Install]
WantedBy=multi-user.target
''')
    (directory/'study-hub-fo-transcription.service').write_text(f'''[Unit]
Description=Study Hub transcription - explicit manual authorization required
After=network-online.target
ConditionPathExists=/etc/study-hub/fo-transcription.authorized
ConditionPathExists=/etc/study-hub/fo-vps.marker
[Service]
Type=simple
User=ubuntu
WorkingDirectory={ROOT}
EnvironmentFile=/home/ubuntu/.config/study-hub/transcription.env
Environment=PYTHONUNBUFFERED=1
ExecStart={PY} -m fo_hub.worker --run --loop
Restart=on-failure
RestartPreventExitStatus=3
RestartSec=60
CPUQuota=300%
MemoryMax=12G
TasksMax=128
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths={STATE} /home/ubuntu/.config/rclone
UMask=0077
# No timer. Install target is optional, NEVER enable without new approval.
[Install]
WantedBy=multi-user.target
''')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path)
    render(parser.parse_args().directory)
