# Aftergift Phase 2H-2 — My Actions & Restore Workflow

## 目标

为 Aftergift 用户提供完整的个人发布管理能力：
- **归档恢复**：将已归档的礼物重新提交审核
- **操作历史**：记录并查看用户对礼物的所有操作
- **API Alias 清理**：提供干净的 `/api/me/` 路径，保留旧路径兼容
- **编辑草稿自动保存**：前端本地草稿保护，防止意外丢失

## 新 API Alias

| 方法 | 新路径 | 说明 |
|------|--------|------|
| GET | `/api/me/gifts/{gift_id}` | 查看我的礼物详情 |
| PATCH | `/api/me/gifts/{gift_id}` | 编辑我的礼物 |
| POST | `/api/me/gifts/{gift_id}/resubmit` | 重新提交审核 |
| POST | `/api/me/gifts/{gift_id}/archive` | 归档（暂时收起） |
| POST | `/api/me/gifts/{gift_id}/restore` | **恢复归档 → pending_review** |
| GET | `/api/me/actions` | 查看我的操作历史 |

## 旧路径兼容

以下旧路径仍保留，前端已全面切换至新路径：

- `/api/gifts/me/gifts/{gift_id}` → 仍可用（gifts router 内部处理）

## Restore 逻辑

```
archived ──restore──→ pending_review
```

- 仅 `archived` 状态可恢复
- 恢复后自动触发内容复核（`_review_and_log`）
- 恢复操作记录到 `user_actions` 表
- 非本人访问 → 404
- 非 archived 状态 → 409

## user_actions 表

```sql
CREATE TABLE user_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    gift_id TEXT,
    action TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (gift_id) REFERENCES gifts(id) ON DELETE SET NULL
);
```

记录的操作类型：
- `edit` — 编辑故事
- `resubmit` — 重新提交
- `archive` — 暂时收起
- `restore` — 恢复审核

## GET /api/me/actions

返回当前用户的操作历史，支持筛选：
- `gift_id` — 按礼物筛选
- `action` — 按操作类型筛选
- `page` / `limit` — 分页

响应包含 `gift_title`（关联礼物标题）。

## 前端草稿自动保存

编辑 Modal 中：
- 输入框变化后 800ms debounce 自动保存到 `localStorage`
- Key: `aftergift_edit_draft_{gift_id}`
- 打开 Modal 时自动恢复草稿
- 提交成功后清除草稿
- 提供「放弃草稿」手动清除选项

## 状态机说明

```
draft ──publish──→ pending_review ──approve──→ published
                          │
                          ├──reject──→ rejected
                          │
                          └──needs_edit──→ needs_edit ──resubmit──→ pending_review

published ──archive──→ archived ──restore──→ pending_review
```

可编辑状态：`draft`, `pending_review`, `needs_edit`
可归档状态：`published`, `needs_edit`, `rejected`
可恢复状态：`archived`
可重新提交状态：`needs_edit`, `rejected`

## 当前限制

- 操作历史仅支持 API 模式（static 模式下不显示）
- 草稿仅保存在浏览器本地，换设备/清缓存会丢失
- 操作历史暂无删除/编辑功能
- 未实现操作历史的批量导出

## 测试覆盖

`backend/tests/test_my_actions_and_restore.py` — 12 项测试：
1. GET /api/me/gifts/{id} 本人 → 200
2. GET /api/gifts/me/gifts/{id} 旧路径仍可用
3. POST /api/me/gifts/{id}/restore archived → 200
4. restore 后状态 = pending_review
5. restore 非本人 → 404
6. restore 非 archived → 409
7. PATCH 编辑写入 user_actions
8. resubmit 写入 user_actions
9. archive 写入 user_actions
10. restore 写入 user_actions
11. GET /api/me/actions 只返回当前用户
12. migration 002 创建 user_actions 表且幂等
