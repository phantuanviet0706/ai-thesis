-- ============================================================
-- DATABASE SCHEMA — RETAIL AI CONSULTATION PLATFORM
-- Engine  : MySQL 8.0+ (InnoDB)
-- Charset : utf8mb4
-- ============================================================
-- Domain overview:
--   [1] Core Product   — Brands, Categories, Products, Images, Tags
--   [2] User           — Users, UserProfiles, UserAddresses
--   [3] Commerce       — Carts, Orders, OrderItems, Payments
--   [4] Content        — ProductReviews
--   [5] AI/Consult     — ConversationSessions, Messages, PsychStateLogs, AgentPerfLogs
--   [6] Platform       — APIKeys, SystemConfigs, AuditLogs
--   [7] Deferred FKs   — cross-domain circular references resolved via ALTER TABLE
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- [1] CORE PRODUCT DOMAIN
-- ============================================================

CREATE TABLE IF NOT EXISTS Brands (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,

    name        VARCHAR(255) NOT NULL,
    slug        VARCHAR(100) NOT NULL UNIQUE,
    logo_url    VARCHAR(500),
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,

    created_at  DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at  DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    INDEX idx_brand_slug   (slug),
    INDEX idx_brand_active (is_active)
) ENGINE=InnoDB;

-- Tags — faceted labels (occasion, feng_shui element, style, etc.)
CREATE TABLE IF NOT EXISTS Tags (
    id       BIGINT PRIMARY KEY AUTO_INCREMENT,
    name     VARCHAR(100) NOT NULL UNIQUE,
    slug     VARCHAR(100) NOT NULL UNIQUE,
    tag_type VARCHAR(50) NOT NULL, -- ENUM('product','occasion','feng_shui','style','promo') NOT NULL DEFAULT 'product',

    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),

    INDEX idx_tag_type (tag_type)
) ENGINE=InnoDB;

-- Categories — self-referential hierarchy (kept from original, fixes applied)
CREATE TABLE IF NOT EXISTS Categories (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,

    name        VARCHAR(255) NOT NULL,
    slug        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parent_id   BIGINT,

    depth_level INT     NOT NULL DEFAULT 0 CHECK (depth_level >= 0),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,

    created_at  DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at  DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    CONSTRAINT fk_category_parent FOREIGN KEY (parent_id)
        REFERENCES Categories(id) ON DELETE RESTRICT,

    INDEX idx_category_slug   (slug),
    INDEX idx_category_parent (parent_id),
    INDEX idx_category_active (is_active)
) ENGINE=InnoDB;

-- Products — core catalog (kept from original, extended)
-- embedding_status tracks ChromaDB sync state for the KR Agent pipeline
CREATE TABLE IF NOT EXISTS Products (
    id                BIGINT PRIMARY KEY AUTO_INCREMENT,

    name              VARCHAR(255) NOT NULL,
    slug              VARCHAR(100) NOT NULL UNIQUE,
    sku               VARCHAR(100) UNIQUE,            -- exact-match target for BM25 in KR Agent
    description       TEXT,
    short_description VARCHAR(500),
    category_id       BIGINT,
    brand_id          BIGINT,

    unit_price        DECIMAL(10,2) NOT NULL,
    sale_price        DECIMAL(10,2),
    in_stock          BOOLEAN NOT NULL DEFAULT TRUE,
    stock_qty         INT     NOT NULL DEFAULT 0 CHECK (stock_qty >= 0),

    attributes        JSON,                           -- flexible: material, size, feng-shui props…
    status            VARCHAR(50) NOT NULL, -- ENUM('draft','active','inactive','archived') NOT NULL DEFAULT 'draft',
    embedding_status  VARCHAR(50) NOT NULL, -- ENUM('pending','indexed','failed')           NOT NULL DEFAULT 'pending',

    created_at        DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at        DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    CONSTRAINT fk_product_category FOREIGN KEY (category_id) REFERENCES Categories(id) ON DELETE SET NULL,
    CONSTRAINT fk_product_brand    FOREIGN KEY (brand_id)    REFERENCES Brands(id)     ON DELETE SET NULL,

    INDEX idx_product_id        (id),
    INDEX idx_product_category  (category_id),
    INDEX idx_product_brand     (brand_id),
    INDEX idx_product_status    (status),
    INDEX idx_product_price     (unit_price),
    INDEX idx_product_stock     (in_stock, stock_qty),
    INDEX idx_product_embedding (embedding_status),
    FULLTEXT INDEX idx_product_search (name, description)   -- supports BM25-style sparse search
) ENGINE=InnoDB;

