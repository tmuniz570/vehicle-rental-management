import os
import sys
import json
from datetime import datetime, date

# Set root dir in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import app
from database import db, Motorcycle, Client, Contract, FinancialTransaction, User, ContractType, MotoStatus, ContractStatus

def test_purchase_system():
    print("=== STARTING VEHICLE PURCHASE CONTRACTS TEST ===")
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
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

        # 1. Setup mock customer (seller) and test bikes
        cust = Client.query.filter_by(email="seller_test@ffmotors.co.uk").first()
        if not cust:
            cust = Client(
                nome="Alex Seller",
                email="seller_test@ffmotors.co.uk",
                telefone="07999888777",
                endereco="45 High Street, Birmingham, B12 0JJ"
            )
            db.session.add(cust)
            db.session.commit()
            
        moto1 = Motorcycle.query.get("TEST_BUY1")
        if not moto1:
            moto1 = Motorcycle(
                placa="TEST_BUY1",
                modelo="Honda Forza 125",
                cor="Silver",
                milhagem_atual=14200,
                status=MotoStatus.AVAILABLE.value
            )
            db.session.add(moto1)
        else:
            moto1.status = MotoStatus.AVAILABLE.value
            moto1.cor = "Silver"
            
        moto2 = Motorcycle.query.get("TEST_BUY2")
        if not moto2:
            moto2 = Motorcycle(
                placa="TEST_BUY2",
                modelo="Yamaha XMAX 300",
                cor="Blue",
                milhagem_atual=0,
                status=MotoStatus.MAINTENANCE.value
            )
            db.session.add(moto2)
        else:
            moto2.status = MotoStatus.MAINTENANCE.value
            
        db.session.commit()
        
        # Authenticate session for admin
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin_user.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()
            
        import io
        dummy_img = (io.BytesIO(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00'), 'test_bike_checkin.jpg')

        # ====================================================================
        # TEST 1: Create Purchase Contract - Destination: Available, Bank Transfer
        # ====================================================================
        print("\n[TEST 1] Testing Purchase contract creation (Target: Available, Bank Transfer)...")
        res1 = client.post('/api/contratos', data={
            'tipo_contrato': 'Purchase',
            'id_cliente': str(cust.id),
            'placa': 'TEST_BUY1',
            'milhagem_inicial': '14200',
            'categoria_historico': 'Cat N',
            'moto_cor': 'Metallic Silver',
            'valor_compra_veiculo': '1850.00',
            'metodo_pagamento_compra': 'Bank Transfer',
            'detalhes_pagamento_compra': 'Faster Payments to Sort Code 12-34-56 Acc 98765432 Ref BUY1',
            'status_moto_destino': 'Available',
            'milhagem_nao_verificada': '0',
            'observacoes': 'Front brake pads worn, otherwise sound runner',
            'fotos': dummy_img
        }, content_type='multipart/form-data')

        assert res1.status_code == 201, f"Expected 201 Created, got {res1.status_code}: {res1.data.decode()}"
        data1 = json.loads(res1.data.decode())
        contract_id1 = data1['id']
        print(f"✓ Created Purchase Contract ID: {contract_id1}")

        # Check contract database record
        c1 = Contract.query.get(contract_id1)
        assert c1.tipo_contrato == ContractType.PURCHASE.value, f"Expected Purchase, got {c1.tipo_contrato}"
        assert float(c1.valor_compra_veiculo) == 1850.00, f"Expected 1850.00, got {c1.valor_compra_veiculo}"
        assert c1.metodo_pagamento_compra == "Bank Transfer"
        assert "Faster Payments" in c1.detalhes_pagamento_compra
        assert c1.categoria_historico == "Cat N"
        assert c1.status_moto_destino == "Available"
        assert c1.milhagem_nao_verificada is False

        # Check bike status and color updated
        m1 = Motorcycle.query.get("TEST_BUY1")
        assert m1.status == MotoStatus.AVAILABLE.value, f"Expected Available, got {m1.status}"
        assert m1.cor == "Metallic Silver", f"Expected Metallic Silver, got {m1.cor}"
        print("✓ Motorbike status set to Available and color updated to 'Metallic Silver'")

        # CRITICAL RULE A1: Check that NO financial transactions (receivables) were generated
        trans1 = FinancialTransaction.query.filter_by(id_contrato=contract_id1).all()
        assert len(trans1) == 0, f"Expected ZERO financial transactions for Purchase, got {len(trans1)}"
        print("✓ Rule A1 VERIFIED: Zero receivable financial transactions generated for Purchase contract")

        # ====================================================================
        # TEST 2: Create Purchase Contract - Destination: Maintenance, Unverified Mileage, Trade-in
        # ====================================================================
        print("\n[TEST 2] Testing Purchase contract (Target: Maintenance, Trade-in, Non-runner / Unverified Mileage)...")
        res2 = client.post('/api/contratos', data={
            'tipo_contrato': 'Purchase',
            'id_cliente': str(cust.id),
            'placa': 'TEST_BUY2',
            'milhagem_inicial': '0',
            'categoria_historico': 'Cat S',
            'moto_cor': 'Deep Blue',
            'valor_compra_veiculo': '900.00',
            'metodo_pagamento_compra': 'Trade-in / Exchange',
            'detalhes_pagamento_compra': 'Part-exchange trade-in allowance towards Honda PCX plate XX24ABC',
            'status_moto_destino': 'Maintenance',
            'milhagem_nao_verificada': '1',
            'observacoes': 'Non-runner engine issue, needs full workshop strip down'
        }, content_type='multipart/form-data')

        assert res2.status_code == 201, f"Expected 201 Created, got {res2.status_code}: {res2.data.decode()}"
        data2 = json.loads(res2.data.decode())
        contract_id2 = data2['id']
        print(f"✓ Created Purchase Contract ID: {contract_id2}")

        c2 = Contract.query.get(contract_id2)
        assert c2.tipo_contrato == ContractType.PURCHASE.value
        assert float(c2.valor_compra_veiculo) == 900.00
        assert c2.metodo_pagamento_compra == "Trade-in / Exchange"
        assert c2.categoria_historico == "Cat S"
        assert c2.status_moto_destino == "Maintenance"
        assert c2.milhagem_nao_verificada is True

        # Check bike status updated to Maintenance
        m2 = Motorcycle.query.get("TEST_BUY2")
        assert m2.status == MotoStatus.MAINTENANCE.value, f"Expected Maintenance, got {m2.status}"
        assert m2.cor == "Deep Blue"
        print("✓ Motorbike status set to Maintenance and unverified mileage recorded")

        assert c1.url_seguro is None, "Purchase contract must have no customer insurance"
        assert c2.url_seguro is None, "Purchase contract must have no customer insurance"

        # ====================================================================
        # TEST 2.1: Purchase bike in RENTED or SOLD status (All bikes eligible)
        # ====================================================================
        print("\n[TEST 2.1] Testing Purchase of bike in RENTED or SOLD status...")
        moto3 = Motorcycle.query.get("TEST_BUY3")
        if not moto3:
            moto3 = Motorcycle(
                placa="TEST_BUY3",
                modelo="Honda SH 125",
                cor="Black",
                milhagem_atual=21000,
                status=MotoStatus.RENTED.value
            )
            db.session.add(moto3)
        else:
            moto3.status = MotoStatus.RENTED.value
        db.session.commit()

        res3 = client.post('/api/contratos', data={
            'tipo_contrato': 'Purchase',
            'id_cliente': str(cust.id),
            'placa': 'TEST_BUY3',
            'milhagem_inicial': '21000',
            'categoria_historico': 'Clear',
            'moto_cor': 'Gloss Black',
            'valor_compra_veiculo': '1200.00',
            'metodo_pagamento_compra': 'Cash',
            'detalhes_pagamento_compra': 'Cash paid in full upon collection',
            'status_moto_destino': 'Pound',
            'milhagem_nao_verificada': '0'
        }, content_type='multipart/form-data')

        assert res3.status_code == 201, f"Expected 201 Created, got {res3.status_code}: {res3.data.decode()}"
        data3 = json.loads(res3.data.decode())
        contract_id3 = data3['id']
        
        m3_after = Motorcycle.query.get("TEST_BUY3")
        assert m3_after.status == MotoStatus.POUND.value, f"Expected Pound after purchase, got {m3_after.status}"
        assert m3_after.cor == "Gloss Black"
        c3 = Contract.query.get(contract_id3)
        assert c3.status_moto_destino == "Pound"
        assert c3.url_seguro is None, "Purchase contract must not require insurance"
        print(f"✓ Created Purchase Contract ID: {contract_id3} for previously Rented bike, now successfully in Pound status")

        # ====================================================================
        # TEST 3: Print Route Rendering
        # ====================================================================
        print("\n[TEST 3] Testing Print Agreement View (/contratos/<id>/imprimir)...")
        res_print1 = client.get(f'/contratos/{contract_id1}/imprimir')
        assert res_print1.status_code == 200, f"Expected 200 OK, got {res_print1.status_code}"
        html1 = res_print1.data.decode('utf-8')

        assert "USED VEHICLE PURCHASE AGREEMENT" in html1
        assert "J&amp;F Motorcycles LTD" in html1 or "J&F Motorcycles LTD" in html1
        assert "109 Windmill Lane, Birmingham, B66 3EW" in html1
        assert "0121 492 0697" in html1
        assert "Alex Seller" in html1
        assert "TEST_BUY1" in html1
        assert "Honda Forza 125" in html1
        assert "Metallic Silver" in html1
        assert "Cat N" in html1
        assert "1,850.00" in html1
        assert "Bank Transfer" in html1
        assert "Faster Payments" in html1
        assert "I the Seller hereby declare and warrant the following:" in html1
        assert "I the Buyer hereby declare the following:" in html1
        assert "Seller's Signature" in html1
        assert "Buyer's Signature" in html1
        assert "signature_fernando.png" in html1, "Fixed shop signature must be included in the purchase agreement!"
        print("✓ Print template renders complete Used Vehicle Purchase Agreement with fixed shop signature (signature_fernando.png)")

        # Test unverified mileage printout on second contract
        res_print2 = client.get(f'/contratos/{contract_id2}/imprimir')
        assert res_print2.status_code == 200
        html2 = res_print2.data.decode('utf-8')
        assert "Unverified (Non-runner)" in html2 or "Unverified" in html2
        print("✓ Unverified mileage correctly rendered on print template")

        # Single page assertion
        assert html1.count('class="agreement-page"') == 1, "Must be a single-page agreement (exactly 1 .agreement-page block)"
        assert "Page 1 of 2" not in html1, "Must not have multiple pages pagination"
        assert "Page 2 of 2" not in html1, "Must not have multiple pages pagination"
        print("✓ Single page agreement structure verified (1 .agreement-page)")

        # Verify contract details page HTML elements
        res_det_view = client.get(f'/contratos/{contract_id1}')
        assert res_det_view.status_code == 200
        html_det_view = res_det_view.data.decode('utf-8')
        assert 'id="card_sig_devolucao"' in html_det_view
        assert 'id="card_financial_statement"' in html_det_view
        assert 'detalhe_contrato.js?v=30' in html_det_view
        print("✓ Contract details HTML contains #card_sig_devolucao, #card_financial_statement and updated cachebuster")

        # ====================================================================
        # TEST 4: Digital Signature & Auto-Completion
        # ====================================================================
        print("\n[TEST 4] Testing digital signature auto-completion for Purchase contract...")
        dummy_sig = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        res_sig = client.post(f'/api/contratos/{contract_id1}/assinar', 
                             data=json.dumps({'tipo': 'inicial', 'assinatura': dummy_sig}),
                             content_type='application/json')
        assert res_sig.status_code == 200, f"Expected 200, got {res_sig.status_code}: {res_sig.data.decode()}"
        
        c1_after = Contract.query.get(contract_id1)
        assert c1_after.status == ContractStatus.COMPLETED.value, f"Expected Completed status after signature, got {c1_after.status}"
        assert c1_after.assinatura_cliente_inicial is not None
        assert c1_after.data_assinatura_inicial is not None
        print(f"✓ Purchase contract status automatically transitioned to '{c1_after.status}' upon signature")

        # ====================================================================
        # TEST 5: API Details and Exemption Checks
        # ====================================================================
        print("\n[TEST 5] Testing Contract Details API & Compliance Exemptions...")
        res_det = client.get(f'/api/contratos/{contract_id1}')
        assert res_det.status_code == 200
        det_json = json.loads(res_det.data.decode())

        assert det_json['tipo_contrato'] == 'Purchase'
        assert det_json['is_pre_release_pending'] is False, "Purchase contracts must NOT require pre-release check!"
        assert det_json['checagem_seguro_devida'] is False, "Purchase contracts must NOT require askMID check!"
        assert float(det_json['valor_compra_veiculo']) == 1850.00
        assert det_json['metodo_pagamento_compra'] == 'Bank Transfer'
        print("✓ Contract details API returns purchase terms and confirms askMID/pre-release exemptions")

        # ====================================================================
        # TEST 6: Contracts Listing Filter
        # ====================================================================
        print("\n[TEST 6] Testing Contracts List API with Purchase filter...")
        res_list = client.get('/api/contratos?tipo=Purchase')
        assert res_list.status_code == 200
        list_json = json.loads(res_list.data.decode())
        found_ids = [it['id'] for it in list_json.get('itens', [])]
        assert contract_id1 in found_ids
        assert contract_id2 in found_ids
        print(f"✓ API /api/contratos?tipo=Purchase returned both contracts: {found_ids}")

        print("\n=======================================================")
        print("🎉 ALL USED VEHICLE PURCHASE AGREEMENT TESTS PASSED 100%!")
        print("=======================================================")

if __name__ == '__main__':
    test_purchase_system()
