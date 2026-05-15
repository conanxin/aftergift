# Phase 2 实施计划

> Aftergift Phase 2 后端 MVP | 版本：2.0

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
- [x] 文档（`docs/FASTAPI_DECISION.md`）

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

## Phase 2C：SQLite MVP — 数据库 + API 接入

**目标**：接入真实 SQLite 数据库，实现核心 API，与前端联调

**交付物**：
- [ ] `app.py`（FastAPI 主应用） — ✅ `app/main.py` 已完成
- [ ] 数据库连接（`database.py` + SQLite） — ✅ 已完成
- [ ] 用户注册/登录 API（手机号 HASH）
- [ ] `POST /api/gifts`：故事发布 + 规则预检 + AI 审核
- [ ] `GET /api/gifts`：公开列表（筛选+分页）
- [ ] `GET /api/gifts/{id}`：详情
- [ ] `POST /api/gifts/{id}/favorite`：收藏
- [ ] `DELETE /api/gifts/{id}/favorite`：取消收藏
- [ ] 基础前端联调（用真实 API 替代 `data/gifts.json`）

**技术注意事项**：
- SQLite 够用，Phase 2G 前不迁移 PostgreSQL
- 不上 SQLAlchemy，用手写 SQL
- `.env` 文件不提交 git

**风险**：
- 前端跨域问题（FastAPI CORS 已配置 localhost:8080）
- AI 审核 API 延迟（需做异步队列，Phase 2D 再接真实 API）

---

## Phase 2D：前后端完整联调

**目标**：联调所有功能：story/review/favorite/report

**交付物**：
- [ ] `POST /api/gifts/{id}/report`：举报
- [ ] 审核状态展示（pending_review / needs_edit / published）
- [ ] 收藏跨设备同步（手机号 HASH 登录）
- [ ] 前端 Toast 反馈与后端响应码对接
- [ ] 移动端 API 测试通过

**AI 审核接入**：
- Phase 2D 接入 OpenAI Moderation API（免费 tier）
- 配合本地规则引擎兜底（先用本地，high_risk 再调 API）
- 详见 `docs/FASTAPI_DECISION.md` 第 6 节

**风险**：
- CORS 配置复杂（需允许前端 origin）
- 分页 cursor 实现需前后端同步

---

## Phase 2E：审核队列 + 管理员工具

**目标**：建立审核队列，管理员可复审高风险内容

**交付物**：
- [ ] `GET /api/admin/reviews`：审核队列列表
- [ ] `POST /api/admin/reviews/{gift_id}/decision`：审核决定
- [ ] 管理员 Web 后台（简单 HTML + AJAX）
- [ ] `GET /api/admin/reports`：举报列表
- [ ] `PATCH /api/admin/reports/{id}`：处理举报
- [ ] Telegram Bot 通知（新审核任务 / 新举报）

**Telegram Bot 实现**：
```python
import telegram

async def notify_admin.new_review(gift_id: str, risk_level: str):
    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"🆕 新审核任务\n礼物ID: {gift_id}\n风险: {risk_level}"
    )
```

**风险**：
- Telegram Bot token 需保密管理
- 管理员权限控制（防止未授权访问）

---

## Phase 2F：管理员后台 + 审核日志

**目标**：完善管理员功能，审核日志可查

**交付物**：
- [ ] 管理员登录（固定账号密码，暂不做复杂权限）
- [ ] 审核历史查看（review_logs）
- [ ] 管理员操作日志（admin_actions）
- [ ] 申诉处理（用户对 rejected 的故事申诉）
- [ ] 批量操作（批量 approve / reject）

**风险**：
- 管理员账号安全（建议后续接入 Google Auth）

---

## Phase 2G：小范围内测

**目标**：邀请种子用户内测，收集反馈，修复 bug

**交付物**：
- [ ] 邀请 20-50 名种子用户（朋友圈/社区）
- [ ] 监控：API 错误率、审核队列积压
- [ ] 反馈收集：Telegram 群 / 匿名表单
- [ ] 修复 Phase 2C-F 的 bug
- [ ] 数据备份策略（SQLite 文件备份）

**PostgreSQL 迁移评估**（如果出现以下情况）：
- 并发用户数 > 50
- API P95 响应时间 > 500ms（由 DB 引起）
- 需要全文搜索（PostgreSQL `tsvector`）

**内测验证标准**：
- API P95 响应时间 < 500ms
- 审核队列无积压超过 24h
- 无数据泄露
- 用户反馈 NPS > 40

**风险**：
- 种子用户故事质量低（需引导）
- 恶意用户尝试违规（审核层兜底）

---

## 资源估算

| Phase | 预计工时 | 依赖 |
|-------|---------|------|
| 2A（沙箱蓝图）| 1 天 | 无 |
| 2B（FastAPI 骨架）| 1 天 | 技术选型决策 |
| 2C（SQLite MVP）| 3-5 天 | FastAPI 学习曲线 |
| 2D（前后端联调）| 2-3 天 | 前端 API 替换 |
| 2E（审核队列）| 3-5 天 | Telegram Bot 经验 |
| 2F（管理员后台）| 2-3 天 | Admin 前端 |
| 2G（小范围内测）| 1-2 周 | 种子用户招募 |

**总计**：约 3-4 周（如果全职投入）

---

## 关键风险

| 风险 | 影响 | 应对 |
|------|------|------|
| 前端跨域 CORS | API 无法调用 | FastAPI CORSMiddleware allow localhost:8080 |
| AI 审核 API 限流 | 审核队列积压 | 本地规则引擎兜底 |
| 恶意举报 | 审核队列被污染 | IP hash 防刷 + 验证码 |
| 数据丢失 | SQLite 文件损坏 | 定期备份 + 备份上传到云存储 |
| 管理员账号泄露 | 后台被入侵 | 二次验证 + 操作留痕 |

---

*最后更新：Phase 2B 完成时生成。*
