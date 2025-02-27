import os
import logging

# 환경변수에서 직접 값 읽기
config = {
    "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID"),
    "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY"),
    "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
    "AWS_BUCKET_NAME": os.environ.get("AWS_BUCKET_NAME"),
    "AWS_REGION": os.environ.get("AWS_REGION"),
    "RDS_DATABASE": os.environ.get("RDS_DATABASE"),
    "RDS_HOST": os.environ.get("RDS_HOST"),
    "RDS_PASSWORD": os.environ.get("RDS_PASSWORD"),
    "RDS_PORT": os.environ.get("RDS_PORT"),
    "RDS_USER": os.environ.get("RDS_USER"),
}

# 필수 환경변수가 누락된 경우 예외 처리
required_keys = [
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "OPENAI_API_KEY",
    "AWS_BUCKET_NAME", "AWS_REGION", "RDS_DATABASE", "RDS_HOST",
    "RDS_PASSWORD", "RDS_PORT", "RDS_USER"
]
missing = [key for key in required_keys if config.get(key) is None]
if missing:
    raise EnvironmentError(f"다음 환경변수가 설정되지 않았습니다: {', '.join(missing)}")

# 로그 설정
log_format = '%(levelname)s: %(asctime)s - %(name)s - %(message)s'
logger = logging.getLogger('main-logger')
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter(log_format)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

logger.info("환경변수로부터 설정값을 성공적으로 불러왔습니다.")

