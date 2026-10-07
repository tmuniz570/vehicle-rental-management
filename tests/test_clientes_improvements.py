import unittest
import os
from datetime import datetime, timedelta
import pytz
from app import app
from database import db, User, Client, Contract, ContractStatus, ContractType, Motorcycle, FinancialTransaction, TransactionStatus, TransactionType

class ClientesImprovementsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Authenticate test session as admin
        admin = User.query.filter_by(email='tmuniz570@gmail.com').first()
        if not admin:
            admin = User(
                nome='Admin Test',
                email='tmuniz570@gmail.com',
                is_admin=True,
                role='admin',
                ativo=True,
                perm_alugueis=True,
                perm_financeiro=True,
                perm_claims=True
            )
            admin.set_password('Admin123!')
            db.session.add(admin)
            db.session.commit()

        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()
            sess['_csrf_token'] = 'test-token'

    def tearDown(self):
        self.app_context.pop()

    def test_api_clientes_kpis_and_rich_items(self):
        """Test that /api/clientes returns kpis and enriched items with active deal, debts and document statuses."""
        res = self.client.get('/api/clientes?limit=20')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn('kpis', data)
        kpis = data['kpis']
        self.assertIn('total', kpis)
        self.assertIn('active_hirers', kpis)
        self.assertIn('overdue_count', kpis)
        self.assertIn('overdue_amount', kpis)
        self.assertIn('missing_docs', kpis)
        self.assertGreaterEqual(kpis['total'], 1)

        self.assertIn('itens', data)
        items = data['itens']
        self.assertIsInstance(items, list)
        if len(items) > 0:
            first = items[0]
            self.assertIn('id', first)
            self.assertIn('nome', first)
            self.assertIn('telefone', first)
            self.assertIn('has_active_deal', first)
            self.assertIn('overdue_count', first)
            self.assertIn('overdue_amount', first)
            self.assertIn('status_dot', first)
            self.assertIn('status_dot_title', first)
            self.assertIn('has_licence_front', first)
            self.assertIn('has_licence_back', first)
            self.assertIn('has_proof_address', first)
            self.assertIn('missing_docs', first)

    def test_api_clientes_status_filters(self):
        """Test filtering clients by status: active, overdue, missing_docs, clean."""
        # 1. Filter active
        res_active = self.client.get('/api/clientes?status=active')
        self.assertEqual(res_active.status_code, 200)
        items_active = res_active.get_json().get('itens', [])
        for item in items_active:
            self.assertTrue(item['has_active_deal'])

        # 2. Filter overdue
        res_overdue = self.client.get('/api/clientes?status=overdue')
        self.assertEqual(res_overdue.status_code, 200)
        items_overdue = res_overdue.get_json().get('itens', [])
        for item in items_overdue:
            self.assertGreater(item['overdue_count'], 0)

        # 3. Filter missing docs
        res_missing = self.client.get('/api/clientes?status=missing_docs')
        self.assertEqual(res_missing.status_code, 200)
        items_missing = res_missing.get_json().get('itens', [])
        for item in items_missing:
            self.assertTrue(len(item['missing_docs']) > 0)

    def test_clientes_page_renders_html_properly(self):
        """Test that /clientes renders page with KPI cards and table."""
        res = self.client.get('/clientes')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('Customers KPI Summary Strip', html)
        self.assertIn('clientesKpisGrid', html)
        self.assertIn('kpiCard_all', html)
        self.assertIn('kpiCard_active', html)
        self.assertIn('kpiCard_overdue', html)
        self.assertIn('kpiCard_missing_docs', html)
        self.assertIn('lightboxModal', html)
        self.assertIn('clientesTable', html)
    def test_normalize_phone_canonical_uk_and_international(self):
        """Test that normalize_phone_canonical supports UK local, UK intl, and country codes (e.g. Brazil +55)."""
        from app import normalize_phone_canonical
        
        # UK numbers
        self.assertEqual(normalize_phone_canonical('07123 456789'), '447123456789')
        self.assertEqual(normalize_phone_canonical('07123456789'), '447123456789')
        self.assertEqual(normalize_phone_canonical('+44 7123 456789'), '447123456789')
        self.assertEqual(normalize_phone_canonical('+4407123456789'), '447123456789')
        self.assertEqual(normalize_phone_canonical('0044 7123 456789'), '447123456789')

        # Brazil (+55)
        self.assertEqual(normalize_phone_canonical('+55 11 98765-4321'), '5511987654321')
        self.assertEqual(normalize_phone_canonical('+5511987654321'), '5511987654321')
        self.assertEqual(normalize_phone_canonical('0055 11 987654321'), '5511987654321')

        # Other international (+351 Portugal, +1 USA)
        self.assertEqual(normalize_phone_canonical('+351 912 345 678'), '351912345678')
        self.assertEqual(normalize_phone_canonical('+1 (415) 555-2671'), '14155552671')

    def test_verificar_cliente_duplicado_api(self):
        """Test /api/clientes/verificar-duplicado endpoint for UK and international numbers."""
        unique_suffix = int(datetime.now().timestamp() * 1000) % 1000000

        # Create a customer with a Brazilian phone number
        br_phone = f"+55 11 9{unique_suffix:06d}"
        res_create = self.client.post('/api/clientes', data={
            'nome': 'Rodrigo Paulista',
            'telefone': br_phone,
            'endereco': 'Rua Augusta, Sao Paulo'
        }, headers={'X-CSRFToken': 'test-token'})
        self.assertEqual(res_create.status_code, 201)
        created_id = res_create.get_json()['id']

        try:
            # Check duplicate with slightly different format (e.g. without spaces)
            clean_br_phone = br_phone.replace(' ', '')
            res_dup = self.client.get(f'/api/clientes/verificar-duplicado?telefone={clean_br_phone}')
            self.assertEqual(res_dup.status_code, 200)
            data_dup = res_dup.get_json()
            self.assertTrue(data_dup['duplicate'])
            self.assertEqual(data_dup['matched_by'], 'phone')
            self.assertEqual(data_dup['client']['id'], created_id)

            # Check that creating another client with the same phone is blocked by POST /api/clientes
            res_block = self.client.post('/api/clientes', data={
                'nome': 'Rodrigo Clone',
                'telefone': clean_br_phone,
                'endereco': 'Another Address'
            }, headers={'X-CSRFToken': 'test-token'})
            self.assertEqual(res_block.status_code, 400)
            self.assertIn('already registered', res_block.get_json()['error'])

            # Check non-duplicate returns False
            res_non_dup = self.client.get('/api/clientes/verificar-duplicado?telefone=+551188888888')
            self.assertEqual(res_non_dup.status_code, 200)
            self.assertFalse(res_non_dup.get_json()['duplicate'])
        finally:
            c_obj = db.session.get(Client, created_id)
            if c_obj:
                db.session.delete(c_obj)
                db.session.commit()

    def test_merge_customers_api(self):
        """Test POST /api/clientes/merge endpoint: contracts transfer, document enrichment and source deletion."""
        from database import AuditLog
        
        # 1. Create source client (duplicate) with a contract
        uniq = int(datetime.now().timestamp() * 1000) % 10000000
        phone_src = f"078{uniq:08d}"
        phone_tgt = f"079{uniq:08d}"

        res_src = self.client.post('/api/clientes', data={
            'nome': 'Carlos Duplicado',
            'telefone': phone_src,
            'endereco': '10 Source Lane, Birmingham'
        }, headers={'X-CSRFToken': 'test-token'})
        self.assertEqual(res_src.status_code, 201)
        src_id = res_src.get_json()['id']

        # Add a fake contract to source client
        moto_test = Motorcycle.query.first()
        self.assertIsNotNone(moto_test)
        contrato_src = Contract(
            id_cliente=src_id,
            placa=moto_test.placa,
            tipo_contrato='Rent',
            status='Active',
            valor_aluguel_semanal=80.0
        )
        db.session.add(contrato_src)
        db.session.commit()
        contract_id = contrato_src.id

        # Set a document on source client
        src_client = db.session.get(Client, src_id)
        src_client.url_habilitacao = '/static/uploads/carlos_licence.jpg'
        src_client.notas_internas = 'Customer prefers card payments on Tuesdays'
        db.session.commit()

        # 2. Create target client (primary) without licence
        res_tgt = self.client.post('/api/clientes', data={
            'nome': 'Carlos Principal',
            'telefone': phone_tgt,
            'endereco': '20 Target Road, Birmingham'
        }, headers={'X-CSRFToken': 'test-token'})
        self.assertEqual(res_tgt.status_code, 201)
        tgt_id = res_tgt.get_json()['id']

        try:
            # 3. Test validation errors
            # 3a. Cannot merge into itself
            res_same = self.client.post('/api/clientes/merge', json={
                'source_id': src_id,
                'target_id': src_id
            }, headers={'X-CSRFToken': 'test-token'})
            self.assertEqual(res_same.status_code, 400)

            # 3b. Missing fields
            res_missing = self.client.post('/api/clientes/merge', json={
                'source_id': src_id
            }, headers={'X-CSRFToken': 'test-token'})
            self.assertEqual(res_missing.status_code, 400)

            # 4. Perform successful merge
            res_merge = self.client.post('/api/clientes/merge', json={
                'source_id': src_id,
                'target_id': tgt_id,
                'motivo': 'Duplicate registration cleaned up by operator'
            }, headers={'X-CSRFToken': 'test-token'})
            self.assertEqual(res_merge.status_code, 200)
            data_merge = res_merge.get_json()
            self.assertEqual(data_merge['transferred_contracts'], 1)
            self.assertEqual(data_merge['source_id'], src_id)
            self.assertEqual(data_merge['target_id'], tgt_id)

            # 5. Verify contract now points to target client
            updated_c = db.session.get(Contract, contract_id)
            self.assertEqual(updated_c.id_cliente, tgt_id)

            # 6. Verify target client absorbed missing documents and notes
            updated_tgt = db.session.get(Client, tgt_id)
            self.assertEqual(updated_tgt.url_habilitacao, '/static/uploads/carlos_licence.jpg')
            self.assertIn('Customer prefers card payments', updated_tgt.notas_internas)
            self.assertIn(f'MERGED from Customer #{src_id}', updated_tgt.notas_internas)

            # 7. Verify source client was deleted
            deleted_src = db.session.get(Client, src_id)
            self.assertIsNone(deleted_src)

            # 8. Verify AuditLog entry
            audit_entry = AuditLog.query.filter_by(acao='CLIENT_MERGE', entidade_id=str(tgt_id)).first()
            self.assertIsNotNone(audit_entry)
            self.assertIn(f'Cliente duplicado #{src_id}', audit_entry.descricao)

        finally:
            # Cleanup
            c_clean = db.session.get(Contract, contract_id)
            if c_clean:
                db.session.delete(c_clean)
            tgt_clean = db.session.get(Client, tgt_id)
            if tgt_clean:
                db.session.delete(tgt_clean)
            src_clean = db.session.get(Client, src_id)
            if src_clean:
                db.session.delete(src_clean)
            db.session.commit()

    def test_novo_contrato_renders_smart_customer_search(self):
        """Test that /contratos/novo renders customer filter, count badge, and info card."""
        res = self.client.get('/contratos/novo')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('clienteSearchFilter', html)
        self.assertIn('clienteCountBadge', html)
        self.assertIn('clienteSelectedCard', html)
        self.assertIn('btnClearClienteFilter', html)

if __name__ == '__main__':
    unittest.main()

