from enum import Enum


class ToysSubcategories(str, Enum):
    doll_accessories = "doll_accessories"
    puzzles = "puzzles"
    competition_cars = "competition_cars"
    sets_kits = "sets_kits"
    motorized_toys = "motorized_toys"
    animal_creature = "animal_creature"
    scale_models_other = "scale_models_other"
    musical_toy_instruments = "musical_toy_instruments"
    dolls_human_figures = "dolls_human_figures"
    construction_sets = "construction_sets"
    card_games = "card_games"
    board_room_games_inventory = "board_room_games_inventory"
    toy_weapons = "toy_weapons"
    play_tents = "play_tents"

    @classmethod
    def has_value(cls, value: str | None) -> bool:
        if not value:
            return False
        return value in cls._value2member_map_
