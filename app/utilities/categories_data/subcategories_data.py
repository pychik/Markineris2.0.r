from enum import Enum

from config import settings


# Базовый класс для категорий
class Category(Enum):
    @classmethod
    def is_subcategory(cls, subcategory: str):
        """Проверяет, является ли переданная субкатегория частью этой категории."""
        return subcategory in cls._value2member_map_

    @staticmethod
    def check_subcategory(category: str, subcategory: str) -> bool:
        if not subcategory and category in settings.CATEGORIES_DICT:
            return True
        match category:
            case settings.Clothes.CATEGORY:

                return ClothesSubcategories.is_subcategory(subcategory=subcategory)
            case _:
                return False


class ClothesSubcategories(Category, Enum):
    common: str = "common"
    underwear: str = "underwear"
    swimming_accessories: str = "swimming_accessories"

    @classmethod
    def get_category_name(cls):
        """Возвращает название категории."""
        return settings.Clothes.CATEGORY

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"

# method get_subcategory in .subcategories_logic to check and edit after new category adding logic
#  edit clothes.main check all methods
#  edit ClothesProcessor.get_gender_dec in utilities.download
# validators.ValidateProcess.check_tnveds
# we need to

# if __name__ == "__main__":
#
#     class Settings:
#         class Clothes:
#             CATEGORY = "clothes"
#
#         CATEGORIES_DICT = {
#             "clothes": ClothesSubcategories,
#         }
#
#     settings = Settings()
#
#     # Тесты
#     print(Category.check_subcategory("clothes", "common"))
#     print(Category.check_subcategory("clothes", "underwear"))
#     print(Category.check_subcategory("clothes", "unknown"))
#     print(Category.check_subcategory("unknown_category", "common"))
#     print(Category.check_subcategory("clothes", ""))
#     print(Category.check_subcategory("unknown_category", ""))
