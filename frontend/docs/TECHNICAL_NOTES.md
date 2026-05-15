# 技术架构说明

> 版本：1.0 | 状态：Phase 1E 归档版
> 适用：后端工程 · 前端工程 · 产品设计

---

## 1. 当前技术栈

### 1.1 文件结构

```
aftergift-prototype/
├── index.html          # 主页面（单页应用）
├── style.css          # 样式表（全自包含，无 CDN）
├── app.js             # 前端交互逻辑（Phase 1D 最新）
├── data/
│   └── gifts.json     # 示例礼物数据（14 条，JSON）
├── docs/              # 产品交接文档（Phase 1E 新增）
│   ├── PRODUCT_SPEC.md
│   ├── USER_FLOWS.md
│   ├── CONTENT_POLICY.md
│   ├── TECHNICAL_NOTES.md
│   ├── QA_CHECKLIST.md
│   ├── ROADMAP.md
│   └── CHANGELOG.md
└── README.md          # 项目说明
```

### 1.2 无外部依赖

- **无 CDN**：所有 CSS/JS 内联，无 external bundle
- **无 npm**：不使用 Node.js 构建工具
- **无后端**：纯静态文件，直接浏览器打开即可运行部分功能
- **无数据库**：数据仅存在前端内存（`gifts` 数组）和 localStorage

### 1.3 浏览器兼容性

- 目标：现代浏览器（Chrome 90+、Firefox 88+、Safari 14+、Edge 90+）
- CSS：`clamp()`、CSS Variables、`mask-image`（部分旧浏览器渐进增强）
- JS：ES6（无 Babel）
- localStorage：所有现代浏览器支持

---

## 2. 前端架构

### 2.1 模块划分（app.js）

```
app.js 逻辑分区：
├── State
│   ├── gifts[]           当前礼物列表
│   ├── currentFilter     当前筛选状态
│   ├── displayedCount    已展示卡片数量
│   ├── favorites{}        收藏（localStorage 同步）
│   └── nextTempId        临时 ID 生成器
│
├── Data Loading
│   └── loadGifts()       fetch('./data/gifts.json')
│
├── Rendering
│   ├── renderGifts()     筛选 + 分页 + 渲染
│   ├── giftCardHTML()    单卡片 HTML 生成
│   ├── bindCardEvents()  卡片事件绑定
│   └── emptyStateHTML()  空状态 HTML
│
├── Modal
│   ├── openModal()       打开详情 Modal
│   ├── closeModal()      关闭 Modal
│   └── handleModalAction()  Modal 按钮处理
│
├── Favorites
│   ├── loadFavorites()   localStorage 读取
│   ├── saveFavorites()   localStorage 写入
│   ├── toggleFavorite()  切换收藏状态
│   └── updateHeartIcon() 更新心形按钮样式
│
├── Story AI Review (Phase 1D)
│   ├── runAIReview()     主审核函数
│   ├── checkStoryQuality() 完整度检查
│   ├── getAnonymizationSuggestions() 匿名化建议
│   └── copyAIRewriteSuggestions() 复制建议
│
├── Form
│   ├── getFormData()     读取表单数据
│   ├── handleFormSubmit() 处理发布提交
│   └── initTextareas()   textarea auto-resize
│
├── Filters & Pagination
│   ├── handleFilterClick() 筛选标签点击
│   └── handleLoadMore()    阅读更多
│
└── Utilities
    ├── escHtml()          HTML 转义
    ├── scrollToSection()  平滑滚动
    ├── showToast()        Toast 提示
    └── emotionIconSVG()   情绪图标 SVG
```

### 2.2 gifts.json 数据结构

```json
{
  "id": "gift-001",
  "name": "星空投影灯",
  "type": "家居装饰",
  "relation": "前任",
  "relationLabel": "前任",
  "action": "sell",
  "actionLabel": "出售",
  "emotion": "放下",
  "excerpt": "在一起三年，分手后每次看到它都会想起那段时间……",
  "fullStory": "（600-2000 字中文完整故事）",
  "price": "￥280",
  "status": "出售中",
  "anonymous": true,
  "tags": ["家居", "灯", "前任", "放下"]
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 唯一标识（`gift-XXX` 或 `temp-XXXX`） |
| `name` | string | 礼物名称（显示在卡片标题）|
| `type` | string | 礼物类型（家居装饰/文具/数码/配饰/书籍/玩具摆件/健康/其他）|
| `relation` | string | 关系类型（前任/挚友/同事/恩师/家人/其他）|
| `relationLabel` | string | 关系显示标签（同 relation，但可被 anonymous 覆盖）|
| `action` | string | 处理方式（sell/exchange/giveaway/donate/keep）|
| `actionLabel` | string | 处理方式显示名 |
| `emotion` | string | 情绪标签（放下/遗憾/感谢/释怀/重启/纪念/治愈/平静）|
| `excerpt` | string | 一句话故事（100 字以内，显示在卡片）|
| `fullStory` | string | 完整故事（600-2000 字，显示在 Modal）|
| `price` | string | 价格或交换意向（keep 时为「非卖品，只讲故事」）|
| `status` | string | 当前状态（出售中/待流转/待认领/待捐出/故事保留）|
| `anonymous` | boolean | 是否匿名（当前统一为 true）|
| `tags` | string[] | 标签数组（用于未来扩展分类）|

### 2.3 localStorage 数据

**Key**: `aftergift_favorites`

**Value**: `JSON.stringify({ [giftId]: true, ... })`

```json
{
  "gift-001": true,
  "gift-003": true,
  "gift-007": true
}
```

### 2.4 前端路由

无路由框架，滚动锚点导航：

| Section ID | 功能 |
|-----------|------|
| `#hero` | Hero 首屏 |
| `#concept` | 概念说明区 |
| `#stories` | 礼物故事流 |
| `#publish` | 发布表单 |
| `#ethics` | 安全与伦理边界 |
| `#roadmap` | 产品路线图 |

