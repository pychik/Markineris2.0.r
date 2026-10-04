# Markineris2.0.r
Markineris2.0.r for special agents

## Информационные команды

- Команда help, для просмотра доступных команд и их краткое описание
```shell
make help
```

### CRM-флаг РФ-заказа
- В CRM карточках обычных заказов значок флага показывает, что все позиции заказа имеют страну `РОССИЯ`.
- Флаг считается в общем SQL-агрегаторе `app/utilities/sql_categories_aggregations.py` и протаскивается через `app/views/crm/helpers.py`; отдельной колонки и миграции в `orders` нет.

### CRM-отчет активности операторов
- Роут отчета: `/crm_uoc/avg_order_processing_time_report`.
- Отчет показывает по каждому оператору количество обработанных заказов, строк, марок и среднее время обработки в минутах и часах.
- Заказ попадает в отчет по факту заполненного `orders.m_finished`; это покрывает обычное завершение обработки и переход проблемного заказа в статус `Проблема решена`.
- Дневные колонки распределяют заказы по длительности `m_finished - m_started`: до 1 дня, до 2 дней, до 3 дней и более 3 дней.
- Максимальный диапазон формирования отчета - 4 месяца. На фронте запрос блокируется через `make_message`, если пользователь выбрал больший период.
- В интерфейсе отчета есть раскрываемая справка по иконке `i`; шаблон описания лежит в `app/templates/crm_mod_v1/reports/avg_order_processing_time/report_description.html`.
- Excel-выгрузка использует те же данные и порядок колонок, что и HTML-таблица.

### Белье: комплект постельного белья
- Вид товара `КОМПЛЕКТ ПОСТЕЛЬНОГО БЕЛЬЯ` заполняется как одна позиция заказа с дочерними строками состава комплекта.
- Количество марок для КПБ считается по количеству комплектов и хранится в `Linen.kpb_quantity`.
- Дочерние строки состава хранятся в `LinenSetItem` / `linen_set_items` и связаны с `Linen.set_items`.
- В карточках товаров КПБ доступен как один товар с дочерними строками состава; для модерации используется `Linen.is_approved`.
- При создании GTIN-заказа из карточки КПБ копируется состав комплекта, а введенное количество сохраняется в `Linen.kpb_quantity`.
- Через Excel upload КПБ временно запрещен: комплект нужно заполнять через форму в сервисе.
- Миграция для `linen.kpb_quantity`, `linen.is_approved` и `linen_set_items` генерируется локально и не коммитится:
```shell
cd app
flask db migrate -m "add linen set items"
flask db upgrade
```


### Быстрые заказы из карточек: компании обработки и УПД
- Временное отличие: категория `игрушки` отключена в карточках товаров и быстрых GTIN-заказах из карточек.
- Отключение заведено как временный feature flag в `app/views/main/product_cards/constants.py`; чтобы вернуть категорию, нужно убрать игрушки из `PC_DISABLED_CARD_CATEGORIES` и `PC_DISABLED_ORDER_CATEGORIES`.
- Обычная форма заказов категории `игрушки` не отключалась и должна работать в прежнем режиме.
- Архив Excel для быстрых заказов из карточек делится по компаниям обработки через `fast_order_companies`.
- При создании быстрого заказа компании сохраняются в `fast_order_companies`: одна строка на одну уникальную компанию в рамках заказа.
- В товарные позиции быстрого заказа сохраняется только ссылка `fast_order_company_id`.
- В CRM для быстрого заказа модалка УПД показывает отдельное поле УПД для каждой компании из `fast_order_companies`.
- Копирование быстрого заказа из истории переносит только позиции с одобренными данными и заполненной компанией обработки; остальные позиции пропускаются с предупреждением.
- Миграции для этих изменений генерируются локально и не коммитятся:

```shell
cd app
flask db migrate -m "add fast order companies"
flask db upgrade
```
- В сгенерированной миграции должны быть: создание `fast_order_companies`, добавление `fast_order_company_id` в товарные таблицы заказов и изменение `orders.processing_info` на `text`, если оно еще не применено в базе.

### Организация заказа: backend-валидация
- Тип организации должен входить в `settings.COMPANY_TYPES`: `ИП`, `ООО`, `АО`, `ПАО`, `НПАО`, `ГКФХ`, `Филиал`, `Рынок`, `Магазин`, `НАО`; проверка выполняется без учета регистра и сохраняет каноническое значение из списка.
- `company_idn` принимает только цифры: для `ИП`, `ГКФХ`, `Рынок`, `Магазин` ровно `12`, для остальных типов ровно `10`.
- `company_name` обязателен и не должен начинаться с пробела; при сохранении хвостовые пробелы нормализуются.
- Общая проверка лежит в `app/utilities/validators.py` (`validate_and_normalize_company_fields()`).
- Проверка применяется на backend в создании обычного заказа, создании парфюм-заказа, Excel upload, `send_table`, редактировании организации заказа, перед отправкой обычного заказа в обработку, создании быстрого заказа из `product_cards`, а также перед проверкой и отправкой такого черновика в обработку.
- Ошибки не доходят до записи битых данных в `orders`: HTML-формы получают `flash(..., category='error')` и возврат на форму/заказ, а AJAX-точки `product_cards` отвечают JSON-ошибкой `400`.

