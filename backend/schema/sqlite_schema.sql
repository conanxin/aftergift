-- Aftergift SQLite Schema
-- Phase 2A | Version: 1.0

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- ── Users ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                 TEXT PRIMARY KEY,
    anonymous_nickname TEXT NOT NULL,
    phone_hash         TEXT,
    email_hash         TEXT,
    is_admin           INTEGER DEFAULT 0,
    created_at         TEXT DEFAULT (datetime('now')),
    status             TEXT DEFAULT 'active' CHECK (
        status IN ('active', 'suspended', 'deleted')
    )
);

CREATE INDEX IF NOT EXISTS idx_users_phone_hash ON users(phone_hash);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);

-- ── Gifts ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gifts (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    title           TEXT NOT NULL,
    category        TEXT NOT NULL,
    relation_type   TEXT,
    relation_label  TEXT,
    action_type     TEXT NOT NULL CHECK (
        action_type IN ('sell', 'exchange', 'giveaway', 'donate', 'keep')
    ),
    emotion         TEXT NOT NULL CHECK (
        emotion IN ('放下', '遗憾', '感谢', '释怀', '重启', '纪念', '治愈', '平静')
    ),
    price_or_exchange TEXT,
    condition_note  TEXT,
    city_blur       TEXT,
    is_anonymous   INTEGER DEFAULT 1,
    status          TEXT NOT NULL DEFAULT 'draft' CHECK (
        status IN (
            'draft', 'pending_review', 'published',
            'needs_edit', 'rejected', 'archived'
        )
    ),
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_gifts_user_id ON gifts(user_id);
CREATE INDEX IF NOT EXISTS idx_gifts_status ON gifts(status);
CREATE INDEX IF NOT EXISTS idx_gifts_action_type ON gifts(action_type);
CREATE INDEX IF NOT EXISTS idx_gifts_created_at ON gifts(created_at DESC);

-- ── Gift Stories ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gift_stories (
    id                   TEXT PRIMARY KEY,
    gift_id              TEXT NOT NULL UNIQUE,
    short_story          TEXT NOT NULL,
    full_story           TEXT NOT NULL,
    story_quality_score  REAL DEFAULT 0.0,
    risk_level           TEXT NOT NULL CHECK (
        risk_level IN ('safe', 'caution', 'high_risk')
    ),
    created_at           TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (gift_id) REFERENCES gifts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_stories_gift_id ON gift_stories(gift_id);
CREATE INDEX IF NOT EXISTS idx_stories_risk_level ON gift_stories(risk_level);

-- ── Review Logs ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS review_logs (
    id                         TEXT PRIMARY KEY,
    gift_id                    TEXT NOT NULL,
    risk_level                 TEXT NOT NULL,
    identity_risk              INTEGER DEFAULT 0,
    attack_risk                INTEGER DEFAULT 0,
    identifiable_person_risk   INTEGER DEFAULT 0,
    quality_notes              TEXT,
    suggestions_json          TEXT,
    redaction_summary         TEXT,
    reviewer_type             TEXT NOT NULL CHECK (
        reviewer_type IN ('ai_rule_engine', 'ai_moderation_api', 'human_admin')
    ),
    decision                   TEXT CHECK (
        decision IS NULL OR decision IN ('approve', 'reject', 'needs_edit')
    ),
    decided_by                 TEXT,
    decided_at                TEXT,
    created_at                TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (gift_id) REFERENCES gifts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reviews_gift_id ON review_logs(gift_id);
CREATE INDEX IF NOT EXISTS idx_reviews_risk_level ON review_logs(risk_level);
CREATE INDEX IF NOT EXISTS idx_reviews_reviewer_type ON review_logs(reviewer_type);

-- ── Favorites ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS favorites (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    gift_id    TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, gift_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (gift_id) REFERENCES gifts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_favorites_gift_id ON favorites(gift_id);

-- ── Reports ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reports (
    id                TEXT PRIMARY KEY,
    gift_id           TEXT NOT NULL,
    reporter_user_id  TEXT,
    reporter_ip_hash  TEXT,
    reason            TEXT NOT NULL CHECK (
        reason IN ('privacy', 'attack', 'fake', 'other')
    ),
    detail            TEXT,
    status            TEXT NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'reviewing', 'resolved_dismissed', 'resolved_action_taken')
    ),
    assigned_admin_id TEXT,
    resolution_note   TEXT,
    created_at        TEXT DEFAULT (datetime('now')),
    resolved_at       TEXT,
    FOREIGN KEY (gift_id) REFERENCES gifts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reports_gift_id ON reports(gift_id);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at DESC);

-- ── Admin Actions ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admin_actions (
    id          TEXT PRIMARY KEY,
    admin_id   TEXT NOT NULL,
    target_type TEXT NOT NULL CHECK (
        target_type IN ('gift', 'report', 'user')
    ),
    target_id   TEXT NOT NULL,
    action      TEXT NOT NULL CHECK (
        action IN (
            'approve', 'reject', 'needs_edit',
            'suspend_user', 'dismiss_report', 'take_action'
        )
    ),
    note        TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_admin_actions_admin_id ON admin_actions(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_actions_target ON admin_actions(target_type, target_id);

-- ── User Actions ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  gift_id TEXT,
  action TEXT NOT NULL,
  note TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (gift_id) REFERENCES gifts(id)
);

CREATE INDEX IF NOT EXISTS idx_user_actions_user_id ON user_actions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_actions_gift_id ON user_actions(gift_id);
CREATE INDEX IF NOT EXISTS idx_user_actions_created_at ON user_actions(created_at DESC);