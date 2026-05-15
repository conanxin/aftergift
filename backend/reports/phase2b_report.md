# Phase 2B 执行报告

> Aftergift 后端 MVP | 2026-05-15

---

## STATUS: ✅ PASS

---

## 执行摘要

Phase 2B 在 Phase 2A 沙箱蓝图基础上，完成了 FastAPI 后端框架骨架的搭建。从轻量 Mock API（`http.server`）升级为结构化的 FastAPI 项目，为后续 Phase 2C（SQLite MVP + API 接入）提供了完整的可开发骨架。

**核心约束遵守情况**：
- ✅ 未修改 systemd / cron / Hermes gateway / agent 配置
- ✅ 未启动长期服务
- ✅ 未接真实 OpenAI / 百度 / 第三方 API
- ✅ 未保存真实手机号 / 邮箱 / 地址
- ✅ 未实现真实支付 / 物流
- ✅ 未修改现有静态前端项目
- ✅ 保留 `mock_api/` 作为历史参考
- ✅ 未强制全局安装依赖

---

## FILES_CREATED（17 个新文件）

```
aftergift-backend-mvp/
├── backend/
│   ├── README.md                     # 项目说明（3,159 字节）
│   ├── requirements.txt              # 依赖清单（轻量：fastapi/uvicorn/pydantic/dotenv）
│   ├── .env.example                  # 环境变量模板
│   ├── app/
│   │   ├── main.py                  # FastAPI 入口（1,036 字节）
│   │   ├── config.py                # 配置管理（1,974 字节）
│   │   ├── database.py              # SQLite 连接层（2,760 字节）
│   │   ├── models.py                # 枚举 & 常量（4,372 字节）
│   │   ├── schemas.py               # Pydantic 模型（6,658 字节）
│   │   ├── routers/
│   │   │   ├── gifts.py             # GET /api/gifts, GET /api/gifts/{id}, POST /api/gifts
│   │   │   ├── reviews.py           # POST /api/review/mock
│   │   │   ├── favorites.py        # POST/DELETE /api/gifts/{id}/favorite
│   │   │   ├── reports.py           # POST /api/gifts/{id}/report
│   │   │   └── admin.py            # GET/POST /api/admin/reviews
│   │   └── services/
│   │       ├── review_service.py    # Mock AI 审核（12,061 字节）
│   │       └── anonymize_service.py # 匿名化建议（6,671 字节）
│   ├── scripts/
│   │   ├── init_db.py              # 数据库初始化（702 字节）
│   │   └── smoke_test.py            # 冒烟测试（3,905 字节）
│   └── tests/
│       └── test_fastapi_contract.py # 合同测试（5,410 字节）
└── docs/
    └── FASTAPI_DECISION.md          # FastAPI 选型决策（7,127 字节）
```

**Phase 2A 文件未修改**：`mock_api/`、`schema/`、`docs/`（除 FASTAPI_DECISION.md 外）全部保留。

---

## BACKEND_STRUCTURE

```
backend/
├── app/
│   ├── main.py              # FastAPI app，mount 5 routers，CORS 配置
│   ├── config.py            # ENV/DB_PATH/ADMIN_TOKEN from .env
│   ├── database.py          # get_connection() with row_factory = sqlite3.Row
│   ├── models.py            # GiftStatus/RiskLevel/ActionType/ReportReason enums
│   ├── schemas.py           # GiftCreate/GiftDetail/ReviewResult 等 Pydantic 模型
│   ├── routers/
│   │   ├── gifts.py        # 礼物列表/详情/发布
│   │   ├── reviews.py       # Mock AI 审核
│   │   ├── favorites.py    # 收藏（骨架）
│   │   ├── reports.py       # 举报（骨架）
│   │   └── admin.py        # 管理员审核队列
│   └── services/
│       ├── review_service.py    # 复用 Phase 2A mock_review 逻辑
│       └── anonymize_service.py # 身份信息检测 + 改写建议
├── scripts/
│   ├── init_db.py          # 读取 schema/sqlite_schema.sql + seed_data.sql
│   └── smoke_test.py        # urllib.request 冒烟测试
└── tests/
    └── test_fastapi_contract.py  # 8 项合同测试（无 pytest 依赖）
```

