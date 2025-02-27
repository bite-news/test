from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import declarative_base
from db.connection import engine

Base = declarative_base()

# 📌 Article 테이블 모델
class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # 자동 증가 ID
    title = Column(String(255), index=True, nullable=False)  # 제목
    source_url = Column(String(255), nullable=False)  # 원본 기사 URL
    video_url = Column(String(255), nullable=True)  # 생성된 비디오 URL (AWS S3)
    thumbnail_url = Column(String(255), nullable=True)  # 생성된 썸네일 이미지 URL (AWS S3)
    source_created_at = Column(String(50), nullable=False)  # 기사 원본 생성 시간 (ISO 8601)
    # content= Column(Text, nullable=False)  # 내용

# 📌 DB 테이블 생성 (최초 실행 시 필요)
Base.metadata.create_all(bind=engine)
