from src.schemas.user import TgUserSchema
from src.gateways.db.models.user import TgUser
from src.gateways.db.repositories.abstract import AbstractUserRepository
from src.service.abstract import AbstractUserService
from src.service.utils import generate_verification_code


class UserService(AbstractUserService):

    def __init__(self, repo: AbstractUserRepository):
        self.repo = repo

    async def get_users(self) -> list[TgUser]:
        return await self.repo.get_users()

    async def get_user(self, user_id: int) -> TgUser:
        return await self.repo.get_user(user_id=user_id)

    async def check_user_exist_by_email(self, email: str) -> bool:
        user = await self.repo.get_flask_user_obj(email=email)

        return user is not None

    async def get_or_create(self, user_schema: TgUserSchema) -> TgUser:
        user = await self.repo.get_user(user_schema.tg_user_id)
        if user:
            return user
        return await self.repo.create(user_schema.model_dump())

    # todo: переименовать
    async def confirm_user_verification(self, user_id: int) -> TgUser:
        return await self.repo.update(user_id=user_id, data={"is_verified": False})

    async def generate_verification_code(self, user_id: int) -> TgUser:
        user = await self.get_user(user_id)

        if user.verification_code:
            return user

        verification_code = generate_verification_code()

        return await self.repo.update(user_id=user_id, data={"verification_code": verification_code})
