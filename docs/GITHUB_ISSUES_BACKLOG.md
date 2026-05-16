# Aftergift GitHub Issues Backlog

> 本文档列出 Aftergift 各 Phase 的待办 Issues，可手动创建到 GitHub。
> GitHub 仓库：https://github.com/conanxin/aftergift

---

## Phase 2E Issues

### Issue #1: Replace dev HMAC token with PyJWT
**Title**: Phase 2E-1: Replace HMAC-SHA256 token with PyJWT

**Goal**: 用行业标准 JWT 替换当前的 HMAC 临时 token 方案，支持过期和撤销。

**Acceptance Criteria**:
- [ ] 安装 PyJWT，移除 HMAC 逻辑
- [ ] Token 包含 `exp`（过期）、`iat`（签发）、`jti`（唯一 ID）声明
- [ ] 新增 `revoked_tokens` 表，支持 token 撤销
- [ ] `POST /api/auth/logout` 将 jti 写入 revoked 表
- [ ] `GET /api/auth/me` 验证 JWT 时检查 revoked 表
- [ ] 过期 token 返回 401
- [ ] 14/14 API 端点测试 PASS
- [ ] 前端 `api-client.js` 兼容新旧 token 格式

**Risk**: 中 — JWT secret 必须强随机；需处理 token 格式迁移

**Phase**: 2E

---

### Issue #2: Add token expiry and revoke table
**Title**: Phase 2E-2: Add token expiry and revocation mechanism

**Goal**: 建立完整的 token 生命周期管理，防止泄露后无限期使用。

**Acceptance Criteria**:
- [ ] `revoked_tokens` 表：`id`, `token_jti`, `revoked_at`
- [ ] `POST /api/auth/logout` 端点
- [ ] `GET /api/auth/me` 同时验证签名 + 过期 + revoked
- [ ] `exp` claim 设为 7 天（可配置）
- [ ] `refresh_token` 流程（可选，Phase 2E 或 3A）

**Risk**: 中 — refresh token 流程复杂，可延到 Phase 3A

**Phase**: 2E

---

### Issue #3: Add moderation provider abstraction
**Title**: Phase 2E-3: Add moderation provider abstraction layer

**Goal**: 建立可切换的 AI 审核 provider 架构，保留 mock 兜底。

**Acceptance Criteria**:
- [ ] `services/moderation/base.py` 定义 `ModerationProvider` 抽象基类
- [ ] `services/moderation/mock_provider.py` 迁移现有正则逻辑
- [ ] `services/moderation/openai_provider.py` 调用 OpenAI Moderation API
- [ ] `services/moderation/baidu_provider.py` 调用百度内容审核 API
- [ ] `MODERATION_PROVIDER` 环境变量切换 provider
- [ ] `review_service.py` 调用抽象 provider，不直接依赖实现
- [ ] Provider 切换不影响 API 响应格式

**Risk**: 中 — OpenAI API 有成本，需设置每日调用上限

**Phase**: 2E

---

### Issue #4: Add OpenAI moderation provider behind env flag
**Title**: Phase 2E-4: Implement OpenAI moderation provider behind feature flag

**Goal**: 在 mock provider 稳定后，接入真实的 OpenAI Moderation API。

**Acceptance Criteria**:
- [ ] `OPENAI_API_KEY` 环境变量（不硬编码）
- [ ] `OPENAI_MODERATION_MODEL=text-moderation-latest`
- [ ] 调用 OpenAI Moderation API，解析 `flagged` 和 `categories`
- [ ] `MODERATION_PROVIDER=openai` 时启用
- [ ] API 调用失败时自动降级到 mock provider
- [ ] 每日调用量统计日志

**Risk**: 中 — API 成本，免费 tier 上限需监控

**Phase**: 2E

---

### Issue #5: Redact sensitive fields in review logs
**Title**: Phase 2E-5: Redact sensitive fields before writing review logs

**Goal**: 审核日志入库前脱敏，不存储原始人名、手机号、地址等。

**Acceptance Criteria**:
- [ ] `services/anonymize_service.py` 扩展脱敏规则：
  - 手机号 → `[手机号]`
  - 地址 → `[地址]`
  - 2-4 字中文姓名 → `[姓名]`
  - 公司名 → `[公司]`
  - 社交账号（@开头）→ `[账号]`
- [ ] `review_logs.ai_input` / `ai_output` 写入前脱敏
- [ ] 脱敏操作本身可审计（记录"某字段被脱敏"，不记录原始值）
- [ ] `GET /api/admin/reviews` 响应格式不变（原始内容对 Admin 可见）
- [ ] 单元测试覆盖所有脱敏规则

**Risk**: 低 — 纯数据处理逻辑

**Phase**: 2E

---

## Phase 2F Issues

### Issue #6: Add admin review filters and pagination
**Title**: Phase 2F-1: Add filters, sorting, and pagination to admin review queue

**Goal**: 让管理员高效处理审核队列，支持多维度筛选和分页。

**Acceptance Criteria**:
- [ ] `GET /api/admin/reviews` 增加 `status` 筛选（pending / needs_edit / published / rejected）
- [ ] `GET /api/admin/reviews` 增加 `emotion` 筛选
- [ ] `GET /api/admin/reviews` 增加 `date_from` / `date_to` 时间范围筛选
- [ ] `GET /api/admin/reviews` 增加 `sort_by`（created_at / risk_score）、`order`（asc / desc）
- [ ] `GET /api/admin/reviews` 增加 `limit` / `offset` 分页
- [ ] Admin Review Panel UI 同步更新筛选器和分页控件
- [ ] `review_notes` 字段：Admin 可写审核备注

