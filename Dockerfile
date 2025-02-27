FROM python:3.9.6-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# 환경 변수 설정 (GitHub Actions에서 주입)
ENV AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ENV AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
ENV OPENAI_API_KEY=${OPENAI_API_KEY}
ENV CONFIG_PATH=/app/bitenews.yml

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

CMD ["uvicorn", "bitenews.main:app", "--host", "0.0.0.0", "--port", "8000"]
