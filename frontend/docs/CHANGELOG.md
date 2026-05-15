# 变更日志

> 《后来礼物 / Aftergift》完整开发变更记录

---

## Phase 1A：基础静态原型

**日期**：2026-04（早期开发）

**核心目标**：建立页面基本结构和视觉风格

**主要变更**：
- 创建 `index.html`、`style.css`、`app.js`
- 实现 Hero 首屏（标题/副标题/双按钮）
- 实现概念说明区（三卡片）
- 实现礼物故事网格（静态 10 条示例数据）
- 实现礼物详情 Modal（无完整故事）
- 实现发布表单（基础字段，无校验）
- 实现安全与伦理说明区
- 实现产品路线图
- 配色方案：暖米白 + 浅灰 + 淡粉 + 暖棕
- 全响应式布局（桌面/平板/手机）

**验证结果**：
- 页面可正常加载，CSS/JS 无报错
- JSON 数据正常解析
- 无 CDN 依赖

**遗留问题**：
- 表单无验证，可发布空内容
- 无故事预检机制
- 无移动端专项优化
- 无筛选空状态

---

## Phase 1B：视觉与产品叙事增强

**日期**：Phase 1A 后迭代

**核心目标**：提升视觉质量和产品叙事感

**主要变更**：
- 优化 Hero 区域动效和排版
- 增强卡片视觉层次（添加情绪图标、筛选标签）
- 丰富示例数据（从 10 条扩充至 14 条）
- 新增 Footer（平台声明为静态原型）
- 优化 Modal 视觉（分隔线、安全提示）
- 增强筛选标签交互（`aria-selected`）
- 添加 Toast 反馈系统

**验证结果**：
- 视觉符合「温柔、克制、干净」定位
- 14 条示例数据全部 `anonymous: true`
- 无真实身份信息泄露

**遗留问题**：
- 发布流程无引导
- 故事预检缺失
- 无收藏功能

---

## Phase 1C：故事预检与发布体验

**日期**：Phase 1B 后迭代

**核心目标**：增加故事发布前的引导、预检和预览机制

**主要变更**：

### Phase 1C 主体
- 新增故事模板提示（4 个引导卡片：来历/意义/变化/下一站）
- 实现故事预检功能（18 条正则规则，3 级输出）
- 新增发布前确认 Checkbox（3 项必选）
- 新增故事预览 Modal（预览卡片在列表中的样式）
- 实现筛选空状态（CSS 信封图标 + 温柔文案）
- 表单重置时同步清空情绪标签状态

### Phase 1C.1
- 检查并修复 `data/gifts.json` gift-011 重复 `relation` 字段
- 重新注入 Pages 草稿 `noindex` meta
- Git commit `cc1e6b0`，推送成功
- 验证：JSON 合法 14 条，all anonymous=true

### Phase 1C.2
- 清理 Pages 草稿遗留根目录 `gifts.json`
- 设置 Git 仓库局部身份：`Conan Xin <conanxin@gmail.com>`
- Git commit `ce49c38`，推送成功

**验证结果**：
- 预检规则正确检测手机号/微信号/报复词汇
- 发布确认机制有效（3 项必选）
- 预览 Modal 正常展示
- 空状态 UI 正常显示

**遗留问题**：
- 预检 UI 不够「温柔」（Phase 1D 升级为 AI 编辑建议面板）
- 无收藏功能
- 故事模板引导无「插入」功能

---

## Phase 1D：模拟 AI 审核 UI + 收藏 + 移动端优化

**日期**：Phase 1C 后迭代

**核心目标**：将「规则预检」升级为「AI 编辑助手」体验，增加收藏和移动端优化

**主要变更**：

### AI 编辑建议面板
- 重构预检为完整 AI Review Panel（标题/描述/按钮/Panel 容器）
- 「检查故事是否适合公开」→「运行温柔检查」
- 新增总体风险等级显示（适合公开 / 建议修改后公开 / 不建议直接公开）
- 身份信息风险条目（8 条规则）
- 报复/攻击性表达风险条目（3 条规则）
- 可识别关系对象风险条目（3 条规则）

