# ADMIN_REVIEW_UI.md — Aftergift 管理员审核面板设计

## 1. 目标

为 Aftergift 提供一个轻量级的内容审核界面，使管理员能够：
- 查看待审核礼物故事
- 评估隐私风险和内容质量
- 做出 approve / needs_edit / reject 决策
- 记录审核操作审计轨迹

## 2. 访问方式

```
http://localhost:8080/?api=local&admin=1
```

- `api=local`：激活 API 联调模式（前端显示 Dev Auth Panel）
- `admin=1`：显示 Admin Review Panel
- 普通用户访问 `http://localhost:8080/`（static 模式）不会看到审核面板

## 3. 管理员 Token

- 存储位置：`sessionStorage['aftergift_admin_token']`（会话级，不持久化，不写源码）
- 传入方式：管理员在界面输入框粘贴 token，按"加载队列"按钮
- 默认开发 Token：`dev-admin-aftergift-001`
- 验证 Header：`x-admin-token: {token}`

## 4. 审核队列字段

GET `/api/admin/reviews` 返回的每条记录包含：

| 字段 | 说明 |
|------|------|
| gift_id | 礼物 ID |
| title | 标题 |
| category | 类型 |
| relation_type | 关系类型 |
| relation_label | 关系标签 |
| action_type | 处理方式 |
| emotion | 情绪标签 |
| short_story | 故事摘录 |
| full_story | 完整故事 |
| risk_level | 风险等级：safe / caution / high_risk |
| story_quality_score | AI 质量评分（0-100） |
| review_issues | 风险问题列表 |
| review_suggestions | AI 审核建议 |
| identity_risk | 身份暴露风险 |
| attack_risk | 攻击性风险 |
| identifiable_person_risk | 可识别他人风险 |
| status | pending_review / needs_edit / approved / rejected / published |
| ai_decision | AI 建议 |
| ai_review_notes | AI 详细备注 |

## 5. 风险等级颜色

| 等级 | CSS 类 | 颜色 |
|------|--------|------|
| safe | `.risk-low` | 绿 |
| caution | `.risk-medium` | 黄 |
| high_risk | `.risk-high` | 红 |

## 6. 状态标签颜色

| 状态 | CSS 类 |
|------|--------|
| pending_review | `.status-pending` |
| needs_edit | `.status-needs_edit` |
| approved | `.status-approved` |
| rejected | `.status-rejected` |
| published | `.status-published` |

## 7. 审核操作与状态流转

```
pending_review ──approve──→ published
              ──needs_edit──→ needs_edit ──(用户修改后)──→ pending_review
              ──reject──→ rejected
needs_edit ──approve──→ published
          ──reject──→ rejected
```

### 7.1 操作按钮

- **approve**（绿色）：直接发布
- **needs_edit**（黄色）：退回给用户修改（当前 UI 仍由 admin 操作）
- **reject**（红色）：永久拒绝

### 7.2 Admin Decision 端点

```
POST /api/admin/reviews/{gift_id}/decision
x-admin-token: dev-admin-aftergift-001
Content-Type: application/json

{"decision": "approve" | "needs_edit" | "reject"}
```

**响应**（200）：
```json
{
  "code": 200,
  "data": {
    "gift_id": "gift-003",
    "new_status": "published",
    "decided_at": "2026-05-16 06:59:38"
  }
}
```

## 8. 审计记录

每次 decision 操作会写入 `admin_actions` 表：

| 列 | 说明 |
|----|------|
| id | UUID |
| admin_id | 固定 `dev-admin`（Phase 2D） |
| action | approve / needs_edit / reject |
| target_type | "gift" |
| target_id | gift_id |
| reason | 备注（可选） |
| created_at | 操作时间 |

## 9. 当前限制（Phase 2D）

- 单一固定 admin token，明文存储于代码中（仅本地开发用）
- 无多管理员、无角色权限分级
- decision 无须填理由
- needs_edit 后无自动通知用户机制
- AI 审核（review_service）仅做风险标注，不自动执行决策

## 10. 未来升级方向（Phase 3+）

- 接入真实管理员登录（用户名 + 密码_hash，或 OAuth）
- 审核结果实时通知用户（站内信或邮件）
- 历史审核记录查询和统计
- 敏感词自动过滤 + 人工复审双重关卡
- 多语言内容检测

---

*文档版本：Phase 2D | 更新日期：2026-05-16*
