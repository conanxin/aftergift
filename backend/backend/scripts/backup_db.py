#!/usr/bin/env python3
"""
Aftergift Database Backup Script
================================
备份当前 SQLite 数据库到 backend/backups/ 目录。

Usage:
    cd backend/backend
    python scripts/backup_db.py

Output:
    backend/backups/aftergift_backup_YYYYMMDD_HHMMSS.sqlite
"""

import os
import shutil
from datetime import datetime

DB_PATH = os.environ.get("AFTERGIFT_DB_PATH", "./aftergift_dev.db")
BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backups")

def main():
    if not os.path.exists(DB_PATH):
        print(f"[WARN] Database not found: {DB_PATH}")
        print("       Set AFTERGIFT_DB_PATH or ensure aftergift_dev.db exists.")
        return 1

    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"aftergift_backup_{timestamp}.sqlite"
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    shutil.copy2(DB_PATH, backup_path)
    size_kb = os.path.getsize(backup_path) / 1024
    print(f"[OK] Backup created: {backup_path}")
    print(f"     Size: {size_kb:.1f} KB")
    print(f"     Source: {os.path.abspath(DB_PATH)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
