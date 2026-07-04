"""
generate_seed_data.py — Sinh thêm dữ liệu mẫu cho resources/migrate/seed.sql sao cho
mỗi bảng có ÍT NHẤT 50 bản ghi, đồng thời GIỮ NGUYÊN toàn bộ dữ liệu curated hiện có
(12 sản phẩm, 12 user... đã viết tay) — chỉ nối thêm 1 khối INSERT mới ngay sau khối
gốc của từng bảng trong seed.sql, tiếp nối ID từ giá trị lớn nhất hiện tại.

Cách chạy:
    python scripts/generate_seed_data.py            # ghi đè resources/migrate/seed.sql
    python scripts/generate_seed_data.py --check     # chỉ generate + validate trên DB tạm, không ghi file

Toàn bộ quan hệ khóa ngoại được track thủ công trong Python (không dựa vào MySQL báo lỗi)
để đảm bảo dữ liệu sinh ra luôn tham chiếu đúng ID đã tồn tại.
"""

import argparse
import json
import random
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RNG_SEED = 42
random.seed(RNG_SEED)

SEED_SQL_PATH = Path(__file__).resolve().parent.parent / "resources" / "migrate" / "seed.sql"


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def esc(s) -> str:
    """Escape 1 giá trị Python thành literal SQL an toàn (str/None/bool/số/JSON dict)."""
    if s is None:
        return "NULL"
    if isinstance(s, bool):
        return "TRUE" if s else "FALSE"
    if isinstance(s, (int, float)):
        return str(s)
    if isinstance(s, dict) or isinstance(s, list):
        return "'" + json.dumps(s, ensure_ascii=False).replace("'", "''") + "'"
    return "'" + str(s).replace("'", "''") + "'"


def row(values) -> str:
    return "(" + ", ".join(esc(v) for v in values) + ")"


def insert_stmt(table: str, columns: list[str], rows: list[list]) -> str:
    cols = ", ".join(columns)
    values_sql = ",\n".join(row(r) for r in rows)
    return f"INSERT INTO {table} ({cols}) VALUES\n{values_sql};\n"


def rand_dt(start: datetime, end: datetime) -> datetime:
    delta = end - start
    seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=seconds)


def dt_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


BASE_START = datetime(2026, 1, 5)
BASE_END = datetime(2026, 7, 4)

# ------------------------------------------------------------------
# Vietnamese name / text data pools
# ------------------------------------------------------------------

SURNAMES = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng",
            "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý", "Đinh", "Trương", "Lâm", "Mai"]
MIDDLE_MALE = ["Văn", "Minh", "Hữu", "Đức", "Quang", "Thành", "Anh", "Công", "Bá", "Xuân"]
MIDDLE_FEMALE = ["Thị", "Ngọc", "Thanh", "Thu", "Kim", "Hồng", "Diệu", "Bích", "Minh", "Thùy"]
GIVEN_MALE = ["Nam", "Tuấn", "Hùng", "Dũng", "Long", "Khoa", "Bình", "Đức", "Sơn", "Phong",
              "Đạt", "Huy", "Việt", "Quân", "Thắng", "Kiên", "Phúc", "Tài", "Đăng", "Vinh"]
GIVEN_FEMALE = ["Lan", "Hoa", "Mai", "Linh", "Thu", "Hương", "Ngọc", "Trang", "Nhung", "Yến",
                "Hằng", "Nga", "Vy", "Chi", "Anh", "Thảo", "Huyền", "My", "Ly", "Xuân"]
ZODIAC_SIGNS = ["Bạch Dương", "Kim Ngưu", "Song Tử", "Cự Giải", "Sư Tử", "Xử Nữ",
                "Thiên Bình", "Bọ Cạp", "Nhân Mã", "Ma Kết", "Bảo Bình", "Song Ngư"]
PROVINCES = [
    ("Phường Bến Thành", "Quận 1", "TP. Hồ Chí Minh"),
    ("Phường Đa Kao", "Quận 1", "TP. Hồ Chí Minh"),
    ("Phường An Phú", "Thành phố Thủ Đức", "TP. Hồ Chí Minh"),
    ("Phường Hội An", "Quận Hải Châu", "Đà Nẵng"),
    ("Phường Thạch Thang", "Quận Hải Châu", "Đà Nẵng"),
    ("Phường Phú Hội", "Thành phố Huế", "Thừa Thiên Huế"),
    ("Phường An Hòa", "Quận Ninh Kiều", "Cần Thơ"),
    ("Phường 1", "Quận Phú Nhuận", "TP. Hồ Chí Minh"),
    ("Phường 6", "Quận 3", "TP. Hồ Chí Minh"),
    ("Phường Trần Phú", "Thành phố Nha Trang", "Khánh Hòa"),
    ("Phường Vĩnh Trại", "Thành phố Lạng Sơn", "Lạng Sơn"),
    ("Phường Yên Đỗ", "Thành phố Pleiku", "Gia Lai"),
    ("Phường Cửa Nam", "Quận Hoàn Kiếm", "Hà Nội"),
    ("Phường Dịch Vọng", "Quận Cầu Giấy", "Hà Nội"),
    ("Phường Việt Hưng", "Quận Long Biên", "Hà Nội"),
]
STREETS = ["Nguyễn Trãi", "Lê Lợi", "Trần Hưng Đạo", "Hoàng Diệu", "Bạch Đằng",
           "Điện Biên Phủ", "Nguyễn Văn Cừ", "Lạc Long Quân", "Nguyễn Đình Chiểu",
           "Phan Đình Phùng", "Võ Văn Tần", "Cách Mạng Tháng Tám", "Nguyễn Huệ",
           "Lý Thường Kiệt", "Trần Phú", "Hai Bà Trưng", "Phan Chu Trinh", "Trường Chinh"]

MATERIALS = [
    ("đá mắt hổ vàng", "Kim, Thổ", "Nam Phi"),
    ("thạch anh tím", "Thủy, Mộc", "Brazil"),
    ("mã não đỏ", "Hỏa", "Việt Nam"),
    ("ngọc bích xanh", "Mộc, Thủy", "Myanmar"),
    ("thạch anh hồng", "Kim, Thổ", "Brazil"),
    ("obsidian đen", "Thủy", "Mexico"),
    ("lapis lazuli", "Thủy", "Afghanistan"),
    ("ngọc trai Akoya", "Thủy", "Nhật Bản"),
    ("thạch anh vàng citrine", "Thổ, Kim", "Brazil"),
    ("aquamarine xanh biển", "Thủy", "Brazil"),
    ("garnet đỏ", "Hỏa", "Ấn Độ"),
    ("turquoise ngọc lam", "Mộc, Thủy", "Iran"),
    ("moonstone đá mặt trăng", "Thủy", "Sri Lanka"),
    ("amazonite xanh ngọc", "Mộc", "Brazil"),
    ("sapphire xanh", "Thủy, Kim", "Sri Lanka"),
    ("ruby đỏ", "Hỏa", "Myanmar"),
    ("hổ phách amber", "Thổ", "Việt Nam"),
    ("san hô đỏ", "Hỏa", "Địa Trung Hải"),
    ("đá thạch anh khói", "Thổ", "Brazil"),
    ("mã não trắng", "Kim", "Việt Nam"),
    ("ngọc trai nước ngọt", "Thủy", "Trung Quốc"),
    ("đá aventurine xanh lá", "Mộc", "Ấn Độ"),
    ("đá sodalite xanh dương", "Thủy", "Brazil"),
    ("đá rhodonite hồng", "Hỏa, Thổ", "Nga"),
    ("đá labradorite", "Thủy", "Madagascar"),
    ("vàng 18K", "Kim, Thổ", "Việt Nam"),
    ("bạc 925", "Kim", "Việt Nam"),
    ("bạch kim", "Kim", "Nam Phi"),
]

