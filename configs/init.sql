-- ISABEL Commercial Schema (base)
CREATE TABLE IF NOT EXISTS tenants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'starter',
    seats INT DEFAULT 1,
    tokens_used BIGINT DEFAULT 0,
    tokens_quota BIGINT DEFAULT 500000,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS plans (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    monthly_tokens BIGINT NOT NULL,
    price_brl NUMERIC(10,2) NOT NULL,
    seats INT DEFAULT 1
);

INSERT INTO plans (id, name, monthly_tokens, price_brl, seats) VALUES
    ('starter', 'Starter', 500000, 297.00, 3),
    ('pro', 'Pro', 2000000, 897.00, 10),
    ('enterprise', 'Enterprise', 10000000, 2497.00, 50)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS token_usage (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INT REFERENCES tenants(id),
    tokens INT NOT NULL,
    reason VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    tenant_id INT REFERENCES tenants(id),
    machine_id VARCHAR(255) UNIQUE,
    hostname VARCHAR(255),
    last_seen TIMESTAMPTZ,
    version VARCHAR(20),
    active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INT,
    action VARCHAR(100),
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
