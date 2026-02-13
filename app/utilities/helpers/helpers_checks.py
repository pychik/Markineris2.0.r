from config import settings
from models import Shoe, Linen, Parfum, Socks, Clothes
from utilities.categories_data.clothes_common.tnved_processor import get_tnved_codes_for_gender
from utilities.categories_data.subcategories_data import ClothesSubcategories
from utilities.categories_data.underwear_data import UNDERWEAR_TYPE_GENDERS, UNDERWEAR_TNVED_DICT


def rd_name_clean(value) -> str:
    # безопасно чистим "№", даже если None
    return (value or "").replace("№", "").strip()


def _has_rd_fields(item) -> bool:
    return bool(
        (getattr(item, "rd_name", "") or "").strip()
        and (getattr(item, "rd_type", "") or "").strip()
        and getattr(item, "rd_date", None)
    )


def _get_countries_without_rd(item) -> list[str]:
    """
    Ограниченные страны БЕЗ РД — по категории (по классу модели).
    """
    if isinstance(item, Clothes) or isinstance(item, Socks):
        return list(settings.CLOTHES_COUNTRIES_RD)

    if isinstance(item, Shoe):
        return list(settings.SHOES_COUNTRIES_RD)

    if isinstance(item, Linen):
        return list(settings.LINEN_COUNTRIES_RD)

    if isinstance(item, Parfum):
        return list(settings.PARFUM_COUNTRIES_RD)



    # если вдруг неизвестная модель — безопасный дефолт
    return list(settings.COUNTRIES_LIST)


def _check_country_by_rd(item) -> str | bool:
    """
    Универсальная проверка страны с учётом РД.

    Возвращает:
      - False, если корректно
      - str, если ошибка
    """
    country_value = (getattr(item, "country", "") or "").upper().strip()

    if not country_value:
        return "Страна не заполнена"

    has_rd = _has_rd_fields(item)

    allowed = list(settings.COUNTRIES_LIST) if has_rd else _get_countries_without_rd(item)
    allowed_up = {str(c).upper().strip() for c in allowed}

    if country_value in allowed_up:
        return False

    if has_rd:
        return f"Недопустимая страна: {country_value}. Допустимые страны: {allowed}"

    return f"{settings.Clothes.UPLOAD_COUNTRY_ERROR} Допустимые страны без РД: {allowed}"


def _append_err(base: str, extra: str | bool) -> str:
    if not extra:
        return base
    return f"{base}; {extra}"


def _check_clothes_compatibility(clothes) -> str | bool:
    """
    Проверяет, сочетаются ли type/gender/tnved/size у одной позиции.
    Возвращает:
      - False, если позиция корректна
      - str "[Тип Пол, ТНВЭД] ..." — если есть ошибки
    """
    def _needs_gender(subcat) -> bool:
        return subcat in ('', ClothesSubcategories.underwear.value, ClothesSubcategories.common.value, None, 'None')

    def _norm_tnved(s: str) -> str:
        return (s or '').replace(' ', '').replace('-', '').strip()

    cl_type   = (clothes.type or '').strip()
    cl_gender = (clothes.gender or '').strip()
    cl_tnved  = (clothes.tnved_code or '').strip()
    cl_subcat = getattr(clothes, 'subcategory', None)

    # --- Проверка пола ---
    need_gender = _needs_gender(cl_subcat)

    if need_gender:
        match cl_subcat:
            case ClothesSubcategories.underwear.value:
                correct_genders = UNDERWEAR_TYPE_GENDERS.get(cl_type.upper(), [])
                gender_ok = bool(cl_gender) and (cl_gender in correct_genders)
                data = UNDERWEAR_TNVED_DICT
            case _:
                correct_genders = settings.Clothes.CLOTHES_TYPE_GENDERS.get(cl_type.upper(), [])
                gender_ok = bool(cl_gender) and (cl_gender in correct_genders)
                data = settings.Clothes.CLOTHES_TNVED_DICT
    else:
        gender_ok = True

    # --- Проверка ТНВЭД ---
    tnved_ok = True
    if cl_tnved:
        try:
            allowed_tnveds = get_tnved_codes_for_gender(type_name=cl_type, gender=cl_gender, data=data) or ()
        except Exception:
            allowed_tnveds = ()
        allowed_tnveds = {_norm_tnved(x) for x in allowed_tnveds}
        tnved_ok = _norm_tnved(cl_tnved) in allowed_tnveds

    # --- Проверка соответствия размеров типу (только для РОССИЯ) ---
    size_errors = []  # ← собираем несоответствия

    for sq in getattr(clothes, "sizes_quantities", []) or []:
        sq_size = (getattr(sq, "size", "") or "").strip()
        sq_size_type = (getattr(sq, "size_type", "") or "").strip()

        if sq_size_type == settings.Clothes.DEFAULT_SIZE_TYPE and sq_size not in settings.Clothes.CLOTHES_ST_RUSSIA:
            size_errors.append(sq_size)

    sizes_ok = not size_errors

    # --- Итог ---
    country_err = _check_country_by_rd(clothes)

    if gender_ok and tnved_ok and sizes_ok and not country_err:
        return False

    # Формируем короткое описание для отчёта
    t = cl_type or '—'
    g = cl_gender or '—'
    n = cl_tnved or '—'

    base = f"[{t} {g}, {n}]"

    if size_errors:
        bad = ", ".join(size_errors)
        base = f"{base} — несоответствующие размеры: {bad}"

    base = _append_err(base, country_err)

    return base


