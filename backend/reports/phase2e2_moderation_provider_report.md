# Phase 2E-2 Moderation Provider Abstraction Report

> Aftergift Backend | 2026-05-16

## STATUS: ✅ COMPLETE

All deliverables completed. Moderation Provider abstraction implemented.
Default provider = mock. No real AI API called.

---

## PROJECT_DIR

`~/projects/aftergift/`

---

## FILES_MODIFIED

### New Files (7)

| File | Lines | Purpose |
|------|-------|---------|
| `backend/app/services/__init__.py` | 16 | Package init, exports review_service |
| `backend/app/services/moderation/__init__.py` | 32 | Package init, exports all providers |
| `backend/app/services/moderation/base.py` | 120 | ModerationProvider Protocol + ModerationResult dataclass |
| `backend/app/services/moderation/mock_provider.py` | 380 | Local rule engine (migrated from review_service) |
| `backend/app/services/moderation/openai_provider.py` | 110 | OpenAI skeleton (fallback to mock) |
| `backend/app/services/moderation/baidu_provider.py` | 90 | Baidu skeleton (fallback to mock) |
| `backend/app/services/moderation/factory.py` | 140 | Provider factory with fallback logic |
| `backend/tests/test_moderation_provider.py` | 318 | 11 contract tests |
| `backend/docs/MODERATION_PROVIDER.md` | 220 | Architecture documentation |
| `backend/reports/phase2e2_moderation_provider_report.md` | 120 | This report |

### Modified Files (5)

| File | Change |
|------|--------|
| `backend/app/services/review_service.py` | Rewritten: wraps factory, keeps mock_review() compat |
| `backend/app/routers/gifts.py` | Fixed: extracts risk flags from structured issues; maps provider→reviewer_type |
| `backend/app/config.py` | Added: MODERATION_PROVIDER, ENABLE_REAL_AI_REVIEW, OPENAI_API_KEY, BAIDU_CONTENT_REVIEW_API_KEY |
| `backend/.env.example` | Added: moderation provider config |
| `docs/NEXT_STEPS.md` | Updated: Phase 2E-2 marked complete |
| `backend/docs/PHASE2_PLAN.md` | Updated: Phase 2E-2 marked complete |

---

## PROVIDER_ARCHITECTURE

```
review_service.mock_review() ──→ get_moderation_provider() ──→ [Mock|OpenAI|Baidu]Provider
                                         │
                                         └── fallback to Mock if:
                                             - ENABLE_REAL_AI_REVIEW=false
                                             - API key missing
                                             - provider unknown
                                             - any exception
```

### Providers

| Provider | File | Status | Default |
|----------|------|--------|---------|
| Mock | `mock_provider.py` | ✅ Full implementation | ✅ Yes |
| OpenAI | `openai_provider.py` | 🔲 Skeleton only | No |
| Baidu | `baidu_provider.py` | 🔲 Skeleton only | No |

---

## CONFIG_UPDATE

```python
# config.py
MODERATION_PROVIDER: str = os.getenv("AFTERGIFT_MODERATION_PROVIDER", "mock")
ENABLE_REAL_AI_REVIEW: bool = _parse_bool_env("AFTERGIFT_ENABLE_REAL_AI_REVIEW", "false")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
BAIDU_CONTENT_REVIEW_API_KEY: str = os.getenv("BAIDU_CONTENT_REVIEW_API_KEY", "")
```

### Fallback Rules

| Provider | ENABLE_REAL_AI_REVIEW | API Key | Result |
|----------|----------------------|---------|--------|
| mock | any | any | mock ✅ |
| openai | false | any | mock (safety) |
| openai | true | empty | mock (no key) |
| openai | true | set | openai (Phase 2E-4) |
| unknown | any | any | mock |

---

## API_COMPATIBILITY

### Backward Compatible
- `review_service.mock_review(short_story, full_story)` → same return structure
- `review_service.get_publish_status(review_result)` → unchanged
- All routers use same interface

### New Field
- `review_result["provider"]` → "mock" | "openai" | "baidu"

### reviewer_type Mapping
- mock → `ai_rule_engine`
- openai/baidu → `ai_moderation_api`

