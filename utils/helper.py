import json
import os
import re

# Project root — one level up from utils/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ưu tiên khớp "pronoun + động từ ngôi thứ nhất" trước (độ chính xác cao hơn — tránh nhầm
# pronoun dùng để GỌI người khác), fallback sang "pronoun ở đầu câu" nếu không khớp mẫu trên.
_SELF_REF_WITH_VERB_RE = re.compile(
    r"\b(anh|chị|em|mình|tôi|tui|bạn)\s+"
    r"(muốn|cần|thích|hỏi|lấy|mua|xem|đặt|order|chưa|đang|sẽ|nghĩ|thấy|định|có thể|xin)\b",
    re.IGNORECASE,
)
_SELF_REF_LEADING_RE = re.compile(r"^\s*(anh|chị|em|mình|tôi|tui|bạn)\b", re.IGNORECASE)


def _detect_customer_pronoun(messages: list) -> str | None:
    """
    @desc Quét ngược từ tin nhắn gần nhất của khách để tìm đại từ khách tự xưng cho bản thân
    (không phải đại từ gọi người khác) — lấy tín hiệu MỚI NHẤT vì khách có thể đổi giọng văn
    giữa cuộc hội thoại.
    @params messages (list): Danh sách BaseMessage của toàn bộ hội thoại
    @return str | None: Đúng từ khách dùng ("anh"/"chị"/"em"/"mình"/"tôi"/"tui"/"bạn"), hoặc None nếu chưa rõ
    """
    for msg in reversed(messages):
        if getattr(msg, "type", "") != "human":
            continue
        text = (msg.content or "").strip()
        m = _SELF_REF_WITH_VERB_RE.search(text)
        if m:
            return m.group(1).lower()
        m = _SELF_REF_LEADING_RE.match(text)
        if m:
            return m.group(1).lower()
    return None


def resolve_address_style(messages: list) -> str:
    """
    @desc Xác định cặp xưng hô (bot tự xưng gì, gọi khách là gì) dựa trên đại từ khách VỪA dùng
    để tự xưng cho bản thân — để Synth Agent phản chiếu đúng thay vì tự đoán chung chung, theo
    yêu cầu: khách xưng "anh/chị" -> bot xưng "em"; khách xưng "bạn" -> bot xưng "mình"; khách
    xưng "em" -> bot xưng "mình" (không xưng "anh/chị" lại, tránh lệch vai vế).
    @params messages (list): Danh sách BaseMessage của toàn bộ hội thoại
    @return str: Dòng hướng dẫn xưng hô cụ thể để chèn thẳng vào prompt Synth Agent
    """
    pronoun = _detect_customer_pronoun(messages)

    if pronoun in ("anh", "chị"):
        return f"Khách tự xưng '{pronoun}' → BẠN xưng 'em', gọi khách là '{pronoun}' (giữ nguyên)."
    if pronoun == "em":
        return "Khách tự xưng 'em' → BẠN xưng 'mình' (KHÔNG xưng 'anh/chị' lại), gọi khách là 'bạn'."
    if pronoun in ("bạn", "mình", "tôi", "tui"):
        return "Khách tự xưng theo giọng thân mật → BẠN xưng 'mình', gọi khách là 'bạn'."
    return "Chưa rõ khách tự xưng gì — dùng mặc định: BẠN xưng 'em', gọi khách là 'anh/chị'."


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


def format_customer_profile(extracted_info: dict | None) -> str:
    """
    @desc Định dạng hồ sơ khách hàng đã tích lũy (extracted_info.preferences + thông tin định danh)
    thành 1 dòng văn bản ngắn gọn để đưa vào prompt của KR Agent / Synth Agent. Dùng chung cho cả hai
    vì extracted_info giờ được merge tích lũy qua nhiều lượt (xem graph/state.py::_merge_extracted_info),
    nên ngay cả khi lượt hiện tại khách không nhắc lại mệnh/ngân sách, agent vẫn cần biết để cá nhân hóa.
    @params extracted_info (dict | None): Giá trị extracted_info tích lũy từ ConversationState
    @return str: Chuỗi mô tả hồ sơ khách hàng, hoặc chuỗi rỗng nếu chưa biết gì
    """
    if not extracted_info:
        return ""

    prefs = extracted_info.get("preferences") or {}
    parts: list[str] = []

    if prefs.get("phong_thuy_menh"):
        parts.append(f"Mệnh {prefs['phong_thuy_menh']}")
    if extracted_info.get("zodiac_sign"):
        parts.append(f"Cung {extracted_info['zodiac_sign']}")
    if prefs.get("budget"):
        try:
            parts.append(f"Ngân sách ~{float(prefs['budget']):,.0f}₫")
        except (TypeError, ValueError):
            pass
    if prefs.get("material"):
        parts.append(f"Chất liệu ưa thích: {prefs['material']}")
    if prefs.get("color"):
        parts.append(f"Màu ưa thích: {prefs['color']}")
    if prefs.get("style"):
        parts.append(f"Phong cách ưa thích: {prefs['style']}")
    if prefs.get("occasion"):
        parts.append(f"Dịp mua: {prefs['occasion']}")

    if not parts:
        return ""
    return "Hồ sơ khách hàng đã biết (tích lũy qua các lượt trước): " + " | ".join(parts)
