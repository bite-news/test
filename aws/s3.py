import boto3
from config import logger, config

# AWS config: 환경변수에서 읽어온 값 사용
AWS_ACCESS_KEY = config["AWS_ACCESS_KEY_ID"]
AWS_SECRET_KEY = config["AWS_SECRET_ACCESS_KEY"]
AWS_REGION_NAME = config["AWS_REGION"]
AWS_BUCKET_NAME = config["AWS_BUCKET_NAME"]

# S3 Client 생성
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION_NAME
)

# ✅ S3 업로드 함수
def upload_to_s3(file_path: str, s3_key: str, content_type: str) -> str:
    """
    파일을 S3에 업로드하고 URL을 반환하는 함수

    :param file_path: 로컬 파일 경로
    :param s3_key: S3 내 저장될 파일 경로
    :param content_type: 파일 MIME 타입 (예: "image/png", "video/mp4")
    :return: S3에 업로드된 파일의 URL
    """
    try:
        with open(file_path, "rb") as file_data:
            s3_client.upload_fileobj(
                file_data,
                AWS_BUCKET_NAME,
                s3_key,
                ExtraArgs={"ContentType": content_type}
            )
        file_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION_NAME}.amazonaws.com/{s3_key}"
        logger.info(f"✅ S3 업로드 완료: {file_url}")
        return file_url
    except Exception as e:
        logger.error(f"❌ S3 업로드 실패: {e}")
        raise Exception(f"S3 업로드 오류: {e}")