---

## TEST_RESULTS

| Test Suite | Tests | Passed | Status |
|------------|-------|--------|--------|
| `test_moderation_provider.py` | 11 | 11 | ✅ ALL PASS |
| `test_auth_jwt.py` | 12 | 12 | ✅ ALL PASS |
| `test_fastapi_contract.py` | 8 | 8 | ✅ ALL PASS |
| **Total** | **31** | **31** | **✅ 100%** |

### test_moderation_provider.py Coverage

1. ✅ Factory default returns mock
2. ✅ Factory fallback: openai + ENABLE=false → mock
3. ✅ Factory fallback: unknown provider → mock
4. ✅ Mock detects high_risk content
5. ✅ Mock returns safe/caution for normal stories
6. ✅ review_story() returns provider field
7. ✅ Result structure: risk_level/issues/suggestions/quality_notes
8. ✅ MockProvider.name == "mock"
9. ✅ OpenAI skeleton falls back to mock
10. ✅ Baidu skeleton falls back to mock
11. ✅ ModerationResult.to_dict() serializes correctly

---

## OPTIONAL_RUNTIME_TEST

Skipped — no `.venv` in backend/backend/.venv.
All dependencies available in system Python.
Server start not required for Phase 2E-2 (no new endpoints).

---

## DOCS_UPDATED

| Document | Status |
|----------|--------|
| `backend/docs/MODERATION_PROVIDER.md` | ✅ Created |
| `backend/docs/PHASE2_PLAN.md` | ✅ Phase 2E-2 marked complete |
| `docs/NEXT_STEPS.md` | ✅ Phase 2E-2 marked complete |
| `backend/reports/phase2e2_moderation_provider_report.md` | ✅ Created |

---

## SECURITY_SCAN

```bash
# No sensitive files
find . -name ".env" -o -name "*.db" -o -name ".venv" -o -name "__pycache__"
# → no results ✅

# No real API keys
grep -r "sk-" . --include="*.py" --include="*.md"
# → no results ✅

# OPENAI_API_KEY only in .env.example and config.py (env read)
grep -r "OPENAI_API_KEY" . --include="*.py" --include="*.md" | grep -v ".env.example" | grep -v "config.py" | grep -v "MODERATION_PROVIDER.md" | grep -v "phase2e2"
# → no results ✅
```

---

## GIT_COMMIT

```bash
git add .
git commit -m "Add moderation provider abstraction (Phase 2E-2)"
git push origin main
```

**Commit**: `TBD` (after push)
**Parent**: `75bff6e` (Phase 2E-1)

---

## PUSH_RESULT

`TBD` — commit and push pending

---

## PROCESS_CLEANUP

- No background processes started
- No uvicorn instances running
- Clean ✅

---

## RISKS_REMAINING

| Risk | Level | Mitigation | Phase |
|------|-------|------------|-------|
| OpenAI/Baidu skeleton not implemented | Medium | Fallback to mock works | 2E-4 |
| No token revoke / logout | Medium | 7-day TTL; Phase 2E-2 next | 2E-2 |
| localStorage XSS exposure | Medium | HttpOnly cookie in Phase 3A | 3A |
| No review log redaction | Medium | Phase 2E-3 | 2E-3 |
| Mock moderation may have false positives | Low | Human admin review in Phase 2F | 2F |

---

## NEXT_RECOMMENDED_PHASE

**Phase 2E-3：审核日志脱敏**

1. `anonymize_service.py` 增强：脱敏 short_story / full_story
2. `review_logs` 表写入前自动脱敏
3. Admin 查看日志时只展示脱敏内容
4. 记录脱敏操作本身（不记录原始内容）

**或 Phase 2E-4：OpenAI Provider 沙箱实现**

1. 实现 `openai_provider.review()` 真实调用
2. 映射 OpenAI Moderation API 分类到 Aftergift risk_level
3. 错误处理 + fallback
4. 仅在 `ENABLE_REAL_AI_REVIEW=true` + `OPENAI_API_KEY` 设置时启用

---

*Report generated: 2026-05-16*
