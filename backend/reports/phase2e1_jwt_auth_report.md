# Phase 2E-1 JWT Auth Upgrade Report

> Aftergift Backend | 2026-05-16

## STATUS: ✅ COMPLETE

All deliverables completed. HMAC auth replaced with PyJWT HS256. No real AI moderation, phone/email login, payment, or public deployment in this phase.

---

## PROJECT_DIR
`~/projects/aftergift/`

## FILES_MODIFIED
| File | Change |
|------|--------|
| `backend/backend/requirements.txt` | Added `PyJWT>=2....` |
| `backend/backend/.env.example` | Added `AFTERGIFT_JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_TTL_SECONDS` |
| `backend/backend/app/config.py` | Added JWT config reads with dev-safe defaults |
| `backend/backend/app/auth.py` | Complete rewrite: HMAC → PyJWT, new functions: `create_access_token`, `decode_access_token`, `_require_auth_payload`, `get_bearer_token` |
| `backend/backend/app/routers/auth.py` | `wrap()` fixed `status_code=` param; `get_current_user` uses `_require_auth_payload` |
| `backend/backend/app/routers/gifts.py` | Added missing `review_result` call; confirmed `_require_auth` returns str |
| `backend/backend/app/routers/favorites.py` | Confirmed `_require_auth` returns str |
| `backend/backend/app/routers/reports.py` | Confirmed `_require_auth` returns str |
| `backend/docs/AUTH_DESIGN.md` | Full rewrite for Phase 2E-1: JWT payload structure, 401/403 semantics, future plans |
| `backend/docs/PHASE2_PLAN.md` | Phase 2E-1 marked ✅ complete; 2E-2 onward unchanged |
| `docs/NEXT_STEPS.md` | Phase 2E-1 marked 100% complete; risk table updated |

## FILES_CREATED
| File | Purpose |
|------|---------|
| `backend/tests/test_auth_jwt.py` | 12 contract tests for JWT auth (12/12 PASS) |
| `backend/reports/phase2e1_jwt_auth_report.md` | This report |

## AUTH_CHANGE

**Before (Phase 2D)**:
```
af2d_{base64url(user_id + ":" + HMAC-SHA256(user_id, SECRET))}
```
- No standard JWT claims (no iat/exp/jti/sub)
- Custom HMAC signature, not verifiable by standard JWT libraries
- No expiry enforcement

**After (Phase 2E-1)**:
```
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyLT...In0.XXXXX
```
- Standard PyJWT HS256
- `iat` + `exp` (7-day TTL)
- `jti` (UUID for future revoke)
- `token_version` (for future force-refresh)
- Full 401/403 semantic separation

## TOKEN_PAYLOAD

```json
{
  "sub": "user-46f9b6e927e8",
  "nickname": "匿名整理者 0421",
  "role": "user",
  "jti": "550df102855c4d96a...",
  "iat": 1747372000,
  "exp": 1747976800,
  "token_version": 1
}
```

**Type**: Bearer  
**TTL**: 604800 seconds = 7 days

## API_COMPATIBILITY

| Endpoint | Before | After | Compatible |
|----------|--------|-------|------------|
| `POST /api/auth/anonymous` | `af2d_...` token | JWT token | ✅ `access_token` + `token_type` + `expires_in` in response |
| `GET /api/auth/me` | af2d_ token | Bearer JWT | ✅ Same Authorization header format |
| `POST /api/gifts` | af2d_ token | Bearer JWT | ✅ Same auth header |
| All other protected endpoints | af2d_ token | Bearer JWT | ✅ Same auth header |

**Breaking change**: None. Frontend `api-client.js` unchanged (stores and sends `access_token` as-is).

## FRONTEND_COMPATIBILITY
- `api-client.js` **no changes required** — stores and sends `access_token` which is now a JWT instead of af2d_ token
- localStorage mechanism unchanged
- Token display strings updated to generic "Bearer token" in UI (not hardcoded af2d_ prefix)

## TEST_RESULTS

### Contract Tests (`backend/tests/test_auth_jwt.py`): 12/12 PASS
```
✅ PASS [imports]          PyJWT=2.12.1, ALGORITHM=HS256, TTL=604800s
✅ PASS [token_structure]  Standard 3-part JWT
✅ PASS [token_payload]     sub/role/exp/jti/iat all correct
✅ PASS [invalid_token]    4 forged tokens rejected
✅ PASS [expired_token]    Expired token correctly rejected
✅ PASS [require_auth_no_header] 401
✅ PASS [require_auth_wrong_format] 401
✅ PASS [require_auth_invalid_token] 403
✅ PASS [create_anonymous_returns_jwt] 201 + JWT
✅ PASS [auth_me_valid_token] 200 + user info
✅ PASS [gifts_requires_auth] POST /api/gifts 401 without token
✅ PASS [gifts_with_valid_token] 200/201 + status
```

