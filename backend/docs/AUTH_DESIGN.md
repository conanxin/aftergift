# AUTH_DESIGN.md — Aftergift Phase 2D 匿名认证设计

## 1. Phase 2D 目标

在不收集用户真实手机号、邮箱的前提下，为每个匿名用户提供唯一身份标识，
使所有用户操作（发布礼物、收藏、举报）可被关联至同一身份，同时防止未登录用户访问受保护接口。

## 2. 为什么不用真实手机号 / 邮箱

- Aftergift 处理的是关系结束后难以面对的礼物，用户对隐私极度敏感
- 真实身份会破坏产品的"匿名叙述"核心价值
- 减少数据收集，降低平台责任和隐私合规成本
- Phase 2E 考虑接入第三方 OAuth，但非强制

## 3. 认证流程

### 3.1 创建匿名身份

```
POST /api/auth/anonymous
```

**请求体**（可选）：可传入 `device_id`（设备指纹）用于去重

**响应**（201）：
```json
{
  "code": 200,
  "data": {
    "user_id": "user-46f9b6e927e8",
    "anonymous_nickname": "匿名整理者 0216",
    "access_token": "af2d_dXNlci00NmY5YjZlOTI3ZTg6..."
  }
}
```

**生成规则**：
- `user_id`：`user-{uuid4前12位}`
- `anonymous_nickname`：`匿名整理者 {NNN}`，NNNN 为 4 位随机数
- `access_token`：长度 89 字符，格式 `af2d_{base64(user_id:hmac_sha256(user_id, SECRET))}`

**存储**：
- `users` 表：id, anonymous_nickname, created_at, last_active
- `sessions` 表：id, user_id, token(HASH), created_at, expires_at

### 3.2 验证身份

```
GET /api/auth/me
Authorization: Bearer <access_token>
```

**响应**（200）：
```json
{
  "code": 200,
  "data": {
    "user_id": "user-46f9b6e927e8",
    "anonymous_nickname": "匿名整理者 0216",
    "status": "active",
    "created_at": "2026-05-16 06:57:45"
  }
}
```

**响应**（401，缺少凭证）：
```json
{"detail": {"code": 401, "message": "缺少身份凭证，请先创建匿名身份", "data": null}}
```

**响应**（401，Token 无效或已过期）：
```json
{"detail": {"code": 401, "message": "身份凭证无效或已过期，请重新创建匿名身份", "data": null}}
```

## 4. 401 vs 403 语义

- **401 Unauthorized**：缺少 Authorization 头，或 Token 格式/签名不合法
- **403 Forbidden**：Token 格式正确但无权访问特定资源（暂未使用）

## 5. Token 安全细节

- **前缀**：`af2d_`，便于识别和过滤
- **不透明**：Token 本身不含用户身份明文，需要 HMAC 验证才能解析
- **TTL**：7 天（`sessions.expires_at`）
- **存储**：前端 `localStorage`（可被 XSS 读取），仅存储 token 而非真实身份
- **风险**：localStorage XSS → 攻击者可冒用该身份发布内容。缓解：内容审核队列。

## 6. 当前不是生产 JWT

Phase 2D Token = HMAC-SHA256 签名，非标准 JWT（无 iat/exp/jti 声明）。
未来 Phase 2E 升级路径：

```
当前（Phase 2D）：
  af2d_{base64(user_id:HMAC-SHA256(user_id, SECRET))}

未来（Phase 2E，可选）：
  Bearer eyJhbGciOiJIUzI1NiJ9...  ← PyJWT RS256/HS256
  + Redis token blacklist
  + refresh token rotation
```

## 7. 受保护接口列表

| 接口 | 保护方式 |
|------|---------|
| `POST /api/gifts` | Bearer Token |
| `POST /api/gifts/{id}/favorite` | Bearer Token |
| `DELETE /api/gifts/{id}/favorite` | Bearer Token |
| `POST /api/gifts/{id}/report` | Bearer Token |
| `GET /api/admin/reviews` | x-admin-token |
| `POST /api/admin/reviews/{id}/decision` | x-admin-token |

## 8. 前端 token 管理（api-client.js）

```javascript
getStoredToken()   // localStorage['aftergift_token']
storeToken(token)  // localStorage['aftergift_token'] = token
clearStoredToken() // delete localStorage['aftergift_token']
authHeader(token)  // { Authorization: 'Bearer ' + token }
```

## 9. 数据库表

### users
| 列 | 类型 | 说明 |
|----|------|------|
| id | TEXT PRIMARY KEY | user-{uuid12} |
| anonymous_nickname | TEXT NOT NULL | 显示名 |
| created_at | TEXT | ISO 时间 |
| last_active | TEXT | 最近活跃时间 |

### sessions
| 列 | 类型 | 说明 |
|----|------|------|
| id | TEXT PRIMARY KEY | uuid |
| user_id | TEXT NOT NULL | FK → users.id |
| token | TEXT NOT NULL | HASH(af2d_...) |
| created_at | TEXT | 创建时间 |
| expires_at | TEXT | 过期时间 |

---

*文档版本：Phase 2D | 更新日期：2026-05-16*
