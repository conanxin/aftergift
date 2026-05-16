# Aftergift 社区功能准备文档
**Phase 2L-1 | Community Readiness**
**Date**: 2026-05-16

---

## 1. Phase 2L-1 目标

本阶段**不实现**评论、私信、交易功能。只做前端收藏体验优化（收藏时间标签、收藏成功引导文案、Modal 静默提示），并为后续 Phase 3A 社区功能建立安全边界文档。

---

## 2. 为什么暂不实现评论 / 私信

Aftergift 处理的是**关系结束后**的礼物——这个场景天然伴随着：
- 情绪敏感的双方（刚分手、离婚、朋友疏远）
- 潜在的报复冲动（晒截图、挂人）
- 人肉搜索风险（通过礼物信息反推身份）

一旦开放自由评论或私信，平台极有可能变成：
1. **曝光区**：用礼物故事、图片、描述来挂人
2. **骚扰工具**：前任/伴侣通过私信继续骚扰
3. **情绪勒索**：用评论施压要求归还礼物

因此，社区功能必须**后置**，在有完整的审核机制和匿名保护之后才能开放。

---

## 3. 后续社区功能的安全边界

### 3.1 评论（如果实现）

**必须满足**：
- 所有评论必须经过审核才能展示（先审后发，或先发后审但可快速撤回）
- 评论不得包含：真实姓名、手机号、地址、公司、社交账号
- 评论不得使用侮辱、威胁、报复语言
- 每人每件礼物限评论 1 次（防止刷屏）
- 礼物主人可以隐藏评论（但不能删除）
- 系统可以静默删除违规评论，不通知评论者（避免激怒报复）

**推荐方案**：
- **温和评论**（先发后审）：允许用户评论，但全部进入审核队列，通过后才展示
- **模板化开场白**（推荐）：
  - "我想了解这件礼物的下一站"
  - "我愿意交换一个相似的小物"
  - "谢谢你写下这个故事"
  - "这件礼物对你意味着什么？"
- **禁止自由文本评论**，至少初期如此

### 3.2 私信（如果实现）

**必须满足**：
- 私信必须通过**匿名中继**：发送方和接收方互相不知道对方真实身份
- 禁止在私信中索要任何真实联系方式
- 平台提供**模板化开场白**，不开放自由文本：
  - "我想了解这件礼物的下一站"
  - "我愿意交换一个相似的小物"
  - "谢谢你写下这个故事"
- 用户可以**举报/屏蔽**发送者
- 平台可以**单方面封禁**违规用户，不提供申诉渠道
- 私信内容**不公开**，即使双方都同意也不公开

### 3.3 共同约束

- 不允许曝光他人姓名、照片、手机号、地址、公司、社交账号
- 不允许把他人真实身份作为卖点
- 不鼓励网暴或猎奇
- 鼓励匿名化叙述，聚焦物品本身和自己的感受
- "我们处理的是礼物，不是审判一个人。你可以讲述关系，但不要暴露他人。"

---

## 4. 未来 API 预留设计（仅文档，不实现）

### 4.1 评论 API

```
POST /api/gifts/{gift_id}/comments
  Header: Authorization: Bearer <token>
  Body: { "content": "...", "template_id": "want_to_know_next" }
  Response: { "comment_id": "...", "status": "pending_review" }

GET /api/gifts/{gift_id}/comments
  Query: ?status=approved&page=1&limit=20
  Response: { "items": [...], "total": N }
  Note: 只有 approved 状态的评论才返回

DELETE /api/comments/{comment_id}
  Header: Authorization: Bearer <token>
  Note: 仅评论者本人可删除，或管理员可删除
```

**评论状态流转**：
```
pending_review → approved → (hidden by owner) → deleted
               ↘ rejected → (通知评论者，重新提交)
```

### 4.2 私信 API

```
POST /api/conversations
  Header: Authorization: Bearer <token>
  Body: { "gift_id": "...", "template_id": "want_to_know_next", "message": "可选补充" }
  Response: { "conversation_id": "...", "status": "active" }
  Note: 不暴露接收者身份

GET /api/conversations
  Header: Authorization: Bearer <token>
  Response: { "items": [{ "conversation_id": ..., "gift_title": ..., "last_message": ..., "created_at": ... }] }

POST /api/conversations/{conversation_id}/messages
  Header: Authorization: Bearer <token>
  Body: { "template_id": "exchange_propose", "message": "可选补充" }
  Response: { "message_id": ..., "status": "sent" }

GET /api/conversations/{conversation_id}/messages
  Header: Authorization: Bearer <token>
  Response: { "items": [...], "total": N }
```

