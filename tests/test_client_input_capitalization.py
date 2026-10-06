import os
import sys
import unittest
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, capitalize_words
from database import Client, User

class TestClientInputCapitalization(unittest.TestCase):
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

        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            admin = User.query.first()

        if admin:
            admin.is_admin = True
            admin.perm_alugueis = True
            db.session.commit()

            with self.client.session_transaction() as sess:
                sess['_user_id'] = str(admin.id)
                sess['_fresh'] = True
                sess['last_activity'] = datetime.now().timestamp()

    def tearDown(self):
        self.app_context.pop()

    def test_capitalize_words_helper(self):
        """Test that capitalize_words formats names and addresses properly."""
        self.assertEqual(capitalize_words("john smith"), "John Smith")
        self.assertEqual(capitalize_words("mary-ann smith"), "Mary-Ann Smith")
        self.assertEqual(capitalize_words("o'connor"), "O'Connor")
        self.assertEqual(capitalize_words("123 high st, birmingham B4 7ET, UK"), "123 High St, Birmingham B4 7ET, UK")
        self.assertEqual(capitalize_words("45 park avenue, birmingham b66 3ew"), "45 Park Avenue, Birmingham B66 3ew")
        self.assertEqual(capitalize_words(""), "")
        self.assertIsNone(capitalize_words(None))

    def test_html_templates_attributes(self):
        """Test that cadastro_cliente and clientes templates have the required mobile keyboard and autocorrect attributes."""
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        
        # 1. cadastro_cliente.html
        with open(os.path.join(root_dir, 'templates', 'cadastro_cliente.html'), 'r', encoding='utf-8') as f:
            cadastro_html = f.read()

        self.assertIn('id="nome"', cadastro_html)
        self.assertIn('autocapitalize="words"', cadastro_html)
        self.assertIn('autocorrect="off"', cadastro_html)
        self.assertIn('spellcheck="false"', cadastro_html)
        self.assertIn('id="endereco"', cadastro_html)

        # 2. clientes.html
        with open(os.path.join(root_dir, 'templates', 'clientes.html'), 'r', encoding='utf-8') as f:
            clientes_html = f.read()

        self.assertIn('id="edit_nome"', clientes_html)
        self.assertIn('id="edit_endereco"', clientes_html)
        self.assertIn('autocapitalize="words"', clientes_html)
        self.assertIn('autocorrect="off"', clientes_html)

    def test_api_client_creation_and_update_capitalization(self):
        """Test that /api/clientes POST and PUT automatically capitalizes each word in name and address."""
        test_tel = f"07888{int(datetime.now().timestamp() * 1000) % 1000000:06d}"

        # Create client with all-lowercase input
        res = self.client.post('/api/clientes', data={
            'nome': 'carlos eduardo da silva',
            'telefone': test_tel,
            'email': f'carlos.{test_tel}@ffmotors.co.uk',
            'endereco': '155 windmill lane, birmingham b66 3ew'
        })
        self.assertEqual(res.status_code, 201, res.get_json())
        client_id = res.get_json()['id']

        # Verify capitalized values in database
        client_obj = db.session.get(Client, client_id)
        self.assertEqual(client_obj.nome, 'Carlos Eduardo Da Silva')
        self.assertEqual(client_obj.endereco, '155 Windmill Lane, Birmingham B66 3ew')

        # Update client with all-lowercase input via PUT (JSON)
        res_put = self.client.put(f'/api/clientes/{client_id}', json={
            'nome': 'carlos e. silva',
            'endereco': '12 soho road, birmingham b21 9st'
        })
        self.assertEqual(res_put.status_code, 200, res_put.get_json())

        db.session.refresh(client_obj)
        self.assertEqual(client_obj.nome, 'Carlos E. Silva')
        self.assertEqual(client_obj.endereco, '12 Soho Road, Birmingham B21 9st')

        # Cleanup
        db.session.delete(client_obj)
        db.session.commit()

if __name__ == '__main__':
    unittest.main()
