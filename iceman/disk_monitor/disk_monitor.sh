#!/bin/bash

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export SLACK_WEBHOOK_ICEMAN=$(grep SLACK_WEBHOOK_ICEMAN /etc/environment | cut -d= -f2)

THRESHOLD=80
MOUNT="/"
HOSTNAME=$(hostname)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG="/home/pi/projects/iceman/disk_monitor/logs/disk_monitor.log"
DAY_OF_WEEK=$(date '+%u')  # 1=Monday

USAGE=$(df "$MOUNT" | awk 'NR==2 {gsub("%",""); print $5}')
TOTAL=$(df -h "$MOUNT" | awk 'NR==2 {print $2}')
USED=$(df -h "$MOUNT" | awk 'NR==2 {print $3}')
FREE=$(df -h "$MOUNT" | awk 'NR==2 {print $4}')

echo "[$TIMESTAMP] disk=${USAGE}% used=${USED} free=${FREE} total=${TOTAL}" >> "$LOG"

# Alert if over threshold
if [ "$USAGE" -ge "$THRESHOLD" ]; then
    curl -s -X POST "$SLACK_WEBHOOK_ICEMAN" \
        -H 'Content-type: application/json' \
        --data "{\"text\":\"⚠️ *Disk Alert — $HOSTNAME*\n*Mount:* $MOUNT\n*Usage:* ${USAGE}%\n*Used:* $USED / $TOTAL\n*Free:* $FREE\n*Time:* $TIMESTAMP\"}"
fi

# Weekly Monday report regardless of threshold
if [ "$DAY_OF_WEEK" -eq 1 ]; then
    curl -s -X POST "$SLACK_WEBHOOK_ICEMAN" \
        -H 'Content-type: application/json' \
        --data "{\"text\":\"💾 *Weekly Disk Report — $HOSTNAME*\n*Mount:* $MOUNT\n*Usage:* ${USAGE}%\n*Used:* $USED / $TOTAL\n*Free:* $FREE\"}"
fi
