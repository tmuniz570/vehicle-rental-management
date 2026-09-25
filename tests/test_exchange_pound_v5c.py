import os
import sys
import json
from datetime import datetime, timedelta

# Set root dir in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import app
from database import db, Motorcycle, User, MotoStatus, FinancialTransaction, MotorcycleV5C, Contract, Client, init_db

def run_tests():
    print("=== STARTING EXCHANGE, POUND, AND V5C ALERT TESTS ===")
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        init_db(app)
        client = app.test_client()

        # 0. Setup admin user
        admin_user = User.query.filter_by(email="admin@ffmotors.co.uk").first()
        if not admin_user:
            admin_user = User(
                nome="Admin Test",
                email="admin@ffmotors.co.uk",
                is_admin=True,
                perm_alugueis=True,
                perm_financeiro=True,
                perm_claims=True,
                ativo=True
            )
            admin_user.set_password("admin123")
            db.session.add(admin_user)
            db.session.commit()

        # Authenticate admin session
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin_user.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

        # -------------------------------------------------------------
        # 1. TEST POUND STATUS & MOT/TAX EXEMPTION
        # -------------------------------------------------------------
        print("\n--- 1. Testing Pound Status & MOT/TAX Alert Exemption ---")
        placa_pound = "POUND_TEST_01"
        # Clean up any existing
        Motorcycle.query.filter_by(placa=placa_pound).delete()
        db.session.commit()

        yesterday_date = (datetime.now().date() - timedelta(days=5))
        
        # Create bike with status = Pound and EXPIRED MOT & TAX
        moto_pound = Motorcycle(
            placa=placa_pound,
            modelo="Honda Vision 110 Pound Test",
            cor="Grey",
            status=MotoStatus.POUND.value,
            milhagem_atual=12000,
            vencimento_mot=yesterday_date,
            vencimento_tax=yesterday_date,
            tax_sorn=False
        )
        db.session.add(moto_pound)
        db.session.commit()

        # Query dashboard API
        dash_res = client.get('/api/dashboard')
        assert dash_res.status_code == 200, f"Dashboard failed: {dash_res.data.decode()}"
        dash_data = json.loads(dash_res.data.decode())

        # Assert Pound bike is NOT in mot_vencendo, mot_vencidos, tax_vencendo, tax_vencidos
        alertas = dash_data.get('alertas', {})
        mot_vencidos = alertas.get('mot_vencidos', [])
        mot_vencendo = alertas.get('mot_vencendo', [])
        tax_vencidos = alertas.get('tax_vencidos', [])
        tax_vencendo = alertas.get('tax_vencendo', [])

        all_mot_plates = [m.get('placa') for m in mot_vencidos + mot_vencendo]
        all_tax_plates = [m.get('placa') for m in tax_vencidos + tax_vencendo]

        assert placa_pound not in all_mot_plates, f"Plate {placa_pound} should NOT be in MOT alerts when in Pound status!"
        assert placa_pound not in all_tax_plates, f"Plate {placa_pound} should NOT be in Tax alerts when in Pound status!"
        print(f"✓ Verified: {placa_pound} in Pound status is strictly exempt from MOT & Tax alerts.")

        # Assert motos_pound in dashboard
        motos_pound_count = dash_data.get('motos_pound', 0)
        assert motos_pound_count >= 1, f"Expected motos_pound >= 1, got {motos_pound_count}"
        print(f"✓ Verified: motos_pound count in dashboard is {motos_pound_count}.")

        # -------------------------------------------------------------
        # 2. TEST MISSING V5C ALERT IN DASHBOARD & LISTAR MOTOS
        # -------------------------------------------------------------
        print("\n--- 2. Testing Missing V5C Alert ---")
        motos_sem_v5c_count = dash_data.get('motos_sem_v5c_count', 0)
        motos_sem_v5c_list = dash_data.get('motos_sem_v5c', [])
        
        sem_v5c_plates = [m.get('placa') for m in motos_sem_v5c_list]
        assert placa_pound in sem_v5c_plates, f"Expected {placa_pound} to be in missing V5C list, got {sem_v5c_plates}"
        print(f"✓ Verified: {placa_pound} is correctly detected as missing V5C logbook (total missing: {motos_sem_v5c_count}).")

        # Query /api/motos?v5c=missing
        res_v5c_filter = client.get('/api/motos?v5c=missing')
        assert res_v5c_filter.status_code == 200
        v5c_filter_data = json.loads(res_v5c_filter.data.decode())
        filter_plates = [item['placa'] for item in v5c_filter_data.get('itens', [])]
        assert placa_pound in filter_plates, f"Expected {placa_pound} in /api/motos?v5c=missing"
        print(f"✓ Verified: /api/motos?v5c=missing returns {placa_pound}.")

        # Query /api/motos?status=Pound
        res_pound_filter = client.get('/api/motos?status=Pound')
        assert res_pound_filter.status_code == 200
        pound_filter_data = json.loads(res_pound_filter.data.decode())
        pound_plates = [item['placa'] for item in pound_filter_data.get('itens', [])]
        assert placa_pound in pound_plates, f"Expected {placa_pound} in /api/motos?status=Pound"
        print(f"✓ Verified: /api/motos?status=Pound returns {placa_pound}.")

        # -------------------------------------------------------------
        # 3. TEST EXCHANGE PAYMENT METHOD
        # -------------------------------------------------------------
        print("\n--- 3. Testing Exchange Payment Method ---")
        # Ensure we have a contract
        contract = db.session.query(Contract).first()
        if not contract:
            c_client = Client(nome="Test Client", telefone="07000000000")
            db.session.add(c_client)
            db.session.flush()
            contract = Contract(
                id_cliente=c_client.id,
                placa=placa_pound,
                status='Active',
                tipo_contrato='Rent',
                data_retirada=datetime.now()
            )
            db.session.add(contract)
            db.session.commit()

        # Create a pending transaction
        pending_tx = FinancialTransaction(
            id_contrato=contract.id,
            tipo='Aluguel',
            valor=250.0,
            status='Pending',
            data_vencimento=datetime.now().date()
        )
        db.session.add(pending_tx)
        db.session.commit()

        # Pay with Exchange + Cash split AND a Payment Note
        test_note = "Trade-in Honda PCX 125 reg AB12CDE - approved by manager"
        pay_payload = {
            'metodos_pagamento': [
                {'forma': 'Exchange', 'valor': 200.0},
                {'forma': 'Cash', 'valor': 50.0}
            ],
            'nota': test_note
        }
        res_pay = client.post(f'/api/financeiro/pagar/{pending_tx.id}', json=pay_payload)
        assert res_pay.status_code == 200, f"Failed to pay transaction: {res_pay.data.decode()}"
        
        # Verify transaction saved in database
        db.session.refresh(pending_tx)
        assert pending_tx.status == 'Paid', f"Expected 'Paid', got {pending_tx.status}"
        assert 'Exchange (£200.00)' in pending_tx.forma_pagamento, f"Expected Exchange in forma_pagamento, got {pending_tx.forma_pagamento}"
        assert 'Cash (£50.00)' in pending_tx.forma_pagamento, f"Expected Cash in forma_pagamento, got {pending_tx.forma_pagamento}"
        assert pending_tx.nota == test_note, f"Expected note '{test_note}', got '{pending_tx.nota}'"
        print(f"✓ Verified: Split payment registered successfully with Exchange and Note: '{pending_tx.nota}'.")

        # Verify /api/financeiro returns the note (also testing search by note!)
        res_fin = client.get(f'/api/financeiro?search={pending_tx.id}')
        assert res_fin.status_code == 200
        fin_data = json.loads(res_fin.data.decode())
        tx_item = next((item for item in fin_data.get('itens', []) if item['id'] == pending_tx.id), None)
        assert tx_item is not None, "Transaction not found in /api/financeiro list"
        assert tx_item.get('nota') == test_note, f"Expected note in API item, got {tx_item.get('nota')}"
        print(f"✓ Verified: /api/financeiro correctly delivers payment note.")

        # Test revert clears note
        res_rev = client.post(f'/api/financeiro/{pending_tx.id}/reverter')
        assert res_rev.status_code == 200
        db.session.refresh(pending_tx)
        assert pending_tx.status == 'Pending'
        assert pending_tx.nota is None, f"Expected note to be cleared on revert, got {pending_tx.nota}"
        print(f"✓ Verified: Reverting payment cleanly resets note to None.")

        # Cleanup test data
        db.session.delete(pending_tx)
        Motorcycle.query.filter_by(placa=placa_pound).delete()
        db.session.commit()
        print("✓ Cleanup completed.")

    print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

if __name__ == '__main__':
    run_tests()
