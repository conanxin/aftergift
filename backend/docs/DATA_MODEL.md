# 数据模型设计

> Aftergift Phase 2 后端 MVP | 版本：1.0

---

## 1. 概览

本数据模型基于 SQLite 设计，支持 PostgreSQL 迁移（Phase 2C+）。

**设计原则**：
- 用户身份匿名化：手机号/邮箱存 HASH，不存明文
- 故事优先：gift_stories 独立表，支持长文本和审核元数据
- 审核留痕：review_logs 不可删除，用于合规审计
- 灵活状态机：gift.status 和 report.status 使用有限状态机

---

## 2. 表结构

### 2.1 users（用户表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | UUID v4 |
| anonymous_nickname | TEXT NOT NULL | 系统生成的随机昵称（如「安静的旧物收藏者 #4827」）|
| phone_hash | TEXT | 手机号 SHA-256 HASH（可选，用于跨设备同步）|
| email_hash | TEXT | 邮箱 SHA-256 HASH（可选）|
| created_at | TEXT DEFAULT (datetime('now')) | 创建时间 |
| status | TEXT CHECK(status IN ('active', 'suspended', 'deleted')) | 用户状态 |

**索引**：
- `idx_users_phone_hash` ON (phone_hash)
- `idx_users_status` ON (status)

**说明**：
- phone_hash 和 email_hash 都是可选的
- 不存真实手机号或邮箱，只存 HASH
- HASH 使用 SHA-256，不可逆

---

### 2.2 gifts（礼物表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | UUID v4 |
| user_id | TEXT NOT NULL | 外键 → users.id |
| title | TEXT NOT NULL | 礼物名称 |
| category | TEXT NOT NULL | 礼物类型（家居装饰/文具/数码/配饰/书籍/玩具摆件/健康/其他）|
| relation_type | TEXT | 关系类型（前任/挚友/夫妻/家人/同事/恩师/其他），可空 |
| relation_label | TEXT | 关系显示标签（同 relation_type，但可被 anonymous 覆盖）|
| action_type | TEXT NOT NULL | 处理方式（sell/exchange/giveaway/donate/keep）|
| emotion | TEXT NOT NULL | 情绪标签（放下/遗憾/感谢/释怀/重启/纪念/治愈/平静）|
| price_or_exchange | TEXT | 价格或交换意向 |
| condition_note | TEXT | 物品状态备注（如：九成新/有使用痕迹/全新未拆封）|
| city_blur | TEXT | 城市模糊（仅城市名，不含具体地址）|
| is_anonymous | INTEGER DEFAULT 1 | 是否匿名发布（1=yes, 0=no）|
| status | TEXT NOT NULL | 状态（见下）|
| created_at | TEXT DEFAULT (datetime('now')) | 创建时间 |
| updated_at | TEXT DEFAULT (datetime('now')) | 更新时间 |

**gift.status CHECK 约束**：
```
CHECK(status IN (
  'draft',          -- 用户草稿，未提交
  'pending_review', -- 审核中
  'published',      -- 已发布，公开
  'needs_edit',     -- 需要用户修改
  'rejected',       -- 被拒绝
  'archived'        -- 已归档（下架或用户删除）
))
```

**索引**：
- `idx_gifts_user_id` ON (user_id)
- `idx_gifts_status` ON (status)
- `idx_gifts_action_type` ON (action_type)
- `idx_gifts_created_at` ON (created_at DESC)

---

### 2.3 gift_stories（故事表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | UUID v4 |
| gift_id | TEXT NOT NULL | 外键 → gifts.id，唯一（每件礼物一个故事）|
| short_story | TEXT NOT NULL | 一句话故事（100 字以内）|
| full_story | TEXT NOT NULL | 完整故事（600-2000 字）|
| story_quality_score | REAL | 质量评分（0.0-1.0，AI 生成）|
| risk_level | TEXT NOT NULL | 风险等级（见下）|
| created_at | TEXT DEFAULT (datetime('now')) | 创建时间 |

**risk_level CHECK 约束**：
```
CHECK(risk_level IN ('safe', 'caution', 'high_risk'))
```

**索引**：
- `idx_stories_gift_id` ON (gift_id) UNIQUE
- `idx_stories_risk_level` ON (risk_level)

---

### 2.4 review_logs（审核记录表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | UUID v4 |
| gift_id | TEXT NOT NULL | 外键 → gifts.id |
| risk_level | TEXT NOT NULL | AI 审核风险等级（safe/caution/high_risk）|
| identity_risk | INTEGER | 身份信息风险：0=无，1=低，2=中，3=高 |
| attack_risk | INTEGER | 攻击性表达风险：0=无，1=低，2=中，3=高 |
| identifiable_person_risk | INTEGER | 可识别关系对象风险：0=无，1=低，2=中，3=高 |
| quality_notes | TEXT | 故事质量备注（JSON 格式）|
| suggestions_json | TEXT | 匿名化建议（JSON 格式）|
| reviewer_type | TEXT NOT NULL | 审核类型：ai_rule_engine / ai_moderation_api / human_admin |
| decision | TEXT | 最终决定：approve / reject / needs_edit（可为 null，表示待审核）|
| decided_by | TEXT | 人工审核人员 ID（仅 human_admin 时有效）|
| decided_at | TEXT | 审核决定时间 |
| created_at | TEXT DEFAULT (datetime('now')) | 记录创建时间 |

