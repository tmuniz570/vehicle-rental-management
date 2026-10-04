import os
import sys
import unittest
import secrets

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from database import User, MASTER_ADMIN_EMAIL


class TestRootAdminProtection(unittest.TestCase):
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
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()

        # Ensure root admin exists
        self.root_admin = User.query.filter_by(email=MASTER_ADMIN_EMAIL).first()
        if not self.root_admin:
            self.root_admin = User(
                nome='Thiago Muniz',
                email=MASTER_ADMIN_EMAIL,
                role='admin',
                is_admin=True,
                ativo=True,
                perm_alugueis=True,
                perm_claims=True
            )
            self.root_admin.set_password(secrets.token_hex(16))
            db.session.add(self.root_admin)
            db.session.commit()
        else:
            self.root_admin.is_admin = True
            self.root_admin.ativo = True
            db.session.commit()

        # Ensure secondary admin exists
        self.sec_admin = User.query.filter_by(email='other_admin_test@ffmotors.com').first()
        if not self.sec_admin:
            self.sec_admin = User(
                nome='Secondary Admin',
                email='other_admin_test@ffmotors.com',
                role='admin',
                is_admin=True,
                ativo=True,
                perm_alugueis=True,
                perm_claims=True
            )
            self.sec_admin.set_password(secrets.token_hex(16))
            db.session.add(self.sec_admin)
            db.session.commit()

    def tearDown(self):
        # Clean up secondary admin if needed
        db.session.rollback()
        self.app_context.pop()

    def _login_as(self, user):
        from datetime import datetime
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

    def test_api_cannot_delete_root_admin(self):
        self._login_as(self.sec_admin)

        resp = self.client.delete(f'/api/usuarios/{self.root_admin.id}')
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertIn('root administrator', data.get('error', '').lower())

        # Verify still in db
        user = User.query.filter_by(email=MASTER_ADMIN_EMAIL).first()
        self.assertIsNotNone(user)

    def test_api_cannot_demote_admin_privileges(self):
        self._login_as(self.sec_admin)

        resp = self.client.put(
            f'/api/usuarios/{self.root_admin.id}',
            json={'is_admin': False}
        )
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertIn('cannot be removed', data.get('error', '').lower())

        user = User.query.filter_by(email=MASTER_ADMIN_EMAIL).first()
        self.assertTrue(user.is_admin)

    def test_api_cannot_suspend_root_admin(self):
        self._login_as(self.sec_admin)

        resp = self.client.put(
            f'/api/usuarios/{self.root_admin.id}',
            json={'ativo': False}
        )
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertIn('cannot be suspended', data.get('error', '').lower())

        user = User.query.filter_by(email=MASTER_ADMIN_EMAIL).first()
        self.assertTrue(user.ativo)

    def test_api_cannot_change_root_admin_email(self):
        self._login_as(self.sec_admin)

        resp = self.client.put(
            f'/api/usuarios/{self.root_admin.id}',
            json={'email': 'tampered_email@evil.com'}
        )
        self.assertEqual(resp.status_code, 403)

        user = User.query.filter_by(email=MASTER_ADMIN_EMAIL).first()
        self.assertIsNotNone(user)

    def test_orm_hook_prevents_db_delete(self):
        user = User.query.filter_by(email=MASTER_ADMIN_EMAIL).first()
        db.session.delete(user)
        with self.assertRaises(PermissionError):
            db.session.commit()
        db.session.rollback()

    def test_orm_hook_enforces_admin_and_active_on_update(self):
        user = User.query.filter_by(email=MASTER_ADMIN_EMAIL).first()
        user.is_admin = False
        user.ativo = False
        user.email = 'tampered@fake.com'
        db.session.commit()

        # Hook forces them back
        db.session.expire(user)
        refreshed = db.session.get(User, user.id)
        self.assertEqual(refreshed.email, MASTER_ADMIN_EMAIL)
        self.assertTrue(refreshed.is_admin)
        self.assertTrue(refreshed.ativo)


if __name__ == '__main__':
    unittest.main()