def _check_socks_compatibility(sock: Socks) -> str | bool:
    country_err = _check_country_by_rd(sock)
    if not country_err:
        return False
    return country_err


def _check_linen_compatibility(linen) -> str | bool:
    content = (linen.content or '')
    tnved = (linen.tnved_code or '')
    l_type = (linen.type or '')

    content_up = str(content).upper()
    tnved_norm = str(tnved).replace('.0', '').strip()
    type_up = str(l_type).strip().upper()

    errors = []

    # --- ПРАВИЛО ПО ХЛОПКУ ТОЛЬКО ДЛЯ ОПРЕДЕЛЕННЫХ ТИПОВ ---
    required_tnved = None
    if 'ХЛОПОК' in content_up:
        if 'ПОЛОТЕНЦЕ' in type_up:
            required_tnved = '6302910000'
        elif type_up == 'КОМПЛЕКТ ПОСТЕЛЬНОГО БЕЛЬЯ':
            required_tnved = '6302100001'

    if required_tnved and tnved_norm != required_tnved:
        art = (linen.article or '—')
        t = (linen.type or '—')
        errors.append(
            f"[арт. {art}, тип {t}] Состав содержит ХЛОПОК → допустим только ТНВЭД {required_tnved} "
            f"(сейчас: {tnved_norm or 'пусто'})"
        )

    l_textile_type = (linen.textile_type or '').strip()
    _linen_textile_type_exclude: tuple = ('СИНТЕПОН',)

    linen_ok = ((l_type or '').strip() in settings.Linen.TYPES and l_textile_type not in _linen_textile_type_exclude)

    if not linen_ok:
        t_bad = '' if (l_type or '').strip() in settings.Linen.TYPES else ((l_type or '').strip() or '—')
        tt_bad = '' if l_textile_type not in _linen_textile_type_exclude else (l_textile_type or '—')
        errors.append(f"[{t_bad} {tt_bad}]")

    # --- Страна (универсально) ---
    country_err = _check_country_by_rd(linen)
    if country_err:
        if errors:
            errors[-1] = _append_err(errors[-1], country_err)
        else:
            errors.append(str(country_err))

    if not errors:
        return False

    return "; ".join(errors)


def _check_shoes_compatibility(shoe: Shoe) -> str | bool:
    """
    Проверяет материалы обуви + страну (через универсальный _check_country_by_rd).

    Возвращает:
      - False, если позиция корректна
      - str, если есть ошибки
    """
    s_material_top = (shoe.material_top or "").strip().capitalize()
    s_material_lining = (shoe.material_lining or "").strip().capitalize()

    excepted = settings.Shoes.EXCEPTED_MATERIALS_TOP_LINING

    top_bad = s_material_top in excepted
    lining_bad = s_material_lining in excepted

    # --- Страна ---
    country_err = _check_country_by_rd(shoe)

    # --- Всё корректно ---
    if not top_bad and not lining_bad and not country_err:
        return False

    # --- База по материалам ---
    top = s_material_top if top_bad else "—"
    linen = s_material_lining if lining_bad else "—"
    base = f"[Материал верха {top}, Материал подкладки {linen}]"

    # --- Добавляем страну ---
    base = _append_err(base, country_err)

    return base


def _check_parfum_compatibility(parfum: Parfum) -> str | bool:
    """
    Минимальная проверка парфюма под новые правила ЧЗ:
    - страна с учётом РД (универсальный _check_country_by_rd)

    Возвращает:
      - False если ок
      - str если ошибка
    """
    country_err = _check_country_by_rd(parfum)
    if not country_err:
        return False

    return country_err
