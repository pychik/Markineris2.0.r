"""Exercise account search against SQLite without loading the production app."""
import ast
from datetime import datetime
from pathlib import Path
import re
from types import SimpleNamespace as NS
import unittest

from flask import Flask, jsonify, request
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


ROOT = Path(__file__).resolve().parents[1]


class AccountSearchTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        engine = create_engine('sqlite://')
        self.session = Session(engine)
        self.addCleanup(engine.dispose)
        self.addCleanup(self.session.close)
        self.session.execute(text("ATTACH DATABASE ':memory:' AS public"))
        self.session.execute(text('CREATE TABLE public.users (id INTEGER PRIMARY KEY, email TEXT, login_name TEXT, role TEXT)'))
        self.session.execute(text('''CREATE TABLE public.orders (
            id INTEGER PRIMARY KEY, user_id INTEGER, manager_id INTEGER, stage INTEGER,
            to_delete BOOLEAN, order_idn TEXT, category TEXT, payment BOOLEAN,
            user_comment TEXT, processing_info TEXT, is_moderation BOOLEAN, crm_created_at TEXT,
            created_at TEXT, company_type TEXT, company_name TEXT, company_idn TEXT)'''))
        self.session.execute(text("INSERT INTO public.users VALUES (1, 'Client@Example.org', 'ClientLogin', 'ordinary'), (2, 'other@example.org', 'other', 'ordinary'), (10, '', 'Chief', 'supermanager'), (11, '', 'Mod', 'm2r_admin')"))
        for stage in range(12):
            self.session.execute(text("INSERT INTO public.orders (id,user_id,stage,order_idn,created_at) VALUES (:id,1,:stage,:number,'2026-11-16')"), {'id': stage + 1, 'stage': stage, 'number': f'1_{stage}'})
        self.session.execute(text("INSERT INTO public.orders (id,user_id,stage,to_delete,order_idn) VALUES (20,1,3,TRUE,'deleted'), (21,2,3,FALSE,'other'), (22,1,3,FALSE,'protected')"))
        self.session.execute(text('UPDATE public.orders SET manager_id=11 WHERE id=22'))
        stages = NS(NEW=1, POOL=2, MANAGER_START=3, MANAGER_EDO=4, MANAGER_PROBLEM=6, MANAGER_SOLVED=7)
        settings = NS(SUPER_USER='superuser', MARKINERIS_ADMIN_USER='m2r_admin',
                      SUPER_MANAGER='supermanager', MANAGER_USER='manager', OrderStage=stages)
        source = ast.parse((ROOT / 'app/views/crm/account_search.py').read_text())
        functions = [node for node in source.body if isinstance(node, ast.FunctionDef)]
        self.rendered = {}

        def render(template, **values):
            self.rendered.update(values)
            return 'rendered'

        self.namespace = dict(
            settings=settings, db=NS(session=self.session), text=text, re=re, User=object,
            jsonify=jsonify, request=request, render_template=render,
            CRM_STAGE_LABELS={stage: f'Stage {stage}' for stage in range(12)},
            SQLQueryCategoriesAll=NS(get_joins=lambda: '', get_stmt=lambda field: "'common'" if field == 'subcategory' else '0'),
        )
        exec(compile(ast.Module(body=functions, type_ignores=[]), '<account-search>', 'exec'), self.namespace)

    def search(self, role, value='client@example.org', is_at2=False):
        with self.app.test_request_context(method='POST', data={'account': value}):
            result = self.namespace['search_orders_by_account'](NS(id=10, role=role, is_at2=is_at2))
            if isinstance(result, tuple):
                return result[0].get_json(), result[1]
            return result.get_json(), 200

    def test_privileged_email_and_active_stages(self):
        for role in ('superuser', 'm2r_admin'):
            result, status = self.search(role, ' client@example.ORG ')
            self.assertEqual(status, 200)
            self.assertEqual(result['status'], 'success')
            self.assertEqual([g['stage'] for g in self.rendered['groups']], [1, 2, 3, 4, 6, 7])
            self.assertEqual(self.rendered['total'], 7)  # Six stages and the moderator's order.
            self.assertNotIn(20, [o.id for g in self.rendered['groups'] for o in g['orders']])

    def test_roles_and_invalid_input(self):
        for role in ('manager', 'supermanager', 'admin', 'ordinary'):
            self.assertEqual(self.search(role)[1], 403)
            self.assertEqual(self.namespace['get_orders_by_account'](NS(role=role), 'client@example.org'), [])
        for value in ('', 'no-at-sign', 'a@b', 'a@b.org extra', 'a' * 255 + '@b.org'):
            self.assertEqual(self.search('superuser', value)[1], 400)
        self.assertEqual(self.search('superuser', value='')[1], 400)
        self.search('superuser', value="foo'OR1=1--@example.org")
        self.assertEqual(self.rendered['total'], 0)
        self.search('superuser', value='%@example.org')
        self.assertEqual(self.rendered['total'], 0)

    def test_agents_type_2_cannot_search(self):
        for role in ('admin', 'ordinary', 'superuser', 'm2r_admin'):
            self.assertEqual(self.search(role, is_at2=True)[1], 403)
        env = Environment(loader=FileSystemLoader(ROOT / 'app/templates'), autoescape=True)
        env.globals.update(url_for=lambda *a, **kw: '/url', csrf_token=lambda: 'csrf')
        for name in ('helpers/search_order_find_manager.html', 'helpers/modals/account_search_modal.html'):
            html = env.get_template('crm_mod_v1/' + name).render(
                current_user=NS(role='admin', is_at2=True), user=NS(role='admin'),
                request=NS(path='/crm_dashboard/agents'), managers_list=[])
            self.assertNotIn('id="searchOrderAccountMode"', html)
            self.assertNotIn('id="accountOrdersModal"', html)

    def test_templates_group_escape_and_hide_switch(self):
        env = Environment(loader=FileSystemLoader(ROOT / 'app/templates'), autoescape=True)
        env.globals.update(url_for=lambda *a, **kw: '/url', csrf_token=lambda: 'csrf')
        order = NS(id=42, order_idn='1_42', category='одежда', stage=3, is_moderation=False, subcategory='common', row_count=1, pos_count=2,
                   crm_created_at=datetime.now(), company_type='ИП', company_name='<script>bad</script>',
                   company_idn='123', manager='Operator', has_children=True, declar_doc=False,
                   user_comment='', payment=False, processing_info='')
        html = env.get_template('crm_mod_v1/helpers/account_search_results.html').render(
            account='client@example.org', total=1,
            groups=[dict(stage=3, label='В работе', orders=[order])])
        self.assertIn('accountSearchOrder_42', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>bad', html)
        template = env.get_template('crm_mod_v1/helpers/search_order_find_manager.html')
        for role in ('manager', 'supermanager', 'superuser', 'm2r_admin'):
            for page in ('/crm/managers', '/crm/agents'):
                html = template.render(current_user=NS(role=role, is_at2=False), user=NS(role=role), request=NS(path=page), managers_list=[])
                expected = role == 'superuser' or (role == 'm2r_admin' and 'manager' not in page)
                self.assertEqual('id="searchOrderAccountMode"' in html, expected)
                self.assertNotIn('search_orders_login', html)


if __name__ == '__main__':
    unittest.main()
