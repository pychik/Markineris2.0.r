from collections import namedtuple


# order_list_common object
Olc = namedtuple("Olc", "order_list company_type company_name company_idn\
            edo_type edo_id mark_type trademark orders_pos_count pos_count total_price price_exist")

OLC_NONE = Olc(None, None, None, None, None, None, None, None, None, None, None, None)
OLC_PARFUM_NONE = tuple((None for _ in range(12)))
OLC_PARFUM_9NONE = tuple((None for _ in range(9)))
