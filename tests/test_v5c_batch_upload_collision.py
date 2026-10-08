"""
test_v5c_batch_upload_collision.py - Test Batch Upload Collision Prevention and File Isolation
FF Motors APP
"""

import io
import os
import sys
import time
import unittest
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import app, db
from database import Motorcycle, MotorcycleV5C, MotorcycleTracker, User

def create_test_image(color=(255, 0, 0), text="TEST"):
    img = Image.new('RGB', (120, 120), color=color)
    bio = io.BytesIO()
    img.save(bio, format='JPEG')
    bio.seek(0)
    return bio

class TestV5CBatchUploadCollision(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        
        # Authenticate test client as admin
        with self.client.session_transaction() as sess:
            admin = User.query.filter_by(role='admin').first()
            if not admin:
                admin = User(
                    nome='Admin Test',
                    email='admin_collision_test@ffmotors.co.uk',
                    role='admin',
                    is_admin=True,
                    perm_alugueis=True,
                    perm_claims=True,
                    perm_financeiro=True
                )
                admin.set_password('Admin123!')
                db.session.add(admin)
                db.session.commit()
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True
            sess['last_activity'] = time.time()
            
        self.test_placa = 'COLLISION99'
        moto = Motorcycle.query.get(self.test_placa)
        if not moto:
            moto = Motorcycle(
                placa=self.test_placa,
                modelo='Honda PCX 125',
                cor='Black',
                status='Available',
                milhagem_atual=1200
            )
            db.session.add(moto)
            db.session.commit()
            
    def tearDown(self):
        # Clean up records and files created during tests
        upload_folder = self.app.config.get('UPLOAD_FOLDER', os.path.join(self.app.root_path, 'static', 'uploads'))
        v5cs = MotorcycleV5C.query.filter_by(placa=self.test_placa).all()
        for v in v5cs:
            if v.url_arquivo:
                fpath = os.path.join(upload_folder, os.path.basename(v.url_arquivo))
                if os.path.exists(fpath):
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass
            db.session.delete(v)
            
        trackers = MotorcycleTracker.query.filter_by(placa=self.test_placa).all()
        for t in trackers:
            if t.url_fotos:
                for u in t.url_fotos.split(','):
                    fpath = os.path.join(upload_folder, os.path.basename(u.strip()))
                    if os.path.exists(fpath):
                        try:
                            os.remove(fpath)
                        except Exception:
                            pass
            db.session.delete(t)
            
        moto = Motorcycle.query.get(self.test_placa)
        if moto:
            db.session.delete(moto)
        db.session.commit()
        self.ctx.pop()
        
    def test_v5c_batch_upload_with_identical_filenames_preserves_both_files(self):
        """
        Simulates iPhone iOS camera behavior where multiple captured photos
        are all named 'image.jpg'. Verifies both files are preserved independently.
        """
        upload_folder = self.app.config.get('UPLOAD_FOLDER', os.path.join(self.app.root_path, 'static', 'uploads'))
        
        # Photo 1 (Red) and Photo 2 (Blue), BOTH named 'image.jpg'
        img1 = create_test_image(color=(255, 0, 0)) # Red
        img2 = create_test_image(color=(0, 0, 255)) # Blue
        
        data = {
            'categoria_doc': 'v5c',
            'v5c_arquivos': [
                (img1, 'image.jpg'),
                (img2, 'image.jpg')
            ]
        }
        
        res = self.client.post(
            f'/api/motos/{self.test_placa}/v5c',
            data=data,
            content_type='multipart/form-data'
        )
        self.assertEqual(res.status_code, 201)
        resp_json = res.get_json()
        self.assertEqual(len(resp_json['v5c_arquivos']), 2)
        
        rec1_info = resp_json['v5c_arquivos'][0]
        rec2_info = resp_json['v5c_arquivos'][1]
        
        url1 = rec1_info['url_arquivo']
        url2 = rec2_info['url_arquivo']
        
        # 1. URLs MUST BE DIFFERENT
        self.assertNotEqual(url1, url2, "V5C upload URLs must be completely distinct!")
        
        fpath1 = os.path.join(upload_folder, os.path.basename(url1))
        fpath2 = os.path.join(upload_folder, os.path.basename(url2))
        
        # 2. Both physical files MUST exist on disk
        self.assertTrue(os.path.exists(fpath1), f"Physical file 1 must exist: {fpath1}")
        self.assertTrue(os.path.exists(fpath2), f"Physical file 2 must exist: {fpath2}")
        
        # 3. Check image content: File 1 was red, File 2 was blue. They must not have overwritten each other!
        im1_loaded = Image.open(fpath1)
        im2_loaded = Image.open(fpath2)
        
        p1 = im1_loaded.getpixel((60, 60))
        p2 = im2_loaded.getpixel((60, 60))
        
        # Red channel > Blue channel for image 1, Blue channel > Red channel for image 2
        self.assertGreater(p1[0], p1[2], "Photo 1 should remain the original red image (not overwritten)")
        self.assertGreater(p2[2], p2[0], "Photo 2 should remain the original blue image")
        
        # 4. Deleting Record 1 MUST NOT delete Record 2's file from disk
        del_res = self.client.delete(f'/api/motos/{self.test_placa}/v5c/{rec1_info["id"]}')
        self.assertEqual(del_res.status_code, 200)
        
        self.assertFalse(os.path.exists(fpath1), "Physical file 1 should be removed after its record is deleted")
        self.assertTrue(os.path.exists(fpath2), "Physical file 2 MUST REMAIN on disk after record 1 is deleted!")
        
    def test_shared_file_deletion_safety(self):
        """
        Verifies that if two records hypothetically point to the same file URL,
        deleting one record does not delete the physical file on disk.
        """
        upload_folder = self.app.config.get('UPLOAD_FOLDER', os.path.join(self.app.root_path, 'static', 'uploads'))
        
        # Create a single test file
        test_filename = 'shared_safety_test.webp'
        test_path = os.path.join(upload_folder, test_filename)
        with open(test_path, 'wb') as f:
            f.write(b'RIFF....WEBP')
            
        rec1 = MotorcycleV5C(
            placa=self.test_placa,
            url_arquivo=f"/static/uploads/{test_filename}",
            nome_original='Page 1',
            tipo_arquivo='image',
            categoria_doc='v5c'
        )
        rec2 = MotorcycleV5C(
            placa=self.test_placa,
            url_arquivo=f"/static/uploads/{test_filename}",
            nome_original='Page 2',
            tipo_arquivo='image',
            categoria_doc='v5c'
        )
        db.session.add_all([rec1, rec2])
        db.session.commit()
        
        # Delete record 1
        res = self.client.delete(f'/api/motos/{self.test_placa}/v5c/{rec1.id}')
        self.assertEqual(res.status_code, 200)
        
        # File MUST STILL EXIST because rec2 is still referencing it!
        self.assertTrue(os.path.exists(test_path), "File must NOT be deleted while rec2 still references it!")
        
        # Now delete record 2
        res2 = self.client.delete(f'/api/motos/{self.test_placa}/v5c/{rec2.id}')
        self.assertEqual(res2.status_code, 200)
        
        # Now file should be gone since no other records reference it
        self.assertFalse(os.path.exists(test_path), "File should be deleted now that no records reference it")

    def test_tracker_batch_photos_identical_filenames(self):
        """
        Verifies tracker photo batch upload with identical filenames also generates distinct files.
        """
        upload_folder = self.app.config.get('UPLOAD_FOLDER', os.path.join(self.app.root_path, 'static', 'uploads'))
        
        img1 = create_test_image(color=(100, 100, 0))
        img2 = create_test_image(color=(0, 100, 100))
        
        data = {
            'numero': 'TRACKER99999',
            'tipo_propriedade': 'Company',
            'observacoes': 'Batch photo test',
            'fotos': [
                (img1, 'photo.jpg'),
                (img2, 'photo.jpg')
            ]
        }
        
        res = self.client.post(
            f'/api/motos/{self.test_placa}/trackers',
            data=data,
            content_type='multipart/form-data'
        )
        self.assertEqual(res.status_code, 201)
        resp_json = res.get_json()
        photos = resp_json['tracker']['fotos']
        self.assertEqual(len(photos), 2)
        self.assertNotEqual(photos[0], photos[1], "Tracker photos must have distinct URLs")
        
        fpath1 = os.path.join(upload_folder, os.path.basename(photos[0]))
        fpath2 = os.path.join(upload_folder, os.path.basename(photos[1]))
        
        self.assertTrue(os.path.exists(fpath1))
        self.assertTrue(os.path.exists(fpath2))

if __name__ == '__main__':
    unittest.main()