### Оформление заказа: дубли в архиве
- Проверка похожего заказа в архиве больше не выполняется при оформлении/отправке заказа в обработку.
- Preflight-ручки оформления (`requests_common.cubaa` и `product_cards` `check_before_process`) продолжают проверять баланс, готовность позиций и обязательные поля, но возвращают `status_order=0` и не блокируют оформление из-за дубля в архиве.

### CRM-массовый перенос заказов AT2
- Массовый перенос `NEW -> POOL` в CRM (`/crm_d/all_new_multi_pool`) доступен `superuser`, модератору `m2r_admin` и агенту тип2 (`role = admin`, `is_at2 = true`).
- `superuser` и `m2r_admin` переносят все новые заказы.
- Агент тип2 переносит только свои заказы и заказы своих клиентов (`orders.user_id = current_user.id` или `users.admin_parent_id = current_user.id`).
- Обычный `admin` без `is_at2` получает предупреждение, заказы не переносятся.
- Логика находится в `app/views/crm/helpers_mo.py`.

### CRM-отчет активности операторов
- Роут отчета: `/crm_uoc/avg_order_processing_time_report`.
- На странице общий фильтр периода и оператора, ниже вкладки 4 отчетов:
  - заказы операторов по категориям;
  - взятые заказы по дням и категориям;
  - среднее время обработки заказов;
  - полные метрики заказов в `.txt` с JSON-массивом для анализа ИИ.
- Заказ попадает в отчеты по факту заполненного `orders.m_finished`; отмененные заказы исключаются через `stage != CANCELLED`.
- В MRS категория `носки и прочее` в отчетах по категориям считается в колонку `Одежда`.
- Отчет среднего времени распределяет заказы по длительности `m_finished - m_started`: до 1 дня, до 2 дней, до 3 дней, до 4 дней и более 4 дней.
- Максимальный диапазон формирования обычных отчетов - 4 месяца, дневного отчета - 1 месяц, отчета полных метрик - 1 год. Ограничения применяются на фронте и на backend.
- В интерфейсе каждой вкладки есть раскрываемая справка по иконке `i`; общие стили описаний лежат в `app/templates/crm_mod_v1/reports/avg_order_processing_time/report_description.html`.
- Excel-выгрузки используют те же данные и порядок колонок, что и HTML-таблицы.

## Инструкция по развертыванию

### Виртуальное окружение и переменные среды 
- <h4>Переименуй .env.example в .env и заполни переменные своими значениями</h4>

### Telegram через proxy (если есть таймауты из РФ)
- Основная переменная: TELEGRAM_PROXY
- Поддерживаемый формат:
```dotenv
TELEGRAM_PROXY=http://login:password@proxy-host:port
```
- Пример дополнительных настроек устойчивости:
```dotenv
TELEGRAM_CONNECT_TIMEOUT_SEC=25
TELEGRAM_READ_TIMEOUT_SEC=60
TELEGRAM_SEND_RETRIES=3
TELEGRAM_RETRY_BACKOFF_SEC=2.0
TELEGRAM_RETRY_BACKOFF_FACTOR=1.7
TELEGRAM_RETRY_MAX_DELAY_SEC=20.0
```
- Для bot_notifications можно отдельно регулировать polling/startup:
```dotenv
TELEGRAM_REQUEST_TIMEOUT_SEC=90
TELEGRAM_POLLING_TIMEOUT_SEC=30
TELEGRAM_STARTUP_RETRIES=5
TELEGRAM_STARTUP_RETRY_DELAY_SEC=3.0
TELEGRAM_BACKOFF_MIN_DELAY_SEC=1.0
TELEGRAM_BACKOFF_MAX_DELAY_SEC=30.0
TELEGRAM_BACKOFF_FACTOR=1.5
TELEGRAM_BACKOFF_JITTER=0.2
TELEGRAM_DROP_PENDING_UPDATES_ON_STARTUP=true
```
- Проверка подключения из контейнера flask_app:
```shell
docker exec flask_app python -c "from telebot import apihelper; print('proxy=', apihelper.proxy, 'connect=', apihelper.CONNECT_TIMEOUT, 'read=', apihelper.READ_TIMEOUT)"
docker exec flask_app curl -I --max-time 20 https://api.telegram.org
```
- Проверка подключения из контейнера bot_notification:
```shell
docker exec bot_notification curl -I --max-time 20 https://api.telegram.org
```

### Алерты в Telegram

