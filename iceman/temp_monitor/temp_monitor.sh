#!/bin/bash
source /etc/environment
THRESHOLD=65
TEMP=$(vcgencmd measure_temp | grep -o '[0-9]*\.[0-9]*')
HOSTNAME=$(hostname)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] temp=${TEMP}°C threshold=${THRESHOLD}°C" >> /home/pi/projects/iceman/temp_monitor/logs/temp_monitor.log

if (( $(echo "$TEMP > $THRESHOLD" | bc -l) )); then
  curl -s -X POST $SLACK_WEBHOOK_ICEMAN \
    -H 'Content-type: application/json' \
    --data "{\"text\":\"🌡️ *Temperature Alert!* \n*Host:* $HOSTNAME\n*Temp:* ${TEMP}°C\n*Time:* $TIMESTAMP\n*Threshold:* ${THRESHOLD}°C\"}"
fi
