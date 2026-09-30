import unittest
from datetime import datetime, timedelta
from app import app, db, Contract, Client, Motorcycle, ContractType, ContractStatus, User

class TestContratosImprovements(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app
        self.client = app.test_client()

        with app.app_context():
            self.admin = User.query.filter_by(is_admin=True).first()
            if not self.admin:
                self.admin = User(
                    nome="Admin Test",
                    email="admin_contratos@ffmotors.co.uk",
                    is_admin=True,
                    perm_alugueis=True,
                    ativo=True
                )
                self.admin.set_password("admin123")
                db.session.add(self.admin)
                db.session.commit()

    def test_contratos_api_kpis_and_enriched_fields(self):
        with self.app.app_context():
            with self.client.session_transaction() as sess:
                sess['_user_id'] = str(self.admin.id)
                sess['_fresh'] = True
                sess['last_activity'] = datetime.now().timestamp()

            res = self.client.get('/api/contratos?limit=5')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()

            # 1. Assert KPI strip metrics are present
            self.assertIn('kpis', data)
            kpis = data['kpis']
            self.assertIn('rentals', kpis)
            self.assertIn('sales', kpis)
            self.assertIn('pending_release', kpis)
            self.assertIn('deposit_holds', kpis)
            self.assertIn('pending_v5c', kpis)
            self.assertIsInstance(kpis['rentals'], int)
            self.assertIsInstance(kpis['sales'], int)

            # 2. Assert items have enriched fields (model, phone, signature, real-time balances)
            if data['itens']:
                item = data['itens'][0]
                self.assertIn('cliente_telefone', item)
                self.assertIn('moto_modelo', item)
                self.assertIn('assinado', item)
                self.assertIn('dia_pagamento_semanal', item)
                self.assertIn('total_pendente', item)
                self.assertIn('total_pago', item)

            # 3. Test Dia de Pagamento filter (e.g. Monday = 0)
            res_monday = self.client.get('/api/contratos?dia_pagamento=0')
            self.assertEqual(res_monday.status_code, 200)
            data_monday = res_monday.get_json()
            for it in data_monday['itens']:
                self.assertEqual(it['dia_pagamento_semanal'], 0)

            # 4. Test Date Range filter
            today_str = datetime.now().strftime('%Y-%m-%d')
            past_str = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            res_date = self.client.get(f'/api/contratos?data_inicio={past_str}&data_fim={today_str}')
            self.assertEqual(res_date.status_code, 200)
            data_date = res_date.get_json()
            self.assertIn('itens', data_date)

            print(f"\n✓ /api/contratos KPIs validated: {kpis}")
            print(f"✓ /api/contratos enriched fields and filters (day of week, date range) verified successfully.")

if __name__ == '__main__':
    unittest.main()
