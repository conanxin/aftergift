# Phase 3A 实施计划
**Phase 3A-0 至 Phase 3A-5**

> 本文档说明 Phase 3A 评论功能各子阶段的实施计划，以及 Phase 3B 私信功能的延后建议。

---

## Phase 3A-0（当前阶段）：设计评审 ✅

**目标**：社区功能设计评审与安全边界文档，不实现任何功能。

**完成内容**：
- `COMMENTS_POLICY.md` — 评论政策（允许/禁止/灰区/可见性规则）
- `COMMENT_REVIEW_WORKFLOW.md` — 评论审核工作流（风险等级/审核维度/与现有体系关系）
- `COMMENTS_API_DESIGN.md` — 评论 API 设计草案（端点/数据表/状态流转）
- `ANONYMOUS_MESSAGING_DESIGN_REVIEW.md` — 匿名私信设计评审（模板化中继方案）
- `ABUSE_PREVENTION.md` — 滥用预防与威胁模型（8种威胁/7层防护）
- `PHASE3A_PLAN.md` — 本文档（各子阶段计划）

**状态**：✅ 完成（设计评审，无代码实现）

---

## Phase 3A-1：评论数据模型与 Migration

**目标**：创建评论相关数据库表，建立基础 CRUD。

**前置条件**：
1. Phase 3A-0 设计评审文档完成 ✅
2. 用户确认后开始实施

**实施内容**：

1. **数据库 Migration**
   - 创建 `comments` 表（含 `body_original`/`body_redacted`/`status`/`risk_level`）
   - 创建 `comment_review_logs` 表
   - 创建 `comment_reports` 表
   - 编写回滚脚本（支持 migration rollback）

2. **基础 CRUD API**
   - `POST /api/gifts/{gift_id}/comments` — 提交评论
   - `GET /api/gifts/{gift_id}/comments` — 获取评论列表（仅 approved）
   - `GET /api/me/comments` — 获取我的评论
   - `POST /api/comments/{comment_id}/report` — 举报评论
   - `POST /api/gifts/{gift_id}/comments/{comment_id}/hide` — 隐藏评论

3. **频率限制**
   - 每用户每礼物 1 条评论
   - 每用户每小时 10 条评论
   - 每 IP 每小时 20 条评论

4. **静态规则检查**
   - 正则检测手机号、微信号、地址等
   - 检测到直接拒绝（不写入数据库）

**安全验证**：
- 测试评论提交频率限制
- 测试静态规则拦截
- 测试 `body_redacted` 脱敏输出

**不包含**：AI moderation（Phase 3A-2）、Admin 队列（Phase 3A-3）

---

## Phase 3A-2：评论审核引擎

**目标**：实现完整的评论审核流程（静态规则 → AI moderation → risk_level 判定）。

**前置条件**：
1. Phase 3A-1 完成
2. `ModerationProvider` 抽象已存在（Phase 2E-2）
3. 用户确认后开始实施

**实施内容**：

1. **审核工作流**
   - 评论提交 → 静态规则检查 → AI moderation → risk_level 判定 → 状态分流
   - 复用 `backend/app/services/moderation/` 中的 Provider
   - `comment_review_logs` 写入审核记录

2. **风险等级处理**
   - `safe` → 自动 approved
   - `caution` → approved（限流）
   - `high_risk` → `pending_review`（进入人工队列）
   - `blocked` → `rejected`（静默）

3. **Admin 审核端点**
   - `GET /api/admin/comments` — 待审评论队列
   - `POST /api/admin/comments/{comment_id}/decision` — 审核决策（approve/reject/flag）
   - `DELETE /api/admin/comments/{comment_id}` — 删除评论

4. **审核 SLA 配置**
   - 高风险内容：4 小时内审核
   - 普通标记内容：24 小时内审核

**安全验证**：
- 测试各 risk_level 的状态流转
- 测试 `comment_review_logs` 脱敏记录
- 测试 Admin 审核操作的权限控制

---

## Phase 3A-3：Admin 评论队列

**目标**：在 Admin 审核台新增评论队列界面，完整实现 Phase 3A-0 设计的审核功能。

**前置条件**：
1. Phase 3A-2 完成

**实施内容**：

1. **Admin 台评论页面**
   - 评论队列列表（筛选：pending_review / flagged）
   - 评论详情（脱敏内容 + 原始内容 + 礼物上下文）
   - 审核操作（approve / reject / flag）
   - 举报记录查看

