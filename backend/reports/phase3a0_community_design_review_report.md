# Phase 3A-0：社区功能设计评审 — 阶段报告

**STATUS**: ✅ PASS | ALL VALIDATION PASSED

**日期**: 2026-05-16
**BASELINE_COMMIT**: `96ce8fb` — Add local drafts management view (Phase 2M)

---

## 目标

为 Aftergift 社区功能（评论、私信）建立完整的安全边界文档、审核流程设计、API 草案和实施计划。本阶段**不实现任何代码**，仅设计评审。

---

## 新增文档

### 1. COMMENTS_POLICY.md
评论政策文档，定义：
- 评论系统目标（温和回应，非审判/曝光工具）
- 允许的评论（感谢/共情/询问礼物状态/分享经历/祝福）
- 禁止的评论（身份攻击/真实身份暴露/骚扰/交易绕行/自伤威胁/审判关系对象）
- 灰区评论（情绪倾向/身份追问/私下联系暗示/地域相关/高频雷同）
- 评论可见性规则（先审后发/风险分级/发布者控制/管理员操作）
- 评论语气建议（短句/温和/共情但不追问）
- 与现有 review_logs 体系的关系

### 2. COMMENT_REVIEW_WORKFLOW.md
评论审核工作流文档，定义：
- 评论提交流程（静态规则 → AI moderation → risk_level → 状态分流）
- 风险等级（safe/caution/high_risk/blocked）
- 审核维度（身份泄露/骚扰/报复/交易绕行/自伤风险/暴力威胁）
- 与现有 review_logs / redaction 体系的关系
- Admin 审核台需新增的内容（评论队列/详情/操作/上下文）
- 发布者控制（隐藏/关闭评论/举报）
- 评论数据表草案（不创建 migration）
- 状态流转图

### 3. COMMENTS_API_DESIGN.md
评论 API 设计草案，包含：
- 设计原则（先审后发/不支持公开联系方式/匿名优先）
- 数据表草案（comments/comment_review_logs/comment_reports）
- 8 个 API 端点设计（POST/GET/Admin 操作）
- 评论状态流转图
- 评论频率限制（每人每礼物1条/每小时10条/每IP每小时20条）
- 敏感信息检测规则（静态正则 + AI 第二道检测）
- 明确说明不创建 migration，仅设计文档

### 4. ANONYMOUS_MESSAGING_DESIGN_REVIEW.md
匿名私信设计评审文档，定义：
- 为什么私信风险更高（一对一私密性/关系不对等/交易纠纷/真实身份交换/线下邀约）
- 不建议直接开放自由私信的原因
- 推荐方案：模板化匿名中继（双方匿名/模板化/中继/可追溯/可阻断）
- 允许的开场模板（5种安全模板 + 50字补充）
- 禁止的模板选项（身份追问/联系方式索要/关系审判/线下邀约/情感勒索/威胁/交易绕行）
- 安全机制（双方同意/频率限制/一键屏蔽/举报入口/不允许联系方式/AI审核/管理员复审）
- 私信状态流转
- 私信数据表草案（conversations/messages/conversation_reports/conversation_blocks）
- 私信 API 草案（7个端点）
- 私信与评论的对比表

### 5. ABUSE_PREVENTION.md
滥用预防与威胁模型文档，定义：
- 8种威胁模型（前任曝光/人肉搜索/情绪攻击/骚扰/交易诈骗/自伤表达/暴力威胁/绕过审核）
- 7层防护体系（前端提示/静态规则/AI moderation/人工审核/举报/屏蔽/速率限制/日志脱敏）
- 敏感信息类型（身份信息/可追踪信息/关系信息）
- 高风险行为处理（身份泄露/情绪攻击/骚扰/线下跟踪威胁/自伤表达/交易绕行）
- 与 Aftergift 产品定位的关系

### 6. PHASE3A_PLAN.md
Phase 3A 实施计划，包含：
- Phase 3A-0（当前）：设计评审 ✅
- Phase 3A-1：评论数据模型与 Migration（需用户确认）
- Phase 3A-2：评论审核引擎
- Phase 3A-3：Admin 评论队列
- Phase 3A-4：前端温和评论 UI
- Phase 3A-5：举报与隐藏评论
- Phase 3A-6：匿名中继私信设计二次评审（延后）
- Phase 3B 延后建议（私信风险高于评论）

### 7. 后端文档更新
- `backend/docs/COMMUNITY_READINESS.md`：新增 Phase 3A-0 文档索引
- `docs/NEXT_STEPS.md`：新增 Phase 3A-0 行项目
- `README.md`：更新 Phase 表格，新增 Phase 3A-0 完成状态

---

## 修改文件

| 文件 | 改动 |
|------|------|
| `backend/docs/COMMUNITY_READINESS.md` | 更新"下一步建议" + 新增"Phase 3A-0 新增文档索引"章节 |
| `docs/NEXT_STEPS.md` | 新增 Phase 3A-0 行项目 |
| `README.md` | 更新 Phase 表格（补全 Phase 2K-2/2L-1/2L-2/2L-2.1/2M，新增 Phase 3A-0） |

---

## 验证结果

```
node --check frontend/app.js          ✅ EXIT:0
node --check frontend/api-client.js   ✅ EXIT:0
python3 -m json.tool gifts.json      ✅ EXIT:0

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
```

---

## 安全扫描

```
aftergift_dev.db   ← 已在 .gitignore ✅
__pycache__/       ← 已在 .gitignore ✅
No .env files      ✅
No API keys found  ✅
```

---

## BASELINE_COMMIT

`96ce8fb` — Add local drafts management view (Phase 2M)

## TARGET_COMMIT

（本阶段修改待提交推送）

---

## 后续推荐阶段

**Phase 3A-1：评论数据模型与 Migration**（需用户确认后开始）
- 创建 comments / comment_review_logs / comment_reports 表
- 实现基础 CRUD API
- 实现频率限制和静态规则检查

**Phase 3B-0：私信功能二次评审**（延后，建议评论系统稳定运行 3 个月后评估）

---

*本文档为设计评审文档，不构成产品承诺。所有功能需经安全评审后方可实施。*