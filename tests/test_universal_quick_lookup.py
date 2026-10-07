import unittest
from datetime import datetime
from app import app, db
from database import User

class TestUniversalQuickLookup(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        with self.app.app_context():
            # Setup an admin user with full permissions
            self.admin = User.query.filter_by(email="admin_lookup_test@ffmotors.co.uk").first()
            if not self.admin:
                self.admin = User(
                    email="admin_lookup_test@ffmotors.co.uk",
                    nome="Admin Lookup Test",
                    role="admin",
                    is_admin=True,
                    perm_alugueis=True,
                    perm_claims=True,
                    perm_financeiro=True,
                    ativo=True
                )
                self.admin.set_password("AdminPass123!")
                db.session.add(self.admin)
                db.session.commit()

            # Setup a claims-only user
            self.claims_user = User.query.filter_by(email="claims_only_lookup@ffmotors.co.uk").first()
            if not self.claims_user:
                self.claims_user = User(
                    email="claims_only_lookup@ffmotors.co.uk",
                    nome="Claims Only User",
                    role="claims",
                    is_admin=False,
                    perm_alugueis=False,
                    perm_claims=True,
                    perm_financeiro=False,
                    ativo=True
                )
                self.claims_user.set_password("ClaimsPass123!")
                db.session.add(self.claims_user)
                db.session.commit()

    def login_admin(self):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.admin.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

    def login_claims_only(self):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.claims_user.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

    def test_quick_lookup_rendered_on_allowed_pages(self):
        self.login_admin()
        
        pages_to_test = [
            '/',
            '/motos',
            '/clientes',
            '/contratos',
            '/vistorias',
            '/financeiro',
            '/contratos/novo',
            '/clientes/novo',
            '/motos/nova',
            '/vistorias/nova',
        ]

        for path in pages_to_test:
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, f"Page {path} should return 200")
            html = resp.data.decode('utf-8')
            
            # Universal Quick Lookup modal and sidebar trigger must be present
            self.assertIn('id="quickLookupModal"', html, f"Quick lookup modal must be in layout on {path}")
            self.assertIn('id="dashQuickSearch"', html, f"Quick search input must be on {path}")
            self.assertIn('id="sidebarSearchTrigger"', html, f"Sidebar fixed menu search trigger must be on {path}")
            self.assertIn('id="dashSearchResults"', html, f"Search results popover must be on {path}")
            
            # Exactly 1 instance of dashQuickSearch
            self.assertEqual(html.count('id="dashQuickSearch"'), 1, f"There must be exactly ONE dashQuickSearch on {path}")

            # Topbar is completely gone
            self.assertNotIn('class="app-topbar"', html, f"app-topbar should NOT exist on {path}")
        print("\n✓ Universal Quick Lookup verified in fixed sidebar menu and Command Palette modal across all operational pages.")

    def test_quick_lookup_excluded_on_claims_and_users(self):
        self.login_admin()

        excluded_pages = ['/claims', '/usuarios']

        for path in excluded_pages:
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, f"Page {path} should return 200")
            html = resp.data.decode('utf-8')

            # Quick lookup modal and sidebar trigger must NOT be rendered on claims or users
            self.assertNotIn('id="dashQuickSearch"', html, f"Quick lookup must NOT be on {path}")
            self.assertNotIn('id="quickLookupModal"', html, f"quickLookupModal must NOT be on {path}")
            self.assertNotIn('id="sidebarSearchTrigger"', html, f"sidebarSearchTrigger must NOT be on {path}")
        print("✓ Quick Lookup correctly excluded from /claims and /usuarios.")

    def test_quick_lookup_excluded_for_claims_only_user(self):
        self.login_claims_only()

        # Accessing /claims as claims user
        resp = self.client.get('/claims')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertNotIn('id="dashQuickSearch"', html, "Quick lookup must NOT be on claims page")

        # Trying to access /api/busca-rapida should return 403 Forbidden
        api_resp = self.client.get('/api/busca-rapida?q=XX10')
        self.assertEqual(api_resp.status_code, 403, "/api/busca-rapida must be forbidden for claims-only user")
        print("✓ Quick Lookup permissions enforced: claims-only user cannot access search API or UI.")

if __name__ == '__main__':
    unittest.main()
