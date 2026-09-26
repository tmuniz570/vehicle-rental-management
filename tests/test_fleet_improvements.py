import os
import sys
import unittest
from datetime import datetime, timedelta
import pytz

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from database import Motorcycle, Contract, Client, User, MotoStatus, ContractStatus, ContractType

class TestFleetImprovements(unittest.TestCase):
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

    def test_api_motos_returns_contracts_and_kpis(self):
        res = self.client.get('/api/motos')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        self.assertIn('itens', data)
        self.assertIn('kpis', data)
        
        kpis = data['kpis']
        self.assertIn('total', kpis)
        self.assertIn('operational', kpis)
        self.assertIn('available', kpis)
        self.assertIn('rented', kpis)
        self.assertIn('maintenance', kpis)
        self.assertIn('missing_v5c', kpis)
        self.assertIn('tax_mot_warnings', kpis)
        
        print(f"\n✓ Fleet KPIs retrieved successfully:")
        print(f"  Total: {kpis['total']} | Operational: {kpis['operational']} | Available: {kpis['available']}")
        print(f"  Rented: {kpis['rented']} | Maintenance: {kpis['maintenance']} | Missing V5C: {kpis['missing_v5c']} | Alerts: {kpis['tax_mot_warnings']}")

        # Verify contracts in items
        rented_found = False
        for item in data['itens']:
            self.assertIn('active_contract', item)
            self.assertIn('last_contract', item)
            if item['status'] in ['Rented', 'Alugada']:
                rented_found = True
                if item['active_contract']:
                    print(f"✓ Found Rented bike {item['placa']} with active contract #{item['active_contract']['id']} ({item['active_contract']['cliente_nome']})")

    def test_api_motos_warnings_filter(self):
        res = self.client.get('/api/motos?status=warnings')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('itens', data)
        print(f"✓ Querying /api/motos?status=warnings returned {len(data['itens'])} bikes with tax/mot warnings")

    def test_api_motos_csv_export(self):
        res = self.client.get('/api/motos/export')
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/csv', res.content_type)
        self.assertIn('attachment;', res.headers.get('Content-Disposition', ''))
        
        csv_text = res.get_data(as_text=True)
        lines = csv_text.strip().split('\n')
        self.assertGreater(len(lines), 1, "CSV should contain headers and at least one data row")
        
        header = lines[0]
        self.assertIn('Reg Plate', header)
        self.assertIn('Active Contract ID', header)
        self.assertIn('Active Hirer Name', header)
        self.assertIn('Active Hirer Phone', header)
        print(f"✓ CSV Export verified: {len(lines)} lines exported with valid headers and data")

    def test_motos_relatorio_pdf(self):
        # 1. Unfiltered report
        res = self.client.get('/motos/relatorio-pdf')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('Fleet Status & Operational Report', html)
        self.assertIn('FF MOTORS', html)
        self.assertIn('Print / Save as PDF', html)
        self.assertIn('Reg Plate', html)
        self.assertIn('Mileage', html)
        print("✓ /motos/relatorio-pdf renders full printable PDF report correctly")

        # 2. Filtered report (e.g. status=Rented)
        res_rented = self.client.get('/motos/relatorio-pdf?status=Rented')
        self.assertEqual(res_rented.status_code, 200)
        html_rented = res_rented.get_data(as_text=True)
        self.assertIn('Filter: Status: Rented', html_rented)
        print("✓ /motos/relatorio-pdf with status=Rented renders filtered report correctly")

if __name__ == '__main__':
    unittest.main()
