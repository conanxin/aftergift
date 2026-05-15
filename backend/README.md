# Aftergift 后端 MVP 沙箱

> Phase 2A | 状态：后端蓝图设计 · 可运行 Mock

---

## 1. 项目目的

`aftergift-backend-mvp/` 是《后来礼物 / Aftergift》的后端 MVP 沙箱目录，用于：
- 设计数据库模型和 API 契约
- 定义内容审核工作流
- 提供可本地运行的 mock API 示例
- 生成开发交接文档

**这不是生产服务**，不部署、不长期运行、不接入真实 AI、不处理真实用户数据。

---

## 2. 与前端原型的关系

| 组件 | 路径 | 说明 |
|------|------|------|
| 静态原型（Phase 1） | `~/projects/aftergift-prototype/` | 纯前端，无后端 |
| 后端 MVP 沙箱（Phase 2A） | `~/projects/aftergift-backend-mvp/` | 本目录，蓝图+mock |
| 真实后端（Phase 2C+） | 待定 | 基于本蓝图接入 SQLite + FastAPI |

Phase 1 原型调用 `./data/gifts.json`；Phase 2 后端将替代为 `/api/gifts` REST 接口。

---

## 3. 当前不做什么

- ❌ 不做真实生产服务
- ❌ 不做真实支付、物流、担保交易
- ❌ 不做真实用户登录系统（手机号注册、实名认证）
- ❌ 不接真实 OpenAI / 百度 / 第三方 AI 审核 API
- ❌ 不保存明文手机号、邮箱、地址
- ❌ 不允许上传他人照片或隐私附件
- ❌ 不对公网暴露服务

---

## 4. 本地运行方式

```bash
# Mock API（轻量，可用 Python 标准库运行）
cd ~/projects/aftergift-backend-mvp
python3 mock_api/app.py
# 访问 http://localhost:8090/api/health

# Schema 测试
python3 tests/test_schema.py

# Mock Review 测试
python3 -c "from mock_api.mock_review import review_story; import json; print(json.dumps(review_story('测试', '这是故事内容'), ensure_ascii=False, indent=2))"
```

---

## 5. 文件结构

```
aftergift-backend-mvp/
├── README.md                # 本文件
├── docs/                    # 后端设计文档
│   ├── BACKEND_SPEC.md      # 后端产品说明（Phase 2A 核心交付物）
│   ├── DATA_MODEL.md        # 数据模型设计
│   ├── API_DESIGN.md        # REST API 契约设计
│   ├── REVIEW_WORKFLOW.md   # 内容审核流程
│   ├── SECURITY_NOTES.md    # 安全与隐私说明
│   └── PHASE2_PLAN.md       # Phase 2 实施计划
├── schema/                  # 数据库 schema
│   ├── sqlite_schema.sql    # SQLite 建表语句
│   └── seed_data.sql       # 虚构种子数据
├── mock_api/                # 可本地运行的 mock API
│   ├── app.py              # 基于 http.server 的 mock API
│   └── mock_review.py      # Mock AI 审核逻辑（规则引擎）
├── tests/
│   └── test_schema.py      # Schema 验证测试
└── reports/
    └── phase2a_report.md   # 本次执行报告
```

---

## 6. 后续接入路径

```
Phase 2A（本目录）
    ↓ 完成后生成完整蓝图
Phase 2B: 选择后端框架（FastAPI / Express）
Phase 2C: 接入 SQLite，联调前端
Phase 2D: 前后端完整联调（story/review/favorite/report）
Phase 2E: 审核队列（admin review）
Phase 2F: 管理员工具（web 后台 + Telegram 通知）
Phase 2G: 小范围内测（邀请种子用户）
```

---

*最后更新：Phase 2A 完成时由 Hermes 自动生成。*