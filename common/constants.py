MAX_ITERATIONS = 8

VALID_NODES = {"kr_agent", "psych_agent", "synth_agent", "error_handler"}

# Hybrid search weights — determined via grid search on Recall@5 (thesis §3.2.2)
LAMBDA_DENSE = 0.50
LAMBDA_SPARSE = 0.30
LAMBDA_META = 0.20

# MMR diversity/relevance balance
MMR_LAMBDA = 0.7

# Retrieval pipeline sizes
TOP_K_INITIAL = 20   # candidates before re-rank
TOP_K_FINAL = 5      # results passed to Synth Agent

# ChromaDB collection names (multi-granularity strategy)
COLLECTION_OVERVIEW = "product_overview"   # 256 tokens, 32 overlap — general queries
COLLECTION_SPECS = "product_specs"         # 512 tokens, 64 overlap — technical detail
COLLECTION_REVIEWS = "product_reviews"     # 384 tokens, 48 overlap — trust/experience

# Embedding model (outperforms multilingual-E5/LaBSE on Vietnamese MIRACL benchmark)
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 1536

# Psychological states (zero-shot classification targets)
PSYCH_STATES = ["CURIOUS", "INTERESTED", "HESITATION", "COMMITTED", "OBJECTING"]

# Session TTL in Redis (seconds)
SESSION_TTL = 3600

# Rate limiting
RATE_LIMIT_RPM = 100
