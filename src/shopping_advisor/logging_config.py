import logging
import logging.handlers
from pathlib import Path

def setup_logging(log_dir: str = "logs", log_level: str = "INFO"):
    """로깅 설정을 초기화합니다.
    
    Args:
        log_dir (str): 로그 파일을 저장할 디렉토리
        log_level (str): 로깅 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # 로그 디렉토리 생성
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # 로거 설정
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 포맷터 정의
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 1. 콘솔 핸들러 (INFO 이상만 출력)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 2. 파일 핸들러 - 전체 로그 (RotatingFileHandler 사용)
    file_handler = logging.handlers.RotatingFileHandler(
        log_path / "shopping_advisor.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,  # 최대 5개 백업 파일 유지
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 3. 에러 전용 파일 핸들러
    error_handler = logging.handlers.RotatingFileHandler(
        log_path / "error.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    logger.info("로깅 시스템 초기화 완료")