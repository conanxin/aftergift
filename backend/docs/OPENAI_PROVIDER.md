# OPENAI_PROVIDER.md — Aftergift OpenAI Moderation Provider 沙箱

> 版本：Phase 2E-4 | 更新：2026-05-16

---

## 1. 设计目标

在接入真实 OpenAI Moderation API 之前，建立一个安全的沙箱实现：

1. **默认不启用**：只有显式配置后才调用真实 API
2. **输入脱敏**：用户原文在发送给 OpenAI 前必须经过 Phase 2E-3 脱敏
3. **结果合并**：OpenAI 不覆盖身份泄露检测，必须与 Mock 结果合并
4. **错误兜底**：任何 API 失败自动 fallback 到 Mock，不崩溃服务
5. **零额外依赖**：使用 Python 标准库 `urllib`，不引入 `openai` SDK

---

## 2. 启用条件

必须**同时满足**以下三个条件：

| 条件 | 环境变量 | 要求 |
|------|----------|------|
| Provider 指定 | `AFTERGIFT_MODERATION_PROVIDER=openai` | 必须为 `openai` |
| 安全开关 | `AFTERGIFT_ENABLE_REAL_AI_REVIEW=true` | 必须为 `true` |
| API Key | `OPENAI_API_KEY=sk-...` | 非空、非占位符 |

**任一条件不满足 → 自动 fallback 到 MockModerationProvider**

---

## 3. 环境变量

```bash
# Provider 选择
AFTERGIFT_MODERATION_PROVIDER=openai

# 安全开关（必须 true 才调用真实 API）
AFTERGIFT_ENABLE_REAL_AI_REVIEW=true

# OpenAI API Key（不要提交到 git）
OPENAI_API_KEY=sk-your-real-key-here

# Moderation 模型（默认 omni-moderation-latest）
AFTERGIFT_OPENAI_MODERATION_MODEL=omni-moderation-latest

# HTTP 超时（秒，默认 8）
AFTERGIFT_OPENAI_TIMEOUT_SECONDS=8
```

---

## 4. 输入脱敏

在调用 OpenAI API 前，自动执行以下脱敏：

```python
from app.services.anonymize_service import redact_sensitive_text

redacted_short = redact_sensitive_text(short_story)
redacted_full = redact_sensitive_text(full_story)
input_text = f"{redacted_short}\n{redacted_full}"
```

**脱敏类型**：
- 手机号 → `[手机号已隐藏]`
- 邮箱 → `[邮箱已隐藏]`
- 微信/QQ/社交账号 → `[社交账号已隐藏]`
- 详细地址 → `[地点信息已隐藏]`
- 姓名暴露模式 → `[姓名已隐藏]`

**目的**：防止用户敏感信息通过第三方 API 泄露。

---

## 5. 分类映射

OpenAI Moderation API 返回的 `categories` 映射到 Aftergift `risk_level`：

| OpenAI 分类 | Aftergift risk_level | 说明 |
|-------------|----------------------|------|
| `hate`, `hate/threatening` | `high_risk` | 仇恨言论 |
| `harassment`, `harassment/threatening` | `high_risk` | 骚扰/威胁 |
| `violence`, `violence/graphic` | `high_risk` | 暴力内容 |
| `self-harm`, `self-harm/intent`, `self-harm/instructions` | `high_risk` | 自残内容 |
| `sexual/minors` | `high_risk` | 未成年人相关 |
| `sexual` | `caution` | 成人内容 |
| `flagged=false` + 无上述分类 | `safe` | 安全 |

**注意**：OpenAI Moderation **不检测**身份泄露（手机号、姓名、地址），因此必须与 Mock 结果合并。

---

## 6. 错误 Fallback

| 错误类型 | 处理方式 | 日志 |
|----------|----------|------|
| 网络错误 (URLError) | fallback mock | `warning` |
| 超时 (socket.timeout) | fallback mock | `warning` |
| 401/403 | fallback mock | `warning` + auth error |
| 429 | fallback mock | `warning` + rate limit |
| 5xx | fallback mock | `warning` |
| JSON 解析错误 | fallback mock | `warning` |
| 任何未捕获异常 | fallback mock | `warning` |

**保证**：`POST /api/gifts` 和 `/api/review/mock` 永远不会因 OpenAI API 问题而崩溃。

---

## 7. 合并策略

```
OpenAI result  +  Mock result  →  Merged result
```

| 字段 | 合并规则 |
|------|----------|
| `risk_level` | 取更高者（safe < caution < high_risk） |
| `issues` | 合并两个列表 |
| `suggestions` | 合并两个列表 |
| `quality_notes` | 合并 dict，标记 `local_rules_applied=true` |
| `overall_score` | 取更低者（更保守） |
| `provider` | `"openai+mock"` |
| `raw` | 仅保存 `flagged` + `model` 摘要，不存完整响应 |

---

## 8. 测试策略

所有测试**不调用真实外网**，使用 `unittest.mock.patch`：

```python
with patch("app.services.moderation.openai_provider.urlopen") as mock_urlopen:
    mock_urlopen.return_value = _mock_response({"flagged": False, ...})
    result = provider.review("test", "")
```

测试覆盖：
1. 未启用时 fallback mock
2. Key 为空时 fallback mock
3. 输入脱敏验证
4. flagged=false → safe/caution
5. flagged=true + hate → high_risk
6. 429 → fallback
7. 网络错误 → fallback
8. 结果不含原始敏感值
9. 结果结构完整
10. 合并后保留 Mock 的 identity issues
11. 完整流程（启用 + mock API）

---

## 9. 安全边界

1. **不存储 raw 响应**：`ModerationResult.raw` 仅保存摘要（`flagged` + `model`）
2. **不记录 API Key**：日志中绝不出现 `sk-` 前缀内容
3. **脱敏后发送**：未经脱敏的原文不会离开本机
4. **超时保护**：默认 8 秒超时，防止挂起
5. **默认关闭**：新部署默认 `ENABLE_REAL_AI_REVIEW=false`

---

## 10. 未来生产化要求

在正式启用真实 OpenAI API 前，还需：

1. **Rate Limiting**：限制每分钟/每小时调用次数
2. **缓存**：相同内容的审核结果缓存 1 小时
3. **成本监控**：记录每次调用的 token 消耗（估算）
4. **A/B 测试**：逐步放量，对比 OpenAI 与 Mock 的审核质量
5. **告警**：API 错误率 > 5% 时通知管理员
6. **Key Rotation**：支持多 key 轮询，单 key 失效自动切换

---

## 11. 文件位置

```
backend/backend/app/services/moderation/openai_provider.py   # 核心实现
backend/tests/test_openai_provider.py                         # 测试集
backend/docs/OPENAI_PROVIDER.md                               # 本文档
```

---

*文档创建：Phase 2E-4（2026-05-16）*
