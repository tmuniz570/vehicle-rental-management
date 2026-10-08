import unittest
from datetime import datetime, date
from app import app, db, User, Contract, Client, Motorcycle, FinancialTransaction, ContractType, ContractStatus

class TestContratosFinancialLink(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        with self.app.app_context():
            self.user = User.query.filter_by(email='admin_fin_link@ffmotors.co.uk').first()
            if not self.user:
                self.user = User(
                    nome='Test Admin Fin Link',
                    email='admin_fin_link@ffmotors.co.uk',
                    is_admin=True,
                    perm_financeiro=True,
                    perm_alugueis=True,
                    ativo=True
                )
                self.user.set_password('password123')
                db.session.add(self.user)
                db.session.commit()

    def test_financeiro_endpoint_filters_by_contrato_id(self):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.user.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

        with self.app.app_context():
            cli = Client.query.filter_by(email='fin_link_client@example.com').first()
            if not cli:
                cli = Client(nome='Customer Fin Link', email='fin_link_client@example.com', telefone='07111222333')
                db.session.add(cli)
                db.session.commit()

            bike = Motorcycle.query.filter_by(placa='FIN111').first()
            if not bike:
                bike = Motorcycle(placa='FIN111', modelo='Honda PCX 125', cor='Black', status='Rented')
                db.session.add(bike)
                db.session.commit()

            c1 = Contract(
                id_cliente=cli.id,
                placa=bike.placa,
                tipo_contrato=ContractType.RENT.value,
                status=ContractStatus.ACTIVE.value,
                valor_aluguel_semanal=80.0
            )
            c2 = Contract(
                id_cliente=cli.id,
                placa=bike.placa,
                tipo_contrato=ContractType.RENT.value,
                status=ContractStatus.ACTIVE.value,
                valor_aluguel_semanal=90.0
            )
            db.session.add_all([c1, c2])
            db.session.commit()

            t1 = FinancialTransaction(
                id_contrato=c1.id,
                tipo='Rent',
                valor=80.0,
                status='Pending',
                data_vencimento=date(2026, 10, 1)
            )
            t2 = FinancialTransaction(
                id_contrato=c2.id,
                tipo='Rent',
                valor=90.0,
                status='Pending',
                data_vencimento=date(2026, 10, 1)
            )
            db.session.add_all([t1, t2])
            db.session.commit()

            c1_id = c1.id
            c2_id = c2.id
            t1_id = t1.id
            t2_id = t2.id

        # Query /api/financeiro with contrato_id filter
        res = self.client.get(f'/api/financeiro?contrato_id={c1_id}')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        item_ids = [item['id'] for item in data['itens']]
        self.assertIn(t1_id, item_ids)
        self.assertNotIn(t2_id, item_ids)

    def test_contratos_html_and_js_contain_financial_link_features(self):
        with open('static/js/contratos.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
        self.assertIn('/financeiro?contrato_id=', js_content)
        self.assertIn('badge-financial-link', js_content)
        self.assertIn('badge-financial-dot', js_content)

        with open('static/js/financeiro.js', 'r', encoding='utf-8') as f:
            fin_js = f.read()
        self.assertIn("urlParams.get('contrato_id')", fin_js)

        with open('templates/contratos.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        self.assertIn('.badge-financial-link', html_content)
        self.assertIn('.badge-financial-dot', html_content)

    def test_financeiro_endpoint_filters_by_cliente_id(self):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.user.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

        with self.app.app_context():
            cli_a = Client.query.filter_by(email='cli_a_fin@example.com').first()
            if not cli_a:
                cli_a = Client(nome='Customer A Fin', email='cli_a_fin@example.com', telefone='07999888771')
                db.session.add(cli_a)
                db.session.commit()

            cli_b = Client.query.filter_by(email='cli_b_fin@example.com').first()
            if not cli_b:
                cli_b = Client(nome='Customer B Fin', email='cli_b_fin@example.com', telefone='07999888772')
                db.session.add(cli_b)
                db.session.commit()

            bike_a = Motorcycle.query.filter_by(placa='FINA01').first()
            if not bike_a:
                bike_a = Motorcycle(placa='FINA01', modelo='Honda PCX 125', cor='Black', status='Rented')
                db.session.add(bike_a)

            bike_b = Motorcycle.query.filter_by(placa='FINB02').first()
            if not bike_b:
                bike_b = Motorcycle(placa='FINB02', modelo='Yamaha NMAX 125', cor='Blue', status='Rented')
                db.session.add(bike_b)
            db.session.commit()

            ca = Contract(id_cliente=cli_a.id, placa=bike_a.placa, tipo_contrato=ContractType.RENT.value, status=ContractStatus.ACTIVE.value)
            cb = Contract(id_cliente=cli_b.id, placa=bike_b.placa, tipo_contrato=ContractType.RENT.value, status=ContractStatus.ACTIVE.value)
            db.session.add_all([ca, cb])
            db.session.commit()

            ta = FinancialTransaction(id_contrato=ca.id, tipo='Rent', valor=100.0, status='Pending', data_vencimento=date(2026, 10, 1))
            tb = FinancialTransaction(id_contrato=cb.id, tipo='Rent', valor=120.0, status='Pending', data_vencimento=date(2026, 10, 1))
            db.session.add_all([ta, tb])
            db.session.commit()

            cli_a_id = cli_a.id
            ta_id = ta.id
            tb_id = tb.id

        res = self.client.get(f'/api/financeiro?cliente_id={cli_a_id}')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        item_ids = [item['id'] for item in data['itens']]
        self.assertIn(ta_id, item_ids)
        self.assertNotIn(tb_id, item_ids)

    def test_clientes_html_and_js_contain_financial_link_features(self):
        with open('static/js/clientes.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
        self.assertIn('/financeiro?cliente_id=', js_content)
        self.assertIn('badge-financial-link', js_content)
        self.assertNotIn('btn-action-fin', js_content)

        with open('templates/clientes.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        self.assertIn('.badge-financial-link', html_content)
        self.assertNotIn('.btn-action-fin', html_content)

if __name__ == '__main__':
    unittest.main()
