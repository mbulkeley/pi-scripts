#!/bin/bash

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

WOLFMAN="macbook@wolfman.local"
SSH_KEY="$HOME/.ssh/id_ed25519_wolfman"
DEST="$WOLFMAN:/Volumes/Nextcloud"
LOG="$HOME/Projects/pi-scripts/oxford/backup/logs/oxford_backup.log"
SLACK_WEBHOOK="$SLACK_WEBHOOK_OXFORD"
LOCKFILE="/tmp/oxford_to_samsung.lock"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

mkdir -p $HOME/Projects/pi-scripts/oxford/backup/logs

# Prevent overlapping runs
if [ -e "$LOCKFILE" ] && kill -0 "$(cat "$LOCKFILE")" 2>/dev/null; then
    echo "[$TIMESTAMP] Backup already running, skipping" >> "$LOG"
    exit 1
fi
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT

# Check if WOLFMAN is reachable
if ! ping -c 3 -W 5 wolfman.local > /dev/null 2>&1; then
    curl -s -X POST "$SLACK_WEBHOOK" \
      -H 'Content-type: application/json' \
      --data "{\"text\":\"⚠️ *OXFORD Backup FAILED*\n*Time:* $TIMESTAMP\n*Reason:* WOLFMAN is unreachable - backup skipped\"}"
    echo "[$TIMESTAMP] WOLFMAN unreachable - backup skipped" >> "$LOG"
    exit 1
fi

echo "[$TIMESTAMP] Starting OXFORD → Samsung backup via WOLFMAN" >> "$LOG"
START_TIME=$(date +%s)

rsync -av --no-perms --no-group --no-owner --ignore-errors --partial --stats -e "ssh -i $SSH_KEY" \
  --exclude='*.log' \
  --exclude='*.log.1' \
  --exclude='appdata_*/preview/**' \
  /home/pi/nextcloud/nextcloud/data/ "$DEST/data/" >> "$LOG" 2>&1

RSYNC_EXIT=$?
END_TIME=$(date +%s)
DURATION=$(( (END_TIME - START_TIME) / 60 ))
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

FILES_TRANSFERRED=$(grep "Number of regular files transferred:" "$LOG" | tail -1 | grep -oE '[0-9,]+$')
TOTAL_SIZE_RAW=$(grep "Total transferred file size:" "$LOG" | tail -1 | grep -oE '[0-9,]+' | head -1)
TOTAL_SIZE_GB=$(echo "${TOTAL_SIZE_RAW:-0}" | tr -d ',' | awk '{printf "%.2f", $1/1073741824}')

if [ $RSYNC_EXIT -eq 0 ] || [ $RSYNC_EXIT -eq 23 ] || [ $RSYNC_EXIT -eq 24 ]; then
    curl -s -X POST "$SLACK_WEBHOOK" \
      -H 'Content-type: application/json' \
      --data "{\"text\":\"💾 *OXFORD → Samsung backup complete*\n*Time:* $TIMESTAMP\n*Duration:* ${DURATION} min\n*Files transferred:* ${FILES_TRANSFERRED:-0}\n*Data transferred:* ${TOTAL_SIZE_GB} GB\"}"
    echo "[$TIMESTAMP] Backup complete (exit $RSYNC_EXIT) - ${FILES_TRANSFERRED:-0} files, ${TOTAL_SIZE_GB} GB, ${DURATION} min" >> "$LOG"
else
    curl -s -X POST "$SLACK_WEBHOOK" \
      -H 'Content-type: application/json' \
      --data "{\"text\":\"⚠️ *OXFORD Backup FAILED*\n*Time:* $TIMESTAMP\n*Reason:* rsync exited with code $RSYNC_EXIT — check log\"}"
    echo "[$TIMESTAMP] Backup FAILED (rsync exit $RSYNC_EXIT)" >> "$LOG"
fi

echo "---" >> "$LOG"
