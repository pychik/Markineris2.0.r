FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ="Europe/Moscow"

ARG ROOT_DIR=/

WORKDIR /app

RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i \
            -e 's|http://deb.debian.org/debian-security|http://mirror.selectel.ru/debian-security|g' \
            -e 's|http://security.debian.org/debian-security|http://mirror.selectel.ru/debian-security|g' \
            -e 's|http://deb.debian.org/debian|http://mirror.selectel.ru/debian|g' \
            /etc/apt/sources.list.d/debian.sources; \
    fi; \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i \
            -e 's|http://deb.debian.org/debian-security|http://mirror.selectel.ru/debian-security|g' \
            -e 's|http://security.debian.org/debian-security|http://mirror.selectel.ru/debian-security|g' \
            -e 's|http://deb.debian.org/debian|http://mirror.selectel.ru/debian|g' \
            /etc/apt/sources.list; \
    fi; \
    printf 'Acquire::Retries "5";\nAcquire::ForceIPv4 "true";\nAcquire::http::Timeout "30";\nAcquire::https::Timeout "30";\n' > /etc/apt/apt.conf.d/80-retries; \
    apt-get update; \
    apt-get install -y --no-install-recommends netcat-traditional tzdata wget ca-certificates; \
    wget --tries=5 --retry-connrefused --waitretry=5 --timeout=30 \
        -O /tmp/unrar_5.0.10-1_amd64.deb \
        http://archive.ubuntu.com/ubuntu/pool/multiverse/u/unrar-nonfree/unrar_5.0.10-1_amd64.deb; \
    dpkg -i /tmp/unrar_5.0.10-1_amd64.deb || apt-get -y --no-install-recommends -f install; \
    rm -f /tmp/unrar_5.0.10-1_amd64.deb; \
    ln -fs /usr/share/zoneinfo/Europe/Moscow /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata; \
    rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && pip install -r /app/requirements.txt
COPY . /app

ENV PYTHONPATH /app

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x entrypoint.sh

EXPOSE 5005
