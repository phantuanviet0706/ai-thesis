import os

# Project root — one level up from utils/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_file_contents(file_path: str) -> str:
    """
    @desc Đọc nội dung file văn bản theo đường dẫn tương đối so với thư mục gốc của dự án
    @params file_path (str): Đường dẫn tương đối tính từ thư mục gốc dự án (ví dụ: resources/prompt/kr_agent.md)
    @return str: Nội dung file đã được đọc và loại bỏ khoảng trắng đầu cuối
    """
    abs_path = os.path.join(BASE_DIR, file_path)
    with open(abs_path, "r", encoding="utf-8") as f:
        return f.read().strip()