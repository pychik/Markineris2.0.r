#!/bin/sh

#flask db init
#flask db migrate
#flask db upgrade
#flask create_superuser

gunicorn --workers 8 --max-requests 1000 --max-requests-jitter 50 --timeout 300 --bind 0.0.0.0:5005 wsgi:app &

python3 redis_queue/worker.py &
python3 redis_queue/scheduler.py
