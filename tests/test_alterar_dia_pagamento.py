import os
import sys
import time
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import app, db, Contract, Client, Motorcycle, FinancialTransaction, User, ContractStatus, ContractType, TransactionStatus, TransactionType, MotoStatus

def test_alterar_dia_pagamento():
    print("=== STARTING ALTERAR DIA PAGAMENTO TEST ===")
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        client = app.test_client()

        # Admin user
        admin_user = User.query.filter_by(email="admin@ffmotors.co.uk").first()
        if not admin_user:
            admin_user = User(
                nome="Admin Test",
                email="admin@ffmotors.co.uk",
                is_admin=True,
                perm_alugueis=True,
                perm_claims=True,
                ativo=True
            )
            admin_user.set_password("admin123")
            db.session.add(admin_user)
            db.session.commit()

        # Test client & motorcycle
        test_client_obj = Client.query.first()
        if not test_client_obj:
            test_client_obj = Client(nome="Test Client Due Day", telefone="07111222333")
            db.session.add(test_client_obj)
            db.session.commit()

        test_moto = Motorcycle.query.first()
        if not test_moto:
            test_moto = Motorcycle(placa="DUE26DAY", modelo="Honda PCX", status=MotoStatus.AVAILABLE.value)
            db.session.add(test_moto)
            db.session.commit()

        # 1. Create an active Rental contract with due day = 0 (Monday)
        contract = Contract(
            id_cliente=test_client_obj.id,
            placa=test_moto.placa,
            tipo_contrato=ContractType.RENT.value,
            status=ContractStatus.ACTIVE.value,
            valor_aluguel_semanal=120.0,
            dia_pagamento_semanal=0 # Monday
        )
        db.session.add(contract)
        db.session.commit()

        # Add a pending rent transaction due on a Monday
        base_monday = datetime(2026, 9, 28, 0, 0, 0) # 2026-09-28 is a Monday (weekday=0)
        assert base_monday.weekday() == 0

        pending_tx = FinancialTransaction(
            id_contrato=contract.id,
            tipo=TransactionType.RENT.value,
            valor=120.0,
            data_vencimento=base_monday,
            status=TransactionStatus.PENDING.value
        )
        db.session.add(pending_tx)
        db.session.commit()

        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin_user.id)
            sess['_fresh'] = True
            sess['last_activity'] = time.time()

        # Test 1: Change to Friday (4) with ajustar_pendentes=True
        res = client.put(f"/api/contratos/{contract.id}/dia-pagamento", json={
            'dia_pagamento_semanal': 4,
            'ajustar_pendentes': True
        })
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data.decode()}"
        data = res.get_json()
        assert data['dia_pagamento_semanal'] == 4
        assert data['dia_nome'] == 'Friday'
        assert data['cobrancas_ajustadas'] == 1

        db.session.refresh(contract)
        db.session.refresh(pending_tx)
        assert contract.dia_pagamento_semanal == 4
        assert pending_tx.data_vencimento.weekday() == 4
        print("✓ Verified: Contract due day updated to Friday (4) and pending transaction shifted to Friday")

        # Test 2: Try changing non-active contract (e.g. Cancelled)
        contract.status = ContractStatus.CANCELLED.value
        db.session.commit()

        res_inactive = client.put(f"/api/contratos/{contract.id}/dia-pagamento", json={
            'dia_pagamento_semanal': 2
        })
        assert res_inactive.status_code == 400
        print("✓ Verified: Non-active contract correctly rejected with 400")

        # Test 3: Try changing non-rental contract (e.g. Sale)
        contract.status = ContractStatus.ACTIVE.value
        contract.tipo_contrato = 'Sale'
        db.session.commit()

        res_sale = client.put(f"/api/contratos/{contract.id}/dia-pagamento", json={
            'dia_pagamento_semanal': 2
        })
        assert res_sale.status_code == 400
        print("✓ Verified: Non-rental (Sale) contract correctly rejected with 400")

        # Test 4: Validation on invalid day (<0 or >6)
        contract.tipo_contrato = ContractType.RENT.value
        db.session.commit()

        res_invalid = client.put(f"/api/contratos/{contract.id}/dia-pagamento", json={
            'dia_pagamento_semanal': 99
        })
        assert res_invalid.status_code == 400
        print("✓ Verified: Invalid day number correctly rejected with 400")

        # Cleanup
        db.session.delete(pending_tx)
        db.session.delete(contract)
        db.session.commit()
        print("✓ Cleaned up test contract cleanly")

    print("=== ALL TESTS PASSED SUCCESSFULLY! ===")

if __name__ == '__main__':
    test_alterar_dia_pagamento()
