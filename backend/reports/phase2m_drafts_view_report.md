# Phase 2M：本地草稿管理 — 阶段报告

**STATUS**: ✅ PASS | ALL VALIDATION PASSED

**日期**: 2026-05-16
**BASELINE_COMMIT**: `8295bcd` — Stabilize my space view rendering (Phase 2L-2.1)

---

## 目标

增强本地草稿管理。基于现有 `aftergift_edit_draft_{gift_id}` localStorage 草稿机制，新增草稿列表、草稿预览、恢复编辑、删除草稿、过期提示，并接入 My Space。

---

## 新增内容

### 1. 草稿数据结构升级

从纯 payload 升级为封套格式：

```json
{
  "payload": { ... },
  "updated_at": "2026-05-16T21:00:00.000Z"
}
```

- 写入时自动附加 `updated_at`（ISO 8601）
- 读取时自动识别新/旧格式（检测 `payload` 字段）
- 兼容旧格式（无 `payload` 字段视为旧格式，`updated_at` 为 null）
- 不影响编辑 Modal 中的草稿恢复功能

### 2. 新增 `?view=drafts` 视图

入口：My Space 本地草稿统计卡片点击，或直接访问 URL。

功能：
- **空状态**：显示"这里还没有本地草稿。你编辑过的故事会暂时保存在这台设备上。"
- **草稿卡片列表**：按 `updated_at` 倒序，每条显示：
  - 礼物名称（无则为"未命名草稿"）
  - gift_id 简写（8字符）
  - 最后修改时间（`toLocaleString` 本地格式）
  - 30天过期提示（超过30天显示黄色徽章）
- **操作按钮**：继续编辑 / 删除（含二次确认按钮文案变化）
- **返回**：返回 My Space（清除 URL 参数）

### 3. My Space 接入草稿入口

- `#mySpaceStatDrafts` 改为可点击（`cursor:pointer`，`onclick=enterDraftsView()`）
- `renderMySpaceStats()` 中当 `drafts > 0` 时显示"查看草稿 →"链接（`#mySpaceDraftsLink`）
- 删除草稿后同步更新 My Space 草稿数量显示

### 4. 恢复编辑流程

- 点击"继续编辑" → 检查 `gifts` 数组是否存在 `gift_id`
- 存在 → `exitDraftsView()` → `openEditModal(giftId)`
- 不存在 → toast "这个草稿对应的礼物暂时找不到了。"

Edit Modal 中的恢复逻辑已升级：自动识别新/旧格式。

### 5. 删除草稿

- 第一次点击"删除"：按钮文案变为"确认删除"（红色样式），3000ms 后自动恢复
- 确认后删除 `localStorage` key，显示 toast"本地草稿已删除"，刷新草稿列表
- My Space 草稿计数同步更新

### 6. 30 天过期提示

- `updated_at` 距今超过 30 天显示黄色徽章"已保存超过 30 天"
- 不自动删除，由用户手动处理
- `updated_at` 为 null（旧格式）不显示过期提示

---

## 修改文件

| 文件 | 改动 |
|------|------|
| `frontend/app.js` | 新增 `enterDraftsView`/`exitDraftsView`/`renderDraftsView`；`checkUrlView` 增加 `?view=drafts`；草稿封套格式写入（`bindEditFormEvents`）；草稿读取兼容新/旧格式（`restoreDraftBtn`）；`renderMySpaceStats` 增加草稿链接显示 |
| `frontend/index.html` | `#mySpaceStatDrafts` 改为可点击；新增 `#mySpaceDraftsLink` 链接；新增 `#draftsView` / `#draftsViewContainer` |
| `frontend/style.css` | 新增 `.drafts-view`、`.draft-card`、`.draft-expired-badge` 等样式（~150行）；`body.drafts-view` 隐藏其他区块 |
| `frontend/docs/DRAFTS_VIEW.md` | 新建文档 |
| `frontend/docs/MY_SPACE_VIEW.md` | 更新本地草稿章节，新增 Phase 2M 草稿视图说明 |
| `docs/NEXT_STEPS.md` | 新增 Phase 2M 行项目 |
| `backend/reports/phase2m_drafts_view_report.md` | 本报告 |

---

## 验证结果

```
node --check frontend/app.js          ✅ EXIT:0
node --check frontend/api-client.js   ✅ EXIT:0
python3 -m json.tool gifts.json       ✅ EXIT:0

后端测试（13/13）：全部 150/150 PASS ✅
  test_favorites_api                 15/15 PASS
  test_my_gifts                      12/12 PASS
  test_my_actions_and_restore         12/12 PASS
  test_auth_jwt                      12/12 PASS
  test_schema                         7/7  PASS
  test_discovery_api                 18/18 PASS
  test_my_gift_management            14/14 PASS
  test_search_api                    12/12 PASS
  test_migrations                     4/4  PASS
  test_admin_enhancements            11/11 PASS
  test_redaction                     11/11 PASS
  test_moderation_provider           11/11 PASS
  test_openai_provider               11/11 PASS

HTTP preview (frontend http.server 8080):
  /                     → HTTP 200 ✅
  /?view=me             → HTTP 200 ✅
  /?view=drafts         → HTTP 200 ✅
  /?view=favorites      → HTTP 200 ✅
```

---

## 隐私与安全说明

1. **草稿仅本地**：草稿数据仅存在于 localStorage，不上传至服务器。
2. **列表页不显示正文**：草稿列表仅显示名称和时间戳，不展示故事正文。
3. **恢复需找到礼物**：如果草稿对应的礼物已不在内存列表中，无法恢复。
4. **二次确认删除**：删除按钮需要两次点击确认，防止误操作。
5. **无自动上传**：草稿保存仅在编辑表单中触发（800ms 防抖），不自动同步。

---

## 限制说明

1. 草稿仅存在当前浏览器 localStorage，换设备/换浏览器不可访问。
2. 草稿不自动同步到后端 API。
3. 暂不支持草稿导入/导出。
4. 暂不支持自动清理过期草稿（未来可增加"30天无操作自动清理"条款）。

---

## 后续推荐阶段

**Phase 3A-0：社区功能设计评审**
- 温和评论系统（`POST /api/gifts/{id}/comments`）+ 匿名审核流程
- 私信匿名中继设计（防骚扰机制）

**Phase 3B：轻量社区功能**
- 收藏故事评论
- 匿名私信

---

## BASELINE_COMMIT

`8295bcd` — Stabilize my space view rendering (Phase 2L-2.1)

## TARGET_COMMIT

（本阶段修改待提交推送）