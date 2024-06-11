from src.gateways.db.models.user import TgUser, FlaskUserModel
from src.gateways.db.repositories.abstract import AbstractUserRepository
from src.infrastructure.utils import generate_verification_code
from src.schemas.user import TgUserSchema
from src.service.abstract import AbstractUserService


class UserService(AbstractUserService):

    def __init__(self, repo: AbstractUserRepository):
        self.repo = repo

    async def get_user(self, user_id: int) -> TgUser:
        return await self.repo.get_user(user_id=user_id)

    async def get_flask_user_by_id(self, user_id: int) -> FlaskUserModel:
        return await self.repo.get_flask_user_by_id(user_id=user_id)

    async def check_user_exist_by_email(self, email: str) -> FlaskUserModel | None:
        user = await self.repo.get_flask_user_obj(email=email)

        return user

    async def get_or_create(self, user_schema: TgUserSchema) -> TgUser:
        user = await self.repo.get_user(user_schema.tg_user_id)
        if user:
            return user
        return await self.repo.create(user_schema.model_dump())

    async def generate_verification_code(self, user_id: int) -> TgUser:
        verification_code = generate_verification_code()

        return await self.repo.update(user_id=user_id, data={"verification_code": verification_code})

    async def get_verification_code(self, user: TgUser) -> str:
        if user.verification_code:
            return user.verification_code

        user = await self.generate_verification_code(user_id=user.tg_user_id)

        return user.verification_code

    async def delete_user(self, user_id: int) -> None:
        await self.repo.delete_user(user_id=user_id)
