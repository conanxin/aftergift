# 评论审核工作流文档
**Phase 3A-0 | Comment Review Workflow**
**本文档：设计评审阶段，不实现评论 API**

---

## 1. 评论提交流程总览

```
用户提交评论
    ↓
静态规则检查（正则：电话/微信号/地址等）
    ↓
AI Moderation（OpenAI/Baidu Provider，已抽象化）
    ↓
risk_level 判定
    ↓
状态分流
├── safe       → 直接展示（aftergift_comments.status = 'approved'）
├── caution    → 展示 + 限流（同用户每礼物1条）
├── high_risk  → 暂不展示 → 人工复审队列
└── blocked    → 拒绝（无通知）
    ↓
审核日志写入 comment_review_logs（脱敏后）
```

---

## 2. 风险等级定义

| 等级 | 标识 | 含义 | 行为 |
|------|------|------|------|
| 安全 | `safe` | 无风险词，通过静态规则和 AI 检查 | 直接展示 |
| 注意 | `caution` | 轻微情绪词或模糊身份追问，不构成直接违规 | 展示 + 限流 |
| 高风险 | `high_risk` | 疑似骚扰、身份追问、线下邀约等 | 暂不展示，进人工复审 |
| 阻止 | `blocked` | 明确违规（真实身份/骚扰/威胁/自伤） | 拒绝，静默处理 |

---

## 3. 审核维度

评论审核需评估以下维度：

### 3.1 身份泄露风险
检测评论中是否包含：
- 真实姓名（正则 + AI）
- 手机号（11位数字正则）
- 社交账号（微信号、QQ号、微博号等）
- 地址（省市区详细地址）
- 公司/学校名称
- 车牌、订单号、快递号

### 3.2 骚扰风险
检测：
- 重复发送相似内容（频率检测）
- 情感勒索语气
- 线下邀约
- 威胁语言

### 3.3 报复风险
检测：
- "你应该报复"
- "把照片发出来"
- 对前任/关系对象的人身攻击

### 3.4 交易绕行风险
检测：
- "加我微信"
- "私下转账"
- 提及其他交易平台

### 3.5 自伤 / 暴力风险
检测：
- 自伤意念表达
- 对他人暴力威胁
- 违法内容描述

---

## 4. 与现有 review_logs / redaction 体系的关系

Aftergift 已建立 `review_logs` 表和 `redaction.py` 脱敏系统（Phase 2E-3）。

评论审核将复用以下设计：

### 4.1 review_logs 复用模式

评论审核日志结构与礼物审核日志类似：

```sql
-- 逻辑设计（不创建 migration）
comment_review_logs:
  id           -- UUID 主键
  comment_id   -- 评论 UUID（关联 comments.id）
  reviewer_type -- 'system_static' | 'ai_moderation' | 'human_admin'
  risk_level   -- 'safe' | 'caution' | 'high_risk' | 'blocked'
  issues_json  -- 检测到的具体问题（JSON 数组）
  suggestions_json -- 建议修改内容（JSON 数组，供人工参考）
  redaction_summary -- 脱敏后的内容摘要（供 Admin 查看）
  reviewer_user_id -- 仅 human_admin 时记录
  created_at
```

### 4.2 redaction.py 复用

`backend/app/utils/redaction.py` 中 `redact_text()` 函数将用于：
- 评论内容脱敏（写入 `body_redacted`）
- 评论审核日志脱敏（`redaction_summary`）
- Admin 查看时展示脱敏版本

### 4.3 Moderation Provider 复用

`backend/app/services/moderation/` 中的 Provider 抽象（Phase 2E-2）将直接用于评论审核：
- `MockModerationProvider`（开发/测试）
- `OpenAIModerationProvider`（真实 API）
- `BaiduModerationProvider`（备选）

调用接口：`provider.moderate(text) -> { risk_level, issues[], suggestions[] }`

---

## 5. Admin 审核台后续需要新增的内容

现有 Admin 台（Phase 2D/2F）已有礼物审核队列。评论功能需新增：

### 5.1 评论队列页面
- `GET /api/admin/comments` — 获取待审评论列表
- 列表显示：comment_id（简写）、礼物名称、评论摘要（脱敏）、提交时间、举报数量（如果有）
- 支持筛选：pending_review / flagged

### 5.2 评论详情页
- 评论完整内容（脱敏后）
- 关联礼物信息（礼物名称、发布者匿名ID）
- 审核历史（comment_review_logs）
- 举报记录（comment_reports）

