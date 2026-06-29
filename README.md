# Markineris2.0.r
Markineris2.0.r for special agents

## Информационные команды

- Команда help, для просмотра доступных команд и их краткое описание
```shell
make help
```

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


