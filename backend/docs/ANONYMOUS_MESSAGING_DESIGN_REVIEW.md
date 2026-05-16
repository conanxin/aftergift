# 匿名私信设计评审文档
**Phase 3A-0 | Anonymous Messaging Design Review**
**本文档：设计评审阶段，不实现私信 API**

---

## 1. 为什么私信风险更高

相比评论，私信有更高的滥用风险，原因如下：

### 1.1 一对一私密性
- 没有社区监督（不像评论有其他用户可见）
- 没有公开举报机制
- 骚扰难以被第三方发现

### 1.2 关系不对等风险
Aftergift 用户场景天然包含：
- 前任骚扰（前伴侣通过私信继续施压）
- 情感勒索（以复合为由要求归还礼物）
- 跟踪风险（通过私信获取更多信息后线下跟踪）

### 1.3 交易纠纷
- 私信中绕过平台进行私下交易
- 交易后否认、欺诈

### 1.4 真实身份交换
- 私信中交换微信、电话、地址
- 导致匿名身份名存实亡

### 1.5 线下邀约
- 通过私信获取信息后约线下见面
- 安全风险

---

## 2. 直接开放自由私信的问题

直接开放一对一自由文本私信（类似微信/邮件）将使 Aftergift 面临：

| 风险 | 后果 |
|------|------|
| 前任骚扰 | 分手后继续通过私信施压，平台成为骚扰工具 |
| 情感勒索 | "如果不还礼物我就公开你的照片" |
| 人肉搜索 | 通过私信交换信息后确定对方身份 |
| 线下跟踪 | 约线下见面后发生人身安全问题 |
| 交易绕行 | 私信中谈好私下交易，平台无法监控 |

---

## 3. 推荐方案：模板化匿名中继

Aftergift 不建议开放自由私信，采用**模板化匿名中继**模式：

### 3.1 核心设计原则

1. **双方匿名**：发送方和接收方互不知道对方真实身份
2. **模板化**：仅允许选择预设开场白，不支持自由文本（或仅支持极短补充）
3. **中继**：消息通过平台转发，双方不直接获取对方联系方式
4. **可追溯**：Admin 可看到消息内容（用于安全审核，不向普通用户暴露）
5. **可阻断**：接收方可随时屏蔽，单方面终止对话

---

## 4. 允许的开场模板

以下模板可视为安全选项（需配合审核机制）：

| 模板 ID | 中文文案 | 英文说明 |
|--------|---------|---------|
| `want_to_know_next` | "我想了解这件礼物的下一站。" | Ask about the gift's next destination |
| `exchange_propose` | "我愿意交换一个相似的小物。" | Propose an exchange |
| `thank_story` | "谢谢你写下这个故事。" | Thank the storyteller |
| `giveaway_interest` | "这件礼物还在吗？我想免费带走它。" | Express interest in the gift |
| `curious_story` | "这个故事对我很有启发。" | Share how the story impacted them |

每条消息最多额外补充 50 字（需通过审核才能发送）。

---

## 5. 禁止的模板选项

以下内容不允许作为私信开场或补充：

| 类型 | 示例 |
|------|------|
| 身份追问 | "你是谁？" / "你叫什么？" / "你住哪里？" |
| 联系方式索要 | "你的微信是什么？" / "能留个电话吗？" / "加个好友？" |
| 关系审判 | "你和 TA 后来怎样了？" / "你前任现在在哪？" |
| 线下邀约 | "我们见面聊" / "约个地方见" / "你在哪个城市？" |
| 情感勒索 | "如果你不回复我就…" / "你欠我的" |
| 威胁 | "我知道你在哪" / "你等着" |
| 交易绕行 | "我们私下交易，不走平台" |

---

## 6. 安全机制

### 6.1 双方同意机制
私信对话需双方确认才能继续：

```
用户 A 发送私信给礼物发布者 B
    ↓
B 收到通知，可选择：
    ├── 接受 → 对话激活，双方可继续交流
    ├── 拒绝 → B 不会收到 A 的任何后续消息，A 也不会知道 B 拒绝了
    └── 举报 → B 可直接举报 A，平台介入
```

### 6.2 频率限制
| 维度 | 限制 |
|------|------|
| 每用户每小时发起对话数 | 3 条 |
| 每对话每用户每分钟消息数 | 1 条 |
| 每用户每分钟消息总数 | 3 条 |

### 6.3 一键屏蔽
- 接收方可随时屏蔽对方，无需说明原因
- 屏蔽后对方消息不再送达
- 屏蔽记录进入 Admin 审计日志

### 6.4 举报入口
- 每条消息均有举报入口
- 举报时需选择理由（骚扰/身份泄露/威胁/交易绕行/其他）
- 举报后该对话进入 Admin 优先复审队列

### 6.5 不允许联系方式
- 私信内容通过 AI + 静态规则审核
- 检测到联系方式立即拒绝发送
- 多次尝试发送联系方式可触发临时封禁

### 6.6 AI / 规则审核每条消息
- 每条发出的消息都经过审核
- 支持手动配置审核严格度（普通模式 / 严格模式）
- 拒绝的消息不告知发送者真实原因（防止试探）

### 6.7 管理员复审高风险消息
以下情况触发人工复审：
- 同一对话中连续 3 条消息被 AI 标记为 caution
- 消息中包含线下邀约相关关键词
- 被举报的消息

---

## 7. 私信状态流转

