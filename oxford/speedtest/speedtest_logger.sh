#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
source /etc/environment
LOGFILE="$HOME/Projects/speedtest/speedtest_log.csv"
DATE=$(date +"%Y-%m-%d %H:%M:%S")

# Run test and extract useful fields
RESULT=$(/usr/local/bin/speedtest --format=json --accept-license --accept-gdpr)
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
  --data "{\"text\":\"📡 *Speedtest Results - $HOSTNAME*\n*Date:* $DATE\n*Ping:* ${PING}ms\n*Download:* ${DOWNLOAD} Mbps\n*Upload:* ${UPLOAD} Mbps\n*ISP:* $ISP\"}"
