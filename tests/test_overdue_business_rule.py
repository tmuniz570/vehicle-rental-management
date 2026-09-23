import os
import sys
import json
from datetime import datetime, timedelta
import pytz

# Set root dir in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import app, get_london_now
from database import db, Motorcycle, Client, Contract, FinancialTransaction, User, ContractType, TransactionType, MotoStatus, TransactionStatus, ContractStatus

def test_overdue_business_rule():
    print("=== TESTING OVERDUE BUSINESS RULES (TODAY VS YESTERDAY) ===")
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        client = app.test_client()
        
        # 1. Setup admin user for authentication
        admin_user = User.query.filter_by(email="admin_overdue_test@ffmotors.co.uk").first()
        if not admin_user:
            admin_user = User(
                nome="Admin Overdue Test",
                email="admin_overdue_test@ffmotors.co.uk",
                is_admin=True,
                perm_alugueis=True,
                perm_claims=True,
                ativo=True
            )
            admin_user.set_password("admin123")
            db.session.add(admin_user)
            db.session.commit()
            
        # Login with Flask-Login session keys
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin_user.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

        # 2. Setup mock customer and motorbike
        test_client = Client.query.filter_by(email="client_overdue@ffmotors.co.uk").first()
        if not test_client:
            test_client = Client(
                nome="Test Overdue Customer",
                email="client_overdue@ffmotors.co.uk",
                telefone="07999888777",
                endereco="10 Birmingham Road, B5 5TH"
            )
            db.session.add(test_client)
            db.session.commit()

        test_moto = db.session.get(Motorcycle, "OV26TEST")
        if not test_moto:
            test_moto = Motorcycle(
                placa="OV26TEST",
                modelo="Honda Vision 110",
                cor="Red",
                milhagem_atual=1000,
                status=MotoStatus.RENTED.value
            )
            db.session.add(test_moto)
            db.session.commit()

        # 3. Setup test contract
        test_contract = Contract.query.filter_by(placa="OV26TEST").first()
        if not test_contract:
            test_contract = Contract(
                id_cliente=test_client.id,
                placa=test_moto.placa,
                tipo_contrato=ContractType.RENT.value,
                valor_aluguel_semanal=80.0,
                valor_deposito=300.0,
                status=ContractStatus.ACTIVE.value,
                dia_pagamento_semanal=2
            )
            db.session.add(test_contract)
            db.session.commit()

        # 4. Clean up any existing test transactions for this contract
        FinancialTransaction.query.filter_by(id_contrato=test_contract.id).delete()
        db.session.commit()

        london_now = get_london_now()
        hoje_zero = london_now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        ontem = hoje_zero - timedelta(days=1)
        hoje_madrugada = hoje_zero + timedelta(hours=1) # 01:00 AM (APScheduler simulation)
        hoje_tarde = hoje_zero + timedelta(hours=15, minutes=30) # 15:30 PM
        amanha = hoje_zero + timedelta(days=1)

        # Create transactions:
        # T1: Due YESTERDAY, Pending -> MUST BE OVERDUE
        tx_ontem_pending = FinancialTransaction(
            id_contrato=test_contract.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=ontem,
            valor=80.0,
            status=TransactionStatus.PENDING.value
        )
        db.session.add(tx_ontem_pending)

        # T2: Due TODAY at 01:00 AM, Pending -> MUST NOT BE OVERDUE TODAY! (Only due tomorrow if unpaid)
        tx_hoje_madrugada = FinancialTransaction(
            id_contrato=test_contract.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=hoje_madrugada,
            valor=80.0,
            status=TransactionStatus.PENDING.value
        )
        db.session.add(tx_hoje_madrugada)

        # T3: Due TODAY at 15:30, Pending -> MUST NOT BE OVERDUE TODAY!
        tx_hoje_tarde = FinancialTransaction(
            id_contrato=test_contract.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=hoje_tarde,
            valor=80.0,
            status=TransactionStatus.PENDING.value
        )
        db.session.add(tx_hoje_tarde)

        # T4: Due TODAY, Paid -> MUST NOT BE OVERDUE
        tx_hoje_paid = FinancialTransaction(
            id_contrato=test_contract.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=hoje_zero,
            valor=80.0,
            status=TransactionStatus.PAID.value
        )
        db.session.add(tx_hoje_paid)

        # T5: Due TOMORROW, Pending -> MUST NOT BE OVERDUE
        tx_amanha = FinancialTransaction(
            id_contrato=test_contract.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=amanha,
            valor=80.0,
            status=TransactionStatus.PENDING.value
        )
        db.session.add(tx_amanha)

        db.session.commit()

        # --- TEST 1: Check /relatorios/vencidos ---
        res_rel = client.get('/relatorios/vencidos')
        assert res_rel.status_code == 200, f"Expected 200, got {res_rel.status_code}"
        html_content = res_rel.get_data(as_text=True)

        # T1 (Due yesterday) must appear in the report
        ontem_str = ontem.strftime('%d/%m/%Y')
        hoje_str = hoje_zero.strftime('%d/%m/%Y')
        assert "OV26TEST" in html_content, "OV26TEST must be in overdue report"
        assert ontem_str in html_content, f"Yesterday date {ontem_str} must appear in overdue report"
        print("  -> /relatorios/vencidos passed: Report renders correctly.")
        
        # --- TEST 2: Check /api/financeiro?status=overdue ---
        res_api_overdue = client.get('/api/financeiro?status=overdue&limit=100')
        assert res_api_overdue.status_code == 200
        data_overdue = res_api_overdue.get_json()
        overdue_ids = [item['id'] for item in data_overdue.get('itens', [])]

        assert tx_ontem_pending.id in overdue_ids, f"T1 (Due yesterday ID {tx_ontem_pending.id}) SHOULD be in overdue list"
        assert tx_hoje_madrugada.id not in overdue_ids, f"T2 (Due today 01:00 ID {tx_hoje_madrugada.id}) MUST NOT be in overdue list today!"
        assert tx_hoje_tarde.id not in overdue_ids, f"T3 (Due today 15:30 ID {tx_hoje_tarde.id}) MUST NOT be in overdue list today!"
        assert tx_hoje_paid.id not in overdue_ids, f"T4 (Paid ID {tx_hoje_paid.id}) MUST NOT be in overdue list"
        assert tx_amanha.id not in overdue_ids, f"T5 (Due tomorrow ID {tx_amanha.id}) MUST NOT be in overdue list"

        print("  -> /api/financeiro?status=overdue passed: Only yesterday's pending charges are overdue.")

        # --- TEST 3: Check /api/financeiro?status=pending (Pending list) ---
        res_api_pending = client.get('/api/financeiro?status=pending&limit=100')
        assert res_api_pending.status_code == 200
        data_pending = res_api_pending.get_json()
        pending_ids = [item['id'] for item in data_pending.get('itens', [])]

        assert tx_hoje_madrugada.id in pending_ids, "T2 must be in pending list"
        assert tx_hoje_tarde.id in pending_ids, "T3 must be in pending list"
        print("  -> /api/financeiro?status=pending passed: Today's charges correctly show as PENDING.")

        # --- TEST 4: Check /api/dashboard ---
        res_dash = client.get('/api/dashboard')
        assert res_dash.status_code == 200, f"Expected 200, got {res_dash.status_code}"
        dash_data = res_dash.get_json()
        
        # Verify dashboard overdue query matches exactly
        inicio_hoje = get_london_now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        expected_vencidas_count = FinancialTransaction.query.filter(
            FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
            FinancialTransaction.data_vencimento < inicio_hoje
        ).count()

        assert dash_data['total_vencidos'] == expected_vencidas_count, (
            f"Dashboard total_vencidos ({dash_data['total_vencidos']}) does not match DB query ({expected_vencidas_count})"
        )
        print(f"  -> Dashboard statistics passed: total_vencidos = {dash_data['total_vencidos']}.")

        # Cleanup
        FinancialTransaction.query.filter_by(id_contrato=test_contract.id).delete()
        db.session.delete(test_contract)
        db.session.delete(test_moto)
        db.session.delete(test_client)
        db.session.delete(admin_user)
        db.session.commit()
        print("=== ALL OVERDUE BUSINESS RULE TESTS PASSED SUCCESSFULLY! ===")

if __name__ == '__main__':
    test_overdue_business_rule()