**Risk**: 低 — 纯查询增强

**Phase**: 2F

---

### Issue #7: Add report management queue
**Title**: Phase 2F-2: Implement report management queue for admins

**Goal**: 建立举报管理流程，管理员可处理举报内容。

**Acceptance Criteria**:
- [ ] `GET /api/admin/reports`：举报列表
  - 支持 `status` 筛选（pending / resolved / dismissed）
  - 支持 `gift_id` 筛选
  - 支持分页
- [ ] `PATCH /api/admin/reports/{id}`：处理举报
  - `dismiss`：无效举报，忽略
  - `warn`：向礼物发布者发送系统警告（不暴露举报人身份）
  - `hide_gift`：隐藏该礼物（用户仍可见自己的礼物）
- [ ] 同一 `gift_id + reporter_id` 重复举报合并为一条
- [ ] 举报人身份对 Admin 不可见
- [ ] Admin 操作记录写入 `admin_actions`

**Risk**: 中 — 警告消息内容需审核，防止滥用

**Phase**: 2F

---

### Issue #8: Add admin action history view
**Title**: Phase 2F-3: Add admin action history view and audit trail

**Goal**: 完整记录管理员操作，支持合规审计。

**Acceptance Criteria**:
- [ ] `GET /api/admin/actions`：Admin 操作历史
  - 字段：`id`, `admin_id`, `action_type`, `target_type`, `target_id`, `created_at`
  - 支持 `admin_id` 筛选
  - 支持 `action_type` 筛选（approve_review / reject_review / dismiss_report / warn_user）
  - 支持时间范围筛选
  - 支持分页
- [ ] Admin Review Panel 增加"操作历史" Tab
- [ ] `admin_actions` 表字段与实际使用一致
- [ ] Admin 只能查看自己的操作历史（不包含其他 admin 的操作）

**Risk**: 低 — 纯查询功能

**Phase**: 2F

---

## Phase 2G Issues

### Issue #9: Add local beta test checklist
**Title**: Phase 2G-1: Prepare and execute local beta test checklist

**Goal**: 邀请种子用户进行本地内测，收集反馈，修复问题。

**Acceptance Criteria**:
- [ ] `docs/BETA_TEST_CHECKLIST.md`：内测检查清单
  - [ ] 数据备份方案（每日备份 + 云存储上传）
  - [ ] 内测协议（数据使用说明 + 隐私政策）
  - [ ] 种子用户招募（20-50 人）
  - [ ] API 错误率 < 1%
  - [ ] 审核队列无积压（pending > 24h 为积压）
  - [ ] 匿名反馈表单链接
  - [ ] Telegram 私密反馈群（可选）
  - [ ] NPS 收集（每周）
  - [ ] Phase 2E-F bug 修复清单
- [ ] `docs/RISK_REVIEW.md`：风险复盘文档
- [ ] `scripts/backup.py`：自动备份脚本（每日定时）
- [ ] 备份上传至云存储（AWS S3 / Cloudflare R2）

**Risk**: 中 — 种子用户故事质量不可控，需内容引导

**Phase**: 2G

---

## Phase 3A Issues

### Issue #10: Design low-risk story interactions
**Title**: Phase 3A-1: Design low-risk story interaction system (favorites + anonymous comments)

**Goal**: 在 Phase 2E-F 完成后，设计低风险社区互动功能。

**Acceptance Criteria**:
- [ ] `docs/STORY_INTERACTIONS_DESIGN.md`：互动功能设计文档
  - 收藏故事（`POST /api/gifts/{id}/favorite`）
  - 匿名评论（`POST /api/gifts/{id}/comments`，需 Admin 审核后可见）
  - 匿名私信（频率限制：每用户每礼物限 1 条，每天最多 5 条）
- [ ] 评论内容审核（同礼物审核流程）
- [ ] 私信反骚扰机制（同 IP 限流）
- [ ] 用户 Reputation 分数（低 reputation 限制操作）
- [ ] `GET /api/gifts/{id}/comments`：获取评论列表（仅 Admin 审核通过）
- [ ] 不包含公开评论流（防止网络暴力扩散）

**Risk**: 中 — 匿名评论和私信是骚扰风险最高的两个功能，需严格频率限制

**Phase**: 3A

---

## Issue 优先级总览

| # | Issue | Phase | Priority | Risk |
|---|-------|-------|----------|------|
| 1 | PyJWT token 升级 | 2E | P0 | 中 |
| 2 | Token 过期与撤销 | 2E | P0 | 中 |
| 3 | Moderation provider 抽象 | 2E | P0 | 中 |
| 4 | OpenAI moderation provider | 2E | P1 | 中 |
| 5 | 审核日志脱敏 | 2E | P1 | 低 |
| 6 | Admin 审核队列筛选/分页 | 2F | P1 | 低 |
| 7 | 举报管理队列 | 2F | P1 | 中 |
| 8 | Admin 操作历史 | 2F | P1 | 低 |
| 9 | 本地内测检查清单 | 2G | P2 | 中 |
| 10 | 低风险互动设计 | 3A | P2 | 中 |

---

## 手动创建 Issues 方法

由于 `gh` CLI 不可用，请手动创建：

1. 打开 https://github.com/conanxin/aftergift/issues/new
2. 选择对应 Issue title 和内容（见上方模板）
3. 添加 Labels：`phase-2e` / `phase-2f` / `phase-2g` / `phase-3a`
4. 添加 Milestone：Phase 2E / Phase 2F / Phase 2G / Phase 3A

---

*文档更新：2026-05-16*
