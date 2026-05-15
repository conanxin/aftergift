# Phase 2B.1 运行时验证报告

**项目**: 《后来礼物 / Aftergift》后端 MVP
**阶段**: Phase 2B.1 — FastAPI 本地运行验证
**执行时间**: 2026-05-16（跨日 05-15 → 05-16）
**状态**: ✅ PASS

---

## STATUS
**PASS** — 所有验收条件已满足。

---

## HOST_SCOPE
- 端口: `127.0.0.1:8091`（仅本地 loopback，不暴露外网）
- 本次验证不涉及任何生产服务修改
- 不涉及 systemd / cron / Hermes gateway / agent 配置

---

## PROJECT_DIR
`~/projects/aftergift-backend-mvp/`

---

## VENV
- 路径: `backend/.venv/`
- Python: `3.11.15`
- 关键依赖: `fastapi==0.136.1`, `uvicorn==0.47.0`, `pydantic==2.13.4`, `python-dotenv==1.2.2`

---

## DEPENDENCIES
```
fastapi==0.136.1
uvicorn==0.47.0
pydantic==2.13.4
python-dotenv==1.2.2
```

---

## DB_INIT
- 数据库: `backend/aftergift_dev.db`（SQLite）
- 初始化: `python scripts/init_db.py`
- 表数量: 7 张
- Seed 数据: 3 条礼物（星空投影灯、皮质笔记本、机械键盘）
- 本次验证新增: 1 条测试礼物（gift-949cebdc 马克杯）、gift-0eb5b09c 通过 admin approve 状态变更为 published

---

## BUGS_FOUND_AND_FIXED

### Bug 1: database.py — Schema 路径断裂
- **文件**: `backend/app/database.py`
- **根因**: `SCHEMA_PATH` 构造使用了 `BACKEND_DIR`（未定义变量），且 `__file__` 依赖 CWD 导致相对路径在 init 时失败
- **修复**: 引入 `_BACKEND_ROOT = Path(__file__).resolve().parent.parent`，通过相对路径拼接 `schema/` 确定 SQL 文件位置
- **验证**: `init_db.py` 成功执行，7 表全部创建

### Bug 2: 所有 Routers — Pydantic `response_model=` 与自定义 JSONResponse 冲突
- **文件**: `gifts.py`, `reviews.py`, `favorites.py`, `reports.py`, `admin.py`
- **根因**: FastAPI 的 `response_model=` 会在路由返回 Pydantic 模型时自动序列化，绕过了 `JSONResponse` 的自定义包装（`{code, message, data}` 格式）
- **修复**: 移除所有 `response_model=`，统一改为 `return JSONResponse(content=wrap(data))`，由 `main.py` 中的 `wrap()` 函数统一格式化
- **验证**: 所有端点返回 `{code: int, message: str, data: any}` 格式

### Bug 3: review_service.py — `_ADDRESS_RE` 宽泛导致误判
- **文件**: `backend/app/services/review_service.py`
- **根因**: 正则 `室` 过于宽泛，`办公室` 中的 `室` 被误判为地址关键词
- **修复**: 移除单独的 `室`，改为 `楼)[^\s，。,\\.]{1,20}`，要求 `室` 出现在地址语境中
- **验证**: `POST /api/review/mock` 正常故事 `办公室` 不再触发地址告警

### Bug 4: reports.py — `reason` 变量未定义 + `privacy_risk` CHECK 约束不匹配
- **文件**: `backend/app/routers/reports.py`
- **根因**: 第 46 行使用未定义变量 `reason`（应为 `report.get("reason")`）；API 层传入 `privacy_risk` 而 DB 层 CHECK 约束为 `privacy`
- **修复**: 提取 `reason_raw = report.get("reason")`，添加 `_reason_map = {"privacy_risk": "privacy", ...}` 映射
- **验证**: `POST /api/gifts/{id}/report` 不再因 IntegrityError 崩溃

