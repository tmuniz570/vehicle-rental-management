import os
import sys
import unittest
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from database import Motorcycle, Contract, Client, User, MotoStatus, ContractStatus

class TestDashboardImprovements(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

        # Authenticate session as Admin / Rentals user
        admin = User.query.filter_by(role='Admin').first()
        if not admin:
            admin = User.query.first()

        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

    def tearDown(self):
        self.app_context.pop()

    def test_api_dashboard_payload_enrichment(self):
        res = self.client.get('/api/dashboard')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # Verify new cashflow metrics
        self.assertIn('collected_today', data)
        self.assertIn('collected_this_week', data)
        self.assertIsInstance(data['collected_today'], (int, float))
        self.assertIsInstance(data['collected_this_week'], (int, float))

        # Verify due_today section corresponds to real pending FinancialTransactions
        self.assertIn('due_today', data)
        due_today = data['due_today']
        self.assertIn('total_count', due_today)
        self.assertIn('total_amount', due_today)
        self.assertIn('items', due_today)
        self.assertIsInstance(due_today['items'], list)

        for item in due_today['items']:
            self.assertIsNotNone(item.get('transacao_id'), "All items in due_today must originate from a real FinancialTransaction")
            self.assertIn('tipo', item)
            self.assertIn('valor', item)
            self.assertGreater(item['valor'], 0)

        print(f"\n✓ Dashboard enrichment verified:")
        print(f"  Collected Today: £{data['collected_today']:.2f}")
        print(f"  Collected This Week: £{data['collected_this_week']:.2f}")
        print(f"  Payments Due Today: {due_today['total_count']} items, Total: £{due_today['total_amount']:.2f}")

    def test_api_busca_rapida(self):
        # Test empty or short query
        res_short = self.client.get('/api/busca-rapida?q=a')
        self.assertEqual(res_short.status_code, 200)
        data_short = res_short.get_json()
        self.assertEqual(data_short['motos'], [])
        self.assertEqual(data_short['clientes'], [])
        self.assertEqual(data_short['contratos'], [])

        # Test search query with existing moto plate or client
        moto = Motorcycle.query.first()
        if moto:
            search_term = moto.placa[:3]
            res = self.client.get(f'/api/busca-rapida?q={search_term}')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertIn('motos', data)
            self.assertIn('clientes', data)
            self.assertIn('contratos', data)
            
            # Verify moto keys
            if data['motos']:
                m0 = data['motos'][0]
                self.assertIn('placa', m0)
                self.assertIn('contract_id', m0)
                self.assertIn('hirer_name', m0)

            print(f"\n✓ Quick Lookup search for '{search_term}': {len(data['motos'])} bikes, {len(data['clientes'])} customers, {len(data['contratos'])} contracts found.")

        # Test searching for a contract ID
        contract = Contract.query.first()
        if contract:
            res_c = self.client.get(f'/api/busca-rapida?q={contract.id}')
            self.assertEqual(res_c.status_code, 200)
            data_c = res_c.get_json()
            self.assertIn('contratos', data_c)
            found = any(ct['id'] == contract.id for ct in data_c['contratos'])
            self.assertTrue(found, f"Contract #{contract.id} should be found in quick search")
            print(f"✓ Quick Lookup search by ID '{contract.id}' successfully found contract #{contract.id}")

if __name__ == '__main__':
    unittest.main()
