# 内容审核工作流

> Aftergift Phase 2 后端 MVP | 版本：1.0

---

## 1. 设计原则

1. **故事优先**：审核的目的是帮助用户安全地讲故事，而不是阻止用户发布
2. **分级处理**：不同风险等级的故事走不同的处理路径
3. **留痕可查**：所有审核操作不可删除，用于合规审计
4. **人工兜底**：AI 审核不确定的案例，最终由人工判断

---

## 2. 风险等级定义

| 等级 | 标识 | 定义 | 处理路径 |
|------|------|------|---------|
| 低风险 | `safe` | 无身份信息，无攻击性表达，故事完整度合格 | 直接发布 |
| 中风险 | `caution` | 有轻微可识别信息，或故事完整度不足 | 返回修改建议，用户修改后重新提交 |
| 高风险 | `high_risk` | 直接暴露真实身份，或有明确的报复/攻击内容 | 进入人工复审队列 |

---

## 3. 审核状态流转

```
用户提交（POST /api/gifts）
   │
   ▼
┌─────────────────────────┐
│   服务端基础规则预检     │  ← 同步，毫秒级
│   （Phase 1 的正则规则） │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│   AI 审核层              │  ← 异步，2-3 秒
│   （Phase 2 接入 API）   │
└──────────┬──────────────┘
           │
    ┌──────┴──────┐
    ▼              ▼
 safe          caution/high_risk
    │              │
    ▼              ▼
 published    进入人工复审队列
              ┌──────────┐
              │ 管理员   │
              │ 人工复审  │
              └────┬─────┘
                   │
          ┌────────┼────────┐
          ▼        ▼        ▼
      approve   needs_edit  reject
          │        │         │
          ▼        ▼         ▼
      published  用户收到   用户收到
                修改建议   拒绝通知
                          （可申诉）
```

---

## 4. 文本流程图

### 4.1 普通发布流程（无风险内容）

```
[用户] ──POST /api/gifts──▶ [API Server]
                              │
                              ▼
                    ┌───────────────────┐
                    │  1. 规则基础预检   │
                    │  （同步，毫秒级）   │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │  2. 写入 gifts     │
                    │  status=draft     │
                    │  写入 gift_stories │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │  3. AI 审核       │
                    │  （异步，2-3 秒）  │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │  risk_level=safe  │
                    │  → 写入 review_log │
                    │  → status=published│
                    └─────────┬─────────┘
                              │
                              ▼
                      [返回用户: 已发布]
```

### 4.2 高风险内容流程

```
[用户] ──POST /api/gifts──▶ [API Server]
                              │
                              ▼
                    [基础预检] → risk_level=high_risk
                              │
                              ▼
                    ┌───────────────────┐
                    │  status=pending   │
                    │  review_log=high  │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │  进入人工复审队列  │
                    │  Telegram Bot     │
                    │  通知管理员       │
                    └─────────┬─────────┘
                              │
                    [管理员 Web 后台]
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              [人工复审: approve]  [人工复审: reject]
                    │                   │
                    ▼                   ▼
              status=published    用户收到拒绝通知
                              │
                         [用户可申诉]
```

### 4.3 举报处理流程

```
[任意用户] ──POST /api/gifts/{id}/report──▶ [API Server]
                                               │
                                               ▼
                                    ┌──────────────────┐
                                    │  写入 reports    │
                                    │  status=pending  │
                                    │  gift status     │
                                    │  → hidden       │
                                    └────────┬─────────┘
                                             │
                                    [Telegram Bot]
                                    通知管理员
                                             │
                                    [管理员 Web 后台]
                                             │
                         ┌───────────────────┴────────────────┐
                         ▼                                   ▼
              [审核: dismiss]                    [审核: take_action]
                         │                                   │
                         ▼                                   ▼
                   故事恢复可见                    故事保持下架
                   举报者无通知                    通知举报者已处理
```

---

## 5. AI 审核层设计

### 5.1 规则引擎（Phase 2A，Mock）

Phase 2A 的 `mock_api/mock_review.py` 实现纯本地正则规则，与前端 Phase 1D 的规则保持一致：
- 身份信息检测（手机/微信/QQ/邮箱/地址）
- 攻击性表达检测（渣男/诅咒/侮辱）
- 可识别关系对象检测（"TA叫XXX"格式）

### 5.2 AI Moderation API（Phase 2B+）

Phase 2B 后接入真实 AI 审核：

```python
# 方案 A：OpenAI Moderation API（免费，简单）
import openai
response = openai.Moderation.create(input=full_story)
if response["results"][0]["flagged"]:
    risk_level = "high_risk"
else:
    risk_level = "safe"

# 方案 B：百度文本审核（中文优化，付费）
# https://ai.baidu.com/ai-doc/ANTIPORN/3k3fjhkh1
```

### 5.3 多级审核决策

| AI 审核结果 | 最终 risk_level | 处理 |
|-------------|----------------|------|
| 无 flag | safe | 直接发布 |
| 轻微 flag | caution | 返回修改建议 |
| 明确 flag | high_risk | 人工复审 |
| 严重 flag（暴力/儿童） | high_risk + 立即下架 | 人工复审 + 安全告警 |

---

## 6. 审核日志

所有审核操作记录到 `review_logs` 表，字段包括：

- gift_id
- risk_level（AI 审核结果）
- identity_risk / attack_risk / identifiable_person_risk（0-3 评分）
- quality_notes（JSON，故事质量建议）
- suggestions_json（JSON，匿名化建议）
- reviewer_type（ai_rule_engine / ai_moderation_api / human_admin）
- decision（approve/reject/needs_edit）
- decided_by（管理员 ID）
- decided_at

**不可删除**，用于：
- 合规审计
- 用户申诉参考
- 产品优化分析

---

## 7. 申诉机制

用户收到 `rejected` 决定后，可提交申诉：

```
[用户] ──POST /api/gifts/{id}/appeal──▶ [管理员复审]
                                              │
                                    [重新评估 + 决定]
                                              │
                              ┌───────────────┴───────────────┐
                              ▼                               ▼
                    [申诉通过: approve]          [申诉驳回: reject]
                              │                               │
                              ▼                               ▼
                      故事发布                        用户收到最终结果
```

---

*最后更新：Phase 2A 完成时生成。*