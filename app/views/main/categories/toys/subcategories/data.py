from enum import Enum


class ToysSubcategories(str, Enum):
    doll_accessories = "doll_accessories"
    puzzles = "puzzles"
    competition_cars = "competition_cars"
    sets_kits = "sets_kits"
    motorized_toys = "motorized_toys"
    animal_creature = "animal_creature"

    @classmethod
    def has_value(cls, value: str | None) -> bool:
        if not value:
            return False
        return value in cls._value2member_map_