JEWELRY_TYPES = [
    ("Vòng Tay", "VT", [4, 34, 35]),
    ("Nhẫn", "NH", [5, 36, 37]),
    ("Dây Chuyền", "DC", [6, 38, 39]),
    ("Hoa Tai", "HT", [7, 40, 41]),
    ("Lắc Tay", "LT", [8, 42, 43]),
    ("Trâm Cài", "TC", [13]),
    ("Charm Phong Thủy", "CM", [14]),
    ("Tỳ Hưu", "TH", [11, 47, 48]),
    ("Tượng Phật & Quan Âm", "PQ", [12, 49, 50]),
]

STYLE_ADJ = ["Cao Cấp", "Thanh Lịch", "Sang Trọng", "Tinh Xảo", "Độc Đáo", "Hiện Đại",
             "Cổ Điển", "Tối Giản", "Quý Phái", "Đặc Biệt"]

CONCERN_TEMPLATES = [
    "Lo ngại về giá — vượt ngân sách dự kiến",
    "Chưa chắc chắn về chất lượng đá thật hay nhân tạo",
    "Phân vân giữa 2 mẫu sản phẩm khác nhau",
    "Cần thêm thời gian suy nghĩ trước khi quyết định",
    "Muốn hỏi ý kiến người thân trước khi mua",
    "Băn khoăn về chính sách đổi trả",
    None,
]

CONSULT_STRATEGIES = [
    "direct_recommendation", "education_first", "reassurance_building",
    "gift_framing", "premium_showcase", "upsell_premium", "soft_recommendation",
]

USER_MESSAGE_TEMPLATES = [
    "Xin chào, tôi sinh năm {year}, mệnh {element}. Tôi muốn tìm {jewelry} phong thủy hợp mệnh.",
    "Cho hỏi bên shop có {jewelry} nào tầm {budget} không ạ?",
    "Tôi muốn mua {jewelry} tặng {occasion}, ngân sách khoảng {budget}.",
    "Mệnh {element} nên đeo đá gì thì hợp vậy shop?",
    "Sản phẩm {jewelry} này giá bao nhiêu vậy ạ, có giảm giá không?",
]
ASSISTANT_MESSAGE_TEMPLATES = [
    "Dạ chào anh/chị! Với mệnh {element}, em gợi ý {jewelry} rất phù hợp, giá khoảng {budget}. Anh/chị có muốn xem thêm chi tiết không ạ?",
    "Với ngân sách {budget}, bên em có vài mẫu {jewelry} rất đẹp và hợp mệnh {element}. Để em gửi thông tin chi tiết nhé!",
    "Dạ sản phẩm này đang có giá ưu đãi, rất hợp cho {occasion}. Anh/chị có cần tư vấn thêm về ý nghĩa phong thủy không ạ?",
]
OCCASIONS = ["sinh nhật", "kỷ niệm ngày cưới", "tân gia", "khai trương", "bản thân", "người yêu", "mẹ", "bố"]
ELEMENTS = ["Kim", "Mộc", "Thủy", "Hỏa", "Thổ"]
BUDGETS = ["300-500k", "500k-1 triệu", "1-3 triệu", "3-5 triệu", "5-10 triệu", "trên 10 triệu"]

REVIEW_TITLES = [
    "Rất hài lòng với sản phẩm", "Chất lượng tuyệt vời", "Đẹp hơn mong đợi",
    "Giao hàng nhanh, đóng gói cẩn thận", "Đáng đồng tiền bát gạo", "Sẽ ủng hộ tiếp",
    "Sản phẩm ổn nhưng giao hơi chậm", "Đẹp, đúng như mô tả",
]
REVIEW_BODY_TEMPLATES = [
    "Sản phẩm {material} rất đẹp, đúng như hình. Đóng gói cẩn thận, giao hàng nhanh. Sẽ ủng hộ shop tiếp!",
    "Chất lượng {material} tốt, màu sắc tự nhiên. Nhân viên tư vấn nhiệt tình về ý nghĩa phong thủy phù hợp mệnh của mình.",
    "Mua tặng người thân, ai cũng khen đẹp. Chatbot AI tư vấn rất chính xác theo mệnh và tuổi.",
    "Sản phẩm ổn, đúng mô tả. Chỉ tiếc giao hàng chậm hơn dự kiến 1-2 ngày.",
    "Rất ưng ý với {material}, cảm giác đeo vào thấy tự tin và may mắn hơn hẳn.",
]

SYSTEM_CONFIG_EXTRA = [
    ("security.jwt.access_ttl_minutes", "120", "integer", "Thời gian sống access token (phút)"),
    ("security.jwt.refresh_ttl_days", "7", "integer", "Thời gian sống refresh token (ngày)"),
    ("notification.email.enabled", "true", "boolean", "Bật/tắt gửi email thông báo đơn hàng"),
    ("notification.sms.enabled", "false", "boolean", "Bật/tắt gửi SMS thông báo đơn hàng"),
    ("logging.level", "INFO", "string", "Mức log mặc định toàn hệ thống"),
    ("cache.product_list.ttl_seconds", "300", "integer", "TTL cache danh sách sản phẩm"),
    ("marketing.banner.homepage", "sale_summer_2026", "string", "Banner khuyến mãi trang chủ hiện tại"),
    ("marketing.newsletter.enabled", "true", "boolean", "Bật/tắt đăng ký nhận bản tin"),
    ("retrieval.top_k_initial", "20", "integer", "Số candidate ban đầu cho BM25 re-rank"),
    ("retrieval.mmr_lambda", "0.7", "float", "Hệ số MMR cân bằng relevance/diversity"),
    ("retrieval.lambda_dense", "0.5", "float", "Trọng số dense retrieval trong hybrid search"),
    ("retrieval.lambda_sparse", "0.3", "float", "Trọng số BM25 sparse trong hybrid search"),
    ("retrieval.lambda_meta", "0.2", "float", "Trọng số metadata filter trong hybrid search"),
    ("psych.confidence_threshold", "0.6", "float", "Ngưỡng confidence đủ tin cậy của Psych Agent"),
    ("orchestrator.max_iterations", "8", "integer", "Số vòng lặp tối đa của Orchestrator trong 1 lượt"),
    ("kafka.consumer_group", "pancharm-mas", "string", "Kafka consumer group ID"),
    ("kafka.enabled", "true", "boolean", "Bật/tắt tích hợp Kafka cho bot messaging"),
    ("telegram.webhook.enabled", "true", "boolean", "Bật/tắt webhook Telegram"),
    ("zalo.webhook.enabled", "false", "boolean", "Bật/tắt webhook Zalo OA"),
    ("messenger.webhook.enabled", "false", "boolean", "Bật/tắt webhook Facebook Messenger"),
    ("order.auto_cancel_hours", "48", "integer", "Số giờ tự động huỷ đơn chưa thanh toán"),
    ("order.min_order_amount", "100000", "integer", "Giá trị đơn hàng tối thiểu (VND)"),
    ("review.auto_publish", "false", "boolean", "Tự động publish review mới không cần duyệt"),
    ("review.min_rating_alert", "2", "integer", "Ngưỡng rating thấp cần cảnh báo nhân viên"),
    ("chatbot.typing_delay_ms", "800", "integer", "Độ trễ giả lập typing indicator (ms)"),
    ("chatbot.max_message_length", "2000", "integer", "Độ dài tối đa 1 tin nhắn người dùng"),
    ("vector_db.embedding_model", "paraphrase-multilingual-MiniLM-L12-v2", "string", "Model embedding local cho ChromaDB"),
    ("vector_db.embedding_dims", "384", "integer", "Số chiều vector embedding"),
    ("analytics.retention_days", "365", "integer", "Số ngày lưu trữ dữ liệu phân tích hội thoại"),
    ("backup.schedule_cron", "0 2 * * *", "string", "Lịch backup DB tự động (cron expression)"),
]


