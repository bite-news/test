import os
import json
import subprocess
import requests
import openai
import time
import shutil
from io import BytesIO
from langchain_community.chat_models import ChatOpenAI
from langchain_community.document_loaders import WebBaseLoader
from langchain.schema import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment
from config import config, logger

# ====================================
# 초기화 및 설정
# ====================================
os.environ["OPENAI_API_KEY"] = config['openai']['api_key']
openai.api_key = config['openai']['api_key']

# 출력 디렉토리 설정
OUTPUT_DIR = config.get('output_directory', 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "temp"), exist_ok=True)

# ====================================
# 유틸리티 함수
# ====================================


def get_temp_filepath(filename: str) -> str:
    """임시 파일 경로를 생성하는 헬퍼 함수"""
    return os.path.join(OUTPUT_DIR, "temp", filename)


def cleanup_temp_files() -> None:
    """임시 파일들을 정리합니다."""
    try:
        temp_dir = os.path.join(OUTPUT_DIR, "temp")
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            logger.info("임시 파일 정리 완료")
    except Exception as e:
        logger.error(f"[임시 파일 정리 오류] {e}")

# 폰트 로드 (한 번만 수행)


def load_font():
    """폰트를 한 번만 로드하는 함수"""
    # 기본 폰트 경로 설정 - bitenews 디렉토리 내의 폰트 파일
    default_font_path = 'bitenews/GmarketSansTTFBold.ttf'
    font_path = config.get('font_file', default_font_path)
    font_size = config.get('font_size', 50)

    try:
        font = ImageFont.truetype(font_path, size=font_size)
        logger.info(f"{font_path} 폰트 로드 성공")
        return font
    except IOError:
        # 기본 경로로 다시 시도
        try:
            font = ImageFont.truetype(default_font_path, size=font_size)
            logger.info(f"{default_font_path} 폰트 로드 성공")
            return font
        except IOError:
            logger.warning("폰트 파일을 찾을 수 없어 기본 폰트를 사용합니다.")
            return ImageFont.load_default()


# 전역 변수로 폰트 로드
OVERLAY_FONT = load_font()

# ====================================
# 뉴스 시나리오 생성 모델 설정
# ====================================
# GPT 모델 설정
model_config = config.get('model', {})
model = ChatOpenAI(
    model_name=model_config.get('name', 'gpt-4o-mini'),
    temperature=model_config.get('temperature', 0.7),
    max_tokens=model_config.get('max_tokens', 1000),
)

# Pydantic을 이용한 JSON 출력 구조 정의


class Scene(BaseModel):
    scene: int = Field(description="씬 번호 (1~4)")
    dialogue: str = Field(description="해당 씬의 대화 및 설명 (최소 40단어)")


class Scenario(BaseModel):
    title: str = Field(description="유튜브 쇼츠 제목 (8자 이내)", max_length=8)
    scenes: list[Scene] = Field(description="4개의 뉴스 씬 정보 배열")


# JSON 파서 설정
parser = JsonOutputParser(pydantic_object=Scenario)

# 프롬프트 정의
prompt = ChatPromptTemplate.from_messages([
    ("system", "당신은 유튜브 쇼츠용 뉴스 시나리오 제작자입니다. "
     "주어진 뉴스를 바탕으로 **기승전결 구조(1,2,3,4)의 스토리텔링 뉴스 시나리오**를 작성하세요. "
     "각 씬은 **최소 20단어 이상**이어야 하며, **실제 뉴스 앵커가 보도하는 스타일**로 작성해야 합니다."),
    ("user",
     "#Format: {format_instructions}\n\n#News Title: {news_title}\n\n#News Article: {news_text}")
])

# JSON 응답을 강제하는 포맷 지시사항을 프롬프트에 주입
prompt = prompt.partial(format_instructions=parser.get_format_instructions())

# ====================================
# 주요 기능 함수
# ====================================


def generate_scenario(news_text, title):
    """뉴스 기사를 기반으로 4개의 씬으로 구성된 뉴스 스토리 생성"""
    try:
        # 랭체인 구성 및 실행
        chain = prompt | model | parser
        scenario_obj = chain.invoke(
            {"news_text": news_text, 'news_title': title})
        logger.info("GPT API로부터 시나리오 생성 완료")

        # JSON 저장
        with open(get_temp_filepath("scenario.json"), "w", encoding="utf-8") as f:
            json.dump(scenario_obj, f, ensure_ascii=False, indent=2)

        return scenario_obj
    except Exception as e:
        logger.error(f"[GPT API 오류] {e}")
        # 오류 발생 시 기본 시나리오 반환
        return {
            "title": "Dummy 제목",
            "scenes": [
                {"scene": 1, "dialogue": "Dummy 기: 뉴스 기사의 핵심 내용을 요약한 내용입니다."},
                {"scene": 2, "dialogue": "Dummy 승: 상황 전개와 인물들의 발언을 요약한 내용입니다."},
                {"scene": 3, "dialogue": "Dummy 전: 경제·정치적 영향을 설명한 내용입니다."},
                {"scene": 4, "dialogue": "Dummy 결: 결론 및 전망을 제시한 내용입니다."}
            ]
        }


