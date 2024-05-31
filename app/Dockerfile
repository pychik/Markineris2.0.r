# FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ARG ROOT_DIR=/

WORKDIR /app

RUN apt-get update && apt-get install -y netcat-traditional && \
    apt-get install -yq tzdata && \
    apt-get install -y wget && \
    wget http://archive.ubuntu.com/ubuntu/pool/multiverse/u/unrar-nonfree/unrar_5.0.10-1_amd64.deb && \
    dpkg -i unrar_5.0.10-1_amd64.deb && \
    apt-get install -f && \
    ln -fs /usr/share/zoneinfo/Europe/Moscow /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

ENV TZ="Europe/Moscow"
COPY ./requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && pip install -r /app/requirements.txt
COPY . /app

ENV PYTHONPATH /app

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x entrypoint.sh

EXPOSE 5005
