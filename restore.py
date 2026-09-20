import os
import sys
import zipfile
import subprocess
import re
import sqlite3

def list_backups():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backups_dir = os.path.join(base_dir, 'backups')
    if not os.path.exists(backups_dir):
        return []
    files = [f for f in os.listdir(backups_dir) if f.endswith('.zip')]
    files.sort(reverse=True)
    return files

def restore_backup(backup_file=None):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backups_dir = os.path.join(base_dir, 'backups')
    
    backups = list_backups()
    if not backups:
        print("No backups found in backups/ directory.")
        return
        
    if not backup_file:
        print("\nAvailable restore points:")
        for idx, b in enumerate(backups):
            print(f"[{idx+1}] {b}")
        
        choice = input("\nEnter number to restore (or 'q' to cancel): ").strip()
        if choice.lower() == 'q' or not choice.isdigit():
            print("Cancelled.")
            return
            
        idx = int(choice) - 1
        if 0 <= idx < len(backups):
            backup_file = backups[idx]
        else:
            print("Invalid choice.")
            return

    target_zip = os.path.join(backups_dir, backup_file)
    print(f"\nRestoring from {backup_file} ...")
    
    with zipfile.ZipFile(target_zip, 'r') as zipf:
        zipf.extractall(base_dir)
        
    db_dump_file = os.path.join(base_dir, 'database_dump.sql')
    if os.path.exists(db_dump_file):
        print("\nPostgreSQL dump found in backup. Restoring database...")
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            env_path = os.path.join(base_dir, '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    env_content = f.read()
                db_match = re.search(r'^DATABASE_URL=(postgres(?:ql)?:\/\/[^\s]+)', env_content, re.MULTILINE)
                if db_match:
                    db_url = db_match.group(1)
        
        if db_url:
            pg_url = db_url.replace("postgres://", "postgresql://", 1) if db_url.startswith("postgres://") else db_url
            try:
                subprocess.run(['psql', pg_url, '-f', db_dump_file], check=True)
                print("PostgreSQL database restored successfully.")
            except Exception as e:
                print(f"Warning: Failed to restore PostgreSQL database: {e}")
        else:
            print("Warning: DATABASE_URL not found for Postgres, but a dump exists in the backup.")
            
        try:
            os.remove(db_dump_file)
        except Exception:
            pass
    else:
        # SQLite: Check if database exists and checkpoint
        sqlite_file = os.path.join(base_dir, 'ffmotors.db')
        if os.path.exists(sqlite_file):
            try:
                conn = sqlite3.connect(sqlite_file)
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                conn.close()
                print("SQLite database verified and checkpointed.")
            except Exception as e:
                print(f"Notice: SQLite verification note: {e}")
        
    print("Application successfully restored to the chosen restore point!")

if __name__ == '__main__':
    selected = sys.argv[1] if len(sys.argv) > 1 else None
    restore_backup(selected)
