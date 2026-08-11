#!/bin/bash
# cleanup_cron.sh
# Deletes files in all logs_in and reports_out directories older than 7 days

find /opt/log_agent/drop_zones/*/* -type f -mtime +7 -exec rm -f {} \;
