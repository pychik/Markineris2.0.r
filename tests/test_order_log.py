import ast
import sys
from pathlib import Path
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.utilities.order_log import (
    MAX_ORDER_LOG, append_order_log, h_append_order_log, log_order_stage, order_log_line,
)


class OrderLogTests(unittest.TestCase):
    def test_empty_and_existing_history(self):
        self.assertEqual(h_append_order_log(None, "new"), "new")
        self.assertEqual(h_append_order_log("old", "\nnew"), "old\nnew")

    def test_discards_oldest_characters_and_preserves_newest(self):
        old = "старое" * 300
        line = "\n03.11.2026 12:34:56 operator: взял заказ;"
        result = h_append_order_log(old, line)
        self.assertEqual(len(result), MAX_ORDER_LOG)
        self.assertEqual(result, (old + line)[-1000:])
        self.assertTrue(result.endswith(line))

    def test_oversized_new_entry_is_bounded(self):
        self.assertEqual(h_append_order_log("old", "я" * 1500), "я" * 1000)

    def test_timestamp_actor_and_single_line(self):
        self.assertEqual(
            order_log_line("прикрепил\nфайл", "operator\r\nname", at=datetime(2026, 11, 3, 12, 34, 56)),
            "\n03.11.2026 12:34:56 operator name: прикрепил файл;",
        )

    def test_atomic_append_uses_bound_parameters_and_leaves_commit_to_caller(self):
        session = Mock()
        with patch.dict(sys.modules, {"models": SimpleNamespace(db=SimpleNamespace(session=session))}):
            append_order_log(42, "прикрепил файл: 'имя'.zip", actor="operator")
        statement, params = session.execute.call_args.args
        self.assertIn("right(coalesce(order_log, '') || :line, :max_length)", str(statement))
        self.assertNotIn("'имя'", str(statement))
        self.assertEqual(params["order_id"], 42)
        self.assertEqual(params["max_length"], 1000)
        self.assertIn("operator: прикрепил файл: 'имя'.zip;", params["line"])
        session.commit.assert_not_called()

    def test_background_actor(self):
        session = Mock()
        with patch.dict(sys.modules, {"models": SimpleNamespace(db=SimpleNamespace(session=session))}):
            append_order_log(42, "перевёл заказ")
        self.assertIn("Система:", session.execute.call_args.args[1]["line"])

    def test_request_uses_actual_actor(self):
        from flask import Flask

        session = Mock()
        user = SimpleNamespace(is_authenticated=True, login_name="moderator")
        with Flask(__name__).test_request_context(), patch("flask_login.current_user", user):
            with patch.dict(sys.modules, {"models": SimpleNamespace(db=SimpleNamespace(session=session))}):
                append_order_log(42, "назначил оператора: operator")
        self.assertIn("moderator: назначил оператора: operator;", session.execute.call_args.args[1]["line"])

    def test_agent_is_recorded_as_actor(self):
        from flask import Flask

        session = Mock()
        agent = SimpleNamespace(is_authenticated=True, login_name="agent", role="admin", id=123)
        with Flask(__name__).test_request_context(), patch("flask_login.current_user", agent):
            with patch.dict(sys.modules, {"models": SimpleNamespace(db=SimpleNamespace(session=session))}):
                append_order_log(42, "удалил файл / ссылку результата")
        self.assertIn("agent: удалил файл", session.execute.call_args.args[1]["line"])

    def test_agent_history_access_is_scoped_to_own_and_client_orders(self):
        # Execute the actual access predicate without initializing Flask/Redis/DB.
        path = Path(__file__).resolve().parents[1] / "app/views/crm/helpers.py"
        tree = ast.parse(path.read_text())
        predicate = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_can_view_order_desc")
        settings = SimpleNamespace(SUPER_USER="superuser", MARKINERIS_ADMIN_USER="m2r_admin",
                                   ADMIN_USER="admin", MANAGER_USER="manager", SUPER_MANAGER="supermanager",
                                   OrderStage=SimpleNamespace(POOL=2))
        namespace = {"settings": settings, "User": object}
        exec(compile(ast.Module(body=[predicate], type_ignores=[]), str(path), "exec"), namespace)
        can_view = namespace["_can_view_order_desc"]
        agent = SimpleNamespace(id=123, role="admin")
        own = SimpleNamespace(user_id=123, admin_parent_id=None, to_delete=False)
        client = SimpleNamespace(user_id=456, admin_parent_id=123, to_delete=False)
        other = SimpleNamespace(user_id=789, admin_parent_id=987, to_delete=False)
        self.assertTrue(can_view(own, agent))
        self.assertTrue(can_view(client, agent))
        self.assertFalse(can_view(other, agent))
        client.to_delete = True
        self.assertFalse(can_view(client, agent))

    def test_history_template_escapes_html(self):
        from jinja2 import DictLoader, Environment

        root = Path(__file__).resolve().parents[1]
        source = (root / "app/templates/crm_mod_v1/helpers/order_description.html").read_text()
        env = Environment(autoescape=True, loader=DictLoader({
            "description.html": source,
            "crm_mod_v1/helpers/order_manager_block.html": "",
            "crm_mod_v1/helpers/order_companies_block.html": "",
        }))
        html = env.get_template("description.html").render(
            current_user=SimpleNamespace(role="admin"),
            n=SimpleNamespace(order_log='<script>alert("x")</script>'),
        )
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_stage_names_distinguish_crm_columns(self):
        with patch("app.utilities.order_log.append_order_log") as append:
            for stage, label in [(2, "ПУЛ компаний"), (5, "Обработан оператором"), (7, "Проблема решена")]:
                log_order_stage(42, stage, actor="operator")
                append.assert_called_with(42, f"перевёл заказ в «{label}»", actor="operator")


if __name__ == "__main__":
    unittest.main()
