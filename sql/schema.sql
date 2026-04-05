-- ================================================
-- Access Digital Health - Philanthropic Intelligence Platform
-- Supabase Schema — Run this in the Supabase SQL Editor
-- ================================================

-- 1. Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT UNIQUE,
    display_name TEXT,
    api_key_hash TEXT,  -- we store a hash, never the raw key
    giving_profile JSONB DEFAULT '{}',  -- causes, budget, geography, philosophy, experience
    preferences JSONB DEFAULT '{}',  -- UI preferences, default mode, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Portfolio grants
CREATE TABLE IF NOT EXISTS portfolio_grants (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    organization TEXT,
    geography TEXT,
    sector TEXT,
    sector_code TEXT,
    budget TEXT,
    status TEXT DEFAULT 'Active - On track',
    milestones TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Proposal evaluations
CREATE TABLE IF NOT EXISTS evaluations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    proposal_name TEXT,
    proposal_text TEXT,  -- first 3000 chars of uploaded proposal
    sector TEXT,
    geography TEXT,
    recommendation TEXT,  -- FUND / FUND WITH CONDITIONS / DO NOT FUND
    evaluation_text TEXT,  -- full AI evaluation output
    tool_calls JSONB DEFAULT '[]',  -- agent reasoning log
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Report analyses (grantee reports analyzed in portfolio mode)
CREATE TABLE IF NOT EXISTS report_analyses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    grant_id UUID REFERENCES portfolio_grants(id) ON DELETE SET NULL,
    grant_name TEXT,
    report_text TEXT,  -- first 3000 chars of uploaded report
    analysis_text TEXT,  -- full AI analysis output
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Conversations (chat history per mode)
CREATE TABLE IF NOT EXISTS conversations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    mode TEXT NOT NULL,  -- 'donor', 'evaluation', 'portfolio'
    title TEXT,  -- auto-generated from first message
    messages JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Data cache (DHIS2 queries, web research results)
CREATE TABLE IF NOT EXISTS data_cache (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    cache_key TEXT UNIQUE NOT NULL,  -- e.g., "dhis2:malaria:sierra_leone"
    data JSONB NOT NULL,
    source TEXT,  -- 'dhis2', 'web_research', 'evidence'
    ttl_hours INTEGER DEFAULT 24,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours')
);

-- 7. Board reports (generated quarterly reports)
CREATE TABLE IF NOT EXISTS board_reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    period TEXT,  -- e.g., "Q1 2026"
    report_text TEXT,
    portfolio_snapshot JSONB,  -- snapshot of portfolio at time of report
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_portfolio_user ON portfolio_grants(user_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_user ON evaluations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_mode ON conversations(user_id, mode);
CREATE INDEX IF NOT EXISTS idx_cache_key ON data_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON data_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_report_analyses_grant ON report_analyses(grant_id);

-- Auto-update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER users_updated_at
    BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER portfolio_grants_updated_at
    BEFORE UPDATE ON portfolio_grants FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER conversations_updated_at
    BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Row Level Security (RLS) — users can only access their own data
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE board_reports ENABLE ROW LEVEL SECURITY;
-- data_cache is shared across users (public read, system write)

-- For MVP: allow all access via service key (we authenticate in the app layer)
-- In production: replace these with proper per-user RLS policies
CREATE POLICY "Allow all via service key" ON users FOR ALL USING (true);
CREATE POLICY "Allow all via service key" ON portfolio_grants FOR ALL USING (true);
CREATE POLICY "Allow all via service key" ON evaluations FOR ALL USING (true);
CREATE POLICY "Allow all via service key" ON report_analyses FOR ALL USING (true);
CREATE POLICY "Allow all via service key" ON conversations FOR ALL USING (true);
CREATE POLICY "Allow all via service key" ON board_reports FOR ALL USING (true);
CREATE POLICY "Allow all via service key" ON data_cache FOR ALL USING (true);
