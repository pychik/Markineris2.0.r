# Модуль Redis-кэша Tezaurus

## Назначение

Модуль формирует и отдает локальный Redis-кэш словарей Tezaurus.

Основные цели:

- опрашивать ревизии Tezaurus каждые 5 минут
- перезагружать только изменившиеся словари
- сохранять последний валидный снимок при ошибках синхронизации (fallback)
- предоставлять read-only доступ к данным из Redis во время работы приложения (без прямых вызовов внешнего API)

## Текущий охват

- реализовано: синхронизация, сохранение в Redis и read API из кэша
- реализовано: периодическая задача планировщика для обновления кэша
- реализовано: переключение цветов и стран Markineris на чтение из Redis-кэша Tezaurus
- реализовано: прямой запрос подбора обрабатывающей фирмы через Tezaurus для админского тестирования
- реализовано: список обрабатывающих фирм для CRM-фильтра через Redis-кэш Tezaurus
- пока не реализовано: полная замена существующих источников TNVED в UI и бизнес-логике Markineris

## Что уже переведено на Redis

Для цветов и стран в основном приложении `app/` прямое чтение из `settings.ALL_COLORS` и `settings.COUNTRIES_LIST` в рабочих сценариях заменено на слой `runtime_catalogs.py`.

Сейчас через Redis-кэш Tezaurus идут:

- обычные пользовательские формы категорий;
- формы одежды;
- карточки товаров;
- серверная валидация цветов;
- серверная проверка стран с учетом РД;
- Excel upload-валидация для основных upload-потоков;
- legacy `bp` upload-валидаторы.

## Что еще не переведено

- TNVED-справочники все еще читаются из старых источников и локальных структур;
- fallback на старые `settings` оставлен в `runtime_catalogs.py`, если Redis пустой или недоступен.

## Структура модуля

- `api_client.py` - клиент API Tezaurus для получения ревизий и полных выгрузок
- `processing_companies.py` - клиент и нормализация запроса подбора обрабатывающей фирмы
- `redis_repository.py` - хранение JSON в Redis и управление ключами
- `sync_service.py` - оркестрация синхронизации по ревизиям с fallback-поведением
- `cache_service.py` - read API для цветов, стран и TNVED из Redis
- `runtime_catalogs.py` - runtime-адаптер для Markineris с fallback на старые `settings`
- `key_builder.py` - нормализация ключей и алиасы для категорий/подкатегорий
- `exceptions.py` - исключения модуля

## Поток синхронизации

1. Планировщик запускает `TezaurusSyncService.sync()`.
2. Сервис запрашивает `GET /api/v1/meta/dictionaries-state`.
3. Сервис сравнивает удаленные ревизии с `tezaurus:v1:version` в Redis.
4. Если ревизия изменилась (или отсутствует ключ кэша), сервис загружает полную выгрузку и обновляет Redis.
5. Если загрузка или сохранение завершились ошибкой, старый кэш остается без изменений.

Текущие словари:

- colors: `GET /api/v1/export/colors`
- countries: `GET /api/v1/export/countries`
- tnved (clothes): `GET /api/v1/export/tnved/clothes`
- processing_companies: `GET /api/v1/export/processing-companies`

Для `processing_companies` Tezaurus должен отдавать ревизию в `GET /api/v1/meta/dictionaries-state`.
Если Redis-снимок еще не создан или недоступен, `runtime_catalogs.py` использует локальный default-список компаний,
синхронизированный с `DEFAULT_PROCESSING_COMPANY_RULES` Tezaurus.

## Запрос обрабатывающей фирмы

Подбор обрабатывающей фирмы не кэшируется в Redis. Tezaurus выполняет выбор по текущей очереди и правилам на каждый запрос, поэтому Markineris отправляет прямой `POST` в API.

Справочник всех обрабатывающих фирм кэшируется отдельно. Он используется только для CRM-фильтра в колонке
"На модерации" и не влияет на алгоритм назначения фирмы карточке.

Endpoint Tezaurus:

`POST /api/v1/processing-companies/select`

Batch endpoint Tezaurus:

`POST /api/v1/processing-companies/select-batch`

Payload:

```json
{"category":"clothes","origin":"rf"}
```

Batch payload:

```json
{
  "items": [
    {"client_id": "card-7121", "category": "clothes", "origin": "import"},
    {"client_id": "card-10369", "category": "shoes", "origin": "rf"}
  ]
}
```

`client_id` возвращается в ответе как есть и используется Markineris для сопоставления ответа с `ProductCard.id`. В одном batch-запросе Tezaurus принимает до `200` карточек; если карточек больше, Markineris отправляет несколько batch-запросов по `200`.

