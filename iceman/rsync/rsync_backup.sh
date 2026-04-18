#!/bin/bash

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

OXFORD="pi@192.168.178.201"
DEST="$OXFORD:/home/pi/Backup/iceman"
SSH_OPT="-e \"ssh -i ~/.ssh/id_ed25519_oxford\""
LOG="/home/pi/projects/rsync/logs/rsync.log"
MAX_LOG_KB=500
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Cap log size
if [ -f "$LOG" ] && [ $(du -k "$LOG" | cut -f1) -ge $MAX_LOG_KB ]; then
    mv "$LOG" "${LOG}.1"
    gzip "${LOG}.1"
fi

echo "[$TIMESTAMP] Starting rsync backup to OXFORD" >> "$LOG"

# Dump crontab
crontab -l > /home/pi/projects/rsync/crontab.bak 2>/dev/null

# Sync projects/ (excluding venv, caches)
rsync -avz -e "ssh -i ~/.ssh/id_ed25519_oxford" \
  --exclude='venv/' \
  --exclude='.ruff_cache/' \
  --exclude='__pycache__/' \
  ~/projects/ "$DEST/projects/" >> "$LOG" 2>&1

# Sync home dir (dotfiles/configs, excluding projects/)
rsync -avz -e "ssh -i ~/.ssh/id_ed25519_oxford" \
  --exclude='projects/' \
  --exclude='.cache/' \
  --exclude='.local/' \
  --filter=':- .gitignore' \
  ~/ "$DEST/home/" >> "$LOG" 2>&1

# Sync crontab backup
rsync -avz -e "ssh -i ~/.ssh/id_ed25519_oxford" \
  ~/projects/rsync/crontab.bak "$DEST/crontab.bak" >> "$LOG" 2>&1

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$TIMESTAMP] rsync backup complete" >> "$LOG"
echo "---" >> "$LOG"
