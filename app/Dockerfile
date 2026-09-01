FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ="Europe/Moscow"

ARG ROOT_DIR=/

WORKDIR /app

RUN set -eux; \
    python -c "from urllib.request import urlretrieve; urlretrieve('http://archive.ubuntu.com/ubuntu/pool/multiverse/u/unrar-nonfree/unrar_5.0.10-1_amd64.deb', '/tmp/unrar_5.0.10-1_amd64.deb')"; \
    dpkg -i /tmp/unrar_5.0.10-1_amd64.deb; \
    rm -f /tmp/unrar_5.0.10-1_amd64.deb

COPY ./requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && pip install -r /app/requirements.txt
COPY . /app

ENV PYTHONPATH /app

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x entrypoint.sh

EXPOSE 5005
