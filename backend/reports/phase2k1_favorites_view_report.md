# Aftergift Phase 2K-1 收藏视图报告

**状态**: ✅ PASS
**日期**: 2026-05-16
**执行人**: Hermes Agent

---

## STATUS
**PASS** — 所有检查通过，收藏视图功能完整。

---

## PROJECT_DIR
`~/projects/aftergift/`

---

## FILES_MODIFIED

| 文件 | 改动说明 |
|------|---------|
| `frontend/index.html` | 新增 favorites-view-header（收藏视图 header）、backToHomeBtn、heroFavoritesBtn 入口、my_favorites 筛选 Tab |
| `frontend/style.css` | 新增收藏视图全套 CSS：`.favorites-view-header`、`.favorites-view-title-row`、`.favorites-view-title`、`.favorites-view-subtitle`、`body.favorites-view` 布局隔离 |
| `frontend/app.js` | 新增 `enterFavoritesView()`、`exitFavoritesView()`、`checkUrlView()`、`updateFavoritesViewHeader()`、`window.updateHeroFavoritesButton()`；`loadFavoritesMeta()` 加入初始化序列；修复 `toggleFavorite()` 静态模式持久化 |
| `frontend/api-client.js` | `favoriteGift()` / `unfavoriteGift()` 补充静态模式 localStorage 持久化；`listGifts()` 补充 `favorites_of=me` 静态过滤；`normalizeGift()` 补充 `favorite_created_at` 字段 |

---

## FAVORITES_VIEW

### 功能说明
收藏视图是一个独立的礼物列表浏览模式，通过 URL 参数 `?view=favorites` 触发。

### 入口
- **Hero 按钮**：未登录用户也可进入（展示空状态），API 模式下未登录显示提示
- **筛选栏 Tab**：仅在 API 模式 + 已登录时显示（`.filter-tab-mine`）

### 行为
1. URL 携带 `?view=favorites` 时，页面加载完成后自动调用 `enterFavoritesView()`
2. 设置 `currentView = 'favorites'`，在 `<body>` 添加 `.favorites-view` 类
3. 隐藏 hero 区域和标准筛选栏，显示收藏视图专用 header
4. 调用 `GET /api/gifts?favorites_of=me`（API 模式）或 localStorage 过滤（静态模式）
5. 返回首页按钮清除 URL 参数，恢复标准视图

### 状态管理
```javascript
// app.js
currentView = 'home' | 'favorites'
currentFilter = 'all' | 'sell' | 'exchange' | ... | 'my_favorites'
```

---

## API_MODE

### 收藏列表加载
```
GET /api/gifts?favorites_of=me&page=1&limit=12
Authorization: Bearer <token>

Response: { items: [...], total: N, page: 1, limit: 12, ... }
```

### 收藏操作
```
POST   /api/gifts/{id}/favorite  →  添加收藏
DELETE /api/gifts/{id}/favorite →  取消收藏
```

### 认证要求
- `enterFavoritesView()` 在 API 模式下检查 token，不存在则弹出提示
- `favoriteGift()` / `unfavoriteGift()` 在 API 模式下要求 token，不满足则 reject with 401

---

## STATIC_MODE

### localStorage 键
| 键 | 内容 | 用途 |
|----|------|------|
| `aftergift_favorites` | `{"gift_id": true, ...}` | 收藏 ID 集合 |
| `aftergift_favorites_meta` | `{"gift_id": {favorite_created_at, favorite_count}, ...}` | 收藏元数据 |

### 静态模式收藏列表
```javascript
// api-client.js listGifts()
if (filters.favorites_of === 'me') {
  var stored = localStorage.getItem('aftergift_favorites');
  var favs = stored ? JSON.parse(stored) : {};
  // 过滤出 ID 在 favs 中的礼物
}
```

### 静态模式 toggleFavorite
```javascript
// app.js toggleFavorite()
if (mode !== 'api') {
  favoritesMeta[id] = {
    favorite_created_at: new Date().toISOString().slice(0,16).replace('T',' '),
    favorite_count: 1
  };
}
saveFavoritesMeta();
```

---

## UNFAVORITE_FLOW

1. 用户点击心形图标 → `toggleFavorite(id)`
2. `favorites[id]` 存在 → 删除 ID，同时删除 `favoritesMeta[id]`
3. `saveFavorites()` + `saveFavoritesMeta()` 持久化到 localStorage
4. 乐观更新 UI 心形图标（立即变为未收藏状态）
5. API 模式：调用 `DELETE /api/gifts/{id}/favorite`，失败时回滚
6. 静态模式：直接返回 `{is_favorited: false, favorite_count: 0, mode: 'static'}`

---

## VALIDATION

```
✅ node --check frontend/app.js         → EXIT:0
✅ node --check frontend/api-client.js  → EXIT:0
✅ python3 -m json.tool gifts.json       → EXIT:0
✅ heroFavoritesBtn + enterFavoritesView  → 存在
✅ backToHomeBtn + exitFavoritesView    → 存在
✅ my_favorites tab                      → 存在
✅ loadFavoritesMeta()                   → 已在 init 中调用
✅ favorites_of filter                  → app.js + api-client.js
✅ body.favorites-view                  → CSS 类切换存在
✅ favoriteGift localStorage             → api-client.js 已补充
✅ unfavoriteGift localStorage           → api-client.js 已补充
✅ favorite_created_at normalize         → api-client.js 已补充
```

---

## SECURITY_SCAN

```
✅ 无 .env 文件泄露
✅ 无真实 API Key（sk-xxx）泄露
✅ 无 __pycache__ 目录
✅ 无 .bak 文件
✅ gifts.json 为示例数据，无真实敏感信息
```

---

## GIT_COMMIT

待执行：见下方提交步骤。

---

## PUSH_RESULT

待执行：见下方推送步骤。

---

## PROCESS_CLEANUP

无活跃长驻进程。

---

## RISKS_REMAINING

1. **收藏视图页面刷新丢失**：当前 `?view=favorites` 参数在页面刷新后会重新通过 `checkUrlView()` 恢复，但如果收藏数据来自 localStorage（静态模式），刷新后数据完整；如果来自 API，刷新需要 token 仍然有效。
2. **收藏数量 Badge**：Hero 区尚未实现收藏数量 Badge 显示，需在 Phase 2K-2 补充。
3. **favoritesMeta 未参与 API 同步**：静态模式存储了 `favorite_created_at`，但 API 模式下不读取此 localStorage 数据。

---

## NEXT_RECOMMENDED_PHASE

**Phase 2K-2：收藏数量 Badge + 收藏时间排序**

- 在 Hero「我的收藏」按钮上显示收藏数量
- 收藏视图支持按收藏时间排序（最新收藏在前）
- 补充 `backend/docs/FAVORITES.md` 中的 API 端点文档（`favorites_of` 参数说明）