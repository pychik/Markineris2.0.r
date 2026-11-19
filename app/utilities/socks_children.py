"""Children's sock size grids, validation and export conversion."""
from utilities.exceptions import SizeTypeException
import re


CHILDREN_INTERNATIONAL = ('6', '8', '10', '12', '14', '16', '18', '20', '22')
CHILDREN_AGE_SIZES = {
    'month': (('0-3', '6'), ('3-6', '8'), ('6-9', '10')),
    'years': (('1,5', '12'), ('2-3', '14'), ('4-5', '16'),
              ('6-7', '18'), ('8-9', '20'), ('10-12', '22')),
}


def normalize_socks_size(size: str, size_type: str) -> str:
    value = str(size or '').strip()
    if size_type == 'years' and value == '1.5':
        return '1,5'
    if re.fullmatch(r'\d+\.0', value):
        return value[:-2]
    return value


def parse_socks_children(value: str, gender: str, size_type: str) -> bool:
    """Read optional Excel flags; retain support for templates without this column."""
    flag = str(value or '').strip().lower()
    if flag in {'', 'nan', 'none'}:
        return gender == 'Детск.' or size_type in CHILDREN_AGE_SIZES
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
            if not is_children or value not in dict(CHILDREN_AGE_SIZES[size_type]):
                raise SizeTypeException(f'Недопустимый детский размер: {value} ({size_type}).')
        elif size_type == 'МЕЖДУНАРОДНЫЙ':
            if is_children and value not in CHILDREN_INTERNATIONAL and value != 'ONE SIZE':
                raise SizeTypeException('Выберите международный размер из детской сетки.')
            if not is_children and value in CHILDREN_INTERNATIONAL:
                raise SizeTypeException('Для этого размера включите «Детский товар».')
        elif size_type == 'РОССИЯ':
            child_sizes = {'7', '8-10', '12', '14', '16', '18', '20', '22'}
            if is_children and value not in child_sizes | {'ЕДИНЫЙ РАЗМЕР'}:
                raise SizeTypeException('Выберите российский размер из детской сетки.')
            if not is_children and value in child_sizes:
                raise SizeTypeException('Для этого размера включите «Детский товар».')


def socks_size_for_export(size: str, size_type: str, flag_046: bool = False) -> tuple[str, str]:
    value = normalize_socks_size(size, size_type)
    if flag_046 and size_type in CHILDREN_AGE_SIZES:
        try:
            return dict(CHILDREN_AGE_SIZES[size_type])[value], 'МЕЖДУНАРОДНЫЙ'
        except KeyError:
            raise SizeTypeException(f'Недопустимый возрастной размер: {value} ({size_type}).') from None
    return value, size_type