def vn_name(gender: str) -> tuple[str, str]:
    """Trả về (họ tên đầy đủ, giới tính) theo cấu trúc Họ + Tên đệm + Tên."""
    surname = random.choice(SURNAMES)
    if gender == "male":
        middle = random.choice(MIDDLE_MALE)
        given = random.choice(GIVEN_MALE)
    else:
        middle = random.choice(MIDDLE_FEMALE)
        given = random.choice(GIVEN_FEMALE)
    return f"{surname} {middle} {given}"


_VN_FOLD_MAP = {
    "à": "a", "á": "a", "ả": "a", "ã": "a", "ạ": "a", "ă": "a", "ằ": "a", "ắ": "a", "ẳ": "a", "ẵ": "a", "ặ": "a",
    "â": "a", "ầ": "a", "ấ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
    "è": "e", "é": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e", "ê": "e", "ề": "e", "ế": "e", "ể": "e", "ễ": "e", "ệ": "e",
    "ì": "i", "í": "i", "ỉ": "i", "ĩ": "i", "ị": "i",
    "ò": "o", "ó": "o", "ỏ": "o", "õ": "o", "ọ": "o", "ô": "o", "ồ": "o", "ố": "o", "ổ": "o", "ỗ": "o", "ộ": "o",
    "ơ": "o", "ờ": "o", "ớ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
    "ù": "u", "ú": "u", "ủ": "u", "ũ": "u", "ụ": "u", "ư": "u", "ừ": "u", "ứ": "u", "ử": "u", "ữ": "u", "ự": "u",
    "ỳ": "y", "ý": "y", "ỷ": "y", "ỹ": "y", "ỵ": "y",
    "đ": "d",
}


def ascii_fold(s: str) -> str:
    """
    Hạ chữ thường + bỏ dấu tiếng Việt — dùng để phát hiện trùng lặp dưới collation
    utf8mb4_0900_ai_ci (accent-insensitive) mặc định của MySQL 8. VD: "Tuổi Tý" và
    "Tuổi Tỵ" khác nghĩa (Tý=Chuột, Tỵ=Rắn) nhưng MySQL coi là TRÙNG vì "ý"/"ỵ" đều
    fold về "y" — nếu không check ở tầng Python, INSERT sẽ lỗi UNIQUE constraint.
    """
    s = s.lower()
    for k, v in _VN_FOLD_MAP.items():
        s = s.replace(k, v)
    return re.sub(r"[^a-z0-9\s]", "", s).strip()


def slugify(s: str, suffix: str = "") -> str:
    s = ascii_fold(s)
    s = re.sub(r"\s+", "-", s.strip())
    return f"{s}-{suffix}" if suffix else s


# ------------------------------------------------------------------
# Table generators — mỗi hàm trả về (columns, rows) cho phần MỞ RỘNG (không đụng data gốc)
# ------------------------------------------------------------------

def gen_brands(start_id: int, n: int):
    prefixes = ["Kim", "Ngọc", "Bảo", "Thiên", "Hoàng", "Phúc", "Lộc", "Tài", "An", "Vinh",
                "Đại", "Hồng", "Minh", "Gia", "Việt", "Á Đông", "Xuân", "Phượng", "Long", "Phát"]
    suffixes = ["Bảo Phong Thủy", "Jewelry", "Gems", "Craft", "Studio", "Kim Hoàn",
                "Trang Sức", "Phong Thủy", "Đá Quý", "Ngọc Việt"]
    rows, used = [], set()
    while len(rows) < n:
        name = f"{random.choice(prefixes)} {random.choice(suffixes)}"
        folded = ascii_fold(name)
        if folded in used:
            continue
        used.add(folded)
        bid = start_id + len(rows)
        slug = slugify(name)
        rows.append([
            bid, name, slug,
            f"https://cdn.pancharm.vn/brands/{slug}-logo.png",
            f"Thương hiệu {name.lower()} chuyên trang sức và vật phẩm phong thủy chất lượng cao.",
            True,
        ])
    cols = ["id", "name", "slug", "logo_url", "description", "is_active"]
    return cols, rows


