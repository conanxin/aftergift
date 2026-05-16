# 收藏视图（Phase 2K-1 + 2K-2）

**状态**: ✅ 已完成
**最后更新**: 2026-05-16（Phase 2K-2 更新）

---

## 概述

收藏视图是 Aftergift 前端的一个独立浏览模式，通过 URL 参数 `?view=favorites` 触发。它展示当前用户收藏的所有礼物故事，支持 API 模式和静态双模式。

**Phase 2K-2 更新**：新增收藏数量 Badge、按收藏时间倒序、auth 失败分级处理。

---

## 入口

### 1. Hero 按钮（主要入口）
```
位置: index.html hero-actions 区域
元素: #heroFavoritesBtn
行为: 点击 → enterFavoritesView()
显示条件:
  - 静态模式: 始终显示
  - API 模式: 已登录（token 存在）时显示
```

### 2. 筛选栏「我的收藏」Tab
```
位置: #filterTabsSection
元素: .filter-tab[data-filter="my_favorites"]
显示条件: API 模式 + 已登录
行为: 点击 → handleFilterClick('my_favorites')
注意: 此 Tab 在静态模式下不显示（因为收藏数据仅存在于 localStorage）
```

---

## URL 路由

```
?view=favorites        → 进入收藏视图
                       → DOMContentLoaded → checkUrlView() → enterFavoritesView()

页面刷新: checkUrlView() 在 init 中调用，可恢复收藏视图状态
```

---

## enterFavoritesView() 行为

```javascript
window.enterFavoritesView = function () {
  // 1. API 模式 auth gate
  if (mode === 'api' && !token) {
    showToast('请先创建匿名身份，再查看你的收藏。');
    return;
  }

  // 2. 设置状态
  currentView = 'favorites';
  document.body.classList.add('favorites-view');  // CSS 布局隔离

  // 3. 滚动到顶部
  window.scrollTo({ top: 0, behavior: 'smooth' });

  // 4. 设置筛选器
  currentFilter = 'my_favorites';
  displayedCount = INITIAL_DISPLAY;

  // 5. 加载数据
  if (mode === 'api') {
    // GET /api/gifts?favorites_of=me&page=1&limit=12
    AftergiftAPI.listGifts(params, []).then(render);
  } else {
    // 静态模式: AftergiftAPI.listGifts 使用 localStorage favorites_of 过滤
    if (window.__AF_STATIC_DATA) {
      AftergiftAPI.listGifts(params, __AF_STATIC_DATA).then(render);
    }
  }
};
```

---

## exitFavoritesView() 行为

```javascript
window.exitFavoritesView = function () {
  // 1. 恢复状态
  currentView = 'home';
  document.body.classList.remove('favorites-view');
  currentFilter = 'all';
  displayedCount = INITIAL_DISPLAY;

  // 2. 清除 URL 参数
  params.delete('view');
  history.replaceState({}, '', newUrl);

  // 3. 重新加载全部礼物
  loadGifts();

  // 4. 恢复「全部」Tab 高亮
  document.querySelectorAll('.filter-tab').forEach(t => {
    t.classList.remove('active');
    t.setAttribute('aria-selected', 'false');
  });
  document.querySelector('.filter-tab[data-filter="all"]')?.classList.add('active');
};
```

---

## 布局隔离（CSS）

`body.favorites-view` 类切换实现收藏视图与标准视图的布局隔离：

```css
/* index.html 主 hero 在收藏视图下隐藏 */
body.favorites-view .hero {
  display: none;
}

/* 标准筛选栏在收藏视图下隐藏 */
body.favorites-view #filterTabsSection {
  display: none;
}

/* 收藏视图专用 header */
.favorites-view-header {
  display: flex;   /* 默认隐藏，JS 设为 display:'' 显示 */
}
```

---

## 收藏视图 Header

```html
<div class="favorites-view-header" id="favoritesViewHeader" style="display:none">
  <div class="favorites-view-title-row">
    <div class="favorites-view-title">
      <svg heart icon/>
      <span>我的收藏</span>
    </div>
    <button id="backToHomeBtn" onclick="exitFavoritesView()">
      返回首页
    </button>
  </div>
  <p class="favorites-view-subtitle" id="favoritesViewSubtitle">
    已收藏 N 个故事
    <!-- 或: 你还没有收藏任何故事。也许下一件打动你的旧物，就在下面的故事里。 -->
  </p>
</div>
```

