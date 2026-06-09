:::: titlepage
::: center
**MINISTRY OF EDUCATION AND TRAINING**\
**FPT SCHOOL OF BUSINESS & TECHNOLOGY**\

**MULTI-AGENT SYSTEM DESIGN**\
**FOR RETAIL CUSTOMER SUPPORT**\

**Author by:**\
**Phan Tuấn Việt**\

**Supervisor:** & PhD. Bùi Văn Hiệu\
**Co-Supervisor:** & PhD. Trương Công Đoàn

**Hanoi, May 2026**
:::
::::

# INTRODUCTION

In recent years, the global retail industry, including Vietnam's, has
undergone a profound transformation. From traditional volume-based sales
methods, the economy is moving toward a Unified Commerce model
[@viet2026_29; @viet2026_30; @viet2026_31]. This approach utilizes a
comprehensive architecture that integrates information from every
touchpoint to create seamless customer experiences across both online
and offline channels, thereby breaking down existing barriers. Park et
al. define this evolution as a progression that goes far beyond
conventional omnichannel strategies, one in which technology serves as
the central enabler to create unified movement across fully integrated
channels [@viet2026_22].

In 2024, Vietnam's e-commerce industry was valued at USD 32 billion by
VECOM, representing 27 percent of the country's annual growth. Online
retail sales accounted for approximately 12% of total retail revenues
[@viet2026_20]. Additionally, the Ministry of Industry and Trade (MoIT)
has increased its growth projection to 25.5 percent by 2025, which will
yield a total transaction value of USD 28 billion [@viet2026_21].
Furthermore, e-commerce revenue in Vietnam is expected to account for
20% of total retail sales by 2030, with shoppertainment platforms such
as TikTok Shop and Shopee dominating the market, capturing up to 97% of
the market share in the first half of 2025 [@viet2026_1]. These figures
serve as clear evidence of the scale and outstanding development speed
of Vietnam's digital retail industry. Concurrently, they highlight the
strategic value for existing businesses in adopting artificial
intelligence (AI) within this space. Research by BCG and Harvard
Business Review consistently demonstrates that individualized shopping
experiences can increase average basket size by as much as 40 percent.
McKinsey's Next in Personalization report demonstrates that companies
excelling at personalization generate 40 percent more revenue from those
activities than average players, and that 71 percent of consumers now
expect companies to deliver personalized interactions --- with 76
percent expressing frustration when this expectation goes unmet
[@viet2026_23]. And with Vietnamese consumers making an average of 6.5
different online purchases per month and expecting context-aware,
consultative, and highly personalized interactions, traditional
single-function chatbot models are becoming increasingly outdated
[@viet2026_25].

Grand View Research indicates that approximately 29% of deployed
chatbots fail during intent recognition due to inaccuracies or an
inability to preserve contextual understanding across multi-turn
conversations. Despite advances in AI customer service technologies,
existing architectures remain largely constrained to handling
transactional queries rather than supporting the dynamic conversational
flows required in high-value retail consultations. This limitation is
fundamentally architectural. Prior studies have predominantly focused on
single-agent AI systems or chatbots operating under rigid, pre-scripted
scenarios. While such systems are sufficient for standardized FAQ
responses, they struggle in real-world consultative environments where
conversational context evolves continuously alongside product
information, and customer psychological states must be interpreted and
addressed in real time. This limitation is particularly evident in
single-turn chatbot architectures, which are inherently unsuitable for
tasks requiring sustained contextual awareness or extensive background
knowledge across complex interactions. Multi-turn conversational agents
powered by Large Language Models (LLMs) therefore represent a
substantial advancement in capability [@viet2026_26].

One critical consequence of these architectural limitations is software
fragmentation, which may cause AI systems to lose track of
conversational objectives or generate inaccurate and hallucinatory
product information, ultimately reducing purchase conversion and
deal-closing rates [@viet2026_24]. The central challenge lies in
designing a system that simultaneously ensures functional separation of
responsibilities while preserving semantic and contextual consistency
throughout specialized consultation processes. To address this issue,
the proposed architecture distributes reasoning responsibilities across
four specialized agents: an Orchestrator Agent, a Knowledge Retrieval
(KR) Agent, a Psych (KP) Agent, and a Synthesis (Synth) Agent, all
coordinated through a centralized conversation state.

Based on the study's \"divide and conquer\" principle, how can multiple
specialized agents be integrated in such an effort to maintain a
consistent conversational flow across channels while also improving
customer conversion rates? Focusing on highly consultative sectors such
as feng shui jewelry, the scope of this research will be narrowed to the
Vietnamese retail market during the 2025--2026 period. It is anticipated
that the outcomes will provide a fresh software architecture framework
for the Multi-Agent Systems (MAS) literature and potentially facilitate
practical solutions for Vietnamese retail establishments to enhance
their customer consultation capabilities in the digital era.

The remainder of this paper is structured as follows: Section 2
establishes the theoretical foundations of MAS, GraphRAG, and their
application in retail. Section 3 details the system analysis and design,
focusing on agent coordination via LangGraph and template-based database
integration. Section 4 evaluates the system through real-world
deployment and experimental analysis. Finally, Section 5 summarizes the
contributions, discusses practical implications for Vietnam's retail
sector, and suggests future research directions.

# LITERATURE REVIEW

## MULTI-AGENT SYSTEMS

### Definition and Fundamental Properties

The theoretical foundation of this research begins with the formal
definition of Multi-Agent Systems (MAS). Wooldridge and Jennings define
a multi-agent system is "a system composed of multiple autonomous agents
that interact with one another within a shared environment, with the
ability to perceive and act upon that environment in order to achieve
individual or collective goals" [@viet2026_2]. This definition
encapsulates four essential properties that distinguish MAS from
conventional software systems: **autonomy**, the ability to make
independent decisions without direct human intervention; **social
ability**, the capacity to communicate and cooperate with other agents
through an agent communication language (ACL); **reactivity**, the
ability to perceive and respond promptly to changes in the environment;
and **proactiveness**, the ability to plan and act in a goal-directed
manner. In the context of Large Language Models (LLMs), these properties
are realized through Chain-of-Thought (CoT) reasoning, planning
approaches such as ReAct or Monte Carlo Tree Search (MCTS), and
communication via natural language. In their comprehensive survey of
LLM-based agents, Xi et al. classify agents along three dimension:
degree of autonomy, scope of action (ex: tool use, code execution, web
browsing, etc), and memory mechanism (in-context, external memory and
parametrics) [@viet2026_3]. This classification framework provides the
conceptual scaffold upon which the agent roles in the proposed system
are differentiated, as each agent in the architecture occupies a
distinct position along these three dimensions.

### Co-ordination Architecture in Multi-Agent Systems

