import datetime
import json
from copy import deepcopy
from io import BytesIO
from typing import Any, TypeVar, Optional

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

from config import settings
from data_migrations.schemas import PartnerCodeSchema, UserSchema, SchemaType
from data_migrations.utils import get_hashed_password, make_email, make_login_name, make_password
from logger import logger
from models import (
    User,
    PartnerCode,
    ModelType,
    Price,
    Promo,
    Telegram,
    TelegramMessage,
    UserTransaction,
    Order,
    OrderFile,
    OrderStat,
    Shoe,
    Linen,
    Parfum,
    Clothes,
    Socks,
    ShoeQuantitySize,
    LinenQuantitySize,
    ClothesQuantitySize,
    SocksQuantitySize,
)
from redis_queue.redis_instance import get_redis_client
from utilities.minio_service.services import get_s3_service
from views.crm.helpers import helper_create_filename

T = TypeVar("T")


class ETLUploadProcessUserAndPartnerCode:

    def __init__(self, session: Session):
        self.data_download_url = settings.DATA_DOWNLOAD_URL_FROM_MARKINERS_1

        self.session = session

        self.inserted_and_updated_data = {}
        self.user_inserted_data = 0
        self.code_inserted_data = 0

        self._users = {}
        self._codes = {}
        self._agents = {}

        self._user_codes = {}
        self._agent_codes = {}

    def start_etl_process(self) -> dict[str, dict[str, int]]:
        logger.info("Start ETL process")

        data = self._get_data_from_markineris_1()

        super_user = self._get_super_user()

        code_schemas = self._form_schemas(data.get("partner_codes", []), PartnerCodeSchema, is_code=True)
        agent_schemas = self._form_schemas(
            self._form_agent_data_from_partner_code_for_create(code_schemas),
            schema=UserSchema,
            is_agent=True,
        )
        user_schemas = self._form_schemas(data=data.get("users", []), schema=UserSchema)

        user_prepared_data = {u.email: u.dict() for u in user_schemas}
        agent_prepared_data = {u.email: u.dict() for u in agent_schemas}
        code_prepared_data = {c.code: c.dict() for c in code_schemas}

        with self.session.connection():
            self._agents = self._upsert_data(agent_prepared_data, User, key="email")

            self._codes = self._upsert_data(code_prepared_data, PartnerCode, key="code")
            self.code_inserted_data = self.inserted_and_updated_data

            self._users = self._upsert_data(user_prepared_data, User, key="email")
            self.user_inserted_data = self.inserted_and_updated_data

            self._link_users_and_codes(super_user)
            self._link_code_to_agent()

            self.session.commit()

        data = {
            "users": self.user_inserted_data,
            "partner_codes": self.code_inserted_data
        }

        logger.info(f"ETL process successfully complete.\nUploaded {data}")

        return data

    def _get_super_user(self) -> ModelType:
        return self.session.query(User).filter(User.role == "superuser").first()

    def _get_data_from_markineris_1(self):
        headers = {'MARKINERS_V2_TOKEN': settings.MARKINERS_V2_TOKEN}

        return requests.post(self.data_download_url, headers=headers).json()

    @staticmethod
    def _add_admin_parent_id_to_user(data: list[SchemaType], super_user_id: int) -> list[SchemaType]:
        for user in data:
            user.admin_parent_id = super_user_id

        return data

    def _form_schemas(self, data: list[dict], schema: SchemaType, is_code=False, is_agent=False):
        if is_code:
            return [schema(**item) for item in data]

        if is_agent:
            agents = []

            for agent in data:
                code = agent.get("partner", None)
                agent = schema(**agent)
                self._agent_codes[code] = agent
                agents.append(agent)

            return agents

        items = []

        for item in data:

            code = item.get("partner", None)
            item_schema = schema(**item)
            if item_schema.role == "superuser":
                continue
            if code:
                self._user_codes.setdefault(item_schema.email, code)

            items.append(item_schema)

        return items

    def _upsert_data(self, entries: dict[str, dict], model: ModelType, key: str) -> dict[str, ModelType]:
        entries_to_update = []
        entries_to_insert = []
        entries_to_get = deepcopy(entries)

        existed_codes_in_db = self._get_items(entries, model, key)

        # get all entries to be updated
        for each in existed_codes_in_db.values():
            entries.pop(str(getattr(each, key)))
            entries_to_update.append(each.__dict__)

        # get all entries to be inserted
        for entry in entries.values():
            entries_to_insert.append(entry)

        if entries_to_update:
            self.session.bulk_update_mappings(model, entries_to_update)
        if entries_to_insert:
            self.session.bulk_insert_mappings(model, entries_to_insert)

        self.inserted_and_updated_data = {
            "inserted": len(entries_to_insert),
            "updated": len(entries_to_update),
        }

        return self._get_items(entries_to_get, model, key)

    def _get_items(self, entries: dict[str, dict], model: ModelType, key: str) -> dict[str, ModelType]:
        items = {}

        for each in self.session.query(model).filter(getattr(model, key).in_(entries.keys())).all():
            items[str(getattr(each, key))] = each

        return items

    @staticmethod
    def _link_codes_to_user(user, new_codes):
        old_user_codes = user.partners
        user_code_to_link = set(new_codes) - set(old_user_codes)
        if user_code_to_link:
            user.partners.extend(user_code_to_link)

    def _link_users_and_codes(self, super_user) -> None:
        for user in self._users.values():
            new_user_codes = []

            code = self._user_codes.get(user.email, None)
            code_instance = self._codes.get(code)
            if code_instance is not None:
                agent = self._agents[self._agent_codes[code].email]
                user.admin_parent_id = agent.id
                new_user_codes.append(code_instance)

            if new_user_codes:
                self._link_codes_to_user(user, new_user_codes)
            else:
                user.admin_parent_id = super_user.id

    def _link_code_to_agent(self):
        for code, code_instance in self._codes.items():
            agent = self._agents[self._agent_codes[code].email]
            if agent:
                agent.partners.append(code_instance)

    @staticmethod
    def _form_agent_data_from_partner_code_for_create(codes: list[PartnerCodeSchema]) -> list:
        data = []
        for code in codes:
            login_name = make_login_name(code.code)
            email = make_email(login_name)
            password = get_hashed_password(
                make_password(
                    email,
                    settings.SALT.get_secret_value()
                )
            )

            data.append({
                "email": email,
                "name": login_name,
                "phone": code.phone,
                "role": settings.ADMIN_USER,
                "status": True,
                "is_crm": True,
                "password": password,
                "created_at": datetime.datetime.now().isoformat(),
                "client_code": settings.AU_CLIENT_CODE,
                "partner": code.code,
            })

        return data


