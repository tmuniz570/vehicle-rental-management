import os
import shutil
import sqlite3
from datetime import datetime, timedelta, date
from app import app
from database import (
    db, Motorcycle, Client, Contract, Inspection, FinancialTransaction, User, AuditLog, Claim,
    ContractAttachment, MotoStatus, ContractStatus, InspectionType, TransactionType, TransactionStatus
)

def seed():
    with app.app_context():
        base_dir = os.path.dirname(os.path.abspath(__file__))
        uploads_dir = os.path.join(base_dir, 'static', 'uploads')
        demo_assets_dir = os.path.join(base_dir, 'static', 'demo_assets')
        
        # 1. Clean uploads and restore demo assets
        if os.path.exists(uploads_dir):
            for item in os.listdir(uploads_dir):
                if item == '.gitkeep':
                    continue
                item_path = os.path.join(uploads_dir, item)
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception:
                    pass
        else:
            os.makedirs(uploads_dir, exist_ok=True)
            
        gitkeep_path = os.path.join(uploads_dir, '.gitkeep')
        if not os.path.exists(gitkeep_path):
            with open(gitkeep_path, 'w') as f:
                pass
                
        if os.path.exists(demo_assets_dir):
            for asset in os.listdir(demo_assets_dir):
                src = os.path.join(demo_assets_dir, asset)
                dst = os.path.join(uploads_dir, asset)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
            print("✓ Restored demo asset images to static/uploads")

        print("Clearing database tables for clean state...")
        AuditLog.query.delete()
        ContractAttachment.query.delete()
        FinancialTransaction.query.delete()
        Inspection.query.delete()
        Contract.query.delete()
        Client.query.delete()
        Motorcycle.query.delete()
        Claim.query.delete()
        User.query.delete()
        
        # Reset sqlite autoincrement sequence
        conn = db.session.connection()
        try:
            conn.execute(db.text("DELETE FROM sqlite_sequence WHERE name IN ('usuarios', 'clientes', 'contratos', 'contrato_anexos', 'vistorias', 'financeiro_transacoes', 'logs_auditoria', 'claims');"))
        except Exception:
            pass
        db.session.commit()

        print("Seeding users & staff accounts...")
        u_admin = User(
            nome="Thiago Brandão",
            email="tmuniz570@gmail.com",
            role="admin",
            is_admin=True,
            perm_alugueis=True,
            perm_claims=True,
            ativo=True
        )
        u_admin.set_password("Admin123!")

        u_staff1 = User(
            nome="Carlos Silva",
            email="carlos@ffmotors.co.uk",
            role="staff",
            is_admin=False,
            perm_alugueis=True,
            perm_claims=False,
            ativo=True
        )
        u_staff1.set_password("Staff123!")

        u_staff2 = User(
            nome="Emma Watson",
            email="emma@ffmotors.co.uk",
            role="staff",
            is_admin=False,
            perm_alugueis=True,
            perm_claims=False,
            ativo=True
        )
        u_staff2.set_password("Staff123!")

        u_aline = User(
            nome="Aline Ferreira",
            email="aline@ffmotors.co.uk",
            role="staff",
            is_admin=False,
            perm_alugueis=False,
            perm_claims=True,
            ativo=True
        )
        u_aline.set_password("Aline123!")

        db.session.add_all([u_admin, u_staff1, u_staff2, u_aline])
        db.session.flush()

        hoje = datetime.utcnow()
        hoje_date = hoje.date()

        print("Seeding fleet with diverse operational alert states (FF Motors Birmingham)...")
        # Fleet of 18 bikes covering all states:
        # - Available bikes (some fresh, one with MOT expiring soon)
        # - Rented bikes (some fresh, one with Tax expiring soon, one with insurance cancelled, one with 15-day check overdue)
        # - Maintenance bikes (one with MOT already expired!)
        motos_data = [
            # (plate, model, colour, status, mot_days_ahead, tax_days_ahead, milhagem_atual)
            ("XX10YYY", "Honda Forza 300", "Blue Metallic", MotoStatus.RENTED.value, 240, 210, 14850),
            ("FF27MOT", "Honda Vision 110", "Pearl White", MotoStatus.RENTED.value, 300, 270, 8920),
            ("BK22NMX", "Yamaha NMAX 125", "Midnight Black", MotoStatus.AVAILABLE.value, 18, 150, 11400),  # YELLOW ALERT: MOT due in 18 days!
            ("WM23PCX", "Honda PCX 125", "Silver Frost", MotoStatus.AVAILABLE.value, 330, 330, 6200),      # AVAILABLE: 100% valid
            ("BM19WKP", "Honda Vision 110", "Red Gloss", MotoStatus.MAINTENANCE.value, -4, 90, 24350),     # RED ALERT: Expired MOT (-4 days)!
            ("BV21XKT", "Honda PCX 125", "Matt Black", MotoStatus.RENTED.value, 180, 14, 16100),           # YELLOW ALERT: Road Tax due in 14 days!
            ("BW71FGH", "Yamaha NMAX 125", "Phantom Blue", MotoStatus.RENTED.value, 210, 190, 12750),
            ("BL20ZTR", "Honda Vision 110", "Moondust Grey", MotoStatus.RENTED.value, 270, 240, 19800),    # CONTRACT ALERT: 15-day insurance check due!
            ("BN22LKP", "Honda PCX 125", "Pearl Jasmine White", MotoStatus.RENTED.value, 310, 290, 9400),
            ("BP23XMN", "Yamaha XMAX 125", "Icon Blue", MotoStatus.RENTED.value, 340, 310, 5800),
            ("BX69VTR", "Honda Forza 125", "Matt Cynos Grey", MotoStatus.RENTED.value, 160, 140, 18200),   # RED ALERT: Insurance CANCELLED!
            ("WM22KLJ", "Piaggio Liberty 125", "Nero Lucido", MotoStatus.RENTED.value, 220, 200, 13600),   # OVERDUE ALERT: 2 weeks rent behind (£170)!
            ("WN21TYU", "Honda Vision 110", "Candy Luster Red", MotoStatus.RENTED.value, 290, 260, 15900), # OVERDUE ALERT: 1 week rent behind (£80)!
            ("WO72HJK", "Honda PCX 125", "Matt Dim Gray", MotoStatus.RENTED.value, 320, 300, 8100),
            ("WP20QWE", "Yamaha NMAX 125", "Anvil Grey", MotoStatus.AVAILABLE.value, 250, 220, 14200),     # AVAILABLE: 100% valid
            ("WR23ZXC", "Honda Vision 110", "Pearl White", MotoStatus.RENTED.value, 360, 330, 7500),
            ("WT21OPL", "Honda PCX 125", "Matte Galaxy Black", MotoStatus.RENTED.value, 190, 170, 11950),
            ("WU22VBN", "Yamaha NMAX 125", "Tech Kamo", MotoStatus.AVAILABLE.value, 280, 250, 17320),      # AVAILABLE: Just returned from contract
        ]
        
        motos = {}
        for placa, modelo, cor, status, mot_offset, tax_offset, milhagem in motos_data:
            m = Motorcycle(
                placa=placa,
                modelo=modelo,
                cor=cor,
                status=status,
                milhagem_atual=milhagem,
                vencimento_mot=hoje_date + timedelta(days=mot_offset),
                vencimento_tax=hoje_date + timedelta(days=tax_offset)
            )
            db.session.add(m)
            motos[placa] = m
        db.session.flush()

        print("Seeding clients with diverse document combinations (Full Licence, CBT, Incomplete, Missing Back)...")
        # Client situations:
        # 1. Full UK Licence: Front + Back + Address (No CBT needed)
        # 2. Provisional Licence with CBT: Front + Back + CBT + Address
        # 3. Incomplete: Missing Back of Licence (Only Front + Address)
        # 4. Incomplete: Missing Proof of Address (Front + Back + CBT)
        # 5. New lead / Initial: Only Front uploaded
        clientes_specs = [
            # (name, phone, email, address, has_front, has_back, has_cbt, has_addr, description)
            ("Thiago Brandao", "07360469902", "thiago.brandao@example.com", "34 Harrow Road, Kings Heath, Birmingham B14 7RL", True, True, False, True, "Full UK Licence (Front + Back + Address)"),
            ("Mohamed da Silva", "07360123456", "mohamed.silva@example.com", "45 Digbeth Avenue, Birmingham B5 6DY", True, True, True, True, "Provisional + CBT Courier (All 4 docs complete)"),
            ("Alexandre Smith", "07400987654", "alex.smith@example.com", "88 Broad Street, Birmingham B1 2HF", True, True, False, True, "Full UK Driving Licence (Full A2)"),
            ("Lucas Oliveira", "07512345678", "lucas.oliveira@example.com", "12 Moseley Road, Highgate, Birmingham B12 0HG", True, False, False, True, "MISSING BACK SIDE: Only Front + Address uploaded"),
            ("Gabriel Santos", "07890123456", "gabriel.santos@example.com", "77 Stratford Road, Sparkhill, Birmingham B11 4DA", True, True, True, True, "Provisional + CBT (All 4 docs complete)"),
            ("Mateus Ferreira", "07701928374", "mateus.ferreira@example.com", "104 Alcester Road, Moseley, Birmingham B13 8EE", True, True, False, True, "Full UK Licence (Front + Back + Address)"),
            ("Bruno Carvalho", "07911223344", "bruno.carvalho@example.com", "23 Soho Road, Handsworth, Birmingham B21 9SN", True, True, True, False, "MISSING ADDRESS: Front + Back + CBT (No Address)"),
            ("Rafael Costa", "07455667788", "rafael.costa@example.com", "56 Harborne High Street, Birmingham B17 9NE", True, True, True, True, "Provisional + CBT (All 4 docs complete)"),
            ("Leonardo Souza", "07333444555", "leonardo.souza@example.com", "19 Bristol Road, Edgbaston, Birmingham B5 7TT", True, True, False, True, "Full UK Driving Licence (Front + Back + Address)"),
            ("David Johnson", "07888999000", "david.johnson@example.com", "82 Coventry Road, Small Heath, Birmingham B10 0UG", True, False, False, False, "NEW LEAD: Only Licence Front uploaded"),
            ("Tariq Al-Mansoor", "07555666777", "tariq.mansoor@example.com", "41 Erdington High Street, Birmingham B23 6RH", True, True, True, True, "Provisional + CBT (All 4 docs complete)"),
            ("Felipe Mendes", "07999888777", "felipe.mendes@example.com", "15 Pershore Road, Stirchley, Birmingham B30 2BU", True, True, False, True, "Full UK Licence (Front + Back + Address)"),
            ("Rodrigo Lima", "07322114455", "rodrigo.lima@example.com", "93 Hagley Road, Edgbaston, Birmingham B16 8QG", True, True, True, True, "Provisional + CBT (All 4 docs complete)"),
            ("Carlos Eduardo", "07844332211", "carlos.eduardo@example.com", "62 Aston Expressway, Birmingham B6 4DA", True, True, False, True, "Full UK Licence (Front + Back + Address)"),
            ("Anderson Silva", "07777888999", "anderson.silva@example.com", "18 Walsall Road, Perry Barr, Birmingham B42 1SF", True, True, False, True, "Completed contract client (Full Licence)"),
            ("Victor Hugo", "07900112233", "victor.hugo@example.com", "50 Jewellery Quarter, Birmingham B18 6EW", True, True, True, True, "Quarantine deposit client (All 4 docs)"),
        ]

        clients = []
        for nome, tel, email, endereco, has_front, has_back, has_cbt, has_addr, desc in clientes_specs:
            cl = Client(
                nome=nome,
                telefone=tel,
                email=email,
                endereco=endereco,
                url_habilitacao="/static/uploads/demo_driving_licence.webp" if has_front else None,
                url_habilitacao_verso="/static/uploads/demo_licence_back.webp" if has_back else None,
                url_cbt="/static/uploads/demo_cbt_certificate.webp" if has_cbt else None,
                url_comprovante_endereco="/static/uploads/demo_proof_address.webp" if has_addr else None
            )
            db.session.add(cl)
            clients.append(cl)
        db.session.flush()

        print("Seeding diverse contract scenarios (Up to date, Overdue, Cancelled insurance, 15-day check due, Quarantine, Completed)...")
        staff_pool = [u_admin, u_staff1, u_staff2]

        contracts_specs = [
            # (client_idx, plate, weeks_active, rent_val, deposit_val, status, pay_day, ins_status, ins_days_ago, overdue_weeks, notes)
            (0, "XX10YYY", 4, 140.0, 400.0, ContractStatus.ACTIVE.value, 4, "Valid", 4, 0, "Honda Forza 300 - Premium rental, 100% up to date"),
            (1, "FF27MOT", 2, 80.0, 300.0, ContractStatus.ACTIVE.value, 4, "Valid", 2, 0, "Honda Vision 110 - Delivery rider, up to date"),
            (2, "WM23PCX", 3, 90.0, 350.0, ContractStatus.COMPLETED.value, 4, "Valid", 25, 0, "Past contract with £50 damage deduction (£300 refunded)"),
            (3, "BV21XKT", 6, 95.0, 350.0, ContractStatus.ACTIVE.value, 0, "Valid", 6, 0, "Honda PCX 125 - Bike has Road Tax due in 14 days"),
            (4, "BW71FGH", 3, 95.0, 350.0, ContractStatus.ACTIVE.value, 1, "Valid", 1, 0, "Yamaha NMAX 125 - Up to date, recently checked"),
            (5, "BL20ZTR", 8, 85.0, 300.0, ContractStatus.ACTIVE.value, 4, "Valid", 18, 0, "ALERT: 15-Day Insurance Check overdue (checked 18 days ago)!"),
            (6, "BN22LKP", 5, 90.0, 350.0, ContractStatus.ACTIVE.value, 2, "Valid", 7, 0, "Honda PCX 125 - Up to date, full-time courier"),
            (7, "BP23XMN", 3, 120.0, 400.0, ContractStatus.ACTIVE.value, 4, "Valid", 3, 0, "Yamaha XMAX 125 - Up to date"),
            (8, "BX69VTR", 4, 110.0, 400.0, ContractStatus.ACTIVE.value, 3, "Cancelled", 1, 0, "CRITICAL ALERT: Insurance CANCELLED! Action required"),
            (9, "WM22KLJ", 7, 85.0, 300.0, ContractStatus.ACTIVE.value, 4, "Valid", 10, 2, "OVERDUE ALERT: 2 weeks late (£170 overdue in reports)"),
            (10, "WN21TYU", 5, 80.0, 300.0, ContractStatus.ACTIVE.value, 5, "Valid", 9, 1, "OVERDUE ALERT: 1 week late (£80 overdue in reports)"),
            (11, "WO72HJK", 2, 95.0, 350.0, ContractStatus.ACTIVE.value, 4, "Valid", 4, 0, "PCX 125 - Up to date courier"),
            (12, "WR23ZXC", 6, 85.0, 300.0, ContractStatus.ACTIVE.value, 4, "Valid", 11, 0, "Vision 110 - Regular customer, on time"),
            (13, "WT21OPL", 4, 90.0, 350.0, ContractStatus.ACTIVE.value, 0, "Valid", 8, 0, "PCX 125 - Active contract"),
            (14, "BM19WKP", 12, 80.0, 300.0, ContractStatus.COMPLETED.value, 4, "Valid", 30, 0, "COMPLETED: Full £300 deposit refunded via Bank Transfer"),
            (15, "WU22VBN", 10, 95.0, 350.0, ContractStatus.DEPOSIT_HOLD.value, 4, "Valid", 5, 0, "DEPOSIT HOLD: Bike returned 5 days ago, £350 in 14-day hold"),
        ]

        all_logs = []
        created_contracts = []

        for idx, spec in enumerate(contracts_specs):
            cl_idx, plate, weeks_active, rent_val, dep_val, c_status, pay_day, ins_status, ins_days_ago, overdue_wks, desc = spec
            c_client = clients[cl_idx]
            staff_member = staff_pool[idx % len(staff_pool)]
            retirada = hoje - timedelta(days=weeks_active * 7)
            
            devolucao = None
            if c_status == ContractStatus.DEPOSIT_HOLD.value:
                devolucao = hoje - timedelta(days=5) # returned 5 days ago
            elif c_status == ContractStatus.COMPLETED.value:
                devolucao = hoje - timedelta(days=20) # returned 20 days ago

            moto_obj = motos[plate]
            milhas_rodadas_semanais = 150 # media realista de entregador em Birmingham (150 milhas/semana)
            milhas_totais_contrato = weeks_active * milhas_rodadas_semanais

            # Milhagem inicial no início do contrato
            milhagem_ini = max(1000, moto_obj.milhagem_atual - milhas_totais_contrato)
            milhagem_fim = None
            if c_status in (ContractStatus.DEPOSIT_HOLD.value, ContractStatus.COMPLETED.value):
                milhagem_fim = moto_obj.milhagem_atual

            # Cenários de Assinatura:
            # - A maioria assinou na retirada (touch screen)
            # - O contrato 1 anexou via escaneada/PDF
            # - Os contratos encerrados (DEPOSIT_HOLD e COMPLETED) também têm assinatura de devolução
            assinatura_ini = None
            data_assinatura_ini = None
            assinatura_dev = None
            data_assinatura_dev = None

            if idx == 1:
                # Contrato com documento assinado escaneado / anexado (papel)
                assinatura_ini = None
                data_assinatura_ini = None
            elif idx % 5 != 4:
                # 80% dos clientes assinaram na tela na retirada
                assinatura_ini = "/static/uploads/demo_signature_client.png"
                data_assinatura_ini = retirada

            if c_status in (ContractStatus.DEPOSIT_HOLD.value, ContractStatus.COMPLETED.value):
                assinatura_dev = "/static/uploads/demo_signature_client.png"
                data_assinatura_dev = devolucao

            ct = Contract(
                id_cliente=c_client.id,
                placa=plate,
                data_retirada=retirada,
                data_devolucao=devolucao,
                dia_pagamento_semanal=pay_day,
                valor_aluguel_semanal=rent_val,
                status=c_status,
                milhagem_inicial=milhagem_ini,
                milhagem_final=milhagem_fim,
                assinatura_cliente_inicial=assinatura_ini,
                data_assinatura_inicial=data_assinatura_ini,
                assinatura_cliente_devolucao=assinatura_dev,
                data_assinatura_devolucao=data_assinatura_dev,
                url_seguro="/static/uploads/demo_insurance_forza.webp",
                url_comprovante_deposito="/static/uploads/demo_proof_address.webp",
                criado_por_nome=staff_member.nome,
                data_ultima_checagem_seguro=hoje_date - timedelta(days=ins_days_ago),
                status_seguro=ins_status,
                seguro_verificado_por=staff_member.nome
            )
            db.session.add(ct)
            db.session.flush()
            created_contracts.append(ct)

            # Anexos de Contrato Físico / Escaneado
            if idx in (1, 3): # Contrato 2 e 4 possuem contratos escaneados anexados
                anexo_pdf = ContractAttachment(
                    id_contrato=ct.id,
                    tipo='initial_contract',
                    url_arquivo="/static/uploads/demo_contract_scan.pdf",
                    nome_original=f"Rental_Agreement_Signed_{plate}.pdf",
                    data_criacao=retirada
                )
                db.session.add(anexo_pdf)

            if c_status == ContractStatus.COMPLETED.value:
                # Contrato concluído tem anexo da via de devolução escaneada
                anexo_ret = ContractAttachment(
                    id_contrato=ct.id,
                    tipo='return_contract',
                    url_arquivo="/static/uploads/demo_contract_scan.pdf",
                    nome_original=f"Termination_Return_Inspection_{plate}.pdf",
                    data_criacao=devolucao
                )
                db.session.add(anexo_ret)

            # Contract Creation Audit Log
            all_logs.append(AuditLog(
                data_hora=retirada,
                id_usuario=staff_member.id,
                usuario_nome=staff_member.nome,
                acao="CREATE_CONTRACT",
                entidade="Contract",
                entidade_id=str(ct.id),
                descricao=f"Contrato #{ct.id} aberto para {c_client.nome} ({plate}) por {staff_member.nome} (Aluguel: £{rent_val:.2f}/sem, Depósito: £{dep_val:.2f})",
                ip_origem="127.0.0.1"
            ))

            # Initial Deposit Transaction
            t_dep = FinancialTransaction(
                id_contrato=ct.id,
                tipo=TransactionType.DEPOSIT.value,
                data_vencimento=retirada,
                data_pagamento=retirada,
                valor=dep_val,
                status=TransactionStatus.PAID.value,
                forma_pagamento="Bank Transfer" if idx % 2 == 0 else "Card",
                registrado_por_nome=staff_member.nome
            )
            db.session.add(t_dep)

            # Weekly Rent Transactions
            for w in range(weeks_active):
                venc = retirada + timedelta(days=w * 7)
                is_overdue_week = (overdue_wks > 0) and (w >= weeks_active - overdue_wks)

                if is_overdue_week:
                    # Explicitly overdue transaction: dueDate is in the past, status is PENDING!
                    t_rent = FinancialTransaction(
                        id_contrato=ct.id,
                        tipo=TransactionType.RENT.value,
                        data_vencimento=venc,
                        data_pagamento=None,
                        valor=rent_val,
                        status=TransactionStatus.PENDING.value,
                        forma_pagamento=None,
                        registrado_por_nome=None
                    )
                elif venc <= hoje - timedelta(days=7):
                    # Past week: paid on time
                    t_rent = FinancialTransaction(
                        id_contrato=ct.id,
                        tipo=TransactionType.RENT.value,
                        data_vencimento=venc,
                        data_pagamento=venc,
                        valor=rent_val,
                        status=TransactionStatus.PAID.value,
                        forma_pagamento="Card" if w % 2 == 0 else "Cash",
                        registrado_por_nome=staff_pool[(w + idx) % len(staff_pool)].nome
                    )
                elif venc <= hoje:
                    # Current week: on time
                    t_rent = FinancialTransaction(
                        id_contrato=ct.id,
                        tipo=TransactionType.RENT.value,
                        data_vencimento=venc,
                        data_pagamento=venc,
                        valor=rent_val,
                        status=TransactionStatus.PAID.value,
                        forma_pagamento="Card",
                        registrado_por_nome=staff_member.nome
                    )
                else:
                    # Future week scheduled
                    t_rent = FinancialTransaction(
                        id_contrato=ct.id,
                        tipo=TransactionType.RENT.value,
                        data_vencimento=venc,
                        valor=rent_val,
                        status=TransactionStatus.PENDING.value
                    )
                db.session.add(t_rent)

            # Check-out Inspection
            is_forza = "forza" in plate.lower() or "xx10" in plate.lower() or "bx69" in plate.lower()
            insp_checkout = Inspection(
                id_contrato=ct.id,
                tipo=InspectionType.CHECK_OUT.value,
                data=retirada,
                milhagem=milhagem_ini,
                observacoes=f"Full pre-delivery checkout for {plate}. Tires checked, brakes tested, full tank of petrol, helmet and lock handed over.",
                url_fotos="/static/uploads/demo_forza_front.webp,/static/uploads/demo_forza_side.webp,/static/uploads/demo_forza_rear.webp" if is_forza else "/static/uploads/demo_vision_front.webp,/static/uploads/demo_vision_side.webp",
                realizado_por_nome=staff_member.nome
            )
            db.session.add(insp_checkout)

            # Special Cases: Deposit Hold, Completed Full, and Completed with Damage Deduction
            if c_status == ContractStatus.DEPOSIT_HOLD.value:
                # Returned bike check-in
                insp_checkin = Inspection(
                    id_contrato=ct.id,
                    tipo=InspectionType.CHECK_IN.value,
                    data=devolucao,
                    milhagem=milhagem_fim,
                    observacoes=f"Bike {plate} returned in good order. Minimal wear on rear tyre. Retained deposit under standard 14-day quarantine hold.",
                    url_fotos="/static/uploads/demo_vision_front.webp,/static/uploads/demo_vision_side.webp",
                    realizado_por_nome=staff_pool[1].nome
                )
                db.session.add(insp_checkin)
                all_logs.append(AuditLog(
                    data_hora=devolucao,
                    id_usuario=staff_pool[1].id,
                    usuario_nome=staff_pool[1].nome,
                    acao="RETURN_VEHICLE",
                    entidade="Contract",
                    entidade_id=str(ct.id),
                    descricao=f"Moto {plate} devolvida no Contrato #{ct.id}. Odômetro final: {milhagem_fim} mi ({milhagem_fim - milhagem_ini} mi rodadas). Depósito de £{dep_val:.2f} retido em quarentena de 14 dias.",
                    ip_origem="127.0.0.1"
                ))

            elif c_status == ContractStatus.COMPLETED.value:
                # Returned bike check-in for completed contract
                insp_checkin = Inspection(
                    id_contrato=ct.id,
                    tipo=InspectionType.CHECK_IN.value,
                    data=devolucao,
                    milhagem=milhagem_fim,
                    observacoes=f"Contract completed. Bike {plate} final inspection passed. All equipment returned, return mileage recorded ({milhagem_fim} mi).",
                    url_fotos="/static/uploads/demo_vision_front.webp,/static/uploads/demo_vision_side.webp",
                    realizado_por_nome=u_admin.nome
                )
                db.session.add(insp_checkin)
                all_logs.append(AuditLog(
                    data_hora=devolucao,
                    id_usuario=u_admin.id,
                    usuario_nome=u_admin.nome,
                    acao="RETURN_VEHICLE",
                    entidade="Contract",
                    entidade_id=str(ct.id),
                    descricao=f"Encerramento de contrato: Moto {plate} devolvida no Contrato #{ct.id}. Odômetro final: {milhagem_fim} mi ({milhagem_fim - milhagem_ini} mi rodadas no total).",
                    ip_origem="127.0.0.1"
                ))

                if idx == 2:
                    # Completed with Damage Deduction (£50 damage deduction, £300 refunded)
                    t_deduction = FinancialTransaction(
                        id_contrato=ct.id,
                        tipo=TransactionType.FINE.value,
                        data_vencimento=devolucao,
                        data_pagamento=devolucao,
                        valor=50.0,
                        status=TransactionStatus.PAID.value,
                        forma_pagamento="Damage / Deposit Deduction",
                        registrado_por_nome=u_admin.nome
                    )
                    db.session.add(t_deduction)

                    t_refund = FinancialTransaction(
                        id_contrato=ct.id,
                        tipo=TransactionType.DEPOSIT_REFUND.value,
                        data_vencimento=devolucao + timedelta(days=14),
                        data_pagamento=devolucao + timedelta(days=14),
                        valor=dep_val - 50.0,
                        status=TransactionStatus.PAID.value,
                        forma_pagamento="Bank Transfer",
                        registrado_por_nome=u_admin.nome
                    )
                    db.session.add(t_refund)

                    all_logs.append(AuditLog(
                        data_hora=devolucao + timedelta(days=14),
                        id_usuario=u_admin.id,
                        usuario_nome=u_admin.nome,
                        acao="REFUND_DEPOSIT",
                        entidade="Contract",
                        entidade_id=str(ct.id),
                        descricao=f"Devolução parcial de caução: £50.00 deduzidos por danos no retrovisor, £{dep_val - 50.0:.2f} restituídos via Bank Transfer no Contrato #{ct.id}",
                        ip_origem="127.0.0.1"
                    ))
                else:
                    # Full completed contract with deposit refund
                    t_refund = FinancialTransaction(
                        id_contrato=ct.id,
                        tipo=TransactionType.DEPOSIT_REFUND.value,
                        data_vencimento=devolucao + timedelta(days=14),
                        data_pagamento=devolucao + timedelta(days=14),
                        valor=dep_val,
                        status=TransactionStatus.PAID.value,
                        forma_pagamento="Bank Transfer",
                        registrado_por_nome=u_admin.nome
                    )
                    db.session.add(t_refund)
                    all_logs.append(AuditLog(
                        data_hora=devolucao + timedelta(days=14),
                        id_usuario=u_admin.id,
                        usuario_nome=u_admin.nome,
                        acao="REFUND_DEPOSIT",
                        entidade="Contract",
                        entidade_id=str(ct.id),
                        descricao=f"Devolução integral de caução de £{dep_val:.2f} confirmada por {u_admin.nome} via Bank Transfer no Contrato #{ct.id}",
                        ip_origem="127.0.0.1"
                    ))

        # Add recent staff payment received logs for rich audit stream
        recent_payments = FinancialTransaction.query.filter_by(status=TransactionStatus.PAID.value).limit(10).all()
        for p in recent_payments:
            all_logs.append(AuditLog(
                data_hora=p.data_pagamento or hoje - timedelta(days=2),
                id_usuario=u_staff1.id,
                usuario_nome=p.registrado_por_nome or u_staff1.nome,
                acao="PAYMENT_RECEIVED",
                entidade="Transaction",
                entidade_id=str(p.id),
                descricao=f"Baixa de £{float(p.valor):.2f} ({p.tipo}) confirmada via {p.forma_pagamento or 'Card'} no Contrato #{p.id_contrato}",
                ip_origem="127.0.0.1"
            ))

        print("Seeding realistic Claims & Storage processes (McAms, ALS, 365)...")
        claims_data = [
            # 1. McAms: Em Aberto, Indicação Pendente (vencendo em breve, 8 dias atrás aprovado)
            Claim(
                claim_number="MC-2026-8819",
                empresa_parceira="McAms",
                cliente_nome="Gabriel Santos",
                cliente_telefone="07890123456",
                placa="BK22NMX",
                modelo_moto="Yamaha NMAX 125",
                status="Em Aberto",
                data_acidente=hoje_date - timedelta(days=12),
                data_aprovacao=hoje_date - timedelta(days=8),
                valor_indicacao=600.00,
                prazo_indicacao=hoje_date - timedelta(days=8) + timedelta(days=14),
                status_indicacao="Pendente",
                data_entrada_storage=hoje_date - timedelta(days=10),
                prazo_liberacao_storage=hoje_date - timedelta(days=8) + timedelta(days=28),
                status_storage="No Pátio",
                valor_diaria_storage=18.50,
                observacoes="Terceiro bateu na traseira no semáforo em Digbeth. Documentação enviada à McAms.",
                criado_por_nome=u_aline.nome
            ),
            # 2. ALS: Em Aberto, Indicação Atrasada (+14 dias de aprovação), moto liberada sem invoice
            Claim(
                claim_number="ALS-UK-4412",
                empresa_parceira="ALS",
                cliente_nome="Lucas Oliveira",
                cliente_telefone="07512345678",
                placa="BM19WKP",
                modelo_moto="Honda Vision 110",
                status="Em Aberto",
                data_acidente=hoje_date - timedelta(days=25),
                data_aprovacao=hoje_date - timedelta(days=18),
                valor_indicacao=550.00,
                prazo_indicacao=hoje_date - timedelta(days=18) + timedelta(days=14),
                status_indicacao="Atrasado",
                data_entrada_storage=hoje_date - timedelta(days=22),
                prazo_liberacao_storage=hoje_date - timedelta(days=18) + timedelta(days=28),
                data_liberacao_storage=hoje_date - timedelta(days=2),
                status_storage="Liberado",
                valor_diaria_storage=18.50,
                dias_storage=20,
                valor_total_storage=370.00,
                observacoes="Moto retirada pelo guincho da ALS. Falta Aline emitir e enviar o invoice.",
                criado_por_nome=u_aline.nome
            ),
            # 3. 365: Em Aberto, Indicação Paga, Invoice de Storage Enviado (aguardando pagamento)
            Claim(
                claim_number="365-CLM-9031",
                empresa_parceira="365",
                cliente_nome="Rafael Costa",
                cliente_telefone="07455667788",
                placa="BP23XMN",
                modelo_moto="Yamaha XMAX 125",
                status="Em Aberto",
                data_acidente=hoje_date - timedelta(days=35),
                data_aprovacao=hoje_date - timedelta(days=30),
                valor_indicacao=500.00,
                prazo_indicacao=hoje_date - timedelta(days=30) + timedelta(days=14),
                status_indicacao="Pago",
                data_pagamento_indicacao=hoje_date - timedelta(days=20),
                data_entrada_storage=hoje_date - timedelta(days=34),
                prazo_liberacao_storage=hoje_date - timedelta(days=30) + timedelta(days=28),
                data_liberacao_storage=hoje_date - timedelta(days=10),
                status_storage="Invoice Enviado",
                valor_diaria_storage=18.50,
                dias_storage=24,
                valor_total_storage=444.00,
                data_envio_invoice=hoje_date - timedelta(days=8),
                prazo_pagamento_invoice=hoje_date - timedelta(days=8) + timedelta(days=14),
                status_pagamento_storage="Pendente",
                observacoes="Invoice #FF-INV-101 enviado para contas da 365. Aguardando TED.",
                criado_por_nome=u_aline.nome
            ),
            # 4. McAms: Concluído (Tudo Pago)
            Claim(
                claim_number="MC-2026-7730",
                empresa_parceira="McAms",
                cliente_nome="Rodrigo Lima",
                cliente_telefone="07322114455",
                placa="WN21TYU",
                modelo_moto="Honda Vision 110",
                status="Concluido",
                data_acidente=hoje_date - timedelta(days=60),
                data_aprovacao=hoje_date - timedelta(days=50),
                valor_indicacao=600.00,
                prazo_indicacao=hoje_date - timedelta(days=50) + timedelta(days=14),
                status_indicacao="Pago",
                data_pagamento_indicacao=hoje_date - timedelta(days=40),
                data_entrada_storage=hoje_date - timedelta(days=58),
                prazo_liberacao_storage=hoje_date - timedelta(days=50) + timedelta(days=28),
                data_liberacao_storage=hoje_date - timedelta(days=35),
                status_storage="Pago",
                valor_diaria_storage=18.50,
                dias_storage=23,
                valor_total_storage=425.50,
                data_envio_invoice=hoje_date - timedelta(days=34),
                prazo_pagamento_invoice=hoje_date - timedelta(days=34) + timedelta(days=14),
                status_pagamento_storage="Pago",
                data_pagamento_storage=hoje_date - timedelta(days=24),
                observacoes="Processo concluído com sucesso. Todos os valores recebidos e conferidos.",
                criado_por_nome=u_aline.nome
            )
        ]
        db.session.add_all(claims_data)
        db.session.flush()

        for cl in claims_data:
            all_logs.append(AuditLog(
                data_hora=hoje - timedelta(days=10),
                id_usuario=u_aline.id,
                usuario_nome=u_aline.nome,
                acao="CREATE_CLAIM",
                entidade="Claim",
                entidade_id=str(cl.id),
                descricao=f"Claim #{cl.claim_number} ({cl.empresa_parceira}) cadastrado para {cl.cliente_nome} ({cl.placa}) por {u_aline.nome}",
                ip_origem="127.0.0.1"
            ))

        db.session.add_all(all_logs)
        db.session.commit()

        print("\n=======================================================")
        print("🎉 RICH REALISTIC SEED COMPLETED SUCCESSFULLY!")
        print(f"✓ {User.query.count()} Staff Accounts (Thiago Brandão [Admin], Carlos Silva, Emma Watson, Aline Ferreira [Claims])")
        print(f"✓ {Claim.query.count()} Claims & Storage processes (McAms, ALS, 365)")
        print(f"✓ {Motorcycle.query.count()} Motorbikes in Birmingham Fleet:")
        print("    - 4 Available (including 1 with MOT due in 18d)")
        print("    - 13 Rented (including 1 with Tax due in 14d, 1 with Cancelled Insurance, 1 with 15-day check overdue)")
        print("    - 1 Maintenance (with MOT expired -4 days)")
        print(f"✓ {Client.query.count()} Clients with varied document profiles:")
        print("    - Full UK Licences (Front + Back + Address, no CBT)")
        print("    - Provisional + CBT Couriers (Front + Back + CBT + Address)")
        print("    - Incomplete (Missing Back, Missing Address, or New Lead)")
        print(f"✓ {Contract.query.count()} Contracts:")
        print("    - Up to date active rentals")
        print("    - Overdue rentals (1 week and 2 weeks behind in rent)")
        print("    - 14-day Deposit Hold (quarantine after bike return)")
        print("    - Completed rentals (1 with £50 damage deduction, 1 with full refund)")
        print(f"✓ {FinancialTransaction.query.count()} Financial Ledger Transactions")
        print(f"✓ {Inspection.query.count()} Check-out and Check-in Inspections with odometer mileages & photos")
        print(f"✓ {ContractAttachment.query.count()} Official Signed Agreement Attachments (PDFs & Scans)")
        print(f"✓ {Contract.query.filter(Contract.assinatura_cliente_inicial.isnot(None)).count()} Contracts with touch-screen digital signatures")
        print(f"✓ {AuditLog.query.count()} Audit Log activities across the timeline")
        print("=======================================================\n")

if __name__ == '__main__':
    seed()
