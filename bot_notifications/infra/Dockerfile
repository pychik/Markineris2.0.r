FROM python:3.11-slim-buster

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1

ENV PYTHONBUFFERED 1

RUN apt-get -y update; apt-get -y install curl &&  \
    ln -fs /usr/share/zoneinfo/Europe/Moscow /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

ENV TZ="Europe/Moscow"

COPY ./requirements.txt ./requirements.txt

RUN pip install --upgrade pip && pip install -r requirements.txt

COPY ./src ./src

ENV PYTHONPATH /app/src