# pi-scripts

![Python](https://img.shields.io/badge/python-3.x-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-C51A4A?logo=raspberry-pi&logoColor=white)
![Slack](https://img.shields.io/badge/posts%20to-Slack-4A154B?logo=slack&logoColor=white)
![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
![Private](https://img.shields.io/badge/repo-private-lightgrey)
[![Built with Claude](https://img.shields.io/badge/assisted%20by-Claude-D97757?logo=anthropic&logoColor=white)](https://claude.ai/code)

Automation scripts for the ICEMAN and OXFORD homelabs in Amsterdam, Netherlands, plus backup handoff to WOLFMAN. Scripts post to Slack and run via cron.

## Repository Structure

```
pi-scripts/
├── iceman/                         ← ICEMAN (Pi 3 Model B, armhf)
│   ├── disk_monitor/
│   │   └── disk_monitor.sh         ← disk usage alerts + weekly report
│   ├── docs/
│   │   └── my_crontab_backup.txt
│   ├── lacrosse/
│   │   └── main.py                 ← NCAA D1 + CSU MCLA lacrosse scores
│   ├── logs/                       ← shared logs directory
│   ├── rsync/
│   │   └── rsync_backup.sh         ← weekly backup to OXFORD
│   ├── security_monitor/
│   │   └── security_monitor.sh     ← unexpected listening-port alerts
│   ├── slackbot/
│   │   └── slackbot.py             ← daily morning briefing
│   ├── speedtest/
│   │   └── speedtest_logger.sh     ← network speedtest logger
│   └── temp_monitor/
│       └── temp_monitor.sh         ← Pi temperature monitor
├── oxford/                         ← OXFORD (Pi 4 Model B, 64-bit)
│   ├── backup/
│   │   └── oxford_to_samsung.sh    ← Nextcloud backup to Samsung SSD via WOLFMAN
│   ├── disk_monitor/
│   │   └── disk_monitor.sh         ← disk usage alerts + weekly report
│   ├── health_monitor/
│   │   └── health_monitor.sh       ← load/memory/zombie/Docker/cloudflared checks
│   ├── security_monitor/
│   │   └── security_monitor.sh     ← unexpected listening-port alerts
│   ├── speedtest/
│   │   └── speedtest_logger.sh     ← network speedtest logger
│   └── temp_monitor/
│       └── temp_monitor.sh         ← Pi temperature monitor
└── venv/                           ← shared Python virtual environment (ICEMAN)
```

## Devices

### ICEMAN
| Item | Detail |
|------|--------|
| Model | Raspberry Pi 3 Model B Rev 1.2 |
| OS | Raspbian GNU/Linux 13 (Trixie) — 32-bit armhf |
| RAM | 922MB |
| Storage | 32GB SanDisk High Endurance microSD (18% used) |
| IP | 192.168.178.187 |
| Role | Pi-Hole & Dev playground - Python, bots, experiments, cron jobs |

### OXFORD
| Item | Detail |
|------|--------|
| Model | Raspberry Pi 4 Model B Rev 1.5 |
| OS | Raspbian GNU/Linux 13 (Trixie) — 64-bit |
| RAM | 2GB |
| Storage | 1TB Western Digital SSD (57% used) |
| IP | 192.168.178.201 |
| Role | Infrastructure — Nextcloud, Docker, Cloudflare Tunnel, backups |

### WOLFMAN
| Item | Detail |
|------|--------|
| Model | MacBook Air |
| OS | macOS 12.7.6 (Monterey) — x86_64 |
| RAM | 8GB |
| Storage | 931GB "Nextcloud" volume, mounted for backups (39% used) |
| IP | 192.168.178.141 |
| Role | Off-Pi backup target — OXFORD's Nextcloud data lands here via `oxford_to_samsung.sh`; also runs this repo's Claude Code sessions |

## ICEMAN Scripts

### slackbot
Posts a daily morning briefing to Slack at 9:05am including:
- Amsterdam weather (Open-Meteo — no API key required)
- Moon phase (US Naval Observatory + local fallback calculation)
- Wikipedia "On This Day" historical event
- US and Dutch holiday notifications + personal dates
- Daily Calvin and Hobbes comic link

### lacrosse
Posts two things to Slack:
- NCAA Division I lacrosse scores in a two-column scoreboard format, sourced from the ESPN API
- Colorado State MCLA (club) latest result, scraped from mcla.us

Currently disabled in cron (out of season) — was scheduled daily at 9:30am.

### temp_monitor
Runs every 15 minutes. Checks CPU temperature via `vcgencmd measure_temp`, logs every reading, and posts a Slack alert if it exceeds 65°C.

### disk_monitor
Runs daily at 8am. Alerts to Slack if `/` usage is ≥80%, plus a weekly usage report every Monday regardless of threshold.

### speedtest
Runs daily at 5:30pm. Logs network speedtest results (ping, download, upload, ISP) to CSV using the Ookla speedtest CLI.

### rsync
Runs weekly on Sundays at 2am. Backs up `~/projects/`, home directory, and crontab to OXFORD (`~/Backup/iceman/`). Posts a Slack summary including files and data transferred.

### security_monitor
Runs every 15 minutes. Compares TCP listeners bound to non-loopback addresses against an expected allowlist (SSH + Pi-hole's DNS/admin ports) and posts a Slack alert if anything unexpected shows up. UDP is intentionally excluded — mDNS/avahi and ephemeral client sockets make it too noisy to be a useful signal.

## OXFORD Scripts

### backup (oxford_to_samsung.sh)
Runs Sundays and Thursdays at 11pm. Rsyncs Nextcloud data to a Samsung SSD volume mounted on WOLFMAN, with a lockfile to prevent overlapping runs. Posts a Slack summary including duration, files, and data transferred, and alerts if WOLFMAN is unreachable or the backup fails.

### temp_monitor
Runs every 15 minutes. Checks CPU temperature and posts a Slack alert if it exceeds 65°C.

### disk_monitor
Runs daily at 8am. Alerts to Slack if `/` usage is ≥80%, plus a weekly usage report every Monday regardless of threshold.

### health_monitor
Runs every 15 minutes. Checks load average, memory usage, zombie processes, required Docker containers (Nextcloud app/db/redis), and the cloudflared tunnel — posts a combined Slack alert if anything's off.

### security_monitor
Runs every 15 minutes. Compares TCP listeners bound to non-loopback addresses against an expected allowlist (SSH, Nextcloud on 8080, a separate meal-planner app on 8000 — both LAN-only per ufw) and posts a Slack alert if anything unexpected shows up. VNC (5900) is deliberately *not* on the allowlist since it's meant to stay off except when in active use — see [Security](#security).

### speedtest
Runs daily at 5:15pm. Logs network speedtest results to Slack using the Ookla speedtest CLI.

## ICEMAN Crontab

```
*/15 * * * * /bin/bash /home/pi/projects/iceman/temp_monitor/temp_monitor.sh >> /home/pi/projects/iceman/temp_monitor/logs/temp_monitor.log 2>&1
0 8 * * *    /bin/bash /home/pi/projects/iceman/disk_monitor/disk_monitor.sh >> /home/pi/projects/iceman/disk_monitor/logs/disk_monitor.log 2>&1
0 2 * * 0    /bin/bash /home/pi/projects/iceman/rsync/rsync_backup.sh
05 9 * * *   /home/pi/projects/venv/bin/python3 /home/pi/projects/iceman/slackbot/slackbot.py >/dev/null 2>&1
# 30 9 * * *   /home/pi/projects/venv/bin/python3 /home/pi/projects/iceman/lacrosse/main.py >> /home/pi/projects/iceman/lacrosse/logs/lacrosse.log 2>&1  (disabled — out of season)
30 17 * * *  /bin/bash /home/pi/projects/iceman/speedtest/speedtest_logger.sh >> /home/pi/projects/iceman/speedtest/logs/speedtest.log 2>&1
*/15 * * * * /bin/bash /home/pi/projects/iceman/security_monitor/security_monitor.sh >> /home/pi/projects/iceman/security_monitor/logs/security_monitor.log 2>&1
```

## OXFORD Crontab

```
*/5 * * * *   docker exec -u 33 nextcloud-app php -f /var/www/html/cron.php >> /home/pi/nextcloud/logs/nextcloud-cron.log 2>&1
0 23 * * 0,4  /home/pi/Projects/pi-scripts/oxford/backup/oxford_to_samsung.sh
*/15 * * * *  /bin/bash /home/pi/Projects/pi-scripts/oxford/temp_monitor/temp_monitor.sh >> /home/pi/Projects/pi-scripts/oxford/temp_monitor/logs/temp_monitor.log 2>&1
*/15 * * * *  /bin/bash /home/pi/Projects/pi-scripts/oxford/health_monitor/health_monitor.sh >> /home/pi/Projects/pi-scripts/oxford/health_monitor/logs/health_monitor.log 2>&1
0 8 * * *     /bin/bash /home/pi/Projects/pi-scripts/oxford/disk_monitor/disk_monitor.sh >> /home/pi/Projects/pi-scripts/oxford/disk_monitor/logs/disk_monitor.log 2>&1
15 17 * * *   /bin/bash /home/pi/Projects/pi-scripts/oxford/speedtest/speedtest_logger.sh >> /home/pi/Projects/pi-scripts/oxford/speedtest/logs/speedtest.log 2>&1
*/15 * * * *  /bin/bash /home/pi/Projects/pi-scripts/oxford/security_monitor/security_monitor.sh >> /home/pi/Projects/pi-scripts/oxford/security_monitor/logs/security_monitor.log 2>&1
```

## Setup

### ICEMAN Prerequisites
```bash
sudo apt install python3 python3-venv libopenblas0
```

### ICEMAN Install
```bash
git clone git@github.com:mbulkeley/pi-scripts.git ~/projects
cd ~/projects
python3 -m venv venv
source venv/bin/activate
pip install requests pandas python-dateutil holidays beautifulsoup4 lxml
```

### OXFORD Prerequisites
```bash
sudo apt install bc rsync docker.io
```
Also needs an `id_ed25519_wolfman` SSH key pair (for `oxford_to_samsung.sh`) and Docker containers named `nextcloud-app`, `nextcloud-db`, `nextcloud-redis` running (checked by `health_monitor.sh`).

### OXFORD Install
```bash
git clone git@github.com:mbulkeley/pi-scripts.git /home/pi/Projects/pi-scripts
```
No venv/pip install needed — OXFORD's scripts are all bash.

### Environment Variables
Stored in `/etc/environment` (no quotes around values):
```
SLACK_WEBHOOK_ICEMAN=https://hooks.slack.com/services/...
SLACK_WEBHOOK_OXFORD=https://hooks.slack.com/services/...
SLACK_WEBHOOK_WORK=https://hooks.slack.com/services/...
```
`SLACK_WEBHOOK_WORK` is used by `slackbot.py` to mirror the daily briefing to a separate work Slack workspace.

## Security
- SSH key auth only — no passwords (ICEMAN enforces this; OXFORD's `sshd_config` needs `PasswordAuthentication no` set manually, see Notes)
- Secrets in `/etc/environment`, never in scripts
- Gitleaks pre-commit hook, plus a gitleaks GitHub Action on push/PR as a backstop for clones without the hook installed
- Ruff for linting and formatting
- ufw active on both hosts, default-deny incoming. OXFORD only opens 22 to the internet; 8000 (meal-planner) and 8080 (Nextcloud, bypassing the Cloudflare Tunnel) are LAN-only (`192.168.178.0/24`) — no router port-forwarding exists, so nothing here is reachable from the internet beyond the Cloudflare Tunnel's `nextcloud.mauriecloud.com` route
- Cloudflare Tunnel (`cloudflared`) on OXFORD only routes `nextcloud.mauriecloud.com` → `localhost:8080`; everything else 404s
- VNC on OXFORD (`vncserver-x11-serviced`, used periodically for Garmin watch fixes) is start-on-demand, not always-on: `sudo systemctl start vncserver-x11-serviced` before use, `stop` after. `security_monitor.sh` will alert if it's ever left running
- `security_monitor.sh` on both hosts flags any TCP listener that isn't on the expected allowlist — see the ICEMAN/OXFORD Scripts sections above

## VNC Access (OXFORD)
Used periodically for Garmin watch fixes. Off by default — start it before use, stop it when done:
```bash
ssh oxford
sudo systemctl start vncserver-x11-serviced
sudo ufw allow from 192.168.178.0/24 to any port 5900 proto tcp comment 'VNC LAN access - Garmin fixes'  # first time only, rule persists after
# ... do the Garmin fix ...
sudo systemctl stop vncserver-x11-serviced
```
Connect to `192.168.178.201:5900` (LAN only — not exposed externally, ufw blocks it otherwise).

**Known issue:** last tested 2026-08-16, the client connected but couldn't display the desktop. OXFORD boots to `graphical.target` with an active (idle) session on `seat0`, so a desktop session does exist — likely cause is RealVNC's Service Mode struggling to capture Raspberry Pi OS Trixie's default Wayland compositor. Not yet resolved; worth trying Virtual Mode (`vncserver-virtuald`) or forcing an X11 session if it recurs.

## License
Private repository, all rights reserved. Not currently licensed for reuse.

## Notes
- ICEMAN is 32-bit armhf — check compatibility before installing packages (NodeSource and official Docker repos do not support armhf)
- `/etc/environment` values must have no quotes
- Cron loads `/etc/environment` automatically; manual runs need `export VAR=$(grep VAR /etc/environment | cut -d= -f2)`
- Trixie uses journald: `sudo journalctl` not `/var/log/syslog`
- To lock down OXFORD's SSH to key-only (matching ICEMAN): `sudo sed -i 's/^#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config && sudo sshd -t && sudo systemctl restart sshd`. Verify a *new* SSH connection still works before closing your existing session.
