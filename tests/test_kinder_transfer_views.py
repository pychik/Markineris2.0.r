"""Check M2R-specific permissions and clothing templates after the transfer."""
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

from jinja2 import Environment, FileSystemLoader


ROOT = Path(__file__).resolve().parents[1]


class KinderTransferViewTests(unittest.TestCase):
    def setUp(self):
        self.env = Environment(loader=FileSystemLoader(ROOT / 'app/templates'))
        self.env.globals.update(
            csrf_token=lambda: 'test-csrf',
            url_for=lambda endpoint, **kwargs: endpoint + '?' + '&'.join(f'{k}={v}' for k, v in kwargs.items()),
        )

    def test_download_preserves_staff_roles_and_preview_for_agents(self):
        template = self.env.get_template('crm_mod_v1/helpers/table_download.html')
        for role in ('manager', 'supermanager', 'superuser', 'm2r_admin', 'admin', 'ordinary_user'):
            with self.subTest(role=role):
                html = template.render(current_user=NS(role=role), n=NS(id=42, category='одежда'))
                if role in ('manager', 'supermanager', 'superuser', 'm2r_admin'):
                    self.assertEqual(html.count('downloadCrmOrderTable(event,'), 2)
                    self.assertIn('?flag_046=1', html)
                    self.assertNotIn('crm_d.crm_preload', html)
                else:
                    self.assertIn('crm_d.crm_preload', html)
                    self.assertNotIn('downloadCrmOrderTable', html)

    def test_children_switch_restores_saved_value(self):
        template = self.env.get_template('helpers/clothes/genders_block.html')
        for children in (False, True):
            with self.subTest(children=children):
                html = template.render(copied_order=NS(is_children=children, gender='Муж.'),
                                       genders=['Муж.'], subcategory='common')
                self.assertIn('name="is_children" value="yes"', html)
                self.assertEqual('checked>' in html, children)

    def test_company_editor_keeps_existing_server_permission_gate(self):
        template = self.env.get_template('product_cards/user/helpers/_card_view_companies_block.html')
        card = NS(id=42, processing_company_label='Компания', processing_company_assigned_at=None,
                  processing_company_inn='123', processing_company_external_id=None, processing_company_title=None)
        for allowed in (False, True):
            with self.subTest(allowed=allowed):
                html = template.render(card=card, can_change_processing_company=allowed, processing_companies=[])
                self.assertEqual('id="pc-card-processing-company-select"' in html, allowed)


if __name__ == '__main__':
    unittest.main()
