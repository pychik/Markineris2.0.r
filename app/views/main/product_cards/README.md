# Product Cards

Краткая карта модуля `app/views/main/product_cards`, чтобы было понятно, где лежат маршруты, бизнес-логика и связанные сценарии.

## Структура

- [users.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/users.py)
  Пользовательский blueprint `user_product_cards`. Здесь только роуты и привязка URL к handler-функциям.

- [handlers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/handlers.py)
  Главная точка входа пользовательской части. Тут собраны:
  - список карточек пользователя и AJAX-таблица;
  - создание, просмотр, редактирование, удаление карточек;
  - отправка карточек на модерацию;
  - сценарии черновиков заказов, собранных из карточек.

- [support.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/support.py)
  Основная бизнес-логика карточек:
  - конфиг категорий `CATEGORIES_COMMON`;
  - валидация форм;
  - нормализация полей;
  - сохранение category-моделей;
  - правила уникальности товара;
  - дедупликация размеров;
  - ограничения на редактирование и удаление по статусам.

- [order_helpers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/order_helpers.py)
  Вспомогательная логика заказов из карточек:
  - проверка доступа к карточке;
  - выбор approved-данных;
  - перенос данных карточки в строку заказа;
  - копирование черновиков заказов.

- [pc_cart.js](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/static/product_cards/users/pc_cart.js)
  Фронтовая корзина заказов из карточек:
  - хранение корзины в `localStorage`;
  - синхронизация модалки карточки с корзиной;
  - сборка payload для `make_pc_basket_order`;
  - применение настроек компании и типа маркировки.

- [utils.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/utils.py)
  Локальные утилиты модуля. Сейчас здесь в основном проверка блока РД и парсинг дат.

- [crm/main.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/crm/main.py)
  CRM blueprint `crm_product_cards` с маршрутами CRM-части.

- [crm/handlers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/crm/handlers.py)
  Обработка CRM-сценариев:
  - доска/списки карточек;
  - взятие в работу;
  - переводы по статусам;
  - approve / reject;
  - merge карточек и перенос размеров;
  - служебные выгрузки и работа с компаниями обработки.

- [crm/helpers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/crm/helpers.py)
  Выборки CRM, агрегации, подготовка данных для колонок и вспомогательные представления карточек.

- [crm/transitions.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/crm/transitions.py)
  Правила переходов статусов CRM.

- [chat/main.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/chat/main.py)
  Blueprint чата по карточкам.

- [chat/handlers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/chat/handlers.py)
  HTTP-обработчики чата: получить сообщения, отправить, отметить прочитанным.

- [chat/helpers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/chat/helpers.py)
  Права доступа к чату, фильтр видимости сообщений, unread counters.

## Как идет пользовательский поток

1. Пользователь открывает `/cards`, маршрут идет через [users.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/users.py) в `h_cards()` из [handlers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/handlers.py).
2. Таблица карточек грузится отдельно через `h_cards_table()`.
3. Создание и редактирование карточки проходят через `validate_card_form(...)`, `save_*_card(...)`, `update_card_allowed_fields(...)` и соседние функции из [support.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/support.py).
4. Если пользователь собирает заказ из карточек, сначала работает фронтовая корзина в [pc_cart.js](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/static/product_cards/users/pc_cart.js), а затем серверная сборка заказа в [handlers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/handlers.py) и [order_helpers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/order_helpers.py), где approved-данные карточки копируются в строки заказа.

## Ключевые бизнес-правила

- Категории и category-модели описаны в `CATEGORIES_COMMON`.
- Для `parfum` сравнение товара завязано на `trademark`.
- Для вещевых категорий (`clothes`, `shoes`, `linen`, `socks`) логика уникальности строится вокруг `article + color`, а для одежды дополнительно важна `subcategory`.
- В корзине и в модалке добавления позиции вещевые товары нельзя склеивать только по `article`: там безопасная идентичность идет от `card_id`, а размеры объединяются только внутри одной карточки.
- Размеры живут не в `ProductCard`, а в дочерних таблицах `*QuantitySize`.
- Доступные действия пользователя и CRM зависят от `status` и `data_status`.

