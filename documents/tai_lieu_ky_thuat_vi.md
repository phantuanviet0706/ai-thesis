# TÀI LIỆU KỸ THUẬT TRIỂN KHAI
# Hệ Thống Đa Tác Nhân (MAS) Hỗ Trợ Tư Vấn Bán Lẻ

**Tác giả:** Phan Tuấn Việt
**Người hướng dẫn:** TS. Bùi Văn Hiệu | **Đồng hướng dẫn:** TS. Trương Công Đoàn
**Trường:** FPT School of Business & Technology
**Hoàn thành:** Tháng 5/2026
**Ứng dụng thực tế:** Startup Pancharm (trang sức phong thủy, thị trường Việt Nam)

---

## MỤC LỤC

1. [Bối Cảnh và Bài Toán](#1-bối-cảnh-và-bài-toán)
2. [Tổng Quan Kiến Trúc Hệ Thống](#2-tổng-quan-kiến-trúc-hệ-thống)
3. [Nền Tảng Công Nghệ — LangGraph](#3-nền-tảng-công-nghệ--langgraph)
4. [Quản Lý Trạng Thái — ConversationState](#4-quản-lý-trạng-thái--conversationstate)
5. [Orchestrator Agent — Trung Tâm Điều Phối](#5-orchestrator-agent--trung-tâm-điều-phối)
6. [KR Agent — Truy Xuất Tri Thức](#6-kr-agent--truy-xuất-tri-thức)
7. [Psych Agent — Phân Tích Tâm Lý Khách Hàng](#7-psych-agent--phân-tích-tâm-lý-khách-hàng)
8. [Synth Agent — Tổng Hợp Phản Hồi](#8-synth-agent--tổng-hợp-phản-hồi)
9. [ChromaDB — Cơ Sở Dữ Liệu Vector](#9-chromadb--cơ-sở-dữ-liệu-vector)
10. [API và Giao Tiếp Hệ Thống](#10-api-và-giao-tiếp-hệ-thống)
11. [Triển Khai Hạ Tầng](#11-triển-khai-hạ-tầng)
12. [Khung Đánh Giá CARS](#12-khung-đánh-giá-cars)
13. [Kết Quả Thực Nghiệm](#13-kết-quả-thực-nghiệm)
14. [Hạn Chế và Hướng Phát Triển](#14-hạn-chế-và-hướng-phát-triển)
15. [Bảng Tra Cứu Công Thức](#15-bảng-tra-cứu-công-thức)

---

## 1. BỐI CẢNH VÀ BÀI TOÁN

### 1.1 Bối Cảnh Thị Trường

Thương mại điện tử Việt Nam đang tăng trưởng mạnh mẽ:
- Năm 2024: định giá **32 tỷ USD**, tốc độ tăng trưởng **27%/năm** (VECOM)
- Doanh thu bán lẻ trực tuyến chiếm khoảng **12%** tổng doanh thu bán lẻ
- Bộ Công Thương dự báo tăng trưởng **25,5%** vào năm 2025, tổng giá trị giao dịch **28 tỷ USD**
- Đến năm 2030, doanh thu TMĐT dự kiến chiếm **20%** tổng doanh thu bán lẻ
- Nền tảng shoppertainment (TikTok Shop, Shopee) chiếm tới **97%** thị phần đầu 2025

**Hành vi người tiêu dùng Việt:**
- Trung bình **6,5 lần mua sắm online/tháng**
- Kỳ vọng được tư vấn **có bối cảnh, chuyên nghiệp, cá nhân hóa cao**
- McKinsey: 71% người tiêu dùng kỳ vọng tương tác cá nhân hóa; 76% thất vọng khi kỳ vọng không được đáp ứng
- Cá nhân hóa tốt có thể tăng doanh thu thêm **40%** so với mức trung bình ngành

### 1.2 Vấn Đề Kỹ Thuật

Chatbot đơn tác nhân hiện tại thất bại vì:

| Vấn đề | Nguyên nhân gốc | Hậu quả |
|---|---|---|
| ~29% thất bại nhận dạng ý định | Không duy trì ngữ cảnh qua nhiều lượt hội thoại | Trải nghiệm người dùng kém |
| Bị giới hạn ở câu hỏi giao dịch | Kiến trúc đơn tuyến, không vòng lặp | Không tư vấn được sản phẩm phức tạp |
| Phân mảnh phần mềm | Agent đơn lẻ cố gắng xử lý tất cả | Mất mạch hội thoại |
| Hallucination thông tin sản phẩm | Không có cơ chế truy xuất có căn cứ | Giảm tỷ lệ chốt đơn |

### 1.3 Câu Hỏi Nghiên Cứu

> "Làm thế nào tích hợp nhiều tác nhân chuyên biệt theo nguyên tắc 'chia để trị' nhằm duy trì luồng hội thoại nhất quán đồng thời cải thiện tỷ lệ chuyển đổi khách hàng?"

### 1.4 Phạm Vi

- **Lĩnh vực:** Bán lẻ trang sức phong thủy (hàng hóa cao cấp, cần tư vấn chuyên sâu)
- **Thị trường:** Việt Nam, giai đoạn 2025–2026
- **Dữ liệu thực tế:** Startup Pancharm (100 sản phẩm, ~1.000 log hội thoại thực)
- **Ngôn ngữ:** Tiếng Việt (thách thức: từ đồng nghĩa địa phương, kính ngữ, thiếu dữ liệu gán nhãn)

---

## 2. TỔNG QUAN KIẾN TRÚC HỆ THỐNG

### 2.1 Sáu Nguyên Tắc Thiết Kế

Toàn bộ kiến trúc được xây dựng dựa trên 6 nguyên tắc:

| # | Nguyên tắc | Ý nghĩa kỹ thuật | Vấn đề được giải quyết |
|---|---|---|---|
| 1 | **Phân tách trách nhiệm** (Separation of Concerns) | Mỗi agent đảm nhận đúng một chức năng duy nhất | Ngăn ô nhiễm ngữ cảnh và trôi ngữ nghĩa |
| 2 | **Chia để trị** (Divide & Conquer) | Tác vụ tư vấn được phân rã thành các bài toán con: truy xuất tri thức, phân tích tâm lý, tổng hợp phản hồi | Tối ưu hóa độc lập từng thành phần |
| 3 | **Quản lý trạng thái tập trung** (Centralized State) | Toàn bộ ngữ cảnh hội thoại lưu trong một `ConversationState` duy nhất | Đảm bảo tất cả agent hoạt động trên dữ liệu nhất quán |
| 4 | **Quan sát được** (Observability) | Log đầy đủ mọi bước xử lý | Cho phép debug thời gian thực và phân tích hiệu năng sau triển khai |
| 5 | **Khả năng phục hồi** (Resilience) | Checkpoint Redis tại mỗi bước — phục hồi sau mất kết nối | Quan trọng với TMĐT di động Việt Nam (kết nối không ổn định) |
| 6 | **Suy giảm duyên dáng** (Graceful Degradation) | Hệ thống tiếp tục hoạt động dù một agent tạm thời không khả dụng | Đảm bảo dịch vụ liên tục |

### 2.2 Kiến Trúc Bốn Tầng

```
┌─────────────────────────────────────────────────────────┐
│  TẦNG 1: GIAO DIỆN (Interface Layer)                    │
│  REST API · Xác thực · Rate limiting 100 req/min        │
│  Khởi tạo/phục hồi phiên từ Redis checkpointer          │
│  Chuyển đổi request thô → ConversationState             │
├─────────────────────────────────────────────────────────┤
│  TẦNG 2: ĐIỀU PHỐI (Orchestration Layer)                │
│  Orchestrator Agent · LangGraph DCG                     │
│  Phân tích ý định · Ra quyết định routing               │
│  Nguồn sự thật duy nhất cho mọi quyết định điều phối    │
├─────────────────────────────────────────────────────────┤
│  TẦNG 3: XỬ LÝ CHUYÊN BIỆT (Specialized Layer)         │
│  KR Agent (GraphRAG) · Psych Agent · Synth Agent        │
│  Mỗi agent chuyên sâu một lĩnh vực, không can thiệp nhau│
├─────────────────────────────────────────────────────────┤
│  TẦNG 4: DỮ LIỆU & HẠ TẦNG (Data/Infrastructure)      │
│  ChromaDB (vector) · Redis (session) · LLM API          │
│  Không chứa logic nghiệp vụ · Có thể thay thế độc lập  │
└─────────────────────────────────────────────────────────┘
```

**Quy tắc phụ thuộc (Dependency Rule):** Tầng cao hơn chỉ phụ thuộc vào tầng thấp hơn. Tầng 4 không biết gì về tầng 3, 2, 1.

### 2.3 Bốn Tác Nhân Chuyên Biệt

```
Người dùng
    │
    ▼
[Orchestrator Agent] ─── Phân tích ý định + quyết định routing
    │
    ├──► [KR Agent]       Truy xuất sản phẩm qua GraphRAG + ChromaDB
    │         │
    │         └──► quay lại Orchestrator
    │
    ├──► [Psych Agent]    Phân tích tâm lý + đề xuất chiến lược tư vấn
    │         │
    │         └──► quay lại Orchestrator
    │
    └──► [Synth Agent]    Tổng hợp phản hồi cuối dựa trên KR + Psych
              │
              └──► Phản hồi tới người dùng
```

| Tác nhân | Vai trò chính | Đầu vào | Đầu ra chính |
|---|---|---|---|
| **Orchestrator** | Điều phối, phân tích ý định, routing | Toàn bộ `ConversationState` | `next_node` (tín hiệu routing) |
| **KR Agent** | Truy xuất tri thức sản phẩm | Câu hỏi người dùng + lịch sử | `retrieved_products` (Top-5) |
| **Psych Agent** | Phân loại trạng thái tâm lý | Toàn bộ lịch sử hội thoại (10 lượt gần nhất) | `psych_state` + `consult_strategy` |
| **Synth Agent** | Tạo phản hồi cuối cùng | `ConversationState` đầy đủ (sau KR + Psych) | `final_response` |

### 2.4 Luồng Xử Lý Tổng Quan (Một Lượt Hội Thoại)

```
1. NHẬN REQUEST      Người dùng gửi tin nhắn qua REST API
        │
2. XÁC THỰC         Controller xác thực + lấy session qua session_id
        │
3. PHỤC HỒI         Lấy ConversationState từ Redis, gắn tin nhắn mới
        │
4. ROUTING          Orchestrator phân tích ý định → next_node = "kr_agent"
        │
5. TRUY XUẤT        KR Agent tìm kiếm song song ChromaDB (≤700ms)
        │
6. TÂM LÝ           Psych Agent phân tích lịch sử hội thoại (≤450ms)
        │
7. TỔNG HỢP         Synth Agent tạo phản hồi AIDA (≤800ms)
        │
8. LƯU TRỮ          Checkpoint ConversationState vào Redis
        │
9. PHẢN HỒI         Trả kết quả cho người dùng
```

**Mục tiêu tổng thời gian:** ≤ 3 giây end-to-end

---

## 3. NỀN TẢNG CÔNG NGHỆ — LANGGRAPH

### 3.1 Lý Do Chọn LangGraph

LangGraph được xây dựng bởi team LangChain, ra mắt năm 2024. Điểm khác biệt then chốt so với các framework khác:

**LangChain Chains (cũ):**
- Cấu trúc **DAG (Directed Acyclic Graph)** — luồng một chiều, không có vòng lặp
- Không thể mô hình hóa hội thoại nhiều lượt, retry, hoặc reflection

**LangGraph (mới):**
- Cấu trúc **DCG (Directed Cyclic Graph)** — hỗ trợ vòng lặp, nhánh điều kiện, thực thi song song
- Vòng lặp là bản chất của hội thoại thực: phản hồi → phân tích → phản hồi tiếp theo

**So sánh các framework MAS:**

| Framework | Điều phối | Trạng thái | Ưu điểm | Phù hợp với |
|---|---|---|---|---|
| **LangGraph** ✓ | Phân cấp DCG | TypedDict + Redis | Hỗ trợ vòng lặp, kiểm soát mạnh | Hội thoại phức tạp |
| AutoGen | Peer-to-peer | Conversation Buffer | Linh hoạt, dễ mở rộng | Lập trình tự động |
| CrewAI | Phân cấp | In-memory | Thiết kế khai báo trực quan | Workflow nghiệp vụ |
| AgentVerse | Phân tán | Shared Memory | Mô phỏng đa vai trò | Mô phỏng xã hội |
| Semantic Kernel | Plugin-based | Planners | Tích hợp Microsoft | Enterprise .NET |

**Lý do chọn LangGraph:** Yêu cầu kiểm soát chặt chẽ luồng hội thoại nhiều lượt có cấu trúc + phân định trách nhiệm rõ ràng trong môi trường sản xuất bán lẻ.

### 3.2 Cơ Chế Quản Lý Trạng Thái

Trạng thái hội thoại được cập nhật theo công thức:

```
S(t+1) = Reducer( S(t), Δ_node(S(t)) )
```

Trong đó:
- `S(t)` — trạng thái hiện tại tại bước t
- `Δ_node(S(t))` — delta (thay đổi) mà node hiện tại trả về
- `Reducer` — hàm gộp delta vào trạng thái

**Ba loại Reducer:**

| Loại Reducer | Kiểu dữ liệu | Hành vi | Ví dụ field |
|---|---|---|---|
| `add` (append) | `List` | Nối thêm phần tử mới | `messages`, `iteration_count` |
| `overwrite` | Scalar, Enum, str | Ghi đè hoàn toàn | `psych_state`, `next_node`, `final_response` |
| `merge` | `Dict` | Gộp key-value | `session_metadata` |

**Checkpointing:** Tại mỗi bước thực thi, trạng thái được lưu xuống persistent storage theo định dạng key `thread_id:checkpoint_id`. Khi người dùng gửi tin nhắn mới trong cùng phiên, hệ thống tự động lấy checkpoint gần nhất từ Redis và tiếp tục — không cần khởi tạo lại từ đầu.

### 3.3 Ba Loại Cạnh (Edge) trong LangGraph

1. **Static edges** — luôn đi đến một node cố định
   - Từ KR Agent → luôn về Orchestrator
   - Từ Psych Agent → luôn về Orchestrator
   - Lý do: Orchestrator là điểm kiểm soát duy nhất

2. **Dynamic edges (Conditional edges)** — dựa trên trạng thái hiện tại
   - Từ Orchestrator → KR Agent / Psych Agent / Synth Agent / END
   - Được triển khai qua `conditional_edges()` của LangGraph

3. **Parallel edges (Send API)** — fan-out/fan-in
   - Cho phép KR Agent và Psych Agent chạy song song (hướng phát triển tương lai)

---

## 4. QUẢN LÝ TRẠNG THÁI — CONVERSATIONSTATE

### 4.1 Schema Đầy Đủ

`ConversationState` là nền tảng kiến trúc của toàn bộ hệ thống. Được định nghĩa là `TypedDict` Python với `Annotated` type hints để chỉ định reducer cho từng field:

```python
from typing import TypedDict, Annotated, List, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class ConversationState(TypedDict):
    # ── Lịch sử hội thoại ──────────────────────────────────────
    messages: Annotated[List[BaseMessage], add_messages]
    # Toàn bộ lịch sử hội thoại theo thứ tự thời gian.
    # Reducer: add (nối thêm) — KHÔNG ghi đè.
    # Sở hữu bởi: tất cả agents đọc, Interface Layer ghi tin mới.

    # ── Phân tích ý định ────────────────────────────────────────
    user_intent: str
    # Ý định cấp cao do Orchestrator phân tích từ tin nhắn người dùng.
    # Reducer: overwrite — chỉ giá trị mới nhất có ý nghĩa.
    # Sở hữu bởi: Orchestrator Agent.

    # ── Kết quả truy xuất ───────────────────────────────────────
    retrieved_products: Annotated[List[ProductDoc], overwrite]
    # Top-k sản phẩm từ ChromaDB kèm đầy đủ metadata.
    # Reducer: overwrite — thay thế kết quả cũ hoàn toàn.
    # Sở hữu bởi: KR Agent.

    retrieval_scores: Annotated[List[float], overwrite]
    # Điểm composite tương ứng cho từng sản phẩm đã truy xuất.
    # Reducer: overwrite.
    # Sở hữu bởi: KR Agent.

    # ── Phân tích tâm lý ────────────────────────────────────────
    psych_state: Annotated[PsychStateEnum, overwrite]
    # Trạng thái tâm lý hiện tại của khách hàng (5 trạng thái).
    # Giá trị: AWARENESS | INTEREST | CONSIDERATION | HESITATION | DECISION
    # Reducer: overwrite.
    # Sở hữu bởi: Psych Agent.

    psych_confidence: Annotated[float, overwrite]
    # Độ tin cậy của phân loại tâm lý, thang 0.0–1.0.
    # Reducer: overwrite.
    # Sở hữu bởi: Psych Agent.

    primary_concern: Annotated[str | None, overwrite]
    # Rào cản chính của khách hàng nếu có (vd: "giá", "chất lượng").
    # Reducer: overwrite.
    # Sở hữu bởi: Psych Agent.

    consult_strategy: Annotated[str, overwrite]
    # Chiến lược tư vấn được Psych Agent đề xuất.
    # Ví dụ: "feel-felt-found", "social-proof", "urgency", "education"
    # Reducer: overwrite.
    # Sở hữu bởi: Psych Agent.

    # ── Metadata phiên ──────────────────────────────────────────
    session_metadata: Annotated[Dict[str, Any], merge]
    # Bao gồm: session_id (UUID v4), timestamp, channel, user_profile.
    # Reducer: merge (gộp key-value) — cho phép cập nhật từng phần.
    # Sở hữu bởi: Interface Layer + cập nhật tích lũy.

    # ── Đầu ra và điều hướng ────────────────────────────────────
    final_response: Annotated[str, overwrite]
    # Phản hồi cuối cùng sẵn sàng gửi cho người dùng.
    # Reducer: overwrite.
    # Sở hữu bởi: Synth Agent.

    next_node: Annotated[str, overwrite]
    # Tín hiệu routing — node tiếp theo trong graph.
    # Giá trị hợp lệ: "kr_agent" | "psych_agent" | "synth_agent.md" | "END"
    # Reducer: overwrite.
    # Sở hữu bởi: Orchestrator Agent.

    # ── Xử lý lỗi ───────────────────────────────────────────────
    error_state: Annotated[str | None, overwrite]
    # Thông tin lỗi nếu có, kích hoạt fallback flow.
    # None khi hệ thống hoạt động bình thường.
    # Reducer: overwrite.

    # ── Bảo vệ vòng lặp ─────────────────────────────────────────
    iteration_count: Annotated[int, add]
    # Bộ đếm vòng lặp, tăng thêm 1 mỗi chu kỳ.
    # Ngưỡng: MAX_ITERATIONS = 8 — trả về END nếu vượt quá.
    # Reducer: add (+1) — KHÔNG ghi đè.
    # Sở hữu bởi: Orchestrator Agent.
```

### 4.2 Nguyên Tắc Thiết Kế Schema

- **"Cần thiết và đủ":** Chỉ lưu thông tin agents cần để ra quyết định tối ưu.
- **Mỗi field có một agent sở hữu duy nhất** — thi hành Separation of Concerns ở tầng dữ liệu.
- **`messages`** dùng `add_messages` (append) để bảo tồn thứ tự thời gian — Psych Agent cần điều này.
- **`iteration_count`** dùng `add` (+1) — quan trọng: KHÔNG overwrite vì mỗi agent cần cộng dồn riêng.

### 4.3 Năm Trạng Thái Tâm Lý (PsychStateEnum)

```python
class PsychStateEnum(str, Enum):
    AWARENESS     = "AWARENESS"      # Khách hàng đang khám phá, chưa có ý định rõ
    INTEREST      = "INTEREST"       # Đã thể hiện quan tâm đến loại sản phẩm
    CONSIDERATION = "CONSIDERATION"  # Đang so sánh, cân nhắc lựa chọn
    HESITATION    = "HESITATION"     # Có rào cản (giá, chất lượng, sự phù hợp)
    DECISION      = "DECISION"       # Sẵn sàng mua, cần CTA phù hợp
```

### 4.4 Session Persistence với Redis

```
Cấu trúc key: thread_id:checkpoint_id
              ↕
              UUID v4 : bước thực thi

TTL mặc định: 3600 giây (1 giờ)
```

**Luồng phục hồi phiên:**
1. Người dùng gửi tin nhắn mới với `session_id` đã biết
2. Controller lấy checkpoint gần nhất từ Redis
3. Hệ thống gắn tin nhắn mới vào `messages`
4. Tiếp tục thực thi — KHÔNG khởi tạo lại từ đầu

---

## 5. ORCHESTRATOR AGENT — TRUNG TÂM ĐIỀU PHỐI

### 5.1 Ba Chức Năng Cốt Lõi

1. **Phân tích ý định (Intent Analysis):** Phân tích ý định cấp cao từ tin nhắn và lịch sử hội thoại
2. **Đánh giá trạng thái (State Evaluation):** Xác định thông tin còn thiếu trong `ConversationState`
3. **Quyết định routing (Routing Decision):** Xác định agent chuyên biệt nào cần kích hoạt tiếp theo

### 5.2 Công Thức Routing

Routing được mô hình hóa là bài toán phân loại đa lớp:

```
a* = argmax_{a ∈ A} P_LLM(a | intent(S), context(S), history(S))
```

Trong đó:
- `A = {kr_agent, psych_agent, synth_agent, END}` — không gian hành động
- `S` — ConversationState hiện tại
- `P` — phân phối xác suất ước lượng bởi LLM qua **structured output (JSON)**

**Lý do dùng structured output thay vì free-text:** Giảm đáng kể tỷ lệ lỗi routing trong kiểm thử nội bộ.

### 5.3 Chain-of-Thought Routing

Orchestrator sử dụng framework CoT (Wei et al.) — bắt buộc agent suy luận qua 4 bước trước khi ra quyết định:

```
Bước 1: XÁC ĐỊNH ý định cấp cao của người dùng là gì?
        → Ví dụ: "Tìm kiếm sản phẩm quà tặng sinh nhật cho mẹ"

Bước 2: LIỆT KÊ thông tin đã có trong ConversationState
        → retrieved_products: [trống], psych_state: INTEREST, ...

Bước 3: XÁC ĐỊNH thông tin còn thiếu để tạo phản hồi tối ưu
        → Chưa có danh sách sản phẩm phù hợp → cần KR Agent

Bước 4: CHỌN agent tiếp theo
        → next_node = "kr_agent"
```

**Kết quả kiểm thử:** CoT cải thiện độ chính xác routing **18,7%** so với prompt không có CoT.

### 5.4 Bảo Vệ Vòng Lặp Vô Hạn

```python
MAX_ITERATIONS = 8

def conditional_router(state: ConversationState) -> str:
    # Ưu tiên 1: Kiểm tra lỗi
    if state["error_state"] is not None:
        return "error_handler"

    # Ưu tiên 2: Kiểm tra giới hạn vòng lặp
    if state["iteration_count"] > MAX_ITERATIONS:
        return END

    # Ưu tiên 3: Routing theo tín hiệu từ Orchestrator
    route = state["next_node"]
    return route if route in VALID_NODES else END

VALID_NODES = {"kr_agent", "psych_agent", "synth_agent.md"}
```

**Tại sao MAX_ITERATIONS = 8?** Một chu trình đầy đủ (Orchestrator → KR → Orchestrator → Psych → Orchestrator → Synth) mất 5 bước. Ngưỡng 8 cho phép tối đa một lần retry trong khi vẫn ngăn vòng lặp vô hạn.

### 5.5 Ví Dụ Routing JSON Output

```json
{
  "reasoning": "Người dùng hỏi về nhẫn cưới cho ngân sách 15 triệu. Chưa có sản phẩm nào được truy xuất. Cần KR Agent để tìm sản phẩm phù hợp trước.",
  "user_intent": "Tìm nhẫn cưới trong ngân sách 15 triệu",
  "missing_info": ["retrieved_products"],
  "next_node": "kr_agent"
}
```

---

## 6. KR AGENT — TRUY XUẤT TRI THỨC

### 6.1 Nguyên Tắc Thiết Kế

**"Retrieval-first, reasoning-later":** Toàn bộ thông tin sản phẩm trong phản hồi cuối phải có nguồn gốc từ tài liệu đã truy xuất — không suy luận từ tham số mô hình.

### 6.2 Pipeline Ba Giai Đoạn

#### Giai Đoạn 1: Cải Hóa và Mở Rộng Query

**Mục tiêu:** Trích xuất thực thể tìm kiếm và mở rộng với từ đồng nghĩa tiếng Việt.

```python
# Ví dụ query: "nhẫn cưới đẹp không quá 15 triệu"

extracted_entities = {
    "product_type": "nhẫn",
    "occasion": "cưới",
    "price_max": 15_000_000,
    "category": "nhẫn cưới"
}

expanded_queries = {
    "nhẫn đính hôn",      # Từ đồng nghĩa
    "nhẫn cưới",          # Query gốc
    "wedding ring",       # Tiếng Anh (index có thể chứa)
    "nhẫn hôn nhân",      # Biến thể
    "nhẫn cặp đôi"        # Khái niệm liên quan
}
```

**Lý do cần mở rộng query trong tiếng Việt:** Người dùng Việt dùng nhiều cách diễn đạt khác nhau cho cùng một sản phẩm; index có thể chứa cả thuật ngữ tiếng Anh trong mô tả kỹ thuật.

#### Giai Đoạn 2: Tìm Kiếm Lai (Hybrid Search)

Ba luồng tìm kiếm song song:

```
Query mở rộng
      │
      ├─── Dense Search ────► text-embedding-3-small (1536 dims)
      │                       Cosine similarity trên ChromaDB
      │                       NDCG@10 = 0.623 (tốt nhất cho tiếng Việt - benchmark MIRACL)
      │
      ├─── Sparse Search ───► BM25 keyword matching
      │                       Hiệu quả với: tên sản phẩm chính xác, mã SKU
      │
      └─── Metadata Filter ► Binary matching
                              category = "nhẫn cưới"
                              price ≤ 15,000,000
                              stock_status = True
```

**Công thức điểm tổng hợp:**

```
FinalScore(d) = λ₁ · DenseScore(d) + λ₂ · SparseScore(d) + λ₃ · MetaScore(d)
             = 0.50 · DenseScore    + 0.30 · SparseScore   + 0.20 · MetaScore
```

**Cách xác định trọng số (λ):** Grid search trên tập validation, đo bằng chỉ số `Recall@5`.
- `λ₁ = 0.50` — Dense search chiếm ưu thế vì hiểu ngữ nghĩa tốt nhất
- `λ₂ = 0.30` — BM25 quan trọng cho khớp chính xác tên/mã sản phẩm
- `λ₃ = 0.20` — Metadata filter đảm bảo kết quả trong ngân sách và còn hàng

`MetaScore` là giá trị nhị phân: 1 nếu sản phẩm thỏa tất cả bộ lọc, 0 nếu không.

#### Giai Đoạn 3: Xếp Hạng Lại và Đa Dạng Hóa

**Bước 3a — Cross-encoder Re-ranking:**
Top 20 kết quả từ Giai đoạn 2 được đánh giá lại bằng cross-encoder (so sánh cặp query–document), cho độ chính xác cao hơn bi-encoder.

**Bước 3b — Maximal Marginal Relevance (MMR):**

```
MMR(d_i) = argmax_{d_i ∈ D\S} [ λ · Sim(q, d_i) - (1-λ) · max_{d_j ∈ S} Sim(d_i, d_j) ]
```

Trong đó:
- `S` — tập tài liệu đã chọn
- `D\S` — tập tài liệu còn lại
- `λ` — cân bằng giữa tính liên quan và tính đa dạng

**Mục đích MMR:** Tránh trả về 5 sản phẩm rất giống nhau. Ví dụ: không trả về 5 chiếc nhẫn vàng 18K cùng mức giá; thay vào đó trả về các sản phẩm đa dạng về kiểu dáng, chất liệu, mức giá trong cùng category.

**Kết quả cuối:** Top-5 tài liệu → chuyển sang Synth Agent qua `ConversationState.retrieved_products`.

### 6.3 Graph RAG — Duyệt Đồ Thị Tri Thức

**Hạn chế của RAG thuần vector:** Không nắm bắt được quan hệ cấu trúc giữa các thực thể trong catalog sản phẩm.

**Graph RAG** xây dựng Knowledge Graph `G = (V, E)`:
- `V` — các đỉnh (thực thể): sản phẩm, danh mục, thương hiệu, dịp, mức giá
- `E` — các cạnh (quan hệ): "thuộc danh mục", "phù hợp với dịp", "trong khoảng giá"

**Cấu trúc đồ thị sản phẩm:**

```
"quà sinh nhật mẹ 60 tuổi"
        │
        ▼ (duyệt đồ thị)
    Dịp: sinh nhật
        │
        ▼
    Đối tượng: người lớn tuổi (60+)
        │
        ▼
    Phong cách: "luxury", "age-appropriate", "phong thủy"
        │
        ▼
    Danh mục: vòng tay, dây chuyền (loại trừ: nhẫn trẻ trung)
        │
        ▼
    Sản phẩm cụ thể: [danh sách được lọc theo graph]
```

**Điểm Graph RAG tổng hợp:**

```
Score(q, d) = α · VecSim(q, d) + β · GraphProx(q, d) + γ · EntMatch(q, d)
```

Trong đó α + β + γ = 1:
- `VecSim` — điểm cosine similarity
- `GraphProx` — độ gần trong đồ thị (normalized)
- `EntMatch` — điểm khớp thực thể cứng (binary hoặc fuzzy)

**Kết quả (Edge et al., Microsoft Research):** Graph RAG cải thiện **72%** trên các query phức tạp đa thực thể so với Naive RAG.

---

## 7. PSYCH AGENT — PHÂN TÍCH TÂM LÝ KHÁCH HÀNG

### 7.1 Đóng Góp Mới Của Nghiên Cứu

**Khác biệt cơ bản so với nghiên cứu trước:**

| Cách tiếp cận trước | Cách tiếp cận trong luận văn |
|---|---|
| Phân tích tâm lý là công cụ **hậu kỳ** (post-hoc) | Psych Agent là thành phần **chủ động, ảnh hưởng quyết định** trong MAS |
| Kết quả analytics để báo cáo | Kết quả trực tiếp thay đổi chiến lược tư vấn real-time |
| Không phải agent độc lập | Agent tự trị với trách nhiệm riêng |

### 7.2 Đặc Trưng Phân Loại

Psych Agent phân tích toàn bộ lịch sử hội thoại (tối đa 10 lượt gần nhất) với 4 nhóm đặc trưng:

**1. Đặc trưng từ vựng (Lexical Features):**

| Nhóm từ | Ví dụ tiếng Việt | Tín hiệu tâm lý |
|---|---|---|
| Từ do dự | "suy nghĩ", "có lẽ", "không chắc", "để xem" | HESITATION / CONSIDERATION |
| Từ so sánh | "hay là", "cái nào tốt hơn", "so với" | CONSIDERATION |
| Từ cam kết | "đặt ngay", "mua luôn", "lấy cái này" | DECISION |
| Từ khám phá | "có loại nào", "cho tôi xem", "tư vấn" | AWARENESS / INTEREST |

**2. Đặc trưng cú pháp (Syntactic Features):**
- Câu hỏi xác nhận: "đúng không?", "có phải...?"
- Câu phủ định: "không thích", "không phù hợp"
- Câu điều kiện: "nếu... thì tôi mới..."

**3. Đặc trưng cảm xúc (Sentiment Features):**
- Cực tính (polarity): tích cực / tiêu cực / trung tính
- Cường độ: nhẹ / vừa / mạnh

**4. Đặc trưng ngữ cảnh (Contextual Features):**
- Số lượt hội thoại đã qua
- Độ phức tạp query (đơn giản/phức tạp)
- Sản phẩm nào đã được đề cập trước đó

### 7.3 Phương Pháp Zero-Shot Classification

**Lý do chọn zero-shot LLM thay vì fine-tuned BERT/RoBERTa:**
- Không cần dữ liệu huấn luyện có nhãn — quan trọng vì **dữ liệu tiếng Việt được gán nhãn còn rất hiếm**
- Hou et al.: zero-shot LLM đạt F1 = **0.78** trên phân loại ý định mua hàng, cạnh tranh với model fine-tuned

**Prompt engineering:** Được thiết kế để trích xuất đầu ra JSON có cấu trúc.

### 7.4 Đầu Ra Structured JSON

```json
{
  "psych_state": "HESITATION",
  "psych_confidence": 0.89,
  "primary_concern": "price",
  "consult_strategy": "feel-felt-found",
  "reasoning": "Khách hàng dùng từ 'đắt quá' và 'suy nghĩ thêm', cho thấy rào cản về giá. Độ tin cậy cao (0.89) do nhiều tín hiệu nhất quán."
}
```

### 7.5 Mapping Trạng Thái → Chiến Lược Tư Vấn

| Trạng thái | Chiến lược điển hình | Mô tả |
|---|---|---|
| `AWARENESS` | `education` | Giới thiệu rộng, tập trung giáo dục về sản phẩm |
| `INTEREST` | `showcase` | Trình bày sản phẩm nổi bật, kích thích tò mò |
| `CONSIDERATION` | `comparison` + `social-proof` | So sánh ưu điểm, đưa đánh giá khách hàng khác |
| `HESITATION` | `feel-felt-found` | Đồng cảm → tái định vị giá trị → dẫn chứng |
| `DECISION` | `urgency` + `close` | Tạo urgency nhẹ, CTA rõ ràng, hỗ trợ chốt đơn |

**Kỹ thuật "Feel-Felt-Found" (cho HESITATION):**
> "Tôi hiểu bạn cảm thấy [rào cản]. Nhiều khách hàng của chúng tôi cũng từng nghĩ vậy [felt]. Nhưng sau khi [mua/sử dụng], họ nhận ra [giá trị thực sự] [found]."

---

## 8. SYNTH AGENT — TỔNG HỢP PHẢN HỒI

### 8.1 Ba Ràng Buộc Bất Biến

1. **Factual Grounding (Căn cứ thực tế):**
   - Toàn bộ thông tin sản phẩm PHẢI đến từ `retrieved_products` của KR Agent
   - Không được suy luận, bịa đặt, hoặc dùng kiến thức tham số của LLM để mô tả sản phẩm
   - Ngưỡng tolerance hallucination: **0%**

2. **Strategy Alignment (Tuân thủ chiến lược):**
   - Cấu trúc phản hồi PHẢI tuân theo `consult_strategy` từ Psych Agent
   - Ví dụ: nếu `consult_strategy = "feel-felt-found"` → phản hồi phải có cấu trúc cảm thông → kinh nghiệm chung → kết quả

3. **Natural Tone (Giọng điệu tự nhiên):**
   - Duy trì tiếng Việt tự nhiên, thân thiện, đúng văn hóa
   - Tránh văn phong máy móc, dịch literal từ tiếng Anh

### 8.2 Mô Hình AIDA

Cấu trúc phản hồi theo mô hình marketing AIDA:

```
A — ATTENTION (Thu hút)
    Mở đầu gắn với nhu cầu cụ thể của người dùng
    Ví dụ: "Với ngân sách 15 triệu cho nhẫn cưới, bạn hoàn toàn có thể..."

I — INTEREST (Gây hứng thú)
    Trình bày sản phẩm liên quan kèm điểm nổi bật
    Dựa trực tiếp vào retrieved_products

D — DESIRE (Khơi gợi mong muốn)
    Nhấn mạnh lợi ích cảm xúc + thực tế
    Điều chỉnh theo psych_state (vd: HESITATION → nhấn giá trị, không phải giá)

A — ACTION (Kêu gọi hành động)
    CTA được hiệu chỉnh theo trạng thái tâm lý
    DECISION → "Đặt hàng ngay hôm nay để..."
    CONSIDERATION → "Bạn có muốn xem thêm hình ảnh thực tế không?"
```

### 8.3 Chỉ Số Chất Lượng Phản Hồi (CRQ)

**Composite Response Quality — Weighted Sum Model:**

```
RQ = w₁ · Relevance + w₂ · Accuracy + w₃ · Persuasion + w₄ · Naturalness
   = 0.35 · Relevance + 0.30 · Accuracy + 0.20 · Persuasion + 0.15 · Naturalness
```

**Nguồn gốc trọng số:** Phỏng vấn 12 chuyên gia bán hàng cấp cao từ Pancharm. Mỗi thành phần được đánh giá bằng thang Likert 1–5 bởi LLM-as-a-Judge.

| Thành phần | Trọng số | Ý nghĩa |
|---|---|---|
| Relevance (Liên quan) | 35% | Phản hồi có đúng chủ đề người dùng hỏi không? |
| Accuracy (Chính xác) | 30% | Thông tin sản phẩm có đúng với nguồn không? |
| Persuasion (Thuyết phục) | 20% | Phản hồi có hiệu quả trong việc dẫn dắt mua hàng không? |
| Naturalness (Tự nhiên) | 15% | Giọng điệu có tự nhiên, phù hợp văn hóa Việt không? |

---

## 9. CHROMADB — CƠ SỞ DỮ LIỆU VECTOR

### 9.1 Ba Collection Sản Phẩm

```
ChromaDB
  │
  ├── product_overview     (USP + mô tả ngắn)
  │   Chunk: 256 tokens, overlap 32 tokens
  │   Mục đích: Câu hỏi tổng quát, gợi ý sản phẩm
  │
  ├── product_specs        (Thông số kỹ thuật chi tiết)
  │   Chunk: 512 tokens, overlap 64 tokens
  │   Mục đích: Câu hỏi kỹ thuật (độ tinh khiết vàng, kích thước, trọng lượng)
  │
  └── product_reviews      (Đánh giá, bằng chứng xã hội)
      Chunk: 384 tokens, overlap 48 tokens
      Mục đích: Câu hỏi về trải nghiệm, tin tưởng ("khách hàng dùng thế nào?")
```

**Lý do 3 collection thay vì 1:** KR Agent route query đến collection phù hợp với loại câu hỏi → giảm nhiễu, tăng precision so với tìm kiếm trong collection đơn nhất.

### 9.2 Semantic Chunking (Thay vì Fixed-size)

**Vấn đề với Fixed-size chunking:**
- Cắt ngay giữa câu, phá vỡ ngữ nghĩa
- Tách các thuộc tính liên quan của cùng sản phẩm vào chunks khác nhau

**Semantic Chunking algorithm:**

```
1. Tách văn bản thành các câu riêng lẻ
2. Tính embedding cho từng câu (text-embedding-3-small)
3. Tính cosine similarity giữa các câu liền kề
4. Xác định điểm cắt chunk: nơi similarity < threshold
5. Gộp các câu liền kề thành chunk

Ví dụ:
  "Nhẫn vàng 18K." (sim=0.92) "Trọng lượng 3.5g." → CÙNG CHUNK
  "Trọng lượng 3.5g." (sim=0.41) "Phù hợp làm quà cưới." → TÁCH CHUNK
```

**Dual-resolution representation (RAPTOR approach):**
- **Chunk-level embeddings:** Cho phép tìm kiếm chi tiết kỹ thuật cụ thể
- **Product summary embedding:** Một vector đại diện cho toàn bộ sản phẩm → xử lý query tổng quát

```
Ví dụ:
Query: "có sản phẩm nhẫn vàng không?"      → summary embedding đủ
Query: "độ tinh khiết vàng 18K là bao nhiêu?" → chunk-level embedding cần thiết
```

### 9.3 Metadata Schema và Hybrid Filtering

**Mỗi document được lưu kèm metadata chuẩn hóa:**

```python
metadata = {
    "product_id":    "PCH-RING-001",
    "product_name":  "Nhẫn Vàng 18K Phong Thủy Bình An",
    "category":      "nhẫn cưới",
    "brand":         "Pancharm",
    "price":         12_500_000,       # VND
    "price_range":   "10M-15M",
    "material":      "vàng 18K",
    "occasion":      ["cưới", "kỷ niệm"],
    "feng_shui_element": "kim",        # Kim/Mộc/Thủy/Hỏa/Thổ
    "stock_status":  True,
    "gender":        "unisex",
    "sku":           "PCH-18K-R-001"
}
```

**Ví dụ Hybrid Filtering trong code:**

```python
# KR Agent kết hợp Semantic + Metadata search
query_vector = embedding_model.embed_query("gold rings for wedding")

metadata_filters = {
    "category":     {"$eq": "nhẫn cưới"},
    "price":        {"$lte": 15_000_000},   # Ngân sách dưới 15 triệu
    "stock_status": {"$eq": True}           # Chỉ lấy hàng còn hàng
}

results = collection.query(
    query_embeddings=[query_vector],
    where=metadata_filters,    # Hard filter áp dụng trước
    n_results=20               # Lấy Top-20 để re-rank
)
```

### 9.4 HNSW Indexing

ChromaDB dùng thuật toán **HNSW (Hierarchical Navigable Small World)** mặc định:

- Độ phức tạp tìm kiếm: **O(log n)** — so với O(n) của brute-force
- Cấu hình: `M=16` (số kết nối mỗi node), `ef=200` (kích thước danh sách ứng viên khi tìm kiếm)
- Đảm bảo latency thấp và recall chính xác cao → thoải mái nằm trong target 700ms của KR Agent

### 9.5 Embedding Model

**text-embedding-3-small (OpenAI):**
- Kích thước vector: 1.536 chiều
- Benchmark MIRACL (đa ngôn ngữ): NDCG@10 = **0.623 cho tiếng Việt**
- Vượt trội so với: multilingual-E5 và LaBSE trên cùng benchmark
- Batch size: 100 documents/request

---

## 10. API VÀ GIAO TIẾP HỆ THỐNG

### 10.1 Hai Endpoint Chính

**1. POST /v1/chat — Đồng bộ (Synchronous)**

```
Request:
{
  "session_id": "uuid-v4",
  "message":    "Tôi muốn tìm nhẫn cưới khoảng 15 triệu",
  "user_id":    "user_123",        // optional
  "channel":    "web"              // web | mobile | zalo
}

Response:
{
  "session_id":      "uuid-v4",
  "response":        "Chào bạn! Với ngân sách 15 triệu...",
  "psych_state":     "INTEREST",
  "products_shown":  ["PCH-001", "PCH-002"],
  "latency_ms":      2750
}

Timeout: 30 giây
```

**2. GET /v1/chat/stream — Token Streaming (SSE)**

```
Server-Sent Events — token-by-token streaming
Phù hợp cho: trải nghiệm chat real-time trên giao diện
Content-Type: text/event-stream

data: {"token": "Chào"}
data: {"token": " bạn"}
data: {"token": "!"}
...
data: [DONE]
```

### 10.2 Rate Limiting

```
Thuật toán: Redis Token Bucket
Ngưỡng: 100 requests/phút/session
Lý do: Ngăn abuse, bảo vệ chi phí LLM API
```

### 10.3 CORS và Bảo Mật

```python
# Chỉ cho phép request từ domain đối tác bán lẻ được phê duyệt
CORS(app, allow_origins=APPROVED_RETAIL_DOMAINS)
```

### 10.4 Validation với Pydantic v2

Tất cả request/response đều qua Pydantic schemas để:
- Validate kiểu dữ liệu tự động
- Sinh OpenAPI documentation
- Nhất quán với chuẩn LLM specification

---

## 11. TRIỂN KHAI HẠ TẦNG

### 11.1 Stack Công Nghệ Đầy Đủ

| Thành phần | Công nghệ | Phiên bản | Cấu hình |
|---|---|---|---|
| Web Framework | FastAPI | 0.111.0 | 4 async workers, Uvicorn, Pydantic v2 |
| Agent Framework | LangGraph | 0.2.x | Redis Checkpointer, async graph execution |
| Vector Database | ChromaDB | 0.5.x | Persistent mode, HNSW M=16, ef=200 |
| LLM | Anthropic Claude API | — | Claude-3.5-Sonnet (main) + Claude-3-Haiku (fast paths) |
| Embedding | text-embedding-3-small | — | 1.536 dims, batch size 100 |
| Session/Cache | Redis | 7.2 | TTL=3600s, 2GB maxmemory, LRU eviction |
| Container | Docker Compose | 2.x | 5 services, health checks, auto-restart |
| Monitoring | Prometheus + Grafana | — | Latency p50/p95/p99, error rate, token usage |

### 11.2 Năm Docker Services

```yaml
services:
  api:        # FastAPI application
  chromadb:   # Vector database (persistent volume)
  redis:      # Session storage + checkpointer
  worker:     # Background embedding jobs (indexing mới)
  nginx:      # Reverse proxy + SSL termination
```

### 11.3 Mục Tiêu Latency

| Giai đoạn | Agent | Mục tiêu | Đo được |
|---|---|---|---|
| Hybrid Retrieval | KR Agent | ≤ 700ms | — |
| Psychological Analysis | Psych Agent | ≤ 450ms | — |
| Response Synthesis | Synth Agent | ≤ 800ms | — |
| **End-to-end** | **Tất cả** | **≤ 3.000ms** | **2.800ms** |

**Cơ sở target 3 giây:** Thời gian phản hồi > 3 giây gắn liền với tỷ lệ bỏ phiên tăng đo được trong các benchmark ngành cho conversational AI. Tham khảo từ JD.com Hybrid-MACRS: thiết kế agent-search lai giảm 70% first-token latency so với single-agent baseline.

---

## 12. KHUNG ĐÁNH GIÁ CARS

### 12.1 Định Nghĩa CARS

**CARS (Conversational AI Retail Score)** — khung đánh giá đa chiều được luận văn này đề xuất lần đầu cho AI bán lẻ tiếng Việt.

### 12.2 Năm Chỉ Số

| Ký hiệu | Tên | Định nghĩa | Trọng số | Benchmark | Đo bằng |
|---|---|---|---|---|---|
| **CR** | Conversion Rate | % hội thoại dẫn đến ý định mua hàng | 35% | ≥ 40% | Human annotation |
| **IA** | Information Accuracy | % thông tin sản phẩm chính xác | 30% | ≥ 90% | So sánh ground truth |
| **CC** | Context Consistency | Tính liên tục và mạch lạc (0–1) | 20% | ≥ 0.85 | LLM-as-a-Judge |
| **RL** | Response Latency | Thời gian phản hồi end-to-end (giây) | 10% | ≤ 3.0s | Đo thực nghiệm |
| **US** | User Satisfaction | Điểm khảo sát sau hội thoại (1–5) | 5% | ≥ 4.0/5 | Khảo sát (n=50) |

**Lý do trọng số CR cao nhất (35%):** Tỷ lệ chuyển đổi là chỉ số kinh doanh trực tiếp nhất — phản ánh liệu hệ thống có thực sự tăng doanh thu hay không.

### 12.3 Công Thức CARS

```
CARS = 0.35·CR + 0.30·IA + 0.20·CC + 0.10·(1 - RL_norm) + 0.05·US_norm
```

**Chuẩn hóa:**
```
RL_norm = min(RL / 3.0, 1.0)      # Latency thấp hơn → điểm cao hơn
US_norm = (US - 1) / 4             # Chuyển từ thang 1-5 sang 0-1
```

### 12.4 Phương Pháp Đánh Giá

**Mô phỏng dựa trên mô hình (Model-based simulation):**
- Dùng Claude Sonnet 3.5 để mô phỏng luồng thực thi từng agent
- Đánh giá đầu ra theo tập dataset thực từ Pancharm

**Tập dữ liệu đánh giá:**
- 100 sản phẩm trang sức phong thủy
- ~1.000 log hội thoại thực (từ đội ngũ bán hàng Pancharm)
- Bao gồm: tư vấn ban đầu → so sánh → xử lý phản đối → chốt đơn

---

## 13. KẾT QUẢ THỰC NGHIỆM

### 13.1 So Sánh Toàn Diện

| Hệ thống | CR (%) | IA (%) | CC | RL (s) | US (/5) |
|---|---|---|---|---|---|
| Rule-based Chatbot | 18.3 | 72.1 | 0.61 | 0.8 | 2.9 |
| Single-agent GPT-4o | 28.7 | 79.3 | 0.74 | 2.0 | 3.3 |
| Single-agent Claude Sonnet | 31.4 | 81.6 | 0.76 | 2.1 | 3.4 |
| MAS không có Psych Agent | 38.2 | 88.4 | 0.87 | 2.5 | 3.8 |
| MAS không có Graph RAG | 35.1 | 82.7 | 0.84 | 2.3 | 3.6 |
| **MAS Đề Xuất (Đầy Đủ)** | **42.3** | **91.2** | **0.91** | **2.8** | **4.3** |

### 13.2 Phân Tích Đóng Góp Từng Thành Phần

**Đóng góp của Psych Agent:**
```
MAS đầy đủ:           CR = 42.3%
MAS không Psych:      CR = 38.2%
Chênh lệch:          +4.1% tuyệt đối → +10.7% tương đối
```
→ Cá nhân hóa chiến lược tư vấn theo trạng thái tâm lý thực sự tăng tỷ lệ chuyển đổi.

**Đóng góp của Graph RAG:**
```
MAS đầy đủ:          IA = 91.2%
MAS không Graph RAG: IA = 82.7%
Chênh lệch:         +8.5% tuyệt đối
```
→ Graph RAG là yếu tố then chốt để vượt ngưỡng IA ≥ 90%.

**So với chatbot hiện tại:**
- Cải thiện tỷ lệ chốt đơn: **+34.7%**
- Tự động hóa **70–80%** quy trình tư vấn

### 13.3 Case Study: Xử Lý Trạng Thái HESITATION

**Kịch bản:** Khách hàng quan tâm đến vòng tay bạc phong thủy Pancharm nhưng lo ngại về giá.

**Psych Agent phát hiện:**
```json
{
  "psych_state": "HESITATION",
  "psych_confidence": 0.89,
  "primary_concern": "price",
  "consult_strategy": "feel-felt-found"
}
```

**Synth Agent phản hồi (theo "Feel-Felt-Found"):**
> "Tôi hiểu bạn đang băn khoăn về giá — nhiều khách hàng của Pancharm cũng từng có cùng suy nghĩ đó. Nhưng sau khi sử dụng, họ chia sẻ rằng chất lượng bạc 925 và năng lượng phong thủy mang lại cảm giác yên tâm lâu dài hơn nhiều so với mức giá chênh lệch. Bạn có muốn tôi gửi thêm một vài đánh giá thực tế từ khách hàng không?"

→ **Không** giảm giá thẳng thắn → **Tái định vị giá trị** theo tâm lý cụ thể.

### 13.4 Case Study: Tư Vấn Dịp Đặc Biệt (Graph RAG)

**Query:** "Quà sinh nhật cho mẹ 60 tuổi"

**Graph traversal:**
```
"sinh nhật mẹ 60 tuổi"
    → Dịp: sinh nhật + người cao tuổi
    → Phong cách: luxury, age-appropriate, phong thủy bình an
    → Loại trừ: nhẫn trẻ trung, vòng cá tính
    → Đề xuất: vòng tay Long Phụng, dây chuyền Bình An, nhẫn Thọ
```

→ Không cần người dùng liệt kê đầy đủ tiêu chí — hệ thống tự suy diễn qua đồ thị.

---

## 14. HẠN CHẾ VÀ HƯỚNG PHÁT TRIỂN

### 14.1 Hạn Chế Hiện Tại

| Hạn chế | Nguyên nhân | Ảnh hưởng |
|---|---|---|
| Sarcasm / tiếng lóng "Gen Z" | Không có dữ liệu huấn luyện đặc thù | Psych Agent phân loại sai trạng thái tâm lý |
| Không hỗ trợ đa phương thức | Thiếu Vision module | Không xử lý được "sản phẩm trong ảnh này là gì?" |

### 14.2 Năm Hướng Phát Triển

| # | Hướng | Mô tả kỹ thuật | Lợi ích dự kiến |
|---|---|---|---|
| 1 | **Multimodal** | Tích hợp Vision-Language Model (VLM) | Khách hàng upload ảnh → hỏi về sản phẩm |
| 2 | **RLHF** | Fine-tune Synth Agent trên dữ liệu hội thoại thực có nhãn kết quả (chốt/không chốt) | Vượt giới hạn zero-shot prompting |
| 3 | **User Profile RAG** | Tích hợp CRM: lịch sử mua hàng, sở thích → đưa vào ConversationState | Dự kiến +15–20% CR |
| 4 | **Streaming MAS** | KR Agent và Psych Agent chạy song song thay vì tuần tự | Giảm latency từ 2.8s → ~1.8–2.0s |
| 5 | **Đa ngôn ngữ ASEAN** | Code-switching: tiếng Việt + tiếng Anh + Thái + Indonesian | Mở rộng thị trường xuất khẩu |

---

## 15. BẢNG TRA CỨU CÔNG THỨC

### 15.1 Công Thức Hệ Thống

```
# LangGraph state transition
S(t+1) = Reducer( S(t), Δ_node(S(t)) )

# Orchestrator routing
a* = argmax_{a∈A} P_LLM(a | intent(S), context(S), history(S))
A = {kr_agent, psych_agent, synth_agent, END}

# Cosine similarity (dùng cho vector search)
sim(q, d) = (q·d) / (||q|| · ||d||)
```

### 15.2 Công Thức KR Agent

```
# Hybrid search score
FinalScore(d) = 0.50·DenseScore(d) + 0.30·SparseScore(d) + 0.20·MetaScore(d)

# Graph RAG aggregated score
Score(q,d) = α·VecSim(q,d) + β·GraphProx(q,d) + γ·EntMatch(q,d)
             α + β + γ = 1

# Maximal Marginal Relevance
MMR(d_i) = argmax_{d_i ∈ D\S} [ λ·Sim(q,d_i) - (1-λ)·max_{d_j∈S} Sim(d_i,d_j) ]
```

### 15.3 Công Thức Đánh Giá

```
# CARS composite score
CARS = 0.35·CR + 0.30·IA + 0.20·CC + 0.10·(1-RL_norm) + 0.05·US_norm
RL_norm = min(RL/3.0, 1.0)
US_norm = (US-1)/4

# Composite Response Quality (Synth Agent)
RQ = 0.35·Relevance + 0.30·Accuracy + 0.20·Persuasion + 0.15·Naturalness
```

### 15.4 Thông Số Quan Trọng

```
MAX_ITERATIONS   = 8          # Giới hạn vòng lặp Orchestrator
REDIS_TTL        = 3600s      # Thời gian sống phiên (1 giờ)
RATE_LIMIT       = 100 req/min/session
EMBEDDING_DIMS   = 1536       # text-embedding-3-small
HNSW_M           = 16         # ChromaDB HNSW connections per node
HNSW_EF          = 200        # ChromaDB HNSW search size
PSYCH_HISTORY    = 10 turns   # Số lượt Psych Agent phân tích
KR_TOP_K_FINAL   = 5          # Sản phẩm truyền sang Synth Agent
KR_TOP_K_RERANK  = 20         # Sản phẩm đưa vào re-ranking

# Trọng số Hybrid Search
λ₁ (Dense)    = 0.50
λ₂ (Sparse)   = 0.30
λ₃ (Metadata) = 0.20
```

---

*Tài liệu này được tạo từ `documents/thesis_report.md` để làm bối cảnh kỹ thuật cho các phiên làm việc với Claude Code.*
*Phiên bản tóm tắt tiếng Anh: `documents/thesis_summary.md`*
