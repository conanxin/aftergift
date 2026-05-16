# Aftergift Phase 2E-4 — OpenAI Provider Sandbox Report

STATUS: COMPLETE

PROJECT_DIR:
~/projects/aftergift/

OPENAI_PROVIDER:
OpenAIModerationProvider 已实现沙箱逻辑，使用 Python 标准库 urllib，不引入 openai SDK。

ENABLEMENT_RULES:
真实 OpenAI 调用只有在以下条件同时满足时启用：
1. AFTERGIFT_MODERATION_PROVIDER=openai
2. AFTERGIFT_ENABLE_REAL_AI_REVIEW=true
3. OPENAI_API_KEY 非空且非占位符

REDACTION_BEFORE_SEND:
发送到 OpenAI 前会先调用 redact_sensitive_text() 对 short_story / full_story 进行脱敏。

RISK_MAPPING:
OpenAI moderation categories 会映射到 Aftergift risk_level。
hate / harassment / violence / self-harm / sexual/minors 等类别会提升为 high_risk 或 caution。

FALLBACK:
网络错误、401/403、429、5xx、JSON parse error、response schema error 均 fallback 到 MockModerationProvider，不让 API 崩溃。

TEST_RESULTS:
- test_redaction.py: 11/11 PASS
- test_moderation_provider.py: 11/11 PASS
- test_auth_jwt.py: 12/12 PASS
- test_schema.py: 7/7 PASS
- test_openai_provider.py: 11/11 PASS
- total: 52/52 PASS

SECURITY_SCAN:
.env.example 中 OPENAI_API_KEY 与 BAIDU_CONTENT_REVIEW_API_KEY 已清空（0 asterisks）。
无真实 OpenAI/Baidu API key。
无 .env / .venv / db 残留（aftergift_dev.db 为开发数据库，aftergift_test.db 已清理）。

DOCS_UPDATED:
- backend/docs/MODERATION_PROVIDER.md
- backend/docs/OPENAI_PROVIDER.md
- backend/docs/PHASE2_PLAN.md
- docs/NEXT_STEPS.md

RISKS_REMAINING:
1. 真实 OpenAI API 成本与限流风险。
2. 外部 API 响应格式未来可能变化。
3. OpenAI moderation 不覆盖所有身份泄露风险，仍需 Mock 本地规则兜底。
4. 当前默认仍为 mock，不代表生产审核已完成。

NEXT_RECOMMENDED_PHASE:
Phase 2F — Admin 审核台增强：筛选、排序、分页、举报队列、review_logs 查看、admin_actions 历史。
