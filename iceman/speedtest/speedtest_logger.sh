#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export SLACK_WEBHOOK_ICEMAN=$(grep SLACK_WEBHOOK_ICEMAN /etc/environment | cut -d= -f2)
LOGFILE="/home/pi/projects/iceman/speedtest/logs/speedtest_log.csv"
DATE=$(date +"%Y-%m-%d %H:%M:%S")
SLACK_WEBHOOK="${SLACK_WEBHOOK_ICEMAN}"

# --- Run test with one retry on failure ---
RESULT=$(/usr/local/bin/speedtest-ookla --format=json --accept-license --accept-gdpr 2>/dev/null)
PING=$(echo "$RESULT" | jq -r '.ping.latency // empty')

if [ -z "$PING" ]; then
  # First attempt failed to produce valid data — wait and retry once
  sleep 30
  RESULT=$(/usr/local/bin/speedtest-ookla --format=json --accept-license --accept-gdpr 2>/dev/null)
  PING=$(echo "$RESULT" | jq -r '.ping.latency // empty')
fi

TEMP=$(vcgencmd measure_temp | grep -o '[0-9]*\.[0-9]*')

if [ -z "$PING" ]; then
  # Both attempts failed — log it quietly, skip Slack post
  echo "$DATE,FAILED,FAILED,FAILED,FAILED" >> "$LOGFILE"
  exit 0
fi

DOWNLOAD=$(echo "$RESULT" | jq '.download.bandwidth' | awk '{print $1/125000}')
UPLOAD=$(echo "$RESULT" | jq '.upload.bandwidth' | awk '{print $1/125000}')
ISP=$(echo "$RESULT" | jq -r '.isp')

# Create header if file doesn't exist
if [ ! -f "$LOGFILE" ]; then
  echo "Date,Ping (ms),Download (Mbps),Upload (Mbps),ISP" > "$LOGFILE"
fi

# Append data
echo "$DATE,$PING,$DOWNLOAD,$UPLOAD,$ISP" >> "$LOGFILE"

# Post to Slack
curl -s -o /dev/null -X POST "$SLACK_WEBHOOK" \
  -H 'Content-type: application/json' \
  --data "{\"text\":\"📡 *Speedtest Results - $HOSTNAME*\n*Date:* $DATE\n*Ping:* ${PING}ms\n*Download:* ${DOWNLOAD} Mbps\n*Upload:* ${UPLOAD} Mbps\n*ISP:* $ISP\n*Temp:* ${TEMP}°C\"}"