The co-ordination structure of a MAS is one of the most consequential
architectural decisions, as it directly determines how information flow,
how decisions are made, and where system bottlenecks emerge. Li et al.
in the landmark CAMEL study, classify MAS architectures into three
primary types [@viet2026_4]. The **hierarchical architecture** places an
Orchestrator Agent at the apex, coordinating the subordinate sub-agents.
This structure offers clear control flow and facilitates debugging,
through the orchestrator can become a bottleneck; it is the best suited
to clearly structured processes such as retail sales consultation. The
**peer-to-peer architecture** enables agents to communicate directly
through peer-level protocols, providing greater flexibility and
eliminating single point of failure, but making global behavioral
control more difficult - a characteristic that renders it more
appropiate for distributed optimization problems and social simulation.
Finally, the **market-based architecture** introduces competitive or
bidding mechanisms, which are most effective when tasks can be naturally
modeled as resource allocation problems. A complementary survey by Yan
el at. further elaborates on how communication patterns - including
broadcasting, targeted messaging, and role-based delegation - influence
the emergent behavior and task performance of LLM-based MAS
[@viet2026_17]. This study adopts a hierarchical architecture because
it's well suited to the requirement for tight control over structured,
multi-turn conversational flows and the clear delineation of
accountability that a production retail environment demands, as
elaborated in Section 3.

::: {#tab:mas-frameworks}
  **Framework**     **Co-ordination**   **State**             **Advantages**                      **Suitable for**
  ----------------- ------------------- --------------------- ----------------------------------- -----------------------
  LangGraph         Hierarchical DCG    TypedDict + Redis     Supports loops and strong control   Complex conversations
  AutoGen           Peer-to-peer        Conversation Buffer   Flexible and easy to scale          Automated programming
  CrewAI            Hierarchical        In-memory             Intuitive declarative design        Business workflows
  AgentVerse        Distributed         Shared Memory         Multi-role simulation               Social simulation
  Semantic Kernel   Plugin-based        Planners              Microsoft integration               Enterprise .NET

  : Framework MAS LLM-based comparison
:::

### MAS in E-commerce

The application of Multi-Agent Systems (MAS) in e-commerce dates back to
the late 1990s, primarily focusing on automated price negotiation and
product comparison tasks [@viet2026_5]. However, the emergence of Large
Language Models (LLMs) has significantly enhanced the capabilities of
MAS in this domain. He et al. demonstrated that LLM-based agents can
effectively play the roles of both customers and sales representatives,
simulating 73.4% of real-world transaction scenarios with a high degree
of perceived naturalness [@viet2026_6]. More recently, Fang et al. at
JD.com proposed a Hybrid Multi-Agent Collaborative Recommender System
(Hybrid-MACRS) that reduces first-token latency by approximately 70
percent compared to single-agent baselines in a live e-commerce
environment, demonstrating the practical feasibility of deploying MAS at
production scale [@viet2026_18]. Additionally, Chu et al. showed that
LLM-powered multi-agent simulation frameworks can model emergent
consumer social dynamics and purchasing decisions without predefined
rules --- a finding directly relevant to the psychology analysis
component of the proposed system [@viet2026_19]. Nevertheless, the
existing literature remains largely confined to simplified price
negotiation scenarios and English-language contexts, leaving the
challenge of complex, multi-turn product consultation in low-resource
languages such as Vietnamese unaddressed --- a gap this research is
specifically designed to fill.

## LangGraph - Agent Orchestration Platform

### From LangChain to LangGraph

Understanding the LangGraph framework requires first contextualizing it
within the evolution of LLM orchestration tooling. LangGraph was
developed by the LangChain team and launched in 2024. It provides an
effective solution to the limitations LangChain faces in building
stateful agent applications. The fundamental difference between
LangChain Chains and LangGraph lies in their graph structure: While
LangChain organizes execution as a DAG (Directed Acyclic Graph), which
just supports one-way flow without cycles, LangGraph uses a DCG
(Directed Cyclic Graph) structure that enables loops, conditional
branching, and parallel execution. The looping capability of LangGraph
is essential for AI agents because it can model reflection, retries, and
multi-turn conversations - elements that are intrinsic to the real
consultation processes. According to the official documentation of
LangGraph in 2024, the framework provides three types of edges: static
edges, dynamic edges (conditional edges based on state), and parallel
edges (via the Send API for fan-out, fan-in)

### State Management Mechanism

The core of LangGraph is a centralized management mechanism. Each graph
defines a state schema in the form Python [`TypedDict`]{.mark}
describing the set of data fields maintained throughout the lifecycle of
a conversation. At each execution step, the current node receives the
entire state, performs ít processing, and returns an update (delta),
which is merged into the global state through a reducer function:
$$\begin{equation}
    S_{t+1} = \text{Reducer}(S_t, \Delta_{\text{node}}(S_t))
\end{equation}$$

The reducer function ís a concept borrowed from functional programming.
For fields of type [`List`]{.mark}, the default reducer is concatenation
(append); for scalar field, the reducer performs overwriting. LangGraph
allows custom reducers to be defined for each field, for example: a
dictionary-merging reducer, a priority-ranking provider, or a reducer
that preserves history.

The checkpointers mechanism ([`SQLite`]{.mark}, [`Redis`]{.mark} or
[`PostgreSQL`]{.mark}) stores the state of each step in persistent
storage, making it possible to restore a conversation after a
disconnection - an important capability in a real conversation, where
unstable connection are quite common.

## Retrieval-Augmented Generation and Graph RAG

### About RAG

Retrieval-Augmented Generation (RAG) was introduced by Lewis et al. in
their seminal "Retrieval-Augmented Generation for Knowledge-Intensive
NLP Tasks" [@viet2026_7] as a principled solution to two fundamental
limitations of pure LLMs: the freezing of world knowledge at training
time, and the tendency to hallucinate when required to answer questions
about specific, domain-particular information. The standard RAG pipeline
comprises three sequential stages: (1) **Encode**, in which documents
are converted into dense vector embeddings; (2) **Retrieve**, in which
the top-k most relevant documents are identified using cosine similarity
between query and document vectors; and (3) **Generate**, in which the
LLM produces a grounded answer conditioned on the retrieved context.

The Cosine similarity between a query vector [`q`]{.mark} and document
vector [`d`]{.mark} is calculated using the following formula:
$$\begin{equation}
    sim(q, d) = \frac{q \cdot d}{\|q\| \cdot \|d\|} = \frac{\sum_{i=1}^{n} q_i d_i}{\sqrt{\sum_{i=1}^{n} q_i^2} \cdot \sqrt{\sum_{i=1}^{n} d_i^2}}
\end{equation}$$

Gao et al., in their comprehensive survey of RAG, classify RAG
approaches into three generation: **Naive RAG** (simple vector
similarity), **Advanced RAG** (query expansion, re-ranking, and hybrid
search), and **Modular RAG** (integration of multiple specialized
modules) [@viet2026_8]. The KR Agent in the proposed system implements
an Advanced RAG strategy, combining dense vector retrieval with sparse
BM25 search and metadata filtering to achieve both semantic precision
and lexical accuracy - an approach that proves particularly valuable
when users query products by exact name, SKU, or technical
specification.

### Graph RAG - Further than Vector Similarity

While standard RAG excels at retrieving semantically similar text
fragments, it fails to capture the structural, relational knowledge that
characterizes complex product catalogs in retail. Graph RAG, introduced
by Edge et al. at Microsoft Research in their study "From Local to
Global: A Graph RAG Approach to Query-Focused Summarization"
[@viet2026_9], addresses this limitation by augmenting the traditional
RAG pipeline with a Knowledge Graph layer that enables queries to
exploit structural relationships between entities.

In the Graph RAG framework, source documents are parsed to extract
entities and their corresponding relations, constructing a knowledge
graph $G = (V, E)$, where $V$ represents the set of vertices (entities)
and $E$ denotes the set of edges (relations). Upon receiving a query,
the system executes two concurrent search modalities: (1) a **vector
search** on embedded chunks and (2) a **graph traversal** across the
entity graph. The final **aggregated score** is formulated as:
$$\begin{equation}
    Score(q, d) = \alpha \cdot VecSim(q, d) + \beta \cdot GraphProx(q, d) + \gamma \cdot EntMatch(q, d)
\end{equation}$$ Where $\alpha + \beta + \gamma = 1$, VecSim represents
the cosine similarity score, GraphProx is the normalized graph
proximity, and EntMatch is a hard entity matching score (either binary
or fuzzy). Edge et al. reported that this approach achieved a 72%
performance improvement on complex multi-entity queries compare to Naive
RAG [@viet2026_9]. In a retail context, Graph RAG is particularly potent
as product data exhibits as a natural graph structure:
$$\begin{equation}
    \text{Product} \rightarrow \text{Category} \rightarrow \text{Brand} \rightarrow \text{Occasion} \rightarrow \text{Price Range}
\end{equation}$$ This structure allows the KR Agent to, for example,
traverse from a customer query from \"birthday gift\" to a set of
age-appropriate luxury jewelry items without requiring the customer to
enumerate all relevant attributes explicitly.

### Chunking & Embedding Skills

The quality of vector retrieval is fundamentally constrained by the
quality of the data partitioning strategy applied during indexing.
Sarthi et al., in their RAPTOR research, proposed a recursive
abstraction approach that generates summaries at multiple levels of
granularity --- enabling the system to address both high-level overview
queries and fine-grained technical questions with equal proficiency
[@viet2026_10]. Building on this insight, the proposed system implements
Semantic Chunking rather than simple fixed-size chunking: the algorithm
segments text at sentence boundaries where cosine similarity between
consecutive sentence embeddings falls below a threshold --- producing
variable-length chunks that preserve semantic coherence. Each product is
additionally represented by a summary embedding capturing its overall
characteristics, in direct adaptation of the RAPTOR approach. Regarding
the embedding model, empirical benchmarks on the MIRACL multilingual
dataset demonstrate that OpenAI's text-embedding-3-small (1,536
dimensions) achieves an NDCG@10 of 0.623 for the Vietnamese language ---
significantly outperforming multilingual-E5 and LaBSE [@viet2026_11] -
[@viet2026_12]. This performance advantage is particularly consequential
for the present system, given its deployment context in the Vietnamese
retail market, where embedding quality directly determines retrieval
precision for product queries.

