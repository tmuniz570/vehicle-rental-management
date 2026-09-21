import os
import sys
import json
from datetime import datetime, date

# Set root dir in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import app
from database import db, Motorcycle, Client, Contract, FinancialTransaction, User, ContractType, TransactionType, MotoStatus, TransactionStatus, ContractStatus

def test_sales_system():
    print("=== STARTING VEHICLE SALE CONTRACTS TEST ===")
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

        # 1. Setup mock customer and bikes
        cust = Client.query.filter_by(email="test_buyer@ffmotors.co.uk").first()
        if not cust:
            cust = Client(
                nome="John Buyer",
                email="test_buyer@ffmotors.co.uk",
                telefone="07123456789",
                endereco="10 Test Street, Birmingham, B1 1AA"
            )
            db.session.add(cust)
            db.session.commit()
            
        moto_full = Motorcycle.query.get("TEST_SALE1")
        if not moto_full:
            moto_full = Motorcycle(
                placa="TEST_SALE1",
                modelo="Honda PCX 125",
                cor="Black",
                milhagem_atual=5400,
                status=MotoStatus.AVAILABLE.value
            )
            db.session.add(moto_full)
        else:
            moto_full.status = MotoStatus.AVAILABLE.value
            
        moto_inst = Motorcycle.query.get("TEST_SALE2")
        if not moto_inst:
            moto_inst = Motorcycle(
                placa="TEST_SALE2",
                modelo="Yamaha NMAX 125",
                cor="Grey",
                milhagem_atual=8200,
                status=MotoStatus.AVAILABLE.value
            )
            db.session.add(moto_inst)
        else:
            moto_inst.status = MotoStatus.AVAILABLE.value
            
        db.session.commit()
        
        # Authenticate session for admin
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin_user.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()
            
        import io
        dummy_img = (io.BytesIO(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00'), 'test_bike.jpg')
        dummy_seg = (io.BytesIO(b'%PDF-1.4 test insurance document content'), 'insurance.pdf')

        # ==========================================
        # TEST 1: Create Full Sale Contract with Itemized Extras
        # ==========================================
        print("\n[TEST 1] Testing Sale_Full creation with itemized extras...")
        extras_test_str = "£180 Easyblok, £45 W. Charger, £140 Leg Cover, £70 Muff Tucano, £100 Rack, £100 Hotgrip Oxford, £100 Windscreen Rex, £100 GPS Rewire"
        total_extras_val = 180 + 45 + 140 + 70 + 100 + 100 + 100 + 100 # 835.00
        preco_moto = 2500.00
        total_esperado = preco_moto + total_extras_val # 3335.00

        res_full = client.post('/api/contratos', data={
            'tipo_contrato': 'Sale_Full',
            'id_cliente': str(cust.id),
            'placa': 'TEST_SALE1',
            'data_inicio': date.today().isoformat(),
            'categoria_historico': 'Clear',
            'valor_venda_veiculo': str(preco_moto),
            'acessorios_extras': extras_test_str,
            'valor_total_extras': str(total_extras_val),
            'valor_total_venda': str(total_esperado),
            'fotos': dummy_img,
            'seguro': dummy_seg
        }, content_type='multipart/form-data')
        
        assert res_full.status_code == 201, f"Expected 201, got {res_full.status_code}: {res_full.data.decode('utf-8')}"
        data_full = res_full.get_json()
        cid_full = data_full['id']
        print(f"-> Sale_Full Contract Created ID #{cid_full}")
        
        # Verify contract in DB
        c_full = db.session.get(Contract, cid_full)
        assert c_full.tipo_contrato == 'Sale_Full'
        assert c_full.categoria_historico == 'Clear'
        assert c_full.acessorios_extras == extras_test_str, f"Extras string mismatch: {c_full.acessorios_extras}"
        assert float(c_full.valor_total_venda) == 3335.00, f"Expected 3335.00, got {c_full.valor_total_venda}"
        assert c_full.status == 'Active'
        
        # Verify moto status is SOLD
        m1 = db.session.get(Motorcycle, 'TEST_SALE1')
        assert m1.status == MotoStatus.SOLD.value, f"Expected moto SOLD, got {m1.status}"
        print("-> Moto TEST_SALE1 status verified as SOLD.")
        
        # Verify transaction
        t_full = FinancialTransaction.query.filter_by(id_contrato=cid_full).all()
        assert len(t_full) == 1, f"Expected 1 transaction, got {len(t_full)}"
        assert t_full[0].tipo == TransactionType.SALE_FULL.value
        assert float(t_full[0].valor) == 3335.00, f"Expected transaction value 3335.00, got {t_full[0].valor}"
        assert t_full[0].status == TransactionStatus.PENDING.value, "Transaction must be Pending upon creation"
        print(f"-> Verified Transaction: Type={t_full[0].tipo}, Amount={t_full[0].valor}, Status={t_full[0].status}")
        
        # ==========================================
        # TEST 2: Create Installment Sale Contract with Extras Summation
        # ==========================================
        print("\n[TEST 2] Testing Sale_Installment creation with extras and installment schedule...")
        # Vehicle: 2800.00, Admin fee: 50.00, Extras: 225.00 (£180 Easyblok, £45 W. Charger) -> Total: 3075.00
        # Down payment: 1075.00 -> Outstanding balance: 2000.00 -> 4 x 500.00
        extras_inst_str = "£180 Easyblok, £45 W. Charger"
        schedule = [
            {"parcela": 1, "data_vencimento": "2026-10-01", "valor": 500.00},
            {"parcela": 2, "data_vencimento": "2026-11-01", "valor": 500.00},
            {"parcela": 3, "data_vencimento": "2026-12-01", "valor": 500.00},
            {"parcela": 4, "data_vencimento": "2027-01-01", "valor": 500.00}
        ]
        
        dummy_img2 = (io.BytesIO(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00'), 'test_bike2.jpg')
        dummy_seg2 = (io.BytesIO(b'%PDF-1.4 test insurance document content 2'), 'insurance2.pdf')
        res_inst = client.post('/api/contratos', data={
            'tipo_contrato': 'Sale_Installment',
            'id_cliente': str(cust.id),
            'placa': 'TEST_SALE2',
            'data_inicio': date.today().isoformat(),
            'categoria_historico': 'Cat N',
            'valor_venda_veiculo': '2800.00',
            'acessorios_extras': extras_inst_str,
            'valor_total_extras': '225.00',
            'valor_admin_fee': '50.00',
            'valor_total_venda': '3075.00',
            'valor_entrada': '1075.00',
            'saldo_devedor': '2000.00',
            'cronograma_parcelas': json.dumps(schedule),
            'fotos': dummy_img2,
            'seguro': dummy_seg2
        }, content_type='multipart/form-data')
        
        assert res_inst.status_code == 201, f"Expected 201, got {res_inst.status_code}: {res_inst.data.decode('utf-8')}"
        data_inst = res_inst.get_json()
        cid_inst = data_inst['id']
        print(f"-> Sale_Installment Contract Created ID #{cid_inst}")
        
        # Verify in DB
        c_inst = db.session.get(Contract, cid_inst)
        assert c_inst.tipo_contrato == 'Sale_Installment'
        assert c_inst.categoria_historico == 'Cat N'
        assert c_inst.acessorios_extras == extras_inst_str
        assert float(c_inst.valor_total_venda) == 3075.00
        assert float(c_inst.valor_entrada) == 1075.00
        assert float(c_inst.saldo_devedor) == 2000.00
        assert c_inst.status == 'Active'
        
        # Verify moto status is SOLD
        m2 = Motorcycle.query.get('TEST_SALE2')
        assert m2.status == MotoStatus.SOLD.value
        print("-> Moto TEST_SALE2 status verified as SOLD.")
        
        # Verify transactions: 1 SALE_DEPOSIT + 4 SALE_INSTALLMENT
        t_inst = FinancialTransaction.query.filter_by(id_contrato=cid_inst).order_by(FinancialTransaction.data_vencimento).all()
        assert len(t_inst) == 5, f"Expected 5 transactions (1 deposit + 4 installments), got {len(t_inst)}"
        
        # Check down payment transaction
        t_dep = [t for t in t_inst if t.tipo == TransactionType.SALE_DEPOSIT.value]
        assert len(t_dep) == 1, "Must have exactly 1 SALE_DEPOSIT transaction"
        assert float(t_dep[0].valor) == 1075.00, f"Expected 1075.00, got {t_dep[0].valor}"
        assert t_dep[0].status == TransactionStatus.PENDING.value, "Sale down payment must be Pending"
        assert t_dep[0].tipo != TransactionType.DEPOSIT.value, "SALE_DEPOSIT must NOT be mixed with rental DEPOSIT"
        print(f"-> Verified Down Payment: Type={t_dep[0].tipo}, Amount={t_dep[0].valor}, Status={t_dep[0].status}")
        
        # Check installments
        t_parc = [t for t in t_inst if t.tipo == TransactionType.SALE_INSTALLMENT.value]
        assert len(t_parc) == 4, "Must have 4 installment transactions"
        for idx, tp in enumerate(t_parc, 1):
            assert float(tp.valor) == 500.00
            assert tp.status == TransactionStatus.PENDING.value
            print(f"   Installment {idx}: Due={tp.data_vencimento}, Amount={tp.valor}, Status={tp.status}")
            
        # ==========================================
        # TEST 3: Contract Detail API & Print Page
        # ==========================================
        print("\n[TEST 3] Testing contract details API and Print Page...")
        res_get = client.get(f'/api/contratos/{cid_inst}')
        assert res_get.status_code == 200
        det = res_get.get_json()
        assert det['tipo_contrato'] == 'Sale_Installment'
        assert det['categoria_historico'] == 'Cat N'
        assert det['acessorios_extras'] == extras_inst_str
        assert det['valor_total_venda'] == 3075.00
        assert det['valor_entrada'] == 1075.00
        assert det['saldo_devedor'] == 2000.00
        assert len(det['cronograma_parcelas']) == 4
        # Assert aliases for details
        assert det.get('cliente') == 'John Buyer'
        assert det.get('cliente_nome') == 'John Buyer'
        assert det.get('modelo') == 'Yamaha NMAX 125'
        assert det.get('moto_modelo') == 'Yamaha NMAX 125'
        assert det.get('telefone') == '07123456789'
        assert det.get('endereco') == '10 Test Street, Birmingham, B1 1AA'
        
        # Verify 15-day insurance compliance is bypassed for sale contracts
        assert det.get('checagem_seguro_devida') is False, "Sold bikes must not have checagem_seguro_devida = True"
        assert det.get('dias_desde_checagem_seguro') is None, "Sold bikes should not track dias_desde_checagem_seguro"
        assert det.get('dias_para_proxima_checagem_seguro') is None, "Sold bikes should not track dias_para_proxima_checagem_seguro"
        
        # Verify dashboard askMID alerts do not include sold bikes
        res_dash = client.get('/api/dashboard')
        assert res_dash.status_code == 200
        dash_data = res_dash.get_json()
        seg_alertas = dash_data.get('contratos_seguro_alerta', [])
        alert_ids = [a['id'] for a in seg_alertas]
        assert cid_inst not in alert_ids, "Sale contract must NEVER trigger askMID insurance alerts on dashboard"
        assert cid_full not in alert_ids, "Sale contract must NEVER trigger askMID insurance alerts on dashboard"
        print("-> Confirmed: Sold bikes are completely exempt from 15-day askMID insurance monitoring and dashboard alerts.")
        print("-> API /api/contratos/<id> returned all sale fields and detail aliases correctly.")
        
        # Assert transaction descriptions in details API
        assert 'transacoes' in det
        txs = det['transacoes']
        dep_tx_list = [t for t in txs if t['tipo'] == 'Sale_Deposit']
        assert len(dep_tx_list) == 1
        assert dep_tx_list[0]['descricao'] == "Vehicle Sale - Down Payment (Deposit)"
        
        inst_tx_list = [t for t in txs if t['tipo'] == 'Sale_Installment']
        assert len(inst_tx_list) == 4
        assert inst_tx_list[0]['descricao'] == "Vehicle Sale - Instalment 1 of 4"
        assert inst_tx_list[1]['descricao'] == "Vehicle Sale - Instalment 2 of 4"
        print("-> Transaction descriptions verified in Contract Details API.")
        
        # Mark first installment paid and test receipt page
        first_inst_id = inst_tx_list[0]['id']
        res_pay = client.post(f'/api/financeiro/pagar/{first_inst_id}', json={'forma_pagamento': 'Card'})
        assert res_pay.status_code == 200
        
        res_recibo = client.get(f'/recibo/{first_inst_id}')
        assert res_recibo.status_code == 200
        html_recibo = res_recibo.data.decode('utf-8')
        assert 'Vehicle Sale - Instalment 1 of 4' in html_recibo
        assert 'Yamaha NMAX 125' in html_recibo
        assert 'J&amp;F Motorcycles LTD' in html_recibo or 'J&F Motorcycles LTD' in html_recibo
        print("-> Verified /recibo/<id> renders enhanced description, vehicle, and company details.")
        
        # Test Print HTML
        res_print = client.get(f'/contratos/{cid_inst}/imprimir')
        assert res_print.status_code == 200
        html_print = res_print.data.decode('utf-8')
        assert 'VEHICLE SALE AGREEMENT' in html_print
        assert 'J&amp;F Motorcycles LTD' in html_print or 'J&F Motorcycles LTD' in html_print
        assert 'Cat N' in html_print
        assert '109 WINDMILL LANE, BIRMINGHAM B66 3EW' in html_print
        assert 'SCHEDULE OF INSTALMENT PAYMENTS' in html_print
        # Assert fixed seller signature, white-background logo, and installment dates formatting
        assert 'signature_fernando.png' in html_print, "Fixed shop signature must be present in sale printout"
        assert 'logo_print.jpg' in html_print, "White-background logo_print.jpg must be used in sale agreement"
        assert '01/10/2026' in html_print, "Installment due dates must be formatted as DD/MM/YYYY in table"
        print("-> Print page successfully rendered VEHICLE SALE AGREEMENT with fixed shop signature, white logo, and formatted installment dates.")
        
        # Test manual charge creation for sale contracts (Sale_Installment and Sale_Deposit)
        print("\n[TEST 3.1] Testing manual charges on sale contract...")
        res_cob_inst = client.post(f'/api/contratos/{cid_inst}/cobrancas', json={
            'tipo': 'Sale_Installment',
            'valor': '250.00',
            'data_vencimento': '2027-02-01'
        })
        assert res_cob_inst.status_code == 201
        
        res_cob_dep = client.post(f'/api/contratos/{cid_inst}/cobrancas', json={
            'tipo': 'Sale_Deposit',
            'valor': '100.00',
            'data_vencimento': '2026-09-25'
        })
        assert res_cob_dep.status_code == 201
        print("-> Successfully created manual Sale_Installment and Sale_Deposit charges on sale contract.")
        
        # Test that Check-in inspection is FORBIDDEN for sold bikes / sale contracts
        print("\n[TEST 3.2] Testing check-in restriction for sold bikes...")
        dummy_insp_img = (io.BytesIO(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00'), 'insp.jpg')
        res_checkin = client.post('/api/vistorias', data={
            'id_contrato': str(cid_inst),
            'tipo': 'Check-in',
            'milhagem': '8500',
            'observacoes': 'Attempting return on sold bike',
            'fotos': dummy_insp_img
        }, content_type='multipart/form-data')
        assert res_checkin.status_code == 400, f"Expected 400 when attempting check-in on sold bike, got {res_checkin.status_code}"
        assert 'Check-in inspections (return) are not allowed' in res_checkin.get_json().get('error', '')
        print("-> Confirmed: Check-in inspection correctly rejected for sold bike.")
        
        # Test that Incident inspection is PERMITTED for sold bikes
        dummy_insp_img2 = (io.BytesIO(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00'), 'insp2.jpg')
        res_incident = client.post('/api/vistorias', data={
            'id_contrato': str(cid_inst),
            'tipo': 'Incident',
            'milhagem': '8550',
            'observacoes': 'Scratch report during warranty inspection',
            'fotos': dummy_insp_img2
        }, content_type='multipart/form-data')
        assert res_incident.status_code == 201, f"Expected 201 for Incident inspection on sold bike, got {res_incident.status_code}"
        # Test auto-completion of sales contract upon full payment and reopening on reversal
        print("\n[TEST 3.3] Testing auto-completion of sales contract upon payment quittance...")
        # cid_full has 1 transaction (Sale_Full), currently Pending
        c_full = db.session.get(Contract, cid_full)
        assert c_full.status in [ContractStatus.ATIVO.value, 'Active']
        t_full = FinancialTransaction.query.filter_by(id_contrato=cid_full).first()
        res_pay_full = client.post(f'/api/financeiro/pagar/{t_full.id}', json={'forma_pagamento': 'Bank Transfer'})
        assert res_pay_full.status_code == 200
        db.session.refresh(c_full)
        assert c_full.status == ContractStatus.COMPLETED.value, f"Expected Completed, got {c_full.status}"
        print("-> Confirmed: Sale_Full auto-transitions to Completed when paid in full.")

        # Revert payment and ensure it re-opens to Active
        res_rev_full = client.post(f'/api/financeiro/reverter/{t_full.id}')
        assert res_rev_full.status_code == 200
        db.session.refresh(c_full)
        assert c_full.status == ContractStatus.ATIVO.value, f"Expected Active after reversal, got {c_full.status}"
        print("-> Confirmed: Reverting payment re-opens Completed sale contract to Active.")

        # Re-pay to test detail API auto-check
        res_pay_full2 = client.post(f'/api/financeiro/pagar/{t_full.id}', json={'forma_pagamento': 'Card'})
        assert res_pay_full2.status_code == 200
        db.session.refresh(c_full)
        assert c_full.status == ContractStatus.COMPLETED.value
        print("-> Confirmed: Re-paying transaction sets status back to Completed.")

        # Revert payment back to Pending so cid_full is Active with Pending transaction for cancellation test (TEST 5)
        res_rev_full2 = client.post(f'/api/financeiro/reverter/{t_full.id}')
        assert res_rev_full2.status_code == 200
        db.session.refresh(c_full)
        assert c_full.status == ContractStatus.ATIVO.value
        
        # ==========================================
        # TEST 4: Weekly Rent Generation Logic
        # ==========================================
        print("\n[TEST 4] Testing weekly rent batch logic...")
        from app import _gerar_cobrancas_semanais_logic
        res_cron = _gerar_cobrancas_semanais_logic()
        
        # Ensure no new rent transactions were created for the sale contracts
        t_after_full = FinancialTransaction.query.filter_by(id_contrato=cid_full).all()
        t_after_inst = FinancialTransaction.query.filter_by(id_contrato=cid_inst).all()
        assert not any(t.tipo in [TransactionType.RENT.value, 'Rent', 'Aluguel'] for t in t_after_full), "Sale_Full must NOT receive weekly rent"
        assert not any(t.tipo in [TransactionType.RENT.value, 'Rent', 'Aluguel'] for t in t_after_inst), "Sale_Installment must NOT receive weekly rent"
        assert len(t_after_full) == 1
        assert len(t_after_inst) == 7, f"Expected 7 transactions (5 initial + 2 manual), got {len(t_after_inst)}"
        print("-> Confirmed weekly rent generator completely ignores sale contracts.")
        
        # ==========================================
        # TEST 5: Cancellation of Sale Contract
        # ==========================================
        print("\n[TEST 5] Testing cancellation of a sale contract...")
        res_cancel = client.post(f'/api/contratos/{cid_full}/cancelar', json={
            'motivo': 'Buyer pulled out before collecting'
        })
        assert res_cancel.status_code == 200
        
        c_cancelled = Contract.query.get(cid_full)
        assert c_cancelled.status == 'Cancelled'
        
        # Moto must return to Available
        m1_after = Motorcycle.query.get('TEST_SALE1')
        assert m1_after.status == MotoStatus.AVAILABLE.value, f"Expected Available, got {m1_after.status}"
        
        # Pending transactions should be cancelled
        t_c = FinancialTransaction.query.filter_by(id_contrato=cid_full).all()
        assert t_c[0].status == TransactionStatus.CANCELLED.value
        print("-> Sale contract cancelled successfully. Moto restored to Available, transactions cancelled.")
        
        print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

if __name__ == '__main__':
    test_sales_system()