class ETLMigrateUserData:
    ENDPOINTS = (
        GET_ARCHIVE_FILE := f"{settings.MARKINERIS_API_HOST}/get_order_file_by_name",
        GET_USER_DATA := f"{settings.MARKINERIS_API_HOST}/get_user_all_data",
    )
    HEADERS = {"TOKEN": settings.MARKINERS_V2_TOKEN}
    CACHE_KEY_PATTERNS = ["order_idn_mapper*", "transaction_mapper*"]

    def __init__(self, session: Session):
        self.session = session
        self.minio_service = get_s3_service()
        self.redis_client = get_redis_client()

    def start(self, email: str) -> dict:
        """Запускает процесс миграции данных пользователя."""
        response = requests.post(f"{self.GET_USER_DATA}", json={"email": email}, headers=self.HEADERS)
        response.raise_for_status()

        try:
            self.migrate_user(response.json())
            self.session.commit()
            self._clear_cache()
            return {"status": "OK"}
        except Exception as e:
            self.session.rollback()
            logger.error(f"Ошибка миграции пользователя {email}: {str(e)}")
            raise e

    def migrate_user(self, user_data: dict[str, Any], admin_parent_id: Optional[int] = None) -> None:
        """Миграция данных пользователя."""
        defaults = {
            "admin_parent_id": admin_parent_id,
            "price_id": None,
            "admin_order_num": 0,
        }

        user_data = self._clear_data_before_save(user_data, defaults)

        nested_data = {
            "transactions": user_data.pop("transactions", []),
            "orders": user_data.pop("orders", []),
            "orders_stats": user_data.pop("orders_stats", []),
            "telegram": user_data.pop("telegram", []),
            "partners": user_data.pop("partners", []),
            "promos": user_data.pop("promos", []),
            "telegram_message": user_data.pop("telegram_message", []),
            "prices": user_data.pop("prices", {}),
            "admin_group": user_data.pop("admin_group", []),
        }

        user = self._create(
            User,
            user_data,
            defaults,
        )

        if nested_data["prices"]:
            price_data = nested_data["prices"]
            if "id" in price_data:
                del price_data["id"]
            price = self._get_or_create(Price, price_data, filters={"price_code": price_data["price_code"]})
            user.price_id = price.id
            self.session.flush([user])

        # Обработка вложенных списков
        self._process_nested_list(nested_data["partners"], PartnerCode, user, "partners")
        self._process_nested_list(nested_data["promos"], Promo, user, "promos")
        self._process_nested_list(
            nested_data["telegram"],
            Telegram,
            user,
            "telegram",
            {"user_id": user.id},
        )
        self._process_nested_list(
            nested_data["telegram_message"],
            TelegramMessage,
            user,
            "telegram_message",
            {"user_id": user.id},
        )

        # Обработка транзакций
        for transaction in nested_data["transactions"]:
            old_id = transaction.pop("id", None)
            transaction["user_id"] = user.id
            new_transaction = self._create(UserTransaction, transaction)
            if old_id:
                self.redis_client.set(f"transaction_mapper:{old_id}", json.dumps(new_transaction.id))

        # Обработка заказов
        for order in nested_data["orders"]:
            self._migrate_order(order, user)

        # Обработка статистики заказов
        for order_stat in nested_data["orders_stats"]:
            self._migrate_order_stat(order_stat, user)

        # Рекурсивная миграция admin_group
        for admin_user in nested_data["admin_group"]:
            self.migrate_user(admin_user, admin_parent_id=user.id)

    def create_order_category(self, item: dict, order: Order) -> None:
        """Создание категории заказа."""
        category_model_mapper = {
            "обувь": Shoe,
            "белье": Linen,
            "парфюм": Parfum,
            "одежда": Clothes,
            "носки и прочее": Socks,
        }
        size_quantity_model_mapper = {
            "обувь": ShoeQuantitySize,
            "белье": LinenQuantitySize,
            "одежда": ClothesQuantitySize,
            "носки и прочее": SocksQuantitySize,
        }
        category_field_mapper = {
            "обувь": "shoe_id",
            "белье": "lin_id",
            "одежда": "cl_id",
            "носки и прочее": "socks_id",
        }

        sizes_quantities = item.pop("sizes_quantities", [])
        if "id" in item:
            del item["id"]
        item["order_id"] = order.id
        category = self._create(category_model_mapper[order.category], item)

        for size_quantity in sizes_quantities:
            if "id" in size_quantity:
                del size_quantity["id"]
            size_quantity[category_field_mapper[order.category]] = category.id
            self._create(size_quantity_model_mapper[order.category], size_quantity)

    def get_order_idn(self, user: User) -> str:
        """Генерация нового order_idn."""
        admin_id = user.admin_parent_id if user.role == settings.ORD_USER else user.id
        stmt = text(
            """UPDATE public.users SET admin_order_num=admin_order_num + 1 
               WHERE id=:admin_id RETURNING admin_order_num, is_crm, is_at2;"""
        ).bindparams(admin_id=admin_id)
        res = self.session.execute(stmt).fetchone()
        self.session.flush()
        return f"{admin_id}_{res.admin_order_num}"

    def _get_or_create(
            self,
            model: type[T],
            data: dict[str, Any],
            filters: dict[str, Any],
    ) -> T:
        """Универсальный метод для создания или получения объекта."""
        instance = self.session.query(model).filter_by(**filters).first()
        if not instance:
            if "id" in data:
                del data["id"]
            instance = model(**data)
            self.session.add(instance)
            self.session.flush([instance])

        return instance

    def _create(
            self,
            model: type[T],
            data: dict[str, Any],
            defaults: dict[str, Any] | None = None,
    ) -> T:
        """Универсальный метод для создания объекта."""
        if "id" in data:
            del data["id"]
        try:
            instance = model(**data)
            self.session.add(instance)
            self.session.flush([instance])
            if defaults:
                for key, value in defaults.items():
                    setattr(instance, key, value)
            return instance
        except Exception as e:
            print(e)

    def _process_nested_list(
            self,
            items: list[dict],
            model: type[T],
            parent: T,
            relation_field: str,
            extra_data: dict = None,
    ) -> None:
        """Обрабатывает список вложенных объектов и связывает их с родителем."""
        for item in items or []:
            if "id" in item:
                del item["id"]
            defaults = extra_data or {}
            item = self._clear_data_before_save(item, defaults)
            if model in [PartnerCode, Promo, Telegram]:
                filters = {"code": item["code"]} if "code" in item else {}
                filters.update({"name": item["name"]} if "name" in item else {})
                item.pop("type", None)
                instance = self._get_or_create(model, item, filters)
            else:
                instance = self._create(model, item, defaults)
            getattr(parent, relation_field).append(instance)
            self.session.flush([instance, parent])

    def _get_manager_id(self, manager_name: Optional[str]) -> Optional[int]:
        """Получает ID менеджера по его имени."""
        if manager_name:
            manager = self.session.query(User).filter_by(login_name=manager_name).first()
            return manager.id if manager else None
        return None

    def _get_transaction_id(self, old_transaction_id: Optional[int]) -> Optional[int]:
        """Получает актуальный ID транзакции из кеша."""
        if old_transaction_id:
            cached_id = self.redis_client.get(f"transaction_mapper:{old_transaction_id}")
            return json.loads(cached_id) if cached_id else None
        return None

    def _get_order_idn(self, order_data: dict, user: User) -> str | None:
        """Генерирует или получает order_idn для заказа."""
        if not order_data.get("order_idn"):
            return None
        key = f"order_idn_mapper:{order_data['order_idn']}"
        new_idn = self.get_order_idn(user)
        self.redis_client.set(key, json.dumps(new_idn))
        return new_idn

    def _migrate_order_file(self, file_data: dict, order: Order, manager_id: Optional[int]) -> None:
        """Миграция файла заказа."""
        if "id" in file_data:
            del file_data["id"]
        manager_name = self.session.query(User).get(manager_id).login_name if manager_id else ""
        origin_name, fs_name = helper_create_filename(
            order_idn=order.order_idn or "",
            manager_name=manager_name,
            filename=file_data["file_system_name"]
        )

        file_response = requests.get(
            f"{self.GET_ARCHIVE_FILE}/{file_data['file_system_name']}",
            headers=self.HEADERS,
        )
        if file_response.ok:
            file_data_stream = BytesIO(file_response.content)
            self.minio_service.upload_file(
                file_data=file_data_stream,
                object_name=fs_name,
                bucket_name=settings.MINIO_CRM_BUCKET_NAME
            )

        file_data["file_system_name"] = fs_name
        file_data["origin_name"] = origin_name
        file_data["order_id"] = order.id
        self._create(OrderFile, file_data)

    def _migrate_order(self, order_data: dict, user: User) -> None:
        """Миграция данных заказа."""
        category_mapper = {
            settings.Shoes.CATEGORY: {"field_name": "shoes", "model": Shoe},
            settings.Linen.CATEGORY: {"field_name": "linen", "model": Linen},
            settings.Parfum.CATEGORY: {"field_name": "parfum", "model": Parfum},
            settings.Clothes.CATEGORY: {"field_name": "clothes", "model": Clothes},
            settings.Socks.CATEGORY: {"field_name": "socks", "model": Socks},
        }

        categories = order_data.pop(category_mapper[order_data["category"]]["field_name"], [])
        order_zip_file = order_data.pop("order_zip_file", {})

        order = self._common_order_create_method(data=order_data, user=user, model=Order)

        if order_zip_file and "id" in order_zip_file:
            self._migrate_order_file(order_zip_file, order, order.manager_id)

        for category in categories:
            self.create_order_category(category, order)

    def _migrate_order_stat(self, order_stat_data: dict, user: User) -> None:
        """Миграция статистики заказа."""
        self._common_order_create_method(order_stat_data, user, OrderStat)

    def _common_order_create_method(self, data: dict[str, Any], user: User, model: type[T]) -> T:
        manager_id = self._get_manager_id(data.pop("manager_id", None))
        transaction_id = self._get_transaction_id(data.pop("transaction_id", None))
        order_idn = self._get_order_idn(data, user)
        if "id" in data:
            del data["id"]

        defaults = {
            "user_id": user.id,
            "manager_id": manager_id,
            "transaction_id": transaction_id,
            "order_idn": order_idn
        }
        data = self._clear_data_before_save(data, defaults)

        return self._create(model, data, defaults)

    @staticmethod
    def _clear_data_before_save(data: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
        for key, value in defaults.items():
            data.pop(key, None)

        return data

    def _clear_cache(self) -> None:
        """Очищает кеш от неактуальных ключей."""
        try:
            to_unlink_keys = [
                key for pattern in self.CACHE_KEY_PATTERNS for key in self.redis_client.keys(pattern)
            ]
            if to_unlink_keys:
                self.redis_client.unlink(*to_unlink_keys)
        except Exception as e:
            logger.error(f"Не удалось очистить кеш: {str(e)}")
