#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export SLACK_WEBHOOK_OXFORD=$(grep SLACK_WEBHOOK_OXFORD /etc/environment | cut -d= -f2)
LOGFILE="/home/pi/Projects/pi-scripts/oxford/speedtest/logs/speedtest_log.csv"
DATE=$(date +"%Y-%m-%d %H:%M:%S")

# Run test and extract useful fields
RESULT=$(/usr/local/bin/speedtest --format=json --accept-license --accept-gdpr)
TEMP=$(vcgencmd measure_temp | grep -o '[0-9]*\.[0-9]*')
PING=$(echo $RESULT | jq '.ping.latency')
DOWNLOAD=$(echo $RESULT | jq '.download.bandwidth' | awk '{print $1/125000}')
UPLOAD=$(echo $RESULT | jq '.upload.bandwidth' | awk '{print $1/125000}')
ISP=$(echo $RESULT | jq -r '.isp')

# Create header if file doesn’t exist
if [ ! -f "$LOGFILE" ]; then
  echo "Date,Ping (ms),Download (Mbps),Upload (Mbps),ISP" > "$LOGFILE"
fi

# Append data
echo "$DATE,$PING,$DOWNLOAD,$UPLOAD,$ISP" >> "$LOGFILE"

# Post to Slack daily-updates
SLACK_WEBHOOK="${SLACK_WEBHOOK_OXFORD}"

curl -s -X POST "$SLACK_WEBHOOK" \
  -H 'Content-type: application/json' \
  --data "{\"text\":\"📡 *Speedtest Results - $HOSTNAME*\n*Date:* $DATE\n*Ping:* ${PING}ms\n*Download:* ${DOWNLOAD} Mbps\n*Upload:* ${UPLOAD} Mbps\n*ISP:* $ISP\n*Temp:* ${TEMP}°C\"}"