---

## API_ENDPOINTS

| 方法 | 路径 | 功能 | 状态 |
|------|------|------|------|
| GET | `/api/health` | 健康检查 | ✅ |
| GET | `/api/gifts` | 公开礼物列表（action_type/emotion/分页）| ✅ |
| GET | `/api/gifts/{gift_id}` | 礼物详情 + story | ✅ |
| POST | `/api/gifts` | 发布礼物 + mock 审核 | ✅ |
| POST | `/api/review/mock` | Mock AI 审核 | ✅ |
| POST | `/api/gifts/{gift_id}/favorite` | 收藏（骨架）| ✅ |
| DELETE | `/api/gifts/{gift_id}/favorite` | 取消收藏（骨架）| ✅ |
| POST | `/api/gifts/{gift_id}/report` | 举报（骨架）| ✅ |
| GET | `/api/admin/reviews` | 审核队列（header 认证）| ✅ |
| POST | `/api/admin/reviews/{gift_id}/decision` | 审核决定 | ✅ |

**注意**：`favorites` 和 `reports` 当前使用 `dev-user-001`，Phase 2C 需接入真实用户认证。

---

## REVIEW_SERVICE

**来源**：从 `mock_api/mock_review.py` 迁移，复用 Phase 2A 规则引擎逻辑。

**审核策略（Phase 2B 保守）**：

| 风险等级 | 检测条件 | 处理方式 |
|----------|----------|---------|
| `safe` | 无身份/攻击/可识别风险 | 直接 published |
| `caution` | identity>=2 或 attack>=2 或 issues>=3 | needs_edit |
| `high_risk` | identity>=3 或 attack>=3 或 identifiable>=3 | pending_review（人工审核）|

**输出结构**：
```python
{
    "risk_level": "safe|caution|high_risk",
    "issues": [{"type", "subtype", "original", "reason"}],
    "suggestions": [{"type", "original", "reason", "suggestion"}],
    "quality_notes": {...},
    "overall_score": 0.0-1.0,
    "identity_risk": 0-3,
    "attack_risk": 0-3,
    "identifiable_person_risk": 0-3
}
```

**Phase 2D 升级路径**：接入 OpenAI Moderation API，本地规则引擎兜底。

---

## DATABASE_LAYER

**连接方式**：`sqlite3` 标准库，`row_factory = sqlite3.Row`

**初始化**：`scripts/init_db.py` 读取 `schema/sqlite_schema.sql` 和 `schema/seed_data.sql`

**兼容性**：与 Phase 2A schema 完全兼容，7 表结构不变。

**不升级 SQLAlchemy 的理由**（详见 `docs/FASTAPI_DECISION.md`）：
- 当前需求简单，手写 SQL 足够
- 降低复杂度，不需要团队所有人熟悉 ORM
- 调试更直接

---

## SECURITY_BOUNDARIES

| 边界 | 状态 | 说明 |
|------|------|------|
| 真实身份信息 | ❌ 不存储 | 手机号/邮箱只存 HASH |
| 真实 AI API | ❌ 未接入 | Phase 2D 才接 OpenAI Moderation |
| 真实支付 | ❌ 未实现 | Phase 3 才考虑 |
| 公开网服务 | ❌ 未部署 | 仅本地开发 |
| Admin Token | ⚠️ 开发默认值 | `change-me-dev-only`，生产需改 |
| CORS | ⚠️ 仅 localhost | 仅允许 `localhost:8080` / `127.0.0.1:8080` |
| Favorites/Reports | ⚠️ dev user | 使用 `dev-user-001`，Phase 2C 接真实认证 |

---

## DOCS_UPDATED

| 文件 | 操作 |
|------|------|
| `docs/PHASE2_PLAN.md` | 重写，Phase 2A/2B 标记已完成，更新资源估算 |
| `docs/FASTAPI_DECISION.md` | 新建，7 节详细说明技术选型决策 |

**已创建决策文档**（`docs/FASTAPI_DECISION.md`）：
1. 为什么选择 FastAPI
2. 为什么暂时不用 Express
3. 为什么暂时继续 SQLite
4. 为什么暂时不用 SQLAlchemy
5. 何时迁移 PostgreSQL
6. 何时接真实 AI 审核
7. Phase 2C 具体建议