def generate_image(scene_dialogue, scene_number, fallback_images=None):
    """DALL·E로 뉴스 보도 스타일 이미지 생성, 실패 시 대체 이미지 사용"""
    # 이미지 파일명 설정
    filename = get_temp_filepath(f"scene_{scene_number}.png")

    # 캐시된 이미지 확인
    if os.path.exists(filename):
        logger.info(f"[이미지 캐시 사용] {filename}")
        return filename

    # 뉴스 보도 스타일 프롬프트
    prompt = "현대적인 한국 뉴스 보도 스타일의 고품질, 사실적인 1024x1024 이미지를 생성하세요. " \
             "이 이미지는 실제 뉴스 방송 화면이나 온라인 뉴스 기사에서 볼 수 있는 장면처럼 보이도록 구성해야 합니다. " \
             f"이미지는 다음 뉴스 내용을 반영해야 합니다: {scene_dialogue}"

    try:
        # DALL-E 이미지 생성 API 호출
        response = openai.Image.create(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024"
        )

        # 이미지 다운로드 및 저장
        image_url = response['data'][0]['url']
        image_data = requests.get(image_url).content
        with open(filename, "wb") as f:
            f.write(image_data)

        logger.info(f"[이미지 생성] {filename} 1024x1024 생성 완료")
        return filename

    except Exception as e:
        logger.error(f"[이미지 생성 오류] {e}")

        # 대체 이미지 활용 로직: 개선된 포괄적 파이프라인
        if fallback_images and len(fallback_images) > 0:
            # 1. 기존 대체 로직 유지
            if scene_number == 1:
                # scene1 실패 시: 우선 scene2, 없으면 scene3, scene4 순으로 시도
                for check_scene in range(2, 5):
                    check_path = get_temp_filepath(f"scene_{check_scene}.png")
                    if os.path.exists(check_path):
                        logger.warning(
                            f"[대체 이미지 사용] 씬 1에 씬 {check_scene}의 이미지 사용")
                        shutil.copy(check_path, filename)
                        return filename

                # 다른 씬 이미지가 없으면 fallback_images 사용
                fallback_image = fallback_images[0]
                logger.warning(
                    f"[대체 이미지 사용] 씬 {scene_number}에 {fallback_image} 사용")
                shutil.copy(fallback_image, filename)
                return filename
            else:
                # 다른 씬 실패 시: 우선 바로 앞 씬, 없으면 모든 존재하는 씬 시도

                # 먼저 바로 앞 씬 확인 (기존 로직)
                prev_scene_path = get_temp_filepath(
                    f"scene_{scene_number-1}.png")
                if os.path.exists(prev_scene_path):
                    logger.warning(
                        f"[대체 이미지 사용] 씬 {scene_number}에 씬 {scene_number-1}의 이미지 사용")
                    shutil.copy(prev_scene_path, filename)
                    return filename

                # 앞 씬이 없으면, 생성된 모든 씬을 순회하며 확인
                for check_scene in range(1, 5):
                    # 자기 자신은 건너뛰기
                    if check_scene == scene_number:
                        continue

                    check_path = get_temp_filepath(f"scene_{check_scene}.png")
                    if os.path.exists(check_path):
                        logger.warning(
                            f"[대체 이미지 사용] 씬 {scene_number}에 씬 {check_scene}의 이미지 사용")
                        shutil.copy(check_path, filename)
                        return filename

                # 모든 씬을 확인했는데도 없으면 fallback 사용
                fallback_image = fallback_images[0]
                logger.warning(
                    f"[대체 이미지 사용] 씬 {scene_number}에 {fallback_image} 사용")
                shutil.copy(fallback_image, filename)
                return filename

        # fallback_images가 없는 경우
        return None


