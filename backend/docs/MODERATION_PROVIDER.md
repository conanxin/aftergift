# MODERATION_PROVIDER.md — Aftergift 审核 Provider 架构

> 版本：Phase 2E-2 | 更新：2026-05-16

---

## 1. 设计目标

Aftergift 的内容审核需要满足以下要求：

1. **可切换**：mock（本地规则）/ OpenAI（云端 API）/ 百度（国内 API）可自由切换
2. **安全兜底**：任何外部 API 不可用时，自动 fallback 到 mock，不导致服务崩溃
3. **向后兼容**：`review_service.mock_review()` 接口不变，不影响现有 router 和测试
4. **不默认启用外部 API**：开发环境默认 mock，真实 API 需显式开启
5. **无 API key 泄露**：key 通过环境变量读取，不写入代码或文档

---

## 2. 架构图

```
┌─────────────────────────────────────────────┐
│  review_service.mock_review()               │  ← 对外接口（不变）
│  review_service.review_story()              │  ← 新接口（推荐）
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  get_moderation_provider()                  │  ← factory.py
│  - 读取 MODERATION_PROVIDER env             │
│  - 检查 ENABLE_REAL_AI_REVIEW               │
│  - 检查 API key 是否存在                    │
│  - fallback 到 mock 如果条件不满足          │
└──────────────┬──────────────────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Mock      │  │   OpenAI    │  │    Baidu    │
│  Provider   │  │  Skeleton   │  │  Skeleton   │
│  (default)  │  │  (fallback) │  │  (fallback) │
└─────────────┘  └─────────────┘  └─────────────┘
```

---

## 3. Provider 说明

### 3.1 MockModerationProvider（默认）

- **文件**：`services/moderation/mock_provider.py`
- **逻辑**：本地正则规则 + 关键词检测
- **检测项**：
  - 身份信息泄露（姓名、手机号、地址、公司、社交账号）
  - 攻击/报复表达（曝光、报复、渣男、渣女等）
  - 可识别关系对象（具体人名 + 关系描述）
  - 故事质量（字数、来源、意义、告别原因、期望）
- **输出**：`risk_level` (safe/caution/high_risk) + `issues` + `suggestions` + `quality_notes`
- **provider 字段**：`"mock"`

### 3.2 OpenAIModerationProvider（骨架）

- **文件**：`services/moderation/openai_provider.py`
- **当前状态**：SKELETON，不调用真实 API
- **fallback 条件**：
  - `ENABLE_REAL_AI_REVIEW != true`
  - `OPENAI_API_KEY` 未设置
  - 任何异常
- **未来实现（Phase 2E-4）**：
  - 调用 OpenAI Moderation API
  - 映射 OpenAI 分类到 Aftergift risk_level
- **provider 字段**：`"openai"`

### 3.3 BaiduModerationProvider（骨架）

- **文件**：`services/moderation/baidu_provider.py`
- **当前状态**：SKELETON，不调用真实 API
- **fallback 条件**：同 OpenAI
- **未来实现**：调用百度内容审核 API
- **provider 字段**：`"baidu"`

---

## 4. 环境变量配置

```bash
# .env.example（已包含）

# Provider 选择：mock | openai | baidu
AFTERGIFT_MODERATION_PROVIDER=mock

# 是否启用真实 AI 审核（安全开关）
AFTERGIFT_ENABLE_REAL_AI_REVIEW=false

# OpenAI API Key（仅 provider=openai 时需要）
OPENAI_API_KEY=

# 百度内容审核 API Key（仅 provider=baidu 时需要）
BAIDU_CONTENT_REVIEW_API_KEY=
```

### Fallback 规则

| MODERATION_PROVIDER | ENABLE_REAL_AI_REVIEW | API Key | 实际使用 |
|---------------------|----------------------|---------|----------|
| mock | 任意 | 任意 | mock ✅ |
| openai | false | 任意 | mock（安全开关关闭） |
| openai | true | 空 | mock（key 缺失） |
| openai | true | 有 | openai（Phase 2E-4） |
| baidu | true | 有 | baidu（未来） |
| unknown | 任意 | 任意 | mock |

