#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
source /etc/environment
LOGFILE="/home/pi/projects/iceman/speedtest/logs/speedtest_log.csv"
DATE=$(date +"%Y-%m-%d %H:%M:%S")

# Run test
RESULT=$(/usr/bin/speedtest --json)
PING=$(echo $RESULT | /usr/bin/jq '.ping')
DOWNLOAD=$(echo $RESULT | /usr/bin/jq '.download' | awk '{print $1/1000000}')
UPLOAD=$(echo $RESULT | /usr/bin/jq '.upload' | awk '{print $1/1000000}')
ISP=$(echo $RESULT | /usr/bin/jq -r '.client.isp')

# Create header if file doesn't exist
if [ ! -f "$LOGFILE" ]; then
  echo "Date,Ping (ms),Download (Mbps),Upload (Mbps),ISP" > "$LOGFILE"
fi

# Append data
echo "$DATE,$PING,$DOWNLOAD,$UPLOAD,$ISP" >> "$LOGFILE"

# Post to Slack
SLACK_WEBHOOK="${SLACK_WEBHOOK_ICEMAN}"
curl -s -X POST "$SLACK_WEBHOOK" \
  -H 'Content-type: application/json' \
  --data "{\"text\":\"📡 *Speedtest Results - $HOSTNAME*\n*Date:* $DATE\n*Ping:* ${PING}ms\n*Download:* ${DOWNLOAD} Mbps\n*Upload:* ${UPLOAD} Mbps\n*ISP:* $ISP\"}"
