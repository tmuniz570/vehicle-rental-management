import os
import pytz
from app import app, basedir, run_daily_jobs
from apscheduler.schedulers.background import BackgroundScheduler

# Garante que a pasta de uploads existe
uploads_dir = os.path.join(basedir, 'static', 'uploads')
os.makedirs(uploads_dir, exist_ok=True)

# Inicia o agendador de tarefas diárias se habilitado
if os.environ.get('ENABLE_SCHEDULER', 'true').lower() in ('true', '1', 'yes'):
    try:
        scheduler = BackgroundScheduler(timezone=pytz.timezone('Europe/London'))
        scheduler.add_job(func=run_daily_jobs, trigger="cron", hour=1, minute=0)
        scheduler.start()
        print("[WSGI] APScheduler iniciado com sucesso (Rotinas diárias à 01:00 de Londres).")
    except Exception as e:
        print(f"[WSGI] Aviso do agendador: {e}")

# Expõe as referências padrão para servidores WSGI (Gunicorn, Waitress, uWSGI)
application = app

if __name__ == "__main__":
    import waitress
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"[*] Iniciando Servidor de Produção WSGI (Waitress) em http://{host}:{port}")
    print("[*] Multi-threaded: 8 workers ativos para alta concorrência.")
    waitress.serve(app, host=host, port=port, threads=8)