### 4.3 模板化开场白

```javascript
const MESSAGE_TEMPLATES = [
  { id: "want_to_know_next",      label: "我想了解这件礼物的下一站",  minVersion: "1.0" },
  { id: "exchange_propose",        label: "我愿意交换一个相似的小物",  minVersion: "1.0" },
  { id: "thank_you",               label: "谢谢你写下这个故事",       minVersion: "1.0" },
  { id: "story_question",          label: "这件礼物对你意味着什么？",  minVersion: "1.0" },
  { id: "custom",                  label: "自由补充（审核后发送）",   minVersion: "1.1" },
];
```

---

## 5. 风险分析

| 风险 | 严重程度 | 缓解措施 |
|------|---------|---------|
| 情绪勒索 | 高 | 匿名中继、模板化开场白、禁止自由私信 |
| 前任骚扰 | 高 | 用户可屏蔽、单方面封禁、禁止真实身份交换 |
| 人肉搜索 | 高 | 内容审核、禁止真实联系方式、故事脱敏 |
| 平台变成曝光区 | 高 | 严格审核、举报机制、隐私保护协议 |
| 评论骚扰 | 中 | 先审后发、每人每件限1条、主人可隐藏 |

---

## 6. Phase 3A 前置条件

在实现任何社区功能之前，必须满足：

1. **审核队列产品化**：有真实的审核后台（不只是管理脚本）
2. **匿名中继私信系统**：技术架构设计完成并评审
3. **用户屏蔽机制**：实现单方面屏蔽，拉黑后双方都不能再互动
4. **内容脱敏自动化**：用 NLP/正则扫描评论和私信中的敏感信息（电话、地址、社交账号）
5. **应急响应机制**：有快速处理举报的能力（目标：1小时内响应）
6. **法律/合规咨询**：确认平台对用户行为不承担连带责任

---

## 7. 当前 Phase 2L-1 完成内容

### 前端收藏体验优化
- 收藏时间标签：收藏视图卡片显示「收藏于 YYYY-MM-DD」
- API 模式使用 `favorite_created_at`，Static 模式使用 `localStorage favoritesMeta[id].favorite_created_at`
- 收藏成功 Toast：已改为「已收藏。稍后可在「我的收藏」中重新找到它。」
- 取消收藏 Toast：已改为「已从我的收藏移除。」
- Modal 静默提示：已收藏的礼物在 Modal 底部显示「这个故事已经被放进你的收藏。」

---

## 8. 下一步建议

- **Phase 2L-2**：用户主页 / 内容空间（展示用户发布的礼物故事，不暴露身份）
- **Phase 3A-0**：社区功能设计评审（评论政策、审核流程、API 草案、滥用预防） ✅ **当前完成**
- **Phase 3A-1**：评论审核引擎 + 数据模型（需用户确认后才开始）

---

## 9. Phase 3A-0 新增文档索引

Phase 3A-0 设计评审完成后，新增以下文档：

| 文档 | 内容 |
|------|------|
| `COMMENTS_POLICY.md` | 评论政策：允许/禁止/灰区内容、可见性规则、语气建议 |
| `COMMENT_REVIEW_WORKFLOW.md` | 评论审核工作流：风险等级、审核维度、与现有体系关系 |
| `COMMENTS_API_DESIGN.md` | 评论 API 设计草案：端点、数据表（不创建 migration）、状态流转 |
| `ANONYMOUS_MESSAGING_DESIGN_REVIEW.md` | 匿名私信设计评审：模板化中继方案、禁止模板、安全机制 |
| `ABUSE_PREVENTION.md` | 滥用预防与威胁模型：8种威胁、7层防护、敏感信息类型 |
| `PHASE3A_PLAN.md` | Phase 3A 实施计划：3A-1 至 3A-6 各子阶段说明 |

---

*本文档仅作为技术设计参考，不构成产品承诺。所有功能需经安全评审后方可实施。*