# 安全与隐私说明

> Aftergift Phase 2 后端 MVP | 版本：1.0

---

## 1. 核心原则

1. **不存明文**：手机号、邮箱、地址、姓名一律 HASH 存储，不可逆
2. **匿名优先**：所有故事默认匿名展示，发布者不暴露真实身份
3. **留痕可查**：所有管理员操作和审核决策记录不可删除
4. **防御纵深**：后端必须防护 XSS、SQL 注入、爬虫、恶意举报

---

## 2. 数据安全

### 2.1 用户身份

| 数据 | 存储方式 | 说明 |
|------|---------|------|
| 手机号 | SHA-256 HASH | 不存明文，不可逆 |
| 邮箱 | SHA-256 HASH | 不存明文，不可逆 |
| 真实姓名 | 禁止存储 | 故事中也不允许出现真实姓名 |
| 地址 | 禁止存储 | 故事中只允许城市名 |
| IP 地址 | HASH | 用于防恶意举报，不展示 |

**实现示例**：
```python
import hashlib

def hash_phone(phone: str) -> str:
    return hashlib.sha256(phone.strip().encode()).hexdigest()

# 存储时
phone_hash = hash_phone("13812345678")
# 数据库只存："a1b2c3d4e5f6..."
```

### 2.2 故事内容

- 故事存储在 `gift_stories.full_story`，完整明文
- `gift_stories.risk_level` 标记风险等级
- 高风险故事（high_risk）在发布前必须经过人工复审

### 2.3 收藏数据

- `favorites` 表只存 user_id + gift_id 关联
- 同一用户对同一礼物只能有一条收藏记录（UNIQUE 约束）

---

## 3. 后端安全措施

### 3.1 必须防护的攻击

| 攻击类型 | 防护方案 |
|---------|---------|
| **XSS** | 所有用户输入在输出时做 HTML 转义；故事内容展示时强制转义 |
| **SQL 注入** | 使用参数化查询（SQLAlchemy ORM）；禁止拼接 SQL |
| **批量爬取** | API rate limit：每 IP 每分钟最多 60 请求 |
| **恶意举报** | 同一 IP 24h 内举报超过 10 次触发验证码 |
| **暴力枚举用户** | 用户 ID 使用 UUID，不顺序自增 |
| **暴力枚举礼物** | 礼物 ID 使用 UUID，不顺序自增 |

### 3.2 API Rate Limit

| 端点 | 限制 |
|------|------|
| GET /api/gifts | 每 IP 60 次/分钟 |
| POST /api/gifts | 每 IP 10 次/分钟 |
| POST /api/gifts/{id}/report | 每 IP 10 次/小时 |
| POST /api/gifts/{id}/favorite | 每 IP 30 次/分钟 |
| 管理员 API | 每管理员 120 次/分钟 |

### 3.3 管理员安全

- 管理员账号与普通用户分离（`users.is_admin` 字段）
- 管理员操作记录到 `admin_actions` 表，不可删除
- 管理员操作需二次验证（TODO：TOTP）
- 管理员不可查看用户明文手机号或 IP

---

## 4. 隐私保护

### 4.1 匿名展示

所有公开的礼物列表和详情，发布者信息只显示：
- `anonymous_nickname`（如「安静的旧物收藏者 #4827」）
- 不显示 user_id、phone_hash、真实姓名、IP

### 4.2 禁止的数据

以下内容在故事中被明确禁止：
- 真实姓名（全名或姓氏+名）
- 手机号（11 位数字）
- 微信号、QQ 号、邮箱地址
- 详细地址（小区/楼栋/门牌号）
- 照片（含他人照片）

### 4.3 数据保留

| 数据类型 | 保留期限 |
|---------|---------|
| 审核日志（review_logs）| 永久 |
| 管理员操作日志（admin_actions）| 永久 |
| 被拒绝的故事 | 6 个月后删除 |
| 已归档的故事 | 用户可申请删除 |
| 举报记录 | 2 年后匿名化 |

---

## 5. 真实支付合规（Phase 4）

> 当前 Phase 2 不涉及真实支付，以下为 Phase 4 的合规注意事项。

1. **支付牌照**：接入微信/支付宝支付需有相应资质
2. **资金托管**：平台不出入金，只做担保，由支付机构托管
3. **KYC**：大额交易需用户完成实名认证（可接入支付宝/微信 KYC）
4. **反洗钱**：交易记录保留 5 年供监管查询
5. **未成年人**：禁止 18 岁以下用户发布交易类礼物

---

## 6. 安全开发规范

### 6.1 输入验证

所有 API 请求必须验证：
```python
# 示例（伪代码）
def validate_gift_input(data):
    assert "title" in data and 1 <= len(data["title"]) <= 50
    assert "short_story" in data and 1 <= len(data["short_story"]) <= 100
    assert "action_type" in data and data["action_type"] in VALID_ACTIONS
    # 手机号/微信号等在审核层检测，不在 API 层拒绝
```

### 6.2 输出转义

所有 HTML 输出必须转义：
```python
import html

def esc(s: str) -> str:
    return html.escape(s, quote=True)
```

### 6.3 错误处理

- 不向用户暴露内部错误详情（如数据库异常、堆栈）
- 所有 API 错误返回统一格式：`{"code": N, "message": "..."}`
- 敏感操作（如删除）需要确认 token

---

## 7. 安全检查清单

- [ ] 手机号/邮箱只存 HASH
- [ ] 用户 ID 使用 UUID，不顺序自增
- [ ] 所有 HTML 输出转义
- [ ] SQL 查询使用参数化
- [ ] API 有 rate limit
- [ ] 管理员操作留痕
- [ ] 审核日志不可删除
- [ ] 故事禁止真实姓名/电话/地址
- [ ] 高风险故事必须人工复审
- [ ] 举报有防刷机制

---

*最后更新：Phase 2A 完成时生成。*