# 收藏视图（Phase 2K-1）

**状态**: ✅ 已完成
**最后更新**: 2026-05-16

---

## 概述

收藏视图是 Aftergift 前端的一个独立浏览模式，通过 URL 参数 `?view=favorites` 触发。它展示当前用户收藏的所有礼物故事，支持 API 模式和静态双模式。

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

## NEXT

**Phase 2K-2**: 收藏数量 Badge + 按收藏时间排序