-- Product Images
CREATE TABLE IF NOT EXISTS ProductImages (
    id         BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_id BIGINT NOT NULL,

    url        VARCHAR(500) NOT NULL,
    alt_text   VARCHAR(255),
    sort_order INT     NOT NULL DEFAULT 0,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,

    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT fk_image_product FOREIGN KEY (product_id) REFERENCES Products(id) ON DELETE CASCADE,

    INDEX idx_image_product  (product_id),
    INDEX idx_image_primary  (product_id, is_primary)
) ENGINE=InnoDB;

-- ProductTags — M:N junction
CREATE TABLE IF NOT EXISTS ProductTags (
    product_id BIGINT NOT NULL,
    tag_id     BIGINT NOT NULL,

    PRIMARY KEY (product_id, tag_id),

    CONSTRAINT fk_pt_product FOREIGN KEY (product_id) REFERENCES Products(id) ON DELETE CASCADE,
    CONSTRAINT fk_pt_tag     FOREIGN KEY (tag_id)     REFERENCES Tags(id)     ON DELETE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- [2] USER DOMAIN
-- ============================================================

-- Users — authentication record only, no profile bloat
CREATE TABLE IF NOT EXISTS Users (
    id               BIGINT PRIMARY KEY AUTO_INCREMENT,

    email            VARCHAR(255) UNIQUE,
    phone            VARCHAR(20)  UNIQUE,
    password_hash    VARCHAR(255),                    -- NULL for OAuth-only accounts
    auth_provider    VARCHAR(50), -- ENUM('local','google','facebook','zalo') NOT NULL DEFAULT 'local',
    auth_provider_id VARCHAR(255),

    role             VARCHAR(50), -- ENUM('customer','staff','admin') NOT NULL DEFAULT 'customer',
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified      BOOLEAN NOT NULL DEFAULT FALSE,

    last_login_at    DATETIME(6),
    created_at       DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at       DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    INDEX idx_user_email    (email),
    INDEX idx_user_phone    (phone),
    INDEX idx_user_role     (role),
    INDEX idx_user_active   (is_active)
) ENGINE=InnoDB;

-- UserProfiles — CRM / personalization data fed into ConversationState.session_metadata
CREATE TABLE IF NOT EXISTS UserProfiles (
    id               BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id          BIGINT NOT NULL UNIQUE,

    display_name     VARCHAR(255),
    avatar_url       VARCHAR(500),
    date_of_birth    DATE,
    gender           VARCHAR(50), -- ENUM('male','female','other'),
    zodiac_sign      VARCHAR(50),                     -- relevant for feng-shui product filtering

    preferences      JSON,                            -- style, price_range, favourite_categories
    total_orders     INT          NOT NULL DEFAULT 0,
    total_spent      DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    loyalty_points   INT          NOT NULL DEFAULT 0,
    customer_segment VARCHAR(50), -- ENUM('new','regular','vip','churned') NOT NULL DEFAULT 'new',
    staff_notes      TEXT,

    created_at       DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at       DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    CONSTRAINT fk_profile_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,

    INDEX idx_profile_segment (customer_segment),
    INDEX idx_profile_zodiac  (zodiac_sign)
) ENGINE=InnoDB;

-- UserAddresses — supports multi-address checkout
CREATE TABLE IF NOT EXISTS UserAddresses (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id         BIGINT NOT NULL,

    label           VARCHAR(100),                     -- "Nhà", "Văn phòng"
    recipient_name  VARCHAR(255) NOT NULL,
    phone           VARCHAR(20)  NOT NULL,
    address_line1   VARCHAR(255) NOT NULL,
    address_line2   VARCHAR(255),
    ward            VARCHAR(100),
    district        VARCHAR(100),
    province        VARCHAR(100) NOT NULL,
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,

    created_at      DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT fk_address_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,

    INDEX idx_address_user    (user_id),
    INDEX idx_address_default (user_id, is_default)
) ENGINE=InnoDB;


-- ============================================================
-- [3] COMMERCE DOMAIN
-- ============================================================

-- Carts — persistent, supports both logged-in and guest users
CREATE TABLE IF NOT EXISTS Carts (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id     BIGINT,                              -- NULL = guest cart
    session_key VARCHAR(255),                        -- browser-side key for guests
    expires_at  DATETIME(6),

    created_at  DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at  DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    CONSTRAINT fk_cart_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,

    INDEX idx_cart_user    (user_id),
    INDEX idx_cart_session (session_key),
    INDEX idx_cart_expires (expires_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS CartItems (
    id         BIGINT PRIMARY KEY AUTO_INCREMENT,
    cart_id    BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    quantity   INT    NOT NULL DEFAULT 1 CHECK (quantity > 0),

    added_at   DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT fk_cartitem_cart    FOREIGN KEY (cart_id)    REFERENCES Carts(id)    ON DELETE CASCADE,
    CONSTRAINT fk_cartitem_product FOREIGN KEY (product_id) REFERENCES Products(id) ON DELETE CASCADE,

    UNIQUE INDEX uq_cart_product (cart_id, product_id),
    INDEX idx_cartitem_cart (cart_id)
) ENGINE=InnoDB;

-- Orders — conversation_session_id resolved via deferred FK in [7]
CREATE TABLE IF NOT EXISTS Orders (
    id                      BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_code              VARCHAR(50) NOT NULL UNIQUE,   -- e.g. PC-20260109-0001
    user_id                 BIGINT,
    shipping_address_id     BIGINT,

    subtotal                DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    discount_amount         DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    shipping_fee            DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    total_amount            DECIMAL(15,2) NOT NULL DEFAULT 0.00,

    status                  VARCHAR(50), -- ENUM('pending','confirmed','processing','shipped','delivered','cancelled','refunded') NOT NULL DEFAULT 'pending',
    payment_status          VARCHAR(50), -- ENUM('unpaid','paid','partial','refunded') NOT NULL DEFAULT 'unpaid',

    shipping_method         VARCHAR(100),
    tracking_number         VARCHAR(100),
    notes                   TEXT,
    staff_notes             TEXT,

    conversation_session_id BIGINT,                        -- FK added in [7]

    confirmed_at            DATETIME(6),
    shipped_at              DATETIME(6),
    delivered_at            DATETIME(6),
    cancelled_at            DATETIME(6),
    created_at              DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at              DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    CONSTRAINT fk_order_user    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE SET NULL,

    INDEX idx_order_code     (order_code),
    INDEX idx_order_user     (user_id),
    INDEX idx_order_status   (status),
    INDEX idx_order_payment  (payment_status),
    INDEX idx_order_created  (created_at),
    INDEX idx_order_session  (conversation_session_id)
) ENGINE=InnoDB;

-- OrderItems — price/name snapshotted at purchase time, never joined for display
CREATE TABLE IF NOT EXISTS OrderItems (
    id           BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id     BIGINT NOT NULL,
    product_id   BIGINT NOT NULL,

    product_name VARCHAR(255) NOT NULL,
    product_sku  VARCHAR(100),
    unit_price   DECIMAL(10,2) NOT NULL,
    quantity     INT           NOT NULL DEFAULT 1 CHECK (quantity > 0),
    total_price  DECIMAL(15,2) NOT NULL,

    created_at   DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT fk_item_order   FOREIGN KEY (order_id)   REFERENCES Orders(id)   ON DELETE CASCADE,
    CONSTRAINT fk_item_product FOREIGN KEY (product_id) REFERENCES Products(id) ON DELETE RESTRICT,

    INDEX idx_item_order   (order_id),
    INDEX idx_item_product (product_id)
) ENGINE=InnoDB;

-- Payments — one order can have multiple payment attempts
CREATE TABLE IF NOT EXISTS Payments (
    id               BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id         BIGINT NOT NULL,

    payment_method   VARCHAR(50), -- ENUM('cod','bank_transfer','momo','vnpay','zalopay','credit_card') NOT NULL,
    transaction_id   VARCHAR(255),
    amount           DECIMAL(15,2) NOT NULL,
    status           VARCHAR(50), -- ENUM('pending','success','failed','refunded') NOT NULL DEFAULT 'pending',
    gateway_response JSON,
    paid_at          DATETIME(6),

    created_at       DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT fk_payment_order FOREIGN KEY (order_id) REFERENCES Orders(id) ON DELETE RESTRICT,

    INDEX idx_payment_order       (order_id),
    INDEX idx_payment_status      (status),
    INDEX idx_payment_transaction (transaction_id)
) ENGINE=InnoDB;


-- ============================================================
-- [4] CONTENT DOMAIN
-- ============================================================

-- ProductReviews — embedding_status tracks ChromaDB product_reviews collection sync
CREATE TABLE IF NOT EXISTS ProductReviews (
    id                   BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_id           BIGINT NOT NULL,
    user_id              BIGINT,
    order_item_id        BIGINT,

    rating               TINYINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title                VARCHAR(255),
    body                 TEXT,
    is_verified_purchase BOOLEAN NOT NULL DEFAULT FALSE,
    is_published         BOOLEAN NOT NULL DEFAULT FALSE,
    moderated_at         DATETIME(6),
    embedding_status     VARCHAR(50), -- ENUM('pending','indexed','failed') NOT NULL DEFAULT 'pending',

    created_at           DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at           DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    CONSTRAINT fk_review_product FOREIGN KEY (product_id) REFERENCES Products(id) ON DELETE CASCADE,
    CONSTRAINT fk_review_user    FOREIGN KEY (user_id)    REFERENCES Users(id)    ON DELETE SET NULL,

    INDEX idx_review_product   (product_id),
    INDEX idx_review_user      (user_id),
    INDEX idx_review_published (is_published),
    INDEX idx_review_embedding (embedding_status)
) ENGINE=InnoDB;


-- ============================================================
-- [5] AI / CONSULTATION DOMAIN
-- ============================================================

-- ConversationSessions — 1:1 with LangGraph thread_id / Redis checkpointer key
-- linked_order_id resolved via deferred FK in [7]
CREATE TABLE IF NOT EXISTS ConversationSessions (
    id                    BIGINT PRIMARY KEY AUTO_INCREMENT,
    thread_id             VARCHAR(36) NOT NULL UNIQUE,   -- UUID v4
    user_id               BIGINT,
    channel               VARCHAR(50), -- ENUM('web','mobile','facebook','zalo','tiktok') NOT NULL DEFAULT 'web',
    status                VARCHAR(50), -- ENUM('active','completed','abandoned','error')   NOT NULL DEFAULT 'active',

    -- Snapshot of final ConversationState fields (avoid hitting Redis for analytics)
    final_psych_state     VARCHAR(50),
    final_consult_strategy VARCHAR(100),
    total_turns           INT NOT NULL DEFAULT 0,
    iteration_count       INT NOT NULL DEFAULT 0,

    -- Outcome for CARS Conversion Rate metric
    conversion_outcome    VARCHAR(50), -- ENUM('no_intent','expressed_interest','added_to_cart','purchased') NOT NULL DEFAULT 'no_intent',
    linked_order_id       BIGINT,                        -- FK added in [7]

    started_at            DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    last_active_at        DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    ended_at              DATETIME(6),

    CONSTRAINT fk_session_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE SET NULL,

    INDEX idx_session_thread   (thread_id),
    INDEX idx_session_user     (user_id),
    INDEX idx_session_status   (status),
    INDEX idx_session_channel  (channel),
    INDEX idx_session_outcome  (conversion_outcome),
    INDEX idx_session_active   (last_active_at)
) ENGINE=InnoDB;

-- ConversationMessages — full message log; Redis holds live state, this is durable record
CREATE TABLE IF NOT EXISTS ConversationMessages (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id  BIGINT NOT NULL,
    turn_number INT    NOT NULL,
    role        VARCHAR(50), -- ENUM('user','assistant','system') NOT NULL,
    content     TEXT   NOT NULL,

    -- Populated for assistant messages to trace which agent produced the turn
    agent_name  VARCHAR(50),     -- orchestrator | kr_agent | psych_agent | synth_agent.md
    latency_ms  INT,
    token_count INT,

    created_at  DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT fk_msg_session FOREIGN KEY (session_id) REFERENCES ConversationSessions(id) ON DELETE CASCADE,

    INDEX idx_msg_session (session_id),
    INDEX idx_msg_turn    (session_id, turn_number),
    INDEX idx_msg_agent   (agent_name)
) ENGINE=InnoDB;

-- PsychStateLogs — per-turn psychological state; feeds CARS Context Consistency metric
CREATE TABLE IF NOT EXISTS PsychStateLogs (
    id               BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id       BIGINT NOT NULL,
    turn_number      INT    NOT NULL,

    psych_state      VARCHAR(50)   NOT NULL,          -- HESITATION | INTEREST | READY_TO_BUY | …
    confidence_score DECIMAL(4,3)  NOT NULL,           -- 0.000–1.000
    primary_concern  VARCHAR(255),
    consult_strategy VARCHAR(100),
    raw_output       JSON,                             -- full Psych Agent JSON output

    created_at       DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT fk_psych_session FOREIGN KEY (session_id) REFERENCES ConversationSessions(id) ON DELETE CASCADE,

    INDEX idx_psych_session (session_id),
    INDEX idx_psych_state   (psych_state)
) ENGINE=InnoDB;

-- AgentPerformanceLogs — latency / token telemetry; feeds CARS Response Latency metric
CREATE TABLE IF NOT EXISTS AgentPerformanceLogs (
    id                   BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id           BIGINT NOT NULL,
    turn_number          INT    NOT NULL,
    agent_name           VARCHAR(50) NOT NULL,

    latency_ms           INT    NOT NULL,
    input_tokens         INT,
    output_tokens        INT,
    retrieval_score      DECIMAL(5,4),                -- composite score from KR Agent Stage 2
    retrieved_product_ids JSON,                       -- product IDs surfaced in this turn

    error_message        TEXT,

    created_at           DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT fk_perf_session FOREIGN KEY (session_id) REFERENCES ConversationSessions(id) ON DELETE CASCADE,

    INDEX idx_perf_session (session_id),
    INDEX idx_perf_agent   (agent_name),
    INDEX idx_perf_latency (latency_ms)
) ENGINE=InnoDB;


-- ============================================================
-- [6] PLATFORM & INFRASTRUCTURE DOMAIN
-- ============================================================

-- APIKeys — retail partner integrations; plaintext key never stored
CREATE TABLE IF NOT EXISTS APIKeys (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    name            VARCHAR(255) NOT NULL,
    key_hash        VARCHAR(255) NOT NULL UNIQUE,     -- SHA-256 of raw key
    key_prefix      VARCHAR(20)  NOT NULL,            -- visible hint e.g. "pk_live_abc…"
    owner_user_id   BIGINT,
    scopes          JSON,                             -- ["chat:write","products:read"]
    rate_limit_rpm  INT     NOT NULL DEFAULT 100,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at    DATETIME(6),
    expires_at      DATETIME(6),

    created_at      DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT fk_apikey_user FOREIGN KEY (owner_user_id) REFERENCES Users(id) ON DELETE SET NULL,

    INDEX idx_apikey_hash   (key_hash),
    INDEX idx_apikey_active (is_active)
) ENGINE=InnoDB;

-- SystemConfigs — runtime feature flags / model params; avoids redeploy for tuning
CREATE TABLE IF NOT EXISTS SystemConfigs (
    id           BIGINT PRIMARY KEY AUTO_INCREMENT,
    config_key   VARCHAR(255) NOT NULL UNIQUE,
    config_value TEXT         NOT NULL,
    value_type   VARCHAR(50), -- ENUM('string','integer','float','boolean','json') NOT NULL DEFAULT 'string',
    description  VARCHAR(500),
    is_sensitive BOOLEAN NOT NULL DEFAULT FALSE,
    updated_by   BIGINT,

    created_at   DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at   DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    INDEX idx_config_key (config_key)
) ENGINE=InnoDB;

-- AuditLogs — append-only; never update or delete rows here
CREATE TABLE IF NOT EXISTS AuditLogs (
    id            BIGINT PRIMARY KEY AUTO_INCREMENT,
    actor_id      BIGINT,
    actor_type    VARCHAR(50), -- ENUM('user','system','api_key') NOT NULL DEFAULT 'user',
    action        VARCHAR(100) NOT NULL,           -- e.g. "order.create", "product.update"
    resource_type VARCHAR(100),
    resource_id   BIGINT,
    old_value     JSON,
    new_value     JSON,
    ip_address    VARCHAR(45),
    user_agent    VARCHAR(500),

    created_at    DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),

    INDEX idx_audit_actor    (actor_id),
    INDEX idx_audit_action   (action),
    INDEX idx_audit_resource (resource_type, resource_id),
    INDEX idx_audit_created  (created_at)
) ENGINE=InnoDB;


-- ============================================================
-- [7] DEFERRED FOREIGN KEYS (cross-domain circular references)
-- ============================================================

-- Orders.conversation_session_id → ConversationSessions
ALTER TABLE Orders
    ADD CONSTRAINT fk_order_session
    FOREIGN KEY (conversation_session_id) REFERENCES ConversationSessions(id) ON DELETE SET NULL;

-- ConversationSessions.linked_order_id → Orders
ALTER TABLE ConversationSessions
    ADD CONSTRAINT fk_session_order
    FOREIGN KEY (linked_order_id) REFERENCES Orders(id) ON DELETE SET NULL;

SET FOREIGN_KEY_CHECKS = 1;
