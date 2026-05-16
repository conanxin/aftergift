# Aftergift 部署说明

**Phase closeout 文档 | 本文档不包含机密信息**

---

## 1. 概述

Aftergift 分为两个部分：

| 部分 | 部署方式 | 说明 |
|------|----------|------|
| `frontend/` | GitHub Pages / 任意静态服务器 | 纯 HTML/CSS/JS，无服务端依赖 |
| `backend/backend/` | FastAPI + uvicorn | Python 3.10+，需要独立服务器 |

两者可以独立运行：前端默认以 static 模式（读取 `data/gifts.json`）工作，不依赖后端。

---

## 2. 前端部署（GitHub Pages）

### 2.1 部署到 GitHub Pages

```bash
# 方式一：推送到 conanxin.github.io 仓库的对应路径
# 方式二：使用 GitHub Actions 自动部署

# 手动部署步骤（假设已有 pages 分支）：
cd frontend
git checkout -b gh-pages
git push origin gh-pages
# 在 GitHub 仓库 Settings → Pages → Source: gh-pages branch
```

### 2.2 GitHub Pages 限制

- **仅支持静态文件**：`backend/` 不会随 GitHub Pages 部署
- **API 模式不可用**：在 GitHub Pages 上只能使用 static 模式（`data/gifts.json`）
- **表单提交仅本地预览**：发布礼物功能需要本地 FastAPI 后端

### 2.3 草稿版部署

在 `index.html` 中添加 noindex meta，可部署到 drafts 目录作为审阅版：

```html
<meta name="robots" content="noindex">
```

---

## 3. 本地开发部署

### 3.1 前端

```bash
cd frontend
python3 -m http.server 8080
# http://127.0.0.1:8080/
```

### 3.2 后端

```bash
cd backend/backend

# 1. 创建虚拟环境
python3 -m venv .venv
. .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，修改以下必填项：
#   AFTERGIFT_JWT_SECRET=your-32bytes-plus-secret
#   AFTERGIFT_ADMIN_TOKEN=your-strong-random-token

# 4. 初始化数据库
python scripts/init_db.py

# 5. 启动服务
uvicorn app.main:app --host 127.0.0.1 --port 8091 --reload
```

### 3.3 前端联调模式

在启动后端后，以联调模式访问前端：

```
http://127.0.0.1:8080/?api=local
```

此时前端读写 `http://127.0.0.1:8091` 的真实 API。

---

## 4. VPS 部署（生产推荐）

### 4.1 系统要求

- Ubuntu 22.04+ 或 macOS
- Python 3.10+
- Nginx（反向代理 + HTTPS）
- systemd（进程管理）
- SQLite 或 PostgreSQL

### 4.2 部署步骤

```bash
# 1. 安装系统依赖
sudo apt update && sudo apt install -y python3.10-venv nginx certbot

# 2. 创建应用用户
sudo useradd -m -s /bin/bash aftergift
sudo mkdir -p /opt/aftergift
sudo cp -r backend /opt/aftergift/
sudo chown -R aftergift:aftergift /opt/aftergift

# 3. 安装 Python 依赖（以 aftergift 用户）
cd /opt/aftergift/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 /opt/aftergift/backend/.env

# 5. 初始化数据库
python scripts/init_db.py

# 6. 创建 systemd 服务文件
sudo nano /etc/systemd/system/aftergift.service
```

**`/etc/systemd/system/aftergift.service` 内容**：

```ini
[Unit]
Description=Aftergift FastAPI Backend
After=network.target

[Service]
User=aftergift
WorkingDirectory=/opt/aftergift/backend
Environment="PATH=/opt/aftergift/backend/.venv/bin"
ExecStart=/opt/aftergift/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8091
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 7. 启动服务
sudo systemctl daemon-reload
sudo systemctl enable aftergift
sudo systemctl start aftergift

# 8. 配置 Nginx（反向代理 + HTTPS）
sudo nano /etc/nginx/sites-available/aftergift
```

**Nginx 配置示例**：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8091;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        add_header X-Frame-Options "SAMEORIGIN" always;
    }
}
```

```bash
# 9. 启用 HTTPS（使用 Let's Encrypt）
sudo certbot --nginx -d your-domain.com
sudo systemctl reload nginx
```

### 4.3 数据库备份

```bash
# 手动备份
python scripts/backup_db.py

# 定时备份（crontab）
# 每天凌晨 3 点备份
0 3 * * * /opt/aftergift/backend/.venv/bin/python /opt/aftergift/backend/scripts/backup_db.py >> /var/log/aftergift_backup.log 2>&1
```

---

## 5. Docker 部署（未来选项）

当前仓库**不包含 Dockerfile**，以下为未来参考设计：

```dockerfile
# backend/Dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
EXPOSE 8091
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8091"]
```

> 注意：Docker 部署需要处理 SQLite 的文件锁问题，或改用 PostgreSQL。

---

## 6. 生产环境安全检查清单

| 检查项 | 说明 |
|--------|------|
| ✅ HTTPS | 必须启用 TLS，避免 Token 明文传输 |
| ✅ JWT Secret | 必须替换为 32+ bytes 随机字符串，不得使用默认值 |
| ✅ Admin Token | 必须替换为强随机值，不得使用开发 token |
| ✅ CORS | `ALLOWED_ORIGINS` 仅允许可信域名 |
| ✅ API 限速 | 建议对匿名用户启用 IP 层面限速（nginx limit_req）|
| ✅ 数据库备份 | 定期备份 SQLite，生产建议换 PostgreSQL |
| ✅ 审核队列 | 定期检查 `pending_review` 礼物，防止积压 |
| ✅ 日志脱敏 | 确保日志中不包含手机号、地址等敏感信息 |
| ✅ 监控系统 | 建议接入 Uptime Monitor / Sentry |

---

## 7. 环境变量参考

| 变量 | 开发默认值 | 生产要求 |
|------|-----------|----------|
| `AFTERGIFT_DB_PATH` | `aftergift_dev.db` | 建议使用绝对路径 |
| `AFTERGIFT_ADMIN_TOKEN` | `dev-admin-aftergift-001` | **必须替换** |
| `AFTERGIFT_JWT_SECRET` | `dev-jwt-secret-...` | **必须替换**（32+ bytes）|
| `AFTERGIFT_MODERATION_PROVIDER` | `openai` | 可保持 |
| `AFTERGIFT_ENABLE_REAL_AI_REVIEW` | `false` | 按需 |
| `OPENAI_API_KEY` | `sk-dev-...` | 仅在 above=true 时配置 |

---

## 8. 当前不是生产就绪

以下功能**尚未实现**，生产部署前必须完成：

| 功能 | 状态 | 影响 |
|------|------|------|
| 真实支付 | 未实现 | 无法完成真实交易 |
| 物流对接 | 未实现 | 无法追踪实物配送 |
| 评论审核 | Phase 3A-0 设计 ✅，实现待定 | 需要人工兜底 |
| 私信功能 | 延后 | — |
| 高并发支持 | SQLite 写锁 | QPS > 50 需迁 PostgreSQL |
| DDoS 防护 | 无 | 需要 CDN/WAF |
| 数据导出（GDPR） | 无 | 法律合规风险 |

---

*本文档为部署参考，不构成生产部署承诺。*