def gen_tags(start_id: int, n: int):
    pool = [
        ("Mệnh Kim Bổ Sung", "feng_shui"), ("Mệnh Mộc Bổ Sung", "feng_shui"),
        ("Mệnh Thủy Bổ Sung", "feng_shui"), ("Mệnh Hỏa Bổ Sung", "feng_shui"),
        ("Mệnh Thổ Bổ Sung", "feng_shui"), ("Tuổi Tý", "feng_shui"), ("Tuổi Sửu", "feng_shui"),
        ("Tuổi Dần", "feng_shui"), ("Tuổi Mão", "feng_shui"), ("Tuổi Thìn", "feng_shui"),
        ("Tuổi Tỵ", "feng_shui"), ("Tuổi Ngọ", "feng_shui"), ("Tuổi Mùi", "feng_shui"),
        ("Tuổi Thân", "feng_shui"), ("Tuổi Dậu", "feng_shui"), ("Tuổi Tuất", "feng_shui"),
        ("Tuổi Hợi", "feng_shui"), ("Giảm Giá Sốc", "promo"), ("Flash Sale", "promo"),
        ("Combo Ưu Đãi", "promo"), ("Hàng Mới Về", "promo"), ("Khai Trương", "occasion"),
        ("Tân Gia", "occasion"), ("Tết Nguyên Đán", "occasion"), ("Valentine", "occasion"),
        ("Quà Tặng Sếp", "occasion"), ("Quà Tặng Đối Tác", "occasion"), ("Trâm Cài", "product"),
        ("Charm Phong Thủy", "product"), ("Lắc Chân", "product"), ("Trang Sức Nam", "product"),
        ("Trang Sức Nữ", "product"), ("Trang Sức Trẻ Em", "product"), ("Bộ Trang Sức", "product"),
        ("Vàng 18K", "style"), ("Bạc 925", "style"), ("Bạch Kim", "style"),
        ("Thiết Kế Tối Giản", "style"), ("Thiết Kế Cổ Điển", "style"), ("Thiết Kế Hiện Đại", "style"),
        ("Chứng Nhận GIA", "style"), ("Hàng Thủ Công", "style"), ("Cao Cấp", "style"),
    ]
    rows = []
    used_folded: set[str] = set()
    pool_idx = 0
    extra_round = 0
    while len(rows) < n:
        name, tag_type = pool[pool_idx % len(pool)]
        if pool_idx >= len(pool) * (extra_round + 1):
            extra_round += 1
        if extra_round > 0:
            name = f"{name} {extra_round + 1}"
        pool_idx += 1

        folded = ascii_fold(name)
        if folded in used_folded:
            # VD: "Tuổi Tý" và "Tuổi Tỵ" khác nghĩa nhưng fold trùng dưới collation
            # accent-insensitive của MySQL — bỏ qua để tránh lỗi UNIQUE constraint.
            continue
        used_folded.add(folded)

        tid = start_id + len(rows)
        rows.append([tid, name, slugify(name, str(tid)), tag_type])
    cols = ["id", "name", "slug", "tag_type"]
    return cols, rows


def gen_categories(start_id: int):
    """38 category mới: thêm nhánh depth1 dưới root cũ + root mới + depth2 leaf phong phú."""
    rows = []
    cid = start_id

    def add(name, parent_id, depth):
        nonlocal cid
        rows.append([cid, name, slugify(name, str(cid)),
                     f"Danh mục {name.lower()}", parent_id, depth, True])
        this_id = cid
        cid += 1
        return this_id

    add("Trâm Cài", 1, 1)                      # 13
    add("Charm Phong Thủy", 1, 1)               # 14
    add("Bộ Trang Sức Phong Thủy", 1, 1)        # 15
    add("Đá Thô Nguyên Khối", 2, 1)             # 16
    add("Đá Trụ Phong Thủy", 2, 1)              # 17
    add("Đá Cầu Phong Thủy", 2, 1)              # 18
    add("Tượng Thần Tài", 3, 1)                 # 19
    add("Vòng Tay Phật Bản Mệnh", 3, 1)         # 20
    add("Đồng Xu Phong Thủy", 3, 1)             # 21
    add("Tượng Di Lặc", 3, 1)                   # 22
    quatang = add("Quà Tặng Phong Thủy", None, 0)   # 23
    add("Quà Tặng Khai Trương", quatang, 1)     # 24
    add("Quà Tặng Tân Gia", quatang, 1)         # 25
    add("Quà Tặng Sinh Nhật Phong Thủy", quatang, 1)  # 26
    tsnam = add("Trang Sức Nam", None, 0)       # 27
    add("Vòng Tay Nam", tsnam, 1)               # 28
    add("Dây Chuyền Nam", tsnam, 1)             # 29
    add("Nhẫn Nam", tsnam, 1)                   # 30
    tstre = add("Trang Sức Trẻ Em", None, 0)    # 31
    add("Vòng Tay Trẻ Em", tstre, 1)            # 32
    add("Lắc Chân Trẻ Em", tstre, 1)            # 33
    add("Vòng Tay Nữ Cao Cấp", 4, 2)            # 34
    add("Vòng Tay Đôi", 4, 2)                   # 35
    add("Nhẫn Đôi Phong Thủy", 5, 2)            # 36
    add("Nhẫn Nữ Đá Quý", 5, 2)                 # 37
    add("Dây Chuyền Mặt Phật", 6, 2)            # 38
    add("Dây Chuyền Đá Quý Nữ", 6, 2)           # 39
    add("Bông Tai Ngọc Trai", 7, 2)             # 40
    add("Bông Tai Đá Quý", 7, 2)                # 41
    add("Lắc Tay Vàng", 8, 2)                   # 42
    add("Lắc Tay Bạc", 8, 2)                    # 43
    add("Đá Thạch Anh Thô", 9, 2)                # 44
    add("Đá Mắt Hổ Thô", 9, 2)                   # 45
    add("Đá Cắt Mài Cao Cấp", 10, 2)             # 46
    add("Tỳ Hưu Đá Quý", 11, 2)                  # 47
    add("Tỳ Hưu Vàng", 11, 2)                    # 48
    add("Tượng Phật Ngọc", 12, 2)                # 49
    add("Tượng Quan Âm Đá Quý", 12, 2)           # 50

    cols = ["id", "name", "slug", "description", "parent_id", "depth_level", "is_active"]
    return cols, rows, list(range(start_id, cid))


def gen_products(start_id: int, n: int, brand_ids: list[int], category_pool: list[int]):
    rows = []
    used_sku = set()
    for i in range(n):
        pid = start_id + i
        jewelry_name, sku_code, cat_choices = random.choice(JEWELRY_TYPES)
        material, element, origin = random.choice(MATERIALS)
        style = random.choice(STYLE_ADJ)
        brand_id = random.choice(brand_ids)
        category_id = random.choice([c for c in cat_choices if c in category_pool] or category_pool)

        suffix = "" if "Phong Thủy" in jewelry_name else " Phong Thủy"
        name = f"{jewelry_name} {material.title()} {style}{suffix}"
        slug = slugify(name, str(pid))
        sku = f"PC-{sku_code}-{pid:03d}"
        while sku in used_sku:
            pid += 1000
            sku = f"PC-{sku_code}-{pid:03d}"
        used_sku.add(sku)

        unit_price = round(random.uniform(280_000, 15_000_000), -3)
        has_sale = random.random() < 0.55
        sale_price = round(unit_price * random.uniform(0.75, 0.95), -3) if has_sale else None
        stock_qty = random.randint(0, 90)
        in_stock = stock_qty > 0

        description = (
            f"{jewelry_name} làm từ {material} thiên nhiên, hỗ trợ mệnh {element}. "
            f"Thiết kế {style.lower()}, phù hợp làm quà tặng hoặc dùng hàng ngày. "
            f"Nguồn gốc {origin}, chọn lọc kỹ càng đảm bảo chất lượng."
        )
        short_description = f"{jewelry_name} {material}, hợp mệnh {element}, phong cách {style.lower()}."

        attributes = {"material": material, "element": element, "origin": origin, "style": style}

        rows.append([
            pid, name, slug, sku, description, short_description,
            category_id, brand_id, unit_price, sale_price, in_stock, stock_qty,
            attributes, "active", "pending",
        ])
    cols = ["id", "name", "slug", "sku", "description", "short_description", "category_id", "brand_id",
            "unit_price", "sale_price", "in_stock", "stock_qty", "attributes", "status", "embedding_status"]
    return cols, rows


