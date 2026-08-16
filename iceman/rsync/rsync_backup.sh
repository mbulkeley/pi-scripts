#!/bin/bash

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

OXFORD="pi@192.168.178.201"
DEST="$OXFORD:/home/pi/Backup/iceman"
SLACK_WEBHOOK="$SLACK_WEBHOOK_ICEMAN"
SSH_OPT="-e \"ssh -i ~/.ssh/id_ed25519_oxford\""
LOG="/home/pi/projects/iceman/rsync/logs/rsync.log"
MAX_LOG_KB=500
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Cap log size
if [ -f "$LOG" ] && [ $(du -k "$LOG" | cut -f1) -ge $MAX_LOG_KB ]; then
    mv "$LOG" "${LOG}.1"
    gzip "${LOG}.1"
fi

echo "[$TIMESTAMP] Starting rsync backup to OXFORD" >> "$LOG"
LOG_START_LINE=$(wc -l < "$LOG" 2>/dev/null || echo 0)

# Dump crontab
crontab -l > /home/pi/projects/iceman/rsync/crontab.bak 2>/dev/null

# Sync projects/ (excluding venv, caches)
rsync -avz --stats -e "ssh -i ~/.ssh/id_ed25519_oxford" \
  --exclude='venv/' \
  --exclude='.ruff_cache/' \
  --exclude='__pycache__/' \
  ~/projects/ "$DEST/projects/" >> "$LOG" 2>&1

# Sync home dir (dotfiles/configs, excluding projects/)
rsync -avz --stats -e "ssh -i ~/.ssh/id_ed25519_oxford" \
  --exclude='projects/' \
  --exclude='.cache/' \
  --exclude='.local/' \
  --filter=':- .gitignore' \
  ~/ "$DEST/home/" >> "$LOG" 2>&1

# Sync crontab backup
rsync -avz --stats -e "ssh -i ~/.ssh/id_ed25519_oxford" \
  ~/projects/iceman/rsync/crontab.bak "$DEST/crontab.bak" >> "$LOG" 2>&1

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Sum files/bytes transferred across all three rsync calls this run
FILES_TRANSFERRED=$(tail -n +$((LOG_START_LINE + 1)) "$LOG" | grep "Number of regular files transferred:" | grep -oE '[0-9,]+$' | tr -d ',' | awk '{sum+=$1} END{print sum+0}')
TOTAL_SIZE_RAW=$(tail -n +$((LOG_START_LINE + 1)) "$LOG" | grep "Total transferred file size:" | grep -oE '[0-9,]+' | tr -d ',' | awk '{sum+=$1} END{print sum+0}')
TOTAL_SIZE_GB=$(awk "BEGIN{printf \"%.2f\", ${TOTAL_SIZE_RAW:-0}/1073741824}")

# Post to Slack
curl -s -X POST "$SLACK_WEBHOOK" \
  -H 'Content-type: application/json' \
  --data "{\"text\":\"💾 *ICEMAN rsync backup complete*\n*Time:* $TIMESTAMP\n*Destination:* OXFORD\n*Files transferred:* ${FILES_TRANSFERRED:-0}\n*Data transferred:* ${TOTAL_SIZE_GB} GB\"}"

echo "[$TIMESTAMP] rsync backup complete" >> "$LOG"
echo "---" >> "$LOG"
