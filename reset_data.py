import os
import sys
import shutil
import sqlite3
from app import app, db
from database import (
    AuditLog, ContractAttachment, FinancialTransaction, Inspection,
    Contract, Client, Motorcycle, Claim, JobExecutionLock, User
)

def clean_all(keep_users=False):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'ffmotors.db')
    uploads_dir = os.path.join(base_dir, 'static', 'uploads')
    demo_assets_dir = os.path.join(base_dir, 'static', 'demo_assets')

    print("=== Iniciando Limpeza Geral do Sistema (reset_data.py) ===")
    if keep_users:
        print("Opção --keep-users ativada: Usuários e operadores serão preservados.")

    # 1. Clean database tables via SQLAlchemy
    with app.app_context():
        try:
            print("Limpando tabelas do banco de dados...")
            AuditLog.query.delete()
            ContractAttachment.query.delete()
            FinancialTransaction.query.delete()
            Inspection.query.delete()
            Claim.query.delete()
            Contract.query.delete()
            Motorcycle.query.delete()
            Client.query.delete()
            JobExecutionLock.query.delete()
            
            if not keep_users:
                User.query.delete()
                print("Tabela usuarios limpa.")

            db.session.commit()
            print("Tabelas operacionais limpas com sucesso via SQLAlchemy.")

            db_uri = str(app.config.get('SQLALCHEMY_DATABASE_URI', '')).lower()

            # SQLite: zera sqlite_sequence e executa checkpoint/vacuum
            if 'sqlite' in db_uri and os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence';")
                if cursor.fetchone():
                    cursor.execute("DELETE FROM sqlite_sequence;")
                    print("Sequências de autoincrement SQLite zeradas.")
                conn.commit()
                cursor.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                cursor.execute("VACUUM;")
                conn.close()
                print("Banco de dados SQLite vacuum e checkpoint executados com sucesso.")
            
            # PostgreSQL: reseta sequências serial
            elif 'postgres' in db_uri:
                tables = ['clientes', 'contratos', 'contrato_anexos', 'vistorias', 'financeiro_transacoes', 'logs_auditoria', 'claims', 'job_locks']
                if not keep_users:
                    tables.append('usuarios')
                for t in tables:
                    try:
                        db.session.execute(db.text(f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), 1, false);"))
                    except Exception:
                        pass
                db.session.commit()
                print("Sequências de ID do PostgreSQL reiniciadas com sucesso.")

        except Exception as e:
            db.session.rollback()
            print(f"Aviso durante limpeza do banco de dados: {e}")

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

    print("=== Limpeza Concluída com Sucesso! ===\n")

if __name__ == '__main__':
    keep = '--keep-users' in sys.argv
    clean_all(keep_users=keep)
