-- Migration 002: Add user_actions table
-- Phase 2H-2 | 2026-05-16
--
-- Tracks user-initiated actions (edit, resubmit, archive, restore)
-- Separate from admin_actions which tracks admin operations.

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
