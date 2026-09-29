import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytz
from datetime import datetime, date, timedelta
from app import app, db, _gerar_cobrancas_semanais_logic, run_daily_jobs, get_london_date
from database import Contract, Motorcycle, Client, FinancialTransaction, ContractType, ContractStatus, TransactionType, TransactionStatus, AuditLog, JobExecutionLock

def test_weekly_billing_resilience():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        print("\n=== STARTING WEEKLY BILLING RESILIENCE & CATCH-UP TEST ===")
        
        # 1. Setup client & motorcycles
        client = Client.query.filter_by(telefone="447000999888").first()
        if not client:
            client = Client(
                nome="Test Weekly Driver",
                telefone="447000999888",
                endereco="100 High St, Birmingham"
            )
            db.session.add(client)
            db.session.commit()
            
        m_mon = Motorcycle.query.filter_by(placa="MON_TEST01").first()
        if not m_mon:
            m_mon = Motorcycle(placa="MON_TEST01", modelo="Honda PCX 125", status="Rented")
            db.session.add(m_mon)
            
        m_tue = Motorcycle.query.filter_by(placa="TUE_TEST01").first()
        if not m_tue:
            m_tue = Motorcycle(placa="TUE_TEST01", modelo="Yamaha NMAX 125", status="Rented")
            db.session.add(m_tue)
            
        db.session.commit()
        
        # 2. Setup active rental contracts:
        # Contract 1: Monday (0)
        c_mon = Contract.query.filter_by(placa="MON_TEST01").first()
        if not c_mon:
            c_mon = Contract(
                id_cliente=client.id,
                placa="MON_TEST01",
                tipo_contrato=ContractType.RENT.value,
                valor_aluguel_semanal=90.00,
                dia_pagamento_semanal=0, # Monday
                status=ContractStatus.ACTIVE.value,
                data_retirada=datetime(2026, 9, 14, 10, 0, 0)
            )
            db.session.add(c_mon)
            db.session.commit()
        else:
            c_mon.status = ContractStatus.ACTIVE.value
            c_mon.dia_pagamento_semanal = 0
            db.session.commit()
            
        # Contract 2: Tuesday (1)
        c_tue = Contract.query.filter_by(placa="TUE_TEST01").first()
        if not c_tue:
            c_tue = Contract(
                id_cliente=client.id,
                placa="TUE_TEST01",
                tipo_contrato=ContractType.RENT.value,
                valor_aluguel_semanal=95.00,
                dia_pagamento_semanal=1, # Tuesday
                status=ContractStatus.ACTIVE.value,
                data_retirada=datetime(2026, 9, 15, 10, 0, 0)
            )
            db.session.add(c_tue)
            db.session.commit()
        else:
            c_tue.status = ContractStatus.ACTIVE.value
            c_tue.dia_pagamento_semanal = 1
            db.session.commit()
            
        # Remove any future rent transactions for these test contracts to simulate missed billing
        hoje_date = get_london_date()
        dia_semana_hoje = hoje_date.weekday()
        
        # Calculate expected target dates for Monday contract and Tuesday contract
        dias_desde_seg = (dia_semana_hoje - 0) % 7
        ult_seg = hoje_date - timedelta(days=dias_desde_seg)
        prox_seg = ult_seg + timedelta(days=7)
        
        dias_desde_ter = (dia_semana_hoje - 1) % 7
        ult_ter = hoje_date - timedelta(days=dias_desde_ter)
        prox_ter = ult_ter + timedelta(days=7)
        
        FinancialTransaction.query.filter(
            FinancialTransaction.id_contrato.in_([c_mon.id, c_tue.id]),
            FinancialTransaction.tipo.in_([TransactionType.RENT.value, 'Rent', 'Aluguel'])
        ).delete()
        db.session.commit()
        
        print(f"-> Test state: Today is {hoje_date} (weekday={dia_semana_hoje}). All rent txs wiped for contracts #{c_mon.id} (Mon) and #{c_tue.id} (Tue).")
        
        # 3. Execute billing logic (Auto-Catch-Up)
        print("-> Running _gerar_cobrancas_semanais_logic()...")
        geradas = _gerar_cobrancas_semanais_logic()
        print(f"-> Generated: {geradas} total charges across the system.")
        
        # Verify Monday contract received its upcoming charge for prox_seg (Monday + 7)
        tx_mon_prox = FinancialTransaction.query.filter(
            FinancialTransaction.id_contrato == c_mon.id,
            FinancialTransaction.tipo.in_([TransactionType.RENT.value, 'Rent', 'Aluguel']),
            FinancialTransaction.data_vencimento >= datetime(prox_seg.year, prox_seg.month, prox_seg.day, 0, 0, 0),
            FinancialTransaction.data_vencimento < datetime(prox_seg.year, prox_seg.month, prox_seg.day, 0, 0, 0) + timedelta(days=1)
        ).first()
        assert tx_mon_prox is not None, f"Expected Rent transaction for Monday #{c_mon.id} on {prox_seg}"
        assert float(tx_mon_prox.valor) == 90.00
        print(f"✓ Verified: Monday contract #{c_mon.id} has next Monday charge {prox_seg} (£{tx_mon_prox.valor}) generated and visible.")
        
        # Verify Tuesday contract received its upcoming charge for prox_ter (Tuesday + 7)
        tx_tue_prox = FinancialTransaction.query.filter(
            FinancialTransaction.id_contrato == c_tue.id,
            FinancialTransaction.tipo.in_([TransactionType.RENT.value, 'Rent', 'Aluguel']),
            FinancialTransaction.data_vencimento >= datetime(prox_ter.year, prox_ter.month, prox_ter.day, 0, 0, 0),
            FinancialTransaction.data_vencimento < datetime(prox_ter.year, prox_ter.month, prox_ter.day, 0, 0, 0) + timedelta(days=1)
        ).first()
        assert tx_tue_prox is not None, f"Expected Rent transaction for Tuesday #{c_tue.id} on {prox_ter}"
        assert float(tx_tue_prox.valor) == 95.00
        print(f"✓ Verified: Tuesday contract #{c_tue.id} has next Tuesday charge {prox_ter} (£{tx_tue_prox.valor}) generated and visible.")
        
        # 4. Test Idempotency (re-running immediately)
        print("-> Re-running _gerar_cobrancas_semanais_logic() immediately...")
        re_run = _gerar_cobrancas_semanais_logic()
        assert re_run == 0, f"Expected 0 new charges on second run, got {re_run}"
        print(f"✓ Verified: Idempotency strictly preserved (0 new charges).")
        
        # 5. Test Day-of-Week change auto-sync
        print("-> Changing Monday contract to Friday (4)...")
        import time as pytime
        from database import User
        admin_user = User.query.filter_by(is_admin=True).first()
        with app.test_client() as client_app:
            with client_app.session_transaction() as sess:
                sess['_user_id'] = str(admin_user.id)
                sess['_fresh'] = True
                sess['last_activity'] = pytime.time()
            
            # Using PUT route to alter due day
            res = client_app.put(f'/api/contratos/{c_mon.id}/dia-pagamento', json={
                'dia_pagamento_semanal': 4, # Friday
                'ajustar_pendentes': True
            })
            assert res.status_code == 200, f"Expected 200 from dia-pagamento, got {res.status_code}"
            
            db.session.refresh(c_mon)
            assert c_mon.dia_pagamento_semanal == 4
            print("✓ Verified: Contract due day changed to Friday (4) and auto-synced.")
            
        # Clean up test artifacts
        FinancialTransaction.query.filter(
            FinancialTransaction.id_contrato.in_([c_mon.id, c_tue.id])
        ).delete()
        Contract.query.filter(Contract.id.in_([c_mon.id, c_tue.id])).delete()
        Motorcycle.query.filter(Motorcycle.placa.in_(["MON_TEST01", "TUE_TEST01"])).delete()
        db.session.commit()
        print("✓ Cleaned up test contract data cleanly.")
        print("\n=== ALL WEEKLY BILLING RESILIENCE TESTS PASSED (100% SUCCESS)! ===\n")

if __name__ == "__main__":
    test_weekly_billing_resilience()
