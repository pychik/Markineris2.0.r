from sqlalchemy import text


class SQLQueryCategoriesAll:
    """
    Common Query categories processing unit
    Be aware of naming collisions pos_count = marks count in requests  somewhere
    """
    CATEGORY_TABLES = {
        "default": {
            "join": """
                LEFT JOIN public.shoes sh ON o.id = sh.order_id
                LEFT JOIN public.shoes_quantity_sizes sh_qs ON sh.id = sh_qs.shoe_id
                LEFT JOIN public.clothes cl ON o.id = cl.order_id
                LEFT JOIN public.cl_quantity_sizes cl_qs ON cl.id = cl_qs.cl_id
                LEFT JOIN public.socks sk ON o.id = sk.order_id
                LEFT JOIN public.socks_quantity_sizes sk_qs ON sk.id = sk_qs.socks_id
                LEFT JOIN public.linen l ON o.id = l.order_id
                LEFT JOIN public.linen_quantity_sizes l_qs ON l.id = l_qs.lin_id
                LEFT JOIN public.parfum p ON o.id = p.order_id
            """,
            "fields": {
                "subcategory": "coalesce(max(cl.subcategory), 'common')",
                "pos_count": "COUNT(COALESCE(sh.id, cl.id, sk.id, l.id, p.id))",
                "marks_count": "SUM(COALESCE(sh.box_quantity * sh_qs.quantity, cl.box_quantity * cl_qs.quantity, sk.box_quantity * sk_qs.quantity, l.box_quantity * l_qs.quantity, p.quantity, 0))",
                "rows_count": "COUNT(COALESCE(sh.id, cl.id, sk.id, l.id, p.id))",
                "category_pos_type_max": "MAX(COALESCE(sh.type, cl.type, sk.type, l.type, p.type))",
                "category_pos_type": "COALESCE(sh.type, cl.type, sk.type, l.type, p.type)",
                "declar_doc": "COUNT(coalesce(sh.rd_date, cl.rd_date, sk.rd_date, l.rd_date, p.rd_date))",
                "orders_count_utm": "COUNT(DISTINCT CASE WHEN o.stage >= 8 AND o.stage != 9 THEN o.id END)",
                "marks_count_utm": """SUM(COALESCE(
                    CASE 
                        WHEN o.stage >= 8 AND o.stage != 9 THEN 
                            COALESCE(sh.box_quantity * sh_qs.quantity, 0) + 
                            COALESCE(cl.box_quantity * cl_qs.quantity, 0) + 
                            COALESCE(sk.box_quantity * sk_qs.quantity, 0) + 
                            COALESCE(l.box_quantity * l_qs.quantity, 0) + 
                            COALESCE(p.quantity, 0)
                        ELSE 0 
                    END, 0))"""
            }
        }
    }

    @staticmethod
    def get_joins():
        return SQLQueryCategoriesAll.CATEGORY_TABLES["default"]["join"]

    @staticmethod
    def get_stmt(field: str):
        return text(f"{SQLQueryCategoriesAll.CATEGORY_TABLES['default']['fields'][field]}")


