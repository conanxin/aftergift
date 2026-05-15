# Phase 2C 集成报告：前端对接 FastAPI 本地 SQLite MVP

**Aftergift Backend MVP**
**Date:** 2026-05-15
**Status:** ✅ PASS

---

## 1. STATUS
**PASS** — 前端已实现 static/api 双模式，FastAPI 后端所有端点联调验证通过，Pages 草稿已同步并提交。

---

## 2. HOST_SCOPE
- **前端服务：** `http://127.0.0.1:8080`（仅本地 loopback）
- **后端服务：** `http://127.0.0.1:8091`（仅本地 loopback）
- **Pages 草稿：** `https://conanxin.github.io/drafts/aftergift-prototype/`（noindex，非索引）

---

## 3. PROJECT_DIR
- **前端项目：** `~/projects/aftergift-prototype/`
- **后端项目：** `~/projects/aftergift-backend-mvp/`
- **Pages 草稿：** `~/conanxin.github.io/drafts/aftergift-prototype/`

---

## 4. FILES_MODIFIED

### 前端项目（Phase 2C 新增/修改）

| 文件 | 操作 | 说明 |
|------|------|------|
| `api-client.js` | **新增** | 双模式 API 适配器：normalizeGift、listGifts、getGift、createGift、reviewStory、favoriteGift、unfavoriteGift、reportGift |
| `index.html` | 修改 | 增加内联模式检测脚本 `<script>window.__AF_MODE</script>`、引入 api-client.js、footer 模式提示元素 |
| `app.js` | 修改 | loadGifts 支持 API 模式、handleFormSubmit 支持 API 发布、toggleFavorite 支持 API 收藏/取消、handleModalAction 支持 API 举报、runAIReview 支持 API 审核、handleFilterClick 支持 API 筛选 |
| `docs/API_INTEGRATION.md` | **新增** | 完整 API 联调指南：模式说明、字段映射、fallback 策略、端点一览 |
| `README.md` | 修改 | 增加 Phase 2C 本地联调章节、文件结构更新 |

### Pages 草稿同步

| 同步内容 | 说明 |
|---------|------|
| `index.html` | 保持 noindex，新增 mode 检测脚本 |
| `app.js` | 同步双模式逻辑 |
| `api-client.js` | 同步 API 适配器 |
| `README.md` | 同步更新 |
| `docs/API_INTEGRATION.md` | 同步新增文档 |

### 后端项目（无修改）

无新修改。所有后端端点 Phase 2B.1/2B.2 均已验证通过。

---

## 5. API_MODE_DESIGN

### 模式切换机制

```
URL 参数 ?api        → api 模式（调用 FastAPI）
无参数              → static 模式（读 data/gifts.json）
window.AFTERGIFT_CONFIG.mode 可覆盖（高级用法）
```

**核心原则：GitHub Pages 永不主动调用 localhost API。**

### API 适配器设计（api-client.js）

```javascript
window.AftergiftAPI = {
  MODE,         // 'static' | 'api'
  API_BASE,     // 'http://127.0.0.1:8091'
  listGifts,    // GET /api/gifts（支持 action_type/emotion 筛选）
  getGift,      // GET /api/gifts/{id}
  createGift,    // POST /api/gifts
  reviewStory,   // POST /api/review/mock
  favoriteGift,  // POST /api/gifts/{id}/favorite
  unfavoriteGift,// DELETE /api/gifts/{id}/favorite
  reportGift,    // POST /api/gifts/{id}/report
  checkHealth,   // GET /api/health
  normalizeGift, // 字段映射函数
}
```

### 字段 normalize 策略

- 后端 `title` → 前端 `name`
- 后端 `category` → 前端 `type`
- 后端 `action_type` → 前端 `action`
- 后端 `relation_label` → 前端 `relationLabel`
- 后端 `price_or_exchange` → 前端 `price`
- 后端 `is_anonymous` → 前端 `anonymous`
- 后端 `story.full_story` → 前端 `fullStory`

