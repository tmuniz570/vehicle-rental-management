import os
import zipfile
import subprocess
import re
import sqlite3
from datetime import datetime

def create_backup():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backups_dir = os.path.join(base_dir, 'backups')
    os.makedirs(backups_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"ffmotors_backup_{timestamp}.zip"
    backup_path = os.path.join(backups_dir, backup_filename)
    
    ignore_dirs = {'venv', 'env', '__pycache__', '.git', 'backups'}
    ignore_exts = {'.pyc', '.pyo'}
    
    # 1. Detect Database Type (PostgreSQL vs SQLite)
    db_dump_file = None
    db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        env_path = os.path.join(base_dir, '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                env_content = f.read()
            db_match = re.search(r'^DATABASE_URL=(postgres(?:ql)?:\/\/[^\s]+)', env_content, re.MULTILINE)
            if db_match:
                db_url = db_match.group(1)
                
    if db_url and (db_url.startswith('postgres://') or db_url.startswith('postgresql://')):
        print("PostgreSQL connection detected! Generating database dump...")
        db_dump_file = os.path.join(base_dir, 'database_dump.sql')
        # Normalize url for pg_dump if needed
        pg_url = db_url.replace("postgres://", "postgresql://", 1) if db_url.startswith("postgres://") else db_url
        try:
            subprocess.run(['pg_dump', pg_url, '-f', db_dump_file], check=True)
            print("PostgreSQL dump successfully generated (database_dump.sql).")
        except Exception as e:
            print(f"Warning: Failed to create PostgreSQL dump: {e}")
            if os.path.exists(db_dump_file):
                os.remove(db_dump_file)
            db_dump_file = None
    else:
        # SQLite: checkpoint WAL file so database file is 100% up-to-date
        sqlite_file = os.path.join(base_dir, 'ffmotors.db')
        if os.path.exists(sqlite_file):
            try:
                conn = sqlite3.connect(sqlite_file)
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                conn.close()
                print("SQLite WAL checkpoint completed.")
            except Exception as e:
                print(f"Notice: SQLite checkpoint skipped: {e}")
    
    print(f"Creating restore point: {backup_filename} ...")
    
    count = 0
    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in ignore_exts:
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, base_dir)
                zipf.write(file_path, arcname)
                count += 1
                
    if db_dump_file and os.path.exists(db_dump_file):
        os.remove(db_dump_file)
        
    size_mb = os.path.getsize(backup_path) / (1024 * 1024)
    print(f"Backup successfully created!")
    print(f"File: {backup_path}")
    print(f"Total files: {count}")
    print(f"Size: {size_mb:.2f} MB")
    return backup_path

if __name__ == '__main__':
    create_backup()