### 自动匿名化建议
- 新增 9 条匿名化规则，每条含：原表达类型 / 风险原因 / 温和替代表达
- 「复制匿名化建议」按钮（`navigator.clipboard.writeText`）
- 匿名化建议卡片：`anon-badge` 类型标签 + `anon-original` + `anon-reason` + `anon-suggest`

### 故事完整度检查
- 5 项检测：字数(<50)/来历/意义/告别理由/下一站
- 每项含温柔文案提示

### 收藏故事功能
- 心形按钮（卡片右上角 + Modal 内）
- `localStorage` 持久化（key: `aftergift_favorites`）
- 「已收藏」筛选标签（图标 + 文字）
- 无收藏时显示温柔空状态文案
- 按钮状态：空心 ↔ 实心珊瑚色

### 阅读更多
- 初始展示 8 条，最多 100 条
- `displayedCount` 状态管理
- 筛选时自动重置

### 移动端体验
- textarea `auto-resize`
- 一句话故事：`n/100` 字数计数
- 完整故事：`n 字` 计数 + <50 字温柔提示
- 预检按钮、预览按钮全宽
- 确认 Checkbox 标签自动换行
- `body { overflow-x: hidden }`
- 360px 极窄屏专项适配

### CSS 新增
- `.card-favorite-btn`、`.load-more-wrap`、`.full-story-footer`、`.story-quality-hint`
- `.ai-review-section`、`.ai-review-intro`、`.ai-review-panel`、`.ai-review-header`、`.ai-issue-*`、`.anon-suggestion`、`.anon-badge-*`、`.ai-copy-btn`
- 移动端响应式优化

**验证结果**：
- AI Review Panel 正确输出所有维度
- 收藏状态跨刷新保留
- 移动端无横向滚动
- `overflow-x: hidden` 有效
- Git commit `e708c76`，推送成功

**遗留问题**：
- 收藏无法跨设备同步（localStorage 限制）
- AI 审核为纯正则规则，无法拦截高级规避手段
- 发布故事无法持久化（重启页面丢失）

---

## Phase 1E：产品化验收包

**日期**：本次迭代

**核心目标**：整理交接文档，归档产品化验收材料

**主要变更**：

### docs/ 目录创建
- `PRODUCT_SPEC.md`：产品说明书（名称/背景/价值/用户/功能/非目标/气质）
- `USER_FLOWS.md`：8 条完整用户路径（含风险和处理方式）
- `CONTENT_POLICY.md`：内容治理政策（价值观/鼓励/禁止/规则/审核层建议）
- `TECHNICAL_NOTES.md`：技术架构说明（文件结构/前端架构/数据结构/部署/后端路径）
- `QA_CHECKLIST.md`：18 类手动测试清单（步骤/预期/状态）
- `ROADMAP.md`：5 阶段路线图（Phase 2-5 + 长期愿景）
- `CHANGELOG.md`：完整变更记录（Phase 1A ~ 1E）

### README 更新
- Phase 版本更新（1C → 1D）
- 新增 docs 目录说明
- 功能列表更新

### 仓库卫生
- 无新增功能
- 验证所有 Phase 1D 功能完整性
- 确认 `noindex`、无 CDN、无根目录 `gifts.json`

**验证结果**：
- 7 个文档全部创建，内容完整
- README 正确引用 docs 目录
- Pages 草稿 `noindex` 保持
- Git commit 完成

**遗留问题**：
- Phase 1 阶段正式结束，无遗留功能问题

---

## 统计摘要

| 指标 | 数值 |
|------|------|
| 累计开发阶段 | 7 个（1A, 1B, 1C, 1C.1, 1C.2, 1D, 1E）|
| Git 提交次数 | 6 次 |
| 示例礼物数据 | 14 条 |
| 所有数据 `anonymous` | 100% |
| docs/ 文档数 | 7 个 |
| 前端 JS 行数 | ~900 行（Phase 1D 最新）|
| CSS 行数 | ~1500 行 |
| GitHub Pages 部署 | `drafts/aftergift-prototype/` |
| 线上地址 | `https://conanxin.github.io/drafts/aftergift-prototype/` |
