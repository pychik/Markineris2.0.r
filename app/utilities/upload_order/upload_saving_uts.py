from datetime import datetime
from typing import Optional

from flask import flash

from config import settings
from logger import logger
from models import User, Order, Shoe, ShoeQuantitySize, Clothes, ClothesQuantitySize, Parfum, Linen, LinenQuantitySize, \
    db, Socks, SocksQuantitySize
from utilities.categories_data.subcategories_data import ClothesSubcategories


def upload_shoe_st(order_list: list, order: Order) -> Order:
    for el in order_list:
        rd_date = datetime.strptime(el[14].strip(), '%d.%m.%Y').date() if el[14].strip() else None
        new_shoe_order = Shoe(trademark=el[0].strip(),
                              article=el[1].strip(), type=el[2].strip(),
                              color=el[3].strip(), box_quantity=1,
                              material_top=el[5].strip(),
                              material_lining=el[6].strip(),
                              material_bottom=el[7].strip(),
                              tnved_code=el[8].strip(),
                              gender=el[9].strip(), country=el[11].strip(),
                              rd_type=el[12].strip(), rd_name=el[13].strip(), rd_date=rd_date,
                              article_price=0, tax=0)

        new_size_quantity = ShoeQuantitySize(size=el[4].strip(), quantity=el[10].strip())
        new_shoe_order.sizes_quantities.append(new_size_quantity)

        order.shoes.append(new_shoe_order)
    return order


def upload_shoe_ext(order_list: list, order: Order) -> Order:
    for el in order_list:
        rd_date = datetime.strptime(el[14].strip(), '%d.%m.%Y').date() if el[14].strip() else None
        new_shoe_order = Shoe(article=el[0].strip(),
                              trademark=el[1].strip(), type=el[2].strip(),
                              material_top=el[3].strip(),
                              material_lining=el[4].strip(),
                              material_bottom=el[5].strip(),
                              color=el[6].strip(), box_quantity=int(el[7].strip()),
                              country=el[9].strip(),
                              tnved_code=el[10].strip(),
                              gender=el[11].strip(),
                              rd_type=el[12].strip(), rd_name=el[13].strip().replace('№', ''), rd_date=rd_date,
                              article_price=0, tax=0)
        from utilities.support import upload_divide_sizes_quantities
        sizes, quantities = upload_divide_sizes_quantities(value=el[8].strip())
        sizes_quantities = zip(sizes, quantities)

        new_shoe_order.sizes_quantities.extend((ShoeQuantitySize(size=el[0], quantity=el[1]) for el in sizes_quantities))
        order.shoes.append(new_shoe_order)
    return order


def upload_clothes_st(order_list: list, order: Order, subcategory: str = None) -> Order:
    for el in order_list:
        rd_date = datetime.strptime(el[13].strip(), '%d.%m.%Y').date() if (el[13].strip() and el[13] != 'nan') else None
        new_clothes_order = Clothes(trademark=el[0].strip(),
                                    article=el[1].strip(), type=el[2].strip(),
                                    color=el[3].strip(), box_quantity=1,
                                    gender=el[4].strip(),
                                    content=el[7].strip(),
                                    tnved_code=el[8].strip(),
                                    country=el[10].strip(),
                                    rd_type=el[11].strip(), rd_name=el[12].strip().replace('№', ''), rd_date=rd_date,
                                    article_price=0, tax=0)
        if subcategory == ClothesSubcategories.underwear.value:
            new_clothes_order.subcategory = subcategory

        new_size_quantity = ClothesQuantitySize(size=el[6].strip(), quantity=el[9].strip(), size_type=el[5].strip())
        new_clothes_order.sizes_quantities.append(new_size_quantity)

        order.clothes.append(new_clothes_order)
    return order


def upload_socks_st(order_list: list, order: Order) -> Order:
    for el in order_list:
        rd_date = datetime.strptime(el[13].strip(), '%d.%m.%Y').date() if (el[13].strip() and el[13] != 'nan') else None
        new_socks_order = Socks(trademark=el[0].strip(),
                                article=el[1].strip(), type=el[2].strip(),
                                color=el[3].strip(), box_quantity=1,
                                gender=el[4].strip(),
                                content=el[7].strip(),
                                tnved_code=el[8].strip(),
                                country=el[10].strip(),
                                rd_type=el[11].strip(), rd_name=el[12].strip().replace('№', ''), rd_date=rd_date,
                                article_price=0, tax=0)

        new_size_quantity = SocksQuantitySize(size=el[6].strip(), quantity=el[9].strip(), size_type=el[5].strip())
        new_socks_order.sizes_quantities.append(new_size_quantity)

        order.socks.append(new_socks_order)
    return order


def upload_parfum_st(order_list: list, order: Order) -> Order:

    new_parfum_order = [Parfum(trademark=el[0].strip(), volume_type=el[1].strip(), volume=el[2].strip(),
                               package_type=el[3].strip(), material_package=el[4].strip(), type=el[5].strip(),
                               with_packages="нет", box_quantity=1, quantity=el[7].strip(), country=el[8].strip(),
                               rd_type=el[9].strip(), rd_name=el[10].replace('№', ''),
                               rd_date=datetime.strptime(el[11].strip(), '%d.%m.%Y').date() if el[11].strip() else None,
                               tnved_code=el[6].strip(), article_price=0, tax=0) for el in order_list]
    order.parfum.extend(new_parfum_order)
    return order


