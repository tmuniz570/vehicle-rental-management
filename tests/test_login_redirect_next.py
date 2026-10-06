import os
import sys
import unittest

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from database import User

class TestLoginRedirectNext(unittest.TestCase):
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

        # Ensure a test user exists
        self.test_email = "redirect_test_user@ffmotors.co.uk"
        self.test_password = "Password123!"
        user = User.query.filter_by(email=self.test_email).first()
        if not user:
            user = User(
                nome="Redirect Test User",
                email=self.test_email,
                role="admin",
                is_admin=True,
                ativo=True
            )
            user.set_password(self.test_password)
            db.session.add(user)
            db.session.commit()
        self.user = user

    def tearDown(self):
        self.app_context.pop()

    def test_unauthenticated_access_preserves_destination_and_query_params(self):
        """Unauthenticated user visiting /motos?status=Available gets redirected to /login?next=/motos?status=Available"""
        res = self.client.get('/motos?status=Available', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login?next=', res.location)
        self.assertIn('/motos?status=Available', res.location.replace('%3F', '?').replace('%3D', '='))

    def test_login_page_renders_next_url_in_form(self):
        """Visiting /login?next=/contratos/15 renders next_url in form action and hidden input"""
        res = self.client.get('/login?next=/contratos/15')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('name="next" value="/contratos/15"', html)
        self.assertIn('action="/login?next=/contratos/15"', html)

    def test_login_redirects_to_destination_url(self):
        """Logging in successfully redirects to next destination instead of dashboard"""
        dest = "/contratos/123"
        res = self.client.post(f'/login?next={dest}', data={
            'email': self.test_email,
            'password': self.test_password,
            'next': dest
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.location, dest)

    def test_already_authenticated_user_redirects_to_next(self):
        """Already authenticated user navigating to /login?next=/financeiro gets sent to /financeiro"""
        # Login first
        self.client.post('/login', data={
            'email': self.test_email,
            'password': self.test_password
        })

        # Navigates to /login with next
        res = self.client.get('/login?next=/financeiro', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.location, '/financeiro')

    def test_malicious_next_redirects_to_index(self):
        """Open redirect attempt is safely blocked and redirects to / (dashboard)"""
        malicious = "//evil.com/phishing"
        res = self.client.post(f'/login?next={malicious}', data={
            'email': self.test_email,
            'password': self.test_password,
            'next': malicious
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.location, '/')

    def test_login_or_logout_as_next_does_not_loop(self):
        """If next is /login or /logout, redirect to / to avoid loops"""
        res = self.client.post('/login?next=/login', data={
            'email': self.test_email,
            'password': self.test_password,
            'next': '/login'
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.location, '/')

if __name__ == '__main__':
    unittest.main()