**索引**：
- `idx_reviews_gift_id` ON (gift_id)
- `idx_reviews_risk_level` ON (risk_level)
- `idx_reviews_reviewer_type` ON (reviewer_type)

**说明**：
- 审核日志不可删除，用于合规审计
- 每次故事状态变化（如提交审核、人工复审）都生成新记录
- suggestions_json 和 quality_notes 存储 JSON 字符串

---

### 2.5 favorites（收藏表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | UUID v4 |
| user_id | TEXT NOT NULL | 外键 → users.id |
| gift_id | TEXT NOT NULL | 外键 → gifts.id |
| created_at | TEXT DEFAULT (datetime('now')) | 收藏时间 |

**约束**：
- UNIQUE(user_id, gift_id)：同一用户对同一礼物只能收藏一次

**索引**：
- `idx_favorites_user_id` ON (user_id)
- `idx_favorites_gift_id` ON (gift_id)

---

### 2.6 reports（举报表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | UUID v4 |
| gift_id | TEXT NOT NULL | 外键 → gifts.id |
| reporter_user_id | TEXT | 举报者用户 ID（可空，匿名举报）|
| reporter_ip_hash | TEXT | 举报者 IP HASH（可空，用于防恶意举报）|
| reason | TEXT NOT NULL | 举报原因（曝光隐私/攻击性内容/虚假信息/其他）|
| detail | TEXT | 详细描述（可选）|
| status | TEXT NOT NULL | 处理状态（见下）|
| assigned_admin_id | TEXT | 处理的管理员 ID |
| resolution_note | TEXT | 处理备注 |
| created_at | TEXT DEFAULT (datetime('now')) | 举报时间 |
| resolved_at | TEXT | 处理完成时间 |

**report.status CHECK 约束**：
```
CHECK(status IN ('pending', 'reviewing', 'resolved_dismissed', 'resolved_action_taken'))
```

**索引**：
- `idx_reports_gift_id` ON (gift_id)
- `idx_reports_status` ON (status)
- `idx_reports_created_at` ON (created_at DESC)

---

### 2.7 admin_actions（管理员操作记录表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | UUID v4 |
| admin_id | TEXT NOT NULL | 管理员用户 ID → users.id |
| target_type | TEXT NOT NULL | 操作对象类型：gift / report / user |
| target_id | TEXT NOT NULL | 操作对象 ID |
| action | TEXT NOT NULL | 操作类型：approve / reject / needs_edit / suspend_user / dismiss_report / take_action |
| note | TEXT | 操作备注 |
| created_at | TEXT DEFAULT (datetime('now')) | 操作时间 |

**索引**：
- `idx_admin_actions_admin_id` ON (admin_id)
- `idx_admin_actions_target` ON (target_type, target_id)

---

## 3. 关系图（文本）

```
users
  ├── 1:N── gifts              （一个用户可发布多件礼物）
  │         └── 1:1── gift_stories  （每件礼物一个故事）
  │                    └── N:1── review_logs （一个故事多次审核）
  ├── 1:N── favorites           （一个用户可收藏多件礼物）
  │         └── N:1── gifts
  └── 1:N── reports             （一个用户可发起多个举报）
        └── N:1── gifts

gifts
  ├── 1:1── gift_stories
  ├── N:1── users
  ├── 1:N── favorites
  └── 1:N── reports

review_logs
  └── N:1── gifts

admin_actions
  ├── N:1── users (admin_id)
  └── target_type: gift | report | user
```

---

## 4. 状态机

### 4.1 Gift Status Flow

```
用户提交 story
   ↓
draft → pending_review
   ↓
   ├── AI 审核：safe → published
   ├── AI 审核：caution → needs_edit → [用户修改] → pending_review
   └── AI 审核：high_risk → [人工复审]
                    ├── approve → published
                    ├── reject → rejected（通知用户）
                    └── needs_edit → needs_edit → [用户修改] → pending_review

published → archived（用户删除 or 管理员下架）
rejected → needs_edit（用户申诉后重新提交）
```

### 4.2 Report Status Flow

```
用户提交举报
   ↓
pending → reviewing（分配给管理员）
   ↓
   ├── dismissed → resolved_dismissed
   └── action_taken → resolved_action_taken（下架故事 + 通知用户）
```

---

## 5. 迁移注意事项

- 所有 TEXT 类型的主键在 SQLite 中使用 UUID v4
- datetime('now') 在 SQLite 中自动设置当前时间
- INTEGER 类型用于布尔值（is_anonymous）
- HASH 字段使用 SHA-256，在应用层生成，数据库只存结果
- JSON 字段在 SQLite 中存为 TEXT，应用层序列化/反序列化

---

*最后更新：Phase 2A 完成时生成。*