# Aftergift 下一步：为什么是 Phase 2E

> 本文档说明 Aftergift 当前完成状态，以及为什么下一步不是交易功能，而是 Phase 2E 安全加固。

---

## 1. 当前完成状态

| Phase | 内容 | 完成度 | 说明 |
|-------|------|--------|------|
| Phase 1 | 静态产品 Demo | 100% | 完整前端原型，含故事流、筛选、详情、发布表单 |
| Phase 2A | 后端沙箱蓝图 | 100% | 数据模型、API 设计、审核流程、安全规范 |
| Phase 2B | FastAPI 骨架 | 100% | 所有 routers 实现，SQLite 数据库 |
| Phase 2C | 前后端双模式联调 | 100% | static 模式（默认）+ API 模式（`?api=local`） |
| Phase 2D | 匿名身份 + Admin UI | 100% | HMAC token、27 字段审核队列、Admin Review Panel |
| Phase 2E-1 | PyJWT Token 升级 | 100% | HMAC → PyJWT JWT，payload=sub/role/jti/iat/exp |
| Phase 2E-2 | Moderation Provider 抽象 | 100% | Provider 抽象层、Mock/OpenAI/Baidu 可切换 |
| Phase 2E-3 | 审核日志脱敏 | 100% | review_logs 自动脱敏，Admin 队列脱敏展示 |
| Phase 2E-4 | OpenAI Provider 沙箱 | 100% | 真实 OpenAI Moderation API 沙箱接入，默认不启用，fallback mock |
| Phase 2F | Admin 增强 + 举报队列 | 100% | 审核队列增强、举报管理、Admin 操作历史 |
| Phase 2G-1 | 搜索 API + 前端搜索 UI | 100% | 多维搜索、筛选、分页、排序 |
| Phase 2G-2 | 我的发布 / 我的收藏 | 100% | mine=true、favorites_of=me、前端筛选标签、状态 badge |
| Phase 2H-1 | 我的发布管理 | 100% | GET/PATCH/resubmit/archive、前端编辑 Modal、状态机保护 |
| Phase 2H-2 | 恢复/操作历史/API alias | 100% | restore、user_actions、/api/me/ 路径、编辑草稿自动保存 |
| Phase 2I-0 | 本地内测准备 | 100% | smoke test、备份脚本、seed 数据指南、反馈表、release notes |
| Phase 2K-1 | 收藏视图 | 100% | `?view=favorites`、Hero 收藏入口、返回首页、API favorites_of=me、静态模式 localStorage |
| Phase 2K-2 | 收藏数量 Badge + 排序 | 100% | Hero 收藏按钮 Badge、按收藏时间倒序（最新收藏在前）、auth 失败分级处理 |
| Phase 2L-1 | 社区功能准备 / Community Readiness | 100% | 收藏时间标签、收藏成功引导文案、Modal 静默提示、COMMUNITY_READINESS.md |
| Phase 2L-2 | 我的空间 / Private User Space | 100% | `?view=me`、身份状态卡片、统计网格、发布列表、操作历史、本地草稿计数 |

---

## 2. 为什么不是交易功能（Phase 3A/3B）？

很多团队会急着做"交易"和"社区"功能，因为它们直接产生商业价值。但 Aftergift 目前的风险暴露面使这样做很危险：

### 当前身份系统的风险（Phase 2E-1 已升级）
- ~~**HMAC token 是临时方案**：无标准 JWT 的 `exp`、`iss`、`sub`声明~~ → ✅ Phase 2E-1 已升级为 PyJWT
- **Token 无撤销机制**：如果 token 泄露，无法撤销，只能等 7 天自然过期
- **localStorage XSS 风险**：token 存 localStorage，XSS 攻击可窃取身份

### 当前审核系统的风险
- **Mock 审核靠正则规则**：无法识别语境中的讽刺、反讽、暗示
- **无真实 Moderation API**：无法处理中文内容的复杂审核
- **审核日志未脱敏**：人名、手机号等原始内容直接写入数据库

