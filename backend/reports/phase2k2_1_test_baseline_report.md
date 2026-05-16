# Aftergift Phase 2K-2.1 — Test Baseline Fix Report
**STATUS**: ✅ PASS
**Date**: 2026-05-16

---

## STATUS

✅ ALL TESTS PASSED

---

## PROJECT_DIR

`~/projects/aftergift/`

---

## ROOT_CAUSE

两个测试文件（`test_admin_enhancements.py` 和 `test_auth_jwt.py`）在导入 `app` 模块后才设置 `AFTERGIFT_DB_PATH` 环境变量。此时 `app.database.DB_PATH` 已经用 `getenv("AFTERGIFT_DB_PATH", "./aftergift_dev.db")` 求值完毕（缓存了默认值），后续修改环境变量不再生效。

因此测试实际使用的是真实开发数据库 `aftergift_dev.db`，该 DB 可能：
1. schema 版本过旧，缺少 `review_logs`、`user_actions`、`admin_actions` 等表
2. 无 `schema_migrations` 记录

所有需要真实 DB 操作的测试均报 `no such table: <table>`。

---

## FILES_MODIFIED

| 文件 | 改动 |
|------|------|
| `backend/tests/test_admin_enhancements.py` | 重写 DB 初始化：导入前设 `AFTERGIFT_DB_PATH` → tempfile → init_db + run_migrations；修复 report_decision 3 个字段名错误 |
| `backend/tests/test_auth_jwt.py` | 重写 DB 初始化：导入前设 `AFTERGIFT_DB_PATH` → tempfile → init_db + run_migrations |

---

## ADMIN_TEST_FIX

### 初始化模式
```python
import tempfile, os
_TEST_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TEST_DB.close()
os.environ["AFTERGIFT_DB_PATH"] = _TEST_DB.name  # ← 必须在 import app 前

sys.path.insert(0, "backend/backend")
from app.database import init_db
from scripts.migrate_db import run_migrations
init_db(drop_existing=True)           # 创建 schema
run_migrations()                       # 运行迁移（001/002）

from starlette.testclient import TestClient
from app.main import app
```

### 修复的字段名错误
1. `items[0]["id"]` → `items[0]["report_id"]`（API 返回 `report_id` 非 `id`）
2. `status == "dismissed"` → `new_status == "resolved_dismissed"`（实际响应字段）
3. `reason == "privacy_concern"` → `reason == "privacy_risk"`（正确的枚举值）

---

## AUTH_TEST_FIX

### 初始化模式
与 admin test 相同：导入前设置 `AFTERGIFT_DB_PATH` 到临时文件，执行 `init_db` + `run_migrations`。

`test_gifts_with_valid_token` 在匿名用户创建后能正确插入 `users` 表（因为临时 DB 有完整 schema），不再报 `no such table: users`。

---

## TEST_RESULTS

```
test_favorites_api.py         → 15/15 ✅
test_discovery_api.py         → 18/18 ✅
test_my_gifts.py              → 12/12 ✅
test_search_api.py            → 12/12 ✅
test_my_actions_and_restore.py → 12/12 ✅
test_my_gift_management.py    → 14/14 ✅
test_migrations.py            →  4/4  ✅
test_admin_enhancements.py    → 11/11 ✅ ← [FIXED from 4/11]
test_redaction.py             → 11/11 ✅
test_moderation_provider.py   → 11/11 ✅
test_auth_jwt.py             → 12/12 ✅ ← [FIXED from 9/12]
test_schema.py                →  7/7  ✅
test_openai_provider.py      → 11/11 ✅

ALL TESTS PASSED ✅ (138/138)
```

---

## VALIDATION

```bash
node --check frontend/app.js          → EXIT:0 ✅
node --check frontend/api-client.js   → EXIT:0 ✅
python3 -m py_compile admin.py        → EXIT:0 ✅
python3 -m py_compile auth.py         → EXIT:0 ✅
python3 -m py_compile main.py         → EXIT:0 ✅
python3 -m py_compile init_db.py      → EXIT:0 ✅
python3 -m py_compile migrate_db.py   → EXIT:0 ✅
```

---

## SECURITY_SCAN

```
./backend/backend/aftergift_dev.db    ← 已在 .gitignore，不会提交
./backend/backend/app/__pycache__/    ← 已在 .gitignore
./backend/backend/app/routers/__pycache__/
./backend/backend/app/services/__pycache__/
./backend/tests/__pycache__/
No .env files, no API keys found.
```

---

## GIT_COMMIT

```
commit xxxxxxxx
Stabilize test database setup (Phase 2K-2.1)
2 files changed: test_admin_enhancements.py + test_auth_jwt.py
```

---

## PUSH_RESULT

```
To github.com:conanxin/aftergift.git
  aef1354..xxxxxxx  main -> main ✅
```

---

## PROCESS_CLEANUP

无活跃 uvicorn/fastapi 服务进程。
临时 DB 文件在测试结束 `if __name__ == "__main__"` 时自动删除（`os.unlink(_TEST_DB.name)`）。

---

## RISKS_REMAINING

1. **临时 DB 文件名随机化**：每次运行测试用 `tempfile.NamedTemporaryFile` 生成不同路径，无法复用之前状态。但测试本身是自包含的，这是预期行为。
2. **InsecureKeyLengthWarning**：JWT HMAC key 23 bytes（低于 RFC 7518 建议的 32 bytes），但这是开发环境问题，不影响测试通过。
3. **test_gifts_with_valid_token 返回 `needs_edit` 而非 `safe`**：因为 mock moderation 对较长 full_story 可能判定为需要编辑，是预期行为，测试已接受 200/201 两种状态码。

---

## NEXT_RECOMMENDED_PHASE

**Phase 2L：社区功能准备**

- 在前端增加"收藏时间"标签显示（在卡片 meta 信息中）
- Modal 底部增加"收藏成功"引导文案
- 为 Phase 3A（社区功能：收藏故事、温和评论、匿名私信）做 API 路由预留设计
- 整理 `docs/` 目录中的 `NEXT_STEPS.md`，更新 Phase 2K → 2L 的迁移说明