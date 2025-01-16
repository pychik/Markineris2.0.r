from datetime import datetime


def count_quantity(value_list,):
    """
    custom max calculation logic
    """

    return sum(list(map(lambda x: x.quantity, value_list)))


def time_since(dt: datetime):
    def get_plural_form(number: float, time_units: tuple[str, str, str]):
        if number % 10 == 1 and number % 100 != 11:
            return time_units[0]
        elif 2 <= number % 10 <= 4 and (number % 100 < 10 or number % 100 >= 20):
            return time_units[1]
        else:
            return time_units[2]
    now = datetime.now()
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        second_form = get_plural_form(seconds, ("секунда", "секунды", "секунд"))
        return f"{int(seconds)} {second_form} назад"
    elif seconds < 3600:
        minutes = seconds // 60
        minute_form = get_plural_form(minutes, ("минута", "минуты", "минут"))
        return f"{int(minutes)} {minute_form} назад"
    elif seconds < 86400:
        hours = seconds // 3600
        hour_form = get_plural_form(hours, ("час", "часа", "часов"))
        return f"{int(hours)} {hour_form} назад"
    else:
        days = seconds // 86400
        day_form = get_plural_form(days, ("день", "дня", "дней"))
        return f"{int(days)} {day_form} назад"
