import os
import multiprocessing

# Endereço e porta de ligação
bind = f"{os.environ.get('HOST', '0.0.0.0')}:{os.environ.get('PORT', '5000')}"
backlog = 2048

# Quantidade de workers (processos simultâneos)
# Em servidores com poucos recursos (ex: 512MB/1GB RAM), limitamos entre 2 e 4 workers
calculated_workers = min(4, max(2, multiprocessing.cpu_count() * 2))
workers = int(os.environ.get("WEB_CONCURRENCY", calculated_workers))
threads = int(os.environ.get("GUNICORN_THREADS", 2))
worker_class = "gthread"
worker_connections = 1000
timeout = 120
keepalive = 5

# Logs
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")

# Nome do processo
proc_name = "ffmotors_fleet_app"

# Recarregamento em quente desabilitado em produção
reload = False
preload_app = False
