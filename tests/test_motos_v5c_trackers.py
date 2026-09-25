import os
import sys
import io
import json
from datetime import datetime

# Set root dir in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import app
from database import db, Motorcycle, MotorcycleV5C, MotorcycleTracker, User, MotoStatus
from cleanup_uploads import collect_valid_files

def test_v5c_and_trackers():
    print("=== STARTING V5C AND TRACKERS TEST ===")
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

        # 1. Setup test motorbike
        test_placa = "V5C_TEST_MOTO"
        moto = Motorcycle.query.get(test_placa)
        if not moto:
            moto = Motorcycle(
                placa=test_placa,
                modelo="Honda Forza 300",
                cor="Blue",
                milhagem_atual=12000,
                status=MotoStatus.AVAILABLE.value
            )
            db.session.add(moto)
        else:
            # Clean any old test records for this moto
            MotorcycleV5C.query.filter_by(placa=test_placa).delete()
            MotorcycleTracker.query.filter_by(placa=test_placa).delete()
        db.session.commit()

        # Authenticate admin session
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin_user.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

        # 2. Test GET /api/motos/<placa>/detalhes (empty state)
        res = client.get(f"/api/motos/{test_placa}/detalhes")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.get_json()
        assert data['placa'] == test_placa
        assert len(data['v5c_arquivos']) == 0
        assert len(data['trackers']) == 0
        print("✓ Initial details endpoint returned empty V5C and Trackers as expected")

        # 3. Test POST /api/motos/<placa>/v5c with image and PDF
        dummy_img_bytes = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00' + b'\x00' * 500
        dummy_pdf_bytes = b'%PDF-1.4\n%V5C DVLA registration certificate test content\n%%EOF'

        data_upload = {
            'v5c_arquivos': [
                (io.BytesIO(dummy_img_bytes), 'v5c_page1.jpg'),
                (io.BytesIO(dummy_pdf_bytes), 'v5c_complete.pdf')
            ]
        }
        res = client.post(f"/api/motos/{test_placa}/v5c", data=data_upload, content_type='multipart/form-data')
        assert res.status_code == 201, f"V5C upload failed: {res.data.decode()}"
        res_json = res.get_json()
        assert len(res_json['v5c_arquivos']) == 2
        print(f"✓ Uploaded 2 V5C documents: {[s['nome_original'] for s in res_json['v5c_arquivos']]}")

        # Verify in DB and file existence
        v5c_records = MotorcycleV5C.query.filter_by(placa=test_placa).all()
        assert len(v5c_records) == 2
        v5c_ids = [v.id for v in v5c_records]
        pdf_rec = next(v for v in v5c_records if v.tipo_arquivo == 'pdf')
        img_rec = next(v for v in v5c_records if v.tipo_arquivo == 'image')
        assert os.path.exists(os.path.join(BASE_DIR, pdf_rec.url_arquivo.lstrip('/')))
        assert os.path.exists(os.path.join(BASE_DIR, img_rec.url_arquivo.lstrip('/')))
        print("✓ V5C records and physical files verified on disk")

        # 4. Check details endpoint reflects V5C
        res = client.get(f"/api/motos/{test_placa}/detalhes")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data['v5c_arquivos']) == 2
        print("✓ Moto details endpoint returned 2 V5C records")

        # 5. Check /api/motos list endpoint has v5c_count
        res = client.get(f"/api/motos?search={test_placa}")
        assert res.status_code == 200
        data = res.get_json()
        moto_item = next(m for m in data['itens'] if m['placa'] == test_placa)
        assert moto_item['v5c_count'] == 2
        assert moto_item['trackers_count'] == 0
        print("✓ Motorbike list API correctly aggregates v5c_count=2, trackers_count=0")

        # 6. Test POST /api/motos/<placa>/trackers - Add Company Tracker with photo
        tracker_img_bytes = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00' + b'\x01' * 500
        tracker_payload = {
            'numero': 'FF-TRK-987654321',
            'tipo_propriedade': 'Company',
            'observacoes': 'Hardwired under rear seat, FF Motors corporate tracker.',
            'fotos': [
                (io.BytesIO(tracker_img_bytes), 'serial_sticker.jpg')
            ]
        }
        res = client.post(f"/api/motos/{test_placa}/trackers", data=tracker_payload, content_type='multipart/form-data')
        assert res.status_code == 201, f"Adding tracker failed: {res.data.decode()}"
        tracker1_data = res.get_json()['tracker']
        tracker1_id = tracker1_data['id']
        assert tracker1_data['numero'] == 'FF-TRK-987654321'
        assert tracker1_data['tipo_propriedade'] == 'Company'
        assert len(tracker1_data['fotos']) == 1
        t1_photo_path = os.path.join(BASE_DIR, tracker1_data['fotos'][0].lstrip('/'))
        assert os.path.exists(t1_photo_path)
        print(f"✓ Company tracker added with photo (ID: {tracker1_id})")

        # 7. Test POST /api/motos/<placa>/trackers - Add Customer Tracker without photos
        tracker_payload2 = {
            'numero': 'CUST-MONIMOTO-555',
            'tipo_propriedade': 'Customer',
            'observacoes': 'Customer private battery tracker placed in battery box.'
        }
        res = client.post(f"/api/motos/{test_placa}/trackers", data=tracker_payload2, content_type='multipart/form-data')
        assert res.status_code == 201
        tracker2_data = res.get_json()['tracker']
        tracker2_id = tracker2_data['id']
        print(f"✓ Customer tracker added (ID: {tracker2_id})")

        # 7b. Test duplicate tracker rejection across motorbikes
        test_placa_2 = "TRK_DUP_MOTO"
        moto_2 = db.session.get(Motorcycle, test_placa_2)
        if not moto_2:
            moto_2 = Motorcycle(
                placa=test_placa_2,
                modelo="Yamaha NMAX 125",
                cor="Black",
                milhagem_atual=5000,
                status=MotoStatus.AVAILABLE.value
            )
            db.session.add(moto_2)
            db.session.commit()
            
        dup_payload = {
            'numero': 'FF-TRK-987654321', # same as tracker 1 on test_placa
            'tipo_propriedade': 'Company'
        }
        res_dup = client.post(f"/api/motos/{test_placa_2}/trackers", data=dup_payload, content_type='multipart/form-data')
        assert res_dup.status_code == 400
        dup_json = res_dup.get_json()
        assert test_placa in (dup_json.get('erro') or dup_json.get('error'))
        print(f"✓ Duplicate tracker across motorbikes successfully blocked! Informed plate: {test_placa}")

        # 7c. Test duplicate tracker rejection on the same motorbike
        res_dup_same = client.post(f"/api/motos/{test_placa}/trackers", data=dup_payload, content_type='multipart/form-data')
        assert res_dup_same.status_code == 400
        print(f"✓ Duplicate tracker on the same motorbike successfully blocked!")

        # 8. Check details endpoint reflects both trackers
        res = client.get(f"/api/motos/{test_placa}/detalhes")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data['trackers']) == 2
        print("✓ Moto details endpoint returned 2 Trackers")

        # 9. Check /api/motos list endpoint has trackers_count and summary
        res = client.get(f"/api/motos?search={test_placa}")
        assert res.status_code == 200
        data = res.get_json()
        moto_item = next(m for m in data['itens'] if m['placa'] == test_placa)
        assert moto_item['trackers_count'] == 2
        assert len(moto_item['trackers_summary']) == 2
        print("✓ Motorbike list API correctly aggregates trackers_count=2 and trackers_summary")

        # 10. Check cleanup_uploads protects both V5C and Tracker photos
        valid_files = collect_valid_files()
        assert pdf_rec.url_arquivo.replace('/static/uploads/', '') in valid_files
        assert img_rec.url_arquivo.replace('/static/uploads/', '') in valid_files
        assert tracker1_data['fotos'][0].replace('/static/uploads/', '') in valid_files
        print("✓ cleanup_uploads whitelist successfully protects V5C and Tracker photos")

        # 11. Test DELETE /api/motos/<placa>/trackers/<tracker_id> - Remove tracker
        res = client.delete(f"/api/motos/{test_placa}/trackers/{tracker1_id}")
        assert res.status_code == 200, f"Delete tracker failed: {res.data.decode()}"
        # Verify tracker1 is gone from DB
        assert MotorcycleTracker.query.get(tracker1_id) is None
        # Verify tracker1 photo deleted from disk
        assert not os.path.exists(t1_photo_path)
        print("✓ Successfully removed Company tracker and verified photo deleted from disk")

        # 12. Test DELETE /api/motos/<placa>/v5c/<v5c_id> - Remove V5C document
        pdf_disk_path = os.path.join(BASE_DIR, pdf_rec.url_arquivo.lstrip('/'))
        res = client.delete(f"/api/motos/{test_placa}/v5c/{pdf_rec.id}")
        assert res.status_code == 200, f"Delete V5C failed: {res.data.decode()}"
        # Verify V5C is gone from DB
        assert MotorcycleV5C.query.get(pdf_rec.id) is None
        # Verify physical PDF was deleted
        assert not os.path.exists(pdf_disk_path)
        print("✓ Successfully removed V5C document and verified physical file deleted from disk")

        # 13. Verify final counts on details endpoint
        res = client.get(f"/api/motos/{test_placa}/detalhes")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data['v5c_arquivos']) == 1
        assert len(data['trackers']) == 1
        assert data['trackers'][0]['id'] == tracker2_id
        print("✓ Moto details endpoint correctly shows 1 remaining V5C and 1 remaining Tracker")

        # 14. Test GET /api/contratos/<id> returns v5c_count and trackers_count for vehicle card shortcut
        from database import Contract, ContractStatus
        test_contract = Contract(
            id_cliente=1,
            placa=test_placa,
            status=ContractStatus.ATIVO.value
        )
        db.session.add(test_contract)
        db.session.commit()

        res_c = client.get(f"/api/contratos/{test_contract.id}")
        assert res_c.status_code == 200
        c_data = res_c.get_json()
        assert c_data['v5c_count'] == 1
        assert c_data['trackers_count'] == 1
        assert len(c_data['trackers_summary']) == 1
        print("✓ Contract details API (/api/contratos/<id>) correctly provides v5c_count and trackers_count for Vehicle Card shortcuts")

        db.session.delete(test_contract)
        db.session.commit()

        # Clean up remaining test records
        client.delete(f"/api/motos/{test_placa}/trackers/{tracker2_id}")
        client.delete(f"/api/motos/{test_placa}/v5c/{img_rec.id}")
        db.session.delete(moto)
        if moto_2:
            db.session.delete(moto_2)
        db.session.commit()
        print("✓ Cleaned up test data cleanly")

    print("=== ALL V5C AND TRACKERS TESTS PASSED SUCCESSFULLY! ===")

if __name__ == '__main__':
    test_v5c_and_trackers()
