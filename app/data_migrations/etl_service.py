import datetime
from copy import deepcopy

import requests
from sqlalchemy.orm import Session

from config import settings
from data_migrations.schemas import PartnerCodeSchema, UserSchema, SchemaType
from data_migrations.utils import get_hashed_password, make_email, make_login_name, make_password
from logger import logger
from models import User, PartnerCode, ModelType


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
