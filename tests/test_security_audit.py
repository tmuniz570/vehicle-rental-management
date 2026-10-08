import os
import sys
import unittest
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from database import User

class TestSecurityHardeningAudit(unittest.TestCase):
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

        # Find or ensure admin user
        self.admin = User.query.filter_by(is_admin=True).first()
        if not self.admin:
            self.admin = User(
                nome="Security Audit Admin",
                email="security_audit_admin@ffmotors.co.uk",
                role="admin",
                is_admin=True,
                perm_alugueis=True,
                perm_financeiro=True,
                ativo=True
            )
            self.admin.set_password("AdminSecurePassword123!")
            db.session.add(self.admin)
            db.session.commit()
        else:
            self.admin.is_admin = True
            self.admin.perm_alugueis = True
            self.admin.perm_financeiro = True
            db.session.commit()

        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.admin.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

    def tearDown(self):
        self.app_context.pop()

    def test_relatorio_financeiro_xss_protection(self):
        """Verify that user search input is escaped and does not render raw XSS payloads in PDF/HTML report"""
        xss_payload = '<script>alert("xss")</script>'
        res = self.client.get(f'/financeiro/relatorio-pdf?search={xss_payload}')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        # Raw payload must NOT appear unescaped in HTML
        self.assertNotIn('<script>alert("xss")</script>', html)
        # Escaped version must appear safely
        self.assertIn('&lt;script&gt;alert(&#34;xss&#34;)&lt;/script&gt;', html)

    def test_password_length_validation_enforces_8_chars(self):
        """Creating an operator with less than 8 characters must return HTTP 400"""
        res_short = self.client.post('/api/usuarios', json={
            'nome': 'Short Pwd User',
            'email': 'shortpwd@ffmotors.co.uk',
            'password': '123456',  # 6 chars
            'is_admin': False
        })
        self.assertEqual(res_short.status_code, 400)
        self.assertIn('8 characters', res_short.get_json().get('error', ''))

        res_7 = self.client.post('/api/usuarios', json={
            'nome': 'Seven Pwd User',
            'email': 'sevenpwd@ffmotors.co.uk',
            'password': '1234567',  # 7 chars
            'is_admin': False
        })
        self.assertEqual(res_7.status_code, 400)

        # 8 chars must succeed
        User.query.filter_by(email='validpwd8@ffmotors.co.uk').delete()
        db.session.commit()
        res_8 = self.client.post('/api/usuarios', json={
            'nome': 'Valid Pwd User',
            'email': 'validpwd8@ffmotors.co.uk',
            'password': 'Password8!',  # 10 chars
            'is_admin': False
        })
        self.assertIn(res_8.status_code, [200, 201])
        # Cleanup
        new_u = User.query.filter_by(email='validpwd8@ffmotors.co.uk').first()
        if new_u:
            db.session.delete(new_u)
            db.session.commit()

    def test_alterar_propria_senha_enforces_8_chars(self):
        """Updating password with less than 8 characters must return HTTP 400"""
        self.admin.set_password("OldPassword123!")
        db.session.commit()

        res = self.client.post('/api/perfil/alterar-senha', json={
            'senha_atual': 'OldPassword123!',
            'nova_senha': '123456',
            'confirmar_senha': '123456'
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('8 caracteres', res.get_json().get('error', ''))

    def test_master_admin_default_password_warning_in_dashboard(self):
        """Dashboard flags aviso_senha_padrao if master admin is using Admin123!"""
        master = User.query.filter_by(email="tmuniz570@gmail.com").first()
        if not master:
            master = User(
                nome="Thiago Brandão",
                email="tmuniz570@gmail.com",
                role="admin",
                is_admin=True,
                ativo=True
            )
            db.session.add(master)
        
        orig_hash = master.password_hash
        try:
            # Test with default password
            master.set_password("Admin123!")
            db.session.commit()

            with self.client.session_transaction() as sess:
                sess['_user_id'] = str(master.id)
                sess['_fresh'] = True
                sess['last_activity'] = datetime.now().timestamp()

            res = self.client.get('/api/dashboard')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get('aviso_senha_padrao', False))

            # Test with custom secure password
            master.set_password("MyStrongSecretPassword2026!")
            db.session.commit()

            res2 = self.client.get('/api/dashboard')
            self.assertEqual(res2.status_code, 200)
            data2 = res2.get_json()
            self.assertFalse(data2.get('aviso_senha_padrao', False))
        finally:
            # Restore original password hash
            master.password_hash = orig_hash
            db.session.commit()

if __name__ == '__main__':
    unittest.main()
