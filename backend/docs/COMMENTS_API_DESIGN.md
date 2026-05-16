# 评论 API 设计草案
**Phase 3A-0 | Comments API Design**
**本文档：设计评审阶段，不创建 migration，不实现 API**

---

## 1. 设计原则

1. **先审后发**：所有评论默认 `pending_review` 状态，通过后才展示
2. **不支持公开联系方式**：评论 API 不暴露用户真实联系方式
3. **匿名优先**：评论者使用 `anonymous_id`，不暴露真实身份
4. **可追究但不可骚扰**：记录 `user_id` 供 Admin 追溯，但不开放给普通用户
5. **发布者控制**：礼物发布者可隐藏/关闭评论

---

## 2. 数据表草案

以下为逻辑设计，**不创建 migration**。详细字段说明：

```sql
-- comments 表
CREATE TABLE comments (
  id              TEXT PRIMARY KEY,       -- UUID v4
  gift_id         TEXT NOT NULL,          -- FK → gifts.id
  user_id         TEXT NOT NULL,          -- FK → users.id（评论发布者）
  body_original   TEXT NOT NULL,          -- 原始内容（仅供 Admin 人工复审，不公开）
  body_redacted   TEXT NOT NULL,          -- 脱敏内容（Admin 查看用）
  status          TEXT NOT NULL DEFAULT 'pending_review',
                                       -- pending_review/approved/rejected/hidden
  risk_level      TEXT,                   -- safe/caution/high_risk/blocked
  is_owner_reply  INTEGER NOT NULL DEFAULT 0,  -- 发布者回复标记（不受每人1条限制）
  created_at      TEXT NOT NULL,          -- ISO 8601
  updated_at      TEXT NOT NULL
);

-- comment_review_logs 表
CREATE TABLE comment_review_logs (
  id              TEXT PRIMARY KEY,
  comment_id      TEXT NOT NULL,          -- FK → comments.id
  reviewer_type   TEXT NOT NULL,           -- system_static/ai_moderation/human_admin
  risk_level      TEXT,
  issues_json     TEXT,                    -- ["identity_phone", "harassment"]
  suggestions_json TEXT,                   -- ["建议移除手机号"]
  redaction_summary TEXT,
  reviewer_user_id TEXT,                   -- 仅 human_admin 时填写
  created_at      TEXT NOT NULL
);

-- comment_reports 表
CREATE TABLE comment_reports (
  id              TEXT PRIMARY KEY,
  comment_id      TEXT NOT NULL,          -- FK → comments.id
  reporter_user_id TEXT NOT NULL,          -- FK → users.id
  reason          TEXT NOT NULL,            -- harassment/identity_leak/threat/spam/other
  detail          TEXT,
  status          TEXT NOT NULL DEFAULT 'pending',  -- pending/reviewed/dismissed
  created_at      TEXT NOT NULL
);
```

---

## 3. API 端点设计

### 3.1 提交评论
```
POST /api/gifts/{gift_id}/comments
  Header: Authorization: Bearer {token}
  Body:
    {
      "content": "这件礼物很美，希望能找到下一站。"
    }
  Response (201):
    {
      "id": "uuid",
      "status": "pending_review",
      "created_at": "2026-05-16T22:00:00Z"
    }

  错误响应（422）：
    {
      "error": "评论内容不能为空",
      "code": "EMPTY_CONTENT"
    }

  错误响应（403）：礼物评论已关闭
    {
      "error": "此礼物已关闭评论功能",
      "code": "COMMENTS_DISABLED"
    }
```

**注意**：
- 评论内容长度限制：5~500 字符
- 每位用户对同一件礼物最多 1 条评论（`is_owner_reply=1` 的发布者回复不受限制）
- 提交后直接进入审核流程，不立即展示

### 3.2 获取评论列表
```
GET /api/gifts/{gift_id}/comments
  Query:
    - page: int (default 1)
    - limit: int (default 20, max 100)
  Response (200):
    {
      "items": [
        {
          "id": "uuid",
          "user_id": "anon-uuid",
          "body_redacted": "这件礼物很美...",  -- 脱敏后内容
          "status": "approved",
          "is_owner_reply": false,
          "created_at": "2026-05-16T22:00:00Z"
        }
      ],
      "total": N,
      "page": 1,
      "limit": 20,
      "has_more": true/false
    }

  说明：
    - 仅返回 `status=approved` 的评论
    - `body_original` 不返回（防止泄露）
    - `user_id` 仅对礼物发布者暴露（可看到自己礼物下的评论者 ID）
```

### 3.3 获取我的评论（用户个人中心）
```
GET /api/me/comments
  Query:
    - page: int (default 1)
    - limit: int (default 20)
  Response (200):
    {
      "items": [
        {
          "id": "uuid",
          "gift_id": "gift-uuid",
          "gift_name": "一只旧手表",
          "body_redacted": "...",
          "status": "approved",
          "created_at": "..."
        }
      ],
      "total": N,
      "page": 1,
      "limit": 20
    }

  说明：
    - 用户只能看到自己发布的评论
    - status=pending_review 的评论也返回，供用户查看审核状态
```

