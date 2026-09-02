from config import settings


COSMETICS_SUBCATEGORY_NOTE_KEYS = (
    'decor_ukhod',
    'cosmetics_aroma',
    'cosmetics_cleaning_products',
    'cosmetics_deodorants',
    'cosmetics_nails',
    'cosmetics_tooth',
    'cosmetics_eye',
    'cosmetics_lips',
    'cosmetics_mochalki',
    'cosmetics_rascheski',
    'cosmetics_the_rest_hair',
    'cosmetics_salt_bomb',
    'cosmetics_toilet_paper',
    'cosmetics_tweezers',
    'razor_blades_and_cassettes',
)
TOYS_SUBCATEGORY_NOTE_KEYS = (
    'doll_accessories',
    'puzzles',
    'competition_cars',
    'sets_kits',
    'motorized_toys',
    'animal_creature',
    'scale_models_other',
    'musical_toy_instruments',
    'dolls_human_figures',
    'construction_sets',
    'card_games',
    'board_room_games_inventory',
    'toy_weapons',
    'play_tents',
    'electric_train_sets',
)


def _subcategory_titles(keys: tuple[str, ...]) -> list[str]:
    return [settings.SUB_CATEGORIES_DICT.get(key, key) for key in keys]


def build_subcategory_notes() -> list[dict[str, list[str] | str]]:
    notes = []

    if settings.Clothes.CATEGORY in settings.CATEGORIES_DICT:
        clothes_items = [
            'одежда основная',
            settings.SUB_CATEGORIES_DICT.get('underwear', 'underwear'),
            settings.SUB_CATEGORIES_DICT.get('swimming_accessories', 'swimming_accessories'),
            settings.SUB_CATEGORIES_DICT.get('hats', 'hats'),
            settings.SUB_CATEGORIES_DICT.get('gloves', 'gloves'),
            settings.SUB_CATEGORIES_DICT.get('shawls', 'shawls'),
        ]
        if settings.Socks.CATEGORY in settings.CATEGORIES_DICT:
            clothes_items.append(settings.Socks.CATEGORY)

        notes.append({
            'category': 'Одежда',
            'items': clothes_items,
        })

    if settings.Cosmetics.CATEGORY in settings.CATEGORIES_DICT:
        notes.append({
            'category': 'Косметика',
            'items': _subcategory_titles(COSMETICS_SUBCATEGORY_NOTE_KEYS),
        })

    if 'игрушки' in settings.CATEGORIES_DICT:
        notes.append({
            'category': 'Игрушки',
            'items': _subcategory_titles(TOYS_SUBCATEGORY_NOTE_KEYS),
        })

    return notes