### 当前 Admin 台的风险
- **Admin 操作无完整审计**：admin_actions 表存在但字段设计不完整
- **举报队列未实现**：`POST /api/gifts/{id}/report` 有端点但无 Admin 管理界面
- **无申诉机制**：用户无法对 `rejected` / `needs_edit` 提起申诉

### 如果现在做交易会怎样
1. 用户用匿名身份发起交易 → 无法追责恶意行为
2. 恶意内容通过 Mock 审核 → 暴露在公开交易中
3. 交易纠纷 → 无 Admin 工具处理举报
4. 隐私泄露 → 无日志脱敏，Admin 可看到原始敏感信息

**结论**：Phase 2E 是安全基础设施，不是功能开发。跳过它直接做交易会把风险放大 10 倍。

---

## 3. Phase 2E 详细计划

### 2E-1：PyJWT Token 升级

**目标**：用行业标准 JWT 替换 HMAC 临时方案

**具体任务**：
1. 安装 `PyJWT`：`pip install PyJWT`
2. 生成 RS256 密钥对（或 HS256 强随机密钥）
3. 更新 `app/auth.py`：
   - `create_token(user_id)` → 签发标准 JWT，含 `exp`（过期时间）、`iat`（签发时间）、`sub`（用户 ID）
   - `verify_token(token)` → JWT decode + 签名验证 + 过期检查 + revoked 表检查
4. 新增 `revoked_tokens` 表：
   ```sql
   CREATE TABLE revoked_tokens (
     id INTEGER PRIMARY KEY,
     token_jti TEXT UNIQUE,  -- JWT ID (jti claim)
     revoked_at DATETIME DEFAULT CURRENT_TIMESTAMP
   );
   ```
5. `POST /api/auth/logout`：将 token jti 写入 revoked 表
6. `GET /api/auth/me`：验证 JWT 时同时检查 revoked 表
7. 前端：`api-client.js` 升级 Bearer token 格式（兼容新旧）

**验收标准**：
- [ ] `python3 -m py_compile` 所有文件通过
- [ ] JWT 包含 `exp`、`iat`、`jti` 声明
- [ ] 过期 token 返回 401
- [ ] revoked token 返回 401
- [ ] 14/14 API 端点测试仍然 PASS

**风险**：中 — JWT secret 必须强随机，前端 localStorage XSS 风险仍需解决（HttpOnly cookie 方案 Phase 3A 再做）

---

### 2E-2：Moderation Provider 抽象

**目标**：建立可切换的 AI 审核 provider 架构，保留 mock 兜底

**Provider 架构**：
```
services/moderation/
├── __init__.py
├── base.py          # ModerationProvider 抽象基类
├── mock_provider.py # 现有正则规则逻辑
├── openai_provider.py
└── baidu_provider.py
```

**环境变量**：
```bash
MODERATION_PROVIDER=mock   # mock | openai | baidu
# openai
OPENAI_API_KEY=sk-...
OPENAI_MODERATION_MODEL=text-moderation-latest
# baidu
BAIDU_API_KEY=
BAIDU_SECRET_KEY=
```

**验收标准**：
- [ ] `MODERATION_PROVIDER=mock` 时行为与 Phase 2D 完全一致
- [ ] `MODERATION_PROVIDER=openai` 时调用 OpenAI Moderation API
- [ ] Provider 切换不影响 API 响应格式
- [ ] 14/14 API 端点测试 PASS

**风险**：中 — OpenAI API 有成本（免费 tier 够小范围内测），Baidu API 需要申请

---

### 2E-3：审核日志脱敏

**目标**：审核日志（review_logs）在写入前脱敏，不存储原始敏感内容

**脱敏规则**：
- 手机号：正则替换为 `[手机号]`
- 地址：替换为 `[地址]`
- 姓名（2-4 字中文名）：替换为 `[姓名]`
- 公司名（特定后缀）：替换为 `[公司]`
- 社交账号（@开头）：替换为 `[账号]`

**注意**：脱敏的是礼物故事内容，不是 gift 表数据。Admin 在审核队列看到的是原始内容（因为那是用户输入），但写入 review_logs 的是脱敏版本。