def gen_product_images(start_id: int, product_ids: list[int]):
    rows = []
    img_id = start_id
    for pid in product_ids:
        n_images = random.choice([1, 2, 2, 3])
        for j in range(n_images):
            rows.append([
                img_id, pid,
                f"https://cdn.pancharm.vn/products/prod-{pid}-{j}.jpg",
                f"Ảnh sản phẩm #{pid} - góc {j + 1}",
                j, j == 0,
            ])
            img_id += 1
    cols = ["id", "product_id", "url", "alt_text", "sort_order", "is_primary"]
    return cols, rows


def gen_product_tags(product_ids: list[int], tag_ids: list[int]):
    rows = []
    for pid in product_ids:
        chosen = random.sample(tag_ids, k=random.choice([2, 3, 3, 4]))
        for tid in chosen:
            rows.append([pid, tid])
    cols = ["product_id", "tag_id"]
    return cols, rows


def gen_users(start_id: int, n: int):
    rows = []
    genders = []
    for i in range(n):
        uid = start_id + i
        gender = random.choice(["male", "female"])
        genders.append(gender)
        full_name = vn_name(gender)
        email_local = slugify(full_name).replace("-", ".")
        email = f"{email_local}{uid}@gmail.com"
        phone_prefix = random.choice(["090", "091", "093", "070", "079", "086", "096", "097", "032", "056"])
        phone = phone_prefix + "".join(str(random.randint(0, 9)) for _ in range(7))
        provider = random.choices(["local", "google", "facebook", "zalo"], weights=[60, 20, 12, 8])[0]
        provider_id = f"{provider}_uid_{uid:04d}" if provider != "local" else None
        is_verified = random.random() < 0.8
        last_login = rand_dt(BASE_START, BASE_END)
        rows.append([
            uid, email, phone,
            f"$2b$12$seedhash{uid:04d}xyzabcxyzabc0000000",
            provider, provider_id, "customer", True, is_verified, dt_str(last_login),
        ])
    cols = ["id", "email", "phone", "password_hash", "auth_provider", "auth_provider_id",
            "role", "is_active", "is_verified", "last_login_at"]
    return cols, rows, genders


def gen_user_profiles(start_id: int, user_ids: list[int], genders: list[str]):
    rows = []
    segments = ["new", "regular", "regular", "vip", "churned"]
    for idx, uid in enumerate(user_ids):
        gender = genders[idx]
        display_name = vn_name(gender)
        birth_year = random.randint(1975, 2005)
        dob = f"{birth_year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        segment = random.choice(segments)
        total_orders = {"new": random.randint(0, 1), "regular": random.randint(2, 5),
                         "vip": random.randint(5, 12), "churned": random.randint(0, 3)}[segment]
        total_spent = round(total_orders * random.uniform(300_000, 4_000_000), -3) if total_orders else 0.0
        loyalty_points = int(total_spent / 10_000)
        prefs = {
            "price_range": sorted([int(random.choice([300000, 500000, 1000000])),
                                    int(random.choice([2000000, 5000000, 15000000]))]),
            "fav_elements": random.sample(ELEMENTS, k=random.choice([1, 2])),
        }
        rows.append([
            start_id + idx, uid, display_name,
            f"https://cdn.pancharm.vn/avatars/u{uid:04d}.jpg" if random.random() < 0.7 else None,
            dob, gender, random.choice(ZODIAC_SIGNS), prefs,
            total_orders, total_spent, loyalty_points, segment,
        ])
    cols = ["id", "user_id", "display_name", "avatar_url", "date_of_birth", "gender",
            "zodiac_sign", "preferences", "total_orders", "total_spent", "loyalty_points", "customer_segment"]
    return cols, rows


def gen_user_addresses(start_id: int, user_ids: list[int]):
    rows = []
    addr_id = start_id
    for uid in user_ids:
        n_addr = random.choice([1, 1, 1, 2])
        for j in range(n_addr):
            ward, district, province = random.choice(PROVINCES)
            recipient = vn_name(random.choice(["male", "female"]))
            phone_prefix = random.choice(["090", "091", "093", "070", "079"])
            phone = phone_prefix + "".join(str(random.randint(0, 9)) for _ in range(7))
            rows.append([
                addr_id, uid, "Nhà" if j == 0 else "Văn phòng", recipient, phone,
                f"{random.randint(1, 200)} {random.choice(STREETS)}",
                None if random.random() < 0.6 else f"Tầng {random.randint(1,20)}",
                ward, district, province, j == 0,
            ])
            addr_id += 1
    cols = ["id", "user_id", "label", "recipient_name", "phone", "address_line1", "address_line2",
            "ward", "district", "province", "is_default"]
    return cols, rows


def gen_carts(start_id: int, user_ids: list[int]):
    rows = []
    for idx, uid in enumerate(user_ids):
        cid = start_id + idx
        expires = rand_dt(BASE_END, BASE_END + timedelta(days=30))
        rows.append([cid, uid, None, dt_str(expires)])
    cols = ["id", "user_id", "session_key", "expires_at"]
    return cols, rows


def gen_cart_items(start_id: int, cart_ids: list[int], product_ids: list[int]):
    rows = []
    item_id = start_id
    for cart_id in cart_ids:
        n_items = random.choice([0, 1, 1, 2])
        chosen_products = random.sample(product_ids, k=min(n_items, len(product_ids))) if n_items else []
        for pid in chosen_products:
            rows.append([item_id, cart_id, pid, random.choice([1, 1, 1, 2])])
            item_id += 1
    cols = ["id", "cart_id", "product_id", "quantity"]
    return cols, rows


def gen_conversation_sessions(start_id: int, n: int, user_ids: list[int]):
    rows = []
    channels = ["web", "web", "mobile", "telegram", "zalo", "facebook", "tiktok"]
    statuses = ["completed", "completed", "completed", "active", "abandoned"]
    outcomes = ["no_intent", "expressed_interest", "added_to_cart", "purchased", "purchased"]
    psych_states = ["CURIOUS", "INTERESTED", "HESITATION", "COMMITTED", "OBJECTING"]
    thread_ids = []
    for i in range(n):
        sid = start_id + i
        uid = random.choice(user_ids)
        started = rand_dt(BASE_START, BASE_END)
        status = random.choice(statuses)
        outcome = random.choice(outcomes)
        turns = random.randint(1, 6)
        ended = started + timedelta(minutes=random.randint(3, 45)) if status != "active" else None
        thread_id = f"seed-{sid:06d}-{'%08x' % random.getrandbits(32)}-{'%04x' % random.getrandbits(16)}"
        thread_ids.append(thread_id)
        rows.append([
            sid, thread_id, uid, random.choice(channels), status,
            random.choice(psych_states) if status != "active" else None,
            random.choice(CONSULT_STRATEGIES) if status != "active" else None,
            turns, min(turns, 5), outcome, None,
            dt_str(started), dt_str(ended or started + timedelta(minutes=5)),
            dt_str(ended) if ended else None,
        ])
    cols = ["id", "thread_id", "user_id", "channel", "status", "final_psych_state",
            "final_consult_strategy", "total_turns", "iteration_count", "conversion_outcome",
            "linked_order_id", "started_at", "last_active_at", "ended_at"]
    return cols, rows


