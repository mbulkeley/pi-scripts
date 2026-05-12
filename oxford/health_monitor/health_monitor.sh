#!/bin/bash
# health_monitor.sh — OXFORD system health check
# Checks: load average, memory, zombie processes, Docker containers, cloudflared
# Schedule: every 15 min via cron
# Logs: ~/Projects/pi-scripts/oxford/health_monitor/logs/health_monitor.log

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# --- Config ---
SLACK_WEBHOOK=$(grep SLACK_WEBHOOK_OXFORD /etc/environment | cut -d= -f2)
LOG_DIR="$(dirname "$0")/logs"
mkdir -p "$LOG_DIR"

LOAD_THRESHOLD=2.0       # 4-core Pi 4; sustained >2 is worth flagging
MEM_THRESHOLD=85         # percent used
REQUIRED_CONTAINERS="nextcloud-app nextcloud-db nextcloud-redis"

HOSTNAME=$(hostname)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
ALERTS=()

log() {
  echo "[$TIMESTAMP] $1" >> "$LOG_DIR/health_monitor.log"
}

slack() {
  local msg="$1"
  curl -s -X POST -H 'Content-type: application/json' \
    --data "{\"text\":\"$msg\"}" \
    "$SLACK_WEBHOOK" > /dev/null
}

# --- Load Average ---
LOAD=$(awk '{print $1}' /proc/loadavg)
log "Load average (1m): $LOAD"
if (( $(echo "$LOAD > $LOAD_THRESHOLD" | bc -l) )); then
  ALERTS+=("⚠️ *High load* on $HOSTNAME: ${LOAD} (threshold: ${LOAD_THRESHOLD})")
fi

# --- Memory ---
read -r MEM_TOTAL MEM_USED <<< $(free -m | awk '/Mem:/ {print $2, $3}')
MEM_PCT=$(awk "BEGIN {printf \"%.0f\", ($MEM_USED/$MEM_TOTAL)*100}")
log "Memory: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PCT}%)"
if [ "$MEM_PCT" -gt "$MEM_THRESHOLD" ]; then
  ALERTS+=("⚠️ *High memory* on $HOSTNAME: ${MEM_PCT}% used (${MEM_USED}MB / ${MEM_TOTAL}MB)")
fi

# --- Zombie Processes ---
ZOMBIES=$(ps aux | awk '$8 == "Z"' | wc -l)
log "Zombie processes: $ZOMBIES"
if [ "$ZOMBIES" -gt 0 ]; then
  ZOMBIE_NAMES=$(ps aux | awk '$8 == "Z" {print $11}' | tr '\n' ', ')
  ALERTS+=("🧟 *Zombie processes* on $HOSTNAME: ${ZOMBIES} found (${ZOMBIE_NAMES})")
fi

# --- Docker Containers ---
for CONTAINER in $REQUIRED_CONTAINERS; do
  STATUS=$(docker inspect --format='{{.State.Status}}' "$CONTAINER" 2>/dev/null)
  if [ -z "$STATUS" ]; then
    log "Docker: $CONTAINER — NOT FOUND"
    ALERTS+=("🐳 *Docker container missing* on $HOSTNAME: \`$CONTAINER\` not found")
  elif [ "$STATUS" != "running" ]; then
    log "Docker: $CONTAINER — $STATUS"
    ALERTS+=("🐳 *Docker container down* on $HOSTNAME: \`$CONTAINER\` is $STATUS")
  else
    log "Docker: $CONTAINER — running"
  fi
done

# --- Cloudflared ---
if systemctl is-active --quiet cloudflared; then
  log "cloudflared: active"
else
  log "cloudflared: INACTIVE"
  ALERTS+=("🌐 *cloudflared is down* on $HOSTNAME — nextcloud.mauriecloud.com is unreachable")
fi

# --- Send Alerts ---
if [ ${#ALERTS[@]} -gt 0 ]; then
  MSG="*OXFORD health alert* ($(date '+%H:%M'))\n"
  for ALERT in "${ALERTS[@]}"; do
    MSG+="$ALERT\n"
  done
  log "Sending ${#ALERTS[@]} alert(s) to Slack"
  slack "$MSG"
else
  log "All checks passed"
fi