## Где завязана уникальность товара

Если меняется правило "что считать тем же товаром", надо проверять сразу несколько мест:

- [support.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/support.py)
  `check_same_fields_if_exists(...)`, `collect_existing_size_keys(...)`, `filter_new_sizes(...)`, `assert_frozen_fields_unchanged(...)`.

- [crm/handlers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/crm/handlers.py)
  approve / merge approved-карточек и перенос недостающих размеров.

- [order_helpers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/order_helpers.py)
  сборка заказа из approved-единиц карточки.

- [pc_cart.js](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/static/product_cards/users/pc_cart.js)
  фронтовая идентичность товара в корзине и в модалке добавления позиции.

Точечная правка только в одном месте почти наверняка даст скрытый рассинхрон.

## Статусы и чат

- Пользователь писать в чат может только в статусах из `USER_CHAT_WRITE_STATUSES`, сейчас это в первую очередь `clarification`.
- Менеджер видит чат только по карточкам, закрепленным за ним.
- Для обычного пользователя скрываются internal-сообщения.
- Unread counters используются и в пользовательской таблице, и в CRM.

## Логи карточки

- Лог карточки хранится в `ProductCard.card_log`, новые строки добавляются через `h_append_card_log(...)`.
- Лог режется до последних `settings.ProducCards.MAX_LOG` символов.
- При редактировании разрешенных полей в статусах `sent_no_rd` и `clarification` пишется короткая запись с автором, статусом и списком измененных полей.
- CRM-редактирование идет через `crm_product_cards.crm_update_product_card` и вызывает `h_update_product_card(crm_=True)`.
- Пользовательское редактирование идет через `user_product_cards.update_product_card` и вызывает `h_update_product_card(crm_=False)`.
- Если карточку в статусе `clarification` редактирует собственник, автор пишется как `Клиент <login>`.
- Короткие метки статусов в логах: `НУ` = `clarification`, `ОБРД` = `sent_no_rd`.

Пример:

```text
13-04-2026 14:20:10 manager_login исправил (ОБРД): Страна, РД;
13-04-2026 14:25:31 Клиент client_login исправил (НУ): РД;
```

## Массовый перенос в CRM

- Универсальная ручка массового переноса карточек: `POST /crm/cards/bulk_move`, route `pc_bulk_move_cards()` в [crm/main.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/crm/main.py), handler `h_pc_bulk_move_cards()` в [crm/handlers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/crm/handlers.py).
- Ручка принимает `card_ids[]`, `target`, а также текущие фильтры `category` и `subcategory`, чтобы после переноса вернуть актуальный HTML затронутых колонок.
- Сейчас массово разрешен только выборочный перенос `clarification -> in_moderation`. Разрешенные bulk-переходы задаются whitelist-ом внутри `h_pc_bulk_move_cards()`.
- Обычный `manager` может массово переносить только карточки, закрепленные за ним по `manager_id`. `superuser` и `supermanager` могут переносить любые карточки.
- Если хотя бы одна выбранная карточка не найдена, не проходит whitelist, не проходит `validate_transition(...)` или проверку прав, вся операция отклоняется без частичного переноса.
- UI массового выбора сейчас добавлен только в колонку "На уточнении": кнопка `✓✓` включает чекбоксы на карточках, затем `✓` переносит выбранные на модерацию, `×` отменяет режим выбора. Фронтовая логика находится в [cards.js](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/static/product_cards/crm/js/cards.js): `pcBulkMoveSelected(...)`, `pcApplyBulkMoveResponse(...)`.


## Что полезно помнить перед изменениями

- `handlers.py` старается быть слоем orchestration, а не местом для низкоуровневой валидации.
- Основные правила карточки лучше искать в `support.py`, а не в роутинге.
- Все сценарии "карточка -> approved данные -> заказ" проходят через `order_helpers.py`.
- Изменения по статусам часто затрагивают сразу пользовательскую часть, CRM и чат.
