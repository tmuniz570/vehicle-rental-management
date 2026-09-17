import os
import shutil
import sqlite3

def clean_all():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'ffmotors.db')
    uploads_dir = os.path.join(base_dir, 'static', 'uploads')
    demo_assets_dir = os.path.join(base_dir, 'static', 'demo_assets')

    # 1. Clean database
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = OFF;")
        
        tables = ['logs_auditoria', 'contrato_anexos', 'financeiro_transacoes', 'vistorias', 'contratos', 'clientes', 'motos', 'claims']
        for table in tables:
            cursor.execute(f"DELETE FROM {table};")
            print(f"Limpa tabela: {table}")
        
        # Reset autoincrement sequences
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence';")
        if cursor.fetchone():
            cursor.execute("DELETE FROM sqlite_sequence;")
            print("Sequências de autoincrement zeradas.")
            
        conn.commit()
        cursor.execute("VACUUM;")
        cursor.execute("PRAGMA foreign_keys = ON;")
        conn.close()
        print("Banco de dados SQLite limpo e otimizado com sucesso.")
    else:
        print("Arquivo ffmotors.db não encontrado.")

    # 2. Clean static/uploads and restore demo assets
    if os.path.exists(uploads_dir):
        deleted_count = 0
        for item in os.listdir(uploads_dir):
            if item == '.gitkeep':
                continue
            item_path = os.path.join(uploads_dir, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.remove(item_path)
                    deleted_count += 1
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    deleted_count += 1
            except Exception as e:
                print(f"Erro ao remover {item_path}: {e}")
        
        print(f"Diretório static/uploads limpo com sucesso! ({deleted_count} arquivos removidos).")
    else:
        os.makedirs(uploads_dir, exist_ok=True)

    # Ensure .gitkeep exists
    gitkeep_path = os.path.join(uploads_dir, '.gitkeep')
    if not os.path.exists(gitkeep_path):
        with open(gitkeep_path, 'w') as f:
            pass

    # Restore demo assets if available
    if os.path.exists(demo_assets_dir):
        restored = 0
        for asset in os.listdir(demo_assets_dir):
            src = os.path.join(demo_assets_dir, asset)
            dst = os.path.join(uploads_dir, asset)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                restored += 1
        print(f"Restaurados {restored} assets de demonstração em static/uploads.")

if __name__ == '__main__':
    clean_all()
