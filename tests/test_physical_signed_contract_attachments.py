import os
import io
import unittest
from datetime import datetime
from app import app, db, Contract, Client, Motorcycle, ContractAttachment, ContractType, ContractStatus, User

class TestPhysicalSignedContractAttachments(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app
        self.client = app.test_client()

        with app.app_context():
            self.admin = User.query.filter_by(is_admin=True).first()
            if not self.admin:
                self.admin = User(
                    nome="Admin Test",
                    email="admin_paper_sig@ffmotors.co.uk",
                    is_admin=True,
                    perm_alugueis=True,
                    ativo=True
                )
                self.admin.set_password("admin123")
                db.session.add(self.admin)
                db.session.commit()

            # Ensure test client & bike exist
            self.test_client = Client.query.filter_by(email="paper_sig_client@test.com").first()
            if not self.test_client:
                self.test_client = Client(
                    nome="Paper Signed Customer",
                    telefone="07111222333",
                    email="paper_sig_client@test.com",
                    endereco="123 High Street, Birmingham"
                )
                db.session.add(self.test_client)
                db.session.commit()
            self.test_client_id = self.test_client.id

            self.test_moto = Motorcycle.query.filter_by(placa="PSIG26T").first()
            if not self.test_moto:
                self.test_moto = Motorcycle(
                    placa="PSIG26T",
                    modelo="Honda PCX 125",
                    cor="Black",
                    status="Available"
                )
                db.session.add(self.test_moto)
                db.session.commit()
            self.test_moto_placa = self.test_moto.placa

    def test_paper_signed_contract_recognition_and_lifecycle(self):
        with self.app.app_context():
            # 1. Create a contract without any signature
            contrato = Contract(
                id_cliente=self.test_client_id,
                placa=self.test_moto_placa,
                tipo_contrato="Rent",
                status="Active",
                valor_aluguel_semanal=95.0,
                url_seguro="/static/uploads/test_ins.pdf",
                assinatura_cliente_inicial=None,
                data_assinatura_inicial=None
            )
            db.session.add(contrato)
            db.session.commit()
            c_id = contrato.id

            with self.client.session_transaction() as sess:
                sess['_user_id'] = str(self.admin.id)
                sess['_fresh'] = True
                sess['last_activity'] = datetime.now().timestamp()

            # Step 1: Before attaching paper contract, verify it is Unsigned
            res = self.client.get(f'/api/contratos?limit=100')
            self.assertEqual(res.status_code, 200)
            item = next((it for it in res.get_json()['itens'] if it['id'] == c_id), None)
            self.assertIsNotNone(item)
            self.assertFalse(item['assinado'])
            self.assertIsNone(item['metodo_assinatura'])
            self.assertIn("Unsigned", item['pendencias'])

            res_det = self.client.get(f'/api/contratos/{c_id}')
            self.assertEqual(res_det.status_code, 200)
            det = res_det.get_json()
            self.assertFalse(det['assinado_inicial'])
            self.assertIsNone(det['metodo_assinatura_inicial'])
            self.assertEqual(det['anexos_iniciais_count'], 0)

            # Step 2: Upload physically signed paper agreement scan/photo
            fake_pdf = io.BytesIO(b"%PDF-1.4 physically signed contract scan")
            res_upload = self.client.post(
                f'/api/contratos/{c_id}/anexos',
                data={
                    'tipo': 'initial_contract',
                    'arquivos': (fake_pdf, 'signed_agreement_page1.pdf')
                },
                content_type='multipart/form-data'
            )
            self.assertEqual(res_upload.status_code, 201)
            up_data = res_upload.get_json()
            self.assertTrue(up_data['success'])
            anexo_id = up_data['anexos'][0]['id']

            # Step 3: Verify /api/contratos list immediately marks as Signed (Paper)
            res_after = self.client.get(f'/api/contratos?limit=100')
            self.assertEqual(res_after.status_code, 200)
            item_after = next((it for it in res_after.get_json()['itens'] if it['id'] == c_id), None)
            self.assertIsNotNone(item_after)
            self.assertTrue(item_after['assinado'], "Contract should be marked as assinado=True with paper attachment")
            self.assertEqual(item_after['metodo_assinatura'], 'physical')
            self.assertEqual(item_after['num_anexos_iniciais'], 1)
            self.assertNotIn("Unsigned", item_after['pendencias'], "Unsigned pendency must be cleared")

            # Step 4: Verify Contract Details API returns assinado_inicial=True and timestamp
            res_det_after = self.client.get(f'/api/contratos/{c_id}')
            self.assertEqual(res_det_after.status_code, 200)
            det_after = res_det_after.get_json()
            self.assertTrue(det_after['assinado_inicial'])
            self.assertEqual(det_after['metodo_assinatura_inicial'], 'physical')
            self.assertEqual(det_after['anexos_iniciais_count'], 1)
            self.assertIsNotNone(det_after['data_assinatura_inicial_uk'])

            # Step 5: Attach return term and verify assinado_devolucao
            fake_ret = io.BytesIO(b"%PDF-1.4 physically signed return term")
            res_ret_upload = self.client.post(
                f'/api/contratos/{c_id}/anexos',
                data={
                    'tipo': 'return_contract',
                    'arquivos': (fake_ret, 'signed_return_term.pdf')
                },
                content_type='multipart/form-data'
            )
            self.assertEqual(res_ret_upload.status_code, 201)
            ret_anexo_id = res_ret_upload.get_json()['anexos'][0]['id']

            res_det_ret = self.client.get(f'/api/contratos/{c_id}')
            det_ret = res_det_ret.get_json()
            self.assertTrue(det_ret['assinado_devolucao'])
            self.assertEqual(det_ret['metodo_assinatura_devolucao'], 'physical')
            self.assertEqual(det_ret['anexos_retorno_count'], 1)

            # Step 6: Delete initial attachment and verify revert to Unsigned
            res_del = self.client.delete(f'/api/contratos/anexos/{anexo_id}')
            self.assertEqual(res_del.status_code, 200)

            res_final = self.client.get(f'/api/contratos?limit=100')
            item_final = next((it for it in res_final.get_json()['itens'] if it['id'] == c_id), None)
            self.assertFalse(item_final['assinado'])
            self.assertIn("Unsigned", item_final['pendencias'])

            # Clean up test contract
            self.client.delete(f'/api/contratos/anexos/{ret_anexo_id}')
            db.session.delete(contrato)
            db.session.commit()
            print("\n✓ Physical signed paper attachments test passed completely!")

if __name__ == '__main__':
    unittest.main()
