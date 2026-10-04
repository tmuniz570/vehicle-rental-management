import os
import sys
import unittest
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from database import Motorcycle, Contract, Client, User, MotoStatus, ContractStatus

class TestInternalNotes(unittest.TestCase):
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

    def tearDown(self):
        self.app_context.pop()

    def test_client_internal_notes_lifecycle(self):
        # 1. Create client with internal notes
        res = self.client.post('/api/clientes', data={
            'nome': 'Test Notes Client',
            'telefone': '07000999111',
            'email': 'notesclient@test.co.uk',
            'endereco': '10 Downing St, London',
            'notas_internas': 'Cliente VIP. Sempre prefere comunicação via WhatsApp.'
        })
        self.assertEqual(res.status_code, 201, res.get_json())
        client_id = res.get_json()['id']

        # Verify in database
        client_obj = db.session.get(Client, client_id)
        self.assertIsNotNone(client_obj)
        self.assertEqual(client_obj.notas_internas, 'Cliente VIP. Sempre prefere comunicação via WhatsApp.')

        # 2. Check listing includes notas_internas
        res_list = self.client.get(f'/api/clientes?id={client_id}')
        self.assertEqual(res_list.status_code, 200)
        items = res_list.get_json().get('itens', [])
        self.assertTrue(len(items) >= 1)
        target = next((c for c in items if c['id'] == client_id), None)
        self.assertIsNotNone(target)
        self.assertEqual(target['notas_internas'], 'Cliente VIP. Sempre prefere comunicação via WhatsApp.')

        # 3. Update client internal notes via PUT
        res_upd = self.client.put(f'/api/clientes/{client_id}', json={
            'notas_internas': 'Cliente VIP. Atualizado: ligar após as 14h.'
        })
        self.assertEqual(res_upd.status_code, 200)
        db.session.refresh(client_obj)
        self.assertEqual(client_obj.notas_internas, 'Cliente VIP. Atualizado: ligar após as 14h.')

        # Clean up
        db.session.delete(client_obj)
        db.session.commit()

    def test_motorcycle_internal_notes_lifecycle(self):
        test_plate = 'NT26XYZ'
        # Remove if exists
        old = db.session.get(Motorcycle, test_plate)
        if old:
            db.session.delete(old)
            db.session.commit()

        # 1. Create motorbike with internal notes
        res = self.client.post('/api/motos', json={
            'placa': test_plate,
            'modelo': 'Honda PCX 125',
            'cor': 'Pearl White',
            'milhagem_atual': 4500,
            'notas_internas': 'Chave reserva no armário 2. Pequeno risco no espelho esquerdo.'
        })
        self.assertEqual(res.status_code, 201, res.get_json())

        # Verify in database
        moto_obj = db.session.get(Motorcycle, test_plate)
        self.assertIsNotNone(moto_obj)
        self.assertEqual(moto_obj.notas_internas, 'Chave reserva no armário 2. Pequeno risco no espelho esquerdo.')

        # 2. Check details endpoint
        res_det = self.client.get(f'/api/motos/{test_plate}/detalhes')
        self.assertEqual(res_det.status_code, 200)
        self.assertEqual(res_det.get_json().get('notas_internas'), 'Chave reserva no armário 2. Pequeno risco no espelho esquerdo.')

        # 3. Check listing endpoint
        res_list = self.client.get(f'/api/motos?search={test_plate}')
        self.assertEqual(res_list.status_code, 200)
        items = res_list.get_json().get('itens', [])
        target = next((m for m in items if m['placa'] == test_plate), None)
        self.assertIsNotNone(target)
        self.assertEqual(target.get('notas_internas'), 'Chave reserva no armário 2. Pequeno risco no espelho esquerdo.')

        # 4. Update motorcycle notes via PUT
        res_upd = self.client.put(f'/api/motos/{test_plate}', json={
            'notas_internas': 'Chave reserva entregue ao mecânico. Risco polido.'
        })
        self.assertEqual(res_upd.status_code, 200)
        db.session.refresh(moto_obj)
        self.assertEqual(moto_obj.notas_internas, 'Chave reserva entregue ao mecânico. Risco polido.')

        # Clean up
        db.session.delete(moto_obj)
        db.session.commit()

    def test_contract_internal_notes_lifecycle(self):
        # Find or create a test client and bike
        client = Client.query.first()
        bike = Motorcycle.query.filter_by(status=MotoStatus.AVAILABLE.value).first()
        if not bike:
            bike = Motorcycle(placa='TESTNT1', modelo='Honda Vision', cor='Grey', status=MotoStatus.AVAILABLE.value)
            db.session.add(bike)
            db.session.commit()

        # 1. Create contract with internal notes
        res = self.client.post('/api/contratos', data={
            'id_cliente': client.id,
            'placa': bike.placa,
            'tipo_contrato': 'Rent',
            'dia_pagamento_semanal': 0,
            'valor_aluguel_semanal': 200.0,
            'valor_deposito': 150.0,
            'milhagem_inicial': 1000,
            'notas_internas': 'Particularidade: caução parcelada em 2x acordada com diretoria.'
        })
        self.assertEqual(res.status_code, 201, res.get_json())
        contract_id = res.get_json()['id']

        # Verify in database
        contract_obj = db.session.get(Contract, contract_id)
        self.assertIsNotNone(contract_obj)
        self.assertEqual(contract_obj.notas_internas, 'Particularidade: caução parcelada em 2x acordada com diretoria.')

        # 2. Check contract details endpoint
        res_det = self.client.get(f'/api/contratos/{contract_id}')
        self.assertEqual(res_det.status_code, 200)
        self.assertEqual(res_det.get_json().get('notas_internas'), 'Particularidade: caução parcelada em 2x acordada com diretoria.')

        # 3. Check contract listing endpoint
        res_list = self.client.get(f'/api/contratos?search={contract_id}')
        self.assertEqual(res_list.status_code, 200)
        items = res_list.get_json().get('itens', [])
        target = next((c for c in items if c['id'] == contract_id), None)
        self.assertIsNotNone(target)
        self.assertEqual(target.get('notas_internas'), 'Particularidade: caução parcelada em 2x acordada com diretoria.')

        # 4. Update contract internal notes via dedicated PUT /api/contratos/<id>/notas
        res_upd = self.client.put(f'/api/contratos/{contract_id}/notas', json={
            'notas_internas': 'Particularidade atualizada: 2ª parcela da caução recebida em dinheiro.'
        })
        self.assertEqual(res_upd.status_code, 200)
        db.session.refresh(contract_obj)
        self.assertEqual(contract_obj.notas_internas, 'Particularidade atualizada: 2ª parcela da caução recebida em dinheiro.')

        # Clean up test contract
        for t in contract_obj.transacoes:
            db.session.delete(t)
        for v in contract_obj.vistorias:
            db.session.delete(v)
        bike.status = MotoStatus.AVAILABLE.value
        db.session.delete(contract_obj)
        if bike.placa == 'TESTNT1':
            db.session.delete(bike)
        db.session.commit()

if __name__ == '__main__':
    unittest.main()
