import os
import sys
import unittest
import io
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from database import Motorcycle, Contract, Client, User, FinancialTransaction, Inspection, MotoStatus, ContractStatus

class TestChargeReferencesAndAttachments(unittest.TestCase):
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

        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            admin = User.query.first()

        if admin:
            admin.is_admin = True
            admin.perm_alugueis = True
            db.session.commit()

            with self.client.session_transaction() as sess:
                sess['_user_id'] = str(admin.id)
                sess['_fresh'] = True
                sess['last_activity'] = datetime.now().timestamp()

        # Find or create a client, bike and active rental contract
        self.client_obj = Client.query.first()
        if not self.client_obj:
            self.client_obj = Client(nome="Test Hirer", telefone="07111222333")
            db.session.add(self.client_obj)
            db.session.commit()

        self.moto = Motorcycle.query.filter_by(status=MotoStatus.AVAILABLE.value).first()
        if not self.moto:
            self.moto = Motorcycle(placa="TST99REF", modelo="Honda PCX 125", status=MotoStatus.AVAILABLE.value)
            db.session.add(self.moto)
            db.session.commit()

        self.contrato = Contract(
            id_cliente=self.client_obj.id,
            placa=self.moto.placa,
            tipo_contrato="Rent",
            status=ContractStatus.ACTIVE.value,
            valor_aluguel_semanal=100.0,
            cliente_nome=self.client_obj.nome,
            moto_placa=self.moto.placa
        )
        db.session.add(self.contrato)
        db.session.commit()

    def tearDown(self):
        FinancialTransaction.query.filter_by(id_contrato=self.contrato.id).delete()
        Inspection.query.filter_by(id_contrato=self.contrato.id).delete()
        db.session.delete(self.contrato)
        db.session.commit()
        self.app_context.pop()

    def test_create_charge_with_reference_and_attachment(self):
        # 1. Create a fine charge with reference text and attached fake photo
        fake_photo = (io.BytesIO(b'fake_image_bytes_pcn'), 'pcn_letter_notice.jpg')
        res = self.client.post(f'/api/contratos/{self.contrato.id}/cobrancas', data={
            'tipo': 'Fine',
            'valor': '65.00',
            'data_vencimento': '2026-10-25',
            'referencia': 'PCN London Congestion Charge #PCN-99881',
            'fotos': fake_photo
        }, content_type='multipart/form-data')

        self.assertEqual(res.status_code, 201, res.get_json())
        data = res.get_json()
        charge_id = data.get('id')
        self.assertIsNotNone(charge_id)

        # Verify in DB
        tx = db.session.get(FinancialTransaction, charge_id)
        self.assertIsNotNone(tx)
        self.assertEqual(tx.tipo, 'Fine')
        self.assertEqual(float(tx.valor), 65.0)
        self.assertEqual(tx.nota, 'PCN London Congestion Charge #PCN-99881')
        self.assertIsNotNone(tx.url_anexos)
        self.assertTrue('pcn_letter_notice' in tx.url_anexos)

        # Verify contract detail API returns reference and attachments
        res_detalhe = self.client.get(f'/api/contratos/{self.contrato.id}')
        self.assertEqual(res_detalhe.status_code, 200)
        detalhe_json = res_detalhe.get_json()
        matching_tx = next((t for t in detalhe_json.get('transacoes', []) if t['id'] == charge_id), None)
        self.assertIsNotNone(matching_tx)
        self.assertEqual(matching_tx['nota'], 'PCN London Congestion Charge #PCN-99881')
        self.assertIsNotNone(matching_tx['url_anexos'])

        # Verify /api/financeiro list returns reference and attachments
        res_fin = self.client.get(f'/api/financeiro?contrato_id={self.contrato.id}&limit=500')
        self.assertEqual(res_fin.status_code, 200)
        fin_json = res_fin.get_json()
        matching_fin_tx = next((t for t in fin_json.get('itens', []) if t['id'] == charge_id), None)
        self.assertIsNotNone(matching_fin_tx)
        self.assertEqual(matching_fin_tx['nota'], 'PCN London Congestion Charge #PCN-99881')
        self.assertIsNotNone(matching_fin_tx['url_anexos'])

    def test_inspection_auto_creates_linked_damage_charge(self):
        # 2. Record an Incident inspection and check "Generate Damage Charge"
        fake_photo1 = (io.BytesIO(b'fake_damage_photo_1'), 'broken_mirror_damage.jpg')
        res = self.client.post('/api/vistorias', data={
            'id_contrato': str(self.contrato.id),
            'tipo': 'Incident',
            'milhagem': '12500',
            'observacoes': 'Customer dropped bike on curb, broken right side mirror and scuffed exhaust.',
            'gerar_cobranca': '1',
            'cobranca_valor': '115.50',
            'cobranca_vencimento': '2026-10-18',
            'cobranca_referencia': 'Right mirror & exhaust repair fee',
            'fotos': fake_photo1
        }, content_type='multipart/form-data')

        self.assertEqual(res.status_code, 201, res.get_json())
        data = res.get_json()
        vistoria_id = data.get('id')
        cobranca_id = data.get('cobranca_id')

        self.assertIsNotNone(vistoria_id)
        self.assertTrue(data.get('cobranca_gerada'))
        self.assertIsNotNone(cobranca_id)

        # Verify inspection in DB
        vistoria = db.session.get(Inspection, vistoria_id)
        self.assertIsNotNone(vistoria)
        self.assertEqual(vistoria.tipo, 'Incident')

        # Verify transaction in DB linked to this inspection
        tx = db.session.get(FinancialTransaction, cobranca_id)
        self.assertIsNotNone(tx)
        self.assertEqual(tx.tipo, 'Damage')
        self.assertEqual(float(tx.valor), 115.50)
        self.assertEqual(tx.id_vistoria, vistoria_id)
        self.assertEqual(tx.nota, 'Right mirror & exhaust repair fee')
        self.assertEqual(tx.url_anexos, vistoria.url_fotos)

        # Verify contract detail returns id_vistoria link
        res_det = self.client.get(f'/api/contratos/{self.contrato.id}')
        det_json = res_det.get_json()
        matching_tx = next((t for t in det_json.get('transacoes', []) if t['id'] == cobranca_id), None)
        self.assertIsNotNone(matching_tx)
        self.assertEqual(matching_tx['id_vistoria'], vistoria_id)
        self.assertEqual(matching_tx['nota'], 'Right mirror & exhaust repair fee')

    def test_charge_description_persists_after_payment_and_reversal(self):
        """Ensure charge description (e.g. Damage notes) never disappears when paid or reverted."""
        # 1. Create a charge with description
        res = self.client.post('/api/financeiro/nova-cobranca', json={
            'id_contrato': self.contrato.id,
            'tipo': 'Damage',
            'valor': 100.00,
            'data_vencimento': datetime.now().strftime('%Y-%m-%d'),
            'nota': 'crack!!!!'
        })
        self.assertEqual(res.status_code, 201)
        charge_id = res.get_json()['id']

        # 2. Pay without payment note
        res_pay = self.client.post(f'/api/financeiro/pagar/{charge_id}', json={
            'forma_pagamento': 'Cash',
            'valor_pago': 100.00
        })
        self.assertEqual(res_pay.status_code, 200)

        # Verify DB and contract API still show 'crack!!!!'
        tx = db.session.get(FinancialTransaction, charge_id)
        self.assertEqual(tx.status, 'Paid')
        self.assertEqual(tx.nota, 'crack!!!!')

        res_det = self.client.get(f'/api/contratos/{self.contrato.id}')
        det_tx = next((t for t in res_det.get_json()['transacoes'] if t['id'] == charge_id), None)
        self.assertIsNotNone(det_tx)
        self.assertEqual(det_tx['nota'], 'crack!!!!')

        # 3. Revert payment
        res_rev = self.client.post(f'/api/financeiro/reverter/{charge_id}')
        self.assertEqual(res_rev.status_code, 200)

        db.session.refresh(tx)
        self.assertEqual(tx.status, 'Pending')
        self.assertEqual(tx.nota, 'crack!!!!')

        # 4. Pay with an explicit payment note
        res_pay2 = self.client.post(f'/api/financeiro/pagar/{charge_id}', json={
            'forma_pagamento': 'Bank Transfer',
            'valor_pago': 100.00,
            'nota': 'Paid via Lloyd\'s Ref #9988'
        })
        self.assertEqual(res_pay2.status_code, 200)

        db.session.refresh(tx)
        self.assertEqual(tx.status, 'Paid')
        self.assertIn('crack!!!!', tx.nota)
        self.assertEqual(tx.nota_pagamento, 'Paid via Lloyd\'s Ref #9988')

if __name__ == '__main__':
    unittest.main()
