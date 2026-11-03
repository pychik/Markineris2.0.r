"""Exercise the real handler and access predicate without starting app services."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from flask import Flask, jsonify


class OrderLogsEndpointTests(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1] / "app/views/crm/helpers.py"
        tree = ast.parse(source.read_text())
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                     and node.name in {"h_order_logs", "_can_view_order_desc"}]
        settings = SimpleNamespace(SUPER_USER="superuser", MARKINERIS_ADMIN_USER="moderator",
                                   ADMIN_USER="admin", MANAGER_USER="manager", SUPER_MANAGER="supermanager",
                                   OrderStage=SimpleNamespace(POOL=2))
        self.viewer = SimpleNamespace(id=10, role="manager")
        self.order = SimpleNamespace(user_id=20, admin_parent_id=30, manager_id=10, manager_role="manager",
                                     stage=3, to_delete=False, order_idn="N42", order_log="operator: действие;")
        self.namespace = {"current_user": self.viewer, "jsonify": jsonify, "settings": settings,
                          "User": object, "_get_order_desc_row": Mock(return_value=self.order),
                          "_can_work_with_order_user": Mock(return_value=True)}
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), self.namespace)
        self.context = Flask(__name__).app_context()
        self.context.push()
        self.addCleanup(self.context.pop)

    def get_logs(self):
        result = self.namespace["h_order_logs"](42)
        return result if isinstance(result, tuple) else (result, 200)

    def test_allowed_operator_gets_only_log_and_number(self):
        response, status = self.get_logs()
        self.assertEqual(status, 200)
        self.assertEqual(response.get_json(), {"status": "success", "logs": self.order.order_log, "order_idn": "N42"})
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_other_operator_and_deleted_order_are_denied(self):
        self.viewer.id = 99
        self.assertEqual(self.get_logs()[1], 403)
        self.viewer.id = 10
        self.order.to_delete = True
        response, status = self.get_logs()
        self.assertEqual(status, 403)
        self.assertNotIn("logs", response.get_json())

    def test_missing_order(self):
        self.namespace["_get_order_desc_row"].return_value = None
        self.assertEqual(self.get_logs()[1], 404)

    def test_empty_history(self):
        self.order.order_log = None
        self.assertEqual(self.get_logs()[0].get_json()["logs"], "")

    def test_agent_can_load_own_and_client_logs_only(self):
        self.viewer.role = "admin"
        self.order.user_id = self.viewer.id
        self.assertEqual(self.get_logs()[1], 200)
        self.order.user_id = 20
        self.order.admin_parent_id = self.viewer.id
        self.assertEqual(self.get_logs()[1], 200)
        self.order.admin_parent_id = 99
        response, status = self.get_logs()
        self.assertEqual(status, 403)
        self.assertNotIn("logs", response.get_json())

    def test_platinum_restriction_when_present(self):
        if "_can_work_with_order_user" not in self.namespace["h_order_logs"].__code__.co_names:
            self.skipTest("This service has no platinum restriction")
        self.namespace["_can_work_with_order_user"].return_value = False
        self.assertEqual(self.get_logs()[1], 403)


if __name__ == "__main__":
    unittest.main()