**验收标准**：
- [ ] `review_logs.ai_input` 不包含手机号/真实姓名/地址
- [ ] 脱敏操作本身可审计（记录"某字段被脱敏"但不记录原始内容）
- [ ] `GET /api/admin/reviews` 响应格式不变

**风险**：低 — 纯数据处理逻辑

---

## 4. Phase 2F 计划（Admin 增强 + 举报队列）

### 2F-1：审核队列增强
- `GET /api/admin/reviews` 增加 `status`、`emotion`、`date_from`、`date_to` 筛选参数
- `GET /api/admin/reviews` 增加 `sort_by`（created_at / risk_score）、`order`（asc / desc）
- `GET /api/admin/reviews` 增加分页（`limit`、`offset`）
- Admin 可对礼物写 `review_notes`（审核备注）

### 2F-2：举报管理队列
- `GET /api/admin/reports`：举报列表（`status`、`gift_id` 筛选）
- `PATCH /api/admin/reports/{id}`：处理举报
  - `dismiss`：无效举报，忽略
  - `warn`：向礼物发布者发送系统警告（不暴露举报人）
  - `hide_gift`：隐藏该礼物（用户仍可见自己的礼物）
- 重复举报去重：同一 `gift_id + reporter_id` 合并为一条
- 举报人身份对 Admin 不可见（防止管理员作弊）

### 2F-3：Admin 操作历史
- `GET /api/admin/actions`：查看 admin_actions 历史
- 字段：`id`、`admin_id`、`action_type`、`target_type`、`target_id`、`created_at`
- 支持按 `admin_id`、`action_type`、`时间范围` 筛选

### 2F-4：申诉机制（可选）
- 用户对 `rejected` / `needs_edit` 状态可在 7 天内提起申诉
- 申诉写入 `appeals` 表
- Admin 在申诉队列处理（维持原判 / 改为通过）

---

## 5. Phase 2G 计划（本地内测）

### 2G-1：内测准备
- 数据备份：每日自动备份 SQLite 文件，上传至云存储
- 种子用户：邀请 20-50 人（朋友圈 / 社区）
- 内测协议：明确数据使用范围和隐私政策
- 风险复盘：识别 Phase 2E-F 未覆盖的风险场景

### 2G-2：监控
- API 错误率监控（错误率 < 1%）
- 审核队列积压告警（pending > 24h 触发通知）
- Token 滥用检测（同 IP 短时间内大量请求）

### 2G-3：反馈收集
- 匿名反馈表单
- Telegram 私密群组（仅受邀用户）
- 定期（每周）收集 NPS 分数

### 2G-4：PostgreSQL 迁移评估
触发条件（满足任一）：
- 并发用户数 > 50
- API P95 响应时间 > 500ms（DB 原因）
- 需要全文搜索

---

## 6. Phase 3A 社区功能边界

### 包含
- ✅ 收藏故事（用户收藏感兴趣的礼物故事）
- ✅ 匿名评论（发布者在 Admin 审核后可见，低风险互动）
- ✅ 匿名私信（频率限制，防止骚扰）

### 不包含
- ❌ 自由发帖（需完整审核队列 + reputation 系统）
- ❌ 公开评论流（防止网络暴力）
- ❌ 真实支付（需支付牌照）
- ❌ 真实物流（需物流 SDK 对接）
- ❌ 公开社交图谱（防止骚扰扩散）

---

## 7. 风险优先级表

| 风险 | 优先级 | 解决阶段 | 说明 |
|------|--------|---------|------|
| HMAC token 无标准签名 | ~~P0~~ → ~~Phase 2E~~ | ✅ Phase 2E-1 已解决（PyJWT HS256） |
| Token 无撤销机制 | P0 | Phase 2E | 泄露后无法止损 |
| AI 审核为 Mock | P0 | Phase 2E | 无法处理复杂内容 |
| 审核日志未脱敏 | P1 | Phase 2E | 管理员可看到原始敏感信息 |
| 举报队列无 Admin 管理 | P1 | Phase 2F | 举报无法处理 |
| Admin 操作无完整审计 | P1 | Phase 2F | 操作合规性无保障 |
| localStorage XSS | P2 | Phase 3A | 升级 HttpOnly cookie |
| SQLite 并发限制 | P2 | Phase 2G | 评估后决定迁移 |
| 无 refresh token | P2 | Phase 2E | 用户体验差 |
| 审核无实时通知 | P3 | Phase 3A | Telegram Bot |

