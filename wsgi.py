"""
Production WSGI Entry Point for FF Motors Fleet Management System
Powered by Waitress (Multi-threaded Production WSGI Server for Windows & Linux)
"""
import os
from waitress import serve
from app import app, basedir, run_daily_jobs
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

# Ensure uploads directory exists
uploads_dir = os.path.join(basedir, 'static', 'uploads')
os.makedirs(uploads_dir, exist_ok=True)

# Start background scheduler for automated UK rental billing and deposit holds
scheduler = BackgroundScheduler(timezone=pytz.timezone('Europe/London'))
scheduler.add_job(func=run_daily_jobs, trigger="cron", hour=1, minute=0)
scheduler.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    threads = int(os.environ.get('WAITRESS_THREADS', 6))
    
    print(f"============================================================")
    print(f"  FF MOTORS FLEET MANAGEMENT - PRODUCTION SERVER")
    print(f"  Serving on http://{host}:{port} with {threads} worker threads")
    print(f"  Timezone: Europe/London (Birmingham, UK)")
    print(f"============================================================")
    
    serve(app, host=host, port=port, threads=threads)