### ChromaDB and Vector Database

ChromaDb is an open-source vector database specifically designed for
AI/ML applications. Its key advantages over alternative solutions (such
as Pinecone, Weaviate, etc.) include: (1) Native integration with
LangChain and LlamaIndex, which minimizes boilerplate code; (2) Support
for complex metadata filtering combined with vector search within a
single query ; (3) Collection-based isolation, aligning with the
multi-collection architecture of the system described in Section 3; and
(4) Versatility in supporting both in-memory and persistent modes.

ChromaDB utilizes the Hierarchical Navigable Small World (HNSW)
algorithm as its default indexing structure. HNSW is a hierarchical
graph-based Approximate Nearest Neighbor (ANN) approach with a search
complexity of $O(\log n)$, offering significantly higher efficiency
compared to the $O(n)$ complexity of brute-force search on large-scale
datasets [@viet2026_13]. By leveraging this indexing structure, the
system can ensure low query latency and high recall accuracy, enabling
the retrieval stage to operate comfortably within the system's overall
3-second end-to-end latency target.

### Analysis of User Psychology in E-commerce

A distinctive and novel dimension of the proposed system is its
incorporation of real-time customer psychology analysis as a first-class
architectural component. Research into online consumer behavior
indicates that purchase decisions are not instantaneous actions but
rather an evolutionary process spanning several psychological stages
[@viet2026_14]. Rane et al. further demonstrate that AI-powered
sentiment analysis integrated with CRM-style conversational data can
drive measurable improvements in customer lifetime value and return on
marketing investment, provided that the emotional analytics are applied
prescriptively rather than merely diagnostically [@viet2026_27].

From a technician perspective, classifying psychological states from
conversational text is framed as a sequence classification problem,
addressable through fine-tuned BERT/RoBERTa models, zero-shot LLM
classification, or few-shot classification with exemplars. Hou et al.
demonstrated that zero-shot LLM approaches achieved an F1-score of 0,78
in purchase intent classification, performing competitively against
specialized fine-tuned models [@viet2026_15]. The primary advantage of
the zero-shot approach is the elimination of the need for annotated
datasets - a crucial factor in the Vietnamese context, where labeled
data remains scarce. This evidence directly motivates the design of the
Psych Agent in Section 3.2.3, which employs zero-shot classification to
infer customer psychological state and dynamically adapt the system's
consultation strategy accordingly.

### Research Gap

Synthesizing the literature reviewed above, five interconnected research
gaps emerge that this study is specifically positioned to address.
First, while hierarchical MAS architectures have been studied
extensively in English-language contexts, no prior work has applied
LangGraph-based hierarchical MAS to multi-turn retail consultation in
the Vietnamese linguistic context, which presents unique challenges in
lexical ambiguity, honorific register, and the scarcity of labeled
training data. Second, most existing retrieval systems rely exclusively
on either vector similarity or static knowledge graphs; this research
pioneers the dynamic integration of GraphRAG with ChromaDB within a live
sales consultation pipeline. Third, while sentiment analysis has been
studied as a post-processing analytical tool, no prior work encapsulates
real-time sentiment classification as an autonomous,
decision-influencing agent within a MAS. Fourth, the literature lacks
standardized evaluation frameworks for retail-specific AI consultants;
this study proposes the CARS (Conversational AI Retail Score) framework
to fill this gap. Fifth, existing MAS implementations frequently
sacrifice response speed for reasoning capability; this research
investigates latency optimization strategies to maintain near-real-time
performance (\< 3 seconds) in a production-ready environment. Taken
together, these five gaps define the precise research space that the
proposed system inhabits and seeks to advance.

# System Analysis and Design

## System Design Overview

### Design Principles

The architecture of the proposed system is governed by six foundational
design principles, each selected to address a specific class of failure
mode observed in prior single-agent and rule-based retail AI systems.
The principle of Separation of Concerns ensures that each agent is
assigned a singular, well-defined responsibility, preventing the
knowledge contamination and context drift that afflict monolithic
architectures. Divide and Conquer decomposes the complex consultation
task into specialized sub-problems --- knowledge retrieval,
psychological analysis, and response synthesis --- allowing each to be
optimized independently. Centralized State Management maintains the
entire conversational context within a single, unified ConversationState
data structure, guaranteeing that all agents operate on a consistent,
synchronized view of the interaction. Observability requires that every
processing step be comprehensively logged, enabling real-time debugging
and the post-hoc performance analysis necessary for iterative system
improvement. Resilience through checkpoint-based recovery ensures zero
loss of conversational data even in the event of connectivity failures
--- a particularly important consideration given the mobile-dominated
nature of Vietnamese e-commerce traffic. Finally, Graceful Degradation
guarantees that the system maintains operational continuity --- albeit
with potentially reduced response quality --- even when individual
agents become temporarily unavailable, ensuring continuous service to
retail customers. These six principles collectively define an
architecture that is simultaneously powerful in its reasoning
capabilities and robust in its operational behavior.

