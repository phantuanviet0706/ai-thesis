import os

# Project root — one level up from utils/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_file_contents(file_path: str) -> str:
    """Read a file relative to the project root directory."""
    abs_path = os.path.join(BASE_DIR, file_path)
    with open(abs_path, "r", encoding="utf-8") as f:
        return f.read().strip()