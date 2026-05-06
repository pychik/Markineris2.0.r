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
- пока не реализовано: полная замена существующих источников TNVED в UI и бизнес-логике Markineris

## Что уже переведено на Redis

Для цветов и стран в основном приложении `app/` прямое чтение из `settings.ALL_COLORS` и `settings.COUNTRIES_LIST` в рабочих сценариях заменено на слой `runtime_catalogs.py`.

Сейчас через Redis-кэш Tezaurus идут:

- обычные пользовательские формы категорий;
- формы одежды;
- карточки товаров;
- серверная валидация цветов;
- серверная проверка стран с учетом РД;
- Excel upload-валидация для основных upload-потоков.

## Что еще не переведено

- TNVED-справочники все еще читаются из старых источников и локальных структур;
- fallback на старые `settings` оставлен в `runtime_catalogs.py`, если Redis пустой или недоступен.

## Структура модуля

- `api_client.py` - клиент API Tezaurus для получения ревизий и полных выгрузок
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

## Ключи Redis

Префикс по умолчанию: `tezaurus:v1` (настраивается через `TEZAURUS_REDIS_PREFIX`).

Обязательные базовые ключи:

- `tezaurus:v1:version` - состояние ревизий (`colors`, `countries`, `tnved`, `synced_at`)
- `tezaurus:v1:colors` - JSON-снимок цветов
- `tezaurus:v1:countries` - JSON-снимок стран
- `tezaurus:v1:tnved` - JSON-снимки TNVED по категориям

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
countries_our_socks = service.get_countries(category="socks", our_rd=True)

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
socks_rd_countries = get_rd_countries("socks")

is_valid_color = is_allowed_color("ЧЕРНЫЙ")
is_valid_country = is_allowed_country("РОССИЯ")
```

`runtime_catalogs.py` сейчас используется как единая точка доступа для цветов и стран в `app/`, чтобы:

- не размазывать прямую работу с Redis по бизнес-логике;
- держать единый fallback на старые `settings`;
- централизованно нормализовать значения к верхнему регистру.

Алиасы фильтров нормализуются для совместимости с реальными значениями payload:

- countries category: `одежда -> clothes`, `носки -> clothes`, `обувь -> shoes`, `белье -> linen`, `парфюм -> parfum`
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