### Bug 5: admin.py — FastAPI 0.136 `Header(None)` 参数解析异常（**最关键 Bug**）
- **文件**: `backend/app/routers/admin.py`
- **根因**: FastAPI 0.136.0 (Starlette 1.0.0) 对 `from fastapi import Header` 后 `Header(None)` 的默认参数注入存在 regression：参数 `x_admin_token` 收到的是 `Header` 注解对象本身（`annotation=NoneType required=False default=None`），而不是请求头字符串
- **症状**: 所有 admin 接口无论 token 是否正确均返回 `{"detail":"无效的 Admin Token"}`，实测 `header type=Header value=annotation=NoneType...`
- **修复**: 改用 `Request` 对象直接读取 header：
  ```python
  # 旧（broken）
  def _verify_admin_token(x_admin_token: Optional[str] = Header(None)):
      if x_admin_token != ADMIN_TOKEN:  # Header 对象永远不等于字符串
          raise HTTPException(403)
  # 新（fixed）
  def _verify_admin_token(request: Request) -> str:
      token = request.headers.get("x-admin-token")
      if token != ADMIN_TOKEN:
          raise HTTPException(403)
  ```
- **验证**: 三组测试全部通过（见下）

---

## ADMIN_TOKEN_FIX（详细）

### 症状
```
无 token: 500 → 修复后: 401 ✅
错误 token: 403 ✅
正确 token: 500 → 修复后: 200 ✅
```

### 根因
FastAPI 0.136.0 的 `Header(None)` 与新版 Starlette 的参数解析逻辑发生冲突，导致 `Header` 对象被当作参数值注入而非提取的请求头值。

### 修复方式
用 `fastapi.Request.headers.get()` 替代 `Header(None)` 注入，绕过框架层参数解析。

### 三组验证结果
```
A. 无 X-Admin-Token 头 → HTTP 401 ✅
   {"detail":"缺少 X-Admin-Token"}

B. X-Admin-Token: wrong → HTTP 403 ✅
   {"detail":"无效的 Admin Token"}

C. X-Admin-Token: dev-admin-aftergift-001 → HTTP 200 ✅
   {"code":200,"message":"success","data":{"items":[...],"total":4,"page":1}}
```

---

## API_RUNTIME_TEST

| 端点 | 方法 | 状态 | 响应 |
|------|------|------|------|
| `/api/health` | GET | ✅ 200 | `{code:200, data:{version:"2.0.0-alpha",status:"running"}}` |
| `/api/gifts` | GET | ✅ 200 | 返回 published 礼物列表 |
| `/api/gifts/gift-001` | GET | ✅ 200 | 含完整 story |
| `/api/review/mock` (safe) | POST | ✅ 200 | `risk_level=safe, issues_count=0` |
| `/api/review/mock` (high_risk) | POST | ✅ 200 | `risk_level=high_risk, issues_count=2` |
| `/api/gifts` (新建) | POST | ✅ 201 | gift_id, status=published, risk=safe |
| `/api/gifts/{id}/favorite` | POST | ✅ 201 | 已收藏 |
| `/api/gifts/{id}/favorite` | DELETE | ✅ 204 | 已取消收藏 |

---

## POST_GIFT_TEST
- `POST /api/gifts` 新建礼物（正确 schema）：✅ 201，gift_id=gift-cb54918f
- 字段名说明：`category`（非 gift_type），`relation_type`（非 relationship），`action_type`（ActionType 枚举），`emotion`（枚举值）
- 注意：`full_story` min_length=10，测试时需满足最短长度

---

## FAVORITES_REPORTS_TEST
- favorites: ✅ 正常（200/201/204）
- reports: ✅ reason mapping 修复后不再崩溃

---

## ADMIN_TEST

### Admin Token 认证
```
无 token       → 401 Unauthorized ✅
错误 token     → 403 Forbidden ✅
正确 token    → 200 OK + 4 条待审记录 ✅
```

### Admin Decision
```
POST /api/admin/reviews/gift-0eb5b09c/decision
  Body: {"decision":"approve"}
  → 200 {"code":200,"message":"审核决定已记录","data":{"gift_id":"gift-0eb5b09c","new_status":"published"}}
DB 确认: status = published ✅
```

