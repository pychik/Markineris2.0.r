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

## Поля даты РД

- Даты РД лежат не в `ProductCard`, а в category-моделях через `CommonMixin`: `rd_date` = "От", `rd_date_to` = "До".
- Поля формы находятся в [rd.html](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/templates/product_cards/new/categories/helpers/rd.html): `id="rd_date"` и `id="rd_date_to"`.
- `rd.html` используется общими формами создания и редактирования карточки, поэтому изменения в нем затрагивают и пользовательскую часть, и CRM-редактирование.
- Для операторов CRM разрешен ручной ввод дат. Видимые поля `rd_date` / `rd_date_to` должны оставаться обычными текстовыми input без привязанного datepicker, иначе клик по полю открывает календарь и ломает ручной ввод.
- Datepicker в карточках РД привязан к скрытым proxy-input без `name`: `rd_date_picker` и `rd_date_to_picker`. Они нужны только для открытия календаря по иконке и не отправляются на backend.
- Календарь открывается только по SVG-иконке рядом с пустым полем. Если дата уже указана или оператор начал ввод, иконка скрывается; после очистки даты через `×` иконка снова появляется.
- Ручной ввод нормализуется во фронтовый формат `dd.mm.yyyy`; примеры: `12042026` -> `12.04.2026`, `120426` -> `12.04.2026`, `12-04-2026` -> `12.04.2026`.
- Нормализация перед отправкой вызывается из [common.js](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/static/product_cards/users/common.js) через `window.pcNormalizeRdDates()`.
- Проверки дат должны сохраняться и при ручном вводе, и при выборе через календарь: `rd_date` не раньше `01.01.2022`, `rd_date` не позже сегодня, `rd_date_to` не раньше сегодня + 1 месяц, `rd_date <= rd_date_to`. Для календаря ограничения пересчитываются перед открытием proxy-datepicker.
- Backend все еще принимает даты через [utils.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/utils.py) в формате `%d.%m.%Y`; если меняется фронтовый ввод, итоговое значение перед submit должно оставаться `dd.mm.yyyy`.
- После правки [common.js](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/static/product_cards/users/common.js) надо поднять cache-busting версию подключения в [main_card.html](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/templates/product_cards/new/main_card.html).

## Пользовательская отправка на модерацию

- Массовая отправка выбранных карточек со статусом `created` идет через `POST /cards/send_moderate`, route `send_cards_moderate()` в [users.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/users.py), handler `h_send_cards_moderate()` в [handlers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/handlers.py).
- Перед выставлением статусов `sent` / `sent_no_rd` выбранные свежие вещевые карточки объединяются через `merge_selected_created_wear_cards(...)` из [support.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/support.py).
- Объединение работает только для категорий с размерами: `clothes`, `shoes`, `linen`, `socks`. `parfum` не трогается.
- Ключ объединения для `clothes`: `category + article + color + subcategory`.
- Ключ объединения для `shoes`, `linen`, `socks`: `category + article + color`.
- В каждой группе базовой остается самая ранняя карточка по `created_at`, затем `id`.
- В базовую карточку копируются только недостающие размеры из дублей. Уже существующие размеры пропускаются.
- После переноса размеров карточки-дубли удаляются через ORM `db.session.delete(...)`.
- Если у базовой карточки нет РД, а у дубля есть РД, блок РД копируется в базовую карточку перед отправкой.
- Ответ ручки возвращает статистику `merged_cards`, `moved_sizes`, `skipped_sizes`, `deleted_card_ids`; фронт показывает `message` из ответа.
- Фронтовая логика отправки находится в [pc_send_created.js](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/static/product_cards/users/pc_send_created.js).

## Массовый перенос в CRM

- Универсальная ручка массового переноса карточек: `POST /crm/cards/bulk_move`, route `pc_bulk_move_cards()` в [crm/main.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/crm/main.py), handler `h_pc_bulk_move_cards()` в [crm/handlers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/crm/handlers.py).
- Ручка принимает `card_ids[]`, `target`, а также текущие фильтры `category` и `subcategory`, чтобы после переноса вернуть актуальный HTML затронутых колонок.
- Сейчас массово разрешен только выборочный перенос `clarification -> in_moderation`. Разрешенные bulk-переходы задаются whitelist-ом внутри `h_pc_bulk_move_cards()`.
- Обычный `manager` может массово переносить только карточки, закрепленные за ним по `manager_id`. `superuser` и `supermanager` могут переносить любые карточки.
- Если хотя бы одна выбранная карточка не найдена, не проходит whitelist, не проходит `validate_transition(...)` или проверку прав, вся операция отклоняется без частичного переноса.
- UI массового выбора сейчас добавлен только в колонку "На уточнении": кнопка `✓✓` включает чекбоксы на карточках, затем `✓` переносит выбранные на модерацию, `×` отменяет режим выбора. Фронтовая логика находится в [cards.js](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/static/product_cards/crm/js/cards.js): `pcBulkMoveSelected(...)`, `pcApplyBulkMoveResponse(...)`.

## Назначение оператора в CRM

- Назначение оператора из карточки доступно только ролям `superuser` и `supermanager`.
- В карточке оператор рендерится через [card_manager_info.html](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/templates/product_cards/crm/helpers/card_manager_info.html). Для разрешенных ролей и разрешенных статусов имя оператора становится кнопкой.
- Нельзя назначать оператора в колонках `sent`, `sent_no_rd`, `approved`, `rejected`. Это проверяется и в шаблоне, и на backend.
- Список доступных операторов грузится AJAX-ом через `GET /crm/cards/managers`, route `pc_managers_list()` в [crm/main.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/crm/main.py), handler `h_pc_managers_list()` в [crm/handlers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/crm/handlers.py).
- Назначение выполняется AJAX-ом через `POST /crm/card/<pc_id>/assign_manager`, route `pc_assign_manager()` в [crm/main.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/crm/main.py), handler `h_pc_assign_manager()` в [crm/handlers.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/views/main/product_cards/crm/handlers.py).
- Ручка назначения меняет только `ProductCard.manager_id`, статус карточки не меняется.
- При успешном назначении пишется строка в `ProductCard.card_log` через `h_append_card_log(...)`.
- Фронтовая логика находится в [cards.js](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/static/product_cards/crm/js/cards.js): `pcOpenAssignManagerModal(...)`, `pcAssignManager(...)`, `pcUpdateManagerOnCard(...)`.
- URL для AJAX передаются через `#pc-config` в [crm_main.html](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/templates/product_cards/crm/crm_main.html): `data-managers-url`, `data-assign-manager-url-template`.

## Что полезно помнить перед изменениями

- `handlers.py` старается быть слоем orchestration, а не местом для низкоуровневой валидации.
- Основные правила карточки лучше искать в `support.py`, а не в роутинге.
- Все сценарии "карточка -> approved данные -> заказ" проходят через `order_helpers.py`.
- Изменения по статусам часто затрагивают сразу пользовательскую часть, CRM и чат.
