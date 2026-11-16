"""Run the actual counting SQL without starting application services."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]


def load_function(path, name, namespace):
    tree = ast.parse((ROOT / path).read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), path, "exec"), namespace)
    return namespace[name]


class RowsMarksTests(unittest.TestCase):
    def setUp(self):
        config = ast.parse((ROOT / "app/config.py").read_text())
        settings_node = next(n for n in config.body if isinstance(n, ast.ClassDef) and n.name == "Settings")
        categories = {}
        for node in settings_node.body:
            if isinstance(node, ast.ClassDef):
                fields = {n.target.id: ast.literal_eval(n.value) for n in node.body
                          if isinstance(n, ast.AnnAssign) and n.target.id in ("CATEGORY", "KPB_TYPE")}
                if "CATEGORY" in fields:
                    categories[node.name] = NS(**fields)
        self.settings = NS(**categories, OrderStage=NS(NEW=1, POOL=2))
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        self.conn = engine.connect()
        self.addCleanup(self.conn.close)
        self.conn.execute(text("ATTACH DATABASE ':memory:' AS public"))
        self.conn.execute(text("CREATE TABLE public.orders (id INTEGER, category TEXT)"))
        for table in ("shoes", "clothes", "socks", "linen", "parfum", "cosmetics", "toys"):
            self.conn.execute(text(f"CREATE TABLE public.{table} (id INTEGER, order_id INTEGER, "
                                   "box_quantity INTEGER, quantity INTEGER, type TEXT, kpb_quantity INTEGER)"))
        for table, fk in (("shoes_quantity_sizes", "shoe_id"), ("cl_quantity_sizes", "cl_id"),
                          ("socks_quantity_sizes", "socks_id"), ("linen_quantity_sizes", "lin_id")):
            self.conn.execute(text(f"CREATE TABLE public.{table} ({fk} INTEGER, quantity INTEGER)"))
        self.count = load_function("app/utilities/saving_uts.py", "get_rows_marks",
                                   dict(settings=self.settings, db=NS(session=self.conn), text=text))
        self.limits = NS(ap_rows=0, ap_marks=0)
        self.stage = load_function("app/utilities/support.py", "get_process_stage",
                                   dict(settings=self.settings, get_rows_marks=self.count,
                                        helper_get_limits=lambda: self.limits))

    def order(self, category, order_id=1):
        self.conn.execute(text("INSERT INTO public.orders VALUES (:id, :category)"),
                          dict(id=order_id, category=getattr(self.settings, category).CATEGORY))

    def test_all_categories_count_positions_and_marks_and_scope_order(self):
        sized = {"Shoes": ("shoes", "shoes_quantity_sizes", "shoe_id"),
                 "Clothes": ("clothes", "cl_quantity_sizes", "cl_id"),
                 "Socks": ("socks", "socks_quantity_sizes", "socks_id"),
                 "Linen": ("linen", "linen_quantity_sizes", "lin_id")}
        simple = {"Parfum": "parfum", "Cosmetics": "cosmetics", "Toys": "toys"}
        for order_id, category in enumerate((*sized, *simple), 1):
            with self.subTest(category=category):
                self.order(category, order_id)
                table = sized[category][0] if category in sized else simple[category]
                self.conn.execute(text(f"INSERT INTO public.{table} "
                                       "(id, order_id, box_quantity, quantity, type) "
                                       "VALUES (:id, :id, 3, 7, 'обычный')"), dict(id=order_id))
                if category in sized:
                    _, sizes, fk = sized[category]
                    self.conn.execute(text(f"INSERT INTO public.{sizes} ({fk}, quantity) VALUES (:id, 2), (:id, 5)"),
                                      dict(id=order_id))
                expected = (2, 21) if category in sized else (1, 7)
                self.assertEqual(self.count(order_id, getattr(self.settings, category).CATEGORY), expected)
                self.assertEqual(self.count(999, getattr(self.settings, category).CATEGORY), (0, 0))

    def test_toys_regression_and_auto_pool_boundaries(self):
        for order_id, quantity in ((1, 150), (2, 120)):
            self.order("Toys", order_id)
            self.conn.execute(text("INSERT INTO public.toys (id, order_id, quantity) VALUES (:id, :id, :quantity)"),
                              dict(id=order_id, quantity=quantity))
            self.assertEqual(self.count(order_id, self.settings.Toys.CATEGORY), (1, quantity))
            self.assertEqual(self.stage(order_id, self.settings.Toys.CATEGORY), 1)
        self.limits.ap_rows, self.limits.ap_marks = 1, 120
        self.assertEqual(self.stage(1, self.settings.Toys.CATEGORY), 1)
        self.assertEqual(self.stage(2, self.settings.Toys.CATEGORY), 2)
        self.limits.ap_rows = 0
        self.assertEqual(self.stage(2, self.settings.Toys.CATEGORY), 1)

    def test_multiple_simple_positions_null_quantity_and_empty_order(self):
        for order_id, category in enumerate(("Cosmetics", "Toys", "Parfum"), 1):
            with self.subTest(category=category):
                self.order(category, order_id)
                table = category.lower()
                self.conn.execute(text(f"INSERT INTO public.{table} (id, order_id, quantity) "
                                       "VALUES (1, :id, 50), (2, :id, 70)"), dict(id=order_id))
                self.assertEqual(self.count(order_id, getattr(self.settings, category).CATEGORY), (2, 120))
                self.conn.execute(text(f"UPDATE public.{table} SET quantity=NULL WHERE order_id=:id"), dict(id=order_id))
                self.assertEqual(self.count(order_id, getattr(self.settings, category).CATEGORY)[1], 0)
                self.order(category, order_id + 10)
                self.assertEqual(self.count(order_id + 10, getattr(self.settings, category).CATEGORY), (0, 0))

    def test_linen_set_uses_set_quantity_without_size_rows(self):
        self.order("Linen")
        self.conn.execute(text("INSERT INTO public.linen (id, order_id, type, kpb_quantity) VALUES (1, 1, :type, 8)"),
                          dict(type=self.settings.Linen.KPB_TYPE))
        self.assertEqual(self.count(1, self.settings.Linen.CATEGORY), (1, 8))


if __name__ == "__main__":
    unittest.main()