def gen_conversation_messages(start_id: int, sessions: list[tuple]):
    """sessions: list of (session_id, turns, started_at str)"""
    rows = []
    msg_id = start_id
    for sid, turns, started_str in sessions:
        started = datetime.strptime(started_str, "%Y-%m-%d %H:%M:%S")
        for turn in range(1, turns + 1):
            element = random.choice(ELEMENTS)
            jewelry = random.choice(JEWELRY_TYPES)[0]
            budget = random.choice(BUDGETS)
            occasion = random.choice(OCCASIONS)
            year = random.randint(1975, 2005)
            user_msg = random.choice(USER_MESSAGE_TEMPLATES).format(
                year=year, element=element, jewelry=jewelry, budget=budget, occasion=occasion)
            ts = started + timedelta(minutes=(turn - 1) * 3)
            rows.append([msg_id, sid, turn, "user", user_msg, None, None, None])
            msg_id += 1

            assistant_msg = random.choice(ASSISTANT_MESSAGE_TEMPLATES).format(
                element=element, jewelry=jewelry, budget=budget, occasion=occasion)
            latency = random.randint(1200, 2800)
            token_count = random.randint(60, 180)
            rows.append([msg_id, sid, turn, "assistant", assistant_msg, "synth_agent", latency, token_count])
            msg_id += 1
    cols = ["id", "session_id", "turn_number", "role", "content", "agent_name", "latency_ms", "token_count"]
    return cols, rows


def gen_psych_state_logs(start_id: int, sessions: list[tuple]):
    rows = []
    log_id = start_id
    states = ["CURIOUS", "INTERESTED", "HESITATION", "COMMITTED", "OBJECTING"]
    for sid, turns, _ in sessions:
        for turn in range(1, turns + 1):
            state = random.choice(states)
            confidence = round(random.uniform(0.55, 0.98), 3)
            concern = random.choice(CONCERN_TEMPLATES)
            strategy = random.choice(CONSULT_STRATEGIES)
            raw = {"state": state, "confidence": confidence, "turn": turn}
            rows.append([log_id, sid, turn, state, confidence, concern, strategy, raw])
            log_id += 1
    cols = ["id", "session_id", "turn_number", "psych_state", "confidence_score",
            "primary_concern", "consult_strategy", "raw_output"]
    return cols, rows


def gen_agent_performance_logs(start_id: int, sessions: list[tuple], product_ids: list[int]):
    rows = []
    log_id = start_id
    agents = ["orchestrator", "kr_agent", "psych_agent", "synth_agent"]
    for sid, turns, _ in sessions:
        for turn in range(1, turns + 1):
            for agent in agents:
                latency = random.randint(250, 2500)
                input_tokens = random.randint(150, 900)
                output_tokens = random.randint(40, 300)
                retrieval_score = round(random.uniform(0.55, 0.98), 4) if agent == "kr_agent" else None
                retrieved_ids = random.sample(product_ids, k=min(3, len(product_ids))) if agent == "kr_agent" else None
                rows.append([
                    log_id, sid, turn, agent, latency, input_tokens, output_tokens,
                    retrieval_score, retrieved_ids, None,
                ])
                log_id += 1
    cols = ["id", "session_id", "turn_number", "agent_name", "latency_ms", "input_tokens",
            "output_tokens", "retrieval_score", "retrieved_product_ids", "error_message"]
    return cols, rows


def gen_orders(start_id: int, n: int, user_addr_pairs: list[tuple], product_price_map: dict):
    """user_addr_pairs: list of (user_id, address_id). Trả về thêm order_items song song."""
    order_rows = []
    item_rows = []
    payment_rows = []
    order_item_id_counter = [0]  # filled by caller via offsets
    statuses_weighted = ["delivered", "delivered", "delivered", "shipped", "processing", "confirmed", "pending", "cancelled"]
    for i in range(n):
        oid = start_id + i
        user_id, addr_id = random.choice(user_addr_pairs)
        n_items = random.choice([1, 1, 2, 2, 3])
        chosen = random.sample(list(product_price_map.items()), k=min(n_items, len(product_price_map)))

        subtotal = 0.0
        items_for_order = []
        for pid, (pname, psku, price) in chosen:
            qty = random.choice([1, 1, 1, 2])
            total_price = round(price * qty, 2)
            subtotal += total_price
            items_for_order.append((pid, pname, psku, price, qty, total_price))

        discount = round(subtotal * random.choice([0, 0, 0.05, 0.1]), -3)
        shipping_fee = 0.0 if subtotal >= 2_000_000 else 30000.0
        total_amount = round(subtotal - discount + shipping_fee, 2)

        status = random.choice(statuses_weighted)
        payment_status = "paid" if status in ("delivered", "shipped", "processing", "confirmed") else (
            "unpaid" if status == "pending" else "refunded")

        created = rand_dt(BASE_START, BASE_END)
        confirmed_at = dt_str(created + timedelta(hours=1)) if status != "pending" else None
        shipped_at = dt_str(created + timedelta(days=1)) if status in ("shipped", "delivered") else None
        delivered_at = dt_str(created + timedelta(days=3)) if status == "delivered" else None

        order_rows.append([
            oid, f"PC-SEED-{oid:05d}", user_id, addr_id,
            round(subtotal, 2), discount, shipping_fee, total_amount,
            status, payment_status,
            random.choice(["GHN Express", "GHTK", "ViettelPost", None]),
            f"SEED{oid:08d}" if status in ("shipped", "delivered") else None,
            None, None, None,
            dt_str(created), confirmed_at, shipped_at, delivered_at,
        ])

        for pid, pname, psku, price, qty, total_price in items_for_order:
            item_rows.append([None, oid, pid, pname, psku, price, qty, total_price])  # id filled later

        if payment_status in ("paid", "refunded"):
            method = random.choice(["momo", "vnpay", "zalopay", "bank_transfer", "credit_card", "cod"])
            pay_status = "success" if payment_status == "paid" else "refunded"
            payment_rows.append([
                None, oid, method, f"SEEDPAY{oid:08d}" if method != "cod" else None,
                total_amount, pay_status,
                {"note": "seed data"} if method != "cod" else None,
                dt_str(created + timedelta(minutes=10)) if pay_status == "success" else None,
            ])
        elif payment_status == "unpaid":
            payment_rows.append([None, oid, "cod", None, total_amount, "pending", None, None])

    return order_rows, item_rows, payment_rows


def gen_product_reviews(start_id: int, n: int, product_ids: list[int], user_ids: list[int]):
    rows = []
    for i in range(n):
        rid = start_id + i
        pid = random.choice(product_ids)
        uid = random.choice(user_ids) if random.random() < 0.9 else None
        material = random.choice(MATERIALS)[0]
        rating = random.choices([5, 4, 3, 2], weights=[55, 30, 10, 5])[0]
        body = random.choice(REVIEW_BODY_TEMPLATES).format(material=material)
        rows.append([
            rid, pid, uid, None, rating, random.choice(REVIEW_TITLES), body,
            random.random() < 0.85, True, "pending",
        ])
    cols = ["id", "product_id", "user_id", "order_item_id", "rating", "title", "body",
            "is_verified_purchase", "is_published", "embedding_status"]
    return cols, rows


