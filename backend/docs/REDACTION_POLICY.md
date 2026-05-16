# REDACTION_POLICY.md — Aftergift 审核日志脱敏策略

> 版本：Phase 2E-3 | 更新：2026-05-16

---

## 1. 为什么需要审核日志脱敏

Aftergift 处理的是关系结束后难以面对的礼物和故事。用户在情绪激动时，可能在故事中留下：
- 前任的姓名、手机号、微信号
- 共同居住地址、公司名
- 报复性表达

这些内容如果未经处理就存入审核日志（review_logs），会带来以下风险：
1. **隐私泄露**：管理员、未来开发者、数据库备份都可能接触到敏感信息
2. **法律风险**：存储他人个人信息可能违反数据保护法规
3. **平台滥用**：如果数据库泄露，这些故事会成为网暴素材

**原则：review_logs 中不应长期保存未经处理的敏感原文。**

---

## 2. 三层数据区分

| 层级 | 内容 | 是否脱敏 | 用途 |
|------|------|----------|------|
| **用户原文** | short_story / full_story | ❌ 不脱敏 | gift_stories 表，供用户自己查看和修改 |
| **审核正文** | short_story / full_story | ❌ 不脱敏 | Admin 审核队列，供人工审核参考 |
| **审核日志** | issues / suggestions / evidence | ✅ 必须脱敏 | review_logs 表，长期保存的审计记录 |
| **API 响应** | review_result | ✅ 脱敏后返回 | 前端展示、第三方调用 |

**关键区分**：
- 管理员需要看 **原文** 才能做出正确判断 → gift_stories 保留原文
- 审计日志只需要知道 **发现了什么问题** → review_logs 存脱敏版本

---

## 3. 脱敏类型

| 类型 | 检测模式 | 替换为 | 示例 |
|------|----------|--------|------|
| **phone** | 1[3-9]\d{9} | [手机号已隐藏] | 13800138000 → [手机号已隐藏] |
| **email** | \w+@\w+\.\w+ | [邮箱已隐藏] | test@example.com → [邮箱已隐藏] |
| **wechat** | 微信号/微信/WX... | [社交账号已隐藏] | 微信号：wx_123 → 微信号：[社交账号已隐藏] |
| **qq** | QQ[：:]\d{5,} | [社交账号已隐藏] | QQ：123456 → QQ：[社交账号已隐藏] |
| **social** | 微博/抖音/小红书... | [社交账号已隐藏] | 微博@username → [社交账号已隐藏] |
| **address** | 小区/栋/号楼/单元... | [地点信息已隐藏] | 某某小区3号楼 → 某某[地点信息已隐藏] |
| **name_pattern** | 他叫/她叫/TA叫... | [姓名已隐藏] | 他叫张三 → 他叫[姓名已隐藏] |

---

## 4. review_logs 脱敏策略

### 4.1 写入前脱敏

在 `gifts.py` 的 `create_gift()` 中，review_result 在写入 review_logs 前经过以下处理：

```python
# 1. 脱敏 issues evidence
for issue in review_result["issues"]:
    issue["original"] = redact_sensitive_text(issue["original"])

# 2. 脱敏 suggestions
for suggestion in review_result["suggestions"]:
    suggestion["original"] = redact_sensitive_text(suggestion["original"])
    suggestion["message"] = redact_sensitive_text(suggestion["message"])
    suggestion["replacement"] = redact_sensitive_text(suggestion["replacement"])

# 3. 生成脱敏摘要
redaction_summary = summarize_redactions(original, redacted)

# 4. 写入 review_logs.suggestions_json
{
    "suggestions": [脱敏后的建议列表],
    "redaction_summary": {"redacted": true, "redaction_count": 3, "categories": ["phone", "name_pattern"]}
}
```

### 4.2 不存储的字段

- ❌ 原始手机号、邮箱、微信号
- ❌ 原始姓名
- ❌ 原始地址
- ❌ 原始社交账号

### 4.3 存储的字段

- ✅ risk_level（safe/caution/high_risk）
- ✅ issues category + severity（不含原始值）
- ✅ suggestions type + message（脱敏后）
- ✅ quality_notes（故事质量评估，不含个人信息）
- ✅ redaction_summary（脱敏操作记录）
- ✅ provider（mock/openai/baidu）

---

## 5. Admin 审核队列脱敏策略

### 5.1 保留原文的部分

Admin 需要看原文才能判断故事是否合规：
- `short_story` — 来自 gift_stories（原文）
- `full_story` — 来自 gift_stories（原文）

### 5.2 脱敏的部分

Admin 看到的审核辅助信息已脱敏：
- `review_suggestions` — 来自 review_logs.suggestions_json（已脱敏）
- `review_issues` — 来自 review_logs（已脱敏）
- `redaction_summary` — 显示哪些类型被脱敏

### 5.3 Admin 接口新增字段

```json
{
  "gift_id": "...",
  "short_story": "他叫[姓名已隐藏]...",      // ← 原文（供审核）
  "full_story": "...",                       // ← 原文（供审核）
  "review_suggestions": [
    {"type": "手机号", "message": "[手机号已隐藏]"}
  ],
  "redaction_summary": {
    "redacted": true,
    "redaction_count": 2,
    "categories": ["phone", "name_pattern"]
  }
}
```

---

## 6. redaction_summary 格式

```json
{
  "redacted": true,
  "redaction_count": 3,
  "categories": ["phone", "email", "name_pattern"]
}
```

**设计原则**：
- 只记录 **类型** 和 **数量**，不记录原始值
- 便于统计：今天脱敏了多少手机号？
- 便于审计：哪些故事触发了脱敏？

---

## 7. 当前限制

1. **正则匹配不完美**：
   - 地址模式可能误匹配 "号是13800138000"（已修复：要求含数字或特定关键词）
   - 姓名模式只匹配 "他叫张三"，不匹配 "张三是个好人"
   - 复杂上下文中的敏感信息可能漏检

2. **不处理图片/音频**：
   - 只处理文本
   - 图片中的文字、语音转文字不在当前范围内

3. **不自动修改用户原文**：
   - gift_stories 中的 short_story / full_story 保持原样
   - 只脱敏审核日志和 API 响应

4. **中文语境为主**：
   - 英文姓名、外文地址检测较弱

---

## 8. 未来真实 AI Provider 接入时的要求

当 Phase 2E-4 接入 OpenAI Moderation API 时：

1. **发送前脱敏**：
   - 调用外部 API 前，先对输入文本进行脱敏
   - 不发送原始手机号、姓名、地址给第三方

2. **响应后脱敏**：
   - OpenAI 返回的 flagged categories 映射到 Aftergift 的 risk_level
   - 如果 OpenAI 返回了具体触发文本，也要脱敏后再存储

3. **raw 字段处理**：
   - `ModerationResult.raw` 包含完整 API 响应
   - **不持久化**到 review_logs（内存中调试用）
   - 如需记录，只记录分类和分数，不记录原始文本片段

4. **成本与隐私平衡**：
   - 先走 mock 过滤明显违规内容
   - 只有 mock 无法判断时才调用 OpenAI
   - 缓存相同内容的审核结果

---

## 9. 文件清单

```
backend/backend/app/services/anonymize_service.py    ← 脱敏核心函数
backend/backend/app/routers/gifts.py                 ← 写入 review_logs 前脱敏
backend/backend/app/routers/admin.py                 ← Admin 队列解析 redaction_summary
backend/tests/test_redaction.py                      ← 脱敏测试
backend/docs/REDACTION_POLICY.md                     ← 本文档
```

---

*最后更新：Phase 2E-3 完成后（2026-05-16）。*
