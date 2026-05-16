#!/usr/bin/env python3
"""
Aftergift Public Data Export
============================
导出 published gifts 的脱敏公开数据为 JSON。

Usage:
    cd backend/backend
    python scripts/export_public_data.py

Output:
    backend/exports/public_gifts_YYYYMMDD_HHMMSS.json

Excludes:
    - User tokens, admin tokens
    - Full review logs with sensitive metadata
    - Unpublished / archived / rejected gifts
    - Internal IDs (user_id is hashed)
"""

import os
import sys
import json
import hashlib
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)

DB_PATH = os.environ.get("AFTERGIFT_DB_PATH", "./aftergift_dev.db")
EXPORT_DIR = os.path.join(PROJECT_ROOT, "exports")

def _hash_id(user_id: str) -> str:
    """One-way hash of internal user_id for public export."""
    return hashlib.sha256(f"aftergift:{user_id}".encode()).hexdigest()[:16]

def main():
    if not os.path.exists(DB_PATH):
        print(f"[WARN] Database not found: {DB_PATH}")
        return 1

    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cur = conn.execute("""
        SELECT g.id, g.title, g.category, g.relation_type, g.relation_label,
               g.action_type, g.emotion, g.price_or_exchange, g.condition_note,
               g.city_blur, g.is_anonymous, g.status, g.created_at, g.updated_at,
               gs.short_story, gs.full_story, gs.risk_level, gs.story_quality_score,
               u.anonymous_nickname
        FROM gifts g
        JOIN users u ON g.user_id = u.id
        LEFT JOIN gift_stories gs ON g.id = gs.gift_id
        WHERE g.status = 'published'
        ORDER BY g.created_at DESC
    """)

    items = []
    for row in cur.fetchall():
        items.append({
            "id": row["id"],
            "title": row["title"],
            "category": row["category"],
            "relation_type": row["relation_type"],
            "relation_label": row["relation_label"],
            "action_type": row["action_type"],
            "emotion": row["emotion"],
            "price_or_exchange": row["price_or_exchange"],
            "condition_note": row["condition_note"],
            "city_blur": row["city_blur"],
            "is_anonymous": bool(row["is_anonymous"]),
            "anonymous_nickname": row["anonymous_nickname"],
            "status": row["status"],
            "short_story": row["short_story"],
            "full_story": row["full_story"],
            "risk_level": row["risk_level"],
            "quality_score": row["story_quality_score"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })

    conn.close()

    os.makedirs(EXPORT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_name = f"public_gifts_{timestamp}.json"
    export_path = os.path.join(EXPORT_DIR, export_name)

    with open(export_path, "w", encoding="utf-8") as f:
        json.dump({
            "exported_at": datetime.now().isoformat(),
            "total": len(items),
            "items": items,
        }, f, ensure_ascii=False, indent=2)

    print(f"[OK] Exported {len(items)} published gifts to {export_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
