import os
import sys
import io
import json
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import app
from database import db, Motorcycle, Client, Contract, Inspection, User, ContractStatus, MotoStatus, init_db

def test_prerelease_compliance():
    print("=== STARTING PRE-RELEASE COMPLIANCE TESTS ===")
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        init_db(app)
        client = app.test_client()

        # 0. Setup admin user
        admin_user = User.query.filter_by(email="admin@ffmotors.co.uk").first()
        if not admin_user:
            admin_user = User(
                nome="Admin Test",
                email="admin@ffmotors.co.uk",
                is_admin=True,
                perm_alugueis=True,
                perm_claims=True,
                ativo=True
            )
            admin_user.set_password("admin123")
            db.session.add(admin_user)
            db.session.commit()

        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin_user.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

        # 1. Setup test customer and motorbike
        test_client_nome = "Test PreDelivery Customer"
        test_placa = "PRERELEASE01"

        cliente = Client.query.filter_by(nome=test_client_nome).first()
        if not cliente:
            cliente = Client(nome=test_client_nome, telefone="07111222333", email="predelivery@test.com")
            db.session.add(cliente)

        moto = Motorcycle.query.filter_by(placa=test_placa).first()
        if not moto:
            moto = Motorcycle(
                placa=test_placa,
                modelo="Yamaha NMAX 125",
                cor="Blue",
                status=MotoStatus.DISPONIVEL,
                milhagem_atual=3000
            )
            db.session.add(moto)
        else:
            moto.status = MotoStatus.DISPONIVEL
            moto.milhagem_atual = 3000

        db.session.commit()

        # 2. Create contract WITHOUT insurance file and WITHOUT checkout inspection photos
        # Simulating multipart form data without 'seguro' file and without 'fotos'
        contract_data = {
            'tipo_contrato': 'Rent',
            'cliente_id': str(cliente.id),
            'moto_placa': test_placa,
            'valor_aluguel_semanal': '95.00',
            'dia_pagamento_semanal': '0',
            'valor_calcao': '250.00',
            'milhagem_inicial': '3000',
            'forma_pagamento_entrada': 'Bank Transfer',
            'observacoes': 'Accessories being fitted in workshop, customer arranging insurance'
        }

        res = client.post('/api/contratos', data=contract_data, content_type='multipart/form-data')
        assert res.status_code == 201, f"Failed to create contract without inspection/insurance: {res.data.decode()}"
        res_json = res.get_json()
        contrato_id = res_json.get('id') or res_json.get('contrato_id')
        print(f"✓ Created contract #{contrato_id} successfully without insurance or inspection photos")

        # 3. Verify contract details via GET /api/contratos/<id>
        res_det = client.get(f'/api/contratos/{contrato_id}')
        assert res_det.status_code == 200
        det_data = res_det.get_json()
        assert det_data['has_checkout_inspection'] is False, "Expected has_checkout_inspection=False"
        assert det_data['has_insurance_doc'] is False, "Expected has_insurance_doc=False"
        assert det_data['is_pre_release_pending'] is True, "Expected is_pre_release_pending=True"
        assert det_data['status_seguro'] == 'Pending'
        print(f"✓ Details API returned has_checkout_inspection=False, has_insurance_doc=False, is_pre_release_pending=True")

        # 4. Verify contracts list with filter=pending_release
        res_list = client.get('/api/contratos?status=pending_release')
        assert res_list.status_code == 200
        list_data = res_list.get_json()
        found_pending = any(c['id'] == contrato_id for c in list_data.get('itens', []))
        assert found_pending, "Contract must appear in GET /api/contratos?status=pending_release"
        print(f"✓ Contract #{contrato_id} correctly returned in pending_release contracts query")

        # 5. Verify Dashboard alerts include this pending release
        res_dash = client.get('/api/dashboard')
        assert res_dash.status_code == 200
        dash_data = res_dash.get_json()
        assert dash_data.get('pendentes_liberacao_count', 0) >= 1
        found_in_dash = any(p['id'] == contrato_id for p in dash_data.get('contratos_pendentes_liberacao', []))
        assert found_in_dash, "Contract must be present in dashboard contratos_pendentes_liberacao"
        print(f"✓ Dashboard reports {dash_data['pendentes_liberacao_count']} pre-delivery pending contracts including #{contrato_id}")

        # 6. Upload insurance certificate via PUT /api/contratos/<id>/seguro
        fake_pdf = (io.BytesIO(b"%PDF-1.4 Fake Insurance Certificate"), "certificate.pdf")
        res_ins = client.put(f'/api/contratos/{contrato_id}/seguro', data={'arquivo': fake_pdf}, content_type='multipart/form-data')
        assert res_ins.status_code == 200, f"Failed to upload insurance: {res_ins.data.decode()}"
        print(f"✓ Uploaded insurance certificate for contract #{contrato_id}")

        # Check details: insurance present, but check-out inspection still pending
        res_det2 = client.get(f'/api/contratos/{contrato_id}')
        det_data2 = res_det2.get_json()
        assert det_data2['has_insurance_doc'] is True
        assert det_data2['has_checkout_inspection'] is False
        assert det_data2['is_pre_release_pending'] is True
        print(f"✓ Contract now has insurance, but is_pre_release_pending remains True (needs inspection)")

        # 7. Record Check-out inspection via POST /api/vistorias
        fake_photo = (io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb"), "checkout.jpg")
        insp_data = {
            'contrato_id': str(contrato_id),
            'tipo': 'Check-out',
            'milhagem': '3050',
            'observacoes': 'Bike accessorised with top box and phone mount, spotless condition',
            'fotos': [fake_photo]
        }
        res_insp = client.post('/api/vistorias', data=insp_data, content_type='multipart/form-data')
        assert res_insp.status_code == 201, f"Failed to register checkout inspection: {res_insp.data.decode()}"
        print(f"✓ Successfully registered Check-out inspection with photos")

        # 8. Check details again: both fulfilled, is_pre_release_pending is now FALSE
        res_det3 = client.get(f'/api/contratos/{contrato_id}')
        det_data3 = res_det3.get_json()
        assert det_data3['has_insurance_doc'] is True
        assert det_data3['has_checkout_inspection'] is True
        assert det_data3['is_pre_release_pending'] is False
        print(f"✓ After both insurance and inspection are recorded, is_pre_release_pending is False!")

        # 9. Verify contract is no longer in pending_release query
        res_list2 = client.get('/api/contratos?status=pending_release')
        list_data2 = res_list2.get_json()
        found_still_pending = any(c['id'] == contrato_id for c in list_data2.get('itens', []))
        assert not found_still_pending, "Contract must NOT appear in pending_release query once compliant"
        print(f"✓ Contract #{contrato_id} is no longer in pending_release filter")

        # 10. Clean up test data
        contrato_obj = db.session.get(Contract, contrato_id)
        if contrato_obj:
            from database import FinancialTransaction
            FinancialTransaction.query.filter_by(id_contrato=contrato_id).delete()
            Inspection.query.filter_by(id_contrato=contrato_id).delete()
            db.session.delete(contrato_obj)
            db.session.commit()
        print("✓ Cleaned up test contract cleanly")

    print("=== ALL PRE-RELEASE COMPLIANCE TESTS PASSED SUCCESSFULLY! ===")

if __name__ == '__main__':
    test_prerelease_compliance()
