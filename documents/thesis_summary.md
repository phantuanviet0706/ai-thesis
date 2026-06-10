# Thesis Summary: Multi-Agent System Design for Retail Customer Support

> **Author:** Phan Tuấn Việt | **Supervisor:** PhD. Bùi Văn Hiệu | **Co-Supervisor:** PhD. Trương Công Đoàn
> **Institution:** FPT School of Business & Technology | **Completion:** May 2026

---

## 1. PROBLEM STATEMENT

**Context:** Vietnamese e-commerce is growing rapidly (USD 32B in 2024, +27% YoY). Consumers average 6.5 online purchases/month and expect personalized, consultative interactions.

**Core Problem:** Existing single-agent chatbots fail because:
- ~29% fail at intent recognition in multi-turn conversations (Grand View Research)
- Architecturally limited to transactional queries, not consultative flows
- Cause software fragmentation → hallucinated product info → lower conversion rates

**Research Question:** How can multiple specialized agents be integrated to maintain consistent conversational flow while improving customer conversion rates?

**Scope:** Feng shui jewelry retail, Vietnamese market, 2025–2026 period (Pancharm startup).

---

## 2. SYSTEM ARCHITECTURE

### 2.1 Four Specialized Agents

| Agent | Role | Key Output |
|---|---|---|
| **Orchestrator** | Intent analysis, routing decisions via CoT | `next_node` routing signal |
| **KR Agent** | 3-stage GraphRAG product retrieval | `retrieved_products` (Top-5) |
| **Psych Agent** | Zero-shot customer psychology classification | `psych_state`, `consult_strategy` |
| **Synth Agent** | Final response generation (AIDA model) | `final_response` |

### 2.2 Four-Layer Architecture

```
Layer 1: Interface Layer       → REST API, auth, rate limiting (100 req/min), session init
Layer 2: Orchestration Layer   → Orchestrator Agent, LangGraph DCG routing
Layer 3: Specialized Layer     → KR Agent + Psych Agent + Synth Agent
Layer 4: Data/Infrastructure   → ChromaDB + Redis + LLM API
```

### 2.3 Design Principles (6)
1. **Separation of Concerns** — each agent has one well-defined responsibility
2. **Divide and Conquer** — decompose complex consultation into sub-problems
3. **Centralized State Management** — single `ConversationState` TypedDict
4. **Observability** — comprehensive logging at every step
5. **Resilience** — Redis checkpoint-based recovery (TTL 3600s)
6. **Graceful Degradation** — maintains service even when individual agents fail

---

## 3. CORE TECHNOLOGIES

### 3.1 LangGraph (Orchestration Framework)

- Uses **DCG (Directed Cyclic Graph)** — enables loops, conditional branching, parallel execution
- State management via `TypedDict` + reducer functions: `S_{t+1} = Reducer(S_t, Δ_node(S_t))`
- Reducer types: `add` (append for Lists), `overwrite` (scalar fields), custom (dict merge, etc.)
- **Checkpointers:** SQLite / Redis / PostgreSQL for session persistence

**Chosen over:** AutoGen (peer-to-peer, less control), CrewAI (in-memory only), AgentVerse (distributed)

### 3.2 ConversationState Schema

```python
class ConversationState(TypedDict):
    messages:           Annotated[List[BaseMessage], add]       # Full conversation history
    user_intent:        str                                      # Orchestrator analysis
    retrieved_products: Annotated[List[ProductDoc], overwrite]  # Top-k from ChromaDB
    retrieval_scores:   Annotated[List[float], overwrite]
    psych_state:        Annotated[PsychStateEnum, overwrite]    # 5 psychological states
    psych_confidence:   Annotated[float, overwrite]             # 0.0–1.0
    primary_concern:    Annotated[str | None, overwrite]
    consult_strategy:   Annotated[str, overwrite]
    session_metadata:   Annotated[Dict[str, Any], merge]
    final_response:     Annotated[str, overwrite]
    next_node:          Annotated[str, overwrite]               # Routing signal
    error_state:        Annotated[str | None, overwrite]
    iteration_count:    Annotated[int, add]                     # Loop protection (MAX=8)
```

### 3.3 LangGraph Routing Logic

```python
def conditional_router(state: ConversationState) -> str:
    if state["error_state"] is not None:
        return "error_handler"
    if state["iteration_count"] > MAX_ITERATIONS:  # MAX_ITERATIONS = 8
        return END
    route = state["next_node"]
    return route if route in VALID_NODES else END
```

