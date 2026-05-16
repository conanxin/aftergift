# 本地草稿视图 (Drafts View) — Phase 2M

## 目标

增强本地草稿管理。基于 `aftergift_edit_draft_{gift_id}` localStorage 机制，新增草稿列表、草稿预览、恢复编辑、删除草稿、30 天过期提示，并接入 My Space。

## 重要约束

- 草稿**仅保存在 localStorage**，不涉及后端数据库。
- 不在 My Space 总览显示完整故事正文，避免敏感信息暴露。
- 不实现评论、私信、交易功能。
- 不做公开用户主页。

---

## localStorage 草稿 key

```
aftergift_edit_draft_{gift_id}
```

例：`aftergift_edit_draft_a1b2c3d4-e5f6-7890-abcd-ef1234567890`

---

## 草稿数据结构

Phase 2M 将草稿格式从纯 payload 升级为带元数据的封套格式：

**新格式（推荐）：**
```json
{
  "payload": {
    "name": "...",
    "story": "...",
    ...
  },
  "updated_at": "2026-05-16T21:00:00.000Z"
}
```

**旧格式（兼容）：**
```json
{
  "name": "...",
  "story": "...",
  ...
}
```

读取时自动识别：如果检测到 `payload` 字段，则为新格式；否则按旧格式解析。`updated_at` 为 null 表示旧格式草稿（无时间戳）。

---

## ?view=drafts

入口：My Space 统计卡片点击，或 URL 直接访问 `?view=drafts`。

功能：
1. **空状态**：显示"这里还没有本地草稿。你编辑过的故事会暂时保存在这台设备上。"
2. **草稿卡片列表**：按最后修改时间倒序排列
   - 每条显示：礼物名称（无则为"未命名草稿"）、gift_id 简写（8字符）、最后修改时间、30天过期提示
3. **操作按钮**：继续编辑 / 删除（含二次确认）
4. **返回**：返回 My Space

### 隐私原则

草稿列表页**不展示完整故事正文**，仅显示礼物名称和时间戳，防止敏感内容在列表页泄露。

---

## My Space 接入

### 统计卡片

本地草稿统计卡片（`#mySpaceStatDrafts`）已改为可点击（`cursor:pointer`）。

渲染 `renderMySpaceStats` 时，如果 `drafts` 数值 > 0，则显示"查看草稿 →"链接（`#mySpaceDraftsLink`）。

### 草稿数量统计

沿用现有 scanner：从 `localStorage` 中遍历所有 `aftergift_edit_draft_*` key 并计数。

---

## 恢复编辑流程

1. 用户点击草稿卡片的"继续编辑"。
2. 检查当前 `gifts` 数组（内存中）中是否存在对应 `gift_id`。
3. **能找到**：调用 `exitDraftsView()` → `openEditModal(giftId)`。Edit Modal 会检测到 `aftergift_edit_draft_{gift_id}` 并显示恢复提示。
4. **找不到**：显示 toast"这个草稿对应的礼物暂时找不到了。"

> 注：Edit Modal 中的草稿恢复按钮（`#editRestoreDraftBtn`）读取新格式（`payload` + `updated_at`），也兼容旧格式（直接为 payload）。

---

## 删除草稿流程

1. 用户点击"删除"按钮。
2. 按钮文案从"删除"变为"确认删除"（红色样式），3000ms 后自动恢复。
3. 再次点击确认：删除 `localStorage` key，更新显示，`showToast('本地草稿已删除')`。
4. 如果 My Space 的草稿计数元素可见，同步更新数字。

---

## 30 天过期提示

规则：
- `updated_at` 距今超过 30 天，显示黄色徽章"已保存超过 30 天"。
- **不自动删除**，由用户手动处理。
- `updated_at` 为 null（旧格式草稿）不显示过期提示。

---

## 限制说明

1. 草稿仅存在当前浏览器 localStorage，换设备/换浏览器不可访问。
2. 草稿不自动同步到后端 API。
3. 暂不支持草稿导入/导出。
4. 暂不支持自动清理过期草稿（未来可在隐私政策中增加"30天无操作自动清理"条款）。

---

## 路由

| URL | 视图 |
|-----|------|
| `?view=drafts` | 本地草稿列表 |
| `?view=me` | My Space（入口含草稿卡片） |

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `frontend/app.js` | `enterDraftsView`、`exitDraftsView`、`renderDraftsView` 函数；`checkUrlView` 新增 `?view=drafts`；`bindEditFormEvents` 升级草稿封套格式 |
| `frontend/index.html` | `#mySpaceStatDrafts` 改为可点击；新增 `#draftsView` / `#draftsViewContainer` |
| `frontend/style.css` | 新增 `.drafts-view`、`.draft-card`、`.draft-expired-badge` 等样式；`body.drafts-view` 隐藏其他区块 |

---

## 历史

| Phase | 日期 | 说明 |
|-------|------|------|
| 2M | 2026-05-16 | 新增 ?view=drafts、草稿数据结构升级为封套格式、My Space 接入草稿入口、30天过期提示 |
| 2H-2 | 2025 | 初代草稿自动保存机制：编辑表单 input 800ms 后自动写入 localStorage key `aftergift_edit_draft_{gift_id}`，Edit Modal 中显示恢复/丢弃按钮 |