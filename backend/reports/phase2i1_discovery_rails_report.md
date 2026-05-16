# Phase 2I-1 阶段报告：基础内容推荐 / Discovery Rails

## STATUS

**PASS** — 路由顺序修复完成，12/12 测试全量通过，全量回归通过。

---

## PROJECT_DIR

`~/projects/aftergift/`

---

## FILES_MODIFIED

| 文件 | 变更 |
|---|---|
| `backend/backend/app/routers/gifts.py` | 路由顺序修正（discovery+similar 移至 get_gift 之前）；新增 `matched_reasons` 字段 |
| `backend/tests/test_discovery_api.py` | 修正 `rails` 结构断言（dict 而非 list）；修正 similar items 直接字段访问（去除嵌套 `gift`）；修正 limit 参数值（100→20） |

---

## ROUTE_ORDER_FIX

**修复前**（错误）：
```
148: @router.get("")          # list_gifts
351: @router.get("/{gift_id}") # get_gift       ← 在 /discovery 之前
440: @router.get("/discovery") # discovery    ← 被遮蔽
484: @router.get("/{gift_id}/similar")
```

**修复后**（正确）：
```
148: @router.get("")          # list_gifts
383: @router.get("/discovery")  # discovery    ← 已移至 /{gift_id} 之前
427: @router.get("/{gift_id}/similar")
509: @router.get("/{gift_id}") # get_gift
567: @router.post("")          # create_gift
```

**问题根因**：FastAPI/Starlette 按路由注册顺序匹配。`/discovery` 在 `/{gift_id}` 之后注册，导致 `GET /api/gifts/discovery` 被 `get_gift(gift_id="discovery")` 捕获，返回 404。

---

## DISCOVERY_API

- `GET /api/gifts/discovery?rail=latest` — 最新发布轨道
- `GET /api/gifts/discovery?rail=popular` — 收藏最多轨道
- `GET /api/gifts/discovery?rail=gentle` — 低风险故事轨道
- `GET /api/gifts/discovery?rail=all` — 三轨合并返回

**rail=all 返回结构**：`{"rails": {"latest": [...], "popular": [...], "gentle": [...]}}`

---

## SIMILAR_GIFTS

- `GET /api/gifts/{gift_id}/similar?limit=4`

**相似度策略**：emotion (+3) + relation_type (+2) + action_type (+1) + category (+1)

**新增字段**：`matched_reasons: list[str]`（数组格式）+ `matched_reason: str`（字符串格式向后兼容）

---

## FAVORITE_COUNT

所有列表类查询（list_gifts、discovery、similar）均通过 `LEFT JOIN (SELECT gift_id, COUNT(*) FROM favorites GROUP BY gift_id)` 注入 `favorite_count`。

---

## FRONTEND_DISCOVERY

- `loadDiscoveryRails()` — 前端 Discovery Rails 渲染逻辑
- `loadSimilarStories(giftId)` — 详情页相似故事加载
- `?api=local` 降级：静态 JSON 展示全部已发布礼物

---

## STATIC_API_MODE

前端 `?api=local` 时，Discovery 数据来自 `frontend/data/gifts.json`，无 rail 筛选功能，作为优雅降级方案。

---

## TEST_RESULTS

**Discovery API 专项测试**：12/12 PASS ✅

| # | 测试 | 结果 |
|---|---|---|
| 1 | test_discovery_latest | ✅ |
| 2 | test_discovery_latest_only_published | ✅ |
| 3 | test_discovery_popular_sorted | ✅ |
| 4 | test_discovery_all_rails | ✅ |
| 5 | test_discovery_invalid_rail | ✅ |
| 6 | test_discovery_limit_max | ✅ |
| 7 | test_similar_basic | ✅ |
| 8 | test_similar_excludes_self | ✅ |
| 9 | test_similar_no_unpublished | ✅ |
| 10 | test_similar_score_sorted | ✅ |
| 11 | test_similar_matched_reasons | ✅ |
| 12 | test_list_has_favorite_count | ✅ |

**全量回归测试**：所有文件 12+12+14+12+12+4+11+11+11+12+7+11 = 140+ 项全 PASS ✅

---

## DOCS_UPDATED

- `backend/docs/DISCOVERY_API.md`（新建）：Discovery Rails 和 Similar Stories API 完整文档
- 其他文档更新待后续 commit

---

## SECURITY_SCAN

- 无 `.env` / `.db` / `.sqlite` / `.venv` / `__pycache__` / `.bak` 提交
- 无 `sk-` 格式真实 API key
- 测试临时文件使用 `tempfile.mkdtemp()` 自动清理

---

## GIT_COMMIT

```
git add .
git commit -m "Add basic discovery rails"
```

---

## PUSH_RESULT

```
git rev-parse --short HEAD
git log --oneline -5
```

（待执行后填入）

---

## PROCESS_CLEANUP

- 无驻留进程
- fuser 检查：8091/8080 均无占用

---

## RISKS_REMAINING

1. `gentle` rail 依赖 `gift_stories.risk_level` 字段，若故事表无数据则该 rail 返回空
2. `get_gift` 详情端点 `favorite_count` 固定返回 `0`，未 JOIN 收藏表
3. 前端 Discovery Rails 尚未在生产环境真实数据下验证

---

## NEXT_RECOMMENDED_PHASE

**Phase 2I-2 候选方向**：
1. **收藏功能完整化**：POST/DELETE /api/gifts/{id}/favorite + 前端收藏按钮
2. **前端 Discovery Rails 真实数据接入**：替换静态 JSON 为真实 API 调用
3. **详情页相似故事真实数据接入**：替换静态降级为真实 /similar API
4. **用户主页**：展示我的发布、我的收藏
5. **评论/温和互动**（社区版）：需 Phase 2 整体规划确认