---

## API 模式数据流

```
enterFavoritesView()
  → AftergiftAPI.listGifts({ favorites_of: 'me', page: 1, limit: 12 }, [])
  → GET /api/gifts?favorites_of=me&page=1&limit=12
      Authorization: Bearer <token>
  → Response: { items: [...], total: N, page: 1, limit: 12, ... }
  → gifts = result.items
  → searchMeta = { total, page, limit, total_pages, has_more }
  → updateFavoritesViewHeader()
  → showModeIndicator('api', total)
  → renderGifts()
```

---

## 静态模式数据流

```
enterFavoritesView()
  → AftergiftAPI.listGifts(params, __AF_STATIC_DATA)
  → listGifts(filters, staticData)
      if (filters.favorites_of === 'me') {
        var stored = localStorage.getItem('aftergift_favorites');
        var favs = JSON.parse(stored);  // {"gift_id": true, ...}
        items = staticData.filter(g => favs[g.id]);
      }
  → { items: filtered, total, page, limit, total_pages, has_more }
  → updateFavoritesViewHeader()
  → renderGifts()
```

---

## favoriteGift / unfavoriteGift 静态模式

```javascript
// api-client.js favoriteGift()
if (MODE !== 'api') {
  var stored = localStorage.getItem('aftergift_favorites');
  var favs = stored ? JSON.parse(stored) : {};
  favs[id] = true;
  localStorage.setItem('aftergift_favorites', JSON.stringify(favs));
  return Promise.resolve({ is_favorited: true, favorite_count: 1, mode: 'static' });
}
```

```javascript
// api-client.js unfavoriteGift()
if (MODE !== 'api') {
  var stored = localStorage.getItem('aftergift_favorites');
  var favs = stored ? JSON.parse(stored) : {};
  delete favs[id];
  localStorage.setItem('aftergift_favorites', JSON.stringify(favs));
  return Promise.resolve({ is_favorited: false, favorite_count: 0, mode: 'static' });
}
```

---

## localStorage 结构

| 键 | 类型 | 说明 |
|----|------|------|
| `aftergift_favorites` | `Object` | `{ [giftId]: true, ... }` 收藏 ID 集合 |
| `aftergift_favorites_meta` | `Object` | `{ [giftId]: { favorite_created_at, favorite_count }, ... }` 收藏元数据 |

---

## 已知限制

1. **收藏视图刷新**: `?view=favorites` 参数在页面刷新后由 `checkUrlView()` 恢复，但如果 token 过期（API 模式），收藏列表会加载失败
2. **收藏数量 Badge**: Hero 收藏按钮上尚未显示未读/收藏数量，需 Phase 2K-2 补充
3. **多 tab 一致性**: 静态模式下多 tab 共享 localStorage，关闭一个 tab 不会影响其他 tab 的收藏状态

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `frontend/index.html` | favorites-view-header、heroFavoritesBtn、my_favorites Tab |
| `frontend/style.css` | `.favorites-view-header`、`.favorites-view-title-row`、`.favorites-view-subtitle`、`body.favorites-view` |
| `frontend/app.js` | `enterFavoritesView`、`exitFavoritesView`、`checkUrlView`、`updateFavoritesViewHeader` |
| `frontend/api-client.js` | `favoriteGift`/`unfavoriteGift` localStorage 持久化、`favorites_of` 过滤、`favorite_created_at` 字段 |
| `backend/docs/FAVORITES.md` | 后端收藏 API 设计文档 |

---

## Phase 2K-2 新增功能

### 收藏数量 Badge

Hero「我的收藏」按钮新增数字 Badge，位于按钮文字右侧：

```html
<button id="heroFavoritesBtn" onclick="enterFavoritesView()">
  <svg .../>
  <span id="heroFavoritesLabel">我的收藏</span>
  <span class="fav-badge" id="heroFavoritesBadge" style="display:none"></span>
</button>
```

