CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY,
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
    tenant_id TEXT NOT NULL,
    tokens INT NOT NULL,
    reason VARCHAR(100),
    agent_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fleet_agents (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    name VARCHAR(64) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    machine_id VARCHAR(255),
    hostname VARCHAR(255),
    version VARCHAR(20) DEFAULT '1.0.2',
    model_local VARCHAR(120) DEFAULT 'Qwen2.5-1.5B-Instruct.Q4_K_M',
    capabilities JSONB DEFAULT '[]',
    allow_paths JSONB DEFAULT '[]',
    deny_paths JSONB DEFAULT '[]',
    local_systems JSONB DEFAULT '[]',
    auto_start BOOLEAN DEFAULT TRUE,
    offline_capable BOOLEAN DEFAULT TRUE,
    agent_token TEXT NOT NULL,
    install_key VARCHAR(32) NOT NULL UNIQUE,
    last_seen TIMESTAMPTZ,
    last_ip VARCHAR(64),
    tokens_used BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (tenant_id, name)
);

CREATE INDEX IF NOT EXISTS idx_fleet_tenant ON fleet_agents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_fleet_install_key ON fleet_agents(install_key);

CREATE TABLE IF NOT EXISTS fleet_queries (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES fleet_agents(id) ON DELETE CASCADE,
    tenant_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    source VARCHAR(40),
    offline BOOLEAN DEFAULT FALSE,
    evidence JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    answered_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT,
    action VARCHAR(100),
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO tenants (id, name, email, plan, seats, tokens_quota)
VALUES ('default', 'Default Tenant', 'admin@local', 'starter', 3, 500000)
ON CONFLICT (id) DO NOTHING;