ElastAlert2 живёт в `docker-compose.elk.yml` как отдельный контейнер, поднимается вместе с `make elk-up`. Раз в минуту опрашивает Elasticsearch, при срабатывании правила шлёт в Telegram.

Правила в `elk/elastalert/rules/`:
- `flask_errors.yaml` — 3+ строки ERROR/CRITICAL в логах Flask за 5 минут
- `nginx_5xx.yaml` — 5+ ответов 500/502/503/504 от nginx за 5 минут
- `apm_exceptions.yaml` — любое Python-исключение через APM-агент (то же что Kibana APM → Errors), группировка по culprit, кулдаун 10 минут
- `apm_failed_transactions.yaml` — любая упавшая транзакция, кулдаун 15 минут на endpoint

Переменные окружения которые нужны:
```dotenv
HEALTHCHECK_BOT=...               # токен Telegram-бота
TELEGRAM_ALERTS_GROUP_ID=...      # chat_id канала с алертами
```

### Health check эндпоинт

`GET /app/health` — проверяет `SELECT 1` к PostgreSQL и `PING` к Redis. Возвращает 200 если всё ок, 503 если что-то упало. Во время тех. обслуживания возвращает `200 {"status":"maintenance"}` — так внешний мониторинг не сходит с ума при плановых деплоях.

Закрыт токеном — без заголовка `X-Health-Token` вернёт 403.

```dotenv
HEALTH_CHECK_TOKEN=...   # одинаковый в .env и в мониторинге
```

### Запуск elk
- Для формирования секретных ключей и сертификатов elk
```shell
make elk-setup
```
- Для запуска elk сервиса(Elasticsearch, logstash, kibana)
```shell
make elk-up
```
- Для сбора логов и запуска filebeat
```shell
make collect-logs
```

### Проверка, почему не приходят логи Nginx
- Проверить, что запущены сервисы приложения и ELK:
```shell
make service-up
make elk-up
make collect-logs
```
- Проверить, что Nginx пишет в файлы на хосте:
```shell
ls -lah /var/log/nginx
tail -n 50 /var/log/nginx/access.log
tail -n 50 /var/log/nginx/error.log
```
- Проверить, что Filebeat и Logstash живы и без ошибок:
```shell
docker compose -f docker-compose.elk.yml -f docker-compose.logs.yml ps
docker compose -f docker-compose.elk.yml -f docker-compose.logs.yml logs --tail=200 filebeat logstash
```

### Ротация и lifecycle логов
- ILM для индексов nginx/flask-app создается автоматически контейнером `ilm-setup` (горячая фаза + удаление).
- Ротация контейнерных логов включена в compose через `json-file` (`max-size=10m`, `max-file=5`).
- Для ротации файловых логов на хосте (`/var/log/nginx/*.log`, `/var/log/flask-app/*.log`):
```shell
make logrotate-install
make logrotate-check
```

### Запуск основного приложения(flask_app) и вспомогательных сервисов(nginx, postgres, redis, rq-dashboard)
- Запуск сервисов
```shell
make service-up
```
- Показать логи сервисов
```shell
make service-logs
```

### Запуск minio s3 хранилища и вспомогательных сервисов(minio, create_buckets)
---
## Для запуска minio
```shell
make minio-up
```
---
## Для остановки minio
```shell
make minio-down
```

### Режим технического обслуживания(maintenance mode)
- Включить режим технического обслуживания
```shell
make maintenance-on
```
- Выключить режим технического обслуживания
```shell
make maintenance-off
```

## Остановка сервисов

- ### Остановка elk и удаление контейнеров
```shell
make elk-down
```
- ### Остановка сервисов основного приложения(flask_app, nginx, postgres, redis, rq-dashboard) и удаление контейнеров
```shell
make service-down
```
---
## Для локального запуска приложения(flask_app)
```shell
make flask-local-run
```

## Cache Bust для static

- Версия для `url_for('static', ...)` задается один раз на старте Flask-контейнера в `app.config['STATIC_VERSION']`.
- Далее `@app.url_defaults` автоматически добавляет `?v=<STATIC_VERSION>` ко всем static URL, если `v` не передан вручную.
- На проде это не зависит от локальной папки `static` внутри `flask_app`, поэтому схема работает вместе с MinIO.
- После нового деплоя или рестарта `flask_app` значение `STATIC_VERSION` меняется, и браузер запрашивает новую статику.
- Ручные `?v=...` в шаблонах добавлять не нужно.

## Порты
```
9181 - rq-dashboard
5005 - flask_app(обращайся к приложению через 80 порт)
80/443 - nginx
9001 - web interface minio
```

## Доступные ссылки после запуска
- [Главная марка- сервис 2.0](http://0.0.0.0:80)
- [Kibana](https://0.0.0.0:5601)
- [Web интерфейс для мониторинга фоновых задач](http://0.0.0.0:9181)
- [Web интерфейс minio s3 хранилища](http://0.0.0.0:9001)
