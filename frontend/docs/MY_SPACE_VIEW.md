# MY_SPACE_VIEW — Phase 2L-2

## 目标

为已登录用户（API 模式）提供一个私有的"我的空间"聚合视图，聚合其身份状态、发布统计、收藏、操作历史和本地草稿。

**重要约束**：这不是公开用户主页（`/user/{anonymous_id}`），不暴露用户发布的礼物聚合页给他人访问。仅当前登录浏览器可见。

## URL 路由

```
?view=me   → 进入我的空间（需登录）
```

- `enterMySpaceView()` / `exitMySpaceView()` 管理视图切换
- `checkUrlView()` 检测 `?view=me` 并自动进入
- 刷新后保持 `?view=me`（URL 参数由 `enterMySpaceView` 设置）
- `exitMySpaceView` 时清除 `view` 参数，恢复首页

## 视图切换

```javascript
currentView = 'my_space';
document.body.classList.add('my-space-active');
// CSS 隐藏 hero / stories / filter-bar / publish / concept / ethics / roadmap / footer
```

返回时移除 class，切回 `currentView = 'home'` 并重新 `loadGifts()`。

## 我的空间入口

- Hero 区域新增「我的空间」按钮（`#heroMySpaceBtn`）
- **API 模式 + 已登录**：显示按钮
- **API 模式 + 未登录**：隐藏按钮
- **Static 模式**：隐藏按钮（本地模式无身份信息）

```javascript
window.updateHeroMySpaceButton(); // DOMContentLoaded 时调用
// bindDevAuthEvents 中创建身份后 / 清除身份后同步调用
```

## 内容布局

### 1. 身份状态卡片

```
GET /api/auth/me  (window.AftergiftAPI.getCurrentUser(token))
```

显示：
- `anonymous_nickname`（匿名昵称）
- `user_id`（身份 ID，隐藏后缀）
- token 状态：绿点「身份有效」/ 红点「无效」

底部提示：**这个身份只保存在当前浏览器，不会上传至服务器。**

### 2. 数据统计卡片（4 格）

| 卡片 | 数据来源 |
|------|---------|
| 已发布 | `GET /api/gifts?mine=true&limit=1` → `total` |
| 待审核 | `GET /api/gifts?mine=true&action_type=pending&limit=1` → `total` |
| 我的收藏 | `GET /api/gifts?favorites_of=me&limit=1` → `total` |
| 本地草稿 | `localStorage` 扫描 `aftergift_edit_draft_*` → count |

统计数字在 `loadMySpaceData` 的 `Promise.allSettled` 中并行获取（6 个 API 调用同时发出，结果独立渲染，失败不影响其他区块）。

### 3. 我的发布（内嵌前 3 条）

```
GET /api/gifts?mine=true&limit=3
```

每条显示：发布图标 + 礼物名称 + 状态标签（已发布/待审核/需修改/已归档）+ 操作类型 + 创建日期

点击整行 → `openDetail(giftId)`

「查看全部」按钮 → `exitMySpaceView()` + 触发 `.filter-tab[data-filter="mine"]` 点击

### 4. 操作历史（最近 5 条）

```
GET /api/me/actions?limit=5
```

每条显示：操作图标（edit/resubmit/archive/restore/publish）+ 礼物名称 + 操作类型 + 时间

支持操作类型映射：
- `edit` → 编辑故事
- `resubmit` → 重新提交
- `archive` → 暂时收起
- `restore` → 恢复审核
- `publish` → 发布故事
- `delete` → 删除

### 5. 本地草稿（无详情）

扫描 `localStorage` 中所有 `aftergift_edit_draft_*` key，仅显示数量，不展示草稿正文。

提示：**草稿只保存在这台设备上。**

## Static 模式降级

| 模块 | Static 模式行为 |
|------|----------------|
| 身份状态 | 显示"本地模式 · 不支持匿名身份" + 说明文案 |
| 已发布 / 待审核 | 显示 `–` |
| 我的收藏 | 从 `localStorage.aftergift_favorites` 读取计数 |
| 本地草稿 | 扫描 `localStorage.aftergift_edit_draft_*` |
| 操作历史 | 显示"本地模式暂不支持" |

## 当前限制

1. **不是公开主页**：无 `/user/{anonymous_id}` 路由，他人无法访问该用户的内容聚合页
2. **无数据持久化**：我的空间数据全部来自 API 实时查询，无本地缓存
3. **无操作撤回**：操作历史仅展示，不可点击撤回
4. **无草稿恢复**：本地草稿只计数，不支持预览或恢复编辑

## 相关文件

- `frontend/index.html` — `#mySpaceView` 区块 + `#heroMySpaceBtn` 按钮
- `frontend/style.css` — `.my-space-*` CSS 类 + `body.my-space-active` 隐藏规则
- `frontend/app.js` — `enterMySpaceView/exitMySpaceView/loadMySpace/renderMySpace*` 系列函数
- `frontend/api-client.js` — `getCurrentUser`（已存在）

## 历史
- Phase 2L-2（本文档）：新增我的空间视图（身份状态 + 统计卡片 + 发布列表 + 操作历史 + 草稿计数）
- Phase 2L-2.1：Promise.allSettled 替代串行 Promise 链，消灭 `window._ms_*` 竞态；Static 模式身份文案改为"本地模式 · 不支持匿名身份"；每个数据区块独立失败处理