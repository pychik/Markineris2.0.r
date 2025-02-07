class BalanceUpdateError(Exception):
    """Ошибка при обновлении баланса пользователя."""


class UserNotFoundError(Exception):
    """Пользователь не найден."""


class NegativeBalanceError(Exception):
    """Отрицательный баланс пользователя после редактирвоание баланса."""


class EmptyFileToUploadError(Exception):
    """Передан пустой файл для загрузки."""


class GetFirstPageFromPDFError(Exception):
    """Ошибка при получении первой страницы из файла PDF."""
