"""
FF Motors App - Morning Cache & Database Pre-Warmer
Executado preferencialmente via crontab às 08:00 AM (Europe/London),
1 hora antes da abertura da loja (09:00 AM) e 2 horas após a limpeza de mídias (06:00 AM).
"""
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from app import app, _compilar_dados_dashboard, get_london_now, registrar_log
from database import db, Client, Motorcycle

def run_warmup():
    print(f"[{get_london_now().strftime('%Y-%m-%d %H:%M:%S %Z')}] Initializing FF Motors morning warm-up...")
    t0 = time.time()
    
    with app.app_context():
        # 1. Compila dados do Dashboard (Motos, Contratos, Faturamento, Avisos)
        dados = _compilar_dados_dashboard(include_claims=True)
        
        # 2. Pré-aquece buffers de tabelas frequentes
        _ = db.session.query(Client.id, Client.nome, Client.telefone).limit(30).all()
        _ = db.session.query(Motorcycle.placa, Motorcycle.status).limit(30).all()

        elapsed_ms = round((time.time() - t0) * 1000, 2)
        
        try:
            registrar_log(
                'SYSTEM_WARMUP',
                'System/WarmupScript',
                None,
                f"Warm-up CLI matinal executado em {elapsed_ms}ms ({dados.get('total_motos')} motos ativas, {dados.get('contratos_ativos')} contratos ativos)."
            )
        except Exception:
            pass

    print(f"✓ Warm-up completed successfully in {elapsed_ms}ms!")
    print(f"  - Active Fleet: {dados.get('total_motos')} bikes")
    print(f"  - Active Contracts: {dados.get('contratos_ativos')}")
    print(f"  - Due Today Items: {dados.get('due_today', {}).get('count')}")
    return elapsed_ms

if __name__ == '__main__':
    run_warmup()