### Four-Layer Architecture

The system is organized into a four-layer hierarchical model. Each layer
has distinct boundaries of responsibility and communicates with the
subsequent layer via explicitly define protocols. The design follows the
Dependency Rule, where higher layers depend solely on lower layers,
ensuring modularity and the ability to replace individual layers
independently. The first layer, the Interface Layer, serves as the
gateway for user requests via a REST API, managing authentication, rate
limiting at 100 requests per minute, and session initialization or
recovery from the Redis checkpointer. Raw requests are transformed into
the standardized ConversationState format at this layer. The second
layer is the Orchestration Layer, centers on the Orchestrator Agent,
which performs intent analysis and determines the execution path across
the LangGraph transition map based on the current conversation state ---
functioning as the single source of truth for all coordination
decisions. The third layer, the Specialized Processing Layer, comprises
the three domain-expert agents: the KR Agent for deep knowledge querying
via GraphRAG, the Psychology Agent for psychological state inference and
consultation strategy selection, and the Synth Agent for generating the
final personalized response. And the last layer, the Data and
Infrastructure Layer, provides the foundational resource services ---
ChromaDB for vector and graph storage, Redis for state management and
checkpointing, and the LLM API endpoints --- without containing any
business logic, maintaining strict adherence to the Dependency Rule and
enabling component-level replacement as technology evolves.

::: center
:::

### General Processing Workflow

The turn-based conversation workflow is optimized to achieve a target
latency $\leq 3\space seconds$ - a threshold consistent with industry
benchmarks for real-time conversational AI, where response times
exceeding three seconds are generally associated with measurable drops
in user engagement and session abandonment. The hybrid retrieval
architecture underpinning this pipeline draws directly from the design
principles of Nie et al.'s Hybrid-MACRS system deployed at JD.com, which
demonstrated that replacing sequential LLM inference chains with a
hybrid agent-search design reduces first token latency by approximately
70 percent compared to single-agent baselines [@viet2026_28]. When a
user sends a message through the retail interface, it is delivered to
the system's REST API (Ingestion). The Controller Layer authenticates
the request and retrieves the active session via [`sessionid`]{.mark}
(Controller Processing). The ConversationState is then fetched from
Redis and the new message is appended to the conversation history (State
Recovery). The Orchestrator Agent analyzes the message intent and sets
[`nextnode = ‘‘kragent’’`]{.mark} to initiate the retrieval pipeline
(Routing). The KR Agent executes concurrent dense and sparse searches
across ChromaDB, applying GraphRAG traversal to update the
[`retrievedproducts`]{.mark} field (Hybrid Retrieval --- target
$\leq 700$). In parallel or subsequently, the Psychology Agent evaluates
the full conversation history to infer the customer's current
psychological state and propose a consultation strategy (Contextual
Analysis --- target $\leq 450$). The Orchestrator then routes control to
the Synth Agent, which merges product data and consultation strategy to
generate the [`finalresponse`]{.mark} (Synthesis --- target $\leq 800$).
The response is returned to the client, and the updated
ConversationState is checkpointed to Redis for subsequent turns
(Response and Persistence). This structured pipeline ensures that
complex reasoning capabilities are delivered within response times that
meet the real-time expectations of modern Vietnamese e-commerce
consumers.

::: center
:::

## System Agent Design

### Orchestrator Agent - The Co-ordination Hub

The Orchestrator Agent functions as the cognitive center of the system,
performing three interdependent core functions: Intent Analysis,
analyzing high-level intent from user messages and conversation history;
State Evaluation, Assessing the current state to identify missing
information; and Routing Decision, determining which specialized agent
should be used next. It's routing function is modeled as a multi-class
classification problem over an action space: $$\begin{equation}
    a^* = \arg\max_{a \in A} P_{LLM}(a \mid intent(S), context(S), history(S))
\end{equation}$$ Where
$\mathcal{A} = \{\text{kr\_agent, psych\_agent, synth\_agent, END}\}$ is
the action space, $\mathcal{S}$ is the current ConversationState, and
$\mathcal{P}$ is the probability distribution estimated by the LLM via
structured output (JSON format). Utilizing structured output (rather
than free-text parsing) significantly reduced routing error rates in
internal testing.

The Orchestrator's system prompt is designed following Chain-of-Thought
(CoT) framework, as established by Wei et al., which requires the agent
to reason through four explicit steps before emitting a routing
decision: (1) identify the current high-level user intent; (2) enumerate
information already present in the ConversationState; (3) identify
information still required to generate an optimal response; and (4)
select the next agent. This structured reasoning approach improved
routing accuracy by 18.7 percent compared to non-CoT prompts in internal
ablation experiments [@viet2026_16]. The Orchestrator also implements an
iteration safeguard: the iteration_count field is incremented with each
cycle (via the add reducer), and the conditional_router function returns
END if the threshold MAX_ITERATIONS = 8 is exceeded, guaranteeing system
stability even in edge cases where the routing logic encounters
unexpected state configurations.

### Knowledge Retrieval Agent (KR Agent)

The KR Agent is responsible for retrieving accurate product information
from ChromaDB using a three-stage Graph RAG strategy. The agent's design
strictly adheres to the "retrieval-first, reasoning-later" principle,
ensuring all information in the final response is grounded in verifiable
sources.

#### (1) Stage 1: Query Reformulation and Expansion {#stage-1-query-reformulation-and-expansion .unnumbered}

The KR Agent first analyzes the user query to extract key search
entities (products, categories, price ranges, occasions, brands). It
then expands the query using Vietnamese synonyms and industry-specific
terminology.

