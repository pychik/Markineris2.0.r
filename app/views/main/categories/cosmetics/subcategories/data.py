from enum import Enum


class CosmeticsSubcategories(str, Enum):
    decor_ukhod = "decor_ukhod"
    cosmetics_aroma = "cosmetics_aroma"
    cosmetics_cleaning_products = "cosmetics_cleaning_products"
    cosmetics_deodorants = "cosmetics_deodorants"
    cosmetics_nails = "cosmetics_nails"
    cosmetics_tooth = "cosmetics_tooth"
    cosmetics_eye = "cosmetics_eye"
    cosmetics_lips = "cosmetics_lips"
    cosmetics_mochalki = "cosmetics_mochalki"
    cosmetics_rascheski = "cosmetics_rascheski"
    cosmetics_the_rest_hair = "cosmetics_the_rest_hair"
    cosmetics_salt_bomb = "cosmetics_salt_bomb"
    cosmetics_toilet_paper = "cosmetics_toilet_paper"
    cosmetics_tweezers = "cosmetics_tweezers"
    razor_blades_and_cassettes = "razor_blades_and_cassettes"

    @classmethod
    def has_value(cls, value: str | None) -> bool:
        if not value:
            return False
        return value in cls._value2member_map_
