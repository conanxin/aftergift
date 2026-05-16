# Discovery API — Phase 2I-1

## 概述

Phase 2I-1 为 Aftergift 后端新增两个非个性化内容推荐端点：

- `GET /api/gifts/discovery` — 首页发现轨道（Discovery Rails）
- `GET /api/gifts/{gift_id}/similar` — 详情页相似故事

**设计原则**：零依赖、纯 SQLite、explainable、无追踪。

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
| `gentle` | `risk_level IN ('safe','caution')` + `created_at DESC` | 温和、低风险故事 |
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
    ]
  }
}
```

**响应（rail=all）：**
```json
{
  "code": 200,
  "data": {
    "rail": "all",
    "rails": {
      "latest": [...],
      "popular": [...],
      "gentle": [...]
    }
  }
}
```

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

## 共同字段

### `favorite_count`

通过 `LEFT JOIN (SELECT gift_id, COUNT(*) FROM favorites GROUP BY gift_id)` 子查询注入到所有列表查询中。

- `list_gifts`: 是
- `discovery rails`: 是
- `similar_gifts`: 是
- `get_gift`: 固定返回 `0`（详情页暂无收藏数显示需求）

---

## Static API Fallback

当前端使用 `?api=local` 模式时，Discovery 数据来自 `frontend/data/gifts.json`，不支持 `rail` 参数筛选，仅展示全部已发布礼物。

---

## 当前限制

1. **非个性化** — 所有用户看到相同内容，无协同过滤
2. **无浏览追踪** — 不记录用户点击历史
3. **SQLite 排序基础** — `popular` rail 依赖 `favorite_count`，无实时热点权重衰减
4. **不引入向量库** — 相似度完全基于规则标签匹配
5. **未启用真实 OpenAI API** — 全部使用 `mock_review`

---

## 路由顺序

```
@router.get("")                        # list_gifts
@router.get("/discovery")                # discovery  ← 在 /{gift_id} 之前
@router.get("/{gift_id}/similar")        # similar_gifts  ← 在 /{gift_id} 之前
@router.get("/{gift_id}")               # get_gift
@router.post("")                        # create_gift
```

> **注意**：FastAPI/Starlette 按路由注册顺序匹配。静态路径必须放在 `{path_param}` 路径之前，否则会被变量路径错误捕获。