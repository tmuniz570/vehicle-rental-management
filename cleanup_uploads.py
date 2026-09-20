import os
import glob
from app import app, db
from database import Motorcycle, Client, Contract, Inspection, ContractAttachment

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
EXCLUDE_PREFIXES = ('demo_', 'placeholder')

def run_cleanup():
    print("Starting orphan files cleanup in static/uploads...")
    
    with app.app_context():
        # 1. Collect all valid URLs from the database
        valid_files = set()
        
        # Motorcycles
        # (No uploaded files associated directly with Motorcycle model yet)
                
        # Clients
        for c in Client.query.all():
            for field in [c.url_habilitacao, c.url_habilitacao_verso, c.url_cbt, c.url_comprovante_endereco]:
                if field:
                    clean_name = os.path.basename(field.split('?')[0].strip())
                    if clean_name:
                        valid_files.add(clean_name)
                    
        # Contracts (active files + immutable snapshot documents)
        for c in Contract.query.all():
            for field in [
                c.url_seguro, c.url_comprovante_deposito, 
                c.assinatura_cliente_inicial, c.assinatura_cliente_devolucao,
                c.url_habilitacao, c.url_habilitacao_verso, c.url_cbt, c.url_comprovante_endereco
            ]:
                if field:
                    clean_name = os.path.basename(field.split('?')[0].strip())
                    if clean_name:
                        valid_files.add(clean_name)
                    
        # Contract Attachments
        for a in ContractAttachment.query.all():
            if a.url_arquivo:
                clean_name = os.path.basename(a.url_arquivo.split('?')[0].strip())
                if clean_name:
                    valid_files.add(clean_name)
                
        # Inspections (can have multiple photos separated by comma)
        for i in Inspection.query.all():
            if i.url_fotos:
                urls = [u.strip() for u in i.url_fotos.split(',') if u.strip()]
                for u in urls:
                    clean_name = os.path.basename(u.split('?')[0].strip())
                    if clean_name:
                        valid_files.add(clean_name)
                    
        print(f"Found {len(valid_files)} valid file references in the database.")
        
        # 2. Scan directory
        all_files = glob.glob(os.path.join(UPLOAD_FOLDER, '*'))
        deleted_count = 0
        total_bytes_saved = 0
        
        for filepath in all_files:
            if not os.path.isfile(filepath):
                continue
                
            filename = os.path.basename(filepath)
            
            # Skip hidden files (.gitkeep, etc.) and excluded prefixes
            if filename.startswith('.') or filename in ('.gitkeep', '.gitignore') or filename.startswith(EXCLUDE_PREFIXES):
                continue
                
            # If not in database, delete it
            if filename not in valid_files:
                file_size = os.path.getsize(filepath)
                try:
                    os.remove(filepath)
                    deleted_count += 1
                    total_bytes_saved += file_size
                    print(f"Deleted orphan file: {filename}")
                except Exception as e:
                    print(f"Error deleting {filename}: {e}")
                    
        print("Cleanup finished!")
        print(f"Total files deleted: {deleted_count}")
        print(f"Total space freed: {total_bytes_saved / 1024 / 1024:.2f} MB")

if __name__ == '__main__':
    run_cleanup()
