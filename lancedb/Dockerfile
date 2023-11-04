FROM python:3.11-slim-bullseye

WORKDIR /wine

COPY requirements.txt /winemag/requirements.txt

RUN pip install --no-cache-dir -U pip wheel setuptools
RUN pip install --no-cache-dir -r /winemag/requirements.txt

COPY app.py /wine/app.py
COPY config.py /wine/config.py
COPY ./winemag /wine/winemag
COPY ./schemas /wine/schemas

EXPOSE 8000