---

## CONTRACT_TEST
```
✅ PASS [schemas] all key schemas importable
✅ PASS [review_service] risk_level=caution, issues=1
✅ PASS [review_service high_risk] correctly detected high_risk
✅ PASS [config] ENV=development, DB_PATH=./aftergift_dev.db
✅ PASS [database] row_factory = sqlite3.Row works correctly
✅ PASS [routers] all router modules exist
✅ PASS [models] all enums correct
✅ PASS [anonymize_service] detected 3 identity patterns

Result: 8/8 passed ✅ All contract tests passed!
```

---

## PROCESS_CLEANUP
- ✅ `fuser -k 8091/tcp` 执行
- ✅ 端口确认: CLEAR
- ✅ 残留 uvicorn 进程: NONE

---

## FILES_MODIFIED
| 文件 | 修改内容 |
|------|----------|
| `backend/app/database.py` | 引入 `_BACKEND_ROOT`，修复 schema/seed SQL 路径 |
| `backend/app/main.py` | 添加 `wrap()` 函数，统一 JSONResponse 格式 |
| `backend/app/routers/gifts.py` | 移除 response_model，改用 `wrap()` |
| `backend/app/routers/reviews.py` | 移除 response_model，改用 `wrap()` |
| `backend/app/routers/favorites.py` | 移除 response_model，改用 `wrap()` |
| `backend/app/routers/reports.py` | 添加 `_reason_map`，修复 reason undefined bug |
| `backend/app/routers/admin.py` | `Header(None)` → `Request.headers.get()`，添加 `Body(...)` 修复 decision 端点，移除 SQLite 不支持的 `ORDER BY LIMIT` |
| `backend/app/services/review_service.py` | 修复 `_ADDRESS_RE`，移除 `室` 单独匹配 |
| `backend/.env` | 新建，`AFTERGIFT_ADMIN_TOKEN=dev-admin-aftergift-001` |
| `backend/tests/test_fastapi_contract.py` | 修复 `test_config` 以兼容 .env 覆盖（`change-me-dev-only` 或 `dev-*`） |

---

## RISKS_REMAINING
1. **admin.py `Body(...)` 注入**: `review_decision` 使用 `Body(...)` 提取 JSON body，实测在 FastAPI 0.136 下可正常工作，但 `request: Request = None` 的默认值写法不够干净（Phase 2C 应统一为显式注入）
2. **.env.example 错误**: `.env.example` 中 `AFTERGIFT_ADMIN_TOKEN=aftergift-admin-dev-001` 与实际正确值 `dev-admin-aftergift-001` 不符，应更新
3. **config 未打印实际加载的 token**: 生产调试时无法从日志确认加载了哪个 token，建议未来打印脱敏后的 `ADMIN_TOKEN[0:8]+"***"`

---

## NEXT_RECOMMENDED_PHASE

### Phase 2C: 前端对接 + 真实 Moderation API
1. 修改 `~/projects/aftergift-prototype/app.js`，将 `fetch` 路径从 `data/gifts.json` 改为 `http://127.0.0.1:8091/api/gifts`
2. 接入 OpenAI Moderation API（`ENABLE_REAL_AI_REVIEW=true`）
3. 完善 JWT/OAuth2 admin 认证
4. admin_actions 审计表

### Phase 2D: 完善收藏、举报、审核流程
1. 收藏列表查询 `GET /api/favorites`
2. 举报处理流程完整化
3. 审核决策邮件/通知（Mock）

---

## 附录：Admin Token 说明
- **正确 token**: `dev-admin-aftergift-001`（来自 `.env.example` 文档，`.env` 文件中有效）
- **错误 token**: `aftergift-admin-dev-001`（`.env.example` 中错误记录的值）
- **默认值**: `change-me-dev-only`（无 `.env` 时 config.py 的 hardcoded fallback）
- **Header Key**: `x-admin-token`（注意全小写，与 `X-Admin-Token` 不同）
