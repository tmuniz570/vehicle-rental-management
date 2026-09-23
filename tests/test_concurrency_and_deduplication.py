#!/usr/bin/env python3
"""
tests/test_concurrency_and_deduplication.py
===========================================
Test suite verifying:
1. Concurrency isolation and atomic multi-worker locking in run_daily_jobs()
2. Idempotency of weekly rent generation logic (_gerar_cobrancas_semanais_logic)
3. Detection and safe cleanup of duplicate pending rent charges
4. Preservation of original charges, paid transactions, and deposits
5. Admin API endpoint /api/admin/limpar-cobrancas-duplicadas security and response
"""

import os
import sys
import threading
from datetime import datetime, timedelta
import pytz

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import (
    app, db, run_daily_jobs,
    _gerar_cobrancas_semanais_logic,
    _limpar_cobrancas_semanais_duplicadas_logic,
    get_london_date, get_local_now
)
from database import (
    Contract, Motorcycle, Client, FinancialTransaction,
    JobExecutionLock, TransactionType, TransactionStatus,
    ContractStatus, MotoStatus, ContractType
)

def run_all_tests():
    print("\n" + "=" * 70)
    print("  TEST SUITE: CONCURRENCY LOCKING & CHARGE DEDUPLICATION")
    print("=" * 70)

    with app.app_context():
        # Setup clean test contract
        test_plate = "DEDUP_TEST_01"
        moto = db.session.get(Motorcycle, test_plate)
        if not moto:
            moto = Motorcycle(
                placa=test_plate,
                modelo="Honda PCX 125 Concurrency Test",
                status=MotoStatus.AVAILABLE.value
            )
            db.session.add(moto)
            db.session.commit()

        client = Client.query.filter_by(email="dedup_test@ffmotors.co.uk").first()
        if not client:
            client = Client(
                nome="Test Concurrency Client",
                email="dedup_test@ffmotors.co.uk",
                telefone="07123456789"
            )
            db.session.add(client)
            db.session.commit()

        # Contract payment day = today's London weekday
        today_london = datetime.now(pytz.timezone('Europe/London'))
        today_weekday = today_london.weekday()

        contrato = Contract.query.filter_by(placa=test_plate, status=ContractStatus.ACTIVE.value).first()
        if not contrato:
            contrato = Contract(
                id_cliente=client.id,
                placa=test_plate,
                tipo_contrato=ContractType.RENT.value,
                valor_aluguel_semanal=85.00,
                dia_pagamento_semanal=today_weekday,
                status=ContractStatus.ACTIVE.value,
                data_retirada=get_local_now()
            )
            db.session.add(contrato)
            db.session.commit()

        print(f"\n[SETUP] Active test contract created: ID #{contrato.id}, Plate={test_plate}, Weekly Day={today_weekday}")

        # -------------------------------------------------------------
        # TEST 1: Idempotency of weekly rent generation
        # -------------------------------------------------------------
        print("\n[TEST 1] Testing weekly rent generator idempotency...")
        # Clean any existing transactions for this contract for this week
        next_due = get_local_now() + timedelta(days=7)
        start_day = next_due.replace(hour=0, minute=0, second=0, microsecond=0)
        end_day = start_day + timedelta(days=1)

        FinancialTransaction.query.filter(
            FinancialTransaction.id_contrato == contrato.id,
            FinancialTransaction.data_vencimento >= start_day,
            FinancialTransaction.data_vencimento < end_day
        ).delete()
        db.session.commit()

        # Run 1: Should generate exactly 1 charge for this contract
        count1 = _gerar_cobrancas_semanais_logic()
        assert count1 >= 1, f"Expected at least 1 charge generated, got {count1}"

        # Verify exactly 1 transaction exists for next week
        txs = FinancialTransaction.query.filter(
            FinancialTransaction.id_contrato == contrato.id,
            FinancialTransaction.data_vencimento >= start_day,
            FinancialTransaction.data_vencimento < end_day
        ).all()
        assert len(txs) == 1, f"Expected exactly 1 charge, found {len(txs)}"
        print(f"✓ Run 1 generated {count1} charge(s). Contract #{contrato.id} has exactly 1 charge (£{txs[0].valor}).")

        # Run 2: Immediately re-run - must generate 0 new charges
        count2 = _gerar_cobrancas_semanais_logic()
        assert count2 == 0, f"Expected 0 charges on second immediate run, got {count2}"

        txs_after = FinancialTransaction.query.filter(
            FinancialTransaction.id_contrato == contrato.id,
            FinancialTransaction.data_vencimento >= start_day,
            FinancialTransaction.data_vencimento < end_day
        ).all()
        assert len(txs_after) == 1, f"Charge was duplicated! Count: {len(txs_after)}"
        print(f"✓ Run 2 generated 0 charges. Charge count strictly preserved at 1.")

        # -------------------------------------------------------------
        # TEST 2: Multi-threaded Concurrency Lock Simulation
        # -------------------------------------------------------------
        print("\n[TEST 2] Testing atomic concurrency locking across simulated workers...")
        job_name = "daily_rent_and_deposit_jobs"
        london_date_str = get_london_date().strftime('%Y-%m-%d')

        # Reset lock to previous day to simulate 01:00 AM transition
        yesterday_str = (get_london_date() - timedelta(days=1)).strftime('%Y-%m-%d')
        lock = JobExecutionLock.query.filter_by(job_name=job_name).first()
        if not lock:
            lock = JobExecutionLock(
                job_name=job_name,
                last_run_date=yesterday_str,
                last_run_at=get_local_now() - timedelta(days=1),
                executed_by="test-init"
            )
            db.session.add(lock)
        else:
            lock.last_run_date = yesterday_str
        db.session.commit()

        # Fire 6 simultaneous threads calling run_daily_jobs()
        threads = []
        for i in range(6):
            t = threading.Thread(target=run_daily_jobs)
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify that lock is now today's date
        updated_lock = JobExecutionLock.query.filter_by(job_name=job_name).first()
        assert updated_lock.last_run_date == london_date_str, "Lock date was not set to today"

        # Verify that contract still has ONLY 1 charge for next week
        final_txs = FinancialTransaction.query.filter(
            FinancialTransaction.id_contrato == contrato.id,
            FinancialTransaction.data_vencimento >= start_day,
            FinancialTransaction.data_vencimento < end_day
        ).all()
        assert len(final_txs) == 1, f"Concurrency test failed! Duplicate charges created: {len(final_txs)}"
        print(f"✓ 6 concurrent worker threads executed. Lock acquired once, exactly 1 charge exists.")

        # -------------------------------------------------------------
        # TEST 3: Safe Duplicate Detection and Cleanup
        # -------------------------------------------------------------
        print("\n[TEST 3] Testing duplicate detection and safe cleanup logic...")

        # Clear any leftover transactions for this test contract first
        FinancialTransaction.query.filter_by(id_contrato=contrato.id).delete()
        db.session.commit()

        # Manually inject 3 duplicate PENDING charges (to reproduce production scenario)
        simulated_due = get_local_now() + timedelta(days=14)
        t_original = FinancialTransaction(
            id_contrato=contrato.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=simulated_due,
            valor=85.00,
            status=TransactionStatus.PENDING.value
        )
        db.session.add(t_original)
        db.session.flush()

        t_dup1 = FinancialTransaction(
            id_contrato=contrato.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=simulated_due,
            valor=85.00,
            status=TransactionStatus.PENDING.value
        )
        t_dup2 = FinancialTransaction(
            id_contrato=contrato.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=simulated_due,
            valor=85.00,
            status=TransactionStatus.PENDING.value
        )
        # Also inject a PAID transaction and DEPOSIT on the same date (MUST NEVER BE DELETED!)
        t_paid = FinancialTransaction(
            id_contrato=contrato.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=simulated_due,
            valor=85.00,
            status=TransactionStatus.PAID.value
        )
        t_deposit = FinancialTransaction(
            id_contrato=contrato.id,
            tipo=TransactionType.DEPOSIT.value,
            data_vencimento=simulated_due,
            valor=300.00,
            status=TransactionStatus.PENDING.value
        )
        db.session.add_all([t_dup1, t_dup2, t_paid, t_deposit])
        db.session.commit()

        orig_id = t_original.id
        dup1_id = t_dup1.id
        dup2_id = t_dup2.id
        paid_id = t_paid.id
        deposit_id = t_deposit.id

        print(f"-> Injected simulated transactions for due date {simulated_due.strftime('%Y-%m-%d')}:")
        print(f"   Original Pending Rent ID: #{orig_id}")
        print(f"   Duplicate Pending Rent ID 1: #{dup1_id}")
        print(f"   Duplicate Pending Rent ID 2: #{dup2_id}")
        print(f"   Legitimate Paid Rent ID: #{paid_id}")
        print(f"   Deposit ID: #{deposit_id}")

        # Step 3.1: Dry-run preview
        preview = _limpar_cobrancas_semanais_duplicadas_logic(dry_run=True)
        assert preview["total_duplicadas"] >= 2, f"Expected at least 2 duplicates detected, got {preview['total_duplicadas']}"
        rem_ids = [d["id_removido"] for d in preview["detalhes"]]
        assert dup1_id in rem_ids and dup2_id in rem_ids, "Duplicate IDs not found in preview"
        assert orig_id not in rem_ids, "Original ID must NOT be marked for removal"
        assert paid_id not in rem_ids, "Paid transaction must NEVER be marked for removal"
        assert deposit_id not in rem_ids, "Deposit transaction must NEVER be marked for removal"
        print(f"✓ Dry-run preview correctly identified duplicate IDs {dup1_id} and {dup2_id}. Protected #{orig_id}, #{paid_id}, #{deposit_id}.")

        # Step 3.2: Execution (apply=True)
        cleanup_res = _limpar_cobrancas_semanais_duplicadas_logic(dry_run=False)
        assert cleanup_res["total_duplicadas"] >= 2

        # Verify database state after cleanup
        assert db.session.get(FinancialTransaction, orig_id) is not None, "Original transaction was accidentally deleted!"
        assert db.session.get(FinancialTransaction, dup1_id) is None, "Duplicate 1 was not deleted!"
        assert db.session.get(FinancialTransaction, dup2_id) is None, "Duplicate 2 was not deleted!"
        assert db.session.get(FinancialTransaction, paid_id) is not None, "Paid transaction was deleted!"
        assert db.session.get(FinancialTransaction, deposit_id) is not None, "Deposit transaction was deleted!"
        print(f"✓ Real execution deleted duplicates successfully and kept #{orig_id}, #{paid_id}, #{deposit_id} intact.")

        # -------------------------------------------------------------
        # TEST 4: Admin API Endpoint
        # -------------------------------------------------------------
        print("\n[TEST 4] Testing /api/admin/limpar-cobrancas-duplicadas endpoint...")
        client_app = app.test_client()

        # 4.1: Unauthorized without auth
        resp_unauth = client_app.post('/api/admin/limpar-cobrancas-duplicadas')
        assert resp_unauth.status_code == 403, f"Expected 403 Forbidden, got {resp_unauth.status_code}"
        print("✓ Unauthorized request rejected with 403 Forbidden.")

        # 4.2: Authorized with cron secret
        cron_key = os.environ.get('CRON_SECRET_KEY', 'ffmotors-internal-cron-key-2026')
        resp_auth = client_app.post(
            '/api/admin/limpar-cobrancas-duplicadas',
            headers={'X-Cron-Key': cron_key},
            json={'dry_run': True}
        )
        assert resp_auth.status_code == 200, f"Expected 200 OK, got {resp_auth.status_code}"
        data = resp_auth.get_json()
        assert data["success"] is True
        print(f"✓ Authorized API call succeeded (dry-run=True, found={data['dados']['total_duplicadas']}).")

        # Cleanup test records cleanly
        FinancialTransaction.query.filter(
            FinancialTransaction.id.in_([orig_id, paid_id, deposit_id])
        ).delete()
        FinancialTransaction.query.filter(
            FinancialTransaction.id_contrato == contrato.id
        ).delete()
        db.session.delete(contrato)
        db.session.delete(client)
        db.session.delete(moto)
        db.session.commit()
        print("\n[CLEANUP] Cleaned up temporary test contract and motorcycle.")

    print("\n" + "=" * 70)
    print("  ALL CONCURRENCY & DEDUPLICATION TESTS PASSED (100% SUCCESS)!")
    print("=" * 70 + "\n")

if __name__ == '__main__':
    run_all_tests()
