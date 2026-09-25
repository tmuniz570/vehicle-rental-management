import os
import sys
import io
import time

sys.path.insert(0, r"c:\Users\tmuni\Downloads\FF Motors APP")

from app import app
from database import db, Motorcycle, Client, Contract, User

def test_contract_immutability():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        # 1. Setup admin user session
        with app.app_context():
            u = User.query.first()
            if not u:
                u = User(nome='Admin', email='admin@test.com', role='admin', is_admin=True)
                u.set_password('Admin@123')
                db.session.add(u)
                db.session.commit()
            u_id = str(u.id)

        with client.session_transaction() as sess:
            sess['_user_id'] = u_id
            sess['_fresh'] = True
            sess['last_activity'] = time.time()
            sess['_csrf_token'] = 'test_token_immutability'

        # 2. Register Client with original details
        ts = int(time.time())
        original_nome = f"Original Customer {ts}"
        original_tel = "07111223344"
        original_email = f"customer_{ts}@test.co.uk"
        original_end = "42 High Street, Harborne, Birmingham"
        
        with app.app_context():
            cust = Client(
                nome=original_nome,
                telefone=original_tel,
                email=original_email,
                endereco=original_end
            )
            db.session.add(cust)
            db.session.commit()
            cust_id = cust.id

        # 3. Register Motorcycle with original details
        test_plate = f"FR{ts % 10000:04d}"
        original_modelo = "Honda PCX 125 Immutability Edition"
        original_cor = "Metallic Grey"
        
        with app.app_context():
            moto = Motorcycle(
                placa=test_plate,
                modelo=original_modelo,
                cor=original_cor,
                status='Available',
                milhagem_atual=8400
            )
            db.session.add(moto)
            db.session.commit()

        # 4. Generate Contract (User clicks 'Create Contract')
        print("Creating contract...")
        res = client.post('/api/contratos', data={
            'id_cliente': cust_id,
            'placa': test_plate,
            'valor_aluguel_semanal': 220.00,
            'valor_deposito': 450.00,
            'milhagem_inicial': 8400,
            'dia_pagamento_semanal': 2, # Wednesday
            'fotos': (io.BytesIO(b"checkout image"), 'checkout.jpg'),
            'seguro': (io.BytesIO(b"insurance pdf"), 'insurance.pdf')
        }, content_type='multipart/form-data', headers={'X-CSRFToken': 'test_token_immutability'})
        
        assert res.status_code in (200, 201), f"Creation failed: {res.status_code}, {res.data}"
        contrato_id = res.get_json()['id']
        print(f"Contract #{contrato_id} successfully created!")

        # 5. Verify snapshot in database
        with app.app_context():
            ct = db.session.get(Contract, contrato_id)
            assert ct.cliente_nome == original_nome, f"Expected {original_nome}, got {ct.cliente_nome}"
            assert ct.cliente_telefone == original_tel
            assert ct.cliente_endereco == original_end
            assert ct.cliente_email == original_email
            assert ct.moto_modelo == original_modelo
            assert ct.moto_cor == original_cor
            assert ct.moto_placa == test_plate
            assert float(ct.valor_deposito) == 450.00
            print(" Snapshot correctly stored in Contract table.")

        # 6. SIMULATE CHANGES TO CLIENT AND MOTORCYCLE IN DATABASE AFTER CONTRACT GENERATION
        print("\nSimulating later edits to the Client and Motorcycle tables...")
        with app.app_context():
            c_edit = db.session.get(Client, cust_id)
            c_edit.nome = "CHANGED NAME - SHOULD NOT AFFECT CONTRACT"
            c_edit.telefone = "07999999999"
            c_edit.endereco = "99 Changed Street, Manchester"
            c_edit.email = f"changed_{ts}@other.com"
            
            m_edit = db.session.get(Motorcycle, test_plate)
            m_edit.modelo = "CHANGED MODEL - YAMAHA TMAX 560"
            m_edit.cor = "Fluorescent Yellow"
            
            db.session.commit()
            print(" Client and Motorcycle records altered in database.")

        # 7. Test /api/contratos/<id> (Detail view)
        # On the contract detail screen, updated customer & bike info is shown so staff has current contact data
        res_detail = client.get(f'/api/contratos/{contrato_id}')
        assert res_detail.status_code == 200
        detail_json = res_detail.get_json()
        
        assert detail_json['cliente'] == "CHANGED NAME - SHOULD NOT AFFECT CONTRACT"
        assert detail_json['telefone'] == "07999999999"
        assert detail_json['endereco'] == "99 Changed Street, Manchester"
        assert detail_json['email'] == f"changed_{ts}@other.com"
        assert detail_json['modelo'] == "CHANGED MODEL - YAMAHA TMAX 560"
        assert detail_json['cor'] == "Fluorescent Yellow"
        
        # Frozen contract snapshot fields preserved for audit
        assert detail_json['snapshot_cliente_nome'] == original_nome
        assert detail_json['snapshot_cliente_telefone'] == original_tel
        assert detail_json['snapshot_cliente_endereco'] == original_end
        assert detail_json['snapshot_cliente_email'] == original_email
        assert detail_json['snapshot_moto_modelo'] == original_modelo
        assert detail_json['snapshot_moto_cor'] == original_cor
        print(" Detail API returned updated live customer/bike data with preserved snapshot fields!")

        # 8. Test /contratos/<id>/imprimir (Print Agreement View)
        # The generated signed agreement is 100% legally immutable!
        res_print = client.get(f'/contratos/{contrato_id}/imprimir')
        assert res_print.status_code == 200
        html = res_print.get_data(as_text=True)
        
        # Verify frozen data is strictly preserved in print view
        assert original_nome in html, f"Print agreement missing frozen name: {original_nome}"
        assert original_tel in html
        assert original_end in html
        assert original_modelo in html
        assert original_cor in html
        assert "£450.00" in html
        assert "£220.00" in html
        assert "Wednesday" in html
        
        # Verify changed data is strictly NOT in the print agreement
        assert "CHANGED NAME" not in html
        assert "07999999999" not in html
        assert "CHANGED MODEL" not in html
        assert "Fluorescent Yellow" not in html
        print(" Print view is 100% immutable and strictly displays frozen contract terms!")

        # 9. Test changing due day does NOT alter the printed contract document
        print("\nTesting changing due day to Friday...")
        res_due = client.put(f'/api/contratos/{contrato_id}/dia-pagamento', json={
            'dia_pagamento_semanal': 4 # Friday
        })
        assert res_due.status_code == 200
        
        # Verify detail view has new due day and original signed day
        res_detail2 = client.get(f'/api/contratos/{contrato_id}')
        d2 = res_detail2.get_json()
        assert d2['dia_pagamento_semanal'] == 4
        assert d2['dia_pagamento_semanal_original'] == 2
        print(" Detail API correctly reflects updated billing schedule (Friday) and original signed day (Wednesday).")
        
        # Verify printed agreement still strictly shows Wednesday!
        res_print2 = client.get(f'/contratos/{contrato_id}/imprimir')
        html2 = res_print2.get_data(as_text=True)
        assert "Wednesday" in html2, "Print agreement should still show originally signed day (Wednesday)"
        assert "Friday" not in html2, "Print agreement must NOT be altered to Friday after being signed!"
        print(" Print view remained strictly unchanged (Wednesday) after billing schedule change!")

        # 10. Test that signatures CAN be added without unfreezing or altering variables
        print("\nTesting signature entry after creation...")
        dummy_sig = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        res_sign = client.post(f'/api/contratos/{contrato_id}/assinar', json={
            'tipo': 'inicial',
            'assinatura': dummy_sig
        }, headers={'X-CSRFToken': 'test_token_immutability'})
        assert res_sign.status_code == 200
        assert res_sign.get_json()['success'] is True
        
        with app.app_context():
            ct_after_sign = db.session.get(Contract, contrato_id)
            assert ct_after_sign.assinatura_cliente_inicial is not None
            assert ct_after_sign.cliente_nome == original_nome
            assert ct_after_sign.moto_modelo == original_modelo
            print(" Signature successfully attached while keeping contract variables 100% frozen!")

        print("\n ALL IMMUTABILITY VERIFICATION CHECKS PASSED!")

if __name__ == '__main__':
    test_contract_immutability()
