#!/usr/bin/env python3
"""
Aftergift Backend - Database Initialization Script
Phase 2B | scripts/init_db.py

用法: python3 scripts/init_db.py
"""

import sys
import os

# Add backend/ to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import init_db

def main():
    print("Initializing Aftergift development database...")

    result = init_db(drop_existing=True)

    print(f"✅ Database initialized successfully")
    print(f"   Tables created: {result['tables']}")
    print(f"   Gifts in database: {result['gifts']}")
    print(f"   (Includes {result['gifts']} seed gifts from schema/seed_data.sql)")

if __name__ == "__main__":
    main()