---

## 5. 输出格式

### ModerationResult（dataclass）

```python
@dataclass
class ModerationResult:
    risk_level: str          # "safe" | "caution" | "high_risk"
    issues: List[Dict]       # [{"category", "severity", "message", ...}]
    suggestions: List[Dict]  # [{"type", "message", "replacement"}]
    quality_notes: Dict      # {"word_count": {...}, "has_origin": {...}, ...}
    overall_score: int       # 0-100
    provider: str            # "mock" | "openai" | "baidu"
    raw: Optional[Dict]      # 原始 API 响应（调试用）
```

### to_dict() 输出（API 返回格式）

```json
{
  "risk_level": "caution",
  "issues": [
    {
      "category": "identity",
      "severity": "medium",
      "message": "包含可能泄露身份的信息",
      "evidence": "详细地址"
    }
  ],
  "suggestions": [
    {
      "type": "anonymize",
      "message": "建议删除详细地址信息，仅保留城市名",
      "replacement": "[城市名]"
    }
  ],
  "quality_notes": {
    "word_count": {"ok": true, "message": "字数已达到基本要求"},
    "has_origin": {"ok": false, "message": "可以补充一下礼物最初是怎么来到你手上的"}
  },
  "overall_score": 65,
  "provider": "mock"
}
```

---

## 6. 与 review_logs 表的映射

| ModerationResult 字段 | review_logs 字段 | 说明 |
|-----------------------|------------------|------|
| `risk_level` | `risk_level` | 直接写入 |
| `issues` (identity) | `identity_risk` | severity 或 "none" |
| `issues` (attack) | `attack_risk` | severity 或 "none" |
| `issues` (identifiable_person) | `identifiable_person_risk` | severity 或 "none" |
| `quality_notes` | `quality_notes` | str() 序列化 |
| `suggestions` | `suggestions_json` | str() 序列化 |
| `provider` | `reviewer_type` | mock→ai_rule_engine, openai/baidu→ai_moderation_api |

---

## 7. 安全要求（未来接入真实 API 时）

1. **API Key 管理**：
   - 绝不写入代码、文档、git
   - 仅通过环境变量或 secrets manager 读取
   - 生产环境使用 rotate key

2. **数据隐私**：
   - 发送给外部 API 前进行脱敏（Phase 2E-3）
   - 不发送用户 ID、手机号等关联信息
   - 保留原始内容仅在本地

3. **成本控制**：
   - 设置 rate limit
   - 缓存相同内容的审核结果
   - 监控 API 调用量

4. **可用性**：
   - 外部 API 超时后自动 fallback mock
   - 记录 fallback 事件到日志

---

## 8. Phase 2E-3 增强：审核日志脱敏

Phase 2E-3 在 provider 输出进入 review_logs 前增加了自动脱敏：

1. **issues evidence 脱敏**：`issue["original"]` 中的手机号、姓名、地址等被替换为占位符
2. **suggestions 脱敏**：`suggestion["original"]` / `message"` / `replacement"` 全部脱敏
3. **redaction_summary**：记录脱敏类型和数量，不记录原始值
4. **raw 字段**：`ModerationResult.raw` 仅用于内存调试，**不持久化**到 review_logs

详见：`backend/docs/REDACTION_POLICY.md`

---

## 9. 文件清单

```
backend/backend/app/services/moderation/
├── __init__.py          # 包导出
├── base.py              # ModerationProvider 协议 + dataclass
├── mock_provider.py     # 本地规则引擎（默认）
├── openai_provider.py   # OpenAI skeleton
├── baidu_provider.py    # 百度 skeleton
└── factory.py           # Provider 工厂 + fallback 逻辑

backend/backend/app/services/
├── __init__.py          # 包导出（新增）
├── review_service.py    # 包装层（重写）
└── anonymize_service.py # Phase 2E-3 增强：脱敏函数
```

---

*最后更新：Phase 2E-2 完成后（2026-05-16）。*
