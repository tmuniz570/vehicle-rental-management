import os
import sys
import unittest
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, is_safe_redirect_url
from database import User, delete_file_if_exists

class TestSecurityHardening(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        self._orig_csrf = app.config.get('WTF_CSRF_ENABLED')
        app.config['WTF_CSRF_ENABLED'] = True

    def tearDown(self):
        if self._orig_csrf is not None:
            app.config['WTF_CSRF_ENABLED'] = self._orig_csrf
        else:
            app.config.pop('WTF_CSRF_ENABLED', None)
        self.app_context.pop()

    def test_open_redirect_protection(self):
        """Verifica que URLs perigosas para Open Redirect são estritamente rejeitadas."""
        self.assertFalse(is_safe_redirect_url("//evil.com"))
        self.assertFalse(is_safe_redirect_url("//evil.com/phishing"))
        self.assertFalse(is_safe_redirect_url("/\\evil.com"))
        self.assertFalse(is_safe_redirect_url("\\evil.com"))
        self.assertFalse(is_safe_redirect_url("https://malicious.com"))
        self.assertFalse(is_safe_redirect_url("http://malicious.com"))
        self.assertFalse(is_safe_redirect_url(""))
        self.assertFalse(is_safe_redirect_url(None))

        # URLs internas válidas
        self.assertTrue(is_safe_redirect_url("/"))
        self.assertTrue(is_safe_redirect_url("/financeiro"))
        self.assertTrue(is_safe_redirect_url("/contratos/1"))
        print("\n✓ Open Redirect protection strictly validated.")

    def test_csrf_cannot_be_bypassed_with_cron_key_on_normal_routes(self):
        """Garante que rotas comuns não podem burlar CSRF passando cron_key."""
        # Cria sessão de usuário autenticado
        user = User.query.first()
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()
            sess['_csrf_token'] = 'valid-csrf-token-12345'

        # Tenta mutation POST em rota comum sem token CSRF, tentando burlar com ?cron_key=bypass
        resp = self.client.post('/api/clientes?cron_key=bypass', json={'nome': 'Test'})
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn('CSRF', data.get('error', '') + data.get('erro', ''))
        print("✓ CSRF bypass attempt using ?cron_key=bypass successfully blocked with 400.")

    def test_delete_file_never_touches_project_root(self):
        """Verifica que delete_file_if_exists nunca exclui arquivos na raiz do projeto (cwd)."""
        app_file = os.path.join(os.getcwd(), 'app.py')
        self.assertTrue(os.path.exists(app_file), "app.py must exist in cwd")

        # Tenta chamar delete_file_if_exists passando 'app.py'
        delete_file_if_exists('app.py')
        delete_file_if_exists('/static/uploads/../../app.py')

        # app.py deve continuar existindo intacto
        self.assertTrue(os.path.exists(app_file), "app.py must NEVER be deleted by delete_file_if_exists")
        print("✓ Critical project file deletion protection validated.")

    def test_busca_rapida_requires_rental_permission(self):
        """Garante que usuário sem permissão de aluguel não acessa busca rápida."""
        # Cria ou obtém usuário exclusivo de claims (sem aluguel)
        claims_user = User.query.filter_by(email='claims_only_test@ffmotors.co.uk').first()
        if not claims_user:
            claims_user = User(
                nome="Claims Only Staff",
                email="claims_only_test@ffmotors.co.uk",
                role="staff",
                is_admin=False,
                perm_alugueis=False,
                perm_claims=True,
                ativo=True
            )
            claims_user.set_password("Claims123!")
            db.session.add(claims_user)
            db.session.commit()

        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(claims_user.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

        resp = self.client.get('/api/busca-rapida?q=XX1')
        self.assertEqual(resp.status_code, 403)
        print("✓ /api/busca-rapida access control verified: 403 Forbidden for claims-only user.")

    def test_max_content_length_configured(self):
        """Verifica que MAX_CONTENT_LENGTH está devidamente configurado."""
        self.assertIn('MAX_CONTENT_LENGTH', app.config)
        self.assertGreaterEqual(app.config['MAX_CONTENT_LENGTH'], 1024 * 1024)
        print(f"✓ MAX_CONTENT_LENGTH verified: {app.config['MAX_CONTENT_LENGTH'] / (1024*1024):.0f} MB limit.")

if __name__ == '__main__':
    unittest.main()