---

## 6. FIELD_MAPPING

### 列表数据（GET /api/gifts → gift card）

| 后端字段 | 前端字段 | 备注 |
|---------|---------|------|
| id | id | 直接透传 |
| title | name | normalize |
| category | type | normalize |
| relation_type | relation | normalize |
| relation_label | relationLabel | normalize |
| action_type | action | normalize |
| action_label | actionLabel | 直接透传 |
| emotion | emotion | 直接透传 |
| short_story | excerpt | normalize |
| price_or_exchange | price | normalize |
| status | status | 直接透传 |
| is_anonymous | anonymous | normalize |
| anonymous_nickname | anonymous_nickname | 附加字段 |

### POST /api/gifts（表单 → 后端）

| 前端字段 | 后端字段 | 备注 |
|---------|---------|------|
| name | title | normalize |
| type | category | normalize |
| relation | relation_type | normalize |
| action | action_type | normalize |
| emotion | emotion | 直接透传 |
| excerpt | short_story | normalize |
| fullStory | full_story | normalize |
| price | price_or_exchange | normalize |
| anonymous | is_anonymous | normalize |

---

## 7. FRONTEND_INTEGRATION

### loadGifts（静态/动态双路径）

```
loadGifts()
  → window.__AF_MODE === 'api'
    → AftergiftAPI.listGifts() → gifts = result.items
    → catch: fallback → loadStaticGifts()
  → else
    → loadStaticGifts() → fetch('./data/gifts.json')
```

### handleFormSubmit（发布表单）

```
static 模式：本地 unshift 到 gifts[]，前端临时卡片
api 模式：AftergiftAPI.createGift() → DB 持久化
          → 成功后更新 newGift.id
          → 失败：仍本地添加，显示警告 Toast
```

### toggleFavorite（收藏）

```
static 模式：localStorage
api 模式：POST/DELETE /api/gifts/{id}/favorite（异步，失败静默）
```

### handleModalAction:report（举报）

```
static 模式：显示 Toast（本地演示）
api 模式：POST /api/gifts/{id}/report → 显示确认 Toast
```

### runAIReview（故事审核）

```
static 模式：前端正则规则引擎（Phase 1D 逻辑）
api 模式：POST /api/review/mock → renderAPIReview()
          → 失败 fallback：runLocalReview()
```

### handleFilterClick（筛选）

```
static 模式：前端数组 filter
api 模式：AftergiftAPI.listGifts({action_type}) → 重渲染
```

---

## 8. BACKEND_FIXES

**无。** 后端 Phase 2B.1/2B.2 全部通过，本次联调未发现新的 API 兼容问题。

---

## 9. LOCAL_INTEGRATION_TEST

### 后端 API 测试

| 测试项 | 方法 | URL | 结果 |
|--------|------|-----|------|
| health | GET | `/api/health` | ✅ 200 |
| gifts list | GET | `/api/gifts` | ✅ 200（2 items） |
| gifts detail | GET | `/api/gifts/gift-001` | ✅ 200 |
| review mock safe | POST | `/api/review/mock` | ✅ 200（risk=safe, issues=0） |
| create gift | POST | `/api/gifts` | ✅ 201（gift-3039cb86, published） |
| create caution gift | POST | `/api/gifts` | ✅ 201（pending_review） |
| create high_risk | POST | `/api/gifts` | ✅ 201（gift-8d8fd7de, pending_review） |
| favorite POST | POST | `/api/gifts/gift-001/favorite` | ✅ 201 |
| favorite DELETE | DELETE | `/api/gifts/gift-001/favorite` | ✅ 200 |
| report | POST | `/api/gifts/gift-001/report` | ✅ 201 |
| admin reviews | GET | `/api/admin/reviews`（正确token） | ✅ 200（1 item） |
| admin reviews (no token) | GET | `/api/admin/reviews` | ✅ 401 |
| admin reviews (wrong token) | GET | `/api/admin/reviews` | ✅ 403 |

