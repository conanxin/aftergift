"""
Aftergift Schema Tests
Phase 2A | Test SQLite schema + seed data validity
"""

import sqlite3
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(BASE_DIR, '..', 'schema', 'sqlite_schema.sql')
SEED_PATH = os.path.join(BASE_DIR, '..', 'schema', 'seed_data.sql')
TEST_DB = '/tmp/aftergift_test_phase2a.db'

def clean_test_db():
    """Remove test database if exists."""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def run_tests():
    """Run all schema tests."""
    results = []

    # ── Test 1: Schema loads without error ──────────────────────────────────
    try:
        clean_test_db()
        conn = sqlite3.connect(TEST_DB)
        conn.execute("PRAGMA foreign_keys = ON")
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.close()

        # Verify tables exist
        conn = sqlite3.connect(TEST_DB)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cur.fetchall()]
        conn.close()

        expected = [
            'admin_actions', 'favorites', 'gift_stories', 'gifts',
            'reports', 'review_logs', 'users'
        ]
        if sorted(tables) == sorted(expected):
            results.append(("T1: Schema loads OK, 7 tables created", "PASS"))
        else:
            results.append(("T1: Schema loads OK, 7 tables created", "FAIL",
                             f"Expected {expected}, got {tables}"))
    except Exception as e:
        results.append(("T1: Schema loads OK, 7 tables created", "FAIL", str(e)))

    # ── Test 2: Seed data loads without error ───────────────────────────────
    try:
        conn = sqlite3.connect(TEST_DB)
        conn.execute("PRAGMA foreign_keys = ON")
        with open(SEED_PATH, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.close()
        results.append(("T2: Seed data loads without error", "PASS"))
    except Exception as e:
        results.append(("T2: Seed data loads without error", "FAIL", str(e)))

    # ── Test 3: Row counts ──────────────────────────────────────────────────
    try:
        conn = sqlite3.connect(TEST_DB)
        conn.execute("PRAGMA foreign_keys = ON")
        checks = {
            'users': 3, 'gifts': 3, 'gift_stories': 3,
            'review_logs': 2, 'favorites': 1, 'reports': 1
        }
        all_ok = True
        for table, expected_count in checks.items():
            cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
            actual = cur.fetchone()[0]
            if actual != expected_count:
                results.append(
                    (f"T3: {table} has {expected_count} rows", "FAIL",
                     f"expected {expected_count}, got {actual}")
                )
                all_ok = False
        if all_ok:
            results.append(("T3: All table row counts match", "PASS"))
        conn.close()
    except Exception as e:
        results.append(("T3: All table row counts match", "FAIL", str(e)))

    # ── Test 4: gifts.status CHECK constraint ────────────────────────────────
    try:
        conn = sqlite3.connect(TEST_DB)
        conn.execute("INSERT INTO users (id, anonymous_nickname) VALUES ('test-user', 'test')")
        # Try inserting invalid status
        try:
            conn.execute(
                """INSERT INTO gifts
                   (id, user_id, title, category, action_type, emotion, status)
                   VALUES ('test-gift', 'test-user', 'Test', '家居', 'sell', '放下', 'invalid_status')"""
            )
            conn.commit()
            results.append(("T4: gifts.status CHECK rejects invalid", "FAIL",
                             "Invalid status was accepted"))
        except sqlite3.IntegrityError:
            results.append(("T4: gifts.status CHECK rejects invalid", "PASS"))
        conn.close()
    except Exception as e:
        results.append(("T4: gifts.status CHECK rejects invalid", "FAIL", str(e)))

    # ── Test 5: review_logs risk_level CHECK constraint ─────────────────────
    try:
        conn = sqlite3.connect(TEST_DB)
        try:
            conn.execute(
                """INSERT INTO gifts
                   (id, user_id, title, category, action_type, emotion, status)
                   VALUES ('test-gift-2', 'test-user', 'Test2', '家居', 'sell', '放下', 'pending_review')"""
            )
            conn.execute(
                """INSERT INTO gift_stories
                   (id, gift_id, short_story, full_story, risk_level)
                   VALUES ('test-story-2', 'test-gift-2', 'short', 'full', 'invalid_risk')"""
            )
            conn.commit()
            results.append(("T5: gift_stories.risk_level CHECK rejects invalid", "FAIL",
                             "Invalid risk_level was accepted"))
        except sqlite3.IntegrityError:
            results.append(("T5: gift_stories.risk_level CHECK rejects invalid", "PASS"))
        conn.close()
    except Exception as e:
        results.append(("T5: gift_stories.risk_level CHECK rejects invalid", "FAIL", str(e)))

    # ── Test 6: favorites UNIQUE constraint ──────────────────────────────────
    try:
        conn = sqlite3.connect(TEST_DB)
        conn.execute("PRAGMA foreign_keys = ON")
        # Check existing favorites count first
        cur = conn.execute("SELECT user_id, gift_id FROM favorites LIMIT 1")
        row = cur.fetchone()
        if not row:
            results.append(("T6: favorites UNIQUE constraint prevents duplicates", "FAIL",
                             "No favorites found to test UNIQUE against"))
            conn.close()
        else:
            user_id, gift_id = row
            # Try inserting exact same user_id+gift_id pair (should fail)
            try:
                conn.execute(
                    "INSERT INTO favorites (id, user_id, gift_id) VALUES (?, ?, ?)",
                    ('fav-dup-test', user_id, gift_id)
                )
                conn.commit()
                results.append(("T6: favorites UNIQUE constraint prevents duplicates", "FAIL",
                                 "Duplicate favorite was accepted"))
            except sqlite3.IntegrityError:
                results.append(("T6: favorites UNIQUE constraint prevents duplicates", "PASS"))
            conn.close()
    except Exception as e:
        results.append(("T6: favorites UNIQUE constraint prevents duplicates", "FAIL", str(e)))

    # ── Test 7: FK constraints work ─────────────────────────────────────────
    try:
        conn = sqlite3.connect(TEST_DB)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            conn.execute(
                """INSERT INTO gifts
                   (id, user_id, title, category, action_type, emotion, status)
                   VALUES ('test-gift-3', 'nonexistent-user', 'Test3', '家居', 'sell', '放下', 'draft')"""
            )
            conn.commit()
            results.append(("T7: Foreign key constraints enforced", "FAIL",
                             "Non-existent user_id was accepted"))
        except sqlite3.IntegrityError:
            results.append(("T7: Foreign key constraints enforced", "PASS"))
        conn.close()
    except Exception as e:
        results.append(("T7: Foreign key constraints enforced", "FAIL", str(e)))

    return results

def main():
    print("=" * 60)
    print("Aftergift Phase 2A Schema Tests")
    print("=" * 60)
    print()

    results = run_tests()

    passed = 0
    failed = 0
    for item in results:
        name = item[0]
        status = item[1]
        detail = item[2] if len(item) > 2 else ""

        if status == "PASS":
            passed += 1
            print(f"[PASS] {name}")
        else:
            failed += 1
            print(f"[FAIL] {name}")
            if detail:
                print(f"       → {detail}")

    print()
    print("=" * 60)
    print(f"Results: {passed} PASS / {failed} FAIL")

    if failed == 0:
        print("All tests passed.")
        sys.exit(0)
    else:
        print("Some tests failed.")
        sys.exit(1)

if __name__ == '__main__':
    main()