# Aftergift 阶段性成果总结

**Phase Closeout — 2026-05-16**
**BASELINE_COMMIT**: `b15add7` — Add community design review docs (Phase 3A-0)

---

## 1. 项目目标

帮助用户在关系结束、变化或疏远后，以更体面的方式处理带有情感记忆的旧礼物——通过讲述故事、温和流转，让每件礼物都能找到下一个归处。

**不是**：普通二手平台、报复工具、曝光平台、情感审判场所。

**是**：故事型礼物流转平台，聚焦物品本身和讲述者的感受。

---

## 2. 阶段完成摘要

### Phase 1：静态原型（完成）
- HTML/CSS/JS 单页 Web App
- 8+ 虚构礼物故事卡片
- 故事流筛选（出售/交换/赠送/捐出/只展示）
- 发布表单 + 安全提示
- 本地草稿原型（JS localStorage）

### Phase 2A-E：后端 MVP 基础（完成）
- FastAPI + SQLite 骨架
- 匿名 JWT 身份（无需绑定真实手机/邮箱）
- 礼物 CRUD API（发布/浏览/详情/编辑）
- 搜索 API + 我的发布/收藏
- OpenAI Moderation Provider 抽象（沙箱可用）
- 敏感信息自动检测（redaction 体系）

### Phase 2F：Admin 增强（完成）
- Admin JWT 认证
- 举报队列
- 审核操作历史（review_logs）
- Admin 增强：分页、排序、按状态筛选、批量操作

### Phase 2G-I：体验完善（完成）
- Discovery API（精选故事流）
- 收藏 API（toggle favoriting，收藏数排序）
- 我的空间（?view=me）：发布管理 + 统计卡片 + 操作历史
- 本地草稿管理（?view=drafts）：30 天过期提示、恢复编辑、删除确认

### Phase 3A-0：社区治理设计（完成）
- 评论政策（允许/禁止/灰区）
- 评论审核工作流（4 级风险/6 维审核/先审后发）
- 评论 API 设计草案
- 匿名中继私信设计评审
- 滥用预防与威胁模型（8 种威胁/7 层防护）
- Phase 3A 实施计划

---

## 3. 当前可演示能力

| 功能 | 演示方式 | 状态 |
|------|----------|------|
| 浏览礼物故事流 | `http://127.0.0.1:8080/` | ✅ 静态模式可用 |
| 筛选礼物（类型/情绪/关系）| 首页筛选按钮 | ✅ 静态模式可用 |
| 搜索礼物 | 搜索框 | ✅ 静态模式可用 |
| 查看礼物详情 | 点击卡片 | ✅ 静态模式可用 |
| 发布礼物故事 | 发布表单 | ⚠️ 需 API 模式 |
| 匿名身份 | 自动创建 | ⚠️ 需 API 模式 |
| 收藏故事 | 详情 Modal | ⚠️ 需 API 模式 |
| 我的收藏 | `?view=favorites` | ⚠️ 需 API 模式 |
| 我的发布管理 | `?view=me` | ⚠️ 需 API 模式 |
| 本地草稿管理 | `?view=drafts` | ✅ 纯前端功能 |
| Admin 审核 | `?api=local&admin=1` | ⚠️ 需 API 模式 |
| AI 审核（沙箱） | 自动触发 | ⚠️ 需 API 模式 |

---

## 4. 当前不可用能力

| 功能 | 原因 |
|------|------|
| 真实支付/物流 | 未实现 |
| 公开评论 | Phase 3A-0 设计 ✅，实现待定 |
| 私信 | 延后（风险高于评论）|
| 服务器端草稿同步 | 仅 localStorage |
| 服务器端收藏持久化 | 仅 localStorage |
| 移动端 App | 延后 |
| 高并发支持 | SQLite 写锁限制 |

---

## 5. 技术栈

| 层 | 技术 |
|----|------|
| 前端 | 原生 HTML/CSS/JS，无框架，无 CDN 依赖 |
| 后端 | Python 3.10+ / FastAPI / uvicorn |
| 数据库 | SQLite（本地/内测）/ PostgreSQL（生产，待迁）|
| 认证 | PyJWT（匿名身份 + Admin）|
| 审核 | OpenAI Moderation API（Provider 抽象，沙箱默认 mock）|
| 测试 | pytest（13 个测试文件，约 150 项）|

---

## 6. 测试基线

```
后端测试（13/13）：全部 150/150 PASS ✅

test_favorites_api           15/15 PASS
test_my_gifts                 12/12 PASS
test_my_actions_and_restore   12/12 PASS
test_auth_jwt                 12/12 PASS
test_schema                    7/7  PASS
test_discovery_api            18/18 PASS
test_my_gift_management       14/14 PASS
test_search_api               12/12 PASS
test_migrations                4/4  PASS
test_admin_enhancements       11/11 PASS
test_redaction                11/11 PASS
test_moderation_provider      11/11 PASS
test_openai_provider          11/11 PASS
```

---

## 7. 已知风险

| 风险 | 级别 | 缓解措施 |
|------|------|----------|
| SQLite 写锁（高并发）| 中 | Phase 5 迁 PostgreSQL |
| AI 审核误判 | 中 | 人工审核兜底 |
| 匿名身份丢失 | 低 | 内测阶段不要频繁清除 localStorage |
| Admin token 泄露 | 高 | 生产必须替换 |
| JWT secret 泄露 | 高 | 生产必须替换 |
| 评论开放后骚扰 | 高 | Phase 3A 设计含完整审核流 |
| 礼物故事隐私泄露 | 中 | redaction 体系 + 内容政策 |

---

## 8. 下一步建议

### 立即推荐：Phase 3A-1（需用户确认）
评论数据模型 + Migration

- 创建 comments / comment_review_logs / comment_reports 表
- 实现基础 CRUD API（先审后发）
- 实现评论频率限制和静态规则检查

### 后续：Phase 3B 延后评估
建议等评论系统稳定运行 3 个月后再评估匿名中继私信。

### 更远期
Phase 4（交易/交换撮合）需支付牌照和法律合规评估，当前不建议推进。

---

## 9. 项目里程碑

| 日期 | 事件 |
|------|------|
| 2026-04-14 | 项目启动，Phase 1 静态原型完成 |
| 2026-04-17 | Phase 2A-E 后端 MVP 完成 |
| 2026-04-22 | Phase 2F Admin 增强完成 |
| 2026-04-25 | Phase 2G-I 体验完善完成 |
| 2026-05-16 | Phase 2M 本地草稿管理完成 |
| 2026-05-16 | Phase 3A-0 社区设计评审完成 |
| **2026-05-16** | **Phase Closeout — Local Beta Milestone** |

---

*本文档为阶段性总结，不构成产品承诺。*