MAX_ITERATIONS = 8

VALID_NODES = {"kr_agent", "psych_agent", "synth_agent", "order_lookup", "error_handler"}

# Hybrid search weights — tuned via grid search trên Recall@5 (thesis §3.2.2)
# Search range: dense ∈ [0.3,0.7], sparse ∈ [0.1,0.4], meta ∈ [0.1,0.3], step=0.1
# Kết quả: dense=0.5 cho dense retrieval dominance (embedding model tốt cho tiếng Việt)
LAMBDA_DENSE = 0.50
LAMBDA_SPARSE = 0.30
LAMBDA_META = 0.20

# MMR λ: 0.7 relevance / 0.3 diversity — nghiêng về relevance vì catalog nhỏ (~200 SKU)
# Nếu catalog mở rộng >1000 SKU, cân nhắc giảm xuống 0.6 để tăng diversity
MMR_LAMBDA = 0.7

# Popularity boost cho sản phẩm "hot" (attributes.is_hot) — cộng thêm ngoài trọng số
# dense/sparse/meta đã tune sẵn, chỉ đủ để phá tie giữa các sản phẩm có độ liên quan
# xấp xỉ nhau, KHÔNG đủ lớn để một sản phẩm hot nhưng lạc đề vượt lên sản phẩm liên quan hơn.
POPULARITY_BOOST = 0.05

# TOP_K_INITIAL=20: đủ candidates cho BM25 re-rank, không quá lớn để tránh noise
# TOP_K_FINAL=5: giới hạn context Synth Agent (~150 tokens/product × 5 = ~750 tokens)
TOP_K_INITIAL = 20
TOP_K_FINAL = 5

# ChromaDB collection names (multi-granularity strategy)
COLLECTION_OVERVIEW = "product_overview"   # 256 tokens, 32 overlap — general queries
COLLECTION_SPECS = "product_specs"         # 512 tokens, 64 overlap — technical detail
COLLECTION_REVIEWS = "product_reviews"     # 384 tokens, 48 overlap — trust/experience

# ChromaDB ML training collections — populated live from conversation turns
COLLECTION_TRAINING_CONV = "training_conversations"      # (user_query, bot_response) pairs per turn
COLLECTION_TRAINING_PSYCH = "training_psych_labels"      # (conv_history, psych_label) pairs per turn
COLLECTION_TRAINING_SUCCESS = "training_sessions_success" # full session transcript khi sale thành công

# Embedding model — local sentence-transformers, no API key required
# paraphrase-multilingual-MiniLM-L12-v2: multilingual (50+ langs incl. Vietnamese), 384 dims, ~420MB
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIMS = 384

# Psychological states (zero-shot classification targets)
PSYCH_STATES = ["CURIOUS", "INTERESTED", "HESITATION", "COMMITTED", "OBJECTING"]

# Ngưỡng psych_confidence đủ tin cậy để bỏ qua psych_agent — khớp với
# bảng định tuyến trong resources/prompt/orchestrator_agent.md
PSYCH_CONFIDENCE_THRESHOLD = 0.6

# Từ vòng lặp này (cùng 1 lượt chat) trở đi, ép next_node=synth_agent nếu chưa có
# final_response — khớp với ràng buộc "iteration_count ≥ 6" trong orchestrator_agent.md
ORCHESTRATOR_FORCE_SYNTH_ITERATION = 6

# Session TTL in Redis (seconds)
SESSION_TTL = 3600

# Rate limiting
RATE_LIMIT_RPM = 100
