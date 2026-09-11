import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from app import app
from database import (
    db, Motorcycle, Client, Contract, Inspection, FinancialTransaction, User, AuditLog,
    MotoStatus, ContractStatus, InspectionType, TransactionType, TransactionStatus
)

def seed():
    with app.app_context():
        print("Clearing database tables for clean state...")
        AuditLog.query.delete()
        FinancialTransaction.query.delete()
        Inspection.query.delete()
        Contract.query.delete()
        Client.query.delete()
        Motorcycle.query.delete()
        User.query.delete()
        
        # Reset sqlite autoincrement sequence
        conn = db.session.connection()
        try:
            conn.execute(db.text("DELETE FROM sqlite_sequence WHERE name IN ('usuarios', 'clientes', 'contratos', 'vistorias', 'financeiro_transacoes', 'logs_auditoria');"))
        except Exception:
            pass
        db.session.commit()

        print("Seeding users & staff accounts...")
        u_admin = User(
            nome="Thiago Brandão",
            email="tmuniz570@gmail.com",
            role="admin",
            ativo=True
        )
        u_admin.set_password("Admin123!")

        u_staff1 = User(
            nome="Carlos Silva",
            email="carlos@ffmotors.co.uk",
            role="staff",
            ativo=True
        )
        u_staff1.set_password("Staff123!")

        u_staff2 = User(
            nome="Emma Watson",
            email="emma@ffmotors.co.uk",
            role="staff",
            ativo=True
        )
        u_staff2.set_password("Staff123!")

        db.session.add_all([u_admin, u_staff1, u_staff2])
        db.session.flush()

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
            url_seguro="/static/uploads/demo_insurance_forza.webp",
            criado_por_nome=u_admin.nome
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
            forma_pagamento="Bank Transfer",
            registrado_por_nome=u_admin.nome
        )
        t1_w1 = FinancialTransaction(
            id_contrato=ct1.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=ct1.data_retirada,
            data_pagamento=ct1.data_retirada,
            valor=140.00,
            status=TransactionStatus.PAID.value,
            forma_pagamento="Card",
            registrado_por_nome=u_admin.nome
        )
        t1_w2 = FinancialTransaction(
            id_contrato=ct1.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=hoje - timedelta(days=7),
            data_pagamento=hoje - timedelta(days=7),
            valor=140.00,
            status=TransactionStatus.PAID.value,
            forma_pagamento="Card",
            registrado_por_nome=u_staff1.nome
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
            url_fotos="/static/uploads/demo_forza_front.webp,/static/uploads/demo_forza_side.webp,/static/uploads/demo_forza_rear.webp",
            realizado_por_nome=u_admin.nome
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
            url_seguro="/static/uploads/demo_insurance_forza.webp",
            criado_por_nome=u_staff1.nome
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
            forma_pagamento="Cash",
            registrado_por_nome=u_staff1.nome
        )
        t2_w1 = FinancialTransaction(
            id_contrato=ct2.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=ct2.data_retirada,
            data_pagamento=ct2.data_retirada,
            valor=80.00,
            status=TransactionStatus.PAID.value,
            forma_pagamento="Cash",
            registrado_por_nome=u_staff1.nome
        )
        t2_w2 = FinancialTransaction(
            id_contrato=ct2.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=hoje + timedelta(days=4),
            valor=80.00,
            status=TransactionStatus.PENDING.value
        )
        db.session.add_all([t2_dep, t2_w1, t2_w2])

        # Inspection for Contract 2 with 2 distinct real photos
        insp2 = Inspection(
            id_contrato=ct2.id,
            tipo=InspectionType.CHECK_OUT.value,
            data=ct2.data_retirada,
            observacoes="Full delivery inspection complete. Clean bodywork, full tank of fuel, delivery box installed, digital speedometer verified.",
            url_fotos="/static/uploads/demo_vision_front.webp,/static/uploads/demo_vision_side.webp",
            realizado_por_nome=u_staff1.nome
        )
        db.session.add(insp2)

        print("Seeding Audit Log history...")
        logs = [
            AuditLog(
                data_hora=hoje - timedelta(days=14, hours=2),
                id_usuario=u_admin.id,
                usuario_nome=u_admin.nome,
                acao="CREATE_CLIENT",
                entidade="Client",
                entidade_id=str(c1.id),
                descricao=f"Cliente {c1.nome} cadastrado com CNH e Comprovante de Endereço por {u_admin.nome}",
                ip_origem="127.0.0.1"
            ),
            AuditLog(
                data_hora=hoje - timedelta(days=14, hours=1),
                id_usuario=u_admin.id,
                usuario_nome=u_admin.nome,
                acao="CREATE_CONTRACT",
                entidade="Contract",
                entidade_id=str(ct1.id),
                descricao=f"Contrato #{ct1.id} aberto para moto {m1.placa} por {u_admin.nome} (Aluguel: £140.00/sem, Depósito: £400.00)",
                ip_origem="127.0.0.1"
            ),
            AuditLog(
                data_hora=hoje - timedelta(days=14, hours=1),
                id_usuario=u_admin.id,
                usuario_nome=u_admin.nome,
                acao="CREATE_INSPECTION",
                entidade="Inspection",
                entidade_id=str(insp1.id),
                descricao=f"Vistoria de Check-out (3 fotos) realizada por {u_admin.nome} no Contrato #{ct1.id}",
                ip_origem="127.0.0.1"
            ),
            AuditLog(
                data_hora=hoje - timedelta(days=14, minutes=45),
                id_usuario=u_admin.id,
                usuario_nome=u_admin.nome,
                acao="PAYMENT_RECEIVED",
                entidade="Transaction",
                entidade_id=str(t1_dep.id),
                descricao=f"Baixa de £400.00 (Deposit) confirmada via Bank Transfer por {u_admin.nome} no Contrato #{ct1.id}",
                ip_origem="127.0.0.1"
            ),
            AuditLog(
                data_hora=hoje - timedelta(days=14, minutes=40),
                id_usuario=u_admin.id,
                usuario_nome=u_admin.nome,
                acao="PAYMENT_RECEIVED",
                entidade="Transaction",
                entidade_id=str(t1_w1.id),
                descricao=f"Baixa de £140.00 (Rent Semana 1) confirmada via Card por {u_admin.nome} no Contrato #{ct1.id}",
                ip_origem="127.0.0.1"
            ),
            AuditLog(
                data_hora=hoje - timedelta(days=7, hours=3),
                id_usuario=u_staff1.id,
                usuario_nome=u_staff1.nome,
                acao="PAYMENT_RECEIVED",
                entidade="Transaction",
                entidade_id=str(t1_w2.id),
                descricao=f"Baixa de £140.00 (Rent Semana 2) confirmada via Card por {u_staff1.nome} no Contrato #{ct1.id}",
                ip_origem="127.0.0.1"
            ),
            AuditLog(
                data_hora=hoje - timedelta(days=4),
                id_usuario=u_staff2.id,
                usuario_nome=u_staff2.nome,
                acao="MOTO_STATUS_CHANGE",
                entidade="Motorcycle",
                entidade_id=m5.placa,
                descricao=f"Status da moto {m5.placa} alterado para 'Maintenance' por {u_staff2.nome} (Troca de pastilhas de freio)",
                ip_origem="127.0.0.1"
            ),
            AuditLog(
                data_hora=hoje - timedelta(days=3, hours=4),
                id_usuario=u_staff1.id,
                usuario_nome=u_staff1.nome,
                acao="CREATE_CLIENT",
                entidade="Client",
                entidade_id=str(c2.id),
                descricao=f"Cliente {c2.nome} cadastrado por {u_staff1.nome}",
                ip_origem="127.0.0.1"
            ),
            AuditLog(
                data_hora=hoje - timedelta(days=3, hours=3),
                id_usuario=u_staff1.id,
                usuario_nome=u_staff1.nome,
                acao="CREATE_CONTRACT",
                entidade="Contract",
                entidade_id=str(ct2.id),
                descricao=f"Contrato #{ct2.id} aberto para moto {m2.placa} por {u_staff1.nome} (Aluguel: £80.00/sem, Depósito: £300.00)",
                ip_origem="127.0.0.1"
            ),
            AuditLog(
                data_hora=hoje - timedelta(days=3, hours=3),
                id_usuario=u_staff1.id,
                usuario_nome=u_staff1.nome,
                acao="CREATE_INSPECTION",
                entidade="Inspection",
                entidade_id=str(insp2.id),
                descricao=f"Vistoria de Check-out (2 fotos) realizada por {u_staff1.nome} no Contrato #{ct2.id}",
                ip_origem="127.0.0.1"
            ),
            AuditLog(
                data_hora=hoje - timedelta(days=3, hours=2),
                id_usuario=u_staff1.id,
                usuario_nome=u_staff1.nome,
                acao="PAYMENT_RECEIVED",
                entidade="Transaction",
                entidade_id=str(t2_dep.id),
                descricao=f"Baixa de £300.00 (Deposit) confirmada via Cash por {u_staff1.nome} no Contrato #{ct2.id}",
                ip_origem="127.0.0.1"
            ),
            AuditLog(
                data_hora=hoje - timedelta(days=3, hours=2),
                id_usuario=u_staff1.id,
                usuario_nome=u_staff1.nome,
                acao="PAYMENT_RECEIVED",
                entidade="Transaction",
                entidade_id=str(t2_w1.id),
                descricao=f"Baixa de £80.00 (Rent Semana 1) confirmada via Cash por {u_staff1.nome} no Contrato #{ct2.id}",
                ip_origem="127.0.0.1"
            )
        ]
        db.session.add_all(logs)

        db.session.commit()
        print("\nDatabase seeded successfully with new structure & staff attribution!")
        print(f"✓ {User.query.count()} Users (Admin + 2 Staff members)")
        print(f"✓ {Motorcycle.query.count()} Motorbikes")
        print(f"✓ {Client.query.count()} Clients (with DVLA Licence and Birmingham Council Tax proofs)")
        print(f"✓ {Contract.query.count()} Contracts (with Fleet Insurance & active schedules)")
        print(f"✓ {FinancialTransaction.query.count()} Financial Transactions (Paid & Pending with staff badges)")
        print(f"✓ {Inspection.query.count()} Inspections (with unique multi-angle galleries & operator names)")
        print(f"✓ {AuditLog.query.count()} Audit Log Events in timeline")

if __name__ == '__main__':
    seed()
