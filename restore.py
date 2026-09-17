import os
import sys
import zipfile
import subprocess
import re

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
        env_path = os.path.join(base_dir, '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                env_content = f.read()
            db_match = re.search(r'^DATABASE_URL=(postgresql[^\s]+)', env_content, re.MULTILINE)
            if db_match:
                db_url = db_match.group(1)
                try:
                    subprocess.run(['psql', db_url, '-f', db_dump_file], check=True)
                    print("PostgreSQL database restored successfully.")
                except Exception as e:
                    print(f"Warning: Failed to restore PostgreSQL database: {e}")
            else:
                print("Warning: .env does not contain a valid DATABASE_URL for Postgres, but a dump exists.")
        else:
            print("Warning: .env file not found. Could not restore PostgreSQL database.")
        os.remove(db_dump_file)
        
    print("Application successfully restored to the chosen restore point!")

if __name__ == '__main__':
    selected = sys.argv[1] if len(sys.argv) > 1 else None
    restore_backup(selected)
