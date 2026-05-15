# Aftergift Backend MVP - FastAPI Skeleton

> Phase 2B | FastAPI 后端框架骨架
> 从 `mock_api/` 轻量 Mock 进入可继续开发的后端结构

---

## 目录结构

```
backend/
├── README.md              # 本文件
├── requirements.txt       # Python 依赖
├── .env.example           # 环境变量模板
├── app/
│   ├── main.py            # FastAPI 入口
│   ├── config.py          # 配置管理
│   ├── database.py        # SQLite 连接层（标准库）
│   ├── models.py          # 枚举 & 常量
│   ├── schemas.py         # Pydantic 模型
│   ├── routers/           # API 路由
│   │   ├── gifts.py
│   │   ├── reviews.py
│   │   ├── favorites.py
│   │   ├── reports.py
│   │   └── admin.py
│   └── services/          # 业务逻辑
│       ├── review_service.py
│       └── anonymize_service.py
├── scripts/
│   ├── init_db.py         # 数据库初始化
│   └── smoke_test.py      # 冒烟测试
└── tests/
    └── test_fastapi_contract.py  # 合同测试
```

---

## 快速启动（开发环境）

### 1. 创建虚拟环境（可选）

```bash
cd ~/projects/aftergift-backend-mvp/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python3 scripts/init_db.py
```

### 3. 启动开发服务器

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8091 --reload
```

### 4. 访问 API 文档

- Swagger UI: http://localhost:8091/docs
- ReDoc: http://localhost:8091/redoc

### 5. 运行冒烟测试

```bash
# 确保 uvicorn 已在 8091 端口运行
python3 scripts/smoke_test.py
```

---

## Phase 2B 已实现

| 功能 | 状态 |
|------|------|
| FastAPI 骨架 + 路由 | ✅ |
| SQLite 标准库连接层 | ✅ |
| Pydantic 请求/响应模型 | ✅ |
| Gift CRUD + 列表/详情 | ✅ |
| Mock AI 审核服务 | ✅ |
| Favorites 接口骨架 | ✅ |
| Reports 接口骨架 | ✅ |
| Admin 审核接口 | ✅ |
| 配置管理（dotenv）| ✅ |
| 数据库初始化脚本 | ✅ |
| 合同测试 | ✅ |

---

## Phase 2B 未实现（后续阶段）

| 功能 | 计划阶段 |
|------|----------|
| 真实用户注册/登录 | Phase 2C |
| 真实 AI 审核 API | Phase 2D |
| PostgreSQL 迁移 | Phase 2C |
| JWT / OAuth2 认证 | Phase 2C |
| 真实支付/物流 | Phase 3 |
| 管理员面板 UI | Phase 2C |

---

## 重要约束

- **不保存真实身份信息**：手机号/邮箱只存 HASH
- **不接真实 AI API**：Phase 2B 只用 mock 规则引擎
- **不启动公网服务**：仅本地开发
- **不删除 mock_api/**：保留作为历史参考

---

## 环境变量说明

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AFTERGIFT_ENV` | development | 运行环境 |
| `AFTERGIFT_DB_PATH` | `./aftergift_dev.db` | 数据库路径 |
| `AFTERGIFT_ENABLE_REAL_AI_REVIEW` | false | 是否启用真实 AI 审核 |
| `AFTERGIFT_ADMIN_TOKEN` | change-me-dev-only | 管理员 Token（开发用）|

---

*最后更新：Phase 2B 完成时生成。*
