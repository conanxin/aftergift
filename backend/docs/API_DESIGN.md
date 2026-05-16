# REST API 设计

> Aftergift Phase 2 后端 MVP | 版本：1.0

---

## 1. 概览

**Base URL**：`/api/v1`

**认证方式**：Bearer Token（Phase 2C 实现，目前先不设计）

**返回格式**：所有响应为 JSON
```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

**错误格式**：
```json
{
  "code": 400,
  "message": "错误描述",
  "data": null
}
```

---

## 2. API 列表

### 2.1 GET /api/health

**用途**：健康检查

**权限**：公开

**响应**：
```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "version": "2.0.0-alpha",
    "status": "running"
  }
}
```

---

### 2.2 GET /api/gifts

**用途**：获取公开礼物列表（支持搜索、筛选、分页、排序）

**权限**：公开

**Query 参数**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| q | string | null | 关键词搜索（标题 + 故事全文） |
| action_type | string | null | 筛选：sell/exchange/giveaway/donate/keep |
| emotion | string | null | 筛选情绪标签 |
| relation_type | string | null | 筛选关系类型 |
| city_blur | string | null | 筛选城市模糊 |
| mine | boolean | false | **Phase 2G-2** 仅返回当前用户发布的礼物（需 Bearer Token）|
| favorites_of | string | null | **Phase 2G-2** 筛选收藏：`me`=当前用户（需 Bearer Token）|
| page | integer | 1 | 页码 |
| limit | integer | 12 | 每页数量（上限 50）|
| sort | string | created_at | 排序字段（白名单：created_at/updated_at/title/price_or_exchange）|
| order | string | desc | 排序方向：asc 或 desc |

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [...],
    "total": 42,
    "page": 1,
    "limit": 12,
    "total_pages": 4,
    "has_more": true,
    "filters": {
      "q": "灯",
      "emotion": null,
      "action_type": null,
      "relation_type": null,
      "city_blur": null,
      "sort": "created_at",
      "order": "desc"
    }
  }
}
```

**安全说明**：
- `sort` / `order` 参数通过白名单校验，非法值返回 400
- 仅返回 `status='published'` 的内容
- 搜索摘要自动移除 HTML 标签，防止 XSS

**风险说明**：
- 不返回 full_story（完整故事），完整故事在 GET /api/gifts/{id} 中获取
- 不返回 user_id（发布者真实身份）
- 不返回 IP 或设备信息

---

### 2.3 GET /api/gifts/{id}

**用途**：获取礼物详情

**权限**：公开（published 故事）或所有者（自己发布的草稿/审核中故事）

**路径参数**：
- `id`：礼物 UUID

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "gift-uuid-001",
    "title": "星空投影灯",
    "category": "家居装饰",
    "relation_label": "前任",
    "action_type": "sell",
    "action_label": "出售",
    "emotion": "放下",
    "price_or_exchange": "￥280",
    "condition_note": "九成新，配件齐全",
    "city_blur": "上海",
    "is_anonymous": true,
    "anonymous_nickname": "安静的旧物收藏者 #4827",
    "status": "published",
    "story": {
      "short_story": "在一起三年，分手后每次看到它都会想起那段时间……",
      "full_story": "（600-2000 字完整故事）",
      "risk_level": "safe",
      "quality_score": 0.82,
      "created_at": "2026-04-15 12:00:00"
    },
    "created_at": "2026-04-15 12:00:00",
    "updated_at": "2026-04-15 12:00:00"
  }
}
```

**错误响应**（404）：
```json
{
  "code": 404,
  "message": "礼物不存在或暂不可查看",
  "data": null
}
```

**风险说明**：
- full_story 包含用户故事，需确认 risk_level <= caution 才展示
- 高风险故事（high_risk）不向普通用户展示详情

---

### 2.4 POST /api/gifts

**用途**：发布新礼物故事

**权限**：需要用户身份（手机号 HASH 登录，或匿名发布）

**请求体**：
```json
{
  "title": "星空投影灯",
  "category": "家居装饰",
  "relation_type": "前任",
  "action_type": "sell",
  "emotion": "放下",
  "price_or_exchange": "￥280",
  "condition_note": "九成新，配件齐全",
  "city_blur": "上海",
  "is_anonymous": true,
  "short_story": "在一起三年，分手后每次看到它都会想起那段时间……",
  "full_story": "（600-2000 字完整故事）"
}
```

**字段说明**：
| 字段 | 必填 | 说明 |
|------|------|------|
| title | ✅ | 礼物名称，1-50 字 |
| category | ✅ | 类型 |
| action_type | ✅ | 处理方式 |
| emotion | ✅ | 情绪标签 |
| short_story | ✅ | 一句话故事，1-100 字 |
| full_story | ✅ | 完整故事，10-2000 字 |
| relation_type | ○ | 关系类型，可空 |
| price_or_exchange | ○ | 价格或交换意向 |
| condition_note | ○ | 物品状态备注 |
| city_blur | ○ | 城市（仅城市名）|
| is_anonymous | ○ | 默认 true |

**响应**：
```json
{
  "code": 201,
  "message": "礼物已提交，正在审核中",
  "data": {
    "gift_id": "gift-uuid-002",
    "status": "pending_review",
    "estimated_review_time": "24小时内"
  }
}
```

**审核流程**：
1. 服务端接收 → 规则预检（同步）
2. AI 审核（异步，2-3 秒）
3. 风险分级
4. 高风险 → 人工复审队列

---

### 2.5 POST /api/gifts/{id}/favorite

**用途**：收藏礼物

**权限**：需要登录（手机号 HASH）

**路径参数**：
- `id`：礼物 UUID

**响应**：
```json
{
  "code": 200,
  "message": "已收藏这个故事",
  "data": {
    "favorite_id": "fav-uuid-001",
    "gift_id": "gift-uuid-001"
  }
}
```

**错误**（已收藏）：
```json
{
  "code": 409,
  "message": "已经收藏过了",
  "data": null
}
```

---

### 2.6 DELETE /api/gifts/{id}/favorite

**用途**：取消收藏

**权限**：需要登录

**路径参数**：
- `id`：礼物 UUID

**响应**：
```json
{
  "code": 200,
  "message": "已取消收藏",
  "data": null
}
```

---

### 2.7 POST /api/gifts/{id}/report

**用途**：举报礼物

**权限**：公开（无需登录）

**请求体**：
```json
{
  "reason": "曝光隐私",
  "detail": "故事中提到了他的真实姓名和公司名称"
}
```

**reason 可选值**：
- `privacy`（曝光隐私）
- `attack`（攻击性内容）
- `fake`（虚假信息）
- `other`（其他）

**响应**：
```json
{
  "code": 201,
  "message": "感谢你的反馈，我们会尽快处理",
  "data": {
    "report_id": "rep-uuid-001",
    "status": "pending"
  }
}
```

**风险说明**：
- 不记录 reporter_ip 明文，只存 HASH
- 恶意举报（同一 IP 大量举报）触发防刷机制

---

### 2.8 GET /api/admin/reviews

**用途**：管理员获取审核队列

**权限**：仅管理员

**Query 参数**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| risk_level | string | null | 筛选：caution/high_risk |
| status | string | pending_review | 筛选状态 |
| page | integer | 1 | 页码 |

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "gift_id": "gift-uuid-003",
        "title": "毛绒熊",
        "short_story": "生日那天她送的……",
        "risk_level": "caution",
        "identity_risk": 1,
        "attack_risk": 0,
        "identifiable_person_risk": 2,
        "suggestions": [...],
        "submitted_at": "2026-04-15 14:00:00",
        "ai_review_notes": "故事中有部分可识别信息，建议人工复审"
      }
    ],
    "total": 5,
    "page": 1
  }
}
```

