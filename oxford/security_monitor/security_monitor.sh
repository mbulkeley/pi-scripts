#!/bin/bash
# security_monitor.sh — OXFORD listening-port drift detector
# Flags any TCP listener bound to a non-loopback address that isn't on the
# expected allowlist below. UDP is intentionally out of scope: mDNS/avahi and
# ephemeral client sockets make it too noisy to be a useful signal.
# Schedule: every 15 min via cron
# Logs: ~/Projects/pi-scripts/oxford/security_monitor/logs/security_monitor.log

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

SLACK_WEBHOOK=$(grep SLACK_WEBHOOK_OXFORD /etc/environment | cut -d= -f2)
LOG_DIR="$(dirname "$0")/logs"
mkdir -p "$LOG_DIR"

# 22: SSH. 8080: Nextcloud (LAN via ufw). 8000: meal-planner gunicorn (LAN via ufw).
# 5900 (VNC) is deliberately NOT here — it should stay firewalled/tunnel-only.
EXPECTED_PORTS="22 8080 8000"

HOSTNAME=$(hostname)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
ALERTS=()

log() {
  echo "[$TIMESTAMP] $1" >> "$LOG_DIR/security_monitor.log"
}

slack() {
  local msg="$1"
  curl -s -X POST -H 'Content-type: application/json' \
    --data "{\"text\":\"$msg\"}" \
    "$SLACK_WEBHOOK" > /dev/null
}

is_expected() {
  local port="$1"
  for p in $EXPECTED_PORTS; do
    [ "$p" = "$port" ] && return 0
  done
  return 1
}

while read -r addr; do
  [ -z "$addr" ] && continue
  ip="${addr%:*}"
  port="${addr##*:}"

  # Loopback-only listeners aren't externally reachable — skip them
  case "$ip" in
    127.0.0.1|"[::1]") continue ;;
  esac

  if ! is_expected "$port"; then
    ALERTS+=("🚨 *Unexpected listener* on $HOSTNAME: port $port ($addr)")
  fi
done < <(ss -tlnH 2>/dev/null | awk '{print $4}')

log "Checked listening ports (expected: $EXPECTED_PORTS)"

if [ ${#ALERTS[@]} -gt 0 ]; then
  MSG="*OXFORD security alert* ($(date '+%H:%M'))\n"
  for ALERT in "${ALERTS[@]}"; do
    MSG+="$ALERT\n"
  done
  log "Sending ${#ALERTS[@]} alert(s) to Slack"
  slack "$MSG"
fi