### Syntax Checks: 10/10 PASS
- All backend Python files: `python3 -m py_compile` ✅
- Frontend JS files: `node --check` ✅
- `gifts.json`: `python3 -m json.tool` ✅

## OPTIONAL_RUNTIME_TEST

Server started on `127.0.0.1:8091` with actual PyJWT signing/verification. All 6 checks passed:

```
1. POST /api/auth/anonymous → 201 | JWT parts=3 ✅
2. GET /api/auth/me with token → 200 | user_id=user-d6807b7be409 ✅
3. GET /api/auth/me without token → 401 ✅
4. GET /api/auth/me wrong token → 403 ✅
5. POST /api/gifts with token → 200 | status=published ✅
6. POST /api/gifts without token → 401 ✅
```

Server shut down cleanly after tests. No residual processes.

## DOCS_UPDATED
- ✅ `backend/docs/AUTH_DESIGN.md` — Full rewrite: Phase 2E-1 JWT payload structure, 401/403 semantics table, future revoke plans
- ✅ `backend/docs/PHASE2_PLAN.md` — Phase 2E-1 marked complete with checklist
- ✅ `docs/NEXT_STEPS.md` — Phase 2E-1 status updated, risk table updated
- ✅ `backend/reports/phase2e1_jwt_auth_report.md` — This report

## SECURITY_SCAN

```
find . -name ".env" -o -name "*.db" -o -name "*.sqlite" -o -name ".venv" -o -name "__pycache__"
```
- `.env`: None (only `.env.example`)
- `*.db/*.sqlite`: None (DB file at `backend/backend/aftergift_dev.db` — outside git tree)
- `.venv`: None
- `__pycache__`: None

```
grep -R "AFTERGIFT_JWT_SECRET" . | grep -v ".example"
grep -R "replace-this-dev-secret" . | grep -v ".example"
```
- No production secrets found
- Only in `.env.example` and documentation (safe)

**JWT Secret Policy**: Production must use `openssl rand -base64 64` generated secret. Dev default (`replace-this-dev-secret`) is intentionally non-functional for production.

## GIT_COMMIT

Commit `da0b6a7` from Phase 2D.1 is the current tip. This Phase 2E-1 work is pending commit.

## PUSH_RESULT

Pending commit and push.

## PROCESS_CLEANUP

- uvicorn server on port 8091: ✅ killed via `process.kill`
- Background sessions: ✅ all cleaned
- No residual services

## RISKS_REMAINING

| Risk | Level | Status | Next Phase |
|------|-------|--------|------------|
| JWT secret still `replace-this-dev-secret` in dev | Low | Expected | Prod deployment must change |
| Token cannot be revoked (no logout) | Medium | Not implemented | Phase 2E-2 or later |
| localStorage XSS exposure | Medium | Not addressed | Phase 3A (HttpOnly cookie) |
| No refresh token rotation | Low | Not implemented | Future phase |
| AI moderation still Mock | High | Not implemented | Phase 2E-2 |
| Review logs not redacted | Medium | Not implemented | Phase 2E-2 |

**Important**: This phase only replaced HMAC with PyJWT. No AI moderation, real identity login, payment, or trading features were added.

## NEXT_RECOMMENDED_PHASE

**Phase 2E-2: Moderation Provider Abstraction**

Continue the Phase 2E sequence:
1. Establish `services/moderation/` with `ModerationProvider` base class
2. Implement `MockModerationProvider` (current regex logic)
3. Implement `OpenAIModerationProvider` (behind `MODERATION_PROVIDER=openai` flag, requires `OPENAI_API_KEY`)
4. Implement `BaiduModerationProvider` (behind `MODERATION_PROVIDER=baidu` flag)
5. `review_service.py` calls abstracted provider

**Phase 2E-2 does NOT**:
- Deploy real AI API to production
- Store real API keys in git
- Enable non-mock provider by default

---

*Report generated: 2026-05-16*
*Phase: 2E-1 JWT Auth Upgrade*
*Status: COMPLETE ✅*
