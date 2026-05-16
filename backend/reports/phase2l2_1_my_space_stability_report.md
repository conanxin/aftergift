# Phase 2L-2.1 — My Space 稳定性修复报告

**日期**: 2026-05-16
**阶段**: Phase 2L-2.1
**状态**: ✅ PASS

---

## 目标

修复 Phase 2L-2 报告中列出的两个风险，不新增产品功能。

1. **Stats 数字竞态**：串行 Promise 链依赖 `window._ms_*` 变量传递计数，高并发下 stats 数字可能先渲染为 `–` 再被覆盖
2. **Static 模式身份文案**：显示"未登录"容易误解，应改为准确的"本地模式不支持匿名身份"

---

## 修复 1：Promise.allSettled 并行加载

**修改文件**: `frontend/app.js`

**问题**: 原有代码使用串行 `.then()` 链，published/pending 计数通过 IIFE 预加载到 `window._ms_publishedCount` 和 `window._ms_pendingCount`。在 fast 网络条件下，stats 渲染函数可能在 IIFE 完成前回退到 `window._ms_*` 的 undefined 值。

**解决**: 重写 `loadMySpaceData()`，使用 `Promise.allSettled` 并行发起 6 个 API 调用：

```javascript
Promise.allSettled([
  window.AftergiftAPI.getCurrentUser(token),         // 0 → identity card
  window.AftergiftAPI.listGifts({ mine: true }, []),      // 1 → published count
  window.AftergiftAPI.listGifts({ mine: true, action_type: 'pending' }, []), // 2 → pending count
  window.AftergiftAPI.listGifts({ favorites_of: 'me' }, []), // 3 → favorites count
  window.AftergiftAPI.getMyActions({ limit: 5 }),           // 4 → action list
  window.AftergiftAPI.listGifts({ mine: true, limit: 3 }, []) // 5 → gift list
])
```

每个结果独立渲染，失败不影响其他区块：
- `results[0]` 失败 → 身份卡片留空（不 crash）
- `results[1]` 失败 → published 显示 `–`
- `results[4]` 失败 → 操作历史显示"暂时无法加载"
- `results[5]` 失败 → 发布列表显示"暂时无法加载发布列表"

同时删除 IIFE 预加载逻辑（`window._ms_publishedCount` / `window._ms_pendingCount`）。

**删除的相关代码**:
```javascript
// 已删除：预加载 IIFE
(function () {
  window.AftergiftAPI.listGifts({ mine: true }, []).then(function (r) {
    window._ms_publishedCount = r.total || 0;
    ...
  });
})();
```

---

## 修复 2：Static 模式身份文案

**修改文件**: `frontend/app.js` + `frontend/style.css`

**修改前**:
```html
<div class="msic-nickname">未登录</div>
<div class="msic-token-status"><span class="msic-token-dot invalid"></span> 无效</div>
```

**修改后**:
```html
<div class="msic-nickname">本地模式</div>
<div class="msic-token-status"><span class="msic-token-dot invalid"></span> 不支持匿名身份</div>
<div class="msic-token-note">当前是静态演示模式，身份、发布和操作历史需要在 API 模式下使用。</div>
```

新增 `.msic-token-note` CSS 样式（0.72rem，柔和灰色）。

---

## 变更文件清单

| 文件 | 改动 |
|------|------|
| `frontend/app.js` | 重写 `loadMySpaceData()` 为 Promise.allSettled；修正 Static 模式身份文案；删除预加载 IIFE |
| `frontend/style.css` | 新增 `.msic-token-note` 样式 |
| `frontend/docs/MY_SPACE_VIEW.md` | 更新实现说明；更新 Static 降级文案；新增 Phase 2L-2.1 历史条目 |
| `docs/NEXT_STEPS.md` | 新增 Phase 2L-2.1 行项目 |

---

## 验证结果

```
node --check frontend/app.js              ✅ EXIT:0
node --check frontend/api-client.js        ✅ EXIT:0
python3 -m json.tool gifts.json           ✅ EXIT:0

Backend tests (13/13): 全部 PASS ✅
  test_favorites_api            15/15 PASS
  test_my_gifts                 12/12 PASS
  test_my_actions_and_restore   12/12 PASS
  test_auth_jwt                 12/12 PASS
  test_schema                    7/7  PASS
  test_discovery_api            18/18 PASS
  test_my_gift_management       14/14 PASS
  test_search_api               12/12 PASS
  test_migrations                4/4  PASS
  test_admin_enhancements       11/11 PASS
  test_redaction                11/11 PASS
  test_moderation_provider      11/11 PASS
  test_openai_provider          11/11 PASS
Total: 150/150 PASS
```

**本地预览** (frontend http.server 8080):
```
/                      HTTP 200 ✅
/ ?view=me             HTTP 200 ✅
/ ?view=favorites      HTTP 200 ✅
/ ?api=local           HTTP 200 ✅
```

---

## 安全扫描

```
aftergift_dev.db       ← 已在 .gitignore ✅
__pycache__/           ← 已在 .gitignore ✅
No .env files found    ✅
No API keys found      ✅
```

---

## 风险残余

1. **Promise.allSettled polyfill**: 现代浏览器均支持（Chrome 76+/Firefox 71+/Safari 13+），云端 Hermes 使用 Node.js 22（内置支持），无需 polyfill。
2. **局部网络故障**: 单个 API 区块失败时其他区块继续显示，但整体骨架（统计数字 initial `–`）会在 `loadMySpaceData` 完成前短暂可见，属于可接受的加载状态。

---

## 下一步建议

- **Phase 2M**: 本地草稿管理（草稿预览、草稿恢复编辑、草稿过期清理）
- **Phase 3A-0**: 社区功能设计评审（温和评论系统 + 私信匿名中继）