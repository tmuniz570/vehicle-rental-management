import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import datetime, timedelta

from app import app
from database import (
    db, Motorcycle, Client, Contract, FinancialTransaction, User,
    ContractType, TransactionType, MotoStatus, TransactionStatus, ContractStatus
)

def run_tests():
    print("\n=== STARTING SPLIT & PARTIAL PAYMENTS TEST ===")
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()

    with app.app_context():
        # Setup test operator user
        admin = User.query.filter_by(email="split_admin@ffmotors.co.uk").first()
        if not admin:
            admin = User(email="split_admin@ffmotors.co.uk", nome="Split Admin", perm_alugueis=True, is_admin=True, ativo=True)
            admin.set_password("pass123")
            db.session.add(admin)
            db.session.commit()

        # Login
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

        # Setup test client and bike
        test_client = Client.query.filter_by(telefone="07999888777").first()
        if not test_client:
            test_client = Client(nome="Split Test Customer", telefone="07999888777", endereco="123 High St, Birmingham")
            db.session.add(test_client)
            db.session.commit()

        test_moto = Motorcycle.query.filter_by(placa="SPLIT01").first()
        if not test_moto:
            test_moto = Motorcycle(placa="SPLIT01", modelo="Honda PCX 125", cor="White", status=MotoStatus.AVAILABLE.value)
            db.session.add(test_moto)
            db.session.commit()

        # Create Sale_Full Contract with £2,500.00
        hoje = datetime.now()
        ct = Contract(
            id_cliente=test_client.id,
            placa=test_moto.placa,
            tipo_contrato=ContractType.SALE_FULL.value,
            data_retirada=hoje,
            valor_venda_veiculo=2500.00,
            valor_total_venda=2500.00,
            status=ContractStatus.ATIVO.value
        )
        db.session.add(ct)
        db.session.commit()

        tx_sale = FinancialTransaction(
            id_contrato=ct.id,
            tipo=TransactionType.SALE_FULL.value,
            data_vencimento=hoje,
            valor=2500.00,
            status=TransactionStatus.PENDING.value
        )
        db.session.add(tx_sale)
        db.session.commit()

        print(f"\n[TEST 1] Validation: Exceeding amount due & zero amount...")
        # Try paying £3,000 (exceeds £2,500)
        res_exceed = client.post(f'/api/financeiro/pagar/{tx_sale.id}', json={
            'metodos_pagamento': [
                {'forma': 'Cash', 'valor': 3000.00}
            ]
        })
        assert res_exceed.status_code == 400, f"Got status {res_exceed.status_code}: {res_exceed.get_data(as_text=True)}"
        print("res_exceed json:", res_exceed.get_json())
        assert 'cannot exceed' in res_exceed.get_json()['error']
        print("-> Rejected payment exceeding amount due.")

        # Try paying £0
        res_zero = client.post(f'/api/financeiro/pagar/{tx_sale.id}', json={
            'metodos_pagamento': [
                {'forma': 'Cash', 'valor': 0.00}
            ]
        })
        assert res_zero.status_code == 400
        print("-> Rejected £0 payment.")

        print(f"\n[TEST 2] Split Payment: Full quittance with 3 payment methods...")
        # Pay £2,500 split: £1,000 Card + £1,000 Cash + £500 Bank Transfer
        res_split = client.post(f'/api/financeiro/pagar/{tx_sale.id}', json={
            'metodos_pagamento': [
                {'forma': 'Card', 'valor': 1000.00},
                {'forma': 'Cash', 'valor': 1000.00},
                {'forma': 'Bank Transfer', 'valor': 500.00}
            ]
        })
        assert res_split.status_code == 200, f"Error: {res_split.get_data(as_text=True)}"
        data_res = res_split.get_json()
        assert not data_res['is_partial']
        assert data_res['saldo_restante'] == 0.0
        
        # Verify in DB
        db.session.refresh(tx_sale)
        assert tx_sale.status == TransactionStatus.PAID.value
        assert float(tx_sale.valor) == 2500.00
        assert "Card (£1000.00) + Cash (£1000.00) + Bank Transfer (£500.00)" in tx_sale.forma_pagamento
        assert tx_sale.detalhes_pagamento_json is not None
        print(f"-> Transaction #{tx_sale.id} marked as PAID via: {tx_sale.forma_pagamento}")

        # Check sale contract completed
        db.session.refresh(ct)
        assert ct.status == ContractStatus.COMPLETED.value
        print("-> Contract auto-completed upon full quittance.")

        print(f"\n[TEST 3] Revert Split Payment...")
        res_rev = client.post(f'/api/financeiro/{tx_sale.id}/reverter')
        assert res_rev.status_code == 200
        db.session.refresh(tx_sale)
        db.session.refresh(ct)
        assert tx_sale.status == TransactionStatus.PENDING.value
        assert tx_sale.forma_pagamento is None
        assert ct.status == ContractStatus.ATIVO.value
        print("-> Reverted successfully to PENDING and contract re-opened to ACTIVE.")

        print(f"\n[TEST 4] Partial Payment with Split Methods...")
        # Customer pays £1,000 of £2,500: £600 Cash + £400 Card
        res_part = client.post(f'/api/financeiro/pagar/{tx_sale.id}', json={
            'metodos_pagamento': [
                {'forma': 'Cash', 'valor': 600.00},
                {'forma': 'Card', 'valor': 400.00}
            ]
        })
        assert res_part.status_code == 200
        part_json = res_part.get_json()
        assert part_json['is_partial'] is True
        assert part_json['valor_pago'] == 1000.00
        assert part_json['saldo_restante'] == 1500.00
        child_id = part_json['id_restante']
        assert child_id is not None

        db.session.refresh(tx_sale)
        assert tx_sale.status == TransactionStatus.PAID.value
        assert float(tx_sale.valor) == 1000.00
        assert "Cash (£600.00) + Card (£400.00)" in tx_sale.forma_pagamento

        # Check remaining balance child transaction
        child_tx = db.session.get(FinancialTransaction, child_id)
        assert child_tx is not None
        assert child_tx.status == TransactionStatus.PENDING.value
        assert float(child_tx.valor) == 1500.00
        assert child_tx.id_transacao_origem == tx_sale.id
        print(f"-> Original tx #{tx_sale.id} paid £1000.00. Child balance tx #{child_tx.id} created pending for £1500.00.")

        # Contract must remain ACTIVE
        db.session.refresh(ct)
        assert ct.status == ContractStatus.ATIVO.value
        print("-> Contract properly stayed ACTIVE because child balance is pending.")

        print(f"\n[TEST 5] Revert Partial Payment & Auto-merge Child Balance...")
        res_rev_part = client.post(f'/api/financeiro/{tx_sale.id}/reverter')
        assert res_rev_part.status_code == 200
        db.session.refresh(tx_sale)
        assert tx_sale.status == TransactionStatus.PENDING.value
        assert float(tx_sale.valor) == 2500.00, f"Expected 2500.00 but got {tx_sale.valor}"
        # Child transaction must be deleted
        assert db.session.get(FinancialTransaction, child_id) is None
        print("-> Revert re-merged £1500.00 child balance back into tx #%d (total: £2500.00) and deleted child tx." % tx_sale.id)

        print(f"\n[TEST 6] Multi-step Partial Payments until Completion...")
        # Step 1: Pay £1,500 via Bank Transfer
        res_p1 = client.post(f'/api/financeiro/pagar/{tx_sale.id}', json={
            'metodos_pagamento': [{'forma': 'Bank Transfer', 'valor': 1500.00}]
        })
        assert res_p1.status_code == 200
        p1_child_id = res_p1.get_json()['id_restante']
        
        # Step 2: Pay the remaining £1,000 on child transaction: £500 Card + £500 Cash
        res_p2 = client.post(f'/api/financeiro/pagar/{p1_child_id}', json={
            'metodos_pagamento': [
                {'forma': 'Card', 'valor': 500.00},
                {'forma': 'Cash', 'valor': 500.00}
            ]
        })
        assert res_p2.status_code == 200
        assert res_p2.get_json()['is_partial'] is False
        assert res_p2.get_json()['saldo_restante'] == 0.0

        # Now all transactions on contract are paid!
        db.session.refresh(ct)
        assert ct.status == ContractStatus.COMPLETED.value
        print("-> Step 1 and Step 2 partial payments fully paid the vehicle sale. Contract auto-completed!")

        # Clean up test records
        FinancialTransaction.query.filter_by(id_contrato=ct.id).delete()
        db.session.delete(ct)
        db.session.commit()

        print("\n=== ALL SPLIT & PARTIAL PAYMENT TESTS PASSED SUCCESSFULLY! ===")

if __name__ == '__main__':
    run_tests()
