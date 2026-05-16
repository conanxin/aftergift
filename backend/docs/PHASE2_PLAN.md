# Phase 2 实施计划

> Aftergift Phase 2 后端 MVP | 版本：2.1 | 更新：2026-05-16

---

## Phase 2A：沙箱蓝图 ✅ 已完成

**目标**：设计数据库模型、API 契约、审核流程、安全规范，提供可运行的 mock API

**交付物**：
- [x] `docs/BACKEND_SPEC.md`：后端产品说明
- [x] `docs/DATA_MODEL.md`：7 表数据模型
- [x] `docs/API_DESIGN.md`：9 个 REST API
- [x] `docs/REVIEW_WORKFLOW.md`：审核流程图
- [x] `docs/SECURITY_NOTES.md`：安全与隐私说明
- [x] `mock_api/app.py`：可本地运行的 mock API
- [x] `mock_api/mock_review.py`：Mock AI 审核逻辑
- [x] `schema/sqlite_schema.sql`：SQLite 建表语句
- [x] `schema/seed_data.sql`：虚构种子数据
- [x] `tests/test_schema.py`：Schema 测试
- [x] `reports/phase2a_report.md`：Phase 2A 执行报告

**验证结果**：
- SQLite schema 7 表全部通过
- Mock API 3/3 端点 HTTP 200
- `row_factory` bug 已修复
- 无生产服务残留

---

## Phase 2B：FastAPI 框架骨架 ✅ 已完成

**目标**：选择技术栈，建立项目结构，配置环境变量

**交付物**：
- [x] 选择后端框架（FastAPI，理由见 `docs/FASTAPI_DECISION.md`）
- [x] 项目初始化 + 目录结构（`backend/`）
- [x] 数据库连接层（`database.py`，复用 Phase 2A schema）
- [x] 环境变量管理（`.env.example`，不提交到 git）
- [x] FastAPI 骨架（`app/main.py` + 5 个 routers）
- [x] Pydantic schemas（`schemas.py`）
- [x] Mock review service（`services/review_service.py`）
- [x] 匿名化服务（`services/anonymize_service.py`）
- [x] 数据库初始化脚本（`scripts/init_db.py`）
- [x] 合同测试（`tests/test_fastapi_contract.py`）

**技术决策**（详见 `docs/FASTAPI_DECISION.md`）：

| 决策点 | 选择 | 原因 |
|--------|------|------|
| 后端框架 | FastAPI | Python 生态、AI 集成方便、自动文档 |
| 数据库 | SQLite（暂时）| 零配置、够用、文件化管理 |
| ORM | 不用（手写 SQL）| 需求简单、降低复杂度 |
| AI 审核 | Mock（暂时）| 零成本、零延迟 |
| 迁移时机 | Phase 2G 后评估 | 按需迁移，避免过早优化 |

**验证结果**：
- 8/8 合同测试全通过
- `py_compile` 语法检查通过（main, database, schemas, review_service, init_db, test_contract）
- 框架骨架完整，可直接启动

---

## Phase 2C：前后端 local API 双模式联调 ✅ 已完成

**目标**：实现核心 CRUD API，接入真实 SQLite 数据库，前端可在 static 模式和 API 模式间切换

**交付物**：
- [x] FastAPI 主应用（`app/main.py`）
- [x] 数据库连接（`database.py` + SQLite）
- [x] `POST /api/gifts`：故事发布 + 规则预检
- [x] `GET /api/gifts`：公开列表（筛选+分页）
- [x] `GET /api/gifts/{id}`：详情
- [x] `POST /api/gifts/{id}/favorite`：收藏
- [x] `DELETE /api/gifts/{id}/favorite`：取消收藏
- [x] `POST /api/gifts/{id}/report`：举报
- [x] 前端 `?api=local` 模式切换
- [x] 前端 Toast 反馈与后端响应码对接
- [x] CORS 配置（允许 localhost:8080）

**技术注意事项**：
- SQLite 够用，Phase 2G 前不迁移 PostgreSQL
- 不上 SQLAlchemy，用手写 SQL
- `.env` 文件不提交 git

**验证结果**：
- 14/14 API 端点测试全通过
- 前端 static 模式（默认）+ API 模式（`?api=local`）均 200
- 无生产服务残留

---

## Phase 2D：匿名身份 + Admin 审核队列 UI ✅ 已完成

**目标**：建立匿名身份系统，管理员可审核高风险内容