### 5.3 审核操作
- `POST /api/admin/comments/{comment_id}/decision`
  - Body: `{ "decision": "approve" | "reject" | "flag" }`
  - decision=reject 时可附带内部备注（不暴露给评论者）
- approve：评论状态变为 `approved`，通知发布者（可选）
- reject：评论状态变为 `rejected`，静默处理（不主动通知）
- flag：标记为高风险，维持 `pending_review` 状态，安排人工

### 5.4 上下文信息
Admin 查看评论时需看到：
- 礼物故事摘要（判断评论是否与故事相关）
- 发布者的历史行为（是否有多次违规）
- 举报人信息（不向评论者暴露）

---

## 6. 发布者控制能力

### 6.1 隐藏评论
- `POST /api/gifts/{gift_id}/comments/{comment_id}/hide`
- 发布者将某条评论设为 `hidden`
- 其他人看不到，评论者可能仍能看到（取决于产品设计）
- 不删除，只是隐藏

### 6.2 关闭评论
- `PATCH /api/gifts/{gift_id}`
  - Body: `{ "comments_enabled": false }`
- 该礼物新提交的评论全部进入 `pending_review` 状态（即使通过审核也需发布者手动开启显示）

### 6.3 举报评论
- `POST /api/comments/{comment_id}/report`
  - Body: `{ "reason": "harassment" | "identity_leak" | "threat" | "spam", "detail": "..." }`
- 举报后该评论进入优先复审队列

---

## 7. 评论数据表草案

以下为逻辑设计，**不创建 migration**（Phase 3A-1 才创建）：

```sql
-- comments 表
CREATE TABLE comments (
  id              TEXT PRIMARY KEY,        -- UUID
  gift_id         TEXT NOT NULL,           -- 关联 gifts.id
  user_id         TEXT NOT NULL,           -- 发布评论的用户 ID（anonymous_id）
  body_original   TEXT NOT NULL,           -- 原始内容（用于人工复审，不公开）
  body_redacted   TEXT NOT NULL,           -- 脱敏后内容（Admin 查看用）
  status          TEXT NOT NULL DEFAULT 'pending_review',  -- pending_review/approved/rejected/hidden
  risk_level      TEXT,                    -- safe/caution/high_risk/blocked（AI 判断）
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL,
  FOREIGN KEY (gift_id) REFERENCES gifts(id),
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- comment_review_logs 表
CREATE TABLE comment_review_logs (
  id              TEXT PRIMARY KEY,
  comment_id      TEXT NOT NULL,
  reviewer_type   TEXT NOT NULL,           -- system_static/ai_moderation/human_admin
  risk_level      TEXT,
  issues_json     TEXT,                    -- ["identity_phone", "emotional_blackmail"]
  suggestions_json TEXT,                   -- ["建议删除电话号码"]
  redaction_summary TEXT,                  -- 脱敏摘要
  reviewer_user_id TEXT,                   -- 仅 human_admin 时记录
  created_at      TEXT NOT NULL,
  FOREIGN KEY (comment_id) REFERENCES comments(id)
);

-- comment_reports 表
CREATE TABLE comment_reports (
  id              TEXT PRIMARY KEY,
  comment_id      TEXT NOT NULL,
  reporter_user_id TEXT NOT NULL,          -- 举报人
  reason          TEXT NOT NULL,            -- harassment/identity_leak/threat/spam
  detail          TEXT,
  status          TEXT NOT NULL DEFAULT 'pending',  -- pending/reviewed/dismissed
  created_at      TEXT NOT NULL,
  FOREIGN KEY (comment_id) REFERENCES comments(id),
  FOREIGN KEY (reporter_user_id) REFERENCES users(id)
);
```

---

## 8. 状态流转图

```
用户提交 → pending_review
              │
    ┌─────────┼─────────┬──────────┐
    ↓         ↓         ↓          ↓
  safe     caution   high_risk   blocked
    │         │         │          │
    ↓         ↓         ↓          ↓
 approved  approved  人工复审   静默拒绝
               │       │
               │   ┌───┴───┐
               │   ↓       ↓
               │ approve  reject
               │       │
               └────→ approved（重新发布）
```

---

## 9. 本文档状态

- **Phase**：3A-0（设计评审）
- **实现状态**：❌ 不实现，仅文档
- **依赖**：Phase 2E-2（Moderation Provider 抽象）、Phase 2E-3（redaction.py）、Phase 2D（Admin 台基础）

---

*本文档为设计评审文档，不构成产品承诺。评论审核功能需经完整安全评审后方可实施。*