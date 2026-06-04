CREATE TABLE customers (
    customer_id     CHAR(36)        NOT NULL DEFAULT (UUID()),
    full_name       VARCHAR(100)    NOT NULL,
    phone           VARCHAR(20)     UNIQUE,
    email           VARCHAR(100)    UNIQUE,
    channel         ENUM('web','mobile','zalo','facebook','shopee') NOT NULL DEFAULT 'web',
    profile_data    JSON            COMMENT 'birth_year, gender, purchase_history_summary',
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (customer_id),
    INDEX idx_phone (phone),
    INDEX idx_email (email),
    INDEX idx_channel (channel)
) ENGINE=InnoDB COMMENT='Retail customers — linked to sessions for personalization';

