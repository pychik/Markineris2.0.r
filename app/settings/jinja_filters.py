def count_quantity(value_list,):
    """
    custom max calculation logic
    """

    return sum(list(map(lambda x: x.quantity, value_list)))