### 前端静态服务测试

| 测试项 | 结果 |
|--------|------|
| static 模式首页 | ✅ HTTP 200 |
| api 模式首页 | ✅ HTTP 200 |
| api-client.js 可访问 | ✅ HTTP 200 |

### 语法检查

```
✅ node --check app.js
✅ node --check api-client.js
✅ python3 -c json.load(gifts.json) → 14 items
```

---

## 10. PAGES_SYNC

**状态：** ✅ 已同步并提交

```
pages repo draft 目录内容：
  drafts/aftergift-prototype/
  ├── index.html          [M] +noindex +mode detection script
  ├── style.css           [未修改]
  ├── app.js              [M] +api mode support
  ├── api-client.js       [A] 双模式适配器
  ├── README.md           [M] +Phase 2C 说明
  ├── data/
  │   └── gifts.json      [未修改]
  └── docs/
      ├── *.md            [未修改]
      └── API_INTEGRATION.md [A] 联调指南
```

**noindex 标签：** ✅ Pages 草稿 `index.html` 包含 `<meta name="robots" content="noindex, nofollow">`

---

## 11. GIT_COMMIT

```
[main 2f2912c] Add Aftergift Phase 2C local API integration mode
 5 files changed, 824 insertions(+), 9 deletions(-)
 create mode 100644 drafts/aftergift-prototype/api-client.js
 create mode 100644 drafts/aftergift-prototype/docs/API_INTEGRATION.md
```

---

## 12. PROCESS_CLEANUP

| 进程 | 状态 |
|------|------|
| uvicorn (PID ~4074180) | ✅ 已终止（fuser -k 8091/tcp） |
| http.server (PID ~4074251) | ✅ 已终止（fuser -k 8080/tcp） |
| 端口 8091 | ✅ CLEAR |
| 端口 8080 | ✅ CLEAR |

---

## 13. RISKS_REMAINING

| 风险 | 级别 | 说明 |
|------|------|------|
| 无用户认证 | 高 | 所有操作使用 dev-user-001，Phase 2C+ 需 JWT |
| admin token 明文 | 中 | dev-admin-aftergift-001 仅本地开发用 |
| API 发布后刷新消失 | 低 | 前端内存 vs DB 持久化，Phase 2C+ 需刷新后重新 fetch |
| CORS 仅限 localhost | 低 | 生产需配置真实域名白名单 |
| 本地收藏状态不同步 | 低 | localStorage vs DB favorites 可能短暂不一致 |

---

## 14. NEXT_RECOMMENDED_PHASE

**Phase 2D：正式用户认证 + 真实 AI 审核**

Phase 2C 核心目标达成：前端可接 FastAPI，线上静态 Demo 不坏。

下一步建议方向（按优先级）：

1. **用户认证层**：JWT / OAuth2 接入，替换 dev-user-001
2. **真实 AI 审核**：Phase 2D 将 `AFTERGIFT_ENABLE_REAL_AI_REVIEW=true` 对接真实 Moderation API
3. **分页/滚动加载**：前端列表从全量改为分页滚动
4. **发布后数据持久化**：API 模式发布后，刷新页面不丢失（需对接用户认证）

---

## 附录：Phase 2 完整记录

| 阶段 | 日期 | 状态 | 关键交付 |
|------|------|------|---------|
| Phase 1 | 2026-05-14 | ✅ PASS | 静态前端原型 |
| Phase 2A | 2026-05-14 | ✅ PASS | schema + mock API + tests |
| Phase 2B.1 | 2026-05-15 | ✅ PASS | FastAPI runtime + 9 bugs fixed |
| Phase 2B.2 | 2026-05-15 | ✅ PASS | 代码卫生清理 |
| Phase 2C | 2026-05-15 | ✅ PASS | 前端对接 FastAPI + 双模式 + 联调验证 |
