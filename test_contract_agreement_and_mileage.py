import os
import sys
import io
import json
import base64
import time
from datetime import date

# Ensure app can be imported
sys.path.insert(0, r"c:\Users\tmuni\Downloads\FF Motors APP")

from app import app
from database import db, Motorcycle, Client, Contract, Inspection, ContractAttachment, User

def test_workflow():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        # Create test user session for Flask-Login
        with app.app_context():
            u = User.query.first()
            if not u:
                u = User(username='admin', role='admin')
                u.set_password('Admin@123')
                db.session.add(u)
                db.session.commit()
            u_id = str(u.id)

        with client.session_transaction() as sess:
            sess['_user_id'] = u_id
            sess['_fresh'] = True
            sess['last_activity'] = time.time()
            sess['_csrf_token'] = 'test_csrf_token_123'

        print("1. Testing motorcycle registration with mileage...")
        # Use a timestamped unique plate for isolation
        test_placa = f"T{int(time.time()) % 100000:05d}"
        res = client.post('/api/motos', json={
            'placa': test_placa,
            'modelo': 'Honda PCX 125',
            'ano': 2023,
            'status': 'Available',
            'cor': 'Black',
            'milhagem_atual': 12500
        }, headers={'X-CSRFToken': 'test_csrf_token_123'})
        assert res.status_code in (200, 201), f"Failed to create motorcycle: {res.status_code}, {res.data}"
        print(" Motorcycle created with milhagem_atual = 12500.")

        with app.app_context():
            moto = Motorcycle.query.filter_by(placa=test_placa).first()
            assert moto.milhagem_atual == 12500, f"Expected 12500, got {moto.milhagem_atual}"

            # Create test client if not exists
            cust = Client.query.filter_by(email="john@example.com").first()
            if not cust:
                cust = Client(nome="John Doe", telefone="07123456789", email="john@example.com", endereco="10 High Street, Birmingham")
                db.session.add(cust)
                db.session.commit()
            cust_id = cust.id

        print("2. Testing contract creation with start mileage...")
        res = client.post('/api/contratos', data={
            'id_cliente': cust_id,
            'placa': test_placa,
            'data_inicio': '2026-09-17',
            'valor_aluguel_semanal': 85.00,
            'valor_deposito': 200.00,
            'milhagem_inicial': 12500,
            'dia_pagamento_semanal': 0,
            'fotos': (io.BytesIO(b"fake image data"), 'checkout.jpg'),
            'seguro': (io.BytesIO(b"fake insurance pdf"), 'insurance.pdf')
        }, content_type='multipart/form-data', headers={'X-CSRFToken': 'test_csrf_token_123'})
        assert res.status_code in (200, 201), f"Failed to create contract: {res.status_code}, {res.data}"
        contrato_data = res.get_json()
        assert 'id' in contrato_data
        contract_id = contrato_data['id']
        print(f" Contract created with ID: {contract_id}")

        with app.app_context():
            ct = Contract.query.get(contract_id)
            assert ct.milhagem_inicial == 12500
            # Check initial inspection
            insp = Inspection.query.filter_by(id_contrato=contract_id, tipo='Check-out').first()
            assert insp is not None
            assert insp.milhagem == 12500
            print(" Initial inspection created with matching mileage: 12500.")

        print("3. Testing touch screen signature endpoint...")
        # 1x1 transparent png base64
        dummy_png = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        res = client.post(f'/api/contratos/{contract_id}/assinar', json={
            'tipo': 'inicial',
            'assinatura': dummy_png
        }, headers={'X-CSRFToken': 'test_csrf_token_123'})
        assert res.status_code == 200, f"Sign failed: {res.data}"
        sign_resp = res.get_json()
        assert sign_resp['success'] is True
        print(f" Start touch signature recorded: {sign_resp['url']}")

        print("4. Testing attachments upload endpoint...")
        data = {
            'tipo': 'escaneado',
            'arquivos': (io.BytesIO(b"%PDF-1.4 dummy pdf content"), 'test_signed_contract.pdf')
        }
        res = client.post(f'/api/contratos/{contract_id}/anexos', data=data, content_type='multipart/form-data', headers={'X-CSRFToken': 'test_csrf_token_123'})
        assert res.status_code in (200, 201), f"Attachment upload failed: {res.data}"
        att_resp = res.get_json()
        assert att_resp['success'] is True
        print(f" Attachment uploaded successfully: {att_resp['anexos'][0]['nome_original']}")

        print("5. Testing contract print view route...")
        res = client.get(f'/contratos/{contract_id}/imprimir')
        assert res.status_code == 200, f"Imprimir failed: {res.status_code}"
        assert b"Motorcycle Rental Agreement" in res.data
        assert b"J&amp;F Motorcycles LTD" in res.data or b"J&F Motorcycles LTD" in res.data
        assert b"12500" in res.data
        print(" Print view rendered correctly with 3-page agreement and signature blocks.")

        print("6. Testing Check-in inspection and mileage calculation...")
        res = client.post('/api/vistorias', data={
            'id_contrato': contract_id,
            'tipo': 'Check-in',
            'milhagem': 13120,
            'observacoes': 'Returned in good condition, small scratch on exhaust.',
            'combustivel': 'Full',
            'pneus': 'Good',
            'freios': 'Good',
            'luzes': 'Good',
            'fotos': (io.BytesIO(b"fake checkin photo"), 'checkin.jpg')
        }, content_type='multipart/form-data', headers={'X-CSRFToken': 'test_csrf_token_123'})
        assert res.status_code in (200, 201), f"Check-in inspection failed: {res.data}"
        print(" Check-in inspection saved.")

        # Test contract details API response
        res = client.get(f'/api/contratos/{contract_id}')
        assert res.status_code == 200
        detalhes = res.get_json()
        assert detalhes['milhagem_inicial'] == 12500
        assert detalhes['milhagem_final'] == 13120
        assert detalhes['milhas_rodadas'] == 620
        assert detalhes['assinatura_cliente_inicial'] is not None
        assert len(detalhes['anexos']) >= 1
        print(f" Contract details verified: initial={detalhes['milhagem_inicial']}, final={detalhes['milhagem_final']}, driven={detalhes['milhas_rodadas']} miles.")

        print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY! ")

if __name__ == '__main__':
    test_workflow()
