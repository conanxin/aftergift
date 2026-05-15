# API Integration Guide — Aftergift Phase 2D

## 概述

Aftergift 前端支持三种运行模式：

| 模式 | 数据来源 | 触发方式 | 适用场景 |
|------|---------|---------|---------|
| **static**（默认） | `data/gifts.json` 本地静态文件 | 无需任何参数 | GitHub Pages 草稿、静态演示 |
| **api** | FastAPI 后端 `http://127.0.0.1:8091` | URL 带 `?api` 参数 | 本地前后端联调开发 |
| **admin** | 同 api + 审核面板 | URL 带 `?api&admin` 参数 | 本地管理员审核联调 |

**关键原则：线上 Demo 永不主动调用 localhost API。**

---

## 1. 如何启动后端

```bash
cd ~/projects/aftergift-backend-mvp/backend

# 初始化数据库（首次）
python scripts/init_db.py

# 激活虚拟环境
. .venv/bin/activate

# 启动 FastAPI（仅监听 127.0.0.1:8091，不暴露公网）
uvicorn app.main:app --host 127.0.0.1 --port 8091
```

**验证后端运行状态：**

```bash
curl http://127.0.0.1:8091/api/health
# → {"code":200,"message":"ok","data":{"version":"2.0.0-alpha","status":"running"}}
```

**验证 admin token（用于审核接口）：**

```bash
curl -H "x-admin-token: dev-admin-aftergift-001" http://127.0.0.1:8091/api/admin/reviews
```

---

## 2. 如何启动前端静态服务

```bash
cd ~/projects/aftergift-prototype
python3 -m http.server 8080
# → 在 http://localhost:8080 或 http://127.0.0.1:8080 打开
```

**⚠️ 不要用 `file://` 协议直接打开 HTML**，否则 `fetch('./data/gifts.json')` 会因 CORS 被浏览器拦截。

---

## 3. 如何进入联调模式（API Mode）

启动前后端后，在浏览器访问：

```
http://127.0.0.1:8080/?api
```

**或同时指定自定义 API 地址（通过全局配置）：**

```javascript
// 在浏览器控制台执行：
window.AFTERGIFT_CONFIG = { mode: 'api', apiBaseUrl: 'http://127.0.0.1:8091' };
location.reload();
```

**URL 参数优先级：** `?api` > `window.AFTERGIFT_CONFIG.mode` > 默认 `static`。

---

## 4. 模式检测机制

前端在 `index.html` 的 `<head>` 中通过内联 `<script>` 立即检测模式：

```html
<script>
  window.__AF_MODE = new URLSearchParams(location.search).has('api') ? 'api' : 'static';
  window.__AF_API_BASE = 'http://127.0.0.1:8091';
</script>
```

此 `window.__AF_MODE` 在所有 JS 模块加载前就绪，确保 `api-client.js` 和 `app.js` 能正确判断模式。

---

## 5. API Base URL

| 模式 | Base URL |
|------|---------|
| static（默认） | 不调用 API |
| api（本地联调） | `http://127.0.0.1:8091` |

可通过 `window.AFTERGIFT_CONFIG.apiBaseUrl` 覆盖。

---

## 6. 字段映射表

### 6.1 Gift List — API → 前端 Card

| 后端字段（GET /api/gifts） | 前端字段（gift card） | 说明 |
|---------------------------|---------------------|------|
| `id` | `id` | 礼物唯一 ID |
| `title` | `name` | 礼物名称 |
| `category` | `type` | 礼物类型 |
| `relation_type` | `relation` | 关系类型（代码值） |
| `relation_label` | `relationLabel` | 关系标签（中文） |
| `action_type` | `action` | 处理方式代码 |
| `action_label` | `actionLabel` | 处理方式中文 |
| `emotion` | `emotion` | 情绪标签 |
| `excerpt`（short_story） | `excerpt` | 故事摘录 |
| `price_or_exchange` | `price` | 价格或交换意向 |
| `status` | `status` | 流转状态 |
| `is_anonymous` | `anonymous` | 是否匿名 |
| `story.risk_level` | `risk_level` | 审核风险等级 |

### 6.2 Gift Detail — API → 前端 Modal

| 后端字段（GET /api/gifts/{id}） | 前端字段 | 说明 |
|-------------------------------|---------|------|
| `story.short_story` | `excerpt` | 摘录 |
| `story.full_story` | `fullStory` | 完整故事 |
| `story.risk_level` | `risk_level` | 风险等级 |
| `condition_note` | `condition_note` | 物品状态说明 |
| `city_blur` | `city_blur` | 模糊城市信息 |
| `anonymous_nickname` | `anonymous_nickname` | 匿名昵称 |

### 6.3 POST /api/gifts — 前端表单 → 后端请求体

| 前端表单字段 | 后端 GiftCreate 字段 | 说明 |
|------------|---------------------|------|
| `name` | `title` | 礼物名称 |
| `type` | `category` | 类型 |
| `relation` | `relation_type` | 关系 |
| `action` | `action_type` | 处理方式（enum） |
| `emotion` | `emotion` | 情绪 |
| `excerpt` | `short_story` | 故事摘录 |
| `fullStory` | `full_story` | 完整故事 |
| `price` | `price_or_exchange` | 价格/交换意向 |
| `anonymous` | `is_anonymous` | 是否匿名 |

---

## 7. API Fallback 策略