**交付物**：
- [x] `app/auth.py`：HMAC-SHA256 token 生成与验证
- [x] `POST /api/auth/anonymous`：创建匿名身份（user_id + nickname + token）
- [x] `GET /api/auth/me`：验证当前 token
- [x] 所有用户操作端点加 auth gate（gifts / favorites / reports）
- [x] `GET /api/admin/reviews`：审核队列列表（27 字段）
- [x] `POST /api/admin/reviews/{gift_id}/decision`：审核决定（approve / needs_edit / reject）
- [x] Admin Review Panel UI（`?api=local&admin=1`）
- [x] Dev Auth Panel UI（`?api=local`）
- [x] `Authorization: Bearer ***` token 注入

**Token 设计**：
- 格式：`af2d_` + base64url(user_id + ":" + HMAC-SHA256)
- 长度：89 字符
- 存储：localStorage（auth token）、sessionStorage（admin token）
- TTL：7 天

**验证结果**：
- 14/14 API 端点测试全通过
- 8/8 合同测试全通过
- `node --check` 前端文件全部 PASS
- `python3 -m py_compile` 后端文件全部 PASS

---

## Phase 2E：PyJWT 升级 + Moderation Provider 抽象 ✅ 进行中

**目标**：用 PyJWT 替换 HMAC 临时方案，建立可切换的 AI 审核 provider 架构

**交付物**：

### 2E-1：PyJWT Token 升级 ✅ 已完成
- [x] 安装 `PyJWT`
- [x] 生成标准 HS256 JWT token
- [x] 更新 `app/auth.py`：JWT decode / encode 替换 HMAC
- [x] 支持 token 过期（`exp` claim）
- [x] `decode_access_token`：标准 JWT 验证 + 过期检查
- [x] `_require_auth_payload`：返回完整 payload dict
- [x] `_require_auth`：返回 `sub` 字段（str），兼容所有 router
- [x] Token payload 含 `sub/role/jti/iat/exp/token_version`
- [x] POST /api/auth/anonymous 签发 JWT
- [x] GET /api/auth/me 验证 JWT payload
- [x] 更新 .env.example / config.py
- [x] 12/12 合同测试 PASS
- [x] 6/6 运行时验证 PASS（201 JWT / 200 / 401 / 403）

### 2E-2：Moderation Provider 抽象 ✅ 已完成
- [x] 建立 `services/moderation/` 目录
- [x] 定义 `ModerationProvider` 协议 + `ModerationResult` dataclass
- [x] 实现 `MockModerationProvider`（Phase 2D 正则逻辑迁移）
- [x] 实现 `OpenAIModerationProvider` skeleton（默认 mock fallback）
- [x] 实现 `BaiduModerationProvider` skeleton（默认 mock fallback）
- [x] `factory.py` — provider 选择 + fallback 逻辑
- [x] `review_service.py` — 包装 factory，保持 `mock_review()` 兼容
- [x] config.py 添加 MODERATION_PROVIDER / ENABLE_REAL_AI_REVIEW / OPENAI_API_KEY / BAIDU_CONTENT_REVIEW_API_KEY
- [x] .env.example 添加对应配置
- [x] reviewer_type → mock=ai_rule_engine / openai&baidu=ai_moderation_api
- [x] 测试 11/11 PASS
- [x] 旧 test_fastapi_contract.py 8/8 PASS

### 2E-3：审核日志脱敏 ✅ 已完成
- [x] `anonymize_service.py` 增强：`redact_sensitive_text()` / `summarize_redactions()` / `safe_excerpt()` / `redact_review_result()`
- [x] `gifts.py` 写入 review_logs 前自动脱敏 issues / suggestions
- [x] `review_logs.suggestions_json` 嵌入 `redaction_summary`
- [x] `admin.py` 解析 redaction_summary，Admin 队列展示脱敏数据
- [x] 脱敏类型：phone / email / wechat / qq / social / address / name_pattern
- [x] 不存储原始敏感值到 review_logs
- [x] gift_stories 保留原文（供用户查看和 Admin 审核）
- [x] 测试 11/11 PASS

### 2E-4：OpenAI Provider 沙箱实现 🔲 待开始
```
MODERATION_PROVIDER=mock      # mock | openai | baidu
OPENAI_API_KEY=               # OpenAI API Key（仅 provider=openai 时需要）
BAIDU_API_KEY=                # 百度 API Key
JWT_SECRET=                   # HS256 密钥（生产必须更换）
JWT_ALGORITHM=HS256
TOKEN_EXPIRY_DAYS=7
```

**风险**：
- JWT secret 必须强随机，开发期可测试，生产必须更换
- OpenAI API 有成本和延迟，需有 mock 兜底

---

## Phase 2F：Admin 审核台增强 + 举报队列 🔲 待开始

**目标**：完善管理员工具，建立举报管理操作历史

