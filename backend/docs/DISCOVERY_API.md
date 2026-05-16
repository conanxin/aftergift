# Discovery API — Phase 2I-1 + Phase 2I-2

## 概述

Phase 2I-1 为 Aftergift 后端新增两个非个性化内容推荐端点，Phase 2I-2 修复了一致性和稳定性问题：

- `GET /api/gifts/discovery` — 首页发现轨道（Discovery Rails）
- `GET /api/gifts/{gift_id}/similar` — 详情页相似故事

**设计原则**：零依赖、纯 SQLite、explainable、无追踪、非个性化。

---

## Discovery Rails

### `GET /api/gifts/discovery`

**参数：**

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `rail` | string | `"all"` | 轨道名：`latest` / `popular` / `gentle` / `all` |
| `limit` | int | `6` | 每轨道返回数量，范围 1–20 |

**轨道说明：**

| rail | 排序规则 | 语义 |
|---|---|---|
| `latest` | `created_at DESC` | 最新发布的故事 |
| `popular` | `favorite_count DESC, created_at DESC` | 被收藏最多的故事 |
| `gentle` | `risk_level IN ('safe','caution')` + fallback to `created_at DESC` | 温和、低风险故事；空时回退到 latest |
| `all` | — | 返回前三轨的合并结果 |

**响应（单轨，rail=latest/popular/gentle）：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "rail": "latest",
    "items": [
      {
        "id": "gift-001",
        "title": "星空投影灯",
        "category": "家居装饰",
        "relation_type": "前任",
        "action_type": "sell",
        "emotion": "放下",
        "excerpt": "...",
        "price_or_exchange": "￥280",
        "status": "published",
        "is_anonymous": true,
        "anonymous_nickname": "安静的旧物收藏者 #4827",
        "created_at": "2026-05-16 07:28:20",
        "city_blur": "上海",
        "favorite_count": 3
      }
    ],
    "fallback_used": false,
    "meta": {
      "strategy": "non_personalized",
      "tracking": false
    }
  }
}
```

**响应（rail=all）：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "rail": "all",
    "rails": {
      "latest": [...],
      "popular": [...],
      "gentle": {"items": [...], "fallback_used": false}
    },
    "meta": {
      "strategy": "non_personalized",
      "tracking": false,
      "description": "无个性化追踪，基于公开礼物数据排序"
    }
  }
}
```

**Phase 2I-2 新增字段：**

- `fallback_used: bool` — gentle 轨道在无 safe/caution 数据时是否回退到 latest
- `meta: { strategy, tracking }` — 声明非个性化推荐策略
- `rails.gentle` 结构变更：正常时为数组；触发 fallback 时为 `{"items": [...], "fallback_used": true}`

---

## Similar Stories

### `GET /api/gifts/{gift_id}/similar`

返回与指定礼物相似的故事列表。

**参数：**

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `gift_id` | string | 必填 | 目标礼物 ID |
| `limit` | int | `4` | 返回数量，范围 1–12 |

**相似度策略：**

| 匹配字段 | 权重 | 匹配标签 |
|---|---|---|
| `emotion` | +3 | "相同情绪" |
| `relation_type` | +2 | "相同关系类型" |
| `action_type` | +1 | "相同处理方式" |
| `category` | +1 | "相同礼物类型" |

仅返回 score > 0 的候选，按 `(score DESC, created_at DESC, id ASC)` 排序。

**响应：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "base_gift_id": "gift-001",
    "strategy": "emotion_relation_action_similarity",
    "items": [
      {
        "id": "gift-007",
        "title": "...",
        "similarity_score": 5,
        "matched_reasons": ["相同情绪", "相同关系类型"],
        "matched_reason": "相同情绪、相同关系类型",
        "favorite_count": 2
      }
    ]
  }
}
```

> `matched_reasons`: 数组格式（推荐）；`matched_reason`: 字符串格式（向后兼容）。

---

## favorite_count 一致性（Phase 2I-2）

| 端点 | favorite_count |
|---|---|
| `GET /api/gifts`（列表） | ✅ JOIN favorites 子查询 |
| `GET /api/gifts/discovery` | ✅ JOIN favorites 子查询 |
| `GET /api/gifts/{id}/similar` | ✅ JOIN favorites 子查询 |
| `GET /api/gifts/{id}`（详情） | ✅ JOIN favorites 子查询（Phase 2I-2 修复）|

> 修复前：详情端 favorite_count 固定返回 0
> 修复后：详情端 JOIN favorites 表，返回真实收藏数，无收藏时返回 0（非 null）

---

## Static API Fallback（前端）

前端双模式适配器 `api-client.js`：

- **API 模式**（`?api=local`）：调用真实 FastAPI 端点
- **Static 模式**（默认）：读取 `frontend/data/gifts.json`，静默降级

**Phase 2I-2 修复：**

1. `getDiscoveryRails()` 在 static 模式下使用 `window.__AF_STATIC_DATA` 作为数据源
2. `getSimilarGifts()` 在 static 模式下使用 `window.__AF_STATIC_DATA` 作为数据源
3. `getSimilarStories` 导出为 `getSimilarGifts` 的别名，解决前端调用不匹配问题

**API 模式失败时：** 前端静默捕获异常，不阻塞页面加载，仅在控制台输出警告。

---

## 当前限制

1. **非个性化** — 所有用户看到相同内容，无协同过滤
2. **无浏览追踪** — 不记录用户点击历史
3. **SQLite 排序基础** — `popular` rail 依赖 `favorite_count`，无实时热点权重衰减
4. **不引入向量库** — 相似度完全基于规则标签匹配
5. **未启用真实 OpenAI API** — 全部使用 `mock_review`
6. **gentle rail 依赖 risk_level** — 若 gift_stories 表无 risk_level 字段，全部回退到 latest

---

## 路由顺序

```
@router.get("")                        # list_gifts
@router.get("/discovery")              # discovery  ← 在 /{gift_id} 之前
@router.get("/{gift_id}/similar")      # similar_gifts  ← 在 /{gift_id} 之前
@router.get("/{gift_id}")              # get_gift
@router.post("")                       # create_gift
```

> **注意**：FastAPI/Starlette 按路由注册顺序匹配。静态路径必须放在 `{path_param}` 路径之前，否则会被变量路径错误捕获（如 `/discovery` 被 `/{gift_id}` 捕获导致 404）。