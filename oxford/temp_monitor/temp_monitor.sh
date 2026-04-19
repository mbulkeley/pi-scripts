#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
source /etc/environment
SLACK_WEBHOOK="${SLACK_WEBHOOK_OXFORD}"
THRESHOLD=65
TEMP=$(vcgencmd measure_temp | grep -o '[0-9]*\.[0-9]*')
HOSTNAME=$(hostname)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

if (( $(echo "$TEMP > $THRESHOLD" | bc -l) )); then
  curl -s -X POST $SLACK_WEBHOOK \
    -H 'Content-type: application/json' \
    --data "{\"text\":\"🌡️ *Temperature Alert!* \n*Host:* $HOSTNAME\n*Temp:* ${TEMP}°C\n*Time:* $TIMESTAMP\n*Threshold:* ${THRESHOLD}°C\"}"
fi