---

## 3. GitHub Pages 部署

### 3.1 部署路径

```
https://conanxin.github.io/drafts/aftergift-prototype/
```

### 3.2 noindex 设置

`index.html` 第 3 行：
```html
<meta name="robots" content="noindex, nofollow">
```

### 3.3 部署校验

```bash
# 本地启动测试
cd ~/projects/aftergift-prototype
python3 -m http.server 8080
# 访问 http://localhost:8080

# 推送到 GitHub Pages
cd ~/conanxin.github.io
git add drafts/aftergift-prototype/
git commit -m "message"
git push origin main
# 约 2-5 分钟后生效
```

### 3.4 注意事项

- 根目录禁止存在 `gifts.json`（Phase 1C.2 已清理）
- 所有 JSON 数据必须放在 `data/` 子目录
- 不引入外部 CDN（Fonts/CSS/JS 全部自包含）

---

## 4. Phase 2 后端升级路径

### 4.1 推荐技术栈

| 层级 | 推荐方案 |
|------|---------|
| 语言 | Python（FastAPI）或 Node.js（Express/Koa）|
| 数据库 | PostgreSQL（关系数据）+ Redis（缓存/队列）|
| ORM | SQLAlchemy（Python）或 Prisma（Node.js）|
| API | RESTful JSON API |
| 文件存储 | S3 / Cloudflare R2（故事图片上传）|
| AI 审核 | OpenAI Moderation / 百度文本审核 |
| 管理后台 | React Admin 或 Django Admin |
| 通知 | Telegram Bot（管理员通知）|

### 4.2 核心 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/gifts` | 获取礼物列表（支持分页 + 筛选）|
| GET | `/api/gifts/:id` | 获取单个礼物详情 |
| POST | `/api/gifts` | 发布新礼物（含 AI 审核）|
| DELETE | `/api/gifts/:id` | 删除自己的礼物 |
| POST | `/api/gifts/:id/favorite` | 收藏（需登录）|
| DELETE | `/api/gifts/:id/favorite` | 取消收藏 |
| GET | `/api/users/:id/favorites` | 获取用户收藏列表 |
| POST | `/api/reports` | 提交举报 |
| GET | `/api/admin/reports` | 管理员查看举报列表 |
| POST | `/api/admin/reviews/:id/approve` | 审核通过 |
| POST | `/api/admin/reviews/:id/reject` | 审核拒绝 |

### 4.3 数据模型

**Gift**
```
id: UUID (PK)
author_id: UUID (FK → User, nullable for anonymous)
name: VARCHAR(100)
type: VARCHAR(50)
relation: VARCHAR(50) — nullable
action: ENUM(sell/exchange/giveaway/donate/keep)
emotion: VARCHAR(50)
excerpt: VARCHAR(200)
full_story: TEXT
price: VARCHAR(200)
is_anonymous: BOOLEAN
status: ENUM(pending/rejected/published/sold/exchanged/donated)
created_at: TIMESTAMP
updated_at: TIMESTAMP
```

**User**（Phase 2 可选匿名手机号注册）
```
id: UUID (PK)
phone_hash: VARCHAR(64) — HASH of phone, 不存真实号码
nickname: VARCHAR(50) — 随机生成匿名昵称
created_at: TIMESTAMP
is_admin: BOOLEAN
```

**Favorite**
```
user_id: UUID (FK)
gift_id: UUID (FK)
created_at: TIMESTAMP
```

**Report**
```
id: UUID (PK)
gift_id: UUID (FK)
reporter_ip: VARCHAR(50)
reason: TEXT
status: ENUM(pending/reviewed/dismissed)
admin_note: TEXT
created_at: TIMESTAMP
```

### 4.4 用户匿名身份设计

- 注册：手机号 HASH 后存储（不可逆，不存真实号码）
- 昵称：系统随机生成（如「安静的旧物收藏者 #4827」）
- 发布：可选择不绑定账号，匿名发布（仅存储 IP hash）
- 查看他人：只能看到昵称和礼物，无法看到 IP 或设备信息

### 4.5 AI 审核集成

```python
# OpenAI Moderation 示例
import openai

response = openai.Moderation.create(
    input=full_story_text
)
result = response["results"][0]
if result["flagged"]:
    # 进入人工复审队列
    status = "review"
else:
    status = "published"
```

---

## 5. 已知约束

| 约束 | 说明 |
|------|------|
| 无跨设备收藏同步 | localStorage 仅限同浏览器 |
| 无真实登录 | 无法区分用户身份 |
| 无图片上传 | 礼物图片暂不支持（可扩展）|
| 无分页 API | 全部 14 条一次性加载 |
| 无内容版本管理 | 编辑后直接覆盖旧版本 |
| 无通知 | 发布/收藏后无邮件/短信通知 |