class SQLQueryFactory:
    CATEGORY_TABLES = {
        "shoes": {
            "join": """
                LEFT JOIN public.shoes sh ON o.id = sh.order_id
                LEFT JOIN public.shoes_quantity_sizes sh_qs ON sh.id = sh_qs.shoe_id
            """,
            "fields": {
                "pos_count": "COUNT(sh.id)",
                "marks_count": "SUM(sh.box_quantity * sh_qs.quantity)",
                "rows_count": "COUNT(sh.id)",
                "category_pos_type_max": "MAX(sh.type)",
                "category_pos_type": "sh.type",
                "declar_doc": "COUNT(sh.rd_date)"
            }
        },
        "clothes": {
            "join": """
                LEFT JOIN public.clothes cl ON o.id = cl.order_id
                LEFT JOIN public.cl_quantity_sizes cl_qs ON cl.id = cl_qs.cl_id
            """,
            "fields": {
                "pos_count": "COUNT(cl.id)",
                "marks_count": "SUM(cl.box_quantity * cl_qs.quantity)",
                "rows_count": "COUNT(cl.id)",
                "category_pos_type_max": "MAX(cl.type)",
                "category_pos_type": "cl.type",
                "declar_doc": "COUNT(cl.rd_date)"
            }
        },
        "socks": {
            "join": """
                LEFT JOIN public.socks sk ON o.id = sk.order_id
                LEFT JOIN public.socks_quantity_sizes sk_qs ON sk.id = sk_qs.socks_id
            """,
            "fields": {
                "pos_count": "COUNT(sk.id)",
                "marks_count": "SUM(sk.box_quantity * sk_qs.quantity)",
                "rows_count": "COUNT(sk.id)",
                "category_pos_type_max": "MAX(sk.type)",
                "category_pos_type": "sk.type",
                "declar_doc": "COUNT(sk.rd_date)"
            }
        },
        "linen": {
            "join": """
                LEFT JOIN public.linen l ON o.id = l.order_id
                LEFT JOIN public.linen_quantity_sizes l_qs ON l.id = l_qs.lin_id
            """,
            "fields": {
                "pos_count": "COUNT(l.id)",
                "marks_count": "SUM(l.box_quantity * l_qs.quantity)",
                "rows_count": "COUNT(l.id)",
                "category_pos_type_max": "MAX(l.type)",
                "category_pos_type": "l.type",
                "declar_doc": "COUNT(l.rd_date)"
            }
        },
        "parfum": {
            "join": """
                LEFT JOIN public.parfum p ON o.id = p.order_id
            """,
            "fields": {
                "pos_count": "COUNT(p.id)",
                "marks_count": "SUM(p.quantity)",
                "rows_count": "COUNT(p.id)",
                "category_pos_type_max": "MAX(p.type)",
                "category_pos_type": "p.type",
                "declar_doc": "COUNT(p.rd_date)"
            }
        }
    }

    @staticmethod
    def get_joins(category: str):
        """Получает JOIN-выражения для указанной категории."""
        if category not in SQLQueryFactory.CATEGORY_TABLES:
            raise ValueError(f"Unknown category: {category}")
        return SQLQueryFactory.CATEGORY_TABLES[category]["join"]

    @staticmethod
    def get_stmt(category: str, field: str):
        """Генерирует SQL-запрос для указанной категории и поля."""
        if category not in SQLQueryFactory.CATEGORY_TABLES:
            raise ValueError(f"Unknown category: {category}")
        if field not in SQLQueryFactory.CATEGORY_TABLES[category]["fields"]:
            raise ValueError(f"Unknown field: {field} for category {category}")

        query = f"{SQLQueryFactory.CATEGORY_TABLES[category]['fields'][field]}"
        return text(query)


if __name__ == "__main__":
    # query_categories = SQLQueryCategoriesAll()
    print(SQLQueryCategoriesAll.get_joins())
    print(SQLQueryCategoriesAll.get_stmt(field="rows_count"))
    print(SQLQueryCategoriesAll.get_stmt(field="category_pos_type"))
    print(SQLQueryCategoriesAll.get_stmt(field="pos_count"))
    print(SQLQueryCategoriesAll.get_stmt(field="marks_count"))
    print(SQLQueryCategoriesAll.get_stmt(field="orders_count_utm"))
    print(SQLQueryCategoriesAll.get_stmt(field="marks_count_utm"))

    print("JOINs для shoes:\n", SQLQueryFactory.get_joins(category="shoes"))
    print("\nЗапрос pos_count для shoes:\n", SQLQueryFactory.get_stmt(category="shoes", field="pos_count"))
    print("\nЗапрос category_pos_type_max для shoes:\n", SQLQueryFactory.get_stmt(category="shoes", field="category_pos_type_max"))


