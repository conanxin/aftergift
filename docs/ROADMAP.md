# Aftergift 路线图

**Phase Closeout — 2026-05-16**
**BASELINE_COMMIT**: `b15add7`

---

## 路线图说明

Aftergift 采用**阶段门控**（Phase-gated）开发模式：
- 每个 Phase 完成后输出结构化报告
- 下一 Phase 必须经过安全评审才能开始
- 支付、评论（实现中）、私信均未完成，审核仍需人工兜底
- 详细技术设计见各 Phase 文档

---

## 下一阶段（推荐）

### Phase 3A-1：评论数据模型与 Migration

**前置条件**：Phase 3A-0 设计评审已完成 ✅，需用户确认后开始。

**目标**：
- 创建 `comments` 表（id, gift_id, user_id, body, status, risk_level, created_at）
- 创建 `comment_review_logs` 表（审核日志）
- 创建 `comment_reports` 表（用户举报）
- 实现基础 CRUD API（`POST/GET /api/gifts/{id}/comments`）
- 所有评论默认 `pending_review`，通过审核才展示
- 频率限制：每人每礼物 1 条，每小时最多 10 条，每 IP 每小时 20 条

**安全边界**：
- 不支持公开联系方式
- 不实现自由私信
- 先审后发，AI + 规则双层审核

**交付物**：
- Migration 文件
- 评论 API 实现
- 频率限制逻辑
- 基础测试

---

### Phase 3A-2：评论审核引擎

**目标**：
- 将 Phase 3A-0 的审核流程设计文档转化为代码
- 静态规则（正则）检测敏感信息
- AI Moderation Provider 第二道审核
- 风险分级（safe/caution/high_risk/blocked）
- Admin 审核台评论队列 UI

---

### Phase 3A-3：Admin 评论队列

**目标**：
- 评论队列管理面板（分页、筛选、按 risk_level 排序）
- 评论详情（含被审核礼物上下文）
- 操作历史（approve/needs_edit/reject + 理由）
- 批量操作支持

---

### Phase 3A-4：温和评论 UI

**目标**：
- 前端礼物详情 Modal 增加评论区
- 展示已通过审核的评论
- 评论输入框（带敏感信息提示）
- 用户可隐藏/举报评论
- 语气引导（短句、温和、不追问）

---

## 延后阶段

### Phase 3B：匿名中继私信（延后）

**原因**：私信风险高于评论（一对一私密性、关系不对等、线下邀约风险）。

**前提**：等评论系统稳定运行 3 个月后，再做二次安全评估。

**设计文档**（已完成）：`backend/docs/ANONYMOUS_MESSAGING_DESIGN_REVIEW.md`

---

### Phase 4：交易/交换撮合（远期）

**前提**：需要支付牌照和法律合规评估。

**当前状态**：不推进，不承诺。

---

### Phase 5：生产部署 + PostgreSQL

**目标**：
- PostgreSQL 替代 SQLite（高并发支持）
- Docker 容器化部署
- 定时任务（crontab）
- 监控和告警

**前置条件**：Phase 3A-4 评论功能稳定运行。

---

### Phase 6：移动端 / PWA

**当前状态**：不推进，不承诺。

---

## 已完成阶段

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 静态原型 | ✅ 完成 |
| Phase 2A | 后端沙箱蓝图 | ✅ 完成 |
| Phase 2B | FastAPI 骨架 + SQLite | ✅ 完成 |
| Phase 2C | 前后端 local API 双模式联调 | ✅ 完成 |
| Phase 2D | 匿名身份 + Admin 审核队列 UI | ✅ 完成 |
| Phase 2E | PyJWT + Moderation Provider 抽象 | ✅ 完成 |
| Phase 2F | Admin 增强 + 举报队列 | ✅ 完成 |
| Phase 2G | 搜索 API + 我的发布/收藏 | ✅ 完成 |
| Phase 2H | 我的发布管理（编辑/重新提交/归档/恢复）| ✅ 完成 |
| Phase 2I-0 | 本地内测准备 | ✅ 完成 |
| Phase 2I | 基础内容推荐（Discovery）| ✅ 完成 |
| Phase 2K-1 | 收藏 API | ✅ 完成 |
| Phase 2K-2 | 收藏数量 Badge + 排序 | ✅ 完成 |
| Phase 2L-1 | 社区功能准备 | ✅ 完成 |
| Phase 2L-2 | 我的空间 / Private User Space | ✅ 完成 |
| Phase 2L-2.1 | My Space 稳定性修复 | ✅ 完成 |
| Phase 2M | 本地草稿管理 | ✅ 完成 |
| Phase 3A-0 | 社区功能设计评审 | ✅ 完成 |

---

## 决策记录

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-04-14 | 匿名身份设计 | 降低用户发布心理门槛，避免真实身份泄露 |
| 2026-04-17 | 先审后发 | 防止报复内容、身份曝光、骚扰 |
| 2026-04-22 | Moderation Provider 抽象 | 支持沙箱/mock 和真实 OpenAI 无缝切换 |
| 2026-05-16 | 评论先审后发 | 高风险内容必须人工兜底 |
| 2026-05-16 | 私信延后 | 一对一私密性 + 线下邀约风险高于评论 |
| 2026-05-16 | 支付延后 | 需支付牌照和法律合规，当前不是 MVP 必要项 |

---

*本文档为路线图参考，会随项目进展更新。所有功能需经安全评审后方可实施。*