**交付物**：

### 2F-1：Admin 审核队列增强
- [ ] `GET /api/admin/reviews` 增加筛选条件（status / emotion / date_range）
- [ ] `GET /api/admin/reviews` 增加排序（created_at / risk_score）
- [ ] 分页支持（limit / offset）
- [ ] `review_notes` 字段：管理员可写审核备注

### 2F-2：举报管理队列
- [ ] `GET /api/admin/reports`：举报列表（status / gift_id 筛选）
- [ ] `PATCH /api/admin/reports/{id}`：处理举报（dismiss / warn / hide_gift）
- [ ] 举报人匿名处理（不暴露举报人身份）
- [ ] 重复举报去重（同一 gift_id + reporter_id）

### 2F-3：Admin 操作历史
- [ ] `GET /api/admin/actions`：查看 admin_actions 历史
- [ ] 记录管理员 ID、时间戳、操作类型、目标礼物/举报 ID
- [ ] 支持按 admin_id 和时间范围筛选

### 2F-4：申诉处理（可选）
- [ ] 用户对 `rejected` / `needs_edit` 状态发起申诉
- [ ] 申诉记录写入 `appeals` 表
- [ ] Admin 审核申诉

---

## Phase 2G：小范围本地内测 🔲 待开始

**目标**：邀请种子用户内测，收集反馈，修复 bug

**交付物**：

### 2G-1：内测准备
- [ ] 数据备份策略（SQLite 文件备份 + 云存储上传）
- [ ] 风险复盘文档
- [ ] 种子用户招募（20-50 人，朋友圈 / 社区）
- [ ] 内测协议（数据使用说明）

### 2G-2：监控
- [ ] API 错误率监控
- [ ] 审核队列积压监控（超过 24h 告警）
- [ ] Token 使用统计

### 2G-3：反馈收集
- [ ] Telegram 群或匿名表单
- [ ] 用户反馈 NPS 收集
- [ ] 修复 Phase 2E-F 的 bug

### 2G-4：PostgreSQL 迁移评估
满足以下任一条件时评估迁移：
- 并发用户数 > 50
- API P95 响应时间 > 500ms（由 DB 引起）
- 需要全文搜索（PostgreSQL `tsvector`）

**内测验证标准**：
- API P95 响应时间 < 500ms
- 审核队列无积压超过 24h
- 无数据泄露
- 用户反馈 NPS > 40

---

## 资源估算（更新版）

| Phase | 预计工时 | 依赖 |
|-------|---------|------|
| 2A（沙箱蓝图）| 1 天 | 无 |
| 2B（FastAPI 骨架）| 1 天 | 技术选型决策 |
| 2C（SQLite MVP）| 3-5 天 | FastAPI 学习曲线 |
| 2D（匿名身份 + Admin UI）| 2-3 天 | Auth 设计 |
| **2E（PyJWT + Moderation 抽象）**| 3-5 天 | PyJWT 经验 |
| **2F（Admin 增强 + 举报队列）**| 2-3 天 | Admin 前端 |
| **2G（小范围内测）**| 1-2 周 | 种子用户招募 |

**Phase 2E-F 预计：5-8 天**

---

## 关键风险

| 风险 | 影响 | 应对 |
|------|------|------|
| JWT secret 泄露 | 管理员权限被冒用 | 生产必须更换强随机密钥 |
| OpenAI API 成本超支 | 审核费用过高 | mock provider 兜底 + 每日调用上限 |
| 前端跨域 CORS | API 无法调用 | FastAPI CORSMiddleware allow localhost:8080 |
| 恶意举报污染队列 | 审核效率降低 | IP hash 防刷 + 验证码 |
| SQLite 并发限制 | 高并发下性能下降 | Phase 2G 前评估 PostgreSQL 迁移 |
| 种子用户故事质量低 | 平台调性偏离 | 内容政策引导 + 审核层兜底 |

---

## 路线图总览

```
Phase 2A  ✅ 沙箱蓝图
Phase 2B  ✅ FastAPI 骨架
Phase 2C  ✅ SQLite MVP + API 联调
Phase 2D  ✅ 匿名身份 + Admin 审核 UI
Phase 2E  ✅ PyJWT 升级 + Moderation Provider 抽象 + 审核日志脱敏
Phase 2F  🔲 Admin 增强 + 举报队列
Phase 2G  🔲 小范围本地内测
Phase 3A  🔲 社区功能（收藏、评论、私信）
Phase 3B  🔲 交易功能（担保交易、物流、交换撮合）
```

---

*最后更新：Phase 2D 完成后（2026-05-16）。*
