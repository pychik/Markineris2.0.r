# Scripts Manual

Ручные сервисные скрипты для запуска из `flask shell`.

Папка: [app/utilities/scripts_manual](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/utilities/scripts_manual)

## Общие правила

- Скрипты из этой папки не вызываются автоматически приложением.
- Они рассчитаны на ручной импорт и запуск из `flask shell`.
- Перед массовым изменением данных сначала делайте просмотр результата или запускайте с `commit=False`, если такая опция есть.

Пример входа:

```python
flask shell
```

## Скрипты

### `product_cards_clarification.py`

Файл: [product_cards_clarification.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/utilities/scripts_manual/product_cards_clarification.py:1)

Что делает:
- переводит указанные карточки товаров в статус `clarification`
- сбрасывает признаки одобрения по данным карточки
- очищает `approved_at`, `rejected_at`, `reject_reason`
- пишет запись в `card_log`

Когда использовать:
- если нужно вручную вернуть конкретные карточки на уточнение по списку `id`

Запуск:

```python
from utilities.scripts_manual.product_cards_clarification import move_cards_to_clarification

move_cards_to_clarification([9505, 9502, 9501])
```

Что возвращает:
- `updated` - какие карточки обновлены
- `missing` - какие `id` не найдены

### `product_cards_reject_by_country.py`

Файл: [product_cards_reject_by_country.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/utilities/scripts_manual/product_cards_reject_by_country.py:1)

Что делает:
- находит все карточки товаров, у которых в category-модели указана страна `РОССИЯ`
- переводит такие карточки в статус `rejected`
- записывает причину отмены в `reject_reason`:
  `ОТМЕНА МОДЕРАЦИИ СОГЛАСНО НОВЫМ ПРАВИЛАМ ЧЗ`
- добавляет запись в `card_log`:
  `отмена сервером; причина: ...`
- сбрасывает `approved_at` и `is_approved`, чтобы в отклонённой карточке не оставались approved-метки

Когда использовать:
- для массовой отмены модерации карточек по правилу страны

Безопасный просмотр перед запуском:

```python
from utilities.scripts_manual.product_cards_reject_by_country import (
    preview_reject_product_cards_by_country,
    reject_product_cards_by_country,
)

preview_reject_product_cards_by_country()
preview_reject_product_cards_by_country()["to_update_ids"]
```

Боевой запуск:

```python
reject_product_cards_by_country()
```

Запуск с другой страной:

```python
reject_product_cards_by_country(country="РОССИЯ")
```

Что возвращает preview:
- `total_found` - всего найдено карточек
- `to_update_count` - сколько будет изменено
- `already_rejected_count` - сколько уже в нужном состоянии
- `to_update_ids` - id карточек к изменению

Что возвращает боевой запуск:
- `updated_count` - сколько карточек изменено
- `skipped_count` - сколько пропущено
- `updated_ids` - id изменённых карточек
- `skipped_ids` - id пропущенных карточек

## Важно

- В модуле карточек нет отдельного статуса `cancelled`.
- Для карточек товаров состояние "отменены" реализуется через статус `rejected`.
- Если добавляете новый скрипт в эту папку, дописывайте его описание в этот README.
