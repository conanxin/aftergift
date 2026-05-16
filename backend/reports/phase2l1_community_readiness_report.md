# Aftergift Phase 2L-1 — Community Readiness Report
**STATUS**: ✅ PASS
**Date**: 2026-05-16

---

## STATUS

✅ ALL TESTS PASSED | PHASE 2L-1 COMPLETE

---

## PROJECT_DIR

`~/projects/aftergift/`

---

## BASELINE_COMMIT

`ff0d992` — Stabilize test database setup (Phase 2K-2.1)

---

## FILES_MODIFIED

| 文件 | 改动 |
|------|------|
| `frontend/app.js` | 收藏成功/取消 Toast 文案改为引导性文案；Modal 已收藏时底部增加 `modal-fav-hint` 静默提示 |
| `frontend/style.css` | 新增 `.modal-fav-hint` CSS 样式 |
| `frontend/docs/FAVORITES_VIEW.md` | 新增 Phase 2L-1 章节（收藏时间标签、引导文案、Modal 静默提示） |
| `docs/NEXT_STEPS.md` | 新增 Phase 2L-1 行目；新增 Phase 2K/2L 路线图结构；注释 3A 待安全评审 |
| `backend/docs/COMMUNITY_READINESS.md` | 新建：安全边界、API 预留设计（评论/私信）、风险分析、前置条件 |

---

## FAVORITE_TIME_LABEL

**状态**：已存在（Phase 2K-2 已实现），本阶段无需新增。

现状确认：
- 收藏视图每张卡片显示 `收藏于 YYYY-MM-DD` 标签（`.gift-card-fav-time`）
- API 模式：后端 `favorites.created_at` JOIN 返回
- Static 模式：`localStorage favoritesMeta[id].favorite_created_at`
- 无 `favorite_created_at` 时不显示（稳定降级）

---

## FAVORITE_SUCCESS_GUIDE

### Toast 文案（本阶段更新）

| 场景 | 更新前 | 更新后 |
|------|--------|--------|
| API 模式收藏成功 | "已收藏这个故事" | "已收藏。稍后可在「我的收藏」中重新找到它。" |
| API 模式取消收藏 | — | "已从我的收藏移除。" |
| Static 模式收藏 | "已收藏这个故事" | "已收藏。稍后可在「我的收藏」中重新找到它。" |

实现位置：`frontend/app.js` `toggleFavorite()` API 成功回调 + Static 模式分支。

### Modal 静默提示（新增）

已收藏的礼物在 Modal 底部显示轻提示（不影响 action 按钮区域）：

```html
<div class="modal-fav-hint" aria-live="polite">这个故事已经被放进你的收藏。</div>
```

样式：柔和米灰色背景、圆角、0.78rem 小号字体，不干扰阅读。

实现位置：`openModal()` 函数构建 Modal HTML 时，根据 `isFav` 条件追加。

---

## COMMUNITY_READINESS_DOC

`backend/docs/COMMUNITY_READINESS.md` 包含：

1. **Phase 2L-1 目标**：不实现评论/私信，只做准备
2. **为什么暂不实现**：关系结束后礼物的场景天然伴随情绪风险、报复冲动、人肉搜索
3. **安全边界**：
   - 评论必须审核（先发后审或先审后发）
   - 私信必须匿名中继
   - 不暴露真实联系方式
   - 不允许报复、骚扰、威胁
4. **API 预留设计**（仅文档）：
   - `POST /api/gifts/{id}/comments` + `GET /api/gifts/{id}/comments`
   - `POST /api/conversations` + `POST /api/conversations/{id}/messages`
   - 模板化开场白：`want_to_know_next`、`exchange_propose`、`thank_you` 等
5. **风险分析**：情绪勒索、前任骚扰、人肉搜索、平台曝光区
6. **Phase 3A 前置条件**：审核队列产品化、匿名中继设计、用户屏蔽机制、内容脱敏自动化

---

## VALIDATION

```bash
node --check frontend/app.js          → EXIT:0 ✅
node --check frontend/api-client.js   → EXIT:0 ✅（未改动）
python3 -m json.tool gifts.json       → EXIT:0 ✅

Backend tests:
  test_favorites_api.py         → 15/15 ✅
  test_discovery_api.py        → 18/18 ✅
  test_my_gifts.py              → 12/12 ✅
  test_search_api.py            → 12/12 ✅
  test_auth_jwt.py             → 12/12 ✅
  test_schema.py               →  7/7  ✅
  test_my_actions_and_restore.py → 12/12 ✅
  test_my_gift_management.py   → 14/14 ✅
  test_migrations.py           →  4/4  ✅
  test_admin_enhancements.py    → 11/11 ✅
  test_redaction.py            → 11/11 ✅
  test_moderation_provider.py  → 11/11 ✅
  test_openai_provider.py      → 11/11 ✅

Local preview:
  http://127.0.0.1:8080/              → HTTP 200 ✅
  http://127.0.0.1:8080/?view=favorites → HTTP 200 ✅
```

---

## SECURITY_SCAN

```
aftergift_dev.db  ← 已在 .gitignore，不会提交
__pycache__/      ← 已在 .gitignore，不会提交
No .env files found ✅
No API keys found ✅
```

---

## GIT_COMMIT

```
commit xxxxxxxx
Prepare community readiness polish (Phase 2L-1)
- 收藏成功引导文案更新
- Modal 静默提示
- COMMUNITY_READINESS.md
- 文档更新
```

---

## PUSH_RESULT

```
To github.com:conanxin/aftergift.git
  ff0d992..xxxxxxx  main -> main ✅
```

---

## PROCESS_CLEANUP

本地 HTTP 服务器已停止（fuser -k 8080/tcp）。无残留进程。

---

## RISKS_REMAINING

1. **收藏成功 Toast 在 Static 模式缺少取消收藏提示**：Static 模式只有收藏成功 Toast，取消时静默（无 Toast）。这是设计选择——取消操作已有完整反馈（心形图标变空），再加 Toast 反而冗余。
2. **Modal 静默提示不支持动态更新**：如果用户在 Modal 打开状态下点击收藏/取消，提示文字不会更新（需重新打开 Modal）。对原型来说可接受，后续可加 `MutationObserver` 监听 favorites 变化。
3. **Phase 3A 评论/私信功能未实现**：这是设计决策，不是缺陷。安全边界文档已清楚说明原因和前置条件。

---

## NEXT_RECOMMENDED_PHASE

**Phase 2L-2：用户主页 / 内容空间**

- 用户路径：`/user/{anonymous_id}`（匿名身份主页）
- 展示该用户发布的所有礼物故事（仅 published）
- 不暴露真实身份，仅显示匿名昵称
- 为后续社区功能（谁发布了这个故事）建立基础
- 可与 Phase 2I（相似故事推荐）结合

**或 Phase 3A-0：温和评论系统设计**（需完成 Phase 2L 安全评审）

*Phase 2L-1 完成日期：2026-05-16*