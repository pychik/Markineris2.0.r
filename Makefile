.DEFAULT_GOAL:=help

FLASK_APP := -f docker-compose.yml

COMPOSE_ALL_FILES := -f docker-compose.elk.yml -f docker-compose.logs.yml
COMPOSE_LOGGING := -f docker-compose.elk.yml -f docker-compose.logs.yml
COMPOSE_S3_STORAGE := -f docker-compose-minio.yml
ELK_SERVICES := elasticsearch logstash kibana apm-server
ELK_LOG_COLLECTION := filebeat
ELK_MAIN_SERVICES := ${ELK_SERVICES}
ELK_ALL_SERVICES := ${ELK_MAIN_SERVICES} ${ELK_LOG_COLLECTION}

compose_v2_not_supported = $(shell command docker compose 2> /dev/null)
ifeq (,$(compose_v2_not_supported))
  DOCKER_COMPOSE_COMMAND = docker-compose
else
  DOCKER_COMPOSE_COMMAND = docker compose
endif

# --------------------------
.PHONY: flask-local-run maintenance-on maintenance-off service-logs service-start service-stop flask-up flask-down set-vm elk-setup elk-up collect-logs elk-down elk-stop elk-restart elk-rm elk-logs elk-images elk-prune ps minio-up minio-down help


up-all:				## Запуск всего сервиса и elk-stack.
	@make elk-setup
	${DOCKER_COMPOSE_COMMAND} ${COMPOSE_ALL_FILES} up --build -d
	@make service-up
down-all:				## Останавливает и удаляет контейнеры всего сервиса и elk-stack.
	${DOCKER_COMPOSE_COMMAND} ${COMPOSE_ALL_FILES} down
	@make service-down

flask-local-run:				## Запуск flask app и его зависимости, локально.
	cd app && flask db migrate
	cd app && flask db upgrade
	cd app && flask run

maintenance-on:					## Включение режима "технических работ".
	touch ./maintenance/maintenance.flag
	@make flask-down
maintenance-off:				## Выключение режима "технических работ" и удаление всех неиспользуемых докер образов.
	@make flask-up
	sleep 68
	rm -fr ./maintenance/maintenance.flag
	docker image prune -f

service-logs:					## Отображение в режиме реального времени всех логов поступающих в сеть контейнеров сервиса маркинерис(Flask app, db, nginx).
	${DOCKER_COMPOSE_COMMAND} ${FLASK_APP} logs -f

service-up:					## Запуск контейнеров сервиса маркинерис(Flask app, db, nginx).
	${DOCKER_COMPOSE_COMMAND} ${FLASK_APP} up --build -d
	${DOCKER_COMPOSE_COMMAND} ${FLASK_APP} restart bot_notification
	docker image prune -f

service-down:					## Остановка контейнеров сервиса маркинерис(Flask app, db, nginx).
	${DOCKER_COMPOSE_COMMAND} ${FLASK_APP} down

service-bccr:     ## builder cache clean restart
	docker builder prune
	@make elk-down
	@make elk-setup
	@make elk-up
	@make service-down
	@make service-up
	@make collect-logs

flask-up:						## Запуск контейнера Flask app.
	${DOCKER_COMPOSE_COMMAND} ${FLASK_APP} up --build -d flask_app
	${DOCKER_COMPOSE_COMMAND} ${FLASK_APP} restart bot_notification
flask-down:						## Остановка контейнера Flask app.
	${DOCKER_COMPOSE_COMMAND} ${FLASK_APP} stop flask_app

set-vm:							## Установка максиального объема памяти виртуальной машины для корректного запуска ELK Stack.
	sudo sysctl -w vm.max_map_count=262144


keystore:
	$(DOCKER_COMPOSE_COMMAND) -f docker-compose.setup.yml run --rm keystore

certs:
	$(DOCKER_COMPOSE_COMMAND) -f docker-compose.setup.yml run --rm certs

elk-setup:		    				## Генериразция SSL-сертификатов Elasticsearch и хранилище ключей.
	@make certs
	@make keystore

elk-up: 						## Запуск elk stack(elasticsearch, logstash, kibana).
	@make set-vm
	$(DOCKER_COMPOSE_COMMAND) -f docker-compose.elk.yml up --build -d
	@echo "Visit Kibana: https://localhost:5601 (user: elastic, password: look in .env file) [Unless you changed values in .env]"

collect-logs: 					## Запусти Filebeat, который собирает логи, и отправьте его в ELK.
	$(DOCKER_COMPOSE_COMMAND) ${COMPOSE_LOGGING} up --build -d ${ELK_LOG_COLLECTION}

ps:								## Показать все запущенные контейнеры.
	$(DOCKER_COMPOSE_COMMAND) ps

elk-down:						## Остановка и удаление контейнеров ELK.
	$(DOCKER_COMPOSE_COMMAND) ${COMPOSE_ALL_FILES} down

elk-stop:						## Остановка контейнеров ELK.
	$(DOCKER_COMPOSE_COMMAND) ${COMPOSE_ALL_FILES} stop ${ELK_ALL_SERVICES}

elk-restart:					## Перезапуск существующих контейнеров ELK и все его дополнительные компоненты.
	$(DOCKER_COMPOSE_COMMAND) ${COMPOSE_ALL_FILES} restart ${ELK_ALL_SERVICES}

elk-rm:							## Удаление ELK и всех дополнительных компонентов.
	$(DOCKER_COMPOSE_COMMAND) $(COMPOSE_ALL_FILES) rm -f ${ELK_ALL_SERVICES}

elk-logs:						## Конец всех логов c -n 1000.
	$(DOCKER_COMPOSE_COMMAND) $(COMPOSE_ALL_FILES) logs --follow --tail=1000 ${ELK_ALL_SERVICES}

elk-images:						## Показать все изображения ELK и всех его дополнительных компонентов.
	$(DOCKER_COMPOSE_COMMAND) $(COMPOSE_ALL_FILES) images ${ELK_ALL_SERVICES}

elk-prune:						## Удалить ELK контейнеры и удалить волюмы с данными, связанные с ELK (том данных elastic_elasticsearch)
	@make stop && make rm
	@docker volume prune -f --filter label=com.docker.compose.project=elastic

minio-up:						## Запустить контейнеры сервиса Minio(minio, create_buckets)
	$(DOCKER_COMPOSE_COMMAND) $(COMPOSE_S3_STORAGE) up --build -d

minio-down:						## Остановить контейнеры сервиса Minio(minio, create_buckets)
	$(DOCKER_COMPOSE_COMMAND) $(COMPOSE_S3_STORAGE) down

minio-logs:						## Остановить контейнеры сервиса Minio(minio, create_buckets)
	$(DOCKER_COMPOSE_COMMAND) $(COMPOSE_S3_STORAGE) logs -f

help:       					## Показать все команды.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m (default: help)\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
