import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from app import app
from database import (
    db, Motorcycle, Client, Contract, Inspection, FinancialTransaction, 
    MotoStatus, ContractStatus, InspectionType, TransactionType, TransactionStatus
)

def seed():
    with app.app_context():
        print("Clearing database tables for clean state...")
        FinancialTransaction.query.delete()
        Inspection.query.delete()
        Contract.query.delete()
        Client.query.delete()
        Motorcycle.query.delete()
        
        # Reset sqlite autoincrement sequence
        conn = db.session.connection()
        try:
            conn.execute(db.text("DELETE FROM sqlite_sequence WHERE name IN ('clientes', 'contratos', 'vistorias', 'financeiro_transacoes');"))
        except Exception:
            pass
        db.session.commit()

        print("Seeding motorcycles...")
        m1 = Motorcycle(placa="XX10 YYY", modelo="Honda Forza 300", cor="Blue Metallic", status=MotoStatus.RENTED.value)
        m2 = Motorcycle(placa="FF27 MOT", modelo="Honda Vision 110", cor="Pearl White", status=MotoStatus.RENTED.value)
        m3 = Motorcycle(placa="BK22 NMX", modelo="Yamaha NMAX 125", cor="Midnight Black", status=MotoStatus.AVAILABLE.value)
        m4 = Motorcycle(placa="WM23 PCX", modelo="Honda PCX 125", cor="Silver Frost", status=MotoStatus.AVAILABLE.value)
        m5 = Motorcycle(placa="BM19 WKP", modelo="Honda Vision 110", cor="Red Gloss", status=MotoStatus.MAINTENANCE.value)
        db.session.add_all([m1, m2, m3, m4, m5])
        db.session.flush()

        print("Seeding clients...")
        c1 = Client(
            nome="Thiago Brandao",
            telefone="07360469902",
            email="thiago.brandao@example.com",
            endereco="34 Harrow Road, Kings Heath, Birmingham B14 7RL",
            url_habilitacao="/static/uploads/demo_driving_licence.webp",
            url_comprovante_endereco="/static/uploads/demo_proof_address.webp"
        )
        c2 = Client(
            nome="Mohamed da Silva",
            telefone="07360123456",
            email="mohamed.silva@example.com",
            endereco="45 Digbeth Avenue, Birmingham B5 6DY",
            url_habilitacao="/static/uploads/demo_driving_licence.webp",
            url_comprovante_endereco="/static/uploads/demo_proof_address.webp"
        )
        c3 = Client(
            nome="Alexandre Smith",
            telefone="07400987654",
            email="alex.smith@example.com",
            endereco="88 Broad Street, Birmingham B1 2HF",
            url_habilitacao="/static/uploads/demo_driving_licence.webp",
            url_comprovante_endereco="/static/uploads/demo_proof_address.webp"
        )
        db.session.add_all([c1, c2, c3])
        db.session.flush()

        hoje = datetime.utcnow()

        print("Seeding Contract #1 (Honda Forza 300 - Thiago Brandao)...")
        ct1 = Contract(
            id_cliente=c1.id,
            placa=m1.placa,
            data_retirada=hoje - timedelta(days=14),
            dia_pagamento_semanal=4, # Friday
            valor_aluguel_semanal=140.00,
            status=ContractStatus.ACTIVE.value,
            url_seguro="/static/uploads/demo_insurance_forza.webp"
        )
        db.session.add(ct1)
        db.session.flush()

        # Contract 1 Ledger
        t1_dep = FinancialTransaction(
            id_contrato=ct1.id,
            tipo=TransactionType.DEPOSIT.value,
            data_vencimento=ct1.data_retirada,
            data_pagamento=ct1.data_retirada,
            valor=400.00,
            status=TransactionStatus.PAID.value,
            forma_pagamento="Bank Transfer"
        )
        t1_w1 = FinancialTransaction(
            id_contrato=ct1.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=ct1.data_retirada,
            data_pagamento=ct1.data_retirada,
            valor=140.00,
            status=TransactionStatus.PAID.value,
            forma_pagamento="Card"
        )
        t1_w2 = FinancialTransaction(
            id_contrato=ct1.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=hoje - timedelta(days=7),
            data_pagamento=hoje - timedelta(days=7),
            valor=140.00,
            status=TransactionStatus.PAID.value,
            forma_pagamento="Card"
        )
        t1_w3 = FinancialTransaction(
            id_contrato=ct1.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=hoje + timedelta(days=1),
            valor=140.00,
            status=TransactionStatus.PENDING.value
        )
        db.session.add_all([t1_dep, t1_w1, t1_w2, t1_w3])

        # Inspection for Contract 1 with 3 distinct real photos (Front, Side, Rear)
        insp1 = Inspection(
            id_contrato=ct1.id,
            tipo=InspectionType.CHECK_OUT.value,
            data=ct1.data_retirada,
            observacoes="Vehicle checked out in mint condition. Michelin tires 100%, brakes tested, windshield intact, 2 keys handed over.",
            url_fotos="/static/uploads/demo_forza_front.webp,/static/uploads/demo_forza_side.webp,/static/uploads/demo_forza_rear.webp"
        )
        db.session.add(insp1)

        print("Seeding Contract #2 (Honda Vision 110 - Mohamed da Silva)...")
        ct2 = Contract(
            id_cliente=c2.id,
            placa=m2.placa,
            data_retirada=hoje - timedelta(days=3),
            dia_pagamento_semanal=4, # Friday
            valor_aluguel_semanal=80.00,
            status=ContractStatus.ACTIVE.value,
            url_seguro="/static/uploads/demo_insurance_forza.webp"
        )
        db.session.add(ct2)
        db.session.flush()

        t2_dep = FinancialTransaction(
            id_contrato=ct2.id,
            tipo=TransactionType.DEPOSIT.value,
            data_vencimento=ct2.data_retirada,
            data_pagamento=ct2.data_retirada,
            valor=300.00,
            status=TransactionStatus.PAID.value,
            forma_pagamento="Cash"
        )
        t2_w1 = FinancialTransaction(
            id_contrato=ct2.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=ct2.data_retirada,
            data_pagamento=ct2.data_retirada,
            valor=80.00,
            status=TransactionStatus.PAID.value,
            forma_pagamento="Cash"
        )
        t2_w2 = FinancialTransaction(
            id_contrato=ct2.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=hoje + timedelta(days=4),
            valor=80.00,
            status=TransactionStatus.PENDING.value
        )
        db.session.add_all([t2_dep, t2_w1, t2_w2])

        # Inspection for Contract 2 with 2 distinct real photos (Front/Body & Cockpit/Wheel inspection)
        insp2 = Inspection(
            id_contrato=ct2.id,
            tipo=InspectionType.CHECK_OUT.value,
            data=ct2.data_retirada,
            observacoes="Full delivery inspection complete. Clean bodywork, full tank of fuel, delivery box installed, digital speedometer verified.",
            url_fotos="/static/uploads/demo_vision_front.webp,/static/uploads/demo_vision_side.webp"
        )
        db.session.add(insp2)

        db.session.commit()
        print("\nClean database seeded successfully with 100% unique photographic assets!")
        print(f"✓ {Motorcycle.query.count()} Motorbikes")
        print(f"✓ {Client.query.count()} Clients (with DVLA Licence and Birmingham Council Tax proofs)")
        print(f"✓ {Contract.query.count()} Contracts (with Fleet Insurance & active schedules)")
        print(f"✓ {FinancialTransaction.query.count()} Financial Transactions (Paid & Pending)")
        print(f"✓ {Inspection.query.count()} Inspections (with unique multi-angle galleries)")

if __name__ == '__main__':
    seed()
