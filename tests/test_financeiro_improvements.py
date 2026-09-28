import unittest
from datetime import datetime, timedelta
import pytz
import json
from app import app, db
from database import User, Client, Motorcycle, Contract, FinancialTransaction, TransactionStatus, TransactionType, ContractType

class TestFinanceiroImprovements(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()
        
        # Ensure an admin user exists and log in
        admin = User.query.filter_by(role='Admin').first()
        if not admin:
            admin = User.query.first()
            
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True
            sess['_csrf_token'] = 'test-token'
            sess['last_activity'] = datetime.now().timestamp()

    def tearDown(self):
        self.app_context.pop()

    def test_01_financeiro_resumo_kpis(self):
        """Test GET /api/financeiro/resumo returns all KPI metrics accurately."""
        res = self.client.get('/api/financeiro/resumo')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        self.assertIn('pendente', data)
        self.assertIn('overdue', data)
        self.assertIn('hoje', data)
        self.assertIn('semana', data)
        self.assertIn('mes', data)
        
        self.assertIn('total', data['pendente'])
        self.assertIn('qtd', data['pendente'])
        self.assertIn('total', data['overdue'])
        self.assertIn('qtd', data['overdue'])
        self.assertIn('total', data['hoje'])
        self.assertIn('total', data['semana'])
        print(f"\n✓ /api/financeiro/resumo verified: Pending £{data['pendente']['total']}, Overdue £{data['overdue']['total']}, Today £{data['hoje']['total']}")

    def test_02_fechamento_caixa(self):
        """Test GET /api/financeiro/fechamento-caixa returns daily register reconciliation."""
        res = self.client.get('/api/financeiro/fechamento-caixa')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        self.assertIn('data', data)
        self.assertIn('total_arrecadado', data)
        self.assertIn('total_transacoes', data)
        self.assertIn('metodos', data)
        self.assertIn('Cash', data['metodos'])
        self.assertIn('Card', data['metodos'])
        self.assertIn('Bank Transfer', data['metodos'])
        self.assertIn('Exchange', data['metodos'])
        print(f"✓ /api/financeiro/fechamento-caixa verified: Total collected on {data['data']} is £{data['total_arrecadado']}")

    def test_03_nova_cobranca_avulsa(self):
        """Test POST /api/financeiro/nova-cobranca creates charge and logs audit."""
        # Find any contract
        contrato = Contract.query.first()
        self.assertIsNotNone(contrato, "Contract required for testing")
        
        payload = {
            'id_contrato': contrato.id,
            'tipo': 'fine',
            'valor': 65.50,
            'data_vencimento': datetime.now().strftime('%Y-%m-%d'),
            'nota': 'Bus lane fine Birmingham City Council #PCN-9988'
        }
        res = self.client.post('/api/financeiro/nova-cobranca', json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn('id', data)
        
        # Verify in database
        t = db.session.get(FinancialTransaction, data['id'])
        self.assertIsNotNone(t)
        self.assertEqual(float(t.valor), 65.50)
        self.assertEqual(t.nota, 'Bus lane fine Birmingham City Council #PCN-9988')
        print(f"✓ POST /api/financeiro/nova-cobranca created charge #{t.id} successfully")

    def test_04_exportar_csv(self):
        """Test GET /api/financeiro/exportar-csv returns downloadable CSV with BOM."""
        res = self.client.get('/api/financeiro/exportar-csv')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'text/csv')
        self.assertTrue('attachment;' in res.headers.get('Content-Disposition', ''))
        
        csv_text = res.data.decode('utf-8')
        self.assertTrue(csv_text.startswith('\ufeff'), "Should start with UTF-8 BOM for Excel")
        self.assertIn('Transaction ID,Contract ID,Customer Name', csv_text)
        print("✓ GET /api/financeiro/exportar-csv generated valid CSV document")

    def test_05_relatorio_pdf_imprimivel(self):
        """Test GET /financeiro/relatorio-pdf renders executive A4 printable statement."""
        res = self.client.get('/financeiro/relatorio-pdf')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('FF MOTORS BIRMINGHAM', html)
        self.assertIn('summary-bar', html.lower())
        print("✓ GET /financeiro/relatorio-pdf rendered printable HTML report successfully")

    def test_06_listar_financeiro_com_metodo_e_telefone(self):
        """Test GET /api/financeiro includes cliente_telefone and supports metodo filtering."""
        res = self.client.get('/api/financeiro?limit=5')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        itens = data.get('itens', [])
        if len(itens) > 0:
            first = itens[0]
            self.assertIn('cliente_telefone', first)
            self.assertIn('id_transacao_origem', first)
            self.assertIn('cliente_dividas_pendentes', first)
            self.assertIn('ultimo_lembrete', first)
            self.assertIn('ultimo_lembrete_por', first)
            print(f"✓ GET /api/financeiro returns phone field: '{first.get('cliente_telefone')}', overdue debts: {first.get('cliente_dividas_pendentes')}")

        # Verify client with overdue debts vs future scheduled debts
        from app import get_london_date
        inicio_hoje = datetime.combine(get_london_date(), datetime.min.time())
        res_all = self.client.get('/api/financeiro?limit=100&status=pendentes')
        itens_pend = res_all.get_json().get('itens', [])
        for it in itens_pend:
            cid = it.get('cliente_id')
            if cid:
                real_overdue = FinancialTransaction.query.join(Contract, Contract.id == FinancialTransaction.id_contrato).filter(
                    Contract.id_cliente == cid,
                    FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
                    FinancialTransaction.data_vencimento < inicio_hoje
                ).count()
                self.assertEqual(it.get('cliente_dividas_pendentes'), real_overdue, "Debt count must strictly match overdue transactions")

    def test_07_lembrete_whatsapp_timestamp(self):
        """Test POST /api/financeiro/<id>/lembrete records timestamp and staff name."""
        t = FinancialTransaction.query.filter_by(status=TransactionStatus.PENDING).first()
        self.assertIsNotNone(t, "Pending transaction required for test")

        res = self.client.post(f'/api/financeiro/{t.id}/lembrete')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('sucesso'))
        self.assertIsNotNone(data.get('ultimo_lembrete'))

        # Verify DB persisted
        db.session.refresh(t)
        self.assertIsNotNone(t.ultimo_lembrete)
        self.assertIsNotNone(t.ultimo_lembrete_por)
        print(f"✓ POST /api/financeiro/{t.id}/lembrete saved timestamp {t.ultimo_lembrete} by {t.ultimo_lembrete_por}")

    def test_08_pagar_lote(self):
        """Test POST /api/financeiro/pagar-lote marks multiple transactions as Paid."""
        # Create 2 pending transactions for testing
        contrato = Contract.query.first()
        t1 = FinancialTransaction(
            id_contrato=contrato.id,
            tipo='Other',
            valor=15.00,
            status=TransactionStatus.PENDING.value,
            data_vencimento=datetime.now(),
            nota="Test Batch 1"
        )
        t2 = FinancialTransaction(
            id_contrato=contrato.id,
            tipo='Other',
            valor=25.00,
            status=TransactionStatus.PENDING.value,
            data_vencimento=datetime.now(),
            nota="Test Batch 2"
        )
        db.session.add_all([t1, t2])
        db.session.commit()

        payload = {
            'ids': [t1.id, t2.id],
            'forma_pagamento': 'Bank Transfer',
            'nota': 'Batch payment test #BATCH-123'
        }
        res = self.client.post('/api/financeiro/pagar-lote', json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('atualizados'), 2)
        self.assertEqual(data.get('total_pago'), 40.00)

        # Verify DB updates
        db.session.refresh(t1)
        db.session.refresh(t2)
        self.assertEqual(t1.status, TransactionStatus.PAID.value)
        self.assertEqual(t2.status, TransactionStatus.PAID.value)
        self.assertEqual(t1.forma_pagamento, 'Bank Transfer')
        self.assertEqual(t2.forma_pagamento, 'Bank Transfer')
        self.assertIn('Batch payment test #BATCH-123', t1.nota)
        self.assertIn('Batch payment test #BATCH-123', t2.nota)
        print("✓ POST /api/financeiro/pagar-lote successfully paid 2 transactions in batch")

    def test_09_filtros_exatos_inline(self):
        """Test GET /api/financeiro with exact contrato_id, cliente_id, and placa filters."""
        # Find a transaction with a contract and client
        t = FinancialTransaction.query.filter(FinancialTransaction.contrato != None).first()
        self.assertIsNotNone(t, "Transaction with contract required")
        cid = t.id_contrato
        cliente_id = t.contrato.id_cliente
        placa = t.contrato.placa

        # 1. Exact Contract Filter
        res_c = self.client.get(f'/api/financeiro?contrato_id={cid}')
        self.assertEqual(res_c.status_code, 200)
        itens_c = res_c.get_json().get('itens', [])
        self.assertTrue(len(itens_c) > 0)
        for item in itens_c:
            self.assertEqual(item['id_contrato'], cid, "Exact contract filter must only return matching contract ID")

        # 2. Exact Customer Filter
        if cliente_id:
            res_cli = self.client.get(f'/api/financeiro?cliente_id={cliente_id}')
            self.assertEqual(res_cli.status_code, 200)
            itens_cli = res_cli.get_json().get('itens', [])
            self.assertTrue(len(itens_cli) > 0)
            for item in itens_cli:
                self.assertEqual(item['cliente_id'], cliente_id, "Exact customer filter must only return matching client ID")

        # 3. Exact Plate Filter
        if placa:
            res_placa = self.client.get(f'/api/financeiro?placa={placa}')
            self.assertEqual(res_placa.status_code, 200)
            itens_placa = res_placa.get_json().get('itens', [])
            self.assertTrue(len(itens_placa) > 0)
            for item in itens_placa:
                self.assertEqual(item['placa'].upper().replace(' ', ''), placa.upper().replace(' ', ''))

        print(f"✓ Exact filters verified: Contract #{cid}, Client #{cliente_id}, Bike {placa}")

    def test_10_relatorio_fechamento_caixa_print(self):
        """Test GET /financeiro/fechamento-caixa/print renders formal executive closing document."""
        res = self.client.get('/financeiro/fechamento-caixa/print')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        
        self.assertIn('FF MOTORS BIRMINGHAM', html)
        self.assertIn('Daily Cashing Up', html)
        self.assertIn('End-of-Day Closing Sheet', html)
        self.assertIn('Total Arrecadado', html)
        self.assertIn('Cash in Till', html)
        self.assertIn('Card Terminal', html)
        self.assertIn('Physical Cash Drawer Reconciliation', html)
        self.assertIn('Cashier / Counter Staff Verification', html)
        self.assertIn('Duty Manager / Supervisor Sign-off', html)
        
        # Test with specific date
        res_date = self.client.get('/financeiro/fechamento-caixa/print?data=2026-09-28')
        self.assertEqual(res_date.status_code, 200)
        html_date = res_date.get_data(as_text=True)
        self.assertIn('28/09/2026', html_date)
        print("✓ /financeiro/fechamento-caixa/print rendered executive closing sheet successfully")

    def test_11_alinhamento_inteligente_filtros(self):
        """Test smart synchronization between status and date fields (Paid -> Payment Date, Pending -> Due Date)."""
        hoje_str = '2026-09-28'

        # 1. When querying Paid transactions without explicit campo_data, backend defaults to data_pagamento
        res_paid = self.client.get(f'/api/financeiro?status=Paid&data_inicio={hoje_str}&data_fim={hoje_str}')
        self.assertEqual(res_paid.status_code, 200)
        data_paid = res_paid.get_json()
        itens_paid = data_paid.get('itens', [])
        self.assertTrue(len(itens_paid) > 0, "Should return transactions paid today")
        for item in itens_paid:
            self.assertEqual(item['status'], 'Paid')
            self.assertIsNotNone(item['data_pagamento'], "Paid item must have payment date")
            self.assertTrue(item['data_pagamento'].startswith(hoje_str), f"Payment date {item['data_pagamento']} must match filter {hoje_str}")

        # 2. When querying pending with campo_data=pagamento, backend safeguards and switches to vencimento
        res_pend = self.client.get(f'/api/financeiro?status=pendentes&campo_data=pagamento&data_inicio={hoje_str}')
        self.assertEqual(res_pend.status_code, 200)
        data_pend = res_pend.get_json()
        for item in data_pend.get('itens', []):
            self.assertEqual(item['status'], 'Pending')

        # 3. PDF report with status=Paid formats filter label with Payment Date
        res_pdf = self.client.get(f'/financeiro/relatorio-pdf?status=Paid&data_inicio={hoje_str}&data_fim={hoje_str}')
        self.assertEqual(res_pdf.status_code, 200)
        html_pdf = res_pdf.get_data(as_text=True)
        self.assertIn('Date (Payment Date):', html_pdf)
        print("✓ Smart filter alignment verified: Paid transactions properly filter on Payment Date across API and PDF Report")

if __name__ == '__main__':
    unittest.main()