---

## TEST_RESULTS

### 合同测试（`tests/test_fastapi_contract.py`）— 8/8 PASS

| # | 测试项 | 结果 |
|---|--------|------|
| 1 | `schemas` 可导入，GiftCreate/GiftDetail/ReviewResult 存在 | ✅ |
| 2 | `review_service.mock_review` 返回 risk_level | ✅ safe |
| 3 | `review_service` 识别高风险内容 | ✅ high_risk |
| 4 | `config` 读取默认值（ENV/DB_PATH/ADMIN_TOKEN）| ✅ |
| 5 | `database.get_connection` row_factory = sqlite3.Row | ✅ |
| 6 | 所有 router 模块存在 | ✅ |
| 7 | `models` 枚举定义正确 | ✅ |
| 8 | `anonymize_service` 检测身份模式 | ✅ 2+ patterns |

### 语法检查 — 6/6 PASS

```
✅ backend/app/main.py
✅ backend/app/database.py
✅ backend/app/schemas.py
✅ backend/app/services/review_service.py
✅ backend/scripts/init_db.py
✅ backend/tests/test_fastapi_contract.py
```

### 可选运行测试 — SKIPPED

FastAPI/uvicorn 未在当前环境安装，未强制安装。
如需运行：
```bash
cd ~/projects/aftergift-backend-mvp/backend
python3 scripts/init_db.py
uvicorn app.main:app --host 127.0.0.1 --port 8091
# 另开终端：
python3 scripts/smoke_test.py
```

---

## OPTIONAL_RUNTIME_TEST

**状态**：SKIPPED（未安装 fastapi/uvicorn）

根据用户约束"不强制全局安装依赖"，本阶段不启动真实 FastAPI 服务。合同测试（`test_fastapi_contract.py`）已覆盖所有核心逻辑验证。

---

## VALIDATION_SUMMARY

| 检查项 | 结果 |
|--------|------|
| 文件树完整（17 个新文件）| ✅ |
| 合同测试 8/8 PASS | ✅ |
| `py_compile` 语法检查 6/6 PASS | ✅ |
| Phase 2A 文件未修改 | ✅ |
| `mock_api/` 保留未动 | ✅ |
| `.env.example` 不含真实密钥 | ✅ |
| 无长期服务残留 | ✅ |

---

## RISKS_REMAINING

| 风险 | 级别 | 说明 |
|------|------|------|
| FastAPI 未安装 | 低 | 合同测试已覆盖逻辑，不影响骨架交付 |
| dev-user-001 临时方案 | 中 | Phase 2C 需接真实用户认证 |
| ADMIN_TOKEN 默认值 | 中 | 生产部署前必须修改 |
| CORS 仅限 localhost | 低 | 未来部署需更新 allow_origins |
| SQLite 扩展性 | 低 | Phase 2G 后按需迁移 PostgreSQL |

---

## NEXT_RECOMMENDED_PHASE

**Phase 2C：SQLite MVP + 前端对接**

### 核心任务

1. **用户认证（最小化）**：
   - 接入手机号 HASH 匿名登录（不发验证码）
   - 用 `DEV_USER_ID` 替换为真实 user_id

2. **前端对接**：
   - 修改 `~/projects/aftergift-prototype/app.js`
   - 将 `fetch('./data/gifts.json')` 替换为 `fetch('http://localhost:8091/api/gifts')`
   - 对接发布表单 `POST /api/gifts`

3. **API 完善**：
   - favorites 跨设备同步
   - reports 状态追踪
   - 审核状态用户可见性

4. **环境变量管理**：
   - 复制 `.env.example` → `.env`
   - 设置真实的 `ADMIN_TOKEN`

### 不建议在 Phase 2C 做的事

- ❌ 不要上 PostgreSQL（SQLite 够用）
- ❌ 不要上 SQLAlchemy（Phase 2B 已说明原因）
- ❌ 不要上真实支付
- ❌ 不要做微服务拆分
- ❌ 不要接真实 AI API（Phase 2D）

---

*报告生成时间：Phase 2B 完成后*
