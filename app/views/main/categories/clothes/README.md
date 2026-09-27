# Clothes URL Logic

Ветка `clothes_url_logic_renew` меняет только слой URL и входную страницу одежды.

## Что изменено

- `/clothes/` теперь открывает индекс одежды с поиском по ТНВЭД/виду товара и плитками подкатегорий.
- Основная форма одежды переехала на `/clothes/common`.
- Подкатегории одежды открываются как `/clothes/<subcategory>`, например `/clothes/underwear` и `/clothes/hats`.
- `socks` остается отдельным backend/model и отдельной категорией обработки. Плитка в индексе одежды ведет через `/clothes/socks`, затем переводит пользователя на существующий `socks.index`.
- Результаты поиска по ТНВЭД показывают не только код, но и описание из справочника. Для `common`, `underwear` и носков пары `код + описание` собираются через `get_clothes_tnved_pairs_for_types(...)`, чтобы не делать отдельный Redis/Tezaurus-запрос по каждому виду товара и полу.

## Производительность поиска

- Индекс страницы `/clothes/` должен строиться пакетно через `get_clothes_tnved_pairs_for_types(...)`.
- Не возвращать обход `get_clothes_tnved_genders(...)` + `ClothesSubcategoryProcessor.get_tnveds(...)` в цикле по всем типам и полам: это увеличивает время открытия `/clothes/`.

## Legacy

- Старые пути заказов `/clothes/<order_id>/` и `/clothes/<order_id>/<update_flag>` оставлены.
- Старые ссылки с query `?subcategory=...` перенаправляются на новые path-based URL.
- Обувь, белье и парфюм остаются отдельными категориями и не входят в индекс одежды.

## Где смотреть

- Routes: `app/views/main/categories/clothes/main.py`
- Index data: `app/views/main/categories/clothes/support.py`
- Template: `app/templates/categories/clothes/index.html`
- Search JS: `app/static/main_v2/js/categories/clothes_index.js`
