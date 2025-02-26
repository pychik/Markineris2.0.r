import pandas as pd
import re


def remove_numbers(text):
    if pd.isna(text):  # Проверяем, является ли значение NaN
        return ''  # Возвращаем пустую строку для NaN
    return re.sub(r'[<>\d]+', '', str(text)).strip()  # Преобразуем в строку и удаляем числа


def extract_tnved_codes_and_descriptions(descriptions):
    codes_and_descriptions = set()  # Используем set для автоматического удаления дубликатов
    codes = set()  # Для хранения уникальных TNVED кодов
    for desc in descriptions:
        # Извлекаем TNVED коды (10-значные числа)
        tnved_codes = re.findall(r'\d{10}', str(desc))  # Извлекаем 10-значные коды
        for code in tnved_codes:
            # Удаляем TNVED код (например, <6406909000>) из описания
            cleaned_description = re.sub(r'<\d{10}>', '', str(desc)).strip()
            # Добавляем код в set кодов
            codes.add(code)
            # Добавляем (код, очищенное описание) в set для уникальности
            codes_and_descriptions.add((code, cleaned_description))
    return tuple(sorted(codes)), tuple(sorted(codes_and_descriptions))  # Возвращаем отсортированные кортежи


NEW_SUBCATEGORY = "BRA"
# Загружаем Excel-файл
file_path = 'bra.xlsx'
sheet_name = 0

df = pd.read_excel(file_path, sheet_name=sheet_name)

# df = df.iloc[1:]  # Пропускаем строку заголовка
df.columns = ['A', 'B', 'C']  # Переименовываем колонки для удобства

# Заполняем пустые ячейки в колонке 'A' последним непустым значением
df['A'] = df['A'].ffill()

# Удаляем строки, где все значения NaN
df = df.dropna(how='all')

# для данных формата 056 выделяем колонку А с номерами
df['T'] = df['A'].astype(str)
# Преобразуем колонку 'A' в строки и очищаем от чисел
df['A'] = df['A'].astype(str).apply(remove_numbers)

# формируем словарь для 056 формата и список всех типов
dictionary_056 = df.set_index('A')['T'].to_dict()
sub_category_types_tuple = list(dictionary_056.keys())
sub_category_types_tuple.sort()
# Группируем по типу товара
grouped = df.groupby('A')

tnved_dict = {}
tnved_list = []
for item_type, group in grouped:
    combined_descriptions = []

    # Итерируемся по каждой строке в группе
    for _, row in group.iterrows():
        # Разделяем описания в колонках 'B' и 'C' по символу новой строки
        desc_b = str(row['B']).split('\n') if pd.notna(row['B']) else []
        desc_c = str(row['C']).split('\n') if pd.notna(row['C']) else []

        # Объединяем описания из обеих колонок
        combined_descriptions.extend(desc_b)
        combined_descriptions.extend(desc_c)

    # Получаем TNVED коды и описания в нужном формате
    codes, codes_and_descriptions = extract_tnved_codes_and_descriptions(combined_descriptions)

    # Организуем словарь с кодами и описаниями в виде кортежа
    tnved_dict[item_type] = (codes, codes_and_descriptions)
    tnved_list.append(codes)
res_tnved_list = list(set([subel for el in tnved_list for subel in el]))
res_tnved_list.sort()

# Выводим результат
print(f"{NEW_SUBCATEGORY}_TYPES =", sub_category_types_tuple, end='\n\n')
print(f"{NEW_SUBCATEGORY}_TYPES_056 =", dictionary_056, end='\n\n')
print(f"{NEW_SUBCATEGORY}_TNVEDS =", res_tnved_list, end='\n\n')
print(f"{NEW_SUBCATEGORY}_TNVED_DICT =", tnved_dict)


# # Опционально сохраняем словарь в файл
# output_file = 'subcategory_dict.py'
# with open(output_file, 'w', encoding='utf-8') as f:
#     f.write("SOCKS_TNVED_DICT = " + str(tnved_dict))