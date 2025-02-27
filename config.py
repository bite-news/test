import logging
import yaml
import os

# 설정 파일 경로
config_file = 'bitenews.yml'

# 설정 파일 로드
def load_config(file_path):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

# 환경변수에서 시크릿 값 불러오기 (없으면 설정 파일에서 가져오기)
config = load_config(config_file)
config["AWS_ACCESS_KEY_ID"] = os.environ.get("AWS_ACCESS_KEY_ID", config.get("AWS_ACCESS_KEY_ID"))
config["AWS_SECRET_ACCESS_KEY"] = os.environ.get("AWS_SECRET_ACCESS_KEY", config.get("AWS_SECRET_ACCESS_KEY"))
config["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", config.get("OPENAI_API_KEY"))

# 로그 설정
log_format = '%(levelname)s: %(asctime)s - %(name)s - %(message)s'
logger = logging.getLogger('main-logger')
logger.setLevel(logging.INFO)

# 콘솔 핸들러 설정
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO) 

# 포맷터 설정
formatter = logging.Formatter(log_format)
console_handler.setFormatter(formatter)

# 핸들러 추가
logger.addHandler(console_handler)

logger.info("Configuration loaded successfully.")