---

### 2.9 POST /api/admin/reviews/{gift_id}/decision

**用途**：管理员对故事做出审核决定

**权限**：仅管理员

**请求体**：
```json
{
  "decision": "approve",
  "note": "人工复审通过，匿名化处理后可以发布"
}
```

**decision 可选值**：
- `approve`：通过，直接发布
- `reject`：拒绝，通知用户
- `needs_edit`：需要用户修改

**响应**：
```json
{
  "code": 200,
  "message": "审核决定已记录",
  "data": {
    "gift_id": "gift-uuid-003",
    "new_status": "published",
    "decided_at": "2026-04-15 15:30:00"
  }
}
```

**风险说明**：
- 所有管理员操作记录到 admin_actions 表
- 管理员操作不可删除，不可修改

---

## 3. 未来 API（Phase 3+）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/users/me | 获取当前用户信息 |
| GET | /api/users/me/favorites | 获取当前用户收藏列表 |
| DELETE | /api/gifts/{id} | 删除自己的故事 |
| GET | /api/admin/reports | 管理员查看举报列表 |
| PATCH | /api/admin/reports/{id} | 管理员处理举报 |
| POST | /api/gifts/{id}/messages | 发送匿名私信（Phase 5）|

---

## 附录：Phase 2H-1 我的发布管理接口

> 当前路径基于 `gifts.py` router prefix `/api/gifts`，因此实际路径为 `/api/gifts/me/gifts/{id}`。后续如需改为 `/api/me/gifts/{id}`，另开兼容迁移阶段。

### A.1 GET /api/gifts/me/gifts/{gift_id}

**用途**：获取当前用户自己的礼物详情（含完整故事和审核备注）

**权限**：Bearer Token（只能查看自己的礼物，非自己 → 404）

**响应字段**：包含 `id`, `title`, `category`, `relation_type`, `action_type`, `emotion`, `price_or_exchange`, `condition_note`, `city_blur`, `is_anonymous`, `status`, `story`, `created_at`, `updated_at`, `review_note`

### A.2 PATCH /api/gifts/me/gifts/{gift_id}

**用途**：编辑自己的礼物

**权限**：Bearer Token

**可编辑字段**：`title`, `category`, `relation_type`, `relation_label`, `action_type`, `emotion`, `price_or_exchange`, `condition_note`, `city_blur`, `is_anonymous`, `short_story`, `full_story`

**状态规则**：仅 `draft` / `pending_review` / `needs_edit` 可编辑；`published` / `rejected` / `archived` → 409

**审核复跑**：编辑 `short_story` 或 `full_story` 后自动重新运行 mock/OpenAI 审核，写入 `review_logs`，suggestions/evidence 仍脱敏

### A.3 POST /api/gifts/me/gifts/{gift_id}/resubmit

**用途**：重新提交礼物审核

**权限**：Bearer Token

**状态规则**：仅 `draft` / `needs_edit` 可重新提交

**行为**：重新运行审核，状态变为 `pending_review`（保守策略）

### A.4 POST /api/gifts/me/gifts/{gift_id}/archive

**用途**：撤回（归档）自己的礼物

**权限**：Bearer Token

**状态规则**：`published` / `pending_review` / `needs_edit` 可归档

**行为**：状态变为 `archived`，普通 `GET /api/gifts` 不再返回，`mine=true` 仍可看到

**审计**：写入 `admin_actions`，`admin_id="self:<user_id>"`，note 记录用户自行归档（MVP 临时方案）

---

*最后更新：Phase 2H-1 完成时更新。*