Категории Tezaurus:

- `clothes`
- `shoes`
- `parfum`
- `cosmetics`
- `toys`
- `home_goods`

Происхождение:

- `rf` - Россия
- `import` - остальные страны

В Markineris запрос оформлен через `tezaurus.processing_companies.ProcessingCompaniesClient`.

Рабочий пользовательский поток `/cards/send_moderate` использует `select-batch` после объединения дублей вещевых карточек. Одиночный `select` остается для прямой проверки и страницы `/admin_control/module-testing`.

Нормализация категории перед отправкой:

- `linen`, `белье` -> `clothes`
- `socks`, `носки`, `носки и прочее` -> `clothes`
- остальные поддерживаемые категории отправляются своим slug из списка Tezaurus

Нормализация происхождения перед отправкой:

- `РОССИЯ`, `РФ`, `RU`, `RUS`, `643` -> `rf`
- любая другая непустая страна -> `import`

Пример прямой проверки:

```bash
curl -sS -X POST \
  -H "Authorization: Bearer ${TEZAURUS_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"category":"clothes","origin":"rf"}' \
  "${TEZAURUS_BASE_URL}/api/v1/processing-companies/select"
```

Пример batch-проверки:

```bash
curl -sS -X POST \
  -H "Authorization: Bearer ${TEZAURUS_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"items":[{"client_id":"card-7121","category":"clothes","origin":"import"},{"client_id":"card-10369","category":"shoes","origin":"rf"}]}' \
  "${TEZAURUS_BASE_URL}/api/v1/processing-companies/select-batch"
```

Batch endpoint возвращает HTTP `200`, если JSON и массив `items` корректны. Ошибки отдельных карточек приходят внутри элемента `items` с `ok=false`, `matched=false` и `status_code`; Markineris собирает все такие ошибки в один ответ пользователю, считает ситуацию ошибкой всей отправки и откатывает транзакцию.

Админская проверка доступна только superuser:

- страница: `/admin_control/module-testing`
- backend POST: `/admin_control/module-testing/processing-companies/select`

Форма админской проверки принимает категорию и страну, нормализует их на стороне Markineris, отправляет запрос в Tezaurus с существующим Bearer-токеном `TEZAURUS_API_TOKEN` и выводит ответ в блоке результата тестирования.

## Ключи Redis

Префикс по умолчанию: `tezaurus:v1` (настраивается через `TEZAURUS_REDIS_PREFIX`).

Обязательные базовые ключи:

- `tezaurus:v1:version` - состояние ревизий (`colors`, `countries`, `tnved`, `synced_at`)
- `tezaurus:v1:colors` - JSON-снимок цветов
- `tezaurus:v1:countries` - JSON-снимок стран
- `tezaurus:v1:tnved` - JSON-снимки TNVED по категориям
- `tezaurus:v1:processing_companies` - JSON-снимок обрабатывающих фирм
- `tezaurus:v1:processing_companies:list` - нормализованный список фирм для runtime-чтения

Ключи фильтров countries (category + our_rd):

- `tezaurus:v1:countries:our_rd:0:category:all` -> `items.user_rd`
- `tezaurus:v1:countries:our_rd:1:category:all` -> полный `items.our_rd`
- `tezaurus:v1:countries:our_rd:1:category:<category>` -> список категории (пример: `clothes`, `shoes`)

Ключи фильтров TNVED (category + subcategory + type + gender):

- `tezaurus:v1:tnved:category:<category>`
- `tezaurus:v1:tnved:category:<category>:subcategory:<subcategory>`
- `tezaurus:v1:tnved:category:<category>:subcategory:<subcategory>:type:<type>`
- `tezaurus:v1:tnved:category:<category>:subcategory:<subcategory>:type:<type>:gender:<gender>`

Примеры для clothes:

- category: `clothes`
- subcategories: `common`, `underwear`

## Использование во время выполнения

## Как теперь забирается информация

Во время работы `Markineris` больше не должен напрямую ходить в API `Tezaurus` из пользовательских сценариев.

Текущая цепочка такая:

1. Фоновая задача `sync_tezaurus_cache` периодически вызывает `TezaurusSyncService.sync()`.
2. `sync_service.py` сравнивает ревизии словарей в API `Tezaurus` и в Redis.
3. Если ревизия изменилась, `redis_repository.py` пересохраняет свежие JSON-снимки и фильтрованные ключи.
4. Рабочий код основного приложения читает данные только из Redis через `TezaurusCacheService`.
5. Бизнес-логика `app/` использует не `cache_service.py` напрямую, а `runtime_catalogs.py`.
6. Если Redis пустой, недоступен или в нем нет нужного фильтра, `runtime_catalogs.py` делает fallback на старые локальные `settings` и Python-структуры.

