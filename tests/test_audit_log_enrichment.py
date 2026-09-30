import os
import sys
import unittest
from datetime import datetime, timedelta

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from database import Motorcycle, Contract, Client, User, FinancialTransaction, AuditLog, Claim, MotoStatus, ContractStatus, TransactionStatus

class TestAuditLogEnrichment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_testing = app.config.get('TESTING', False)
        cls._orig_csrf = app.config.get('WTF_CSRF_ENABLED', True)
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False

    @classmethod
    def tearDownClass(cls):
        app.config['TESTING'] = cls._orig_testing
        app.config['WTF_CSRF_ENABLED'] = cls._orig_csrf

    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

        # Authenticate session as Admin user with full permissions
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            admin = User.query.first()

        if admin:
            admin.is_admin = True
            admin.perm_alugueis = True
            admin.perm_claims = True
            db.session.commit()

        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

    def tearDown(self):
        self.app_context.pop()

    def test_moto_update_generates_detailed_log(self):
        # Create test motorcycle with unique plate
        test_plate = f"LOG{int(datetime.now().timestamp()) % 100000}"
        moto = Motorcycle(
            placa=test_plate,
            modelo="Honda PCX 125",
            cor="White",
            status=MotoStatus.AVAILABLE.value,
            milhagem_atual=10000
        )
        db.session.add(moto)
        db.session.commit()

        try:
            # Update mileage and color
            res = self.client.put(f'/api/motos/{test_plate}', json={
                'milhagem_atual': 12500,
                'cor': 'Matte Black'
            })
            self.assertEqual(res.status_code, 200)

            # Check AuditLog
            log = AuditLog.query.filter_by(acao='MOTO_UPDATE', entidade_id=test_plate).order_by(AuditLog.id.desc()).first()
            self.assertIsNotNone(log)
            self.assertIn("12500", log.descricao)
            self.assertIn("Matte Black", log.descricao)
            print(f"\n✓ MOTO_UPDATE log verified: {log.descricao}")
        finally:
            db.session.delete(moto)
            db.session.commit()

    def test_client_update_generates_detailed_log(self):
        # Create test client with unique email
        unique_email = f"audit_test_{int(datetime.now().timestamp())}_{os.getpid()}@example.com"
        test_client = Client(
            nome="Audit Test Client",
            telefone="07111222333",
            email=unique_email,
            endereco="10 High St, Birmingham"
        )
        db.session.add(test_client)
        db.session.commit()

        try:
            # Update phone and address
            res = self.client.put(f'/api/clientes/{test_client.id}', json={
                'telefone': '07999888777',
                'endereco': '20 New Rd, Birmingham'
            })
            self.assertEqual(res.status_code, 200)

            # Check AuditLog
            log = AuditLog.query.filter_by(acao='CLIENT_UPDATE', entidade_id=str(test_client.id)).order_by(AuditLog.id.desc()).first()
            self.assertIsNotNone(log)
            self.assertIn("07999888777", log.descricao)
            self.assertIn("Endereço", log.descricao)
            print(f"\n✓ CLIENT_UPDATE log verified: {log.descricao}")
        finally:
            db.session.delete(test_client)
            db.session.commit()

    def test_transaction_delete_and_reminder_logs(self):
        # Create dummy transaction
        ct = Contract.query.first()
        tx = FinancialTransaction(
            id_contrato=ct.id if ct else None,
            tipo='Fine',
            valor=120.00,
            status=TransactionStatus.PENDING.value,
            data_vencimento=datetime.now(),
            nota='Speeding Notice A45'
        )
        db.session.add(tx)
        db.session.commit()
        tx_id = tx.id

        # 1. Send WhatsApp reminder
        res_remind = self.client.post(f'/api/financeiro/{tx_id}/lembrete')
        self.assertEqual(res_remind.status_code, 200)
        log_remind = AuditLog.query.filter_by(acao='PAYMENT_REMINDER', entidade_id=str(tx_id)).order_by(AuditLog.id.desc()).first()
        self.assertIsNotNone(log_remind)
        self.assertIn("120.00", log_remind.descricao)
        print(f"\n✓ PAYMENT_REMINDER log verified: {log_remind.descricao}")

        # 2. Delete transaction
        res_del = self.client.delete(f'/api/financeiro/{tx_id}')
        self.assertEqual(res_del.status_code, 200)
        log_del = AuditLog.query.filter_by(acao='TRANSACTION_DELETE', entidade_id=str(tx_id)).order_by(AuditLog.id.desc()).first()
        self.assertIsNotNone(log_del)
        self.assertIn("120.00", log_del.descricao)
        self.assertIn("Fine", log_del.descricao)
        self.assertIn("Speeding Notice A45", log_del.descricao)
        print(f"\n✓ TRANSACTION_DELETE enriched log verified: {log_del.descricao}")

    def test_claim_update_generates_detailed_log(self):
        unique_claim_num = f"CLM-TEST-{int(datetime.now().timestamp()) % 100000}"
        claim = Claim(
            claim_number=unique_claim_num,
            empresa_parceira="McAms",
            cliente_nome="John Rider",
            placa="CL99TST",
            status="Em Aberto",
            status_storage="No Pátio",
            data_entrada_storage=datetime.now().date(),
            valor_diaria_storage=15.0
        )
        db.session.add(claim)
        db.session.commit()

        try:
            # Update claim: release from storage
            release_date_str = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
            res = self.client.put(f'/api/claims/{claim.id}', json={
                'data_liberacao_storage': release_date_str
            })
            self.assertEqual(res.status_code, 200)

            log = AuditLog.query.filter_by(acao='CLAIM_UPDATE', entidade_id=str(claim.id)).order_by(AuditLog.id.desc()).first()
            self.assertIsNotNone(log)
            self.assertIn("liberado do pátio", log.descricao)
            print(f"\n✓ CLAIM_UPDATE log verified: {log.descricao}")
        finally:
            db.session.delete(claim)
            db.session.commit()

    def test_cash_closing_print_generates_log(self):
        today_str = datetime.now().strftime('%Y-%m-%d')
        res = self.client.get(f'/financeiro/fechamento-caixa/print?data={today_str}')
        self.assertEqual(res.status_code, 200)

        log = AuditLog.query.filter_by(acao='CASH_CLOSING_PRINTED', entidade_id=today_str).order_by(AuditLog.id.desc()).first()
        self.assertIsNotNone(log)
        self.assertIn("fechamento de caixa diário", log.descricao)
        print(f"\n✓ CASH_CLOSING_PRINTED log verified: {log.descricao}")

    def test_audit_api_sorting_and_filtering(self):
        # 1. Test sorting by data_hora asc
        res_asc = self.client.get('/api/auditoria?sort_by=data_hora&sort_order=asc&limit=10')
        self.assertEqual(res_asc.status_code, 200)
        data_asc = res_asc.get_json()
        self.assertIn('itens', data_asc)
        self.assertIn('stats', data_asc)
        items_asc = data_asc['itens']
        if len(items_asc) >= 2:
            self.assertLessEqual(items_asc[0]['data_hora'], items_asc[-1]['data_hora'])

        # 2. Test sorting by data_hora desc
        res_desc = self.client.get('/api/auditoria?sort_by=data_hora&sort_order=desc&limit=10')
        self.assertEqual(res_desc.status_code, 200)
        data_desc = res_desc.get_json()
        items_desc = data_desc['itens']
        if len(items_desc) >= 2:
            self.assertGreaterEqual(items_desc[0]['data_hora'], items_desc[-1]['data_hora'])

        # 3. Test filtering by acao
        res_acao = self.client.get('/api/auditoria?acao=CASH_CLOSING_PRINTED')
        self.assertEqual(res_acao.status_code, 200)
        data_acao = res_acao.get_json()
        for it in data_acao['itens']:
            self.assertEqual(it['acao'], 'CASH_CLOSING_PRINTED')

        # 4. Test filtering by date range
        today_str = datetime.now().strftime('%Y-%m-%d')
        res_range = self.client.get(f'/api/auditoria?data_inicio={today_str}&data_fim={today_str}')
        self.assertEqual(res_range.status_code, 200)
        data_range = res_range.get_json()
        self.assertIsInstance(data_range['itens'], list)
        print(f"\n✓ /api/auditoria sorting & filtering verified with {data_range['total']} total items")

    def test_audit_api_csv_export(self):
        res = self.client.get('/api/auditoria/exportar-csv')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'text/csv')
        self.assertTrue('attachment;' in res.headers.get('Content-Disposition', ''))
        
        csv_text = res.data.decode('utf-8')
        self.assertTrue(csv_text.startswith('\ufeff'), "Should start with UTF-8 BOM for Excel")
        self.assertIn('Event ID,Date & Time (London),Staff / Operator,Action Key', csv_text)
        print("✓ /api/auditoria/exportar-csv generated valid CSV document")

if __name__ == '__main__':
    unittest.main()
