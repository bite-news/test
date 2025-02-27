from sqlalchemy import func
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
def get_articles(session: Session, page: int = 1):
    """✅ 최신 ID순 (AutoIncrement 역순)으로 기사 리스트 조회 + Paging 정보 추가"""
    try:
        # 1️⃣ 전체 기사 개수 조회
        total_count = session.query(func.count(Article.id)).scalar()
        total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE  # 올림 처리

        # 2️⃣ 최신 ID순으로 8개씩 페이징 처리 (ID DESC)
        articles = (
            session.query(Article)
            .filter(Article.video_url.isnot(None))  # ✅ 비디오가 있는 것만
            .order_by(Article.id.desc())  # ✅ ID 역순 정렬 (최신 ID부터)
            .limit(PAGE_SIZE)
            .offset((page - 1) * PAGE_SIZE)
            .all()
        )

        # 3️⃣ 추가 데이터 확인 (hasNextPage, hasFirstPage, totalPageCount)
        has_next_page = page < total_pages
        has_prev_page = page > 1

        return {
            "articles": [article.__dict__ for article in articles],  # ✅ SQLAlchemy 객체를 JSON 변환
            "page": page,
            "hasPrev": has_prev_page,
            "hasNextPage": has_next_page,
            "totalPageCount": total_pages
        }
    except Exception as e:
        raise RuntimeError(f"❌ 비디오 리스트 조회 오류: {e}")
    
# ✅ Article 상세 조회
def get_article_detail(session: Session, article_id: int):
    """✅ 특정 기사 조회 + 이전/다음 기사 ID 포함 (ID ± 1 방식)"""
    try:
        # 1️⃣ 현재 기사 조회
        article = session.query(Article).filter(Article.id == article_id).first()
        if not article:
            return None  # 없는 경우 None 반환

        # 2️⃣ 이전/다음 기사 ID 계산 (id + 1, id - 1)
        prev_id = article_id + 1
        next_id = article_id - 1

        # 3️⃣ 존재하는 ID인지 확인 (존재하지 않으면 None)
        prev_exists = session.query(Article.id).filter(Article.id == prev_id).scalar()
        next_exists = session.query(Article.id).filter(Article.id == next_id).scalar()

        return {
            "id": article.id,
            "title": article.title,
            "source_url": article.source_url,
            "thumbnail_url": article.thumbnail_url,
            "video_url": article.video_url,
            "source_created_at": article.source_created_at,
            "prev_id": prev_id if prev_exists else None,  # ✅ 존재하면 유지, 없으면 None
            "next_id": next_id if next_exists else None  # ✅ 존재하면 유지, 없으면 None
        }
    except Exception as e:
        raise RuntimeError(f"❌ 기사 상세 조회 오류: {e}")


# ✅ Article 검색 조회
def search_articles(session: Session, keyword: str):
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