**Routing formula:** `a* = argmax P_LLM(a | intent(S), context(S), history(S))`
where `A = {kr_agent, psych_agent, synth_agent, END}`

---

## 4. KNOWLEDGE RETRIEVAL (KR AGENT) — GraphRAG

### 4.1 Three-Stage Pipeline

**Stage 1: Query Reformulation**
- Extract entities: products, categories, price ranges, occasions, brands
- Expand with Vietnamese synonyms: "nhẫn cưới" → {"nhẫn đính hôn", "nhẫn hôn nhân", "wedding ring"}

**Stage 2: Hybrid Search**
```
FinalScore(d) = λ₁·DenseScore + λ₂·SparseScore + λ₃·MetaScore
              = 0.50·DenseScore + 0.30·SparseScore + 0.20·MetaScore
```
- **Dense:** `text-embedding-3-small` (1536 dims) — NDCG@10 = 0.623 for Vietnamese (best multilingual)
- **Sparse:** BM25 — effective for product names, SKU codes
- **Meta:** Binary filter (category, price range, stock status)

**Stage 3: Re-ranking & Diversity**
```
MMR(d_i) = argmax[λ·Sim(q,d_i) - (1-λ)·max_{d_j∈S} Sim(d_i,d_j)]
```
→ Top 20 → cross-encoder re-rank → MMR diversity → **Top 5 to Synth Agent**

### 4.2 Graph RAG Score
```
Score(q,d) = α·VecSim(q,d) + β·GraphProx(q,d) + γ·EntMatch(q,d)
```
Where α+β+γ=1. Graph structure: `Product → Category → Brand → Occasion → Price Range`

### 4.3 ChromaDB Collections (3)

| Collection | Content | Chunk Size | Use Case |
|---|---|---|---|
| `product_overview` | USP, short descriptions | 256 tokens, 32 overlap | General queries |
| `product_specs` | Technical specs | 512 tokens, 64 overlap | Technical details |
| `product_reviews` | Reviews, social proof | 384 tokens, 48 overlap | Trust/experience queries |

**Indexing:** HNSW algorithm — O(log n) complexity, M=16, ef=200

### 4.4 Semantic Chunking (vs Fixed-size)
- Split at semantic breakpoints where cosine similarity between consecutive sentence embeddings < threshold
- Dual-resolution: chunk-level embeddings + product summary embedding (RAPTOR approach)

---

## 5. PSYCHOLOGY AGENT (PSYCH AGENT)

**Novel contribution:** Real-time customer psychology as a first-class agent (not post-hoc analytics)

**Input:** Full conversation history (up to last 10 turns)

**Classification features:**
- **Lexical:** hesitation ("suy nghĩ", "có lẽ"), comparative ("hay là"), commitment ("đặt ngay")
- **Syntactic:** confirmation questions, negative sentences
- **Sentiment:** polarity and intensity
- **Contextual:** conversation turn count, query complexity

**Method:** Zero-shot LLM classification → F1=0.78 on purchase intent (no annotated data needed)

**Output JSON:**
```json
{
  "psych_state": "HESITATION",       // 5 possible states
  "psych_confidence": 0.89,
  "primary_concern": "price",
  "consult_strategy": "feel-felt-found"
}
```

---

## 6. SYNTHESIS AGENT (SYNTH AGENT)

**Three constraints:**
1. **Factual Grounding** — all product info from KR Agent only (zero hallucination tolerance)
2. **Strategy Alignment** — response structure follows `consult_strategy` from Psych Agent
3. **Natural Tone** — Vietnamese cultural register

**Response structure:** AIDA model
- **A**ttention → opening tied to user's specific need
- **I**nterest → relevant product presentation
- **D**esire → emotional + functional benefit articulation
- **A**ction → CTA calibrated to psychological state

**Quality metric — Composite Response Quality (CRQ):**
```
RQ = 0.35·Relevance + 0.30·Accuracy + 0.20·Persuasion + 0.15·Naturalness
```
(weights from interviews with 12 senior sales specialists)

---

## 7. EVALUATION FRAMEWORK — CARS

**CARS (Conversational AI Retail Score):**
```
CARS = 0.35·CR + 0.30·IA + 0.20·CC + 0.10·(1 - RL_norm) + 0.05·US_norm
```

| Metric | Definition | Weight | Benchmark |
|---|---|---|---|
| **CR** | Conversion Rate (% leading to purchase intent) | 35% | ≥ 40% |
| **IA** | Information Accuracy (% accurate product info) | 30% | ≥ 90% |
| **CC** | Context Consistency (0–1, logical flow) | 20% | ≥ 0.85 |
| **RL** | Response Latency (seconds) | 10% | ≤ 3.0s |
| **US** | User Satisfaction (1–5 Likert) | 5% | ≥ 4.0/5 |

