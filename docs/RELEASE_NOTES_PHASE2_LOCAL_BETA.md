# Aftergift Phase 2 Local Beta Release Notes

> 版本：Phase 2H-2
> 日期：2026-05-16
> 状态：本地内测就绪

## 当前可用功能

### 核心功能
- ✅ 匿名身份创建（JWT Token）
- ✅ 礼物故事发布（含温柔检查）
- ✅ 礼物浏览与搜索（关键词 + 筛选）
- ✅ 礼物详情查看（含完整故事）
- ✅ 收藏 / 取消收藏

### 我的发布管理
- ✅ 查看我的发布（全部状态）
- ✅ 编辑礼物（draft / pending_review / needs_edit）
- ✅ 重新提交审核（needs_edit / rejected → pending_review）
- ✅ 归档礼物（published / pending_review / needs_edit / rejected → archived）
- ✅ 恢复归档（archived → pending_review）
- ✅ 查看操作历史

### 管理功能
- ✅ Admin 审核队列（按风险等级筛选）
- ✅ 审核决定（approve / needs_edit / reject）
- ✅ 举报管理（查看 / 处理）
- ✅ Admin 操作历史

### 安全与审核
- ✅ 内容规则预检（同步）
- ✅ Mock AI 审核（异步）
- ✅ 审核日志脱敏
- ✅ OpenAI Provider 沙箱（可选）

## 当前不可用功能

- ❌ 真实支付与担保交易
- ❌ 物流跟踪
- ❌ 用户间私信
- ❌ 评论功能
- ❌ 内容推荐算法
- ❌ 线下交换活动
- ❌ 多设备草稿同步
- ❌ 邮件/短信通知

## 如何本地启动

### 1. 启动后端

```bash
cd ~/projects/aftergift/backend/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --host 127.0.0.1 --port 8091
```

### 2. 启动前端

```bash
cd ~/projects/aftergift/frontend
python3 -m http.server 8080
```

### 3. 访问

- **普通模式**：http://127.0.0.1:8080/
- **API 模式**：http://127.0.0.1:8080/?api=local
- **Admin 模式**：http://127.0.0.1:8080/?api=local&admin=1

## 内测注意事项

1. **不要发布真实个人信息**
   - 匿名规则：不暴露姓名、电话、地址、社交账号
   - 聚焦物品和自己的感受

2. **这不是二手交易平台**
   - 故事是核心，交易只是可选方式
   - 只标价格不写故事的内容会被审核拒绝

3. **审核是自动 + 人工**
   - 发布后立即进入审核队列
   - Admin 可在 `?admin=1` 面板处理

4. **数据本地存储**
   - 所有数据存在本地 SQLite 文件
   - 定期备份：`python backend/backend/scripts/backup_db.py`

5. **反馈渠道**
   - 内测反馈表：见 `docs/BETA_FEEDBACK_FORM.md`
   - 或直接联系组织者

## 安全边界

- 不收集真实手机号/邮箱
- 不存储密码
- 不调用真实 OpenAI API（默认 mock）
- 不部署公网
- 不启用支付

## 已知问题

详见 `docs/KNOWN_ISSUES.md`

## 下一步

- Phase 2I：基础内容推荐
- 或根据内测反馈优先修复

---

*感谢参与 Aftergift 内测。*
