# Clothes URL Logic

Ветка `clothes_url_logic_renew` меняет только слой URL и входную страницу одежды.

## Что изменено

- `/clothes/` теперь открывает индекс одежды с поиском по ТНВЭД/виду товара и плитками подкатегорий.
- Основная форма одежды переехала на `/clothes/common`.
- Подкатегории одежды открываются как `/clothes/<subcategory>`, например `/clothes/underwear` и `/clothes/hats`.
- `socks` остается отдельным backend/model и отдельной категорией обработки. Плитка в индексе одежды ведет через `/clothes/socks`, затем переводит пользователя на существующий `socks.index`.

## Legacy

- Старые пути заказов `/clothes/<order_id>/` и `/clothes/<order_id>/<update_flag>` оставлены.
- Старые ссылки с query `?subcategory=...` перенаправляются на новые path-based URL.
- Обувь, белье и парфюм остаются отдельными категориями и не входят в индекс одежды.

## Где смотреть

- Routes: `app/views/main/categories/clothes/main.py`
- Index data: `app/views/main/categories/clothes/support.py`
- Template: `app/templates/categories/clothes/index.html`
- Search JS: `app/static/main_v2/js/categories/clothes_index.js`
