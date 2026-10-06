import os
import sys
import unittest
import json

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from database import User

class TestPermFinanceiro(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_testing = app.config.get('TESTING', False)
        cls._orig_csrf = app.config.get('WTF_CSRF_ENABLED', True)
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False

    @classmethod
    def tearDownClass(cls):
        app.config['TESTING'] = cls._orig_testing
        app.config['WTF_CSRF_ENABLED'] = cls._orig_csrf

    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

        # Admin user
        self.admin_email = "admin_fin_test@ffmotors.co.uk"
        self.admin_pwd = "AdminPassword123!"
        admin = User.query.filter_by(email=self.admin_email).first()
        if not admin:
            admin = User(
                nome="Admin Fin Test",
                email=self.admin_email,
                role="admin",
                is_admin=True,
                perm_alugueis=True,
                perm_financeiro=True,
                perm_claims=True,
                ativo=True
            )
            admin.set_password(self.admin_pwd)
            db.session.add(admin)
            db.session.commit()
        else:
            admin.perm_financeiro = True
            admin.is_admin = True
            db.session.commit()
        self.admin = admin

        # Operator with perm_alugueis=True BUT perm_financeiro=False
        self.operador_email = "staff_sem_fin@ffmotors.co.uk"
        self.operador_pwd = "StaffPassword123!"
        operador = User.query.filter_by(email=self.operador_email).first()
        if not operador:
            operador = User(
                nome="Staff Sem Financeiro",
                email=self.operador_email,
                role="staff",
                is_admin=False,
                perm_alugueis=True,
                perm_financeiro=False,
                perm_claims=False,
                ativo=True
            )
            operador.set_password(self.operador_pwd)
            db.session.add(operador)
            db.session.commit()
        else:
            operador.perm_alugueis = True
            operador.perm_financeiro = False
            operador.is_admin = False
            db.session.commit()
        self.operador = operador

    def tearDown(self):
        self.app_context.pop()

    def login_as(self, email, password):
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    def test_user_without_financeiro_can_access_dashboard_and_overdue_report(self):
        """User with perm_financeiro=False MUST access Dashboard, /api/dashboard and /relatorios/vencidos"""
        self.login_as(self.operador_email, self.operador_pwd)

        # 1. Dashboard page
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)

        # 2. /api/dashboard should return full operational data
        res_api = self.client.get('/api/dashboard')
        self.assertEqual(res_api.status_code, 200)
        data = res_api.get_json()
        self.assertIn('due_today', data)
        self.assertIn('collected_today', data)
        self.assertIn('receita_vencida', data)

        # 3. Overdue report (/relatorios/vencidos)
        res_overdue = self.client.get('/relatorios/vencidos')
        self.assertEqual(res_overdue.status_code, 200)

    def test_user_without_financeiro_blocked_from_financeiro_pages_and_apis(self):
        """User with perm_financeiro=False is redirected from /financeiro and gets 403 on /api/financeiro"""
        self.login_as(self.operador_email, self.operador_pwd)

        # Page /financeiro should redirect to index ('/')
        res_fin_page = self.client.get('/financeiro', follow_redirects=False)
        self.assertEqual(res_fin_page.status_code, 302)
        self.assertTrue(res_fin_page.location.endswith('/') or '/index' in res_fin_page.location)

        # Page /relatorios (which redirects to /financeiro)
        res_rel = self.client.get('/relatorios', follow_redirects=False)
        self.assertEqual(res_rel.status_code, 302)

        # API /api/financeiro returns 403
        res_api_fin = self.client.get('/api/financeiro')
        self.assertEqual(res_api_fin.status_code, 403)
        data = res_api_fin.get_json()
        self.assertEqual(data.get('error'), 'Forbidden')

        # API /api/financeiro/resumo returns 403
        res_resumo = self.client.get('/api/financeiro/resumo')
        self.assertEqual(res_resumo.status_code, 403)

        # API /api/financeiro/fechamento-caixa returns 403
        res_fechamento = self.client.get('/api/financeiro/fechamento-caixa')
        self.assertEqual(res_fechamento.status_code, 403)

    def test_contract_financial_operations_remain_accessible_without_perm_financeiro(self):
        """User with perm_alugueis=True but perm_financeiro=False CAN manage charges/payments on contracts"""
        self.login_as(self.operador_email, self.operador_pwd)

        from database import Contract, FinancialTransaction, TransactionStatus
        contract = Contract.query.filter_by(status='Active').first()
        self.assertIsNotNone(contract, "At least one active contract should exist for testing")

        # 1. Create charge on contract via /api/contratos/<id>/cobrancas
        res_add = self.client.post(f'/api/contratos/{contract.id}/cobrancas', json={
            'tipo': 'Fine',
            'valor': 25.0,
            'data_vencimento': '2026-10-15',
            'referencia': 'Test parking ticket'
        })
        self.assertEqual(res_add.status_code, 201)
        cid = res_add.get_json()['id']

        # 2. Pay charge via /api/financeiro/pagar/<id>
        res_pay = self.client.post(f'/api/financeiro/pagar/{cid}', json={
            'forma_pagamento': 'Cash',
            'valor_pago': 25.0
        })
        self.assertEqual(res_pay.status_code, 200)

        # 3. Revert payment via /api/financeiro/<id>/reverter
        res_rev = self.client.post(f'/api/financeiro/{cid}/reverter', json={})
        self.assertEqual(res_rev.status_code, 200)

        # 4. Delete charge via DELETE /api/financeiro/<id>
        res_del = self.client.delete(f'/api/financeiro/{cid}')
        self.assertEqual(res_del.status_code, 200)

    def test_user_with_financeiro_can_access_financeiro(self):
        """User with perm_financeiro=True can access /financeiro and /api/financeiro"""
        self.login_as(self.admin_email, self.admin_pwd)

        res_fin_page = self.client.get('/financeiro')
        self.assertEqual(res_fin_page.status_code, 200)

        res_api_fin = self.client.get('/api/financeiro')
        self.assertEqual(res_api_fin.status_code, 200)

    def test_admin_can_toggle_perm_financeiro(self):
        """Admin can toggle perm_financeiro via API"""
        self.login_as(self.admin_email, self.admin_pwd)

        # Toggle to True
        res = self.client.put(f'/api/usuarios/{self.operador.id}', json={
            'perm_financeiro': True
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['usuario']['perm_financeiro'])

        # Refresh from db
        u = db.session.get(User, self.operador.id)
        self.assertTrue(u.perm_financeiro)
        self.assertTrue(u.pode_financeiro())

        # Toggle back to False
        res2 = self.client.put(f'/api/usuarios/{self.operador.id}', json={
            'perm_financeiro': False
        })
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertFalse(data2['usuario']['perm_financeiro'])

        u2 = db.session.get(User, self.operador.id)
        self.assertFalse(u2.perm_financeiro)
        self.assertFalse(u2.pode_financeiro())

if __name__ == '__main__':
    unittest.main()