---

## 8. EXPERIMENTAL RESULTS

**Dataset:** 100 feng shui jewelry products, ~1,000 real conversation logs (Pancharm)

| System | CR (%) | IA (%) | CC | RL (s) | US (/5) |
|---|---|---|---|---|---|
| Rule-based Chatbot | 18.3 | 72.1 | 0.61 | 0.8 | 2.9 |
| Single-agent GPT-4o | 28.7 | 79.3 | 0.74 | 2.0 | 3.3 |
| Single-agent Claude Sonnet | 31.4 | 81.6 | 0.76 | 2.1 | 3.4 |
| MAS w/o Psych Agent | 38.2 | 88.4 | 0.87 | 2.5 | 3.8 |
| MAS w/o Graph RAG | 35.1 | 82.7 | 0.84 | 2.3 | 3.6 |
| **Full MAS (Proposed)** | **42.3** | **91.2** | **0.91** | **2.8** | **4.3** |

**Key findings:**
- Psych Agent: +10.9% CR vs MAS without it
- Graph RAG: pushes IA above 90% threshold
- Overall: +34.7% deal-closing improvement vs existing chatbots
- Automates 70–80% of consultation process

---

## 9. DEPLOYMENT STACK

```yaml
Web Framework:    FastAPI 0.111.0 (4 async workers, Uvicorn, Pydantic v2)
Agent Framework:  LangGraph 0.2.x (Redis Checkpointer, async graph)
Vector DB:        ChromaDB 0.5.x (persistent, HNSW M=16, ef=200)
LLM:              Anthropic Claude API (Claude-3.5-Sonnet + Claude-3-Haiku)
Embedding:        text-embedding-3-small (1536 dims, batch=100)
Session/Cache:    Redis 7.2 (TTL=3600s, 2GB maxmemory, LRU eviction)
Container:        Docker Compose 2.x (5 services, health checks)
Monitoring:       Prometheus + Grafana (latency p50/p95/p99, error rate, token usage)
```

**API Endpoints:**
- `POST /v1/chat` — synchronous (30s timeout)
- `GET /v1/chat/stream` — Server-Sent Events (token streaming)

**Rate limiting:** 100 req/min/session via Redis Token Bucket algorithm

---

## 10. LATENCY TARGET

**Target:** ≤ 3 seconds end-to-end

| Stage | Target |
|---|---|
| Hybrid Retrieval (KR Agent) | ≤ 700ms |
| Psychological Analysis (Psych Agent) | ≤ 450ms |
| Response Synthesis (Synth Agent) | ≤ 800ms |
| **Actual end-to-end** | **2.8s** |

---

## 11. KNOWN LIMITATIONS & FUTURE WORK

**Current limitations:**
- Sarcasm / "Gen Z" Vietnamese slang → Psych Agent misclassification
- No multimodal support (vision) — critical gap for jewelry retail

**Future directions:**
1. **Multimodal:** Vision-Language Models for product image queries
2. **RLHF:** Fine-tune Synth Agent on labeled conversation outcomes
3. **User Profile RAG:** CRM integration → projected +15–20% CR
4. **Streaming MAS:** Parallel KR+Psych execution → target 1.8–2.0s latency
5. **Multilingual:** English/Thai/Indonesian code-switching for ASEAN markets

---

## 12. KEY FORMULAS REFERENCE

```
# Orchestrator routing
a* = argmax_{a∈A} P_LLM(a | intent(S), context(S), history(S))

# KR Agent hybrid score
FinalScore = 0.50·Dense + 0.30·Sparse + 0.20·Meta

# Graph RAG aggregated score
Score(q,d) = α·VecSim + β·GraphProx + γ·EntMatch  (α+β+γ=1)

# MMR diversity
MMR(d_i) = argmax[λ·Sim(q,d_i) - (1-λ)·max_{d_j∈S} Sim(d_i,d_j)]

# CARS composite score
CARS = 0.35·CR + 0.30·IA + 0.20·CC + 0.10·(1-RL_norm) + 0.05·US_norm

# Synth Agent response quality
RQ = 0.35·Relevance + 0.30·Accuracy + 0.20·Persuasion + 0.15·Naturalness

# LangGraph state transition
S_{t+1} = Reducer(S_t, Δ_node(S_t))
```

---

*Source: `documents/thesis_report.md` — Full MAS system for Vietnamese feng shui jewelry retail consultation (Pancharm startup)*
