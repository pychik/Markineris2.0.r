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

### `product_card_processing_company_rebalance.py`

Файл: [product_card_processing_company_rebalance.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/utilities/scripts_manual/product_card_processing_company_rebalance.py:1)

Что делает:
- приводит уже существующие карточки товаров к правилу: один клиент + категория Tezaurus + `rf` / `import` = одна закрепленная фирма
- если в группе есть несколько фирм, канонической считается самая ранняя закрепленная фирма
- фирмы `Аврора` (`4400023120`) и `Перемены` (`4400027438`) исключены из выбора канонической фирмы; если в группе есть только они, группа пропускается
- меняет только поля `processing_company_*` и добавляет запись в `card_log`
- если меняется фирма у карточки в статусе `approved`, карточка переводится в `in_moderation`, `approved_at` очищается, а `is_approved` по данным карточки сбрасывается
- остальные статусы карточек не меняет
- по умолчанию обрабатывает статусы `sent`, `sent_no_rd`, `in_progress`, `in_moderation`, `clarification`, `approved`, `partially_approved`; `created` и `rejected` не трогает
- карточки без фирмы во всей группе пропускает и показывает в результате

Безопасный просмотр перед запуском:

```python
from utilities.scripts_manual.product_card_processing_company_rebalance import (
    preview_rebalance_product_card_processing_companies,
    rebalance_product_card_processing_companies,
)

preview_rebalance_product_card_processing_companies()
```

Боевой запуск:

```python
rebalance_product_card_processing_companies()
```

Проверочный запуск без commit:

```python
rebalance_product_card_processing_companies(commit=False)
```

Что возвращает preview:
- `change_count` - сколько карточек будет изменено
- `changes` - подробный список изменений по карточкам
- `approved_reset` / `new_status` внутри `changes` - какие approved-карточки будут возвращены на модерацию
- `groups_without_company` - группы, где не найдено ни одной закрепленной фирмы

Что возвращает боевой запуск:
- `updated_count` - сколько карточек изменено
- `updated_ids` - id изменённых карточек
- `approved_reset_count` / `approved_reset_ids` - сколько approved-карточек возвращено на модерацию
- `groups_without_company` - группы, где не найдено ни одной закрепленной фирмы
- `committed` / `rolled_back` - был ли commit или проверочный rollback

### `product_card_processing_company_excluded_tezaurus.py`

Файл: [product_card_processing_company_excluded_tezaurus.py](/home/chik/python/youdo/elvin/elvin_orders/Markineris-2.0/app/utilities/scripts_manual/product_card_processing_company_excluded_tezaurus.py:1)

Что делает:
- отдельно обрабатывает группы, которые основной rebalance-скрипт пропускает, потому что все закрепленные фирмы в группе - `Аврора` (`4400023120`) / `Перемены` (`4400027438`)
- на каждую группу `клиент + категория Tezaurus + rf/import` делает отдельный запрос в Tezaurus
- назначает полученную фирму всем карточкам этой группы
- если Tezaurus снова вернул `Аврора` / `Перемены` или не вернул фирму, скрипт откатывает изменения и возвращает `ok=False`
- если меняется фирма у карточки в статусе `approved`, карточка переводится в `in_moderation`, `approved_at` очищается, а `is_approved` по данным карточки сбрасывается

Безопасный просмотр перед запуском:

```python
from utilities.scripts_manual.product_card_processing_company_excluded_tezaurus import (
    preview_assign_excluded_product_card_companies_from_tezaurus,
    assign_excluded_product_card_companies_from_tezaurus,
)

preview_assign_excluded_product_card_companies_from_tezaurus()
```

Боевой запуск:

```python
assign_excluded_product_card_companies_from_tezaurus()
```

Важно: `commit=False` в этом скрипте специально не делает запросы в Tezaurus и возвращает preview-данные с причиной `commit_false_does_not_call_tezaurus`. Боевой запрос в Tezaurus выполняется только при обычном запуске с `commit=True`.

## Важно

- Для карточек товаров состояние "отменены" реализуется через статус `rejected`.
- Если добавляете новый скрипт в эту папку, дописывайте его описание в этот README.
