# Aftergift Admin Enhancements (Phase 2F)

## 目标

增强 Admin 审核台，让管理员能真正处理待审核内容、举报、审核日志和操作历史。

## 新增 API

### 1. Admin Reviews 筛选与分页

```
GET /api/admin/reviews?status=pending_review&risk_level=high_risk&provider=mock&page=1&limit=20&sort=created_at&order=desc
```

**查询参数：**
- `status`: pending_review | needs_edit | rejected | published | archived
- `risk_level`: safe | caution | high_risk
- `provider`: mock | openai | baidu | openai+mock
- `page`: 默认 1
- `limit`: 默认 20，最大 100
- `sort`: created_at | risk_level | status
- `order`: asc | desc

**返回：**
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "limit": 20,
  "total_pages": 3,
  "filters": { "status": "pending_review", ... }
}
```

### 2. Admin Decision with Note

```
POST /api/admin/reviews/{gift_id}/decision
```

```json
{
  "decision": "approve|needs_edit|reject",
  "note": "给用户或审核记录的说明"
}
```

### 3. Reports 管理

```
GET /api/admin/reports?status=pending&page=1&limit=20
```

```
POST /api/admin/reports/{report_id}/decision
```

```json
{
  "decision": "dismiss|take_action|needs_review",
  "note": "处理说明"
}
```

### 4. Review Logs

```
GET /api/admin/reviews/{gift_id}/logs
```

### 5. Admin Actions 历史

```
GET /api/admin/actions?target_type=gift&target_id=xxx&page=1&limit=20
```

## 前端增强

- **Tab 切换**：审核队列 / 举报队列 / 操作历史
- **筛选栏**：status、risk_level、provider、sort、order
- **分页**：上一页/下一页，页码显示
- **审核备注**：每个卡片支持 textarea 输入 note
- **查看日志**：点击按钮查看 gift 的 review_logs

## 安全边界

1. 所有 Admin API 必须携带 `X-Admin-Token`
2. SQL 参数化，sort/order 白名单校验
3. 不返回未脱敏敏感原文
4. 不泄露 token
5. 不删除用户内容（保守处理）

## 当前限制

- 举报处理中的 `take_action` 仅修改 report 状态和 gift 状态，不涉及真实内容删除
- Admin Actions 查询不支持复杂过滤（仅 target_type / target_id）
- 前端 Admin UI 仅在 `?api=local&admin=1` 模式下显示
