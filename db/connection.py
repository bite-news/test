from config import logger, config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 📌 RDS config
RDS_DB = config['rds']['database']
RDS_HOST = config['rds']['host']
RDS_PORT = config['rds']['port']
RDS_USER = config['rds']['user']
RDS_PASSWORD = config['rds']['password']

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
        yield db # DB가 연결된 경우, DB 세션 시작
    finally:
        db.close() # DB 세션이 시작되고, API 호출이 마무리되면 DB 세션을 닫아준다.