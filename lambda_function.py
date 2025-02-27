import os
import json
import requests
import logging
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# ✅ 로깅 설정
logging.basicConfig(level=logging.INFO)

# ✅ 환경 변수에서 API 엔드포인트 가져오기
FASTAPI_SERVER_URL = os.getenv("FASTAPI_SERVER_URL", "http://3.34.177.106:8000/ai/video")

# ✅ 헤더 설정 (크롤링 차단 방지)
header = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"),
}

# ✅ 현재 시간 (UTC+9 기준)
CURRENT_TIME = datetime.now()

# ✅ 크롤링할 네이버 뉴스 카테고리
categories = {
    "정치": "https://news.naver.com/section/100",
    "경제": "https://news.naver.com/section/101",
    "사회": "https://news.naver.com/section/102",
}

# 📰 개별 기사 크롤링 함수
def scrape_article(article_url):
    try:
        time.sleep(1)  # 요청 간격 조정 (네이버 서버 차단 방지)
        response = requests.get(article_url, headers=header)
        soup = BeautifulSoup(response.text, "html.parser")

        # ✅ 기사 제목 찾기
        title_tag = soup.find("h2", {"id": "title_area"})
        title = title_tag.text.strip() if title_tag else "제목 없음"

        # ✅ 기사 본문 찾기
        content_tag = soup.find("article", {"id": "dic_area"})
        content = content_tag.text.strip().replace('\\"', '"').replace("\n", " ") if content_tag else "본문 없음"

        # ✅ 기사 생성 시간 찾기
        timestamp_tag = soup.find("span", {"class": "media_end_head_info_datestamp_time _ARTICLE_DATE_TIME"}) 
        if timestamp_tag and "data-date-time" in timestamp_tag.attrs:
            article_time = datetime.strptime(timestamp_tag["data-date-time"], "%Y-%m-%d %H:%M:%S")
        else:
            article_time = None

        return {
            "title": title,
            "content": content,
            "timestamp": article_time,
            "link": article_url
        }
    except Exception as e:
        logging.error(f"기사 크롤링 실패: {article_url}, 오류: {e}")
        return None

# 🚀 FastAPI 서버로 데이터 전송 함수
def post_article_to_server(article_data):
    headers = {"Content-Type": "application/json"}
    try:
        logging.info(f"📤 BiteNews에 기사 전송 중: {article_data['title']}")
        response = requests.post(FASTAPI_SERVER_URL, json=article_data, headers=headers)
        if response.status_code == 201:
            response_data = response.json()
            logging.info(f"📥 FastAPI 응답 수신 완료: {response_data}")

            # ✅ 숏폼 생성 완료 or 실패 로그 남김
            if response_data.get("status") == "success":
                logging.info(f"✅ 숏폼 생성 완료: {article_data['title']}")
            else:
                logging.warning(f"⚠️ 숏폼 생성 실패: {article_data['title']}, 이유: {response_data.get('message', '알 수 없음')}")

        else:
            logging.error(f"❌ BiteNews 오류 {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ BiteNews 서버 연결 실패: {e}")

# ⏳ 3시간 이내 기사 필터링 함수
def filter_recent_articles(article_urls):
    valid_articles = []
    three_hours_ago = CURRENT_TIME - timedelta(hours=3)

    for url in article_urls:
        article_data = scrape_article(url)
        
        # 3시간 이내 기사만 추가
        if article_data["timestamp"] >= three_hours_ago:
            article_data["timestamp"] = article_data["timestamp"].strftime("%Y-%m-%dT%H:%M:%S+09:00")
            valid_articles.append(article_data)

    return valid_articles

# 📌 헤드라인 뉴스 크롤링 함수
def check_for_new_articles(base_url, category):
    try:
        news_data = []
        response = requests.get(base_url, headers=header)
        soup = BeautifulSoup(response.text, "html.parser")
        headline_list = soup.find("ul", class_="sa_list")
        
        if not headline_list:
            logging.warning(f"{category}: 헤드라인 뉴스 리스트를 찾을 수 없음")
            return

        for item in headline_list.find_all("li", class_="sa_item _SECTION_HEADLINE")[:5]:
            title_tag = item.find("a", class_="sa_text_title")
            title = title_tag.find("strong", class_="sa_text_strong").text.strip()
            link = title_tag["href"]
            news_data.append({'title': title, 'link': link})

        # 🔥 3시간 이내 기사 필터링
        article_links = [news["link"] for news in news_data]
        recent_articles = filter_recent_articles(article_links)

        # 결과 출력
        for article in recent_articles:
            post_article_to_server(article)

    except Exception as e:
        logging.error(f"{category} 크롤링 실패: {e}")

# 🔄 전체 카테고리 크롤링 실행 함수
def scrap_all_categories():
    for category, base_url in categories.items():
        logging.info(f"📡 {category} 크롤링 시작 ({base_url})")
        check_for_new_articles(base_url, category)
        time.sleep(1)  # 요청 간격 조정

# AWS Lambda용 핸들러 함수
def lambda_handler(event, context):
    logging.info("Lambda 실행 시작")
    scrap_all_categories()
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Lambda 완료"})
    }