```
用户 A 发起对话（选择模板）
    ↓
pending（等待 B 接受）
    ↓
B 选择接受/拒绝
    ├── 拒绝 → 对话结束，A 不会收到任何通知
    └── 接受 → 对话激活
                   ↓
             双方可发消息（每条经过审核）
                   │
                   ├─ 正常交流 → 对话结束（任意一方屏蔽）
                   │
                   ├─ A 违规 → A 被临时封禁，对话挂起
                   │
                   ├─ B 举报 → 对话进入复审队列
                   │
                   └─ 双方 7 天无互动 → 对话自动归档
```

---

## 8. 私信数据表草案

以下为逻辑设计，**不创建 migration**：

```sql
-- conversations 表
CREATE TABLE conversations (
  id              TEXT PRIMARY KEY,
  gift_id         TEXT NOT NULL,          -- 关联的礼物
  initiator_id    TEXT NOT NULL,          -- 发起者 user_id
  receiver_id     TEXT NOT NULL,          -- 接收者 user_id
  status          TEXT NOT NULL DEFAULT 'pending',  -- pending/active/blocked/rejected/archived
  blocker_id      TEXT,                   -- 最后屏蔽者 user_id（如果有）
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);

-- messages 表
CREATE TABLE messages (
  id              TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  sender_id       TEXT NOT NULL,
  template_id     TEXT NOT NULL,           -- 使用的模板 ID
  extra_text      TEXT,                    -- 额外补充文字（50字限制）
  body_redacted   TEXT NOT NULL,           -- 脱敏后内容（Admin 查看）
  status          TEXT NOT NULL DEFAULT 'pending',  -- pending/sent/delivered/read
  risk_level      TEXT,                   -- AI 判断
  is_notified     INTEGER NOT NULL DEFAULT 0,  -- 是否已通知接收者
  created_at      TEXT NOT NULL
);

-- conversation_reports 表
CREATE TABLE conversation_reports (
  id              TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  reporter_id     TEXT NOT NULL,
  reason          TEXT NOT NULL,            -- harassment/identity_leak/threat/spam/other
  detail          TEXT,
  status          TEXT NOT NULL DEFAULT 'pending',
  created_at      TEXT NOT NULL
);

-- conversation_blocks 表
CREATE TABLE conversation_blocks (
  id              TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  blocker_id      TEXT NOT NULL,           -- 屏蔽者
  blocked_user_id TEXT NOT NULL,           -- 被屏蔽者
  created_at      TEXT NOT NULL
);
```

---

## 9. 私信 API 草案

**仅设计，不实现**：

```
POST /api/conversations
  Header: Authorization: Bearer {token}
  Body:
    {
      "gift_id": "...",
      "template_id": "want_to_know_next",
      "extra_text": "我对这本书也很感兴趣"  -- 可选，最多 50 字
    }
  Response (201):
    {
      "conversation_id": "...",
      "status": "pending",
      "message": "对方已收到你的消息，请等待接受。"
    }

GET /api/me/conversations
  Header: Authorization: Bearer {token}
  Response (200):
    {
      "items": [
        {
          "conversation_id": "...",
          "gift_id": "...",
          "gift_title": "一只旧手表",
          "other_party_nickname": "匿名用户",
          "last_message": "我想了解这件礼物的下一站。",
          "last_message_at": "...",
          "unread_count": 1,
          "status": "active"
        }
      ]
    }

GET /api/conversations/{id}/messages
  Header: Authorization: Bearer {token}
  Response (200):
    {
      "items": [
        {
          "id": "...",
          "template_id": "want_to_know_next",
          "extra_text": "我对这本书也很感兴趣",
          "is_mine": true,
          "status": "read",
          "created_at": "..."
        }
      ]
    }

POST /api/conversations/{id}/messages
  Header: Authorization: Bearer {token}
  Body:
    {
      "template_id": "exchange_propose",
      "extra_text": ""  -- 可选
    }
  Response (201):
    {
      "id": "...",
      "status": "pending"
    }

POST /api/conversations/{id}/accept
  Header: Authorization: Bearer {token}
  Response (200):
    {
      "conversation_id": "...",
      "status": "active"
    }

POST /api/conversations/{id}/reject
  Header: Authorization: Bearer {token}
  Response (200):
    {
      "conversation_id": "...",
      "status": "rejected"
    }

POST /api/conversations/{id}/block
  Header: Authorization: Bearer {token}
  Response (200):
    {
      "conversation_id": "...",
      "status": "blocked"
    }

POST /api/conversations/{id}/report
  Header: Authorization: Bearer {token}
  Body:
    {
      "reason": "harassment",
      "detail": "对方多次发送骚扰内容"
    }
  Response (201):
    {
      "id": "...",
      "status": "pending"
    }
```

---

## 10. 私信与评论的关系

| 维度 | 评论 | 私信 |
|------|------|------|
| 公开/私密 | 公开（通过审核后） | 私密（仅双方） |
| 审核 | 先审后发（全员） | 每条消息审核 |
| 模板化 | 可选（建议） | 必须（推荐） |
| 身份暴露风险 | 中（公开发布） | 高（一对一） |
| 可拒绝 | 发布者可隐藏 | 接收方可拒绝/屏蔽 |
| Admin 可追溯 | 是 | 是（但不向用户暴露） |

---

## 11. 本文档状态

- **Phase**：3A-0（设计评审）
- **实现状态**：❌ 不实现，仅评审文档
- **建议**：Phase 3A-1 至 Phase 3A-5 优先实现评论功能，私信延后至 Phase 3A-6（或更晚）
- **前提**：私信功能需在评论系统稳定运行至少 3 个月后再评估是否推进

---

*本文档为设计评审文档，不构成产品承诺。匿名私信功能需经完整安全评审后方可实施。*