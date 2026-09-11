import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from PIL import Image, ImageDraw
from app import app
from database import (
    db, Motorcycle, Client, Contract, Inspection, FinancialTransaction, 
    MotoStatus, ContractStatus, InspectionType, TransactionType, TransactionStatus
)

def create_sample_image(filepath, title, subtitle, bg_color="#111827", accent_color="#FF6600"):
    if os.path.exists(filepath) and os.path.getsize(filepath) > 10000:
        return filepath
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    w, h = 800, 600
    img = Image.new('RGB', (w, h), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Gradient-like frame
    draw.rectangle([(20, 20), (w - 20, h - 20)], outline=accent_color, width=3)
    draw.rectangle([(30, 30), (w - 30, h - 30)], outline="#374151", width=1)

    # Accent header bar
    draw.rectangle([(30, 30), (w - 30, 90)], fill="#1f2937")
    draw.rectangle([(30, 30), (36, 90)], fill=accent_color)
    draw.text((50, 50), "FF MOTORS BIRMINGHAM • VEHICLE INSPECTION ASSET", fill="#9ca3af")

    # Center card box
    box_w, box_h = 700, 380
    box_x0 = (w - box_w) // 2
    box_y0 = 120
    draw.rectangle([(box_x0, box_y0), (box_x0 + box_w, box_y0 + box_h)], fill="#1e293b", outline="#334155", width=2)

    # Title & Subtitle
    draw.text((box_x0 + 40, box_y0 + 60), title, fill="#f8fafc")
    draw.text((box_x0 + 40, box_y0 + 110), subtitle, fill="#94a3b8")
    
    # Badge
    draw.rounded_rectangle([(box_x0 + 40, box_y0 + 170), (box_x0 + 260, box_y0 + 215)], radius=8, fill=accent_color)
    draw.text((box_x0 + 55, box_y0 + 185), "VERIFIED DIGITAL ASSET", fill="#ffffff")

    # Timestamp & metadata
    ts = datetime.utcnow().strftime('%d/%m/%Y %H:%M UTC')
    draw.text((box_x0 + 40, box_y0 + 260), f"Timestamp: {ts}", fill="#64748b")
    draw.text((box_x0 + 40, box_y0 + 290), "Resolution: 800x600 WebP • Compression: 85%", fill="#64748b")
    draw.text((box_x0 + 40, box_y0 + 320), "Status: Compliant with UK Road & Fleet Regulations", fill="#10b981")

    img.save(filepath, 'WEBP', quality=85)
    return filepath

def seed():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    uploads_dir = os.path.join(base_dir, 'static', 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)

    print("Generating demo photos and documents in static/uploads...")
    # Generate realistic demo inspection photos
    p1 = create_sample_image(os.path.join(uploads_dir, 'demo_forza_front.webp'), "HONDA FORZA 300 - FRONT ANGLE", "Reg: XX10 YYY • Headlights, Windscreen & Front Tire 100% OK")
    p2 = create_sample_image(os.path.join(uploads_dir, 'demo_forza_side.webp'), "HONDA FORZA 300 - LEFT SIDE BODYWORK", "Reg: XX10 YYY • Body panels mint, exhaust intact, mirrors aligned")
    p3 = create_sample_image(os.path.join(uploads_dir, 'demo_forza_rear.webp'), "HONDA FORZA 300 - REAR TIRE & BRAKES", "Reg: XX10 YYY • Rear brake pad tested, license plate secured")
    
    p_vis1 = create_sample_image(os.path.join(uploads_dir, 'demo_vision_front.webp'), "HONDA VISION 110 - CHECK-OUT", "Reg: FF27 MOT • Pearl White • Mileage: 4,120 mi")
    p_vis2 = create_sample_image(os.path.join(uploads_dir, 'demo_vision_side.webp'), "HONDA VISION 110 - SIDE INSPECTION", "Reg: FF27 MOT • Clean delivery, 2 helmet locks tested")

    # Generate document proofs
    doc_ins1 = create_sample_image(os.path.join(uploads_dir, 'demo_insurance_forza.webp'), "CERTIFICATE OF MOTOR INSURANCE", "Policy #FF-MTR-88291 • Comprehensive Hire & Reward Coverage", accent_color="#3b82f6")
    doc_ins2 = create_sample_image(os.path.join(uploads_dir, 'demo_insurance_vision.webp'), "CERTIFICATE OF MOTOR INSURANCE", "Policy #FF-MTR-77104 • Full Third-Party Hire & Reward", accent_color="#3b82f6")
    doc_lic = create_sample_image(os.path.join(uploads_dir, 'demo_driving_licence.webp'), "DVLA DRIVING LICENCE (UK)", "Holder: Thiago Brandao • Category A / A2 Valid", accent_color="#10b981")
    doc_bill = create_sample_image(os.path.join(uploads_dir, 'demo_proof_address.webp'), "PROOF OF RESIDENTIAL ADDRESS", "Utility Statement • High Street, Birmingham B4 7SL", accent_color="#6366f1")

    with app.app_context():
        print("Clearing database tables for fresh demo data...")
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

        print("Seeding demo motorcycles...")
        m1 = Motorcycle(placa="XX10 YYY", modelo="Honda Forza 300", cor="Blue Metallic", status=MotoStatus.RENTED.value)
        m2 = Motorcycle(placa="FF27 MOT", modelo="Honda Vision 110", cor="Pearl White", status=MotoStatus.RENTED.value)
        m3 = Motorcycle(placa="BK22 NMX", modelo="Yamaha NMAX 125", cor="Midnight Black", status=MotoStatus.AVAILABLE.value)
        m4 = Motorcycle(placa="WM23 PCX", modelo="Honda PCX 125", cor="Silver Frost", status=MotoStatus.AVAILABLE.value)
        m5 = Motorcycle(placa="BM19 WKP", modelo="Honda Vision 110", cor="Red Gloss", status=MotoStatus.MAINTENANCE.value)
        db.session.add_all([m1, m2, m3, m4, m5])
        db.session.flush()

        print("Seeding demo clients...")
        c1 = Client(
            nome="Thiago Brandao",
            telefone="07360469902",
            email="thiago.brandao@example.com",
            endereco="120 High Street, Birmingham, B4 7SL",
            url_habilitacao="/static/uploads/demo_driving_licence.webp",
            url_comprovante_endereco="/static/uploads/demo_proof_address.webp"
        )
        c2 = Client(
            nome="Mohamed da Silva",
            telefone="07360123456",
            email="mohamed.silva@example.com",
            endereco="45 Digbeth Avenue, Birmingham, B5 6DY",
            url_habilitacao="/static/uploads/demo_driving_licence.webp",
            url_comprovante_endereco="/static/uploads/demo_proof_address.webp"
        )
        c3 = Client(
            nome="Alexandre Smith",
            telefone="07400987654",
            email="alex.smith@example.com",
            endereco="88 Broad Street, Birmingham, B1 2HF",
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

        # Inspection for Contract 1 with 3 photos
        insp1 = Inspection(
            id_contrato=ct1.id,
            tipo=InspectionType.CHECK_OUT.value,
            data=ct1.data_retirada,
            observacoes="Vehicle checked out in mint condition. Tires 100%, brakes tested, 2 keys handed over.",
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
            url_seguro="/static/uploads/demo_insurance_vision.webp"
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

        insp2 = Inspection(
            id_contrato=ct2.id,
            tipo=InspectionType.CHECK_OUT.value,
            data=ct2.data_retirada,
            observacoes="Full delivery inspection complete. Clean bodywork, full tank of fuel, delivery box installed.",
            url_fotos="/static/uploads/demo_vision_front.webp,/static/uploads/demo_vision_side.webp"
        )
        db.session.add(insp2)

        db.session.commit()
        print("\nDemo data & media seeded successfully!")
        print(f"✓ {Motorcycle.query.count()} Motorbikes")
        print(f"✓ {Client.query.count()} Clients (with ID and Address proofs attached)")
        print(f"✓ {Contract.query.count()} Contracts (with Insurance & active schedules)")
        print(f"✓ {FinancialTransaction.query.count()} Financial Transactions (Paid & Pending)")
        print(f"✓ {Inspection.query.count()} Inspections (with multi-photo galleries)")

if __name__ == '__main__':
    seed()
