# Aftergift Database Migrations

## 为什么需要 Migration

Aftergift 使用 SQLite 作为开发数据库。随着功能迭代，schema 会新增列、表或索引。Migration 确保：

1. **旧数据库可以安全升级**，不丢失数据。
2. **新数据库初始化后自动标记已应用的 migration**，避免重复执行。
3. **Migration 可重复运行**（幂等），不会报错。

---

## Migration 列表

### 002: Add user_actions table

**文件：** `backend/migrations/002_add_user_actions.sql`

**目的：** 创建 `user_actions` 表，记录普通用户对礼物的操作历史（编辑、重新提交、归档、恢复）。

**影响：**
- Phase 2H-2 用户操作历史功能依赖此表。
- 与 `admin_actions` 表区分：admin_actions 记录管理员行为，user_actions 记录普通用户行为。

**Schema：**
```sql
CREATE TABLE IF NOT EXISTS user_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    gift_id TEXT,
    action TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (gift_id) REFERENCES gifts(id) ON DELETE SET NULL
);
```

---

### 001: Add review_logs.redaction_summary

**文件：** `backend/migrations/001_add_review_logs_redaction_summary.sql`

**目的：** 为 `review_logs` 表增加 `redaction_summary` TEXT 列，用于存储结构化脱敏元数据。

**影响：**
- Phase 2F Admin 审核台需要此列展示脱敏信息。
- 旧数据库（Phase 2F 之前）缺少此列，必须运行 migration。

---

## 如何运行 Migration

### 方式一：直接运行 migration runner

```bash
cd backend/backend
python scripts/migrate_db.py
```

输出示例：
```
Aftergift Database Migration Runner
Database: /home/ubuntu/projects/aftergift/backend/backend/aftergift_dev.db
Migrations dir: /home/ubuntu/projects/aftergift/migrations
--------------------------------------------------
  applied: 001_add_review_logs_redaction_summary
  applied: 002_add_user_actions
--------------------------------------------------
Migration complete.
```

再次运行：
```
  skipped (already recorded): 001_add_review_logs_redaction_summary
  skipped (already recorded): 002_add_user_actions
```

### 方式二：通过 init_db.py 自动运行

```bash
cd backend/backend
python scripts/init_db.py
```

新库初始化后会自动运行所有 pending migrations。

---

## init_db.py 与 migrate_db.py 的关系

| 脚本 | 用途 | 是否删除数据 |
|------|------|------------|
| `init_db.py` | 全新初始化数据库（schema + seed + migration） | 是（drop_existing=True） |
| `migrate_db.py` | 对现有数据库应用 migrations | 否 |

**开发流程：**
1. 全新环境 → 运行 `init_db.py`
2. 已有数据的环境 → 运行 `migrate_db.py`

---

## 旧数据库升级说明

如果你有一个 Phase 2F 之前的数据库：

```bash
cd backend/backend
# 备份旧数据库
cp aftergift_dev.db aftergift_dev.db.backup

# 运行 migration
python scripts/migrate_db.py
```

Migration runner 会自动：
1. 检查 `review_logs` 是否已有 `redaction_summary` 列。
2. 如果没有，执行 `ALTER TABLE`。
3. 记录到 `schema_migrations` 表。

---

## 添加新 Migration

1. 在 `backend/migrations/` 创建新的 `.sql` 文件。
2. 在 `backend/backend/scripts/migrate_db.py` 的 `MIGRATIONS` 列表中注册。
3. 提供 `check_column` 用于幂等性检查（如适用）。
4. 运行 `migrate_db.py` 测试。

---

## 注意事项

- **不要提交 `.db` 文件**到 Git。
- **不要手动修改 `schema_migrations` 表**。
- Migration SQL 文件只包含 `ALTER TABLE` 等增量操作，不包含完整 schema。
