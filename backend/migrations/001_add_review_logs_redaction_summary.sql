-- Migration 001: Add redaction_summary to review_logs
-- Phase 2F.1 | 2026-05-16
--
-- This migration adds a TEXT column to store structured redaction metadata
-- (e.g., {"redacted": true, "categories": ["phone", "email"], "count": 3})
--
-- Note: SQLite ALTER TABLE ADD COLUMN is idempotent only when the column
-- does not already exist. The Python migration runner checks column existence
-- before executing this script.

ALTER TABLE review_logs ADD COLUMN redaction_summary TEXT;
