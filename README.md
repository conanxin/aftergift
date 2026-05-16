# Aftergift / 后来礼物

> *给一件旧礼物，一个体面的下一站。*
> *Turn the gifts left behind after a relationship ends into stories that can be shared, circulated, sold, exchanged, or donated.*

[English below](#english)

---

## 中文说明

Aftergift（后来礼物）是一个"关系结束后礼物流转与故事记录"的产品原型。它不是普通二手平台，也不是前任曝光区，而是帮助用户以更体面的方式处理带有情感记忆的旧礼物——通过讲述故事、温和流转，让每件礼物都能找到下一个归处。

**产品气质**：温柔、克制、干净、有一点伤感。不鼓励报复、羞辱、猎奇或网暴。

---

## 项目状态

| 状态 | 说明 |
|------|------|
| 🟡 Local Beta | 本地原型阶段，非生产就绪 |
| 🔒 匿名身份 | 用户无需绑定真实手机号或邮箱 |
| 🚫 无真实支付 | 当前不含支付、物流、交易撮合功能 |
| 🔲 评论/私信 | Phase 3A-0 已完成设计评审，尚未实现 |
| 📖 开源透明 | 所有代码、设计文档、阶段报告均在仓库中 |

---

## 功能清单

### 已完成

| 功能 | 说明 |
|------|------|
| 发布礼物故事 | 表单发布，支持匿名，附带故事和情绪标签 |
| 浏览故事流 | 筛选（全部/出售/交换/赠送/捐出/只展示）+ 搜索 |
| 匿名身份 | JWT Bearer Token，无需绑定真实账号 |
| AI/规则审核 | OpenAI Moderation Provider 抽象，沙箱可用 |
| 收藏故事 | 一键收藏我的收藏视图 |
| 搜索与 Discovery | 按关键词、类型、情绪、关系筛选 |
| 我的空间 | 发布管理（编辑/重新提交/归档/恢复）|
| 本地草稿 | 自动草稿保存，`?view=drafts` 管理 |
| Admin 审核台 | 举报队列、人工审核操作、审核日志 |
| 社区治理设计 | 评论政策、审核流程、滥用预防（文档阶段）|

### 未实现（设计阶段）

| 功能 | 状态 |
|------|------|
| 评论功能 | Phase 3A-0 设计评审 ✅，实现待定 |
| 私信功能 | 延后（风险高于评论） |
| 真实支付/物流 | 需支付牌照和法律合规评估 |
| 公开用户主页 | 延后（防止关系追踪骚扰） |

---

## 仓库结构

```
aftergift/
├── frontend/                    # 静态 Web App 原型
│   ├── index.html              # 主页面
│   ├── style.css               # 样式
│   ├── app.js                  # 前端逻辑
│   ├── api-client.js           # API 客户端封装
│   ├── data/gifts.json         # 示例礼物数据（静态模式）
│   └── docs/                   # 前端文档（产品规格、Changelog 等）
├── backend/                    # FastAPI 后端 MVP
│   ├── backend/
│   │   ├── app/                # FastAPI 应用（routers, services, models）
│   │   ├── scripts/            # 运维脚本（init_db, smoke_check, backup 等）
│   │   ├── requirements.txt
│   │   └── .env.example
│   ├── migrations/             # SQLite migration SQL 文件
│   ├── schema/                 # 建表 SQL + seed 数据
│   ├── tests/                  # 合同测试（全量约 150 项）
│   ├── docs/                   # 后端设计文档（API、Auth、审核流、Moderation 等）
│   └── reports/                # 各 Phase 执行报告
├── docs/                       # 顶层文档（部署、使用、路线图等）
└── README.md
```

---

## 快速开始

### 方式一：静态前端（无需后端）

```bash
cd frontend
python3 -m http.server 8080
# 打开 http://127.0.0.1:8080/
```

**重要 URL 参数**：
- `http://127.0.0.1:8080/` — 首页浏览
- `http://127.0.0.1:8080/?view=favorites` — 我的收藏
- `http://127.0.0.1:8080/?view=me` — 我的发布
- `http://127.0.0.1:8080/?view=drafts` — 我的草稿

### 方式二：前端 + 本地 FastAPI 后端

**1. 初始化后端**：

```bash
cd backend/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # 编辑 .env，填入必要的环境变量
python scripts/init_db.py     # 初始化 SQLite 数据库
```

**2. 启动后端**：

```bash
. .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8091
```

**3. 以前端联调模式访问**：

```
http://127.0.0.1:8080/?api=local
```

**4. 进入 Admin 审核面板**：

```
http://127.0.0.1:8080/?api=local&admin=1
```

Admin Token（本地开发用）：`dev-admin-aftergift-001`
> ⚠️ 生产环境必须替换为强随机值。

---

## 环境变量

在 `backend/backend/.env` 中配置：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AFTERGIFT_DB_PATH` | SQLite 数据库路径 | `aftergift_dev.db` |
| `AFTERGIFT_ADMIN_TOKEN` | Admin 访问令牌 | `dev-admin-aftergift-001` |
| `AFTERGIFT_JWT_SECRET` | JWT 签名密钥（生产需 32+ bytes）| `dev-jwt-secret-do-not-use-in-prod` |
| `AFTERGIFT_MODERATION_PROVIDER` | 审核 Provider | `openai` |
| `AFTERGIFT_ENABLE_REAL_AI_REVIEW` | 是否启用真实 AI 审核 | `false` |
| `OPENAI_API_KEY` | OpenAI API Key（仅当 above 为 true 时）| `sk-...` |

---

## 运维脚本

| 脚本 | 用途 |
|------|------|
| `backend/backend/scripts/init_db.py` | 初始化 SQLite 数据库和 seed 数据 |
| `backend/backend/scripts/migrate_db.py` | 运行 pending migrations |
| `backend/backend/scripts/smoke_check.py` | 一键检查服务是否正常运行 |
| `backend/backend/scripts/backup_db.py` | 备份数据库到 `backups/` 目录 |
| `backend/backend/scripts/export_public_data.py` | 导出 published 礼物脱敏数据 |

---

## 测试

```bash
# 核心测试（推荐每次 CI 运行的子集）
python3 backend/tests/test_auth_jwt.py
python3 backend/tests/test_favorites_api.py
python3 backend/tests/test_discovery_api.py
python3 backend/tests/test_my_gifts.py
python3 backend/tests/test_schema.py

# 全量测试（约 150 项）
python3 backend/tests/test_favorites_api.py
python3 backend/tests/test_my_gifts.py
python3 backend/tests/test_my_actions_and_restore.py
python3 backend/tests/test_auth_jwt.py
python3 backend/tests/test_schema.py
python3 backend/tests/test_discovery_api.py
python3 backend/tests/test_my_gift_management.py
python3 backend/tests/test_search_api.py
python3 backend/tests/test_migrations.py
python3 backend/tests/test_admin_enhancements.py
python3 backend/tests/test_redaction.py
python3 backend/tests/test_moderation_provider.py
python3 backend/tests/test_openai_provider.py
```

---

## 部署说明

详见 [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)，简要说明：

- **GitHub Pages**：只能托管 `frontend/` 静态文件，不含后端 API
- **FastAPI 后端**：需要独立服务器（VPS / Docker），不支持 Serverless 静态部署
- **SQLite**：适合本地/小规模内测；生产建议 PostgreSQL + 定期备份
- **生产必须**：强 JWT secret（32+ bytes）、HTTPS、CORS allowlist、API 限速、Admin token 更换

> 当前版本**不是生产就绪**。支付、评论（实现中）、私信均未完成，审核仍需人工兜底。

---

## 安全与内容政策

- [`backend/docs/COMMUNITY_READINESS.md`](backend/docs/COMMUNITY_READINESS.md) — 社区功能就绪检查清单
- [`backend/docs/COMMENTS_POLICY.md`](backend/docs/COMMENTS_POLICY.md) — 评论政策（设计阶段）
- [`backend/docs/ABUSE_PREVENTION.md`](backend/docs/ABUSE_PREVENTION.md) — 滥用预防与威胁模型
- [`frontend/docs/CONTENT_POLICY.md`](frontend/docs/CONTENT_POLICY.md) — 内容安全与伦理政策

**核心原则**：
- ❌ 不曝光他人姓名、照片、电话、地址、社交账号
- ❌ 不发布侮辱、报复、控诉式内容
- ❌ 不把他人真实身份作为卖点
- ❌ 不鼓励网暴或猎奇
- ✅ 匿名化叙述，聚焦物品和自身感受
- ✅ 可以讲述关系，但不要暴露他人

---

## 路线图

### 下一阶段（推荐）

| Phase | 内容 | 说明 |
|-------|------|------|
| **Phase 3A-1** | 评论数据模型 + Migration | 创建 comments 表，先审后发，需确认 |
| Phase 3A-2 | 评论审核引擎 | AI + 规则双层审核 |
| Phase 3A-3 | Admin 评论队列 | 评论审核台 UI |
| Phase 3A-4 | 温和评论 UI | 前端评论展示与交互 |

### 延后阶段

| Phase | 内容 | 说明 |
|-------|------|------|
| Phase 3B | 匿名中继私信 | 风险高于评论，建议评论稳定运行 3 个月后评估 |
| Phase 4 | 交易/交换撮合 | 需法律和支付合规评估 |
| Phase 5 | 生产部署 + PostgreSQL | 高并发支持 |
| Phase 6 | 移动端 / PWA | 独立应用 |

> 私信和支付功能**暂不确定是否实现**，需在评论系统稳定后再评估。

---

## 推荐阅读顺序

1. [`frontend/docs/PRODUCT_SPEC.md`](frontend/docs/PRODUCT_SPEC.md) — 产品规格
2. [`frontend/docs/CONTENT_POLICY.md`](frontend/docs/CONTENT_POLICY.md) — 内容安全与伦理政策
3. [`backend/docs/BACKEND_SPEC.md`](backend/docs/BACKEND_SPEC.md) — 后端 MVP 设计
4. [`backend/docs/AUTH_DESIGN.md`](backend/docs/AUTH_DESIGN.md) — 匿名认证设计
5. [`backend/docs/PHASE2_PLAN.md`](backend/docs/PHASE2_PLAN.md) — Phase 2 完整路线图
6. [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — 部署说明
7. [`docs/ROADMAP.md`](docs/ROADMAP.md) — 完整路线图

---

*Conan Xin — 2026-05-16*