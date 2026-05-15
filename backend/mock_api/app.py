"""
Aftergift Mock API Server
Phase 2A | 基于 Python 标准库 http.server 的轻量 Mock API
仅用于本地演示，不适合生产使用
"""

import json
import sqlite3
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'aftergift.db')
SCHEMA_PATH = os.path.join(BASE_DIR, '..', 'schema', 'sqlite_schema.sql')
SEED_PATH = os.path.join(BASE_DIR, '..', 'schema', 'seed_data.sql')

# ── Database Setup ──────────────────────────────────────────────────────────

def init_db():
    """Initialize SQLite database with schema and seed data."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Load and execute schema
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())

    # Load and execute seed data
    with open(SEED_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())

    conn.commit()
    return conn

def get_db():
    """Get database connection. Creates if not exists."""
    if not os.path.exists(DB_PATH):
        init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ── Response Helpers ─────────────────────────────────────────────────────────

def json_response(handler, code, data, message="success"):
    """Send JSON response."""
    handler.send_response(code)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.end_headers()
    response = json.dumps({"code": code, "message": message, "data": data}, ensure_ascii=False)
    handler.wfile.write(response.encode('utf-8'))

def error_response(handler, code, message):
    """Send error JSON response."""
    json_response(handler, code, None, message)

# ── Route Handlers ──────────────────────────────────────────────────────────

def handle_health(handler):
    """GET /api/health"""
    json_response(handler, 200, {"version": "2.0.0-alpha", "status": "running"})

def handle_gifts_list(handler, query):
    """GET /api/gifts"""
    conn = get_db()

    # Parse query params
    action_type = query.get('action_type', [None])[0]
    emotion = query.get('emotion', [None])[0]
    page = int(query.get('page', ['1'])[0])
    limit = min(int(query.get('limit', ['8'])[0]), 50)
    offset = (page - 1) * limit

    # Build query
    sql = """
        SELECT g.id, g.title, g.category, g.relation_label, g.action_type,
               g.emotion, gs.short_story as excerpt, g.price_or_exchange,
               g.status, g.is_anonymous, u.anonymous_nickname, g.created_at
        FROM gifts g
        JOIN users u ON g.user_id = u.id
        LEFT JOIN gift_stories gs ON g.id = gs.gift_id
        WHERE g.status = 'published'
    """
    params = []

    if action_type:
        sql += " AND g.action_type = ?"
        params.append(action_type)

    if emotion:
        sql += " AND g.emotion = ?"
        params.append(emotion)

    # Count total
    count_sql = sql.replace("SELECT g.id, g.title, g.category, g.relation_label, g.action_type,\n               g.emotion, gs.short_story as excerpt, g.price_or_exchange,\n               g.status, g.is_anonymous, u.anonymous_nickname, g.created_at", "SELECT COUNT(*)")
    cur = conn.execute(count_sql, params)
    total = cur.fetchone()[0]

    # Fetch page
    sql += " ORDER BY g.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cur = conn.execute(sql, params)
    rows = cur.fetchall()

    action_labels = {
        'sell': '出售', 'exchange': '交换', 'giveaway': '赠送',
        'donate': '捐出', 'keep': '只讲故事'
    }

    items = []
    for row in rows:
        items.append({
            "id": row['id'],
            "title": row['title'],
            "category": row['category'],
            "relation_label": row['relation_label'],
            "action_type": row['action_type'],
            "action_label": action_labels.get(row['action_type'], row['action_type']),
            "emotion": row['emotion'],
            "excerpt": row['excerpt'],
            "price_or_exchange": row['price_or_exchange'],
            "status": row['status'],
            "is_anonymous": bool(row['is_anonymous']),
            "anonymous_nickname": row['anonymous_nickname'],
            "created_at": row['created_at']
        })

    has_more = offset + limit < total

    json_response(handler, 200, {
        "items": items,
        "pagination": {
            "page": page, "limit": limit, "total": total,
            "has_more": has_more
        }
    })

def handle_gift_detail(handler, gift_id):
    """GET /api/gifts/{id}"""
    conn = get_db()

    sql = """
        SELECT g.*, u.anonymous_nickname, gs.short_story, gs.full_story,
               gs.risk_level, gs.story_quality_score, gs.created_at as story_created_at
        FROM gifts g
        JOIN users u ON g.user_id = u.id
        LEFT JOIN gift_stories gs ON g.id = gs.gift_id
        WHERE g.id = ?
    """
    cur = conn.execute(sql, [gift_id])
    row = cur.fetchone()

    if not row:
        return error_response(handler, 404, "礼物不存在或暂不可查看")

    action_labels = {
        'sell': '出售', 'exchange': '交换', 'giveaway': '赠送',
        'donate': '捐出', 'keep': '只讲故事'
    }

    data = {
        "id": row['id'],
        "title": row['title'],
        "category": row['category'],
        "relation_label": row['relation_label'],
        "action_type": row['action_type'],
        "action_label": action_labels.get(row['action_type'], row['action_type']),
        "emotion": row['emotion'],
        "price_or_exchange": row['price_or_exchange'],
        "condition_note": row['condition_note'],
        "city_blur": row['city_blur'],
        "is_anonymous": bool(row['is_anonymous']),
        "anonymous_nickname": row['anonymous_nickname'],
        "status": row['status'],
        "story": {
            "short_story": row['short_story'],
            "full_story": row['full_story'],
            "risk_level": row['risk_level'],
            "quality_score": row['story_quality_score'],
            "created_at": row['story_created_at']
        } if row['short_story'] else None,
        "created_at": row['created_at'],
        "updated_at": row['updated_at']
    }

    json_response(handler, 200, data)

def handle_mock_review(handler):
    """POST /api/review/mock"""
    # Parse request body
    content_length = int(handler.headers.get('Content-Length', 0))
    body = handler.rfile.read(content_length).decode('utf-8')
    data = json.loads(body) if body else {}

    short_story = data.get('short_story', '')
    full_story = data.get('full_story', '')

    # Import and run mock review
    from mock_review import review_story
    result = review_story(short_story, full_story)

    json_response(handler, 200, result)

# ── HTTP Request Handler ────────────────────────────────────────────────────

class RequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == '/api/health':
            handle_health(self)
        elif path == '/api/gifts':
            handle_gifts_list(self, query)
        elif path.startswith('/api/gifts/') and path.count('/') == 3:
            gift_id = path.split('/')[-1]
            handle_gift_detail(self, gift_id)
        else:
            error_response(self, 404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/review/mock':
            handle_mock_review(self)
        else:
            error_response(self, 404, "Not Found")

    def log_message(self, format, *args):
        """Suppress default logging to stdout."""
        pass

# ── Entry Point ──────────────────────────────────────────────────────────────

def run(port=8090):
    """Start the mock API server."""
    # Initialize DB on startup
    if not os.path.exists(DB_PATH):
        print(f"Initializing database at {DB_PATH}...")
        init_db()
        print("Database initialized with schema and seed data.")

    server = HTTPServer(('0.0.0.0', port), RequestHandler)
    print(f"Aftergift Mock API running at http://localhost:{port}")
    print(f"  GET  /api/health        — health check")
    print(f"  GET  /api/gifts         — list gifts")
    print(f"  GET  /api/gifts/{{id}}  — gift detail")
    print(f"  POST /api/review/mock   — mock AI review")
    print(f"Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()

if __name__ == '__main__':
    run()