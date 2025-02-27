# Python 3.9.6 버전 사용
FROM python:3.9.6-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 패키지 업데이트 및 libGL 설치
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0

# 필요 라이브러리 설치를 위한 requirements.txt 복사
COPY ./bitenews/requirements.txt /app/requirements.txt

# 의존성 패키지 설치
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# 애플리케이션 코드 복사
COPY . /app

# FastAPI 서버 실행 (Uvicorn 사용)
CMD ["uvicorn", "bitenews.main:app", "--host", "0.0.0.0", "--port", "8000"]
