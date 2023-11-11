FROM python:3.11-slim-bullseye

WORKDIR /wine

COPY ./requirements.txt /wine/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /wine/requirements.txt

COPY config.py /wine/config.py
COPY app.py /wine/app.py
COPY ./schemas/wine.py /wine/wine.py

EXPOSE 8000