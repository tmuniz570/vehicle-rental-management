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
    print("\n=== STARTING FINANCIAL STATEMENT IN CONTRACT DETAILS TEST ===")
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()

    with app.app_context():
        # Setup operator user
        admin = User.query.filter_by(email="extrato_admin@ffmotors.co.uk").first()
        if not admin:
            admin = User(email="extrato_admin@ffmotors.co.uk", nome="Extrato Admin", perm_alugueis=True, is_admin=True, ativo=True)
            admin.set_password("pass123")
            db.session.add(admin)
            db.session.commit()

        # Login
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

        # Setup customer and bike
        test_client = Client.query.filter_by(telefone="07111222333").first()
        if not test_client:
            test_client = Client(nome="Extrato Test Customer", telefone="07111222333", endereco="456 High St, Birmingham")
            db.session.add(test_client)
            db.session.commit()

        test_moto = Motorcycle.query.filter_by(placa="EXTRATO01").first()
        if not test_moto:
            test_moto = Motorcycle(placa="EXTRATO01", modelo="Honda PCX 125", cor="White", status=MotoStatus.RENTED.value, milhagem_atual=2500)
            db.session.add(test_moto)
            db.session.commit()

        # Setup Contract
        contrato = Contract.query.filter_by(placa="EXTRATO01", status=ContractStatus.ACTIVE.value).first()
        if not contrato:
            contrato = Contract(
                id_cliente=test_client.id,
                cliente_nome=test_client.nome,
                cliente_telefone=test_client.telefone,
                cliente_endereco=test_client.endereco,
                placa="EXTRATO01",
                moto_modelo="Honda PCX 125",
                moto_cor="White",
                tipo_contrato=ContractType.RENT.value,
                status=ContractStatus.ACTIVE.value,
                valor_aluguel_semanal=90.0,
                data_retirada=datetime.now()
            )
            db.session.add(contrato)
            db.session.commit()

        # Create test transactions:
        # 1. Overdue transaction
        tx_overdue = FinancialTransaction(
            id_contrato=contrato.id,
            tipo=TransactionType.RENT.value,
            valor=90.0,
            status=TransactionStatus.PENDING.value,
            data_vencimento=datetime.now() - timedelta(days=5)
        )
        # 2. Today pending transaction
        tx_pending = FinancialTransaction(
            id_contrato=contrato.id,
            tipo=TransactionType.RENT.value,
            valor=90.0,
            status=TransactionStatus.PENDING.value,
            data_vencimento=datetime.now()
        )
        # 3. Paid transaction with partial balance origin
        tx_parent = FinancialTransaction(
            id_contrato=contrato.id,
            tipo=TransactionType.RENT.value,
            valor=50.0,
            status=TransactionStatus.PAID.value,
            forma_pagamento='Card',
            data_vencimento=datetime.now() - timedelta(days=7),
            data_pagamento=datetime.now()
        )
        db.session.add_all([tx_overdue, tx_pending, tx_parent])
        db.session.commit()

        tx_child = FinancialTransaction(
            id_contrato=contrato.id,
            id_transacao_origem=tx_parent.id,
            tipo=TransactionType.RENT.value,
            valor=40.0,
            status=TransactionStatus.PENDING.value,
            data_vencimento=datetime.now() - timedelta(days=7)
        )
        db.session.add(tx_child)
        db.session.commit()

        # [TEST 1] Verify API /api/contratos/<id> returns all necessary fields
        print("[TEST 1] Verifying /api/contratos/<id> serialization...")
        res = client.get(f'/api/contratos/{contrato.id}')
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.get_json()
        assert 'transacoes' in data, "Response missing 'transacoes'"
        
        txs = {t['id']: t for t in data['transacoes']}
        assert tx_overdue.id in txs, "tx_overdue not in serialized transactions"
        assert tx_child.id in txs, "tx_child not in serialized transactions"
        
        # Verify id_transacao_origem is populated
        assert txs[tx_child.id]['id_transacao_origem'] == tx_parent.id, f"Expected {tx_parent.id}, got {txs[tx_child.id]['id_transacao_origem']}"
        print(f"-> Child transaction #{tx_child.id} correctly has id_transacao_origem: #{tx_parent.id}")

        # [TEST 2] Test WhatsApp Reminder API /api/financeiro/<id>/lembrete
        print("[TEST 2] Testing reminder logging on transaction...")
        res_remind = client.post(f'/api/financeiro/{tx_overdue.id}/lembrete')
        assert res_remind.status_code == 200, f"Reminder failed with {res_remind.status_code}"
        remind_data = res_remind.get_json()
        assert remind_data.get('sucesso') is True, "Reminder response missing sucesso=True"
        assert remind_data.get('ultimo_lembrete') is not None, "Reminder timestamp missing"
        assert remind_data.get('ultimo_lembrete_por') == "Extrato Admin", f"Expected Extrato Admin, got {remind_data.get('ultimo_lembrete_por')}"
        print(f"-> Reminder logged: timestamp={remind_data['ultimo_lembrete']}, staff={remind_data['ultimo_lembrete_por']}")

        # [TEST 3] Verify that /api/contratos/<id> now returns updated ultimo_lembrete
        print("[TEST 3] Verifying updated reminder data on /api/contratos/<id>...")
        res2 = client.get(f'/api/contratos/{contrato.id}')
        data2 = res2.get_json()
        txs2 = {t['id']: t for t in data2['transacoes']}
        assert txs2[tx_overdue.id]['ultimo_lembrete'] is not None, "ultimo_lembrete was not persisted"
        assert txs2[tx_overdue.id]['ultimo_lembrete_por'] == "Extrato Admin", "ultimo_lembrete_por was not persisted"
        print("-> Transaction in contract details successfully reflects reminder metadata.")

        print("\n=== ALL FINANCIAL STATEMENT CONTRACT DETAILS TESTS PASSED! ===")

if __name__ == '__main__':
    run_tests()
