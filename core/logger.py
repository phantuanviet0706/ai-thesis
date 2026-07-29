import logging
import sys
import time
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class _SafeTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    TimedRotatingFileHandler chuẩn của Python gọi os.rename() lúc rotate — trên Windows, rename
    một file đang bị process KHÁC giữ mở sẽ raise PermissionError (khác POSIX, cho phép rename
    file đang mở). Codebase này có nhiều process cùng ghi vào chung logs/app.log và logs/errors/
    error.log (server đang chạy + các script chạy riêng như scripts/seed_vectordb.py, hoặc nhiều
    worker) nên tình huống này xảy ra thật. logging tự nuốt exception (không crash app) nhưng làm
    mất đúng log record gây rotation, và bỏ dở giữa chừng khiến self.stream=None — mọi log gọi
    sau đó im lặng lỗi cho tới khi rotate thành công.

    Override: thử lại vài lần (lock từ process khác thường tự giải phóng rất nhanh); nếu vẫn thất
    bại thì đảm bảo stream được mở lại (ghi tiếp vào file cũ, bỏ qua rotate lần này) thay vì mất
    hẳn khả năng logging, và hoãn lần thử rotate tiếp theo ~60s thay vì retry ngay trên MỌI log
    call kế tiếp (tránh làm chậm ứng dụng nếu file bị khóa lâu).
    """
    _ROLLOVER_RETRIES = 3
    _ROLLOVER_RETRY_DELAY = 0.5
    _ROLLOVER_DEFER_SECONDS = 60

    def doRollover(self) -> None:
        last_exc: Exception | None = None
        for _ in range(self._ROLLOVER_RETRIES):
            try:
                super().doRollover()
                return
            except PermissionError as exc:
                last_exc = exc
                time.sleep(self._ROLLOVER_RETRY_DELAY)

        if self.stream is None:
            self.stream = self._open()
        self.rolloverAt = int(time.time()) + self._ROLLOVER_DEFER_SECONDS
        print(
            f"[Logger] Rotation của '{self.baseFilename}' bị khóa bởi process khác, "
            f"tạm bỏ qua và thử lại sau {self._ROLLOVER_DEFER_SECONDS}s | error={last_exc}",
            file=sys.stderr,
        )


def setup_logger():
    """
    @desc Khởi tạo và cấu hình logger toàn cục cho ứng dụng với handler ghi file theo ngày và hiển thị console
    @return logging.Logger: Instance logger đã được cấu hình với file handler xoay vòng hàng ngày và console handler
    """
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
    file_handler = _SafeTimedRotatingFileHandler(
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

    # Handler riêng chỉ ghi log mức ERROR trở lên vào logs/errors/, xoay vòng theo ngày (cùng
    # cơ chế suffix như file_handler ở trên — file đang ghi tên "error.log", sau 00:00 được đổi
    # tên thành "error.log.YYYY-MM-DD" và bắt đầu file mới cho ngày kế tiếp, nên mỗi ngày luôn
    # có đúng 1 file log lỗi riêng). Gắn vào CÙNG logger "ai_chatbot" (không tạo logger mới) nên
    # mọi custom_logger.error(...)/critical(...) đã có sẵn trong codebase (orchestrator, synth
    # agent, chat_service, global_exception_handler, v.v.) tự động được ghi thêm vào đây —
    # không cần sửa lại từng call site. exc_info=True ở các lệnh gọi hiện có vẫn giữ nguyên full
    # traceback vì Formatter tự render exc_info của LogRecord cho mọi handler, không riêng gì
    # console/app.log.
    error_log_dir = log_dir / "errors"
    error_log_dir.mkdir(parents=True, exist_ok=True)
    error_handler = _SafeTimedRotatingFileHandler(
        filename=str(error_log_dir / "error.log"),
        when="midnight",
        interval=1,
        backupCount=90,  # giữ log lỗi lâu hơn app.log (30 ngày) để tiện điều tra về sau
        encoding="utf-8"
    )
    error_handler.suffix = "%Y-%m-%d"
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # Add các handler vào logger
    if not logger.handlers:  # Tránh việc add trùng handler nếu gọi setup nhiều lần
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.addHandler(error_handler)

    return logger

custom_logger = setup_logger()