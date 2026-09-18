#!/bin/bash
(crontab -l 2>/dev/null; echo "0 7 * * * cd /var/www/ffmotors && /var/www/ffmotors/venv/bin/python3 cleanup_uploads.py >> /var/log/ffmotors_cleanup.log 2>&1") | crontab -
