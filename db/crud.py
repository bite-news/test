from sqlalchemy.orm import Session
from model.article import Article

# ✅ 기사 데이터 삽입
def insert_article(session: Session, article: Article):
    session.add(article)
    session.commit() 
    session.refresh(article)

# ✅ AWS S3 URL 업데이트 (비디오 & 썸네일)
def update_article(session: Session, article_id: int , video_url: str, thumbnail_url: str):
    article = session.query(Article).filter(Article.id == article_id).first()
    article.video_url = video_url
    article.thumbnail_url = thumbnail_url
    session.commit()
    session.refresh(article)

# ✅ Article List Paging 조회 
PAGE_SIZE = 8
def get_article_list(session: Session, page: int = 1):
    """✅ 최신순으로 기사 리스트 조회 (Infinite Scroll)"""
    try:
        # 1️⃣ 최신순으로 8개씩 페이징 처리
        videos = (
            session.query(Article)
            .filter(Article.video_url.isnot(None))  # ✅ 비디오가 있는 것만
            .order_by(Article.source_created_at.desc())  # 최신순 정렬
            .limit(PAGE_SIZE)
            .offset((page - 1) * PAGE_SIZE)
            .all()
        )

        # 2️⃣ 응답 데이터 변환
        video_list = [
            {
                "id": video.id,
                "title": video.title,
                "source_url": video.source_url,
                "thumbnail_url": video.thumbnail_url,
                "video_url": video.video_url,
                "source_created_at": video.source_created_at
            }
            for video in videos
        ]

        # 3️⃣ 추가 데이터가 있는지 확인
        next_page = page + 1 if len(videos) == PAGE_SIZE else None
        return {
            "articles": video_list,
            "next_page": next_page
        }
    except Exception as e:
        raise RuntimeError(f"❌ 비디오 리스트 조회 오류: {e}")

# ✅ Article 검색 조회
def search_article_list(session: Session, keyword: str):
    """ ✅ 검색어로 숏폼 검색 """
    try:
        videos = (
            session.query(Article)
            .filter(Article.video_url.isnot(None))
            .filter(Article.title.ilike(f"%{keyword}%"))  # ✅ 제목에 검색어 포함
            .order_by(Article.source_created_at.desc())
            .all()
        )

        video_list = [
            {
                "id": video.id,
                "title": video.title,
                "source_url": video.source_url,
                "thumbnail_url": video.thumbnail_url,
                "video_url": video.video_url,
                "source_created_at": video.source_created_at
            }
            for video in videos
        ]

        return {
            "articles": video_list
        }
    except Exception as e:
        raise RuntimeError(f"❌ 비디오 검색 오류: {e}")