### 7.1 列表加载失败

```
AftergiftAPI.listGifts() 失败
  → 捕获异常
  → 显示 Toast："API 连接失败，已回退到示例数据"
  → 静默切换到 loadStaticGifts()
  → 页面正常展示 static JSON 数据
```

### 7.2 发布表单提交失败

```
AftergiftAPI.createGift() 失败
  → 仍然在本地 unshift newGift 到 gifts[]
  → 显示 Toast："礼物已发布（本地演示），API 提交失败"
  → 页面行为与 static 模式完全一致
```

### 7.3 收藏/举报 API 调用失败

```
AftergiftAPI.favorite/unfavorite/report() 失败
  → .catch(function () {}) 静默吞掉错误
  → 前端状态（localStorage/favorites）保持不变
  → 页面不会崩溃
```

### 7.4 GitHub Pages 保障

- 默认 `?api` 不存在 → 永远是 `static` 模式
- `data/gifts.json` 存在且完整 → 页面完全正常运行
- API 不可用 → fallback 到 static → 不影响线上展示

---

## 8. API 端点一览

| 方法 | 路径 | 功能 | API模式调用 |
|------|------|------|-----------|
| GET | `/api/health` | 健康检查 | `AftergiftAPI.checkHealth()` |
| GET | `/api/gifts` | 礼物列表（支持筛选） | `AftergiftAPI.listGifts({action_type, emotion})` |
| GET | `/api/gifts/{id}` | 礼物详情 | `AftergiftAPI.getGift(id)` |
| POST | `/api/gifts` | 发布礼物 | `AftergiftAPI.createGift(payload)` |
| POST | `/api/review/mock` | 故事审核 | `AftergiftAPI.reviewStory(short, full)` |
| POST | `/api/gifts/{id}/favorite` | 收藏 | `AftergiftAPI.favoriteGift(id)` |
| DELETE | `/api/gifts/{id}/favorite` | 取消收藏 | `AftergiftAPI.unfavoriteGift(id)` |
| POST | `/api/gifts/{id}/report` | 举报 | `AftergiftAPI.reportGift(id, payload)` |
| GET | `/api/admin/reviews` | 审核队列 | （admin 专用） |
| POST | `/api/admin/reviews/{id}/decision` | 审核决定 | （admin 专用） |

---

## 9. Phase 2D 新增：匿名认证

### 匿名身份流程

1. 用户点击 Dev Auth Panel 的"创建匿名身份"按钮
2. 前端调用 `POST /api/auth/anonymous`
3. 后端生成 `user_id` + `access_token`（格式：`af2d_...`）
4. Token 存入前端 `localStorage['aftergift_token']`
5. 后续所有用户操作自动在请求头附加 `Authorization: Bearer {token}`

### Auth Token 管理（api-client.js）

```javascript
AftergiftAPI.createAnonymousUser()  // POST /api/auth/anonymous
AftergiftAPI.getCurrentUser(token)  // GET /api/auth/me
AftergiftAPI.getStoredToken()       // localStorage.getItem('aftergift_token')
AftergiftAPI.storeToken(token)      // localStorage.setItem('aftergift_token', token)
AftergiftAPI.clearStoredToken()     // localStorage.removeItem('aftergift_token')
```

### 受保护接口（需 Bearer Token）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/gifts` | 发布礼物 |
| POST | `/api/gifts/{id}/favorite` | 收藏 |
| DELETE | `/api/gifts/{id}/favorite` | 取消收藏 |
| POST | `/api/gifts/{id}/report` | 举报 |

### Admin Token（sessionStorage）

- 用途：管理员审核面板
- 存储：`sessionStorage['aftergift_admin_token']`（会话级）
- Header：`x-admin-token: {token}`
- 开发 Token：`dev-admin-aftergift-001`

---

## 10. 当前限制

| 限制 | 说明 |
|------|------|
| **Phase 2D Token 非 JWT** | 使用 HMAC-SHA256 签名，非标准 JWT，Phase 2E 可升级为 PyJWT |
| **localStorage 风险** | Token 存 localStorage 可被 XSS 读取，内容审核是主要防护 |
| **单一固定 admin token** | Phase 2D 无多管理员、无角色分级 |
| **无 refresh token** | Token 过期后需重新创建匿名身份 |
| **needs_edit 无通知** | 审核退回后无自动消息通知用户 |
| **CORS 仅限本地** | 后端 CORS 白名单仅含 `localhost:8080` 和 `127.0.0.1:8080` |
| **无分页前端** | 前端一次性加载全量列表，未实现滚动加载 |

---

## 11. 快速验证清单

```bash
# 1. 启动后端
cd ~/projects/aftergift-backend-mvp/backend && . .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8091 &

# 2. 启动前端
cd ~/projects/aftergift-prototype && python3 -m http.server 8080 &

# 3. 验证 static 模式
# → 打开 http://127.0.0.1:8080/
# → footer 应显示："当前：静态示例数据（GitHub Pages 原型）"

# 4. 验证 api 模式
# → 打开 http://127.0.0.1:8080/?api
# → footer 应显示："当前：本地 FastAPI 联调模式"

# 5. 验证发布表单（api 模式）
# → 填写表单 → 提交 → 观察后端 aftergift_dev.db 中是否有新记录

# 6. 关闭服务
fuser -k 8091/tcp; fuser -k 8080/tcp
```