def gen_api_keys(start_id: int, n: int, owner_user_id: int):
    rows = []
    names = [
        "Partner Integration", "Internal Testing", "Analytics Dashboard", "Mobile App Build",
        "Web Storefront", "Marketing Automation", "3rd Party Marketplace", "CRM Sync",
        "Loyalty Program", "Warehouse System",
    ]
    for i in range(n):
        kid = start_id + i
        name = f"{random.choice(names)} #{kid}"
        rows.append([
            kid, name, f"sha256_seedhash{kid:06d}abcdef1234567890abcdef1234567890",
            f"pk_seed_{kid:04d}", owner_user_id,
            random.choice([["chat:read", "chat:write"], ["products:read"], ["orders:read", "analytics:read"]]),
            random.choice([100, 200, 300, 500]), random.random() < 0.9,
            dt_str(rand_dt(BASE_START, BASE_END)), None,
        ])
    cols = ["id", "name", "key_hash", "key_prefix", "owner_user_id", "scopes",
            "rate_limit_rpm", "is_active", "last_used_at", "expires_at"]
    return cols, rows


def gen_system_configs(start_id: int, updated_by: int):
    rows = []
    for i, (key, value, vtype, desc) in enumerate(SYSTEM_CONFIG_EXTRA):
        rows.append([start_id + i, key, value, vtype, desc, False, updated_by])
    cols = ["id", "config_key", "config_value", "value_type", "description", "is_sensitive", "updated_by"]
    return cols, rows


def gen_audit_logs(start_id: int, n: int, user_ids: list[int], order_ids: list[int], product_ids: list[int]):
    rows = []
    actions = [
        ("order.create", "Orders"), ("order.status_update", "Orders"),
        ("product.update", "Products"), ("review.create", "ProductReviews"),
        ("session.timeout", "ConversationSessions"),
    ]
    for i in range(n):
        aid = start_id + i
        action, resource_type = random.choice(actions)
        actor_is_system = random.random() < 0.15
        resource_id = random.choice(order_ids) if resource_type == "Orders" else (
            random.choice(product_ids) if resource_type == "Products" else random.randint(1, 100))
        rows.append([
            aid, None if actor_is_system else random.choice(user_ids),
            "system" if actor_is_system else "user", action, resource_type, resource_id,
            None, {"seed": True, "action": action},
            None if actor_is_system else f"{random.randint(1,223)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
            None if actor_is_system else "Mozilla/5.0 (seed-data)",
        ])
    cols = ["id", "actor_id", "actor_type", "action", "resource_type", "resource_id",
            "old_value", "new_value", "ip_address", "user_agent"]
    return cols, rows


