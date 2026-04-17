# pi-scripts

Raspberry Pi automation scripts running on ICEMAN — a Raspberry Pi 3 Model B in Amsterdam, Netherlands. All scripts post to Slack and run via cron.

## Hardware

| Item | Detail |
|------|--------|
| Model | Raspberry Pi 3 Model B Rev 1.2 |
| OS | Raspbian GNU/Linux 13 (Trixie) |
| RAM | 922MB |
| Storage | 32GB SanDisk High Endurance microSD |

## Project Structure

```
pi-scripts/
├── venv/                    ← shared Python virtual environment
├── logs/                    ← shared logs directory
├── docs/
│   └── my_crontab_backup.txt
├── slackbot/
│   └── slackbot.py          ← daily morning briefing
├── temp_monitor/
│   └── temp_monitor.sh      ← Pi temperature monitor
├── speedtest/
│   └── speedtest_logger.sh  ← network speedtest logger
└── lacrosse/
    └── main.py              ← NCAA D1 + CSU MCLA lacrosse scores
```

## Scripts

### slackbot
Posts a daily morning briefing to Slack at 9:05am including:
- Amsterdam weather (Open-Meteo — no API key required)
- Moon phase (US Naval Observatory + local fallback calculation)
- Wikipedia "On This Day" historical event
- US and Dutch holiday notifications + personal dates
- Daily Calvin and Hobbes comic link

### temp_monitor
Runs every 15 minutes. Checks ICEMAN's CPU temperature via `vcgencmd measure_temp` and posts a Slack alert if it exceeds the threshold.

### speedtest
Runs daily at 5:30pm. Logs network speedtest results (ping, download, upload, ISP) to Slack using the Ookla speedtest CLI.

### lacrosse
Runs daily at 9:10am. Posts two things to Slack:
- NCAA Division I lacrosse scores in a clean two-column scoreboard format, sourced from the ESPN hidden API
- Colorado State MCLA (club) latest result, scraped from mcla.us

## Setup

### Prerequisites
```bash
sudo apt install python3 python3-venv libopenblas0
```

### Install
```bash
git clone git@github.com:mbulkeley/pi-scripts.git ~/projects
cd ~/projects
python3 -m venv venv
source venv/bin/activate
pip install requests pandas python-dateutil holidays beautifulsoup4 lxml
```

### Environment Variables
Secrets are stored in `/etc/environment` (no quotes around values):
```
SLACK_TOKEN=xoxb-...
SLACK_WEBHOOK_ICEMAN=https://hooks.slack.com/services/...
```

### Crontab
```
05 9 * * *    /home/pi/projects/venv/bin/python3 /home/pi/projects/slackbot/slackbot.py >/dev/null 2>&1
10 9 * * *    /home/pi/projects/venv/bin/python3 /home/pi/projects/lacrosse/main.py >/dev/null 2>&1
*/15 * * * *  /bin/bash /home/pi/projects/temp_monitor/temp_monitor.sh >/dev/null 2>&1
30 17 * * *   /bin/bash /home/pi/projects/speedtest/speedtest_logger.sh >/dev/null 2>&1
```

## Security
- SSH key auth only — no passwords
- Secrets stored in `/etc/environment`, never in scripts
- Gitleaks pre-commit hook to prevent accidental secret commits
- Ruff for linting and formatting

## Notes
- ICEMAN is a 32-bit armhf Pi 3 — check compatibility before installing new packages (NodeSource and official Docker repos do not support armhf)
- `/etc/environment` values must have no quotes — works correctly for Python, shell, and all other runtimes
- Cron loads `/etc/environment` automatically; manual runs need `export VAR=$(grep VAR /etc/environment | cut -d= -f2)`