def overlay_title_on_image(image_path, title, output_path):
    """정사각형 이미지에 제목 텍스트를 오버레이하고 1080x1920 비율로 변환"""
    font = OVERLAY_FONT

    try:
        # 원본 이미지 로드
        image = Image.open(image_path)
        banner_height = int(image.size[1] * 0.25)  # 상단 25% 영역

        # 1080x1920 캔버스 생성 (유튜브 쇼츠 비율)
        final_image = Image.new("RGB", (1080, 1920), "black")
        draw = ImageDraw.Draw(final_image)

        # 텍스트 폰트 크기 자동 조절
        max_text_width = 1020  # 좌우 여백 30px
        font_size = 50  # Default font size

        while True:
            try:
                # 기본 폰트 경로 설정
                default_font_path = 'bitenews/GmarketSansTTFBold.ttf'

                # 폰트 크기 조절을 위한 새 폰트 로드
                current_font = ImageFont.truetype(
                    default_font_path, size=font_size) if font != ImageFont.load_default() else font
                bbox = draw.textbbox((0, 0), title, font=current_font)
                text_width = bbox[2] - bbox[0]

                # 적절한 폰트 크기 결정
                if text_width <= max_text_width or font_size <= 20:
                    font = current_font
                    break

                font_size -= 5

            except Exception:
                font = OVERLAY_FONT
                break

        # 텍스트 배치를 위한 측정
        bbox = draw.textbbox((0, 0), title, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # 텍스트가 너무 길면 여러 줄로 분할
        if text_width > max_text_width:
            words = title.split()
            lines = []
            current_line = ""

            for word in words:
                test_line = current_line + " " + word if current_line else word
                bbox = draw.textbbox((0, 0), test_line, font=font)
                test_width = bbox[2] - bbox[0]

                if test_width <= max_text_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word

            if current_line:
                lines.append(current_line)

            # 여러 줄 텍스트 그리기
            total_text_height = text_height * len(lines)
            start_y = (banner_height - total_text_height) / 2

            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                text_x = (1080 - line_width) / 2
                text_y = start_y + i * text_height
                draw.text((text_x, text_y), line, fill="white", font=font)
        else:
            # 한 줄 텍스트 그리기
            text_x = (1080 - text_width) / 2
            text_y = (banner_height - text_height) / 2
            draw.text((text_x, text_y), title, fill="white", font=font)

        # 이미지 크기 조정 및 배치
        new_width, new_height = 1024, 1024
        image_resized = image.resize((new_width, new_height), Image.LANCZOS)

        paste_x = (1080 - new_width) // 2
        paste_y = banner_height + (1920 - banner_height - new_height) // 2

        final_image.paste(image_resized, (paste_x, paste_y))

        # 최종 이미지 저장
        final_image.save(output_path)
        logger.info(f"[Overlay 적용 완료] {output_path}")
        return True

    except Exception as e:
        logger.error(f"[이미지 오버레이 오류] {e}")
        return False


def generate_fast_tts(text, output_filename, speed=1.25):
    """gTTS를 사용하여 TTS 생성 및 속도 조절"""
    try:
        # TTS 생성
        tts = gTTS(text=text, lang='ko', tld="co.kr", slow=False)
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)

        # 오디오 속도 조절
        audio = AudioSegment.from_file(fp, format="mp3")
        fast_audio = audio.speedup(
            playback_speed=speed, chunk_size=150, crossfade=25)
        fast_audio.export(output_filename, format="mp3")

        logger.info(f"TTS 생성 완료: {output_filename}")
        return True

    except Exception as e:
        logger.error(f"[TTS 생성 오류] {e}")
        return False


def create_video_clip(image_file, audio_file, output_file):
    """이미지와 오디오를 결합하여 비디오 클립 생성"""
    # 기본값으로 직접 설정
    audio_bitrate = '192k'

    command = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_file,
        "-i", audio_file,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", audio_bitrate,
        "-vf", "scale='iw-mod(iw,2)':'ih-mod(ih,2)',format=yuv420p",
        "-shortest",
        "-movflags", "+faststart",
        output_file
    ]

    try:
        subprocess.run(command, check=True)
        logger.info(f"[영상 클립 생성] {output_file} 생성 완료")
        return output_file
    except subprocess.CalledProcessError as e:
        logger.error(f"[ffmpeg 오류] {e}")
        return None


