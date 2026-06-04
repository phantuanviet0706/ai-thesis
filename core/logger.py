import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def setup_logger():
    log_dir = BASE_DIR / "logs"

    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("ai_chatbot")
    logger.setLevel(logging.INFO)

    # Format log chuẩn: Thời gian - Level - [File:Dòng] - Nội dung
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )

    # Đường dẫn file log cụ thể
    log_file = log_dir / "app.log"

    # Cấu hình xoay vòng file theo ngày (TimedRotatingFileHandler)
    file_handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",  # Chốt file vào 00:00 hàng ngày
        interval=1,
        backupCount=30,  # Giữ log 30 ngày gần nhất
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    # Hậu tố của file khi xoay vòng (ví dụ: app.log.2026-03-31)
    file_handler.suffix = "%Y-%m-%d"

    # Handler để in ra màn hình Terminal (Console)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add các handler vào logger
    if not logger.handlers:  # Tránh việc add trùng handler nếu gọi setup nhiều lần
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

custom_logger = setup_logger()