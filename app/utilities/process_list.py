def main(path: str) -> list:
    with open(file=path, mode='r') as f:
        res_list = f.read().split('\n')
    return res_list


def make_declination_dict(path: str):
    with open(file=path, mode='r') as f:
        res_list = f.read().split('\n')

        res_dict = {el.split(" ")[0]: {"Жен.": el.split(" ")[1], "Муж.": el.split(" ")[2], "Унисекс": el.split(" ")[3],
                                       "Детск": el.split(" ")[4]} for el in res_list}
        print(res_dict)


def make_clothes_list(path: str):
    with open(file=path, mode='r') as f:
        res_list = f.readline().split(',')
    print(res_list)


def make_shoes_materials(path: str) -> dict:
    with open(file=path, mode='r') as file:
        material_groups = file.read().split('\n\n')
        res_dict = dict()
        for materials_raw in material_groups:
            materials = materials_raw.split('\n')
            for material in materials[1:]:
                res_dict[material] = materials[0]
    return res_dict


if __name__ == "__main__":
    res_dict = make_shoes_materials(path='upload_tests/shoe_materials.txt')

    print(res_dict)
# from models import db, UserTransaction
#
# try:
#     processing_transactions = UserTransaction.query.filter(UserTransaction.type == True, UserTransaction.op_cost!=0).all()
#
#     for el in processing_transactions:
#         print(el.id, el.orders, el.wo_account_info)
#         el.order= []
#         el.status=3
#     db.session.commit()
# except Exception as e:
#     db.session.rollback()
#     print(e)