import os
import sys
import unittest
from datetime import datetime, timedelta

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from database import User, Client, Motorcycle, Contract, ContractType, ContractStatus, FinancialTransaction, TransactionType, TransactionStatus, MotoStatus

class TestSaleLifecycleSync(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

        # Disable CSRF for API mutation testing
        self._orig_csrf = app.config.get('WTF_CSRF_ENABLED')
        self._orig_testing = app.config.get('TESTING')
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['TESTING'] = True

        # Authenticate as Admin user
        admin = User.query.filter_by(role='Admin').first() or User.query.first()
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

    def tearDown(self):
        if self._orig_csrf is not None:
            app.config['WTF_CSRF_ENABLED'] = self._orig_csrf
        else:
            app.config.pop('WTF_CSRF_ENABLED', None)
        if self._orig_testing is not None:
            app.config['TESTING'] = self._orig_testing
        else:
            app.config.pop('TESTING', None)
        self.app_context.pop()

    def test_sale_contract_lifecycle_auto_complete_and_reopen(self):
        """
        Valida que contratos de venda transitam dinamicamente:
        1. Conclui para Completed quando todas as cobranças são pagas.
        2. Reabre para Active se uma nova cobrança for adicionada.
        3. Conclui para Completed quando a nova cobrança é quitada.
        4. Reabre para Active se um pagamento for revertido para Pendente.
        5. Conclui para Completed quando o pagamento é quitado novamente.
        6. Reabre para Active se uma cobrança avulsa for adicionada e volta para Completed se for excluída.
        """
        client = self.client

        # Setup: Cliente e Moto de teste (limpeza prévia se houver)
        from database import AuditLog
        old_client = Client.query.filter_by(nome="Sale Lifecycle Test Client").first()
        if old_client:
            old_cids = [c.id for c in Contract.query.filter_by(id_cliente=old_client.id).all()]
            if old_cids:
                AuditLog.query.filter(AuditLog.entidade == 'contratos', AuditLog.entidade_id.in_([str(cid) for cid in old_cids])).delete(synchronize_session=False)
                FinancialTransaction.query.filter(FinancialTransaction.id_contrato.in_(old_cids)).delete(synchronize_session=False)
                Contract.query.filter(Contract.id.in_(old_cids)).delete(synchronize_session=False)
            db.session.delete(old_client)
            db.session.commit()

        placa_teste = "SL99XYZ"
        old_moto = db.session.get(Motorcycle, placa_teste)
        if old_moto:
            db.session.delete(old_moto)
            db.session.commit()

        cliente = Client(nome="Sale Lifecycle Test Client", telefone="07999888777", email="sale_sync_test@ffmotors.co.uk")
        db.session.add(cliente)
        moto = Motorcycle(placa=placa_teste, modelo="Honda PCX 125", status=MotoStatus.AVAILABLE.value)
        db.session.add(moto)
        db.session.commit()

        # Cria contrato de venda parcelada (Sale_Installment)
        contrato = Contract(
            id_cliente=cliente.id,
            placa=moto.placa,
            tipo_contrato=ContractType.SALE_INSTALLMENT.value,
            status=ContractStatus.ATIVO.value,
            valor_total_venda=2000.0,
            valor_entrada=500.0,
            saldo_devedor=1500.0,
            data_retirada=datetime.now()
        )
        db.session.add(contrato)
        db.session.commit()

        # Adiciona 2 parcelas pendentes
        t1 = FinancialTransaction(
            id_contrato=contrato.id,
            tipo=TransactionType.SALE_INSTALLMENT.value,
            valor=1000.0,
            status=TransactionStatus.PENDING.value,
            data_vencimento=datetime.now() + timedelta(days=7)
        )
        t2 = FinancialTransaction(
            id_contrato=contrato.id,
            tipo=TransactionType.SALE_INSTALLMENT.value,
            valor=1000.0,
            status=TransactionStatus.PENDING.value,
            data_vencimento=datetime.now() + timedelta(days=14)
        )
        db.session.add_all([t1, t2])
        db.session.commit()

        # Contrato deve iniciar como Active
        self.assertEqual(contrato.status, ContractStatus.ATIVO.value)

        # Passo 1: Paga a primeira parcela -> Contrato continua Active (ainda tem t2 pendente)
        resp1 = client.post(f'/api/financeiro/pagar/{t1.id}', json={'forma_pagamento': 'Bank Transfer'})
        self.assertEqual(resp1.status_code, 200)
        db.session.refresh(contrato)
        self.assertEqual(contrato.status, ContractStatus.ATIVO.value)

        # Passo 2: Paga a segunda parcela -> Todas quitadas! Contrato deve ir para Completed
        resp2 = client.post(f'/api/financeiro/pagar/{t2.id}', json={'forma_pagamento': 'Bank Transfer'})
        self.assertEqual(resp2.status_code, 200)
        db.session.refresh(contrato)
        self.assertEqual(contrato.status, ContractStatus.COMPLETED.value)
        print("\n✓ Passo 1 & 2: Contrato completou automaticamente após quitar todas as cobranças.")

        # Passo 3: Inclui uma nova cobrança manual via /api/contratos/<id>/cobrancas -> Deve voltar para Active!
        resp3 = client.post(f'/api/contratos/{contrato.id}/cobrancas', json={
            'tipo': 'fine',
            'valor': 150.0,
            'data_vencimento': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
        })
        self.assertEqual(resp3.status_code, 201)
        db.session.refresh(contrato)
        self.assertEqual(contrato.status, ContractStatus.ATIVO.value, "Contrato de venda DEVE reabrir para Active ao incluir nova cobrança pendente!")
        print("✓ Passo 3: Contrato reabriu para Active com sucesso após adicionar nova cobrança.")

        # Obtém o ID da nova cobrança
        t3 = FinancialTransaction.query.filter_by(id_contrato=contrato.id, tipo=TransactionType.FINE.value).first()
        self.assertIsNotNone(t3)

        # Passo 4: Paga a cobrança adicional (t3) -> Contrato deve voltar para Completed!
        resp4 = client.post(f'/api/financeiro/pagar/{t3.id}', json={'forma_pagamento': 'Card'})
        self.assertEqual(resp4.status_code, 200)
        db.session.refresh(contrato)
        self.assertEqual(contrato.status, ContractStatus.COMPLETED.value, "Contrato de venda DEVE voltar para Completed após quitar a nova cobrança!")
        print("✓ Passo 4: Contrato voltou para Completed após pagar a nova cobrança.")

        # Passo 5: Reverte o pagamento de t2 de volta para Pendente -> Contrato DEVE reabrir para Active!
        resp5 = client.post(f'/api/financeiro/reverter/{t2.id}')
        self.assertEqual(resp5.status_code, 200)
        db.session.refresh(contrato)
        self.assertEqual(contrato.status, ContractStatus.ATIVO.value, "Contrato de venda DEVE voltar para Active ao reverter um pagamento para pendente!")
        print("✓ Passo 5: Contrato reabriu para Active ao reverter pagamento para pendente.")

        # Passo 6: Paga t2 novamente -> Contrato DEVE voltar para Completed!
        resp6 = client.post(f'/api/financeiro/pagar/{t2.id}', json={'forma_pagamento': 'Bank Transfer'})
        self.assertEqual(resp6.status_code, 200)
        db.session.refresh(contrato)
        self.assertEqual(contrato.status, ContractStatus.COMPLETED.value, "Contrato de venda DEVE voltar para Completed após pagar novamente!")
        print("✓ Passo 6: Contrato voltou para Completed após re-quitar a pendência.")

        # Passo 7: Adiciona cobrança avulsa via /api/financeiro/nova-cobranca -> Reabre para Active
        resp7 = client.post('/api/financeiro/nova-cobranca', json={
            'id_contrato': contrato.id,
            'tipo': 'admin_fee',
            'valor': 50.0,
            'data_vencimento': (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
            'nota': 'Taxa administrativa teste'
        })
        self.assertEqual(resp7.status_code, 201)
        t4_id = resp7.get_json()['id']
        db.session.refresh(contrato)
        self.assertEqual(contrato.status, ContractStatus.ATIVO.value, "Contrato de venda DEVE reabrir para Active com cobrança avulsa!")

        # Passo 8: Exclui a cobrança pendente (t4) -> Contrato DEVE voltar para Completed!
        resp8 = client.delete(f'/api/financeiro/{t4_id}')
        self.assertEqual(resp8.status_code, 200)
        db.session.refresh(contrato)
        self.assertEqual(contrato.status, ContractStatus.COMPLETED.value, "Contrato de venda DEVE voltar para Completed após excluir a cobrança pendente!")
        print("✓ Passo 7 & 8: Ciclo completo com cobrança avulsa e exclusão validado.")

        # Limpeza
        contract_ids = [c.id for c in Contract.query.filter_by(id_cliente=cliente.id).all()]
        if contract_ids:
            AuditLog.query.filter(AuditLog.entidade == 'contratos', AuditLog.entidade_id.in_([str(cid) for cid in contract_ids])).delete(synchronize_session=False)
            FinancialTransaction.query.filter(FinancialTransaction.id_contrato.in_(contract_ids)).delete(synchronize_session=False)
            Contract.query.filter(Contract.id.in_(contract_ids)).delete(synchronize_session=False)
            db.session.commit()
        db.session.delete(moto)
        db.session.delete(cliente)
        db.session.commit()

if __name__ == '__main__':
    unittest.main()
