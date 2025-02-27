FROM python:3.9.6-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

ENV CONFIG_PATH=/app/bitenews.yml

COPY ./bitenews/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
COPY ./bitenews.yml /app/bitenews.yml 

CMD ["uvicorn", "bitenews.main:app", "--host", "0.0.0.0", "--port", "8000"]

