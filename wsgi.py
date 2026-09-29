import os
import pytz
from app import app, basedir, run_daily_jobs
from apscheduler.schedulers.background import BackgroundScheduler

# Garante que a pasta de uploads existe
uploads_dir = os.path.join(basedir, 'static', 'uploads')
os.makedirs(uploads_dir, exist_ok=True)

_scheduler_lock_fd = None

def _acquire_scheduler_lock():
    """
    Garante que em ambientes multi-worker (como Gunicorn no Linux),
    apenas 1 worker inicialize o BackgroundScheduler.
    Se o worker morrer, o SO libera o lock automaticamente para o próximo.
    No Windows / Waitress, opera normalmente em processo único.
    """
    global _scheduler_lock_fd
    if os.environ.get('ENABLE_SCHEDULER', 'true').lower() not in ('true', '1', 'yes'):
        return False
    try:
        import fcntl
        lock_path = os.path.join(basedir, '.scheduler.lock')
        try:
            _scheduler_lock_fd = open(lock_path, 'a+')
        except (PermissionError, IOError):
            lock_path = '/tmp/.ffmotors_scheduler.lock'
            _scheduler_lock_fd = open(lock_path, 'a+')

        fcntl.flock(_scheduler_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except ImportError:
        # Ambiente Windows / Waitress mono-processo
        return True
    except BlockingIOError:
        print(f"[WSGI] Worker PID {os.getpid()} ignorou APScheduler: já ativo em outro worker.")
        return False
    except Exception as e:
        print(f"[WSGI] Aviso do lock do agendador: {e}")
        return False

# Inicia o agendador de tarefas diárias se este for o worker eleito
if _acquire_scheduler_lock():
    try:
        scheduler = BackgroundScheduler(timezone=pytz.timezone('Europe/London'))
        scheduler.add_job(
            func=run_daily_jobs,
            trigger="cron",
            hour=1,
            minute=0,
            id="daily_rent_and_deposit_jobs",
            replace_existing=True,
            misfire_grace_time=3600
        )
        scheduler.start()
        print(f"[WSGI] APScheduler iniciado com sucesso no Worker PID {os.getpid()} (Rotinas diárias à 01:00 de Londres, misfire_grace=3600s).")

        # Auto-recuperação no startup: se as rotinas de hoje ainda não tiverem sido executadas
        # (ex: deploy após 01:00 AM ou restart do serviço), executa em thread assíncrona.
        import threading
        def _check_and_run_startup_jobs():
            try:
                import time
                time.sleep(3)
                run_daily_jobs()
            except Exception as e_start:
                print(f"[WSGI Startup Job Error]: {e_start}")

        threading.Thread(target=_check_and_run_startup_jobs, daemon=True).start()
    except Exception as e:
        print(f"[WSGI] Aviso do agendador: {e}")

# Habilita suporte a Proxy Reverso (Cloudflare, Render, AWS ALB, Nginx)
# Garante que request.remote_addr seja o IP real do cliente na trilha de auditoria e url_for use HTTPS
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Expõe as referências padrão para servidores WSGI (Gunicorn, Waitress, uWSGI)
application = app

if __name__ == "__main__":
    import waitress
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"[*] Iniciando Servidor de Produção WSGI (Waitress) em http://{host}:{port}")
    print("[*] Multi-threaded: 8 workers ativos para alta concorrência.")
    waitress.serve(app, host=host, port=port, threads=8)