# ------------------------------------------------------------------
# Main assembly
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Chỉ generate, không ghi file (in preview)")
    args = parser.parse_args()

    blocks: dict[str, str] = {}

    # [1] Brands: 10 -> 50
    cols, rows = gen_brands(11, 40)
    new_brand_ids = [r[0] for r in rows]
    blocks["brands"] = insert_stmt("Brands", cols, rows)

    # [2] Tags: 15 -> 50
    cols, rows = gen_tags(16, 35)
    new_tag_ids = [r[0] for r in rows]
    blocks["tags"] = insert_stmt("Tags", cols, rows)

    # [3] Categories: 12 -> 50
    cols, rows, new_category_ids = gen_categories(13)
    blocks["categories"] = insert_stmt("Categories", cols, rows)

    # [4] Products: 12 -> 50
    all_brand_ids = list(range(1, 11)) + new_brand_ids
    all_category_ids = list(range(4, 13)) + new_category_ids
    cols, rows = gen_products(13, 38, all_brand_ids, all_category_ids)
    new_product_ids = [r[0] for r in rows]
    product_name_sku_price = {r[0]: (r[1], r[3], float(r[9] if r[9] is not None else r[8])) for r in rows}
    blocks["products"] = insert_stmt("Products", cols, rows)

    # [5] ProductImages: 20 -> 20 + ~2/new product
    cols, rows = gen_product_images(21, new_product_ids)
    blocks["product_images"] = insert_stmt("ProductImages", cols, rows)

    # [6] ProductTags
    all_tag_ids = list(range(1, 16)) + new_tag_ids
    cols, rows = gen_product_tags(new_product_ids, all_tag_ids)
    blocks["product_tags"] = insert_stmt("ProductTags", cols, rows)

    # [7] Users: 12 -> 55
    cols, rows, genders = gen_users(13, 43)
    new_user_ids = [r[0] for r in rows]
    blocks["users"] = insert_stmt("Users", cols, rows)

    # [8] UserProfiles
    cols, rows = gen_user_profiles(13, new_user_ids, genders)
    blocks["user_profiles"] = insert_stmt("UserProfiles", cols, rows)

    # [9] UserAddresses
    cols, rows = gen_user_addresses(15, new_user_ids)
    new_addr_rows = rows
    blocks["user_addresses"] = insert_stmt("UserAddresses", cols, rows)
    user_addr_pairs = [(r[1], r[0]) for r in new_addr_rows]
    # thêm cả user cũ (1-10) với địa chỉ cũ (1-12) để order có thể tham chiếu cả 2 phía
    old_user_addr_pairs = [(1, 1), (2, 3), (3, 4), (4, 5), (5, 7), (6, 8), (7, 9), (8, 10), (9, 11), (10, 12)]
    all_user_addr_pairs = user_addr_pairs + old_user_addr_pairs

    # [10] Carts: 1 per new user
    cols, rows = gen_carts(13, new_user_ids)
    new_cart_ids = [r[0] for r in rows]
    blocks["carts"] = insert_stmt("Carts", cols, rows)

    # [11] CartItems
    all_product_ids_for_cart = list(range(1, 13)) + new_product_ids
    cols, rows = gen_cart_items(16, new_cart_ids, all_product_ids_for_cart)
    blocks["cart_items"] = insert_stmt("CartItems", cols, rows)

    # [12] ConversationSessions: 12 -> 55
    all_user_ids_for_session = list(range(1, 11)) + new_user_ids  # loại admin/staff (11,12)
    cols, rows = gen_conversation_sessions(13, 43, all_user_ids_for_session)
    session_meta = [(r[0], r[7], r[11]) for r in rows]  # (id, total_turns, started_at)
    blocks["conversation_sessions"] = insert_stmt("ConversationSessions", cols, rows)

    # [13] ConversationMessages
    cols, rows = gen_conversation_messages(21, session_meta)
    blocks["conversation_messages"] = insert_stmt("ConversationMessages", cols, rows)

    # [14] PsychStateLogs
    cols, rows = gen_psych_state_logs(13, session_meta)
    blocks["psych_state_logs"] = insert_stmt("PsychStateLogs", cols, rows)

    # [15] AgentPerformanceLogs
    all_product_ids_for_perf = list(range(1, 13)) + new_product_ids
    cols, rows = gen_agent_performance_logs(13, session_meta, all_product_ids_for_perf)
    blocks["agent_performance_logs"] = insert_stmt("AgentPerformanceLogs", cols, rows)

    # [16] Orders + OrderItems + Payments: 12 -> 55
    all_product_price_map = dict(product_name_sku_price)
    for pid_old, name_old, sku_old, price_old in [
        (1, "Vòng Tay Đá Mắt Hổ Vàng Phong Thủy", "PC-VT-001", 720000.0),
        (2, "Vòng Tay Thạch Anh Tím Amethyst Cao Cấp", "PC-VT-002", 680000.0),
        (3, "Vòng Tay Mã Não Đỏ Huyết Long", "PC-VT-003", 450000.0),
        (4, "Nhẫn Ngọc Bích Xanh Tự Nhiên", "PC-NH-001", 2500000.0),
        (5, "Dây Chuyền Mặt Tỳ Hưu Vàng 18K", "PC-DC-001", 3980000.0),
        (6, "Vòng Tay Đá Đen Obsidian Bảo Vệ", "PC-VT-004", 380000.0),
        (7, "Nhẫn Đá Lapis Lazuli Trí Tuệ", "PC-NH-002", 980000.0),
        (8, "Hoa Tai Ngọc Trai Nước Mặn Cao Cấp", "PC-HT-001", 3200000.0),
        (9, "Vòng Tay Thạch Anh Hồng Tình Yêu", "PC-VT-005", 390000.0),
        (10, "Dây Chuyền Thạch Anh Tím Mặt Trái Tim", "PC-DC-002", 520000.0),
        (11, "Vòng Tay Vàng 18K Phong Thủy Hổ Phù", "PC-LT-001", 7800000.0),
        (12, "Nhẫn Đá Ruby Phong Thủy Mệnh Hỏa", "PC-NH-003", 12000000.0),
    ]:
        all_product_price_map[pid_old] = (name_old, sku_old, price_old)

    order_rows, item_rows_raw, payment_rows_raw = gen_orders(
        13, 43, all_user_addr_pairs, all_product_price_map)
    blocks["orders"] = insert_stmt(
        "Orders",
        ["id", "order_code", "user_id", "shipping_address_id", "subtotal", "discount_amount",
         "shipping_fee", "total_amount", "status", "payment_status", "shipping_method",
         "tracking_number", "notes", "staff_notes", "conversation_session_id",
         "created_at", "confirmed_at", "shipped_at", "delivered_at"],
        order_rows,
    )
    new_order_ids = [r[0] for r in order_rows]

    item_id = 16
    for r in item_rows_raw:
        r[0] = item_id
        item_id += 1
    blocks["order_items"] = insert_stmt(
        "OrderItems",
        ["id", "order_id", "product_id", "product_name", "product_sku", "unit_price", "quantity", "total_price"],
        item_rows_raw,
    )

    pay_id = 13
    for r in payment_rows_raw:
        r[0] = pay_id
        pay_id += 1
    blocks["payments"] = insert_stmt(
        "Payments",
        ["id", "order_id", "payment_method", "transaction_id", "amount", "status",
         "gateway_response", "paid_at"],
        payment_rows_raw,
    )

    # [17] ProductReviews: 12 -> 55
    all_product_ids_for_review = list(range(1, 13)) + new_product_ids
    all_user_ids_for_review = list(range(1, 11)) + new_user_ids
    cols, rows = gen_product_reviews(13, 43, all_product_ids_for_review, all_user_ids_for_review)
    blocks["product_reviews"] = insert_stmt("ProductReviews", cols, rows)

    # [18] APIKeys: 10 -> 50
    cols, rows = gen_api_keys(11, 40, owner_user_id=11)
    blocks["api_keys"] = insert_stmt("APIKeys", cols, rows)

    # [19] SystemConfigs: 20 -> 50
    cols, rows = gen_system_configs(21, updated_by=11)
    blocks["system_configs"] = insert_stmt("SystemConfigs", cols, rows)

    # [20] AuditLogs: 12 -> 55
    all_user_ids_for_audit = list(range(1, 13)) + new_user_ids
    all_product_ids_for_audit = list(range(1, 13)) + new_product_ids
    cols, rows = gen_audit_logs(13, 43, all_user_ids_for_audit, new_order_ids, all_product_ids_for_audit)
    blocks["audit_logs"] = insert_stmt("AuditLogs", cols, rows)

    # ------------------------------------------------------------------
    # Ghép vào seed.sql: chèn từng block ngay sau khối INSERT gốc tương ứng
    # ------------------------------------------------------------------
    content = SEED_SQL_PATH.read_text(encoding="utf-8")

    anchors = [
        ("brands", "-- [2] Tags"),
        ("tags", "-- [3] Categories"),
        ("categories", "-- [4] Products"),
        ("products", "-- [5] ProductImages"),
        ("product_images", "-- [6] ProductTags"),
        ("product_tags", "-- [7] Users"),
        ("users", "-- [8] UserProfiles"),
        ("user_profiles", "-- [9] UserAddresses"),
        ("user_addresses", "-- [10] Carts"),
        ("carts", "-- [11] CartItems"),
        ("cart_items", "-- [12] ConversationSessions"),
        ("conversation_sessions", "-- [13] Orders"),
        ("orders", "-- [14] OrderItems"),
        ("order_items", "-- [15] Payments"),
        ("payments", "-- [16] ProductReviews"),
        ("product_reviews", "-- [17] ConversationMessages"),
        ("conversation_messages", "-- [18] PsychStateLogs"),
        ("psych_state_logs", "-- [19] AgentPerformanceLogs"),
        ("agent_performance_logs", "-- [20] APIKeys"),
        ("api_keys", "-- [21] SystemConfigs"),
        ("system_configs", "-- [22] AuditLogs"),
        ("audit_logs", "-- [23] Resolve circular FK"),
    ]

    for key, anchor_text in anchors:
        marker = f"\n-- ============================================================\n{anchor_text}"
        idx = content.index(marker)
        insertion = (
            f"\n-- ------------------------------------------------------------\n"
            f"-- [{key}] EXTENDED — thêm bằng scripts/generate_seed_data.py (>= 50 rows/bảng)\n"
            f"-- ------------------------------------------------------------\n"
            + blocks[key]
        )
        content = content[:idx] + insertion + content[idx:]

    # Đếm số dòng VALUES mới sinh ra cho từng bảng để verify >= 50 (cộng dữ liệu gốc)
    counts = {k: v.count("\n(") for k, v in blocks.items()}
    print("=== Số row MỚI sinh thêm cho từng bảng ===")
    for k, c in counts.items():
        print(f"  {k}: +{c}")

    if args.check:
        print(f"\nTotal new content length: {len(content)} chars")
        return

    SEED_SQL_PATH.write_text(content, encoding="utf-8")
    print(f"Wrote updated seed.sql -> {SEED_SQL_PATH} ({len(content)} chars)")


if __name__ == "__main__":
    main()
