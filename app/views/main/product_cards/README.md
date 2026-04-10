# Product Cards

Краткая карта модуля `app/views/main/product_cards`, чтобы было понятно, где лежат маршруты, бизнес-логика и связанные сценарии.

## Структура

- [users.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/users.py)
  Пользовательский blueprint `user_product_cards`. Здесь только роуты и привязка URL к handler-функциям.

- [handlers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/handlers.py)
  Главная точка входа пользовательской части. Тут собраны:
  - список карточек пользователя и AJAX-таблица;
  - создание, просмотр, редактирование, удаление карточек;
  - отправка карточек на модерацию;
  - сценарии черновиков заказов, собранных из карточек.

- [support.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/support.py)
  Основная бизнес-логика карточек:
  - конфиг категорий `CATEGORIES_COMMON`;
  - валидация форм;
  - нормализация полей;
  - сохранение category-моделей;
  - правила уникальности товара;
  - дедупликация размеров;
  - ограничения на редактирование и удаление по статусам.

- [order_helpers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/order_helpers.py)
  Вспомогательная логика заказов из карточек:
  - проверка доступа к карточке;
  - выбор approved-данных;
  - перенос данных карточки в строку заказа;
  - копирование черновиков заказов.

- [pc_cart.js](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/static/product_cards/users/pc_cart.js)
  Фронтовая корзина заказов из карточек:
  - хранение корзины в `localStorage`;
  - синхронизация модалки карточки с корзиной;
  - сборка payload для `make_pc_basket_order`;
  - применение настроек компании и типа маркировки.

- [utils.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/utils.py)
  Локальные утилиты модуля. Сейчас здесь в основном проверка блока РД и парсинг дат.

- [crm/main.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/crm/main.py)
  CRM blueprint `crm_product_cards` с маршрутами CRM-части.

- [crm/handlers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/crm/handlers.py)
  Обработка CRM-сценариев:
  - доска/списки карточек;
  - взятие в работу;
  - переводы по статусам;
  - approve / reject;
  - merge карточек и перенос размеров;
  - служебные выгрузки и работа с компаниями обработки.

- [crm/helpers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/crm/helpers.py)
  Выборки CRM, агрегации, подготовка данных для колонок и вспомогательные представления карточек.

- [crm/transitions.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/crm/transitions.py)
  Правила переходов статусов CRM.

- [chat/main.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/chat/main.py)
  Blueprint чата по карточкам.

- [chat/handlers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/chat/handlers.py)
  HTTP-обработчики чата: получить сообщения, отправить, отметить прочитанным.

- [chat/helpers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/chat/helpers.py)
  Права доступа к чату, фильтр видимости сообщений, unread counters.

## Как идет пользовательский поток

1. Пользователь открывает `/cards`, маршрут идет через [users.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/users.py) в `h_cards()` из [handlers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/handlers.py).
2. Таблица карточек грузится отдельно через `h_cards_table()`.
3. Создание и редактирование карточки проходят через `validate_card_form(...)`, `save_*_card(...)`, `update_card_allowed_fields(...)` и соседние функции из [support.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/support.py).
4. Если пользователь собирает заказ из карточек, сначала работает фронтовая корзина в [pc_cart.js](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/static/product_cards/users/pc_cart.js), а затем серверная сборка заказа в [handlers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/handlers.py) и [order_helpers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/order_helpers.py), где approved-данные карточки копируются в строки заказа.

## Ключевые бизнес-правила

- Категории и category-модели описаны в `CATEGORIES_COMMON`.
- Для `parfum` сравнение товара завязано на `trademark`.
- Для вещевых категорий (`clothes`, `shoes`, `linen`, `socks`) логика уникальности строится вокруг `article + color`, а для одежды дополнительно важна `subcategory`.
- В корзине и в модалке добавления позиции вещевые товары нельзя склеивать только по `article`: там безопасная идентичность идет от `card_id`, а размеры объединяются только внутри одной карточки.
- Размеры живут не в `ProductCard`, а в дочерних таблицах `*QuantitySize`.
- Доступные действия пользователя и CRM зависят от `status` и `data_status`.

## Редактирование карточек на модерации

Редактирование существующей карточки идет через `h_edit_product_card(...)` и `h_update_product_card(...)`.

Для пользователя редактирование доступно только в статусе:

- `clarification` — "На уточнении".

Для CRM/оператора редактирование доступно в статусах:

- `sent_no_rd` — "Отправлена без РД";
- `clarification` — "На уточнении".

Пользователь может редактировать только свои карточки. Оператор CRM может редактировать карточки по CRM-ссылке с учетом закрепления и статуса.

Для вещевых категорий (`clothes`, `shoes`, `linen`, `socks`) разрешено менять:

- `article`;
- `trademark`;
- остальные незамороженные товарные поля из `CARD_FIELDS`;
- блок РД.

При этом нельзя менять:

- `color`;
- размеры, типы размеров, единицы размеров и количества.

Если после смены `article` карточка попадает в уже существующий товар с тем же `article + color` (и `subcategory` для одежды), все товарные поля должны совпадать с существующей карточкой. Если, например, у такого товара отличается `trademark`, сохранение блокируется. Это нужно, чтобы CRM approve/merge не склеил размеры разных товаров в одну approved-карточку.

Для `parfum` разрешено менять `trademark`, но это ключ товара. Поэтому новый товарный знак проверяется на уникальность среди неотклоненных parfum-карточек этого же пользователя.

Изменение `article` для вещевых категорий и `trademark` для parfum пишется в `card_log`.

## Где завязана уникальность товара

Если меняется правило "что считать тем же товаром", надо проверять сразу несколько мест:

- [support.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/support.py)
  `check_same_fields_if_exists(...)`, `collect_existing_size_keys(...)`, `filter_new_sizes(...)`, `assert_frozen_fields_unchanged(...)`.

- [crm/handlers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/crm/handlers.py)
  approve / merge approved-карточек и перенос недостающих размеров.

- [order_helpers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/views/main/product_cards/order_helpers.py)
  сборка заказа из approved-единиц карточки.

- [pc_cart.js](/home/chik/python/youdo/elvin/elvin_orders/Markineris2.0.r/app/static/product_cards/users/pc_cart.js)
  фронтовая идентичность товара в корзине и в модалке добавления позиции.

Точечная правка только в одном месте почти наверняка даст скрытый рассинхрон.

## Статусы и чат

- Пользователь писать в чат может только в статусах из `USER_CHAT_WRITE_STATUSES`, сейчас это в первую очередь `clarification`.
- Менеджер видит чат только по карточкам, закрепленным за ним.
- Для обычного пользователя скрываются internal-сообщения.
- Unread counters используются и в пользовательской таблице, и в CRM.

## Что полезно помнить перед изменениями

- `handlers.py` старается быть слоем orchestration, а не местом для низкоуровневой валидации.
- Основные правила карточки лучше искать в `support.py`, а не в роутинге.
- Все сценарии "карточка -> approved данные -> заказ" проходят через `order_helpers.py`.
- Изменения по статусам часто затрагивают сразу пользовательскую часть, CRM и чат.