def upload_parfum_ext(order_list: list, order: Order) -> Order:
    new_parfum_order = [Parfum(trademark=el[0].strip(), volume_type=el[1].strip(), volume=el[2].strip(),
                               package_type=el[3].strip(), material_package=el[4].strip(), type=el[5].strip(),
                               with_packages="да", box_quantity=el[7].strip(), quantity=el[8].strip(),
                               country=el[9].strip(),
                               rd_type=el[10].strip(), rd_name=el[11].replace('№', ''),
                               rd_date=datetime.strptime(el[12].strip(), '%d.%m.%Y').date() if el[12].strip() else None,
                               tnved_code=el[6].strip(), article_price=0, tax=0)
                        for el in order_list]
    order.parfum.extend(new_parfum_order)
    return order


def upload_linen_st(order_list: list, order: Order) -> Order:
    for el in order_list:
        rd_date = datetime.strptime(el[14].strip(), '%d.%m.%Y').date() if el[14].strip() else None
        new_linen_order = Linen(trademark=el[0].strip(),
                                article=el[1].strip(), type=el[2].strip(),
                                color=el[3].strip(), with_packages="нет", box_quantity=1,
                                customer_age=el[4].strip(),
                                textile_type=el[5].strip(),
                                content=el[6].strip(),
                                tnved_code=el[9].strip(),
                                country=el[11].strip(),
                                rd_type=el[12].strip(), rd_name=el[13].strip().replace('№', ''), rd_date=rd_date,
                                article_price=0, tax=0)

        new_size_quantity = LinenQuantitySize(size=f"{el[7].strip()}*{el[8].strip()}", quantity=el[10].strip())
        new_linen_order.sizes_quantities.append(new_size_quantity)

        order.linen.append(new_linen_order)
    return order


def upload_linen_ext(order_list: list, order: Order) -> Order:
    for el in order_list:
        rd_date = datetime.strptime(el[15].strip(), '%d.%m.%Y').date() if el[15].strip() else None
        new_linen_order = Linen(trademark=el[0].strip(),
                                article=el[1].strip(), type=el[2].strip(),
                                color=el[3].strip(), with_packages="да", box_quantity=el[10].strip(),
                                customer_age=el[4].strip(),
                                textile_type=el[5].strip(),
                                content=el[6].strip(),
                                tnved_code=el[9].strip(),
                                country=el[12].strip(),
                                rd_type=el[13].strip(), rd_name=el[14].strip().replace('№', ''), rd_date=rd_date,
                                article_price=0, tax=0)

        new_size_quantity = LinenQuantitySize(size=f"{el[7].strip()}*{el[8].strip()}", quantity=el[11].strip())
        new_linen_order.sizes_quantities.append(new_size_quantity)

        order.linen.append(new_linen_order)
    return order


def upload_table_shoes(user: User, order: Order, order_list: list, type_upload: str) -> Optional[int]:
    try:
        if type_upload == settings.Upload.STANDART:
            n_order = upload_shoe_st(order_list=order_list, order=order)
        else:
            n_order = upload_shoe_ext(order_list=order_list, order=order)
        user.orders.append(n_order)
        db.session.commit()
        no_id = n_order.id
        return no_id
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ORDER_ADD_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)
        return None


def upload_table_clothes(user: User, order: Order, order_list: list, type_upload: str, subcategory: str = None) -> Optional[int]:
    try:
        n_order = upload_clothes_st(order_list=order_list, order=order, subcategory=subcategory)
        user.orders.append(n_order)
        db.session.commit()
        no_id = n_order.id
        return no_id
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ORDER_ADD_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)
        return None


def upload_table_socks(user: User, order: Order, order_list: list, type_upload: str) -> Optional[int]:
    try:
        n_order = upload_socks_st(order_list=order_list, order=order)
        user.orders.append(n_order)
        db.session.commit()
        no_id = n_order.id
        return no_id
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ORDER_ADD_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)
        return None


def upload_table_parfum(user: User, order: Order, order_list: list, type_upload: str) -> Optional[int]:
    try:

        if type_upload == settings.Upload.STANDART:
            n_order = upload_parfum_st(order_list=order_list, order=order)
        else:
            n_order = upload_parfum_ext(order_list=order_list, order=order)
        user.orders.append(n_order)
        db.session.commit()
        no_id = n_order.id
        return no_id
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ORDER_ADD_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)
        return None


def upload_table_linen(user: User, order: Order, order_list: list, type_upload: str) -> Optional[int]:
    try:
        if type_upload == settings.Upload.STANDART:
            n_order = upload_linen_st(order_list=order_list, order=order)
        else:
            n_order = upload_linen_ext(order_list=order_list, order=order)
        user.orders.append(n_order)
        db.session.commit()
        no_id = n_order.id
        return no_id
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ORDER_ADD_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)
        return None


def upload_table_common(user: User, company_type: str, company_name: str,
                        company_idn: str, edo_type: str, edo_id: str, mark_type: str,
                        order_list: list, category: str, type_upload: str, subcategory: str = None) -> Optional[int]:
    order = Order(company_type=company_type, company_name=company_name,
                  edo_type=edo_type, edo_id=edo_id,
                  company_idn=company_idn, mark_type=mark_type,
                  category=category, processed=False)
    match category:
        case settings.Shoes.CATEGORY:
            return upload_table_shoes(user=user, order=order, order_list=order_list, type_upload=type_upload)

        case settings.Clothes.CATEGORY:
            return upload_table_clothes(user=user, order=order, order_list=order_list, type_upload=type_upload,
                                        subcategory=subcategory)
        case settings.Socks.CATEGORY:
            return upload_table_socks(user=user, order=order, order_list=order_list, type_upload=type_upload)

        case settings.Parfum.CATEGORY:
            return upload_table_parfum(user=user, order=order, order_list=order_list, type_upload=type_upload)
        case settings.Linen.CATEGORY:
            return upload_table_linen(user=user, order=order, order_list=order_list, type_upload=type_upload)
