# Aftergift Phase 2H-1 — 我的发布管理

> 版本：1.0 | 日期：2026-05-16

---

## 1. 目标

增强"我的发布"管理能力。用户在 API 模式下创建匿名身份后，可以：
- 编辑自己的待审核/需修改内容
- 将 `needs_edit` 内容重新提交审核
- 将已发布内容撤回归档

**不做**：评论、私信、推荐算法、交易功能。

---

## 2. 接口一览

> 当前路径基于 `gifts.py` router prefix `/api/gifts`，因此实际路径为 `/api/gifts/me/gifts/{id}`。后续如需改为 `/api/me/gifts/{id}`，另开兼容迁移阶段。

### 2.1 GET /api/gifts/me/gifts/{gift_id}

**用途**：获取当前用户自己的礼物详情（含完整故事和审核备注）

**权限**：`Authorization: Bearer <token>`

**安全**：非自己 → 404（避免暴露存在性）

**响应字段**：
- `id`, `title`, `category`, `relation_type`, `relation_label`
- `action_type`, `action_label`, `emotion`, `price_or_exchange`
- `condition_note`, `city_blur`, `is_anonymous`, `anonymous_nickname`
- `status`, `story`, `created_at`, `updated_at`
- `review_note`：最近一次 admin `needs_edit` 备注

---

### 2.2 PATCH /api/gifts/me/gifts/{gift_id}

**用途**：编辑自己的礼物

**权限**：`Authorization: Bearer <token>`

**可编辑字段**：
`title`, `category`, `relation_type`, `relation_label`, `action_type`, `emotion`, `price_or_exchange`, `condition_note`, `city_blur`, `is_anonymous`, `short_story`, `full_story`

**状态规则**：
- ✅ 允许：`draft` / `pending_review` / `needs_edit`
- ❌ 禁止：`published` / `rejected` / `archived` → 409

**审核复跑**：
- 编辑 `short_story` 或 `full_story` 后，自动重新运行 mock/OpenAI 审核
- 审核结果写入 `review_logs`
- suggestions / evidence 仍脱敏（与 Phase 2E-3 策略一致）

**受保护字段**：
- `user_id`、`status`、`id` 不在 `allowed_fields` 中，会被忽略

---

### 2.3 POST /api/gifts/me/gifts/{gift_id}/resubmit

**用途**：重新提交礼物审核

**权限**：`Authorization: Bearer <token>`

**状态规则**：
- ✅ 允许：`draft` / `needs_edit`
- ❌ 禁止：`published` / `pending_review` / `rejected` / `archived` → 409

**行为**：
- 重新运行审核
- 状态变为 `pending_review`（保守策略）
- 写入 `review_logs`

---

### 2.4 POST /api/gifts/me/gifts/{gift_id}/archive

**用途**：撤回（归档）自己的礼物

**权限**：`Authorization: Bearer <token>`

**状态规则**：
- ✅ 允许：`published` / `pending_review` / `needs_edit`
- ❌ 禁止：`draft` / `rejected` / `archived` → 409

**行为**：
- 状态变为 `archived`
- 普通 `GET /api/gifts` 不再返回
- `mine=true` 仍可看到

**审计**：
- 写入 `admin_actions`
- `admin_id="self:<user_id>"`（MVP 临时方案）
- `note` 记录"用户自行归档礼物（原状态：xxx）"

---

## 3. 状态机图

```
                    ┌─────────────┐
                    │    draft    │
                    └──────┬──────┘
                           │ 创建 / resubmit
                           ▼
              ┌────────────────────────┐
              │     pending_review     │◄──── resubmit
              └──────┬─────────────────┘
                     │ 审核通过
                     ▼
              ┌─────────────┐
              │   published │
              └──────┬──────┘
                     │ archive
                     ▼
              ┌─────────────┐
              │   archived  │
              └─────────────┘
                     ▲
                     │ archive
              ┌──────┴──────┐
              │  needs_edit  │
              └─────────────┘
```

**编辑允许**：draft → pending_review → needs_edit（双向）
**重新提交**：draft / needs_edit → pending_review
**归档**：published / pending_review / needs_edit → archived

---

## 4. 前端适配

### 4.1 我的发布卡片操作按钮

按状态显示：

| 状态 | 编辑故事 | 重新提交 | 暂时收起 |
|------|----------|----------|----------|
| draft | ✅ | ✅ | ❌ |
| pending_review | ✅ | ❌ | ✅ |
| needs_edit | ✅ | ✅ | ✅ |
| published | ❌ | ❌ | ✅ |
| rejected | ❌ | ❌ | ❌ |
| archived | ❌ | ❌ | ❌ |

### 4.2 编辑 Modal

- 仅 API 模式下启用
- 轻量表单，字段与发布表单一致
- 顶部显示当前状态
- 如有 `review_note`，显示审核备注（珊瑚色提示条）
- 保存后刷新"我的发布"列表

### 4.3 Toast 反馈

| 操作 | 成功 | 失败 |
|------|------|------|
| 编辑 | "修改已保存" | "保存失败：..." |
| 重新提交 | "已重新进入审核队列" | "重新提交失败：..." |
| 归档 | "这件礼物已暂时收起" | "归档失败：..." |

---

## 5. 安全与隐私

- **404 隐藏存在性**：非本人请求返回 404，不区分"不存在"和"存在但非你"
- **字段白名单**：PATCH 只允许 `allowed_fields`，忽略其他字段
- **状态机保护**：不允许通过 PATCH 直接修改 `status`
- **审核复跑**：编辑 story 后重新审核，防止用户绕过审核
- **脱敏持续**：review_logs 的 suggestions / evidence 仍脱敏
- **审计留痕**：用户归档行为写入 admin_actions

---

## 6. 测试覆盖

`backend/tests/test_my_gift_management.py`（14 项）：

1. GET 无 token → 401
2. GET 非本人 → 404
3. GET 本人 → 200
4. GET needs_edit 含 review_note
5. PATCH 自己的 pending_review → 200
6. PATCH 他人礼物 → 404
7. PATCH published → 409
8. PATCH 不允许改 user_id/status/id
9. POST resubmit needs_edit → 200，状态 pending_review
10. POST resubmit published → 409
11. POST archive published → 200，状态 archived
12. archived 不出现在普通 GET
13. archived 出现在 mine=true
14. 编辑 story 后写入 review_logs，且 suggestions 脱敏

---

## 7. 当前限制

- 路径层级较深：`/api/gifts/me/gifts/{id}`（因 gifts router prefix）
- 无草稿自动保存
- 归档后无法恢复
- 无用户操作历史时间线
- 删除功能未实现（Phase 2H-2 候选）

---

## 8. 相关文档

- `API_DESIGN.md` — 接口详细设计
- `API_INTEGRATION.md` — 前端集成指南
- `PHASE2_PLAN.md` — 阶段计划
- `NEXT_STEPS.md` — 后续方向
