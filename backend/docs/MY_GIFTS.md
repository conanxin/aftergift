# Aftergift Phase 2G-2 — 我的发布 / 我的收藏

## 目标

让用户在 `?api=local` 模式下创建匿名身份后，可以查看：
- **我的发布**：自己发布的所有礼物（含待审核、需修改、已拒绝等状态）
- **我的收藏**：自己收藏的故事（仅已发布内容）

## API 接口

### GET /api/gifts?mine=true

**要求**：`Authorization: Bearer <token>`

**行为**：
- 返回当前用户发布的所有礼物
- 包含所有状态：`published`, `pending_review`, `needs_edit`, `rejected`, `draft`, `archived`
- 支持 `page`, `limit`, `sort`, `order`, `q` 参数
- 无 token → 401

**响应字段**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "gift-xxx",
        "title": "...",
        "status": "pending_review",
        "is_mine": true,
        "is_favorited": false
      }
    ],
    "total": 2,
    "page": 1,
    "limit": 12
  }
}
```

### GET /api/gifts?favorites_of=me

**要求**：`Authorization: Bearer <token>`

**行为**：
- 返回当前用户收藏的礼物
- 仅返回 `published` 状态
- 支持 `page`, `limit`, `q`, `emotion`, `action_type` 参数
- 无 token → 401

**响应字段**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "gift-xxx",
        "title": "...",
        "is_mine": false,
        "is_favorited": true,
        "favorite_created_at": "2024-01-15 08:30:00"
      }
    ]
  }
}
```

### 通用字段说明

| 字段 | 说明 |
|------|------|
| `is_mine` | 该礼物是否由当前用户发布 |
| `is_favorited` | 当前用户是否收藏了该礼物 |
| `favorite_created_at` | 收藏时间（仅 `favorites_of=me` 时返回） |
| `status` | 礼物状态（mine=true 时包含非 published） |

## 前端适配

### Static 模式
- 隐藏"我的发布"和"我的收藏"筛选标签
- "已收藏"标签继续使用 localStorage 本地筛选

### API 模式
- 显示"我的发布"和"我的收藏"筛选标签
- 未登录时点击 → Toast："请先创建匿名身份，再查看你的..."
- 已登录时调用对应 API

## 当前限制

1. 仅支持 `?api=local` 模式（本地开发）
2. 不支持评论、私信、交易
3. 收藏仅在 API 模式下持久化到后端数据库
4. Static 模式下收藏仍使用 localStorage，不与后端同步

## 后续建议

- **Phase 2G-3**：基础内容推荐 / 热门故事
- **Phase 2H**：个人内容管理增强（编辑、删除、重新提交）
