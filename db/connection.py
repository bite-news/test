from config import logger, config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 📌 RDS config (flat key 구조 사용)
RDS_DB = config['RDS_DATABASE']
RDS_HOST = config['RDS_HOST'].strip()
RDS_PORT = config['RDS_PORT']
RDS_USER = config['RDS_USER']
RDS_PASSWORD = config['RDS_PASSWORD']

# 🔥 RDS 연결 설정
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{RDS_USER}:{RDS_PASSWORD}@{RDS_HOST}:{RDS_PORT}/{RDS_DB}"

# 🔥 RDS 연결 엔진 생성
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 🔥 세션 생성 (FastAPI 종속성으로 사용)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# 🔥 DB 세션 의존성 주입
def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