То есть фактический runtime-путь сейчас такой:

`Tezaurus API -> sync_service.py -> Redis -> cache_service.py -> runtime_catalogs.py -> формы / upload / validators / views`

Для одежды это работает так:

- список типов для `common` и `underwear` читается через `get_clothes_tnved_types()`;
- список полов для выбранного типа читается через `get_clothes_tnved_genders()`;
- список кодов ТН ВЭД для пары `тип + пол` читается через `get_clothes_tnved_codes()` или `get_clothes_tnved_pairs()`;
- полный список кодов по подкатегории читается через `get_clothes_all_tnved()`.

Эти вызовы уже используются в рабочих местах:

- `app/utilities/upload_order/upload_clothes.py`
- `app/utilities/validators.py`
- `app/utilities/check_tnved.py`
- `app/views/main/categories/clothes/subcategories.py`
- `app/views/main/categories/clothes/support.py`

Важно:

- для `common` и `underwear` приоритетным источником считается Redis-кэш `Tezaurus`;
- для `swimming_accessories`, `hats`, `gloves`, `shawls` пока продолжают использоваться локальные Python-словарики;
- fallback на старые структуры оставлен специально, чтобы приложение не падало при пустом Redis или неполной синхронизации.

Низкоуровневый доступ к кэшу:

```python
from tezaurus.cache_service import TezaurusCacheService

service = TezaurusCacheService()

colors = service.get_all_colors()

# список user_rd
countries_user_rd = service.get_countries(our_rd=False)

# все категории our_rd
countries_our_rd = service.get_countries(our_rd=True)

# только одна категория our_rd
countries_our_clothes = service.get_countries(category="clothes", our_rd=True)

# полный payload категории tnved
tnved_clothes = service.get_tnved(category="clothes")

# одна подкатегория
tnved_common = service.get_tnved(category="clothes", subcategory="common")

# один тип
tnved_type = service.get_tnved(
    category="clothes",
    subcategory="common",
    type_name="ФУТБОЛКИ",
)

# финальный список кодов с фильтрацией
tnved_codes = service.get_tnved(
    category="clothes",
    subcategory="common",
    type_name="ФУТБОЛКИ",
    gender="Женский",
)
```

Рекомендуемый runtime-слой для основного приложения:

```python
from tezaurus.runtime_catalogs import (
    get_all_countries,
    get_colors,
    get_rd_countries,
    is_allowed_color,
    is_allowed_country,
)

colors = get_colors()
countries = get_all_countries()
clothes_rd_countries = get_rd_countries("clothes")

is_valid_color = is_allowed_color("ЧЕРНЫЙ")
is_valid_country = is_allowed_country("РОССИЯ")
```

`runtime_catalogs.py` сейчас используется как единая точка доступа для цветов и стран в `app/`, чтобы:

- не размазывать прямую работу с Redis по бизнес-логике;
- держать единый fallback на старые `settings`;
- централизованно нормализовать значения к верхнему регистру.

Алиасы фильтров нормализуются для совместимости с реальными значениями payload:

- countries category: `одежда -> clothes`, `обувь -> shoes`, `белье -> linen`, `парфюм -> parfum`
- tnved gender: `Жен.`, `Женский` -> `female`; `Муж.`, `Мужской` -> `male`; `Без указания пола`, `унисекс` -> `no_gender`

## Интеграция с планировщиком

Периодическая синхронизация зарегистрирована в RQ Scheduler через задачу `sync_tezaurus_cache`.

Cron по умолчанию: `*/5 * * * *`.

Настраивается через `TEZAURUS_SYNC_CRON`.

## Конфигурация

Добавьте переменные окружения:

- `TEZAURUS_BASE_URL`
- `TEZAURUS_API_TOKEN`
- `TEZAURUS_TIMEOUT` (по умолчанию `30`)
- `TEZAURUS_VERIFY_SSL` (по умолчанию `1`)
- `TEZAURUS_CA_CERT` (опциональный путь к CA bundle)
- `TEZAURUS_REDIS_PREFIX` (по умолчанию `tezaurus:v1`)
- `TEZAURUS_SYNC_CRON` (по умолчанию `*/5 * * * *`)
- `TEZAURUS_SYNC_ENABLED` (по умолчанию `1`)
