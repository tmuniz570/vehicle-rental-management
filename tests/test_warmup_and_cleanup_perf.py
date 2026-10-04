import os
import sys
import unittest
from datetime import datetime

# Set root dir in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import app, db
from warmup import run_warmup
from cleanup_uploads import collect_valid_files

class TestWarmupAndCleanupPerf(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_warmup_endpoint_unauthorized(self):
        # Request with external IP and no cron key should be blocked
        res = self.client.get('/api/jobs/warmup', headers={'X-Forwarded-For': '203.0.113.195'})
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertIn('error', data)

    def test_warmup_endpoint_with_cron_key(self):
        # Request with valid X-Cron-Key should succeed
        res = self.client.get(
            '/api/jobs/warmup',
            headers={
                'X-Cron-Key': 'ffmotors-internal-cron-key-2026',
                'X-Forwarded-For': '203.0.113.195'
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('duration_ms', data)
        self.assertIn('warmed_at', data)
        self.assertIn('summary', data)
        summary = data['summary']
        self.assertIn('total_motos', summary)
        self.assertIn('contratos_ativos', summary)
        print(f"✓ /api/jobs/warmup completed successfully via HTTP in {data['duration_ms']}ms")

    def test_warmup_script_standalone(self):
        elapsed = run_warmup()
        self.assertIsInstance(elapsed, float)
        self.assertGreater(elapsed, 0.0)
        print(f"✓ warmup.py run_warmup() executed successfully in {elapsed}ms")

    def test_cleanup_uploads_collect_valid_files_optimized(self):
        valid_files = collect_valid_files()
        self.assertIsInstance(valid_files, set)
        print(f"✓ Optimized cleanup_uploads.collect_valid_files() returned {len(valid_files)} valid file entries cleanly")

if __name__ == '__main__':
    unittest.main()
