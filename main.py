from pydantic import BaseModel
from model.article import Article

from config import logger, config
from aws.s3 import upload_to_s3
from db.connection import get_session
from db.crud import insert_article, update_article, get_articles, get_article_detail, search_articles

from fastapi import Depends, FastAPI, HTTPException

from article import create_article

# FastAPI 앱 생성
app = FastAPI()

# 📌 요청 데이터 모델 정의


class ArticleRequestDto(BaseModel):
    title: str
    content: str
    link: str
    timestamp: str

# ✅ FastAPI 엔드포인트: AWS Lambda로부터 News Article 정보 수신 및 Shortform 생성


@app.post("/ai/video", status_code=201)
async def receive_article_and_make_shortform(article_request_dto: ArticleRequestDto, session=Depends(get_session)):
    logger.info(f"📥 기사 정보 수신: {article_request_dto.title}")

    try:
        # ✅ 1️⃣ Article 정보 저장
        new_article = Article(title=article_request_dto.title, source_url=article_request_dto.link,
                              source_created_at=article_request_dto.timestamp)
        insert_article(session, new_article)
        logger.info(f"📥 기사 DB 저장 완료: {article_request_dto.title}")

        # ✅ 2️⃣ 썸네일 & 비디오 생성
        create_article(article_request_dto.title, article_request_dto.content)
        thumbnail_path = "output/thumbnail.png"
        video_path = "output/final_video.mp4"
        logger.info(f"✅ 비디오 생성 완료: {new_article.id} : {new_article.title}")

        # ✅ 3️⃣ S3 업로드 (썸네일 + 영상)
        thumbnail_url = upload_to_s3(
            thumbnail_path, f"article/{new_article.id}/thumbnail.png", "image/png")
        video_url = upload_to_s3(
            video_path, f"article/{new_article.id}/video.mp4", "video/mp4")
        logger.info(f"✅ S3 업로드 완료: {new_article.id} : {new_article.title}")

        # ✅ 4️⃣ Article 정보 업데이트 (S3 URL)
        update_article(session, new_article.id, video_url, thumbnail_url)
        logger.info(f"✅ 기사 DB 업데이트 완료: {new_article.id} : {new_article.title}")

        return {"status": "success", "message": "✅ 기사 숏폼 생성 성공!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ 서버 오류: {e}")

# ✅ FASTAPI 엔드포인트: Frontend에서 호출하는 Video List 조회 API ( Infinite Scroll )
@app.get("/api/articles", status_code=200)
def get_article_list(page: int = 1, session=Depends(get_session)):
    """✅ 최신순으로 비디오 리스트 조회 (Infinite Scroll)"""
    try:
        return {"status": "success", "message": "✅ 기사 페이징 조회 성공!", "data": get_articles(session, page)}
    except Exception as e:
        logger.error(f"❌ 비디오 리스트 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ✅ FASTAPI 엔드포인트: Frontend에서 호출하는 Video 상세 조회 API   
@app.get("/api/articles/{article_id}", status_code=200)
def get_each_article(article_id: int, session=Depends(get_session)):
    """✅ 기사 상세 조회"""
    try:
        return {"status": "success", "message": "✅ 기사 상세 조회 성공!", "data": get_article_detail(session, article_id)}
    except Exception as e:
        logger.error(f"❌ 기사 상세 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ✅ FASTAPI 엔드포인트: Frontend에서 호출하는 Video 검색 API
@app.get("/api/search", status_code=200)
def search_article_list(keyword: str, session=Depends(get_session)):
    """ ✅ 검색어로 숏폼 검색 """
    try:
        return {"status": "success", "message": "✅ 기사 검색 성공!", "data": search_articles(session, keyword)}
    except Exception as e:
        logger.error(f"❌ 비디오 검색 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 🖥️ 서버 실행: uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
