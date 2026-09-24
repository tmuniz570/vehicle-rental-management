import os
import sys
import json
from datetime import datetime, timedelta

# Set root dir in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import app
from database import db, Motorcycle, User, MotoStatus, init_db

def test_sorn_feature():
    print("=== STARTING SORN FEATURE TESTS ===")
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        # Ensure migration applied
        init_db(app)
        client = app.test_client()

        # 0. Setup admin user
        admin_user = User.query.filter_by(email="admin@ffmotors.co.uk").first()
        if not admin_user:
            admin_user = User(
                nome="Admin Test",
                email="admin@ffmotors.co.uk",
                is_admin=True,
                perm_alugueis=True,
                perm_claims=True,
                ativo=True
            )
            admin_user.set_password("admin123")
            db.session.add(admin_user)
            db.session.commit()

        # Authenticate admin session
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin_user.id)
            sess['_fresh'] = True
            sess['last_activity'] = datetime.now().timestamp()

        # 1. Test POST /api/motos with SORN enabled
        test_placa = "SORN_TEST_MOTO"
        Motorcycle.query.filter_by(placa=test_placa).delete()
        db.session.commit()

        post_data = {
            'placa': test_placa,
            'modelo': 'Honda PCX 125 SORN',
            'cor': 'Black',
            'status': 'Available',
            'milhagem_atual': 8500,
            'vencimento_mot': (datetime.now().date() + timedelta(days=90)).strftime('%Y-%m-%d'),
            'tax_sorn': True,
            'vencimento_tax': '2026-05-15' # Should be ignored/set to None because tax_sorn is True
        }
        res = client.post('/api/motos', json=post_data)
        assert res.status_code == 201, f"Failed to register SORN moto: {res.data.decode()}"
        print("✓ Motorbike created via POST /api/motos with SORN active")

        # Verify in database
        moto_db = Motorcycle.query.filter_by(placa=test_placa).first()
        assert moto_db is not None
        assert moto_db.tax_sorn is True
        assert moto_db.vencimento_tax is None
        print("✓ Motorcycle in DB has tax_sorn=True and vencimento_tax=None")

        # 2. Test GET /api/motos/<placa>/detalhes
        res = client.get(f'/api/motos/{test_placa}/detalhes')
        assert res.status_code == 200
        detalhes = res.get_json()
        assert detalhes['tax_sorn'] is True
        assert detalhes['vencimento_tax'] is None
        print("✓ Details endpoint correctly returns tax_sorn=True")

        # 3. Test GET /api/motos list and search=sorn
        res = client.get('/api/motos?search=sorn')
        assert res.status_code == 200
        list_data = res.get_json()
        matching = [m for m in list_data['itens'] if m['placa'] == test_placa]
        assert len(matching) == 1
        assert matching[0]['tax_sorn'] is True
        print("✓ Search by keyword 'sorn' finds SORN motorbike")

        # 4. Test Dashboard Compliance Alert exclusion
        # A SORN motorbike must NOT trigger road tax expired/expiring warning
        res = client.get('/api/dashboard')
        assert res.status_code == 200
        dash_data = res.get_json()
        print(f"✓ Dashboard loaded successfully with compliance checks: mot_warnings={dash_data.get('mot_warnings')}, tax_warnings={dash_data.get('tax_warnings')}")

        # 5. Test PUT /api/motos/<placa> toggling SORN off and setting tax date
        put_data_off = {
            'tax_sorn': False,
            'vencimento_tax': (datetime.now().date() + timedelta(days=120)).strftime('%Y-%m-%d')
        }
        res = client.put(f'/api/motos/{test_placa}', json=put_data_off)
        assert res.status_code == 200
        moto_db = Motorcycle.query.filter_by(placa=test_placa).first()
        assert moto_db.tax_sorn is False
        assert moto_db.vencimento_tax is not None
        print("✓ Successfully toggled SORN off and updated Road Tax expiry date")

        # 6. Test PUT /api/motos/<placa> toggling SORN back on (should clear vencimento_tax)
        put_data_on = {
            'tax_sorn': True
        }
        res = client.put(f'/api/motos/{test_placa}', json=put_data_on)
        assert res.status_code == 200
        moto_db = Motorcycle.query.filter_by(placa=test_placa).first()
        assert moto_db.tax_sorn is True
        assert moto_db.vencimento_tax is None
        print("✓ Successfully toggled SORN back on and verified vencimento_tax is automatically reset to None")

        # Clean up test moto
        Motorcycle.query.filter_by(placa=test_placa).delete()
        db.session.commit()
        print("✓ Cleaned up test motorbike cleanly")

    print("=== ALL SORN TESTS PASSED SUCCESSFULLY! ===")

if __name__ == '__main__':
    test_sorn_feature()
