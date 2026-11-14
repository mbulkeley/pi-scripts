#!/bin/bash
# Weekly backup of ICEMAN to OXFORD.
#  1. Exports a Pi-hole Teleporter zip into ~/projects/iceman/rsync/pihole-teleporter/ (newest 4 kept)
#  2. Dumps the crontab
#  3. rsyncs ~/projects, the home dir and the crontab dump to OXFORD
#  4. Posts green to Slack only if every step succeeded, red otherwise; exits non-zero on failure
#
# Env overrides (for testing):
#   RSYNC_DEST   rsync destination, default pi@192.168.178.201:/home/pi/Backup/iceman

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

DEST="${RSYNC_DEST:-pi@192.168.178.201:/home/pi/Backup/iceman}"
SSH_CMD="ssh -i /home/pi/.ssh/id_ed25519_oxford -o BatchMode=yes -o ConnectTimeout=15"
LOG="/home/pi/projects/iceman/rsync/logs/rsync.log"
TP_DIR="/home/pi/projects/iceman/rsync/pihole-teleporter"
TP_KEEP=4
MAX_LOG_KB=500

# Webhook: from the environment (cron/ssh get /etc/environment via pam_env), else read it directly
SLACK_WEBHOOK="${SLACK_WEBHOOK_ICEMAN:-$(grep '^SLACK_WEBHOOK_ICEMAN=' /etc/environment 2>/dev/null | cut -d= -f2- | tr -d '"')}"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" >> "$LOG"; }

FAILURES=()

# Cap log size
if [ -f "$LOG" ] && [ "$(du -k "$LOG" | cut -f1)" -ge "$MAX_LOG_KB" ]; then
    mv "$LOG" "${LOG}.1"
    gzip -f "${LOG}.1"
fi

log "Starting rsync backup to $DEST"
LOG_START_LINE=$(wc -l < "$LOG" 2>/dev/null || echo 0)

# --- Pi-hole Teleporter export ---
mkdir -p "$TP_DIR" && chmod 700 "$TP_DIR"
if TP_FILE=$(cd "$TP_DIR" && sudo -n pihole-FTL --teleporter 2>>"$LOG") && [ -f "$TP_DIR/$TP_FILE" ]; then
    sudo -n chown pi:pi "$TP_DIR/$TP_FILE" && chmod 600 "$TP_DIR/$TP_FILE"
    log "Teleporter export OK: $TP_FILE"
else
    log "Teleporter export FAILED"
    FAILURES+=("teleporter export")
fi
# Keep only the newest $TP_KEEP exports
ls -1t "$TP_DIR"/pi-hole_*_teleporter_*.zip 2>/dev/null | tail -n +$((TP_KEEP + 1)) | xargs -r rm -f --

# --- Crontab dump ---
if ! crontab -l > /home/pi/projects/iceman/rsync/crontab.bak 2>>"$LOG"; then
    log "crontab dump FAILED"
    FAILURES+=("crontab dump")
fi

# --- rsync; exit 0 = OK, 24 = some source files vanished mid-transfer (OK), anything else = failure ---
run_rsync() {
    local name="$1"; shift
    rsync -avz --stats -e "$SSH_CMD" "$@" >> "$LOG" 2>&1
    local rc=$?
    if [ "$rc" -eq 0 ] || [ "$rc" -eq 24 ]; then
        log "rsync $name OK (exit $rc)"
    else
        log "rsync $name FAILED (exit $rc)"
        FAILURES+=("$name (exit $rc)")
    fi
}

# projects/ (excluding venv, caches); includes the teleporter exports
run_rsync projects \
  --exclude='venv/' \
  --exclude='.ruff_cache/' \
  --exclude='__pycache__/' \
  /home/pi/projects/ "$DEST/projects/"

# Home dir (dotfiles/configs, excluding projects/)
run_rsync home \
  --exclude='projects/' \
  --exclude='.cache/' \
  --exclude='.local/' \
  --filter=':- .gitignore' \
  /home/pi/ "$DEST/home/"

# Crontab backup
run_rsync crontab \
  /home/pi/projects/iceman/rsync/crontab.bak "$DEST/crontab.bak"

# Sum files/bytes transferred across the rsync calls this run
FILES_TRANSFERRED=$(tail -n +$((LOG_START_LINE + 1)) "$LOG" | grep "Number of regular files transferred:" | grep -oE '[0-9,]+$' | tr -d ',' | awk '{sum+=$1} END{print sum+0}')
TOTAL_SIZE_RAW=$(tail -n +$((LOG_START_LINE + 1)) "$LOG" | grep "Total transferred file size:" | grep -oE '[0-9,]+' | tr -d ',' | awk '{sum+=$1} END{print sum+0}')
TOTAL_SIZE_GB=$(awk "BEGIN{printf \"%.2f\", ${TOTAL_SIZE_RAW:-0}/1073741824}")

# --- Slack ---
if [ ${#FAILURES[@]} -eq 0 ]; then
    COLOR="#2eb886"
    TEXT=$(printf '✅ *ICEMAN rsync backup OK*\n*Time:* %s\n*Destination:* %s\n*Files transferred:* %s\n*Data transferred:* %s GB\n*Teleporter:* %s' \
        "$(ts)" "$DEST" "$FILES_TRANSFERRED" "$TOTAL_SIZE_GB" "${TP_FILE:-none}")
else
    COLOR="#d40e0d"
    TEXT=$(printf '🚨 *ICEMAN rsync backup FAILED*\n*Time:* %s\n*Destination:* %s\n*Failed:* %s\nSee %s' \
        "$(ts)" "$DEST" "$(IFS=,; echo "${FAILURES[*]}" | sed 's/,/, /g')" "$LOG")
fi

if [ -n "$SLACK_WEBHOOK" ]; then
    PAYLOAD=$(jq -n --arg c "$COLOR" --arg t "$TEXT" '{attachments: [{color: $c, text: $t, mrkdwn_in: ["text"]}]}')
    HTTP=$(curl -s -o /dev/null -w '%{http_code}' --max-time 30 -X POST \
        -H 'Content-type: application/json' --data "$PAYLOAD" "$SLACK_WEBHOOK")
    log "Slack post HTTP $HTTP"
else
    log "Slack webhook not set; no notification sent"
fi

if [ ${#FAILURES[@]} -eq 0 ]; then
    log "rsync backup complete"
    echo "---" >> "$LOG"
    exit 0
else
    log "rsync backup FAILED: ${FAILURES[*]}"
    echo "---" >> "$LOG"
    exit 1
fi
