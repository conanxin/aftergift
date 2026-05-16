# Aftergift 搜索 API 文档 (Phase 2G-1)

## 目标
实现礼物内容的多维发现与搜索能力，支持关键词、情绪标签、处理方式、关系类型、城市模糊等筛选，以及分页和排序。

## API 端点

### GET /api/gifts

支持以下查询参数：

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| q | string | 关键词搜索（标题 + 故事全文） | `q=灯` |
| emotion | string | 情绪标签筛选 | `emotion=平静` |
| action_type | string | 处理方式筛选 | `action_type=sell` |
| relation_type | string | 关系类型筛选 | `relation_type=lover` |
| city_blur | string | 城市模糊筛选 | `city_blur=上海` |
| page | int | 页码（从 1 开始） | `page=1` |
| limit | int | 每页条数（默认 12，最大 50） | `limit=12` |
| sort | string | 排序字段（白名单） | `sort=created_at` |
| order | string | 排序方向：`asc` 或 `desc` | `order=desc` |

#### sort 白名单
- `created_at` — 创建时间
- `updated_at` — 更新时间
- `title` — 标题
- `price_or_exchange` — 价格/交换意向

#### 返回结构

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [...],
    "total": 42,
    "page": 1,
    "limit": 12,
    "total_pages": 4,
    "has_more": true,
    "filters": {
      "q": "灯",
      "emotion": null,
      "action_type": null,
      "relation_type": null,
      "city_blur": null,
      "sort": "created_at",
      "order": "desc"
    }
  }
}
```

#### items 字段

| 字段 | 说明 |
|------|------|
| id | 礼物唯一 ID |
| title | 礼物名称 |
| category | 礼物类型 |
| relation_type | 关系类型（英文） |
| relation_label | 关系类型（中文） |
| action_type | 处理方式（英文） |
| action_label | 处理方式（中文） |
| emotion | 情绪标签 |
| excerpt | 一句话故事 |
| story_excerpt | 完整故事前 120 字纯文本摘要 |
| price_or_exchange | 价格或交换意向 |
| status | 发布状态 |
| is_anonymous | 是否匿名 |
| anonymous_nickname | 匿名昵称 |
| city_blur | 城市模糊 |
| created_at | 创建时间 |
| updated_at | 更新时间 |
| matched_fields | 匹配到的字段（仅搜索时返回） |

## SQL 注入防护

- `sort` 和 `order` 参数必须通过硬编码白名单校验，不合法值直接返回 400 错误。
- 所有用户输入均通过 SQLite 参数化查询处理，不直接拼接 SQL。

## 搜索范围

关键词 `q` 同时扫描以下字段：
- `gifts.title`
- `gifts.category`
- `gift_stories.story`
- `gift_stories.story_title`
- `gifts.price_or_exchange`

## 双模式支持

### Static 模式（GitHub Pages 默认）
- 前端使用内存中的 `DEMO_GIFTS` 数据。
- 搜索通过 JavaScript `filter` 实现多字段匹配。
- 分页在内存中完成。

### API 模式（`?api=local`）
- 前端调用 `/api/gifts` 端点。
- 后端执行 SQL 查询并返回分页结果。

## 当前限制

- 不支持全文搜索（FTS），当前使用 `LIKE` 匹配。
- 不支持搜索高亮显示。
- 不支持按价格区间筛选。
- 不支持多标签组合筛选（OR 逻辑）。

## 后续扩展

- Phase 2G-2：我的发布 / 我的收藏
- Phase 2H：内容审核与发布工作流
- Phase 3A：担保交易与物流