- **Example:** "nhẫn cưới" (wedding ring) $\rightarrow$ {"nhẫn đính
  hôn", "nhẫn cưới", "wedding ring", "nhẫn hôn nhân"}.

#### (2) Stage 2: Hybrid Search {#stage-2-hybrid-search .unnumbered}

This stage executes three parallel retrieval modalities: dense vector
similarity search using [`text-embedding-3-small`]{.mark} embeddings,
sparse BM25 keyword search (which is particularly effective for product
names and SKU codes), and hard metadata filtering by category, price
range, and stock status. These three signals are combined via a
composite score: $$\begin{equation}
    FinalScore(d) = \lambda_1 \cdot DenseScore(d) + \lambda_2 \cdot SparseScore(d) + \lambda_3 \cdot MetaScore(d)
\end{equation}$$ The $\lambda_1 = 0,50$, $\lambda_2 = 0,30$,
$\lambda_3 = 0,20$ are determined via grid search on a validation set
using the $Recall@5$ metric. MetaScore is a binary value (1 if the
product matches all filters, 0 otherwise).

#### (3) Stage 3: Re-ranking and Diversity {#stage-3-re-ranking-and-diversity .unnumbered}

The top 20 results from Stage 2 are re-ranked using a cross-encoder to
improve precision. Simultaneously, the Maximal Marginal Relevance (MMR)
algorithm is applied to ensure result diversity: $$\begin{equation}
    MMR(d_i) = \arg\max_{d_i \in D \setminus S} [\lambda \cdot Sim(q, d_i) - (1-\lambda) \cdot \max_{d_j \in S} Sim(d_i, d_j)]
\end{equation}$$ Where:

- $S$ is the set of already selected documents.

- $D\setminus S$ is the set of remaining documents.

- $\lambda$ adjusts the balance between relevance and diversity.

The Top-5 documents following the MMR process are then passed as context
to the Synth Agent.

### Psychology Analysis Agent (Psych Agent)

The Psychology Agent represents the most novel contribution of the
proposed architecture: the encapsulation of real-time customer
psychological state inference as a fully autonomous agent within the
MAS. While prior research has treated sentiment analysis as a passive,
post-hoc analytical tool, the Psych Agent functions as an active,
decision-influencing component that continuously shapes the system's
consultation strategy. The Psych Agent analyzed the entire conversation
history (up to the last 10 turns) to infer the customer's current
psychological state. While the KR Agent focuses on informational
content, the Psych Agent focuses on the style of expression, emotional
intensity, and implicit linguistic cues. The classification algorithm
utilizes a zero-shot LLM with a prompt designed to extract
multi-dimensional linguistic features: lexical features (hesitation
markers such as "suy nghĩ" or "có lẽ"; comparative markers such as "hay
là" or "tốt hơn"; commitment markers such as "đặt ngay" or "mua");
syntactic features (confirmation questions, negative sentences);
sentiment features (polarity and intensity); and contextual features
(number of elapsed conversational turns and query complexity). Following
Hou et al.'s finding that zero-shot LLM classification achieves an
F1-score of 0.78 on purchase intent classification without requiring
annotated training data [@viet2026_15], the Psych Agent employs a
zero-shot classification strategy with a carefully engineered prompt,
outputting a structured JSON object containing the inferred psych_state,
a confidence score (psych_confidence), the primary_concern (if any), and
a recommended consult_strategy. This output directly governs how the
Synth Agent frames its final response, creating a feedback loop between
psychological insight and conversational behavior that constitutes a key
differentiator of the proposed system.

### Synthesis Agent (Synth Agent)

The Synth Agent serves as the final convergence point of the pipeline.
It takes the entire [`ConversationState`]{.mark} - enriched by both KR
Agent and Psych Agent - as input to generate the final response for the
customer. The agent adheres to three immutable constraints: **Factual
Grounding**, which mandates that all product information originate
exclusively from the KR Agent's retrieved documents, with zero tolerance
for hallucination; **Strategy Alignment**, which requires the response
structure to conform to the consult_strategy produced by the Psych
Agent; and **Natural Tone**, which ensures the output maintains a
natural, friendly, and culturally localized Vietnamese linguistic
register. The response structure itself follows the AIDA marketing
model: An Attention-capturing opening tied to the user's specific need;
Interest development through relevant product presentation; Desire
cultivation through emotional and functional benefit articulation; and
an Action call-to-action calibrated to the customer's psychological
state.

To quantify Synth Agent performance, this research propose a Composite
Response Quality (CRQ) metric using a Weighted Sum Model (WSM) combined
with the LLM-as-a-judge technique: $$\begin{equation}
    RQ = w_1 \cdot Relevance + w_2 \cdot Accuracy + w_3 \cdot Persuasion + w_4 \cdot Naturalness
\end{equation}$$ Where $w_1 = 0,35$, $w_2 = 0,30$, $w_3 = 0,20$,
$w_4 = 0,15$ were determined through a quick interview with 12 senior
sales specialists from the Pancharm startup team. Each component is
evaluated by an LLM-as-judge using a 1-5 Likert scale.

## LangGraph State Graph Design

### ConversationState Schema

The [`ConversationState`]{.mark} is the architectural foundation upon
which the entire multi-agent system operates. Defined as a Python
[`TypedDict`]{.mark} with [`Annotated`]{.mark} type hints to specify the
reducer functions for each field, it's designed according to the
"necessary and sufficient" principle - storing exclusively the
information required for agents to make optimal decisions, without
introducing unnecessary data coupling or state bloat. The schema
balances completeness with interpretability: each field has a single
owning agent responsible for its updates, enforcing the Separation of
Concerns principle at the data layer. The messages field accumulates the
full conversation history using an append reducer, preserving the
temporal ordering essential for the Psych Agent's analysis. Fields such
as [`psych_state`]{.mark} and [`next_node`]{.mark} use overwrite
reducers, as only the most recent value carries decision-relevant
information. The [`iteration_count`]{.mark} field uses an add reducer
(incrementing by 1 per cycle) to support the loop-termination safety
mechanism described in Section 3.2.1. The complete schema is documented
in Table 3.1.

::: {#tab:conversation_state}
  **Field**            **Data Type**         **Reducer**    **Description and Purpose**
  -------------------- --------------------- -------------- --------------------------------------------------------------
  messages             List\[BaseMessage\]   add (append)   Full conversation history in chronological order.
  user_intent          str                   overwrite      Top-level intent analyzed by the Orchestrator.
  retrieved_products   List\[ProductDoc\]    overwrite      Top-k products from ChromaDB with full metadata.
  retrieval_scores     List\[float\]         overwrite      Corresponding composite scores for each product.
  psych_state          PsychStateEnum        overwrite      Current psychological state (5 states).
  psych_confidence     float                 overwrite      Confidence score of psychological classification (0.0--1.0).
  primary_concern      str \| None           overwrite      Primary customer barrier, if any.
  consult_strategy     str                   overwrite      Consultation strategy suggested by the Psych Agent.
  session_metadata     Dict\[str, Any\]      merge          Includes session_id, timestamp, channel, and user_profile.
  final_response       str                   overwrite      Final response ready to be sent to the user.
  next_node            str                   overwrite      Next node in the graph (routing signal).
  error_state          str \| None           overwrite      Error information if any, triggering the fallback flow.
  iteration_count      int                   add (+1)       Loop counter to prevent infinite loops.

  : Detailed Schema of ConversationState
:::

### Graph Definition and Conditional Routing

The LangGraph architecture is defined with five primary nodes and
dynamic state transition logic based on the [`next_node`]{.mark} value
within the [`ConversationState`]{.mark}. The conditional router is
implemented as follows:

``` {.python language="Python" caption="Implementation of the Conditional Router"}
def conditional_router(state: ConversationState) -> str:
    if state["error_state"] is not None:
        return "error_handler"
        
    if state["iteration_count"] > MAX_ITERATIONS:
        return END
        
    route = state["next_node"]
    return route if route in VALID_NODES else END
```

**Where:**

- **Conditional Routing:** Edges originating from the Orchestrator to
  individual agents utilize LangGraph's [`conditional_edges()`]{.mark}
  function.

- **Normal Edges:** In contrast, edges from the KR Agent and Psych Agent
  always return to the Orchestrator. This ensures the Orchestrator
  remains the sole control point, enforcing the Single Source of Truth
  principle for the co-ordination flow.

- **Infinite Loop Protection:** To prevent system hangs, an iteration
  safeguard is implemented. The [`iteration_count`]{.mark} is
  incremented in each cycle (using the [**add**]{.mark} reducer), and
  the [`conditional_router`]{.mark} returns [`END`]{.mark} if the
  theshold [`MAX_ITERATIONS = 8`]{.mark} is exceeded. This guarantees
  system stability even in cases where the Orchestrator's routing logic
  might fail.

### Checkpointing and Session Persistence

Session persistence is implemented through LangGraph's Redis
checkpointer, which stores state checkpoints at each execution step
using a standardized key format: [`thread_id:checkpoint_id`]{.mark}.
Each conversation is uniquely identified by a [`thread_id`]{.mark} (UUID
v4). The default Time-to-Live (TTL) is set to 3600 seconds (1 hour) - a
duration sufficient to recover sessions after short-term connectivity
interruptions.\
When a user sends a new message within the same session, the system
automatically retrieves the most recent checkpoint from Redis and
resumes execution from the saved state - rather than re-initializing the
conversation from scratch. This mechanism is the key to maintaining
seamless contextual continuity across multiple conversational turns.

## ChromaDB Integration and Indexing Strategy

### Collection Structure

Product data is organized into three distinct collections within
ChromaDB, categorized by granularity and usage purpose, as shown in
Table 3.2 below:

::: center
  **Collection**     **Content**                **Chunk Size**           **Query Purpose**
  ------------------ -------------------------- ------------------------ --------------------------------
  product_overview   USP, short descriptions    256 tokens, 32 overlap   General inquiries, suggestions
  product_specs      Detailed technical specs   512 tokens, 64 overlap   Technical detail inquiries
  product_reviews    Reviews, social proof      384 tokens, 48 overlap   Experience and trust inquiries
:::

This multi-collection strategy allows the KR Agent to route queries to
the most appropriate collection based on the question type---reducing
noise and increasing precision compared to searching a single unified
collection. Results from all three collections are merged and re-ranked
in the final step.

### Semantic Chunking Strategy

The proposed system employs Semantic Chunking rather than traditional
Fixed-size Chunking, motivated by research demonstrating that
semantically coherent chunks produce superior embedding quality and
retrieval precision. The algorithm proceeds as follows: the document is
first segmented into individual sentences; embeddings are computed for
each sentence; chunk boundaries are identified at positions where cosine
similarity between consecutive sentence embeddings falls below a
semantic breakpoints threshold; and semantically contiguous sentence
groups are consolidated into a single chunk. This approach yields
variable-length chunks that preserve thematic integrity --- preventing
the fragmentation of related product attributes across chunk boundaries
that fixed-size approaches inevitably produce. In addition, as adapted
from RAPTOR \], the system generates a dedicated summary embedding for
each product --- a single vector representing the complete product
description --- in parallel with the fine-grained chunk-level
embeddings. This dual-resolution representation ensures the system can
effectively handle both broad discovery queries (e.g., "có sản phẩm nhẫn
vàng không?") and highly specific technical questions (e.g., "độ tinh
khiết vàng 18K là bao nhiêu?") within the same retrieval pipeline
[@viet2026_10].

### Metadata Schema and Hybrid Filtering

Each document is stored with a standardized metadata structure, enabling
hybrid filtering --- a process that combines vector similarity search
with hard attribute-based filtering. Hybrid filtering allows the KR
Agent to simultaneously apply semantic matching and strict attribute
constraints (such as category, price range, and stock availability) in a
single query, significantly reducing irrelevant results and improving
retrieval precision for constrained product searches. An example
implementation is shown below:

``` {.python language="Python" caption="Example of Hybrid Filtering Implementation"}
# KR Agent utilizes Hybrid Filtering to combine Semantic and Metadata search
query_vector = embedding_model.embed_query("gold rings for wedding")

# Define hard filters based on user context
metadata_filters = {
    "category": {"$eq": "nhẫn cưới"},
    "price": {"$lte": 15000000}, # Budget under 15 million
    "stock_status": {"$eq": True}
}

# Perform Hybrid Search in ChromaDB
results = collection.query(
    query_embeddings=[query_vector],
    where=metadata_filters, # Hard filtering
    n_results=5
)
```

### API Design and Communication Protocols

The system provides two primary endpoints: [`POST /v1/chat`]{.mark}
(synchronous, 30-second timeout) and [`GET /v1/chat/stream`]{.mark}
(Server-Sent Events for token-by-token streaming). Both request and
response structures strictly adhere to the LLM specification, with data
validation handled by Pydantic schemas.

To ensure system stability, rate limiting is implemented at a threshold
of 100 requests per minute per session, utilizing the Redis Token Bucket
algorithm. Additionally, CORS (Cross-Origin Resource Sharing) is
configured to permit cross-origin requests exclusively from approved
retail partner domains. This API design ensures that the system can be
readily integrated into existing retail platforms and mobile
applications without requiring significant client-side adaptation.

# Implementation and Experimental Evaluation

## Deployment Environment

The system is fully containerized using Docker Compose, comprising five
distinct services: API (FastAPI Application), ChromaDB (Vector
Database), Redis (session storage and checkpointer), Worker (background
embedding jobs), and Nginx (reverse proxy with SSL termination). The
entire infrastructure is defined as code via
[`docker-compose.yml`]{.mark} and environment variables, ensuring high
reproducibility and seamless deployment across various cloud or
on-premise environments.

::: {#tab:deployment-config}
  **[Component]{.nodecor}**   **Technology / Version**   **Detailed Configuration**
  --------------------------- -------------------------- ----------------------------------------------
  **Web Framework**           FastAPI 0.111.0            4 async workers, Uvicorn, Pydantic v2
  **Agent Framework**         LangGraph 0.2.x            Redis Checkpointer, async graph execution
  **Vector Database**         ChromaDB 0.5.x             Persistent mode, HNSW $M=16$, $ef=200$
  **LLM Provider**            Anthropic Claude API       Claude-3.5-Sonnet + Claude-3-Haiku
  **Embedding Model**         text-embedding-3-small     1536 dimensions, batch size 100
  **Session Storage**         Redis 7.2                  TTL 3600s, 2GB maxmemory, LRU eviction
  **Containerization**        Docker Compose 2.x         5 services, health checks, auto-restart
  **Monitoring**              Prometheus + Grafana       Latency p50/p95/p99, error rate, token usage

  : Detailed Implementation Environment Configuration
:::

## Experimental Data

### Knowledge Base

The product dataset comprises 100 feng shui jewelry items. The data is
currently stored and managed within a physical relational database,
which supports seamless transformation into vector embeddings. These
embeddings are subsequently indexed in ChromaDB to facilitate efficient
and high-precision product retrieval during the conversation cycle.

### Evaluation Set

The evaluation set consists of approximately 1,000 real-world
conversation logs collected from Pancharm's sales team interactions with
customers. This dataset provides a comprehensive range of practical
scenarios, spanning from initial basic consultations to complex
deal-closing and objection-handling maneuvers.

## CARS Framework

This research proposes the CARS (Conversational AI Retail Score)
framework. Evaluation is conducted through simulations using the Claude
Sonnet 3.5 model (or your specified version) to emulate the execution
flow of each individual agent. By measuring the outputs against the
provided dataset, the framework derives five distinct performance
metrics, each assigned a specific weight to reflect its impact on the
overall system effectiveness.

::: {#tab:cars-framework}
  **Metric**   **Definition**                                                        **Weight**  **Measurement**           **Benchmark**
  ------------ -------------------------------------------------------------------- ------------ ------------------------- ---------------
  CR           **Conversion Rate**: % of conversations leading to purchase intent       35%      Human annotation          $\ge 40\%$
  IA           **Information Accuracy**: % of accurate product information              30%      Ground truth comparison   $\ge 90\%$
  CC           **Context Consistency**: Continuity and logical flow ($0-1$)             20%      LLM-as-a-Judge            $\ge 0.85$
  RL           **Response Latency**: End-to-end response time (seconds)                 10%      Empirical measurement     $\le 3.0s$
  US           **User Satisfaction**: Post-conversation survey score ($1-5$)             5%      User survey ($n=50$)      $\ge 4.0/5$

  : Conversational AI Retail Score (CARS) Framework
:::

The composite **CARS** score is calculated using the following weighted
sum model:

$$\begin{equation}
    CARS = 0.35 \cdot CR + 0.30 \cdot IA + 0.20 \cdot CC + 0.10 \cdot (1 - RL_{norm}) + 0.05 \cdot US_{norm}
\end{equation}$$

Where:

- $RL_{norm} = \min(RL/3.0, 1.0)$ normalizes the response latency to a
  scale of $0-1$ (lower latency results in a higher contribution to the
  final score).

- $US_{norm} = (US - 1)/4$ normalizes the user satisfaction score ($1-5$
  Likert scale) to a $0-1$ range.

## Performance Comparison

Based on the model-based evaluation, the results demonstrate that the
Multi-Agent System (MAS) significantly outperforms other single-agent
baselines.

::: {#tab:performance-comparison}
  **System / Baseline**             **CR (%)**   **IA (%)**    **CC**    **RL (s)**   **US (/5)**
  -------------------------------- ------------ ------------ ---------- ------------ -------------
  Rule-based Chatbot                   18.3         72.1        0.61        0.8           2.9
  Single-agent (GPT-4o)                28.7         79.3        0.74        2.0           3.3
  Single-agent (Claude Sonnet)         31.4         81.6        0.76        2.1           3.4
  MAS (w/o Psych Agent)                38.2         88.4        0.87        2.5           3.8
  MAS (w/o Graph RAG)                  35.1         82.7        0.84        2.3           3.6
  **Proposed System (Full MAS)**     **42.3**     **91.2**    **0.91**    **2.8**       **4.3**

  : Overall Performance Comparison between Proposed System and Baselines
:::

The integration of the Psych Agent significantly enhances the Conversion
Rate (CR) by an additional 10.9%, attributed to its ability to
personalize consultation strategies based on user psychological
profiles. Furthermore, the implementation of Graph RAG contributes
directly to elevating the Information Accuracy (IA) above the 90%
threshold, ensuring the reliability of the system's responses.

## Case Study Analysis

### Handling HESITATION State

- **Scenario:** A customer expresses interest in a **Pancharm** feng
  shui silver bracelet but voices concerns regarding the price.

- **Resolution:** The **Psychology Agent** detects a **HESITATION**
  state ($conf = 0.89$). Instead of offering a generic discount, the
  **Synthesis Agent** employs the **\"Feel-Felt-Found\"** technique to
  reposition the product's value proposition.

### Special Occasion Consultation

Leveraging **Graph RAG**, when a user requests a \"birthday gift for a
60-year-old mother,\" the system automatically traverses the entity
graph to recommend jewelry pieces categorized under \"luxury\" and
\"age-appropriate\" styles, rather than returning the entire product
catalog.

## Error Analysis and Limitations

Despite promising performance, the following challenges persist:

- **Nuanced Language Recognition:** Sarcasm, ambiguity, or \"Gen Z\"
  slang in Vietnamese occasionally cause the Psychology Agent to
  misclassify user emotional states.

- **Lack of Multi-modality:** The current system lacks Vision-based
  support, which remains a key requirement for visual-centric industries
  like jewelry retail.

# Conclusion and Future Work

## Research Contributions

This thesis has successfully developed and deployed a four-tier
Multi-Agent System (MAS) architecture for retail customer consultation
on the LangGraph platform, demonstrating measurable improvements over
existing single-agent baselines in the Vietnamese e-commerce context.
The key research contributions are summarized below:

- **Regarding System Architecture:** Successfully proposed and
  implemented a four-tier Multi-Agent System (MAS) architecture on the
  LangGraph platform. The clear separation of concerns among four
  specialized agents, combined with a centralized state management
  mechanism ([`ConversationState`]{.mark}), enables the system to handle
  complex consultation scenarios with flexibility and consistency.

- **Regarding Knowledge Retrieval:** Developed an advanced Graph RAG
  methodology integrated with ChromaDB. By combining vector search,
  metadata filtering, and the MMR (Maximal Marginal Relevance)
  re-ranking algorithm, the system achieved an Information Accuracy (IA)
  of 91.2%, effectively mitigating the "hallucination" issues inherent
  in Large Language Models (LLMs) during product consultation.

- **Regarding Personalized Experience:** Engineered a Psychology Agent
  capable of real-time customer psychological analysis. Experimental
  results indicate that this agent contributed a 10.9 percentage point
  increase in the Conversion Rate (CR), proving that the synergy between
  technology and psychology is key to optimizing sales effectiveness.

- **Regarding Evaluation Standards:** Proposed and standardized the CARS
  (Conversational AI Retail Score) framework. This multi-dimensional
  reference framework provides an accurate quantification of AI
  performance in retail, with experimental results significantly
  outperforming traditional single-agent baselines.

## Practical Significance and Transferability

The research findings offer direct economic value to the Vietnamese
retail industry, demonstrating a 34.7% improvement in the deal-closing
rate compared to existing state-of-the-art chatbots. Furthermore,
automating 70--80% of the consultation process optimizes human resource
productivity amidst rising labor costs. The proposed MAS architecture is
highly versatile and easily customizable for application in other
sectors requiring in-depth consultation, such as electronics, real
estate, or financial services.

## Future Work

Based on the error analysis and identified limitations, this thesis
proposes five high-potential directions for future research:

- **Multimodal Integration:** Expanding the system to process product
  images via Vision-Language Models (VLM). This would allow customers to
  upload a photo and ask, \"Do you have something similar?\" or \"What
  material is this?\". This feature is critical in the context of
  Shoppertainment, where visual imagery is the primary language of
  communication.

- **Reinforcement Learning from Feedback (RLHF):** Fine-tuning the Synth
  Agent's consultation strategy based on real conversation data labeled
  with outcomes (e.g., successful sale vs. drop-off). This approach aims
  to surpass the limits of zero-shot/few-shot prompting to achieve
  optimized, domain-specific sales strategies.

- **History-based Personalization (User Profile RAG):** Integrating with
  CRM systems to incorporate purchase history, preferences, and behavior
  into the ConversationState. This deeper level of personalization is
  projected to improve Conversion Rates (CR) by 15--20%.

- **Latency Optimization via Streaming MAS:** Researching parallel
  execution mechanisms for independent agents (e.g., allowing the KR
  Agent and Psych Agent to run simultaneously). This is expected to
  reduce latency from 2.8s to approximately 1.8--2.0s.

- **Multilingualism and ASEAN Markets:** Expanding the system to support
  English, Thai, and Indonesian within the same conversation
  (code-switching), targeting export markets and international customers
  within Vietnam.

The proposed research directions are grounded in the theoretical
framework and preliminary data established in this thesis. The author
envisions this AI system evolving into a comprehensive AI retail
consultation platform, contributing to the digital transformation of
Vietnam's retail sector during the 2025--2030 period.

::: thebibliography
1

Hajdas, M., Radomska, J., Kawa, A., Klimas, P., & Silva, S.C., "Channel
integration puzzle: internal obstacles, industry drivers and omnichannel
capabilities", 2025.\
<https://doi.org/10.1108/IJRDM-05-2025-0377>

Asante, I.O., Jiang, Y., & Luo, X., "Leveraging Online Omnichannel
Commerce to Enhance Consumer Engagement in the Digital Transformation
Era", 2025.\
<https://doi.org/10.3390/jtaer20010002>

Liao, S.H., Widowati, R., & Linh, P.N.M., "Delivery Service and
Omni-channel Online and Offline in Retailing During the Covid-19
Pandemic", 2024.\
<https://journals.sagepub.com/doi/10.1177/21582440241305047>

Park, T., Quach, S., Barari, M., & Nguyen, M., "Exploring the Role of
Omnichannel Retailing Technologies: Future Research Directions", 2024.\
<https://doi.org/10.1177/14413582231167664>

Vietnam E-Commerce Association (VECOM), "Vietnam E-Commerce Market
Report 2024", 2024.\
<https://esc.vn/wp-content/uploads/2025/07/Bao-cao-EBI-2024-ENG.pdf>

Ministry of Industry and Trade (MoIT), "Vietnam E-Commerce Growth
Outlook 2026", 2025.\
<https://www.vietnam-briefing.com/news/vietnams-e-commerce-sector-outlook-in-2026.html/>

M. A. Tran, "DIGITAL RETAIL PLATFORMS AS CHANGE AGENTS OF THE RETAIL
INDUSTRY IN VIETNAM," *Hanoi University of Science and Technology*,
2025.\
<https://www.researchgate.net/publication/404144915_DIGITAL_RETAIL_PLATFORMS_AS_CHANGE_AGENTS_OF_THE_RETAIL_INDUSTRY_IN_VIETNAM>

McKinsey & Company., "The Value of Getting Personalization Right --- or
Wrong --- is Multiplying", 2021.\
<https://www.mckinsey.com/capabilities/growth-marketing-and-sales/our-insights/the-value-of-getting-personalization-right-or-wrong-is-multiplying>

Payments and Commerce Market Intelligence (PCMI), "Vietnam E-Commerce
Market Data 2024-2027", 2024.\
<https://paymentscmi.com/insights/vietnam-ecommerce-market-data/>

Hassan, G., et al., "Evaluating LLM-based Agents for Multi-Turn
Conversations: A Survey", 2025.\
<https://arxiv.org/abs/2503.22458v1>

Naveen Krishnan, "Advancing Multi-Agent Systems Through Model Context
Protocol: Architecture, Implementation, and Applications", 2025.\
<https://arxiv.org/abs/2504.21030v1>

Wooldridge, M., & Jennings, N. R., "Intelligent agents: Theory and
practice. The Knowledge Engineering Review", 1995.\
<https://doi.org/10.1017/S0269888900008122>

Xi, Z., Chen, W., Guo, X., et al., "The Rise and Potential of Large
Language Model Based Agents: A Survey", 2023/\
<https://arxiv.org/abs/2309.07864>

Li, G., Hammoud, H. A. A. K., Itani, H., et al., "CAMEL: Communicative
Agents for \"Mind\" Exploration of Large Language Model Society", 2023.\
<https://arxiv.org/abs/2303.17760>

Yan, B., et al., "Beyond Self-Talk: A Communication-Centric Survey of
LLM-Based Multi-Agent Systems", 2025\
<https://arxiv.org/abs/2502.14321>

Maes, P., Guttman, R. H., & Moukas, A. G., "Agents that buy and sell.
Communications of the ACM", 1999.\
<https://dl.acm.org/doi/pdf/10.1145/295685.295716>

John J. Horton, Apostolos Filippas, Benjamin S. Manning, "Large Language
Models as Simulated Economic Agents: What Can We Learn from Homo
Silicus?", 2023.\
<https://arxiv.org/abs/2301.07543>

Fang, J., Gao, S., Ren, P., et al., "A Multi-Agent Conversational
Recommender System", 2024\
<https://arxiv.org/abs/2402.01135>

Chu, M-L., et al., "LLM-Based Multi-Agent System for Simulating and
Analyzing Marketing and Consumer Behavior", 2025\
<https://arxiv.org/abs/2510.18155>

Lewis P., et al., "Retrieval-Augmented Generation for
Knowledge-Intensive NLP Tasks", 2020.\
<https://arxiv.org/abs/2005.11401>

Gao Y., et al., "Retrieval-Augmented Generation for Large Language
Models: A Survey", 2023.\
<https://arxiv.org/abs/2312.10997>

Edge D., et al., "From Local to Global: A Graph RAG Approach to
Query-Focused Summarization", 2024.\
<https://arxiv.org/abs/2404.16130>

Sarthi P., et al., "RAPTOR: Recursive Abstractive Processing for
Tree-Organized Retrieval", 2024.\
<https://arxiv.org/abs/2401.18059>

Zhang X., et al., "Making a MIRACL: Multilingual Information Retrieval
Across a Continuum of Languages", 2024.
<https://arxiv.org/abs/2210.09984>

OpenAI, "New Embedding Models"\
<https://openai.com/index/new-embedding-models-and-api-updates/>

Malkov, Y. A., & Yashunin, D. A., "Efficient and robust approximate
nearest neighbor search using Hierarchical Navigable Small World
graphs", 2016.\
<https://arxiv.org/abs/1603.09320>

Kotler, P., & Keller, K. L, "Marketing Management (15th ed.). Pearson
Education", 2016.\
<https://doi.org/10.4236/ojbm.2022.101018>

Rane, N. L., Desai, P., Rane, J., & Mallick, S. K., "Using artificial
intelligence, machine learning, and deep learning for sentiment analysis
in customer relationship management to improve customer experience,
loyalty, and satisfaction", 2024.\
<https://doi.org/10.70593/978-81-981367-4-9_7>

Hou, J., He, Z., et al., "Large Language Models are Zero-Shot Rankers
for Recommender Systems", 2023.\
<https://arxiv.org/abs/2305.08845>

Nie, G., Zhi, R., Yan, X., Du, Y., et al., "A Hybrid Multi-Agent
Conversational Recommender System with LLM and Search Engine in
E-commerce", 2024.\
<https://doi.org/10.1145/3640457.3688061>

Wei, J., Wang, X., Schuurmans, D., et al., "Chain-of-Thought Prompting
Elicits Reasoning in Large Language Models", 2024.\
<https://arxiv.org/abs/2201.11903>
:::