### 3.4 隐藏评论（礼物发布者）
```
POST /api/gifts/{gift_id}/comments/{comment_id}/hide
  Header: Authorization: Bearer {token}
  Response (200):
    {
      "id": "uuid",
      "status": "hidden"
    }

  错误响应（403）：
    {
      "error": "只有礼物发布者可以隐藏评论",
      "code": "NOT_GIFT_OWNER"
    }
```

### 3.5 举报评论
```
POST /api/comments/{comment_id}/report
  Header: Authorization: Bearer {token}
  Body:
    {
      "reason": "harassment",    -- harassment/identity_leak/threat/spam/other
      "detail": "这条评论一直在骚扰我"  -- 可选，最多 200 字
    }
  Response (201):
    {
      "id": "uuid",
      "status": "pending",
      "created_at": "..."
    }

  说明：
    - 举报后该评论立即提高审核优先级
    - 同一用户对同一评论只能举报 1 次
```

### 3.6 Admin：获取待审评论队列
```
GET /api/admin/comments
  Header: Authorization: Bearer {admin_token}
  Query:
    - status: pending_review/high_risk/flagged (default: pending_review)
    - page: int (default 1)
    - limit: int (default 50)
  Response (200):
    {
      "items": [
        {
          "id": "uuid",
          "gift_id": "gift-uuid",
          "gift_title": "一只旧手表",
          "user_id": "anon-uuid",
          "body_redacted": "...",
          "body_original": "..?",  -- 仅 Admin 可见原始内容
          "status": "pending_review",
          "risk_level": "high_risk",
          "report_count": 2,
          "created_at": "..."
        }
      ],
      "total": N,
      "page": 1
    }
```

### 3.7 Admin：审核评论
```
POST /api/admin/comments/{comment_id}/decision
  Header: Authorization: Bearer {admin_token}
  Body:
    {
      "decision": "approve",    -- approve/reject/flag
      "internal_note": "内容正常，同意展示",  -- 可选，仅内部记录
      "risk_override": false    -- 可选，Admin 是否覆盖 AI 风险判断
    }
  Response (200):
    {
      "id": "uuid",
      "status": "approved",
      "reviewed_at": "..."
    }

  说明：
    - decision=approve：评论状态变为 approved，展示
    - decision=reject：评论状态变为 rejected，静默（不通知评论者）
    - decision=flag：维持 pending_review，标记为需重点关注
```

### 3.8 Admin：删除评论
```
DELETE /api/admin/comments/{comment_id}
  Header: Authorization: Bearer {admin_token}
  Body（可选）:
    {
      "reason": "identity_leak",
      "internal_note": "评论包含手机号，已脱敏处理后删除"
    }
  Response (204): No Content

  说明：
    - 静默删除，不通知评论者
    - 写入 comment_review_logs
```

---

## 4. 评论状态流转

```
用户提交
    ↓
pending_review
    │
    ├── system_static 检测 → 无风险 → AI moderation
    │                              ↓
    │                         risk_level = safe
    │                              ↓
    │                         → approved（自动通过）
    │
    ├── AI moderation → risk_level = caution
    │                        ↓
    │                   → approved（限流展示）
    │
    ├── AI moderation → risk_level = high_risk
    │                        ↓
    │                   → 保持 pending_review，进入人工复审
    │                        ↓
    │                   Admin 审核
    │                   ├── approve → approved
    │                   └── reject → rejected（静默）
    │
    └── system_static 检测 → 风险词命中
                        ↓
                   → blocked → rejected（静默）
```

---

## 5. 评论频率限制

| 维度 | 限制 |
|------|------|
| 每用户每礼物评论数 | 1 条（发布者回复不受限） |
| 每用户每小时总评论数 | 10 条 |
| 每用户每分钟评论提交频率 | 2 条/分钟 |
| 每 IP 每小时评论数 | 20 条（防刷） |

---

## 6. 敏感信息检测规则

### 静态正则规则（第一道过滤）
```python
IDENTITY_PATTERNS = [
    r'\d{11}',              # 手机号
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # 邮箱
    r'微[信号]',           # 微信/微信号
    r'QQ[:：\s]?\d+',      # QQ号
    r'1[3-9]\d{9}',        # 常见手机号格式
    r'省.*市.*区.*路',     # 模糊地址
    r'[A-Z]{2}[0-9]{5,}',  # 车牌
]
```

### AI Moderation 第二道检测
- 语境分析：讽刺、反讽、暗示
- 情绪分析：攻击性、勒索性
- 意图分析：线下邀约、交易绕行

---

## 7. 本文档状态

- **Phase**：3A-0（设计评审）
- **实现状态**：❌ 不实现，仅文档
- **下一步**：Phase 3A-1（评论数据模型 migration + 基础 CRUD）

---

*本文档为设计评审文档，不构成产品承诺。评论 API 需经完整安全评审后方可实施。*