**显示逻辑**：
- 有收藏（count > 0）：显示数字，最多 `99+`
- 无收藏或未登录：隐藏 badge

**API 模式**：`GET /api/gifts?favorites_of=me&limit=1`，取 `result.total` 作为收藏数

**Static 模式**：统计 `localStorage['aftergift_favorites']` 中 `true` 值数量

**触发时机**：初始化时 + 每次 `toggleFavorite` 成功/失败/静态分支后

**CSS 样式**：
```css
.fav-badge {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 18px; height: 18px; padding: 0 5px; border-radius: 9px;
  background: var(--primary); color: #fff;
  font-size: 11px; font-weight: 600; line-height: 1; vertical-align: middle;
  margin-left: 4px;
}
#heroFavoritesBtn .fav-badge {
  background: rgba(255,255,255,0.25); color: #fff; /* 适配深色按钮 */
}
```

### 按收藏时间倒序

**API 模式**：后端 `favorites_of=me` 查询按 `favorites.created_at DESC` 返回已排序结果。

**Static 模式**：`api-client.js` 的 `listGifts()` 在 `favorites_of=me` 时对结果排序：

```javascript
if (filters.favorites_of === 'me') {
  items.sort(function (a, b) {
    var aTime = a.favorite_created_at || a.created_at || '';
    // 静态模式：优先取 localStorage favoritesMeta 中的时间
    if (!aTime) { aTime = favoritesMeta[a.id]?.favorite_created_at || ''; }
    var bTime = b.favorite_created_at || b.created_at || '';
    if (!bTime) { bTime = favoritesMeta[b.id]?.favorite_created_at || ''; }
    if (!aTime && !bTime) return 0;
    if (!aTime) return 1;   // 缺少时间排最后
    if (!bTime) return -1;
    return bTime.localeCompare(aTime); // 倒序：最新收藏排最前
  });
}
```

### 统一 favorite meta 结构

`normalizeGift()` 保证以下三个字段始终存在：

```javascript
favorite_count:     g.favorite_count || 0
is_favorited:       !!(g.is_favorited || g.favorited)
favorite_created_at: g.favorite_created_at || g.created_at || null
```

### Auth 失败分级处理

`enterFavoritesView()` 的 `.catch()` 分层处理：

| 场景 | Toast 提示 | 行为 |
|------|-----------|------|
| 无 token | "请先创建匿名身份，再查看你的收藏。" | 不进入收藏视图 |
| 401/403（token 失效） | "身份已失效，请重新创建匿名身份。" | 显示温柔空状态 |
| 网络错误 | "无法加载收藏列表，请检查 API 连接" | 显示空状态 |

---

## Phase 2L-1 新增功能

### 收藏时间标签

收藏视图的每张卡片显示「收藏于 YYYY-MM-DD」：

```javascript
if (currentFilter === 'my_favorites' && g.favorite_created_at) {
  favTime = '<span class="gift-card-fav-time">收藏于 ' + escHtml(g.favorite_created_at) + '</span>';
}
```

- API 模式：`gift.favorite_created_at`（后端 favorites JOIN 返回）
- Static 模式：`localStorage favoritesMeta[id].favorite_created_at`
- 无 `favorite_created_at` 时不显示（稳定降级）

CSS 样式见 `style.css` `.gift-card-fav-time`。

### 收藏成功引导文案

`toggleFavorite` 成功后 Toast：

| 操作 | Toast 文案 |
|------|-----------|
| API 模式收藏成功 | "已收藏。稍后可在「我的收藏」中重新找到它。" |
| API 模式取消收藏 | "已从我的收藏移除。" |
| Static 模式收藏 | "已收藏。稍后可在「我的收藏」中重新找到它。" |

### Modal 静默提示

已收藏的礼物在 Modal 底部显示轻提示（不影响 action 按钮）：

```html
<div class="modal-fav-hint" aria-live="polite">这个故事已经被放进你的收藏。</div>
```

CSS 样式见 `style.css` `.modal-fav-hint`。

---

## 相关文件

**Phase 2K-2**: 收藏数量 Badge + 按收藏时间排序
**Phase 2L-1**: 收藏时间标签 + 引导文案 + Modal 静默提示