---

## 8. 执行顺序

```
Phase 2E（安全基础设施）
  ├── 2E-1 PyJWT 升级 ✅
  ├── 2E-2 Moderation Provider 抽象 ✅
  ├── 2E-3 审核日志脱敏 ✅
  └── 2E-4 OpenAI Provider 沙箱 ✅

Phase 2F（Admin 增强）
  ├── 2F-1 审核队列增强 ✅
  ├── 2F-2 举报管理队列 ✅
  └── 2F-3 Admin 操作历史 ✅

Phase 2G（内容发现）
  ├── 2G-1 搜索 API + 前端搜索 UI ✅
  └── 2G-2 我的发布 / 我的收藏 ✅

Phase 2H（个人内容管理增强）✅ 已完成
  ├── 2H-1 编辑/重新提交/归档 ✅
  └── 2H-2 恢复/操作历史/API alias ✅

Phase 2I-0（本地内测准备）✅ 已完成
  ├── smoke_check.py / backup_db.py / export_public_data.py
  ├── BETA_SEED_DATA.md / BETA_TEST_PLAN.md / BETA_FEEDBACK_FORM.md
  ├── KNOWN_ISSUES.md / RELEASE_NOTES_PHASE2_LOCAL_BETA.md
  └── README.md 更新

Phase 2I（基础内容推荐）🔲 下一步推荐
  ├── 按情绪/关系类型推荐相似故事
  ├── 热门故事排序
  └── 新发布故事流

Phase 2K（收藏体验）✅ 已完成
  ├── 2K-1 收藏视图 ✅
  ├── 2K-2 收藏数量 Badge + 排序 ✅
  └── 2K-2.1 测试基线修复 ✅

Phase 2L（社区功能准备）✅ 已完成
  ├── 2L-1 收藏时间标签 ✅
  ├── 2L-1 收藏成功引导文案 ✅
  ├── 2L-1 Modal 静默提示 ✅
  └── 2L-1 COMMUNITY_READINESS.md ✅（安全边界 + API 设计预留）

Phase 3A（社区功能）🔲 待定（需 Phase 2L 安全评审）
  ├── 收藏故事 ✅（已完成）
  ├── 温和评论系统（先发后审 + 模板化开场白）
  └── 匿名私信（模板化中继）
  ⚠️ 评论/私信暂不开放，需先完成审核队列产品化和匿名中继设计

Phase 3B（交易功能）
  └── （需完成 Phase 2E-I + 完整审核机制后再评估）
```

---

## 9. Phase 2H-1 执行摘要

### 已完成
- `GET /api/gifts/me/gifts/{id}`：用户查看自己的礼物详情（含审核备注）
- `PATCH /api/gifts/me/gifts/{id}`：编辑礼物（仅 draft/pending_review/needs_edit）
- `POST /api/gifts/me/gifts/{id}/resubmit`：重新提交审核（needs_edit/draft → pending_review）
- `POST /api/gifts/me/gifts/{id}/archive`：撤回归档（published/pending_review/needs_edit → archived）
- 前端"我的发布"卡片操作按钮 + 编辑 Modal
- 编辑 story 后自动重新审核，review_logs 脱敏
- 全量测试 105/105 PASS

### 当前限制
- 路径层级较深：`/api/gifts/me/gifts/{id}`（因 gifts router prefix）→ Phase 2H-2 已新增 `/api/me/gifts/{id}`
- 无草稿自动保存 → Phase 2H-2 已实现 localStorage 草稿
- 归档后无法恢复 → Phase 2H-2 已实现 restore
- 无用户操作历史时间线 → Phase 2H-2 已实现 user_actions

### 下一步建议
**Phase 2I：基础内容推荐**（按情绪/关系类型推荐相似故事、热门排序、新发布流）
或根据内测反馈优先修复

---

*文档更新：Phase 2H-1 完成后（2026-05-16）。*
