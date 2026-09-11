import sys
from datetime import datetime, timedelta
from app import app
from database import db, Motorcycle, Client, Contract, Inspection, FinancialTransaction, MotoStatus, ContractStatus, InspectionType, TransactionType, TransactionStatus

def seed():
    with app.app_context():
        # Check if data already exists
        if Motorcycle.query.first() or Client.query.first():
            print("Database already contains data.")
            if '--force' not in sys.argv and '--clean' not in sys.argv:
                print("Run with --force or --clean to reset and re-seed demo data.")
                return

        if '--clean' in sys.argv or '--force' in sys.argv:
            print("Cleaning existing database records...")
            FinancialTransaction.query.delete()
            Inspection.query.delete()
            Contract.query.delete()
            Client.query.delete()
            Motorcycle.query.delete()
            db.session.commit()

        print("Seeding demo data for FF Motors Birmingham...")

        # 1. Seed Motorcycles
        m1 = Motorcycle(placa="XX10 YYY", modelo="Honda Forza 300", cor="Blue Metallic", status=MotoStatus.RENTED.value)
        m2 = Motorcycle(placa="FF27 MOT", modelo="Honda Vision 110", cor="Pearl White", status=MotoStatus.RENTED.value)
        m3 = Motorcycle(placa="BK22 NMX", modelo="Yamaha NMAX 125", cor="Midnight Black", status=MotoStatus.AVAILABLE.value)
        m4 = Motorcycle(placa="WM23 PCX", modelo="Honda PCX 125", cor="Silver Frost", status=MotoStatus.AVAILABLE.value)
        m5 = Motorcycle(placa="BM19 WKP", modelo="Honda Vision 110", cor="Red Gloss", status=MotoStatus.MAINTENANCE.value)
        db.session.add_all([m1, m2, m3, m4, m5])
        db.session.flush()

        # 2. Seed Clients
        c1 = Client(
            nome="Thiago Brandao",
            telefone="07360469902",
            email="thiago.brandao@example.com",
            endereco="120 High Street, Birmingham, B4 7SL"
        )
        c2 = Client(
            nome="Mohamed da Silva",
            telefone="07360123456",
            email="mohamed.silva@example.com",
            endereco="45 Digbeth Avenue, Birmingham, B5 6DY"
        )
        c3 = Client(
            nome="Alexandre Smith",
            telefone="07400987654",
            email="alex.smith@example.com",
            endereco="88 Broad Street, Birmingham, B1 2HF"
        )
        db.session.add_all([c1, c2, c3])
        db.session.flush()

        # 3. Seed Contracts
        hoje = datetime.utcnow()
        
        # Contract 1: Active, Paid deposit & rent
        ct1 = Contract(
            id_cliente=c1.id,
            placa=m1.placa,
            data_retirada=hoje - timedelta(days=14),
            dia_pagamento_semanal=4, # Friday
            valor_aluguel_semanal=140.00,
            status=ContractStatus.ACTIVE.value
        )
        db.session.add(ct1)
        db.session.flush()

        # Transactions for Contract 1
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

        # Inspection for Contract 1
        insp1 = Inspection(
            id_contrato=ct1.id,
            tipo=InspectionType.CHECK_OUT.value,
            data=ct1.data_retirada,
            observacoes="Vehicle checked out in mint condition. Tires 100%, brakes tested, 2 keys handed over."
        )
        db.session.add(insp1)

        # Contract 2: Active
        ct2 = Contract(
            id_cliente=c2.id,
            placa=m2.placa,
            data_retirada=hoje - timedelta(days=3),
            dia_pagamento_semanal=4, # Friday
            valor_aluguel_semanal=80.00,
            status=ContractStatus.ACTIVE.value
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
        db.session.add_all([t2_dep, t2_w1])

        insp2 = Inspection(
            id_contrato=ct2.id,
            tipo=InspectionType.CHECK_OUT.value,
            data=ct2.data_retirada,
            observacoes="Full inspection complete. Clean bodywork, full tank of fuel."
        )
        db.session.add(insp2)

        db.session.commit()
        print("Demo data seeded successfully!")
        print(f"- {Motorcycle.query.count()} Motorbikes")
        print(f"- {Client.query.count()} Clients")
        print(f"- {Contract.query.count()} Contracts")
        print(f"- {FinancialTransaction.query.count()} Financial Transactions")
        print(f"- {Inspection.query.count()} Inspections")

if __name__ == '__main__':
    seed()
