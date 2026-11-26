"""Children's sock size grids, validation and export formatting."""
from utilities.exceptions import SizeTypeException
import re


CHILDREN_INTERNATIONAL = (
    tuple(str(value) for value in range(6, 29, 2))
    + tuple(f'{value}-{value + 2}' for value in range(6, 27, 2))
)
CHILDREN_AGE_SIZES = {
    'month': ('0-3', '3-6', '6-9'),
    'years': tuple(str(value) for value in range(1, 15)) + ('1-2', '2-3', '3-4', '1-3'),
}
# Older saved positions must remain editable and exportable.
LEGACY_CHILDREN_YEARS = ('1,5', '4-5', '6-7', '8-9', '10-12')
FOOT_LENGTH_SIZE_TYPE = 'ДЛИНА СТОПЫ'
FOOT_LENGTH_SIZES = tuple(f'{value}-{value + 2}' for value in range(6, 32))


def normalize_socks_size(size: str, size_type: str) -> str:
    value = str(size or '').strip()
    if size_type == 'years':
        value = re.sub(r'\s*years$', '', value, flags=re.IGNORECASE).strip()
        if value == '1.5':
            return '1,5'
    if re.fullmatch(r'\d+\.0', value):
        return value[:-2]
    return value


def validate_socks_age(size: str, size_type: str) -> None:
    values = CHILDREN_AGE_SIZES[size_type]
    if size_type == 'years':
        values += LEGACY_CHILDREN_YEARS
    if normalize_socks_size(size, size_type) not in values:
        raise SizeTypeException('Выберите возрастной размер из детского справочника.')


def parse_socks_children(value: str, gender: str, size_type: str, size: str = '') -> bool:
    """Read optional Excel flags; retain support for templates without this column."""
    flag = str(value or '').strip().lower()
    if flag in {'', 'nan', 'none'}:
        child_sizes = set(CHILDREN_INTERNATIONAL)
        if size_type == 'РОССИЯ':
            child_sizes.add('7')
        return (gender == 'Детск.' or size_type in CHILDREN_AGE_SIZES
                or (size_type in {'РОССИЯ', 'МЕЖДУНАРОДНЫЙ'}
                    and normalize_socks_size(size, size_type) in child_sizes))
    if flag in {'да', 'yes', 'true', '1'}:
        return True
    if flag in {'нет', 'no', 'false', '0'}:
        return False
    raise SizeTypeException('В колонке «Детский товар» укажите «Да» или «Нет».')


def validate_socks_sizes(sizes: list, is_children: bool, gender: str) -> None:
    """Keep adult and child grids separate, including requests bypassing the UI."""
    if gender == 'Детск.' and not is_children:
        raise SizeTypeException('Для пола «Детск.» включите «Детский товар».')
    for size, _quantity, size_type in sizes:
        value = normalize_socks_size(size, size_type)
        if size_type in CHILDREN_AGE_SIZES:
            if not is_children:
                raise SizeTypeException(f'Недопустимый детский размер: {value} ({size_type}).')
            validate_socks_age(value, size_type)
        elif size_type == FOOT_LENGTH_SIZE_TYPE:
            if is_children or value not in FOOT_LENGTH_SIZES:
                raise SizeTypeException('Длина стопы доступна только для взрослых: диапазоны от 6-8 до 31-33.')
        elif size_type == 'МЕЖДУНАРОДНЫЙ':
            if is_children and value not in CHILDREN_INTERNATIONAL and value != 'ONE SIZE':
                raise SizeTypeException('Выберите международный размер из детской сетки.')
            if not is_children and value in CHILDREN_INTERNATIONAL:
                raise SizeTypeException('Для этого размера включите «Детский товар».')
        elif size_type == 'РОССИЯ':
            child_sizes = set(CHILDREN_INTERNATIONAL) | {'7'}
            if is_children and value not in child_sizes | {'ЕДИНЫЙ РАЗМЕР'}:
                raise SizeTypeException('Выберите российский размер из детской сетки.')
            if not is_children and value in child_sizes:
                raise SizeTypeException('Для этого размера включите «Детский товар».')
        else:
            raise SizeTypeException(f'Неизвестный тип размера носков: {size_type}.')


def socks_size_for_export(size: str, size_type: str, flag_046: bool = False) -> tuple[str, str]:
    value = normalize_socks_size(size, size_type)
    if size_type in CHILDREN_AGE_SIZES:
        if size_type == 'years':
            value = f'{value} years'
        return value, 'МЕЖДУНАРОДНЫЙ'
    return value, size_type
