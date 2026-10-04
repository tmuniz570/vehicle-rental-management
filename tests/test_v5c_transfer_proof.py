import os
import sys
import io
import json
from datetime import datetime

# Set root dir in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import app
from database import db, Motorcycle, MotorcycleV5C, User, Client, Contract, ContractType, ContractStatus, MotoStatus, AuditLog

def run_v5c_transfer_proof_tests():
    print("=== STARTING V5C & TRANSFER PROOF SPECIFICATION TESTS ===")
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        client = app.test_client()

        # 0. Setup admin user
        admin = User.query.filter_by(email="admin_v5c_test@ffmotors.co.uk").first()
        if not admin:
            admin = User(
                nome="Admin V5C Test",
                email="admin_v5c_test@ffmotors.co.uk",
                is_admin=True,
                perm_alugueis=True,
                perm_claims=True,
                ativo=True
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()

        # 1. Setup test customer
        cust = Client.query.filter_by(nome="Customer V5C Test").first()
        if not cust:
            cust = Client(nome="Customer V5C Test", telefone="07123456789")
            db.session.add(cust)
            db.session.commit()

        # 2. Setup test motorbike
        test_placa = "SLIP_TEST_01"
        moto = db.session.get(Motorcycle, test_placa)
        if not moto:
            moto = Motorcycle(
                placa=test_placa,
                modelo="Yamaha NMAX 125",
                cor="Black",
                milhagem_atual=5000,
                status=MotoStatus.AVAILABLE.value
            )
            db.session.add(moto)
        else:
            MotorcycleV5C.query.filter_by(placa=test_placa).delete()
        db.session.commit()

        # Setup test purchase contract with seller signature
        test_contract = Contract(
            id_cliente=cust.id,
            placa=test_placa,
            tipo_contrato=ContractType.PURCHASE.value,
            status=ContractStatus.ATIVO.value,
            valor_compra_veiculo=1500.0,
            assinatura_cliente_inicial='signed_seller.png',
            criado_por_nome=admin.nome
        )
        db.session.add(test_contract)
        db.session.commit()
        contract_id = test_contract.id

        # Authenticate admin session
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

        # Step 1: Initial state before any upload
        res_motos = client.get(f"/api/motos?search={test_placa}&status=all")
        assert res_motos.status_code == 200
        itens = res_motos.get_json()['itens']
        assert len(itens) >= 1
        item_0 = next(i for i in itens if i['placa'] == test_placa)
        assert item_0['v5c_count'] == 0
        assert item_0['transfer_proof_count'] == 0
        assert item_0['has_v5c'] is False
        assert item_0['has_transfer_proof'] is False

        # Dashboard alert check: bike is missing V5C
        res_dash = client.get("/api/dashboard")
        assert res_dash.status_code == 200
        dash_data = res_dash.get_json()
        missing_placas = [m['placa'] for m in dash_data.get('motos_sem_v5c', [])]
        assert test_placa in missing_placas
        missing_obj = next(m for m in dash_data['motos_sem_v5c'] if m['placa'] == test_placa)
        assert missing_obj['has_transfer_proof'] is False
        print("✓ Initial state: Motorbike correctly flagged as missing V5C with no slip")

        # Step 2: Upload provisional Transfer Slip
        dummy_slip = (io.BytesIO(b"%PDF-1.4 dummy slip"), "dvla_new_keeper_slip.pdf")
        res_upload_slip = client.post(
            f"/api/motos/{test_placa}/v5c",
            data={
                "categoria_doc": "transfer_proof",
                "v5c_arquivos": [dummy_slip]
            },
            content_type="multipart/form-data"
        )
        assert res_upload_slip.status_code == 201, res_upload_slip.get_data(as_text=True)
        slip_res_json = res_upload_slip.get_json()
        assert len(slip_res_json['v5c_arquivos']) == 1
        slip_record_id = slip_res_json['v5c_arquivos'][0]['id']
        slip_filename = slip_res_json['v5c_arquivos'][0]['nome_original']
        assert "dvla_new_keeper_slip.pdf" in slip_filename
        print("✓ Uploaded Transfer Proof document successfully")

        # Verify database record
        slip_db = MotorcycleV5C.query.get(slip_record_id)
        assert slip_db is not None
        assert slip_db.categoria_doc == 'transfer_proof'
        assert slip_db.tipo_arquivo == 'pdf'
        assert "transfer_slip_" in slip_db.url_arquivo
        assert os.path.exists(os.path.join(BASE_DIR, slip_db.url_arquivo.lstrip('/')))
        print("✓ Verified Transfer Proof saved on disk with prefix and categoria_doc='transfer_proof'")

        # Step 3: Verify details endpoint
        res_detalhes = client.get(f"/api/motos/{test_placa}/detalhes")
        assert res_detalhes.status_code == 200
        detalhes_data = res_detalhes.get_json()
        assert detalhes_data['v5c_count'] == 0, f"Expected 0 official V5C, got {detalhes_data['v5c_count']}"
        assert detalhes_data['transfer_proof_count'] == 1, f"Expected 1 transfer proof, got {detalhes_data['transfer_proof_count']}"
        assert detalhes_data['has_v5c'] is False
        assert detalhes_data['has_transfer_proof'] is True
        assert len(detalhes_data['v5c_arquivos']) == 1
        assert detalhes_data['v5c_arquivos'][0]['categoria_doc'] == 'transfer_proof'
        print("✓ Moto details API correctly segregates official V5C (0) and Transfer Proof (1)")

        # Step 4: CRITICAL REQUIREMENT - Missing V5C alert MUST REMAIN ACTIVE!
        res_dash2 = client.get("/api/dashboard")
        dash_data2 = res_dash2.get_json()
        missing_placas2 = [m['placa'] for m in dash_data2.get('motos_sem_v5c', [])]
        assert test_placa in missing_placas2, "ALERT BUG: Transfer slip deactivated missing V5C alert!"
        missing_obj2 = next(m for m in dash_data2['motos_sem_v5c'] if m['placa'] == test_placa)
        assert missing_obj2['has_transfer_proof'] is True
        print("✓ CRITICAL REQUIREMENT VERIFIED: Missing V5C alert remains active in Dashboard with has_transfer_proof=True")

        # Step 5: Verify fleet filters
        res_filter_missing = client.get(f"/api/motos?v5c=missing&search={test_placa}")
        assert any(i['placa'] == test_placa for i in res_filter_missing.get_json()['itens'])

        res_filter_awaiting = client.get(f"/api/motos?v5c=awaiting&search={test_placa}")
        assert any(i['placa'] == test_placa for i in res_filter_awaiting.get_json()['itens'])

        res_filter_no_slip = client.get(f"/api/motos?v5c=no_slip&search={test_placa}")
        assert not any(i['placa'] == test_placa for i in res_filter_no_slip.get_json()['itens'])
        print("✓ Fleet filters (v5c=missing, awaiting, no_slip) work accurately")

        # Step 6: Verify Purchase Contract is STILL Active (not completed because only slip is attached)
        contract_db = Contract.query.get(contract_id)
        assert contract_db.status == ContractStatus.ATIVO.value
        res_c_det = client.get(f"/api/contratos/{contract_id}")
        c_det_json = res_c_det.get_json()
        assert c_det_json['needs_v5c'] is True
        assert c_det_json['tem_v5c'] is False
        assert c_det_json['tem_transfer_proof'] is True
        assert c_det_json['v5c_count'] == 0
        assert c_det_json['transfer_proof_count'] == 1
        print("✓ Purchase Contract remains ACTIVE and flags needs_v5c=True with tem_transfer_proof=True")

        # Step 7: Upload Official V5C Logbook
        dummy_v5c_page = (io.BytesIO(b"dummy official v5c image bytes"), "v5c_logbook_page1.jpg")
        res_upload_v5c = client.post(
            f"/api/motos/{test_placa}/v5c",
            data={
                "categoria_doc": "v5c",
                "v5c_arquivos": [dummy_v5c_page]
            },
            content_type="multipart/form-data"
        )
        assert res_upload_v5c.status_code == 201
        v5c_res_json = res_upload_v5c.get_json()
        v5c_record_id = v5c_res_json['v5c_arquivos'][0]['id']
        print("✓ Uploaded Official V5C document successfully")

        # Verify database record
        v5c_db = MotorcycleV5C.query.get(v5c_record_id)
        assert v5c_db.categoria_doc == 'v5c'
        assert "v5c_" in v5c_db.url_arquivo

        # Step 8: Verify Purchase Contract automatically completed now that official V5C is present!
        db.session.expire_all()
        contract_db_after = Contract.query.get(contract_id)
        assert contract_db_after.status == ContractStatus.COMPLETED.value
        print("✓ Purchase Contract automatically marked COMPLETED upon official V5C upload")

        # Step 9: Verify bike is cleared from Dashboard Missing V5C alert
        res_dash3 = client.get("/api/dashboard")
        missing_placas3 = [m['placa'] for m in res_dash3.get_json().get('motos_sem_v5c', [])]
        assert test_placa not in missing_placas3
        print("✓ Missing V5C alert cleared now that official V5C is present")

        # Step 10: Delete official V5C - verify contract re-syncs to ACTIVE
        res_del_v5c = client.delete(f"/api/motos/{test_placa}/v5c/{v5c_record_id}")
        assert res_del_v5c.status_code == 200
        db.session.expire_all()
        contract_db_resync = Contract.query.get(contract_id)
        assert contract_db_resync.status == ContractStatus.ACTIVE.value
        print("✓ Deleting official V5C re-synced purchase contract back to ACTIVE")

        # Step 11: Clean up test documents and records
        res_del_slip = client.delete(f"/api/motos/{test_placa}/v5c/{slip_record_id}")
        assert res_del_slip.status_code == 200
        assert not os.path.exists(os.path.join(BASE_DIR, slip_db.url_arquivo.lstrip('/')))
        print("✓ Deleting transfer slip removed physical file from disk")

        Contract.query.filter_by(placa=test_placa).delete()
        MotorcycleV5C.query.filter_by(placa=test_placa).delete()
        db.session.commit()

        Motorcycle.query.filter_by(placa=test_placa).delete()
        Client.query.filter_by(id=cust.id).delete()
        User.query.filter_by(id=admin.id).delete()
        db.session.commit()
        print("✓ Cleaned up test database entities")

    print("=== ALL V5C & TRANSFER PROOF SPECIFICATION TESTS PASSED SUCCESSFULLY! ===")


def run_repurchase_cycle_and_immunity_tests():
    print("\n=== STARTING REPURCHASE CYCLE SCOPING & HISTORICAL IMMUNITY TESTS ===")
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        client = app.test_client()

        # Setup admin
        admin = User.query.filter_by(email="admin_rebuy_test@ffmotors.co.uk").first()
        if not admin:
            admin = User(
                nome="Admin Rebuy Test",
                email="admin_rebuy_test@ffmotors.co.uk",
                is_admin=True,
                perm_alugueis=True,
                perm_claims=True,
                ativo=True
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()

        # Setup customer
        cust = Client.query.filter_by(nome="Customer Rebuy Test").first()
        if not cust:
            cust = Client(nome="Customer Rebuy Test", telefone="07999888777")
            db.session.add(cust)
            db.session.commit()

        # Setup bike
        rebuy_placa = "REBUY_TEST_99"
        moto = db.session.get(Motorcycle, rebuy_placa)
        if not moto:
            moto = Motorcycle(
                placa=rebuy_placa,
                modelo="Honda PCX 125",
                cor="White",
                milhagem_atual=12000,
                status=MotoStatus.AVAILABLE.value
            )
            db.session.add(moto)
        else:
            Contract.query.filter_by(placa=rebuy_placa).delete()
            MotorcycleV5C.query.filter_by(placa=rebuy_placa).delete()
        db.session.commit()

        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

        # Phase 1: First Purchase in the past (Contract #1)
        contract_1 = Contract(
            id_cliente=cust.id,
            placa=rebuy_placa,
            tipo_contrato=ContractType.PURCHASE.value,
            status=ContractStatus.ATIVO.value,
            valor_compra_veiculo=1200.0,
            assinatura_cliente_inicial='signed_seller_1.png',
            criado_por_nome=admin.nome
        )
        db.session.add(contract_1)
        db.session.commit()
        c1_id = contract_1.id

        # Upload V5C for Contract #1 explicitly linked
        dummy_v5c_1 = (io.BytesIO(b"v5c document 1 bytes"), "v5c_cycle_1.jpg")
        res_up_1 = client.post(
            f"/api/motos/{rebuy_placa}/v5c",
            data={
                "categoria_doc": "v5c",
                "id_contrato": c1_id,
                "v5c_arquivos": [dummy_v5c_1]
            },
            content_type="multipart/form-data"
        )
        assert res_up_1.status_code == 201
        v5c_1_id = res_up_1.get_json()['v5c_arquivos'][0]['id']

        db.session.expire_all()
        c1_db = Contract.query.get(c1_id)
        assert c1_db.status == ContractStatus.COMPLETED.value
        print(f"✓ Phase 1: Contract #{c1_id} (Purchase #1) is COMPLETED with V5C #{v5c_1_id}")

        # Phase 2: Bike is Sold later (Contract #2)
        contract_2 = Contract(
            id_cliente=cust.id,
            placa=rebuy_placa,
            tipo_contrato=ContractType.SALE_FULL.value,
            status=ContractStatus.COMPLETED.value,
            valor_venda_veiculo=1600.0,
            assinatura_cliente_inicial='signed_buyer.png',
            criado_por_nome=admin.nome
        )
        db.session.add(contract_2)
        db.session.commit()
        c2_id = contract_2.id
        print(f"✓ Phase 2: Contract #{c2_id} (Sale) completed. Bike was with another owner.")

        # Phase 3: We buy the bike back! (Contract #3)
        contract_3 = Contract(
            id_cliente=cust.id,
            placa=rebuy_placa,
            tipo_contrato=ContractType.PURCHASE.value,
            status=ContractStatus.ATIVO.value,
            valor_compra_veiculo=1400.0,
            assinatura_cliente_inicial='signed_seller_3.png',
            criado_por_nome=admin.nome
        )
        db.session.add(contract_3)
        db.session.commit()
        c3_id = contract_3.id
        print(f"✓ Phase 3: Contract #{c3_id} (Purchase #2 / Buyback) created with seller signature")

        # Crucial Verification 1: Contract #3 MUST NOT steal V5C #1 from Contract #1!
        res_c3 = client.get(f"/api/contratos/{c3_id}")
        assert res_c3.status_code == 200
        c3_data = res_c3.get_json()
        assert c3_data['needs_v5c'] is True, "Cycle scoping failure: Contract #3 reused old V5C #1!"
        assert c3_data['tem_v5c'] is False
        assert c3_data['tem_transfer_proof'] is False
        assert c3_data['v5c_count'] == 0
        print("✓ Verified Contract #3 isolates cycle: does not count old historical V5C #1")

        # Crucial Verification 2: Contract #3 MUST appear in filter status=pending_v5c and in Dashboard alerts!
        res_filter_p3 = client.get('/api/contratos?status=pending_v5c')
        assert res_filter_p3.status_code == 200
        p3_pending_ids = [it['id'] for it in res_filter_p3.get_json()['itens']]
        assert c3_id in p3_pending_ids, f"Contract #{c3_id} was NOT found in status=pending_v5c filter: {p3_pending_ids}"
        assert res_filter_p3.get_json()['kpis']['pending_v5c'] >= 1
        print(f"✓ Confirmed: Repurchase Contract #{c3_id} appears under status=pending_v5c filter and KPI!")

        res_dash_p3 = client.get('/api/dashboard')
        assert res_dash_p3.status_code == 200
        dash_p3_json = res_dash_p3.get_json()
        dash_p3_cp_ids = [cp['id'] for cp in dash_p3_json.get('compras_pendentes_v5c', [])]
        assert c3_id in dash_p3_cp_ids, f"Contract #{c3_id} was NOT found in dashboard compras_pendentes_v5c: {dash_p3_cp_ids}"
        dash_p3_motos = [m['placa'] for m in dash_p3_json.get('motos_sem_v5c', [])]
        assert rebuy_placa in dash_p3_motos, f"Repurchased bike {rebuy_placa} was NOT found in dashboard motos_sem_v5c: {dash_p3_motos}"
        print(f"✓ Confirmed: Repurchase Contract #{c3_id} and bike {rebuy_placa} appear in Dashboard alerts!")

        # Phase 4: Upload provisional Transfer Slip for the buyback (Contract #3)
        dummy_slip_3 = (io.BytesIO(b"new transfer slip bytes"), "slip_repurchase.pdf")
        res_up_slip3 = client.post(
            f"/api/motos/{rebuy_placa}/v5c",
            data={
                "categoria_doc": "transfer_proof",
                "id_contrato": c3_id,
                "v5c_arquivos": [dummy_slip_3]
            },
            content_type="multipart/form-data"
        )
        assert res_up_slip3.status_code == 201
        slip_3_id = res_up_slip3.get_json()['v5c_arquivos'][0]['id']

        db.session.expire_all()
        c3_db = Contract.query.get(c3_id)
        assert c3_db.status == ContractStatus.ATIVO.value, "Transfer slip must keep contract Active until V5C arrives"
        res_c3_after_slip = client.get(f"/api/contratos/{c3_id}").get_json()
        assert res_c3_after_slip['needs_v5c'] is True
        assert res_c3_after_slip['tem_transfer_proof'] is True
        assert res_c3_after_slip['transfer_proof_count'] == 1
        print("✓ Phase 4: Attached transfer slip to Contract #3; status remains ACTIVE (awaiting V5C)")

        # Verify it STILL appears in pending_v5c filter and Dashboard alerts (with slip OK indicator)
        res_filter_p4 = client.get('/api/contratos?status=pending_v5c')
        assert c3_id in [it['id'] for it in res_filter_p4.get_json()['itens']]
        res_dash_p4 = client.get('/api/dashboard')
        dash_p4_json = res_dash_p4.get_json()
        cp_p4_item = next(cp for cp in dash_p4_json.get('compras_pendentes_v5c', []) if cp['id'] == c3_id)
        assert cp_p4_item['has_transfer_proof'] is True
        moto_p4_item = next(m for m in dash_p4_json.get('motos_sem_v5c', []) if m['placa'] == rebuy_placa)
        assert moto_p4_item['has_transfer_proof'] is True
        print(f"✓ Confirmed: Repurchase Contract #{c3_id} remains in alerts with has_transfer_proof=True")

        # Phase 5: Official V5C arrives for the repurchase
        dummy_v5c_3 = (io.BytesIO(b"v5c document 2 bytes"), "v5c_cycle_2.pdf")
        res_up_v5c3 = client.post(
            f"/api/motos/{rebuy_placa}/v5c",
            data={
                "categoria_doc": "v5c",
                "id_contrato": c3_id,
                "v5c_arquivos": [dummy_v5c_3]
            },
            content_type="multipart/form-data"
        )
        assert res_up_v5c3.status_code == 201
        v5c_3_id = res_up_v5c3.get_json()['v5c_arquivos'][0]['id']

        db.session.expire_all()
        c3_db_after_v5c = Contract.query.get(c3_id)
        assert c3_db_after_v5c.status == ContractStatus.COMPLETED.value
        print(f"✓ Phase 5: Contract #{c3_id} automatically completed upon arrival of its own V5C #{v5c_3_id}")

        # Phase 6: THE CORE USER QUESTION / HISTORICAL IMMUNITY TEST
        # User removes V5C #3 (or has to modify it). Contract #3 will return to ACTIVE.
        # But Contract #1 (historical) MUST REMAIN COMPLETED!
        res_del_v5c3 = client.delete(f"/api/motos/{rebuy_placa}/v5c/{v5c_3_id}")
        assert res_del_v5c3.status_code == 200

        db.session.expire_all()
        c3_db_reopen = Contract.query.get(c3_id)
        assert c3_db_reopen.status == ContractStatus.ACTIVE.value
        print(f"✓ Contract #{c3_id} reopened to ACTIVE as expected since its current V5C was removed")

        c1_db_check = Contract.query.get(c1_id)
        assert c1_db_check.status == ContractStatus.COMPLETED.value, \
            f"CRITICAL IMMUNITY BREACH: Historical Contract #{c1_id} was reopened to {c1_db_check.status}!"
        print(f"✓ CRITICAL HISTORICAL IMMUNITY VERIFIED: Contract #{c1_id} stays 100% COMPLETED and immune!")

        # Also verify if V5C #1 itself was ever deleted, Contract #1 stays completed because it's a closed historical contract
        res_del_v5c1 = client.delete(f"/api/motos/{rebuy_placa}/v5c/{v5c_1_id}")
        assert res_del_v5c1.status_code == 200

        db.session.expire_all()
        c1_db_still_completed = Contract.query.get(c1_id)
        assert c1_db_still_completed.status == ContractStatus.COMPLETED.value, \
            "CRITICAL: Historical contract was reopened after document deletion!"
        print(f"✓ Even after deleting V5C #1, historical Contract #{c1_id} is permanently immune from reopening")

        # Cleanup
        client.delete(f"/api/motos/{rebuy_placa}/v5c/{slip_3_id}")
        Contract.query.filter_by(placa=rebuy_placa).delete()
        MotorcycleV5C.query.filter_by(placa=rebuy_placa).delete()
        Motorcycle.query.filter_by(placa=rebuy_placa).delete()
        Client.query.filter_by(id=cust.id).delete()
        User.query.filter_by(id=admin.id).delete()
        db.session.commit()
        print("✓ Cleaned up repurchase test entities")

    print("=== REPURCHASE CYCLE SCOPING & HISTORICAL IMMUNITY TESTS PASSED 100%! ===")


if __name__ == '__main__':
    run_v5c_transfer_proof_tests()
    run_repurchase_cycle_and_immunity_tests()

