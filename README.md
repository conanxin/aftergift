# Aftergift / 后来礼物

> 给一件旧礼物，一个体面的下一站。

## 项目简介

Aftergift 是一个关系旧物的温柔流转平台原型。用户可以发布关系结束、变化或疏远后留下的礼物，写下礼物背后的故事，并选择出售、交换、赠送、捐出或只展示故事。

**核心原则**：温柔、克制、干净、有一点伤感。不鼓励报复、羞辱、猎奇或网暴。

## 在线 Demo

**正式项目页**（GitHub Pages）：https://conanxin.github.io/projects/aftergift-prototype/

**草稿版**（含开发工具）：https://conanxin.github.io/drafts/aftergift-prototype/

## 当前状态

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 静态产品 Demo | ✅ 完成 |
| Phase 2A | 后端沙箱蓝图 | ✅ 完成 |
| Phase 2B | FastAPI 骨架 + SQLite | ✅ 完成 |
| Phase 2C | 前后端 local API 双模式联调 | ✅ 完成 |
| Phase 2D | 匿名身份 + Admin 审核队列 UI | ✅ 完成 |

## 目录结构

```
aftergift/
├── frontend/         # 静态 Web App 原型（HTML/CSS/JS）
├── backend/           # FastAPI 后端 MVP
│   ├── app/          # FastAPI 应用（routers, services, models）
│   ├── scripts/       # 数据库初始化脚本
│   ├── tests/        # 合同测试
│   ├── docs/          # 后端文档（API 设计、审核流程、Auth 设计等）
│   └── reports/       # 各 Phase 执行报告
├── docs/             # 顶层文档索引
└── reports/          # 顶层报告索引（Phase 2D 执行报告等）
```

## 本地前端运行

```bash
cd frontend
python3 -m http.server 8080
# 打开 http://127.0.0.1:8080/
```

默认以 **static 模式**运行（读取 `data/gifts.json`），不依赖后端。

## 本地 API 联调（可选）

需要先启动后端：

```bash
cd backend/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --host 127.0.0.1 --port 8091
```

前端访问联调模式：

```
http://127.0.0.1:8080/?api=local
```

访问 Admin 审核面板：

```
http://127.0.0.1:8080/?api=local&admin=1
```

Admin token（本地开发）：`dev-admin-aftergift-001`

## 安全说明

- **不要提交 `.env`** — 环境变量文件包含敏感配置
- **不要提交数据库文件** — `*.db`、`*.sqlite`、`aftergift_dev.db`
- **当前 Token 是开发期方案** — HMAC-SHA256，非标准 JWT，仅限本地开发
- **当前 AI 审核为 Mock** — `review_service.py` 使用正则规则，非真实外部 AI API

## 产品边界

- ❌ 不是前任曝光平台
- ❌ 不是报复平台
- ❌ 不是情感审判平台
- ❌ 当前不含真实支付和物流
- ✅ 是关系旧物的温柔流转与故事讲述平台

## 推荐阅读顺序

1. `frontend/docs/PRODUCT_SPEC.md` — 产品规格
2. `frontend/docs/CONTENT_POLICY.md` — 内容安全与伦理政策
3. `frontend/docs/API_INTEGRATION.md` — 前端 API 集成说明
4. `backend/docs/BACKEND_SPEC.md` — 后端 MVP 设计
5. `backend/docs/API_DESIGN.md` — API 设计
6. `backend/docs/AUTH_DESIGN.md` — 匿名认证设计
7. `backend/docs/ADMIN_REVIEW_UI.md` — 管理员审核 UI 设计

---

*Conan Xin — 2026-05-16*
