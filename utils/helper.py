import json
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


def extract_json(text: str) -> dict:
    """
    @desc Trích xuất JSON từ phản hồi LLM, xử lý cả khi bị bọc trong markdown code fence
    @params text (str): Chuỗi văn bản phản hồi từ LLM, có thể chứa ```json ... ``` hoặc JSON thuần
    @return dict: Dictionary đã được parse từ JSON
    """
    text = text.strip()
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    return json.loads(text)
