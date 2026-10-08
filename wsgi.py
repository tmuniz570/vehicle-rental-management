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
        from warmup import run_warmup
        scheduler = BackgroundScheduler(timezone=pytz.timezone('Europe/London'))
        
        # 1. Rotinas Diárias de Cobranças e Quarentena de Depósitos às 01:00 AM (Londres)
        scheduler.add_job(
            func=run_daily_jobs,
            trigger="cron",
            hour=1,
            minute=0,
            id="daily_rent_and_deposit_jobs",
            replace_existing=True,
            misfire_grace_time=3600
        )

        # 2. Limpeza Diária de Uploads Órfãos às 06:00 AM (Londres)
        def _exec_cleanup_scheduler():
            from cleanup_uploads import run_cleanup
            run_cleanup(dry_run=False)

        scheduler.add_job(
            func=_exec_cleanup_scheduler,
            trigger="cron",
            hour=6,
            minute=0,
            id="daily_orphan_uploads_cleanup_job",
            replace_existing=True,
            misfire_grace_time=3600
        )

        # 3. Warm-up Matinal de Cache e Conexões às 08:00 AM (Londres, 1h antes da abertura da loja)
        def _exec_warmup_scheduler():
            run_warmup(origem='System/Scheduler')

        scheduler.add_job(
            func=_exec_warmup_scheduler,
            trigger="cron",
            hour=8,
            minute=0,
            id="morning_warmup_job",
            replace_existing=True,
            misfire_grace_time=3600
        )

        scheduler.start()
        print(f"[WSGI] APScheduler iniciado com sucesso no Worker PID {os.getpid()} (Cobranças 01:00, Limpeza 06:00, Warm-up 08:00 AM Europe/London, misfire_grace=3600s).")

        # Auto-recuperação no startup: se as rotinas de hoje ainda não tiverem sido executadas
        # (ex: deploy após 01:00 AM ou restart do serviço), executa em thread assíncrona
        # no worker eleito com lock de scheduler via force=True para garantir sincronia imediata.
        import threading
        def _check_and_run_startup_jobs():
            try:
                import time
                from app import get_london_now
                time.sleep(3)
                print("[WSGI Startup] Executando rotinas diárias de catch-up no boot/deploy...")
                run_daily_jobs(force=True)

                # Se o servidor inicializar durante a manhã (08:00 às 11:59 AM Londres), executa warm-up de inicialização
                london_now = get_london_now()
                if 8 <= london_now.hour < 12:
                    print(f"[WSGI Startup] Horário matinal detectado ({london_now.strftime('%H:%M %Z')}). Executando warm-up no boot...")
                    run_warmup(origem='System/StartupBoot')
            except Exception as e_start:
                print(f"[WSGI Startup Job Error]: {e_start}")

        threading.Thread(target=_check_and_run_startup_jobs, daemon=True).start()
    except Exception as e:
        print(f"[WSGI] Aviso do agendador: {e}")

# O suporte a Proxy Reverso (Nginx / Cloudflare) já é configurado de forma centralizada em app.py
# (ProxyFix com x_for=1, x_proto=1, x_host=1, x_prefix=1) para evitar duplicação de camadas de proxy.

# Expõe as referências padrão para servidores WSGI (Gunicorn, Waitress, uWSGI)
application = app

if __name__ == "__main__":
    import waitress
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"[*] Iniciando Servidor de Produção WSGI (Waitress) em http://{host}:{port}")
    print("[*] Multi-threaded: 8 workers ativos para alta concorrência.")
    waitress.serve(app, host=host, port=port, threads=8)
