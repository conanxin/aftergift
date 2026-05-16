# AUTH_DESIGN.md — Aftergift Phase 2E-1 认证设计

> 版本：Phase 2E-1 | 更新日期：2026-05-16

## 1. Phase 2D → Phase 2E-1 升级说明

Phase 2D 使用自定义 HMAC token（`af2d_` 前缀 + base64url HMAC-SHA256），Phase 2E-1 已升级为行业标准 **PyJWT HS256**。

**升级原因**：
- HMAC token 无标准 JWT 声明（`exp`/`iat`/`jti`/`iss`）
- 无法被标准 JWT 库验证
- 不利于未来与第三方身份提供商集成
- Phase 2E-2 Moderation Provider 抽象需要标准 JWT payload 格式

**升级内容**：
- `PyJWT>=2....` 替换原有 HMAC 签名逻辑
- Token payload 增加 `sub/role/jti/iat/exp/token_version`
- 保留匿名身份设计（不收集手机号/邮箱）
- 保留 localStorage 存储（开发期临时方案）

## 2. 为什么仍是匿名身份

Aftergift 处理关系结束后难以面对的礼物，用户对隐私极度敏感：
- 不要求真实手机号 / 邮箱
- 不做 OAuth 第三方登录
- Phase 2E-2 之后才评估第三方 OAuth 可行性
- 减少数据收集，降低平台隐私合规成本

## 3. 认证流程

### 3.1 创建匿名身份

```
POST /api/auth/anonymous
```

**响应**（201）：
```json
{
  "code": 201,
  "data": {
    "user_id": "user-46f9b6e927e8",
    "anonymous_nickname": "匿名整理者 0216",
    "access_token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyL...lg",
    "token_type": "Bearer",
    "expires_in": 604800
  }
}
```

**Token 生成规则**：
- `user_id`：`user-{uuid4前12位}`
- `anonymous_nickname`：`匿名整理者 {NNNN}`，NNNN 为 4 位随机数
- `access_token`：PyJWT HS256，payload 包含 `sub/role/jti/iat/exp/token_version`

### 3.2 验证身份

```
GET /api/auth/me
Authorization: Bearer ***
```

**响应**（200）：
```json
{
  "code": 200,
  "data": {
    "user_id": "user-46f9b6e927e8",
    "anonymous_nickname": "匿名整理者 0216",
    "role": "user",
    "token_version": 1
  }
}
```

**响应**（401，缺少 Authorization）：
```json
{"detail": {"code": 401, "message": "缺少身份凭证，请先创建匿名身份", "data": null}}
```

**响应**（401，Token 过期）：
```json
{"detail": {"code": 401, "message": "身份凭证已过期，请重新创建匿名身份", "data": null}}
```

**响应**（403，Token 无效/签名错误）：
```json
{"detail": {"code": 403, "message": "身份凭证无效", "data": null}}
```

## 4. Token Payload 结构

| Claim | 类型 | 说明 |
|-------|------|------|
| `sub` | string | 用户 ID，即 `user-{uuid12}` |
| `nickname` | string | 匿名昵称，如 `匿名整理者 0421` |
| `role` | string | 角色，`user`（当前仅此角色） |
| `jti` | string | JWT ID（UUID），用于 token 撤销 |
| `iat` | int | 签发时间（Unix timestamp） |
| `exp` | int | 过期时间（Unix timestamp，iat + 604800） |
| `token_version` | int | token 版本号（未来用于强制刷新） |

**Token 类型**：`Bearer`
**TTL**：604800 秒 = 7 天

## 5. 401 vs 403 语义

| 场景 | HTTP 状态码 | 说明 |
|------|------------|------|
| 缺少 `Authorization` 头 | 401 | 未认证 |
| `Authorization` 非 Bearer 格式 | 401 | 格式异常 |
| Token 已过期（`exp` 过期） | 401 | 凭证过期 |
| Token 格式正确但签名错误 | 403 | 凭证无效 |
| Token 签名正确但用户不存在/已停用 | 403 | 无权访问 |
| Token jti 已在撤销表中 | 401 | 凭证已撤销 |

## 6. 前端 token 管理（api-client.js）

```javascript
getStoredToken()   // localStorage['aftergift_token']
storeToken(token)  // localStorage['aftergift_token'] = token
clearStoredToken() // delete localStorage['aftergift_token']
authHeader(token)  // { Authorization: 'Bearer ' + token }
```

**localStorage 仍是临时开发方案**：
- Phase 3A 会升级为 HttpOnly cookie（防 XSS）
- 当前 localStorage 仅存 token，不存真实身份
- JWT 本身不包含可读的个人信息

## 7. 未来计划：token revoke / logout / refresh

Phase 2E-2（Moderation Provider）完成后，可继续做：

1. **`POST /api/auth/logout`**：将 token jti 写入 `revoked_tokens` 表
2. **Token 版本号**：当用户修改密码或主动注销时，`token_version` 递增，旧 token 全部失效
3. **Refresh token**：长期会话场景下引入 refresh token rotation

当前 Phase 2E-1 **未实现** revoke/logout/refresh 功能。

## 8. 数据库表

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
| token_hash | TEXT NOT NULL | JWT token jti（哈希存储） |
| created_at | TEXT | 创建时间 |
| expires_at | TEXT | 过期时间 |

---

*文档版本：Phase 2E-1 | 更新日期：2026-05-16*