2. **评论上下文**
   - 显示关联礼物的名称和故事摘要
   - 显示评论者匿名 ID
   - 显示举报次数和举报理由

3. **审核历史**
   - `comment_review_logs` 完整展示
   - 审核操作记录（Admin 操作历史）

4. **批量操作**
   - 批量 approve / reject
   - 批量标记高风险

---

## Phase 3A-4：前端温和评论 UI

**目标**：在礼物详情 Modal 中实现评论 UI，包含发布、查看、隐藏功能。

**前置条件**：
1. Phase 3A-1 完成（基础 API 就绪）
2. 用户确认后开始实施

**实施内容**：

1. **评论入口**
   - Modal 详情底部增加"评论"区块（默认折叠，点击展开）
   - 评论数 badge（如已实现评论功能）

2. **评论列表**
   - 显示已通过审核的评论（`status=approved`）
   - 每条显示：脱敏内容 + 时间 + 匿名标记
   - 礼物发布者可见隐藏按钮

3. **评论输入**
   - 简短输入框（5~500字）
   - 模板化开场白推荐（Phase 3A-0 设计）
   - 提示文案："请用简短、温和的语气回应这个故事。"

4. **发布者控制**
   - 隐藏按钮（每条评论）
   - 关闭评论开关（礼物级别）

5. **审核状态展示**
   - 提交后显示"等待审核"
   - 通过后展示
   - 被拒绝后显示"这条评论暂时无法展示"

**UI 风格**：
- 保持 Aftergift 温柔克制风格
- 大量留白
- 短句展示

---

## Phase 3A-5：举报与隐藏评论

**目标**：完整实现评论举报和隐藏功能，形成闭环。

**前置条件**：
1. Phase 3A-2 完成（审核引擎就绪）

**实施内容**：

1. **举报 UI**
   - 每条评论的举报入口（举报按钮或长按菜单）
   - 举报表单：选择理由（骚扰/身份泄露/威胁/垃圾信息/其他）+ 补充说明（可选，200字）
   - 提交后显示"已收到举报"

2. **举报处理**
   - 举报后该评论立即提高优先级
   - 举报量 ≥ 3 时自动触发人工审核
   - 举报处理结果记录在案

3. **隐藏功能**
   - 礼物发布者点击"隐藏"后，其他用户看不到该评论
   - 评论者可能仍能看到自己评论（取决于设计）
   - 发布者可随时取消隐藏

4. **举报反馈**
   - 用户可查看自己的举报历史
   - 举报处理后不主动通知举报者（避免激怒）

---

## Phase 3A-6：匿名中继私信设计二次评审（不默认实现）

**目标**：对 Phase 3A-0 的私信设计进行二次评审，确认是否具备实施条件。

**前置条件**：
1. Phase 3A-1 至 Phase 3A-5 完成
2. 评论功能稳定运行至少 3 个月
3. 用户确认后开始评估

**二次评审内容**：
1. 评论系统运行期间是否有重大安全事故
2. 用户举报率是否在可接受范围
3. Admin 审核负担是否可控
4. 私信功能是否仍然是用户核心需求

**建议**：私信功能延后至 Phase 3B-1，Phase 3B-0 专注二次评审和实施计划修订。

---

## Phase 3B 延后建议

**私信功能延后理由**：
1. 私信风险高于评论（一对一私密性，无社区监督）
2. 模板化中继方案实施复杂度高
3. 评论系统需先稳定运行以验证审核机制有效性

**Phase 3B-0**：私信功能二次评审（基于 Phase 3A 运行数据）
**Phase 3B-1**：私信数据模型与基础 API（如果评审通过）

---

## 前置条件检查清单

在开始 Phase 3A-1 之前，必须确认：

| 前置条件 | 状态 |
|---------|------|
| Phase 3A-0 设计评审文档完成 | ✅ |
| 用户确认开始 Phase 3A-1 | ⬜ 待确认 |
| Moderation Provider 抽象就绪（Phase 2E-2） | ✅ |
| Admin 台基础功能就绪（Phase 2D/2F） | ✅ |
| redaction.py 脱敏工具就绪（Phase 2E-3） | ✅ |

---

## 本文档状态

- **Phase**：3A-0（设计评审）
- **实现状态**：❌ 不实现，仅计划文档
- **后续**：需用户确认后才开始 Phase 3A-1

---

*本文档为设计评审文档，不构成产品承诺。所有阶段需经安全评审后方可实施。*