# Markineris-2.0.r
Markineris-2.0 for special agents

## Информационные команды

- Команда help, для просмотра доступных команд и их краткое описание
```shell
make help
```

## Инструкция по развертыванию

### Виртуальное окружение и переменные среды 
- <h4>Переименуй .env.example в .env и заполни переменные своими значениями</h4>

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

### Запуск основного приложения(flask_app) и вспомогательных сервисов(nginx, postgres, redis, rq-dashboard)
- Запуск сервисов
```shell
make service-up
```
- Показать логи сервисов
```shell
make service-logs
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
80 - nginx
```

## Доступные ссылки после запуска
- [Главная Маркинерис 2.0](http://0.0.0.0:80)
- [Kibana](https://0.0.0.0:5601)
- [Web интерфейс для мониторинга фоновых задач](http://0.0.0.0:9181)
