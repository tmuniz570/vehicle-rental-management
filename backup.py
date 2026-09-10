import os
import zipfile
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
                
    size_mb = os.path.getsize(backup_path) / (1024 * 1024)
    print(f"Backup successfully created!")
    print(f"File: {backup_path}")
    print(f"Total files: {count}")
    print(f"Size: {size_mb:.2f} MB")
    return backup_path

if __name__ == '__main__':
    create_backup()
