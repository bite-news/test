import logging
import yaml

# 설정 파일 경로
config_file = 'bitenews.yml'

# 설정 파일 로드
def load_config(file_path):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config
config = load_config(config_file)

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