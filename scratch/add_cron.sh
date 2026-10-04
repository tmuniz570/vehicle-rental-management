#!/bin/bash
# FF Motors - Rotinas de Crontab de Produção (Fuso Europe/London)
# 1. 06:00 AM - Limpeza de arquivos órfãos (após backups noturnos do GCP)
# 2. 08:00 AM - Aquecimento de cache e banco de dados (1h antes de abrir a loja às 09:00 AM)

(
  crontab -l 2>/dev/null | grep -v 'cleanup_uploads.py' | grep -v 'warmup'
  echo "0 6 * * * cd /var/www/ffmotors && /var/www/ffmotors/venv/bin/python3 cleanup_uploads.py >> /var/log/ffmotors_cleanup.log 2>&1"
  echo "0 8 * * * cd /var/www/ffmotors && /var/www/ffmotors/venv/bin/python3 warmup.py >> /var/log/ffmotors_warmup.log 2>&1"
) | crontab -
