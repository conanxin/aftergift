# 收藏功能（Aftergift Favorites API）

## 概览

Phase 2J-1 实现。礼物收藏功能，支持幂等 POST/DELETE，提供 `is_favorited` 和 `favorite_count` 字段，为后续"收藏故事"功能奠定基础。

---

## 端点

### POST /api/gifts/{gift_id}/favorite

收藏一件礼物。

**需要认证**：Bearer token（无 token → 401）

**状态过滤**：以下状态不允许收藏 → 422
- `archived`
- `rejected`
- `pending_review`
- `needs_edit`
- `draft`

**幂等语义**：
- 首次收藏：HTTP 201，返回 `favorite_id`
- 重复收藏：HTTP 200，`is_favorited=true`，`favorite_count` 不变

**响应**：
```json
{
  "code": 201,
  "message": "已收藏这个故事",
  "data": {
    "favorite_id": "fav-c83955e1",
    "gift_id": "gift-001",
    "is_favorited": true,
    "favorite_count": 1
  }
}
```

---

### DELETE /api/gifts/{gift_id}/favorite

取消收藏。

**需要认证**：Bearer token（无 token → 401）

**幂等语义**：
- 首次取消：HTTP 200
- 重复取消（从未收藏）：HTTP 200，`is_favorited=false`，`favorite_count: 0`

**响应**：
```json
{
  "code": 200,
  "message": "已取消收藏",
  "data": {
    "gift_id": "gift-001",
    "is_favorited": false,
    "favorite_count": 0
  }
}
```

---

## 字段说明

| 字段 | 来源 | 说明 |
|------|------|------|
| `is_favorited` | favorites 表 JOIN | 当前用户是否收藏了该礼物（需 Bearer token） |
| `favorite_count` | favorites COUNT | 该礼物的收藏总数 |
| `favorite_id` | favorites 表 | 仅在首次 POST 时返回 |

---

## 前端集成（API 模式）

**api-client.js**：
- `favoriteGift(giftId)` — POST，返回 `{is_favorited, favorite_count}`
- `unfavoriteGift(giftId)` — DELETE，返回 `{is_favorited: false, favorite_count}`
- 无 token 时 reject `{status: 401, message: '请先创建匿名身份，再收藏这个故事。'}`

**app.js**：
- `toggleFavorite(giftId)` — 乐观更新模式
  - 记录操作前状态
  - 即时更新图标
  - 调用 API
  - 成功则同步服务端状态，失败则回滚 + Toast 提示
  - 401 提示"请先创建匿名身份，再收藏这个故事"
  - 其他错误提示"收藏操作失败了"

---

## 前端集成（Static 模式）

在 static 模式下，收藏状态存储在本地 `localStorage`：
- `aftergift_favorites` — `Set<giftId>` 的 JSON 序列化
- API 调用被静默忽略，不弹 Toast

---

## favorites_of=me

`GET /api/gifts?favorites_of=me` 返回当前用户收藏的所有礼物。

---

## 已知限制

- 不支持收藏夹/文件夹分组
- 不支持收藏夹变更通知（暂无 push 通知）
- 匿名身份可收藏，但无法取回（除非保留 localStorage 中的 token）
- 同一浏览器多 tab 共享 `localStorage`，状态一致

---

## 数据库表

```sql
CREATE TABLE favorites (
    id        TEXT PRIMARY KEY,
    user_id   TEXT NOT NULL,
    gift_id   TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, gift_id)
);
```