def concatenate_video_clips(video_files, output_filename="final_video.mp4"):
    """여러 비디오 클립을 하나로 합치기"""
    concat_list = get_temp_filepath("concat_list.txt")

    try:
        # concat 파일 생성
        with open(concat_list, "w", encoding="utf-8") as f:
            for video in video_files:
                abs_path = os.path.abspath(video)
                f.write(f"file '{abs_path}'\n")

        # ffmpeg 실행
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
            "-c:v", "copy", "-c:a", "aac", output_filename
        ], check=True)

        # 임시 파일 삭제
        if os.path.exists(concat_list):
            os.remove(concat_list)

        logger.info(f"[최종 영상 합성] {output_filename} 생성 완료")
        return output_filename

    except Exception as e:
        logger.error(f"[영상 합성 오류] {e}")
        return None

# ====================================
# 전체 파이프라인 실행
# ====================================


def create_article(content, title):
    """기사 내용으로부터 영상 생성 파이프라인 실행"""
    # 초기화 - 임시 폴더 정리
    cleanup_temp_files()

    # 1. 시나리오 생성
    scenario_obj = generate_scenario(content, title)
    if not scenario_obj or "scenes" not in scenario_obj:
        logger.error("시나리오 생성 실패")
        return None, None

    overall_title = scenario_obj["title"]
    scenes = scenario_obj['scenes']

    # 2. 각 씬별 이미지 생성
    scene_images = []
    successful_images = []

    for scene in scenes:
        scene_id = scene["scene"]
        dialogue = scene["dialogue"]

        image_path = generate_image(dialogue, scene_id, successful_images)
        if image_path:
            scene_images.append((scene_id, image_path))
            if image_path not in successful_images:
                successful_images.append(image_path)
        else:
            logger.warning(f"씬 {scene_id}의 이미지 생성 실패 및 대체 이미지도 없음")

    # 3. 썸네일 이미지 생성
    thumbnail_path = None
    if scene_images:
        # 첫 번째 씬 ID 찾기 (가능한 scene 1 사용, 없으면 첫 번째 가용 이미지)
        first_scene_id = next(
            (scene_id for scene_id, _ in scene_images if scene_id == 1), None)
        if not first_scene_id and scene_images:
            first_scene_id = scene_images[0][0]  # 첫 번째 항목의 scene_id

        # 해당 씬의 이미지 경로 설정
        if first_scene_id:
            first_scene = next(
                (img for id, img in scene_images if id == first_scene_id), None)
            if first_scene:
                # 오버레이 이미지 생성
                first_overlay_path = get_temp_filepath("thumbnail_overlay.png")
                if overlay_title_on_image(first_scene, overall_title, first_overlay_path):
                    # 생성된 오버레이 이미지를 썸네일로 사용
                    thumbnail_path = os.path.join(OUTPUT_DIR, "thumbnail.png")
                    try:
                        # 오버레이 이미지를 썸네일 경로로 복사
                        shutil.copy(first_overlay_path, thumbnail_path)
                        logger.info(f"썸네일 이미지 저장 완료: {thumbnail_path}")
                    except Exception as e:
                        logger.error(f"썸네일 복사 중 오류: {e}")
                        thumbnail_path = None
                else:
                    logger.error("썸네일 오버레이 생성 실패")
                    # 실패 시에만 thumbnail_path를 None으로 설정 (중복된 None 할당 제거)

    # 4. 각 씬별 영상 클립 생성
    video_clips = []
    for scene_id, image_path in scene_images:
        scene_data = next((s for s in scenes if s["scene"] == scene_id), None)
        if not scene_data:
            continue

        dialogue = scene_data["dialogue"]

        # 오버레이 이미지 생성
        overlay_img_path = get_temp_filepath(f"scene_{scene_id}_overlay.png")
        if not overlay_title_on_image(image_path, overall_title, overlay_img_path):
            continue

        audio_path = get_temp_filepath(f"scene_{scene_id}_fast.mp3")
        if not generate_fast_tts(dialogue, audio_path, speed=1.25):
            continue

        # 비디오 클립 생성
        output_video = get_temp_filepath(f"scene_{scene_id}.mp4")
        video_clip = create_video_clip(
            overlay_img_path, audio_path, output_video)
        if video_clip:
            video_clips.append(video_clip)
        else:
            logger.warning(f"씬 {scene_id}의 영상 클립 생성 실패")

    # 5. 모든 클립을 하나의 영상으로 합성
    final_video_path = None
    if video_clips:
        final_video_path = os.path.join(OUTPUT_DIR, "final_video.mp4")
        concatenate_video_clips(video_clips, final_video_path)
        logger.info(f"최종 영상 생성 완료: {final_video_path}")
    else:
        logger.error("영상 클립 생성 실패")

    # 6. 정리 작업
    cleanup_temp_files()

    return final_video_path, thumbnail_path
