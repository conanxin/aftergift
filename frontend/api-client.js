/**
 * Aftergift API Client
 * Phase 2C | 双模式适配器：static (JSON) / api (FastAPI)
 *
 * 使用方式：
 *   - 默认 static 模式（读取 ./data/gifts.json）
 *   - ?api=local 启用 api 模式（调用 http://127.0.0.1:8091）
 *   - window.AFTERGIFT_CONFIG = { mode: 'api'|'static', apiBaseUrl: '...' }
 */

(function () {
  'use strict';

  // ── Config ──────────────────────────────────────────────────────────────────

  /**
   * 检测运行模式。
   * 优先级：window.AFTERGIFT_CONFIG.mode > URL ?api=local > 默认 static
   */
  function getMode() {
    if (window.AFTERGIFT_CONFIG && window.AFTERGIFT_CONFIG.mode) {
      return window.AFTERGIFT_CONFIG.mode;
    }
    if (new URLSearchParams(window.location.search).has('api')) {
      return 'api';
    }
    return 'static';
  }

  var MODE = getMode();
  var API_BASE = (
    (window.AFTERGIFT_CONFIG && window.AFTERGIFT_CONFIG.apiBaseUrl) ||
    'http://127.0.0.1:8091'
  );

  // ── Response unwrapper ─────────────────────────────────────────────────────

  /**
   * 解析 FastAPI 统一响应格式 {code, message, data}。
   * 非 API 模式或非标准格式时直接透传。
   */
  function unwrap(response) {
    if (MODE !== 'api') return response;
    if (response && typeof response.code !== 'undefined') {
      if (response.code >= 200 && response.code < 300) {
        return response.data;
      }
      var err = new Error(response.message || 'API Error');
      err.code = response.code;
      throw err;
    }
    return response;
  }

  // ── Normalizer ─────────────────────────────────────────────────────────────

  /**
   * 将后端 Gift 字段 normalize 为前端 gift card 期望的字段。
   *
   * 后端字段 → 前端字段：
   *   id              → id
   *   title           → name
   *   category        → type
   *   relation_type   → relation
   *   relation_label  → relationLabel
   *   action_type     → action
   *   action_label   → actionLabel (保持不变)
   *   emotion         → emotion (保持不变)
   *   excerpt         → excerpt (保持不变) / short_story
   *   price_or_exchange → price
   *   status          → status (保持不变)
   *   is_anonymous    → anonymous (保持不变)
   *   story.full_story → fullStory
   *   story.risk_level → risk_level
   *
   * 同时：static 模式的 gifts.json 字段原样透传（部分字段有别名，在 normalizeGift 中处理）
   */
  function normalizeGift(g) {
    // Already normalized (static JSON source)
    if (g._normalized) return g;

    var normalized = {
      _normalized: true,
      // Core identity
      id:       g.id,
      name:     g.name     || g.title     || '',
      type:     g.type     || g.category  || '',
      // Relation
      relation:      g.relation      || g.relation_type  || '',
      relationLabel: g.relationLabel || g.relation_label || '',
      // Action
      action:      g.action      || g.action_type || '',
      actionLabel: g.actionLabel || (
        g.action_type ? {
          sell: '出售', exchange: '交换', giveaway: '赠送',
          donate: '捐出', keep: '只讲故事'
        }[g.action_type] : ''
      ) || '',
      // Story
      excerpt:    g.excerpt    || g.short_story  || '',
      fullStory:  g.fullStory  || (g.story && g.story.full_story) || '',
      shortStory: g.shortStory || g.short_story  || g.excerpt || '',
      // Meta
      emotion: g.emotion || '',
      price:   g.price   || g.price_or_exchange || '',
      status:  g.status  || '',
      anonymous:  !!(g.anonymous || g.is_anonymous),
      tags:    g.tags    || [],
      // Backend extras (for API mode detail)
      risk_level:    (g.story && g.story.risk_level)    || g.risk_level    || null,
      quality_score: (g.story && g.story.quality_score) || g.quality_score || null,
      condition_note: g.condition_note || '',
      city_blur:     g.city_blur     || '',
      anonymous_nickname: g.anonymous_nickname || '',
      created_at: g.created_at || null,
      // Phase 2I-1
      favorite_count: g.favorite_count || 0,
      // Phase 2J-1: is_favorited from API responses
      is_favorited: !!(g.is_favorited || g.favorited),
      // Phase 2K-1: favorite_created_at from GET favorites_of=me
      favorite_created_at: g.favorite_created_at || g.created_at || null,
      similarity_score: g.similarity_score || null,
      matched_reason: g.matched_reason || '',
    };

    return normalized;
  }

  // ── Transport ──────────────────────────────────────────────────────────────

  function apiFetch(path, options) {
    if (MODE !== 'api') {
      throw new Error('API mode is not active');
    }
    var url = API_BASE + path;
    return fetch(url, options).then(function (r) {
      return r.json().then(function (json) {
        if (!r.ok) {
          var err = new Error((json && json.message) || 'Request failed');
          err.status = r.status;
          err.code = json && json.code;
          throw err;
        }
        return json;
      });
    });
  }

  // ── Gift List ──────────────────────────────────────────────────────────────

  /**
   * 获取礼物列表。
   * API 模式：GET /api/gifts?q=...&action_type=...&emotion=...&page=1&limit=12
   * Static 模式：读取 ./data/gifts.json（全量，内存中过滤）
   *
   * @param {Object} filters  - { q, action_type, emotion, relation_type, city_blur, page, limit, sort, order }
   * @param {Array}  staticData - static 模式下的全量数据（由 app.js 传入）
   * @returns {Promise<{items: Array, total: number, page: number, limit: number, total_pages: number, has_more: boolean, mode: string, filters: Object}>}
   */
  function listGifts(filters, staticData) {
    filters = filters || {};
    if (MODE === 'api') {
      var params = new URLSearchParams();
      if (filters.q)             params.set('q',             filters.q);
      if (filters.action_type)   params.set('action_type',   filters.action_type);
      if (filters.emotion)       params.set('emotion',       filters.emotion);
      if (filters.relation_type) params.set('relation_type', filters.relation_type);
      if (filters.city_blur)     params.set('city_blur',     filters.city_blur);
      if (filters.mine)          params.set('mine',          'true');
      if (filters.favorites_of)  params.set('favorites_of',  filters.favorites_of);
      params.set('page',  String(filters.page  || 1));
      params.set('limit', String(filters.limit || 12));
      if (filters.sort)  params.set('sort',  filters.sort);
      if (filters.order) params.set('order', filters.order);
      var qs = params.toString();
      var headers = {};
      var token = getStoredToken();
      if (filters.mine || filters.favorites_of) {
        if (!token) {
          return Promise.reject(new Error('请先创建匿名身份'));
        }
        headers['Authorization'] = 'Bearer ' + token;
      }
      return apiFetch('/api/gifts' + (qs ? '?' + qs : ''), { headers: headers }).then(unwrap).then(function (data) {
        return {
          items:      (data.items || []).map(normalizeGift),
          total:      data.total      || 0,
          page:       data.page       || 1,
          limit:      data.limit      || 12,
          total_pages: data.total_pages || 0,
          has_more:   data.has_more   || false,
          mode:       'api',
          filters:    data.filters    || {}
        };
      });
    }

    // Static mode: filter in-memory
    var q = (filters.q || '').trim().toLowerCase();
    var items = (staticData || []).filter(function (g) {
      // Phase 2K-1: favorites_of filter (static mode uses localStorage)
      if (filters.favorites_of === 'me') {
        try {
          var stored = localStorage.getItem('aftergift_favorites');
          var favs = stored ? JSON.parse(stored) : {};
          if (!favs[g.id]) return false;
        } catch (e) { return false; }
      }
      if (filters.action_type && filters.action_type !== 'all') {
        if (g.action !== filters.action_type && g.action_type !== filters.action_type) return false;
      }
      if (filters.emotion && g.emotion !== filters.emotion) return false;
      if (filters.relation_type && g.relation !== filters.relation_type && g.relation_type !== filters.relation_type) return false;
      if (q) {
        var hay = [
          g.name || g.title || '',
          g.type || g.category || '',
          g.relation || g.relation_type || '',
          g.relationLabel || g.relation_label || '',
          g.action || g.action_type || '',
          g.emotion || '',
          g.excerpt || g.short_story || g.shortStory || '',
          g.fullStory || (g.story && g.story.full_story) || '',
          g.city_blur || g.cityBlur || ''
        ].join(' ').toLowerCase();
        if (hay.indexOf(q) === -1) return false;
      }
      return true;
    });

    // Static pagination
    var page  = Math.max(1, parseInt(filters.page, 10) || 1);
    var limit = Math.max(1, Math.min(100, parseInt(filters.limit, 10) || 12));
    var total = items.length;
    var total_pages = Math.ceil(total / limit) || 0;
    var offset = (page - 1) * limit;
    var paginated = items.slice(offset, offset + limit);

    return Promise.resolve({
      items:       paginated.map(normalizeGift),
      total:       total,
      page:        page,
      limit:       limit,
      total_pages: total_pages,
      has_more:    page < total_pages,
      mode:        'static',
      filters:     {
        q: filters.q || null,
        emotion: filters.emotion || null,
        action_type: filters.action_type || null,
        relation_type: filters.relation_type || null,
        city_blur: filters.city_blur || null,
        sort: filters.sort || null,
        order: filters.order || null
      }
    });
  }

  // ── Gift Detail ────────────────────────────────────────────────────────────

  /**
   * 获取礼物详情。
   * API 模式：GET /api/gifts/{id}
   * Static 模式：在 staticData 中查找
   */
  function getGift(id, staticData) {
    if (MODE === 'api') {
      return apiFetch('/api/gifts/' + encodeURIComponent(id)).then(unwrap).then(normalizeGift);
    }
    var found = null;
    (staticData || []).forEach(function (g) {
      if (g.id === id) found = g;
    });
    if (!found) {
      var e = new Error('礼物不存在');
      e.code = 404;
      return Promise.reject(e);
    }
    return Promise.resolve(normalizeGift(found));
  }

  // ── Discovery Rails (Phase 2I-1) ───────────────────────────────────────────

  function getDiscoveryRails(params) {
    params = params || {};
    if (MODE === 'api') {
      var qs = new URLSearchParams();
      qs.set('rail', params.rail || 'all');
      qs.set('limit', String(Math.max(1, Math.min(20, params.limit || 6))));
      return apiFetch('/api/gifts/discovery?' + qs.toString()).then(unwrap).then(function (data) {
        if (data.rails) {
          var rails = {};
          Object.keys(data.rails).forEach(function (k) {
            var railData = data.rails[k];
            // Phase 2I-2: rails[key] is now {items, fallback_used} for gentle
            var items = Array.isArray(railData) ? railData : (railData.items || []);
            rails[k] = items.map(normalizeGift);
          });
          return { rail: 'all', rails: rails };
        }
        return {
          rail: data.rail,
          items: (data.items || []).map(normalizeGift)
        };
      });
    }
    // Static fallback: use window.__AF_STATIC_DATA as last resort
    var data = (typeof window !== 'undefined' && window.__AF_STATIC_DATA) || [];
    return getStaticDiscoveryRails(params, data);
  }

  function getStaticDiscoveryRails(params, staticData) {
    params = params || {};
    var rail = params.rail || 'all';
    var limit = Math.max(1, Math.min(20, params.limit || 6));
    var items = (staticData || []).filter(function (g) {
      return g.status === 'published' || !g.status;
    });

    function _sortLatest(arr) {
      return arr.slice().sort(function (a, b) {
        return (b.created_at || '') > (a.created_at || '') ? 1 : -1;
      });
    }
    function _sortPopular(arr) {
      return arr.slice().sort(function (a, b) {
        var fa = (a.favorite_count || 0);
        var fb = (b.favorite_count || 0);
        if (fb !== fa) return fb - fa;
        return (b.created_at || '') > (a.created_at || '') ? 1 : -1;
      });
    }

    if (rail === 'latest') {
      return Promise.resolve({ rail: 'latest', items: _sortLatest(items).slice(0, limit).map(normalizeGift) });
    }
    if (rail === 'popular') {
      return Promise.resolve({ rail: 'popular', items: _sortPopular(items).slice(0, limit).map(normalizeGift) });
    }
    if (rail === 'gentle') {
      return Promise.resolve({ rail: 'gentle', items: _sortLatest(items).slice(0, limit).map(normalizeGift) });
    }
    // all
    return Promise.resolve({
      rail: 'all',
      rails: {
        latest: _sortLatest(items).slice(0, limit).map(normalizeGift),
        popular: _sortPopular(items).slice(0, limit).map(normalizeGift),
        gentle: _sortLatest(items).slice(0, limit).map(normalizeGift),
      }
    });
  }

  // ── Similar Gifts (Phase 2I-1) ─────────────────────────────────────────────

  function getSimilarGifts(giftId, params, staticData) {
    params = params || {};
    if (MODE === 'api') {
      var qs = new URLSearchParams();
      qs.set('limit', String(Math.max(1, Math.min(12, params.limit || 4))));
      return apiFetch('/api/gifts/' + encodeURIComponent(giftId) + '/similar?' + qs.toString())
        .then(unwrap).then(function (data) {
          return {
            base_gift_id: data.base_gift_id,
            strategy: data.strategy,
            items: (data.items || []).map(normalizeGift)
          };
        });
    }
    // Static fallback: use passed staticData, or window as last resort
    var data = staticData;
    if (!data || !data.length) {
      data = (typeof window !== 'undefined' && window.__AF_STATIC_DATA) || [];
    }
    return getStaticSimilarGifts(giftId, params, data);
  }

  function getStaticSimilarGifts(giftId, params, staticData) {
    params = params || {};
    var limit = Math.max(1, Math.min(12, params.limit || 4));
    var base = null;
    (staticData || []).forEach(function (g) {
      if (g.id === giftId) base = g;
    });
    if (!base) {
      return Promise.reject(new Error('礼物不存在'));
    }
    var candidates = (staticData || []).filter(function (g) {
      return g.id !== giftId && (g.status === 'published' || !g.status);
    });
    var scored = candidates.map(function (g) {
      var score = 0;
      var reasons = [];
      if (g.emotion === base.emotion) { score += 3; reasons.push('相同情绪'); }
      if ((g.relation || g.relation_type) === (base.relation || base.relation_type)) { score += 2; reasons.push('相同关系类型'); }
      if ((g.action || g.action_type) === (base.action || base.action_type)) { score += 1; reasons.push('相同处理方式'); }
      if ((g.type || g.category) === (base.type || base.category)) { score += 1; reasons.push('相同礼物类型'); }
      return { score: score, gift: g, reasons: reasons };
    }).filter(function (s) { return s.score > 0; });
    scored.sort(function (a, b) {
      if (b.score !== a.score) return b.score - a.score;
      return (b.gift.created_at || '') > (a.gift.created_at || '') ? 1 : -1;
    });
    var items = scored.slice(0, limit).map(function (s) {
      var n = normalizeGift(s.gift);
      n.similarity_score = s.score;
      n.matched_reason = s.reasons.join('、');
      return n;
    });
    return Promise.resolve({
      base_gift_id: giftId,
      strategy: 'emotion_relation_action_similarity',
      items: items
    });
  }

  // ── Create Gift ────────────────────────────────────────────────────────────

  /**
   * 发布新礼物。
   * API 模式：POST /api/gifts
   * Static 模式：返回临时 gift 对象（不持久化）
   *
   * @param {Object} payload  - 表单数据
   * @returns {Promise<{gift_id: string, status: string, review: Object}>}
   */
  function createGift(payload) {
    if (MODE === 'api') {
      var body = {
        title:             payload.name,
        category:          payload.type,
        relation_type:     payload.relation,
        action_type:       payload.action,
        emotion:           payload.emotion,
        short_story:       payload.excerpt,
        full_story:        payload.fullStory,
        price_or_exchange: payload.price,
        condition_note:    payload.condition_note || '',
        city_blur:         payload.city || '',
        is_anonymous:      !!payload.anonymous,
      };
      var token = getStoredToken();
      var headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = 'Bearer ' + token;
      return apiFetch('/api/gifts', {
        method:  'POST',
        headers:  headers,
        body:    JSON.stringify(body)
      }).then(unwrap);
    }
    // Static mode: return a temp gift object
    var tempId = 'temp-' + Date.now();
    return Promise.resolve({
      gift_id: tempId,
      status:  'demo',
      review:  { risk_level: 'demo', issues_count: 0 }
    });
  }

  // ── Story Review ───────────────────────────────────────────────────────────

  /**
   * 故事审核检查。
   * API 模式：POST /api/review/mock
   * Static 模式：返回 null（使用前端本地规则）
   */
  function reviewStory(shortStory, fullStory) {
    if (MODE === 'api') {
      return apiFetch('/api/review/mock', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ short_story: shortStory, full_story: fullStory })
      }).then(unwrap);
    }
    return Promise.resolve(null); // signal: use frontend local rules
  }

  // ── Favorites ──────────────────────────────────────────────────────────────

  function favoriteGift(id) {
    if (MODE === 'api') {
      var token = getStoredToken();
      if (!token) {
        return Promise.reject({ message: '请先创建匿名身份，再收藏这个故事。', status: 401 });
      }
      var headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = 'Bearer ' + token;
      return apiFetch('/api/gifts/' + encodeURIComponent(id) + '/favorite', {
        method:  'POST',
        headers:  headers
      }).then(unwrap);
    }
    // Static mode: update localStorage
    try {
      var stored = localStorage.getItem('aftergift_favorites');
      var favs = stored ? JSON.parse(stored) : {};
      favs[id] = true;
      localStorage.setItem('aftergift_favorites', JSON.stringify(favs));
    } catch (e) {}
    return Promise.resolve({ is_favorited: true, favorite_count: 1, mode: 'static' });
  }

  function unfavoriteGift(id) {
    if (MODE === 'api') {
      var token = getStoredToken();
      if (!token) {
        return Promise.reject({ message: '请先创建匿名身份，再收藏这个故事。', status: 401 });
      }
      var headers = {};
      if (token) headers['Authorization'] = 'Bearer ' + token;
      return apiFetch('/api/gifts/' + encodeURIComponent(id) + '/favorite', {
        method:  'DELETE',
        headers:  headers
      }).then(unwrap);
    }
    // Static mode: update localStorage
    try {
      var stored = localStorage.getItem('aftergift_favorites');
      var favs = stored ? JSON.parse(stored) : {};
      delete favs[id];
      localStorage.setItem('aftergift_favorites', JSON.stringify(favs));
    } catch (e) {}
    return Promise.resolve({ is_favorited: false, favorite_count: 0, mode: 'static' });
  }

  // ── Report ─────────────────────────────────────────────────────────────────

  /**
   * 举报礼物。
   * @param {string} id      - gift id
   * @param {Object} payload - { reason: string, detail: string }
   */
  function reportGift(id, payload) {
    if (MODE === 'api') {
      var token = getStoredToken();
      var headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = 'Bearer ' + token;
      return apiFetch('/api/gifts/' + encodeURIComponent(id) + '/report', {
        method:  'POST',
        headers:  headers,
        body:    JSON.stringify({
          reason: payload.reason  || 'privacy_risk',
          detail: payload.detail || ''
        })
      }).then(unwrap);
    }
    return Promise.resolve({ ok: true, mode: 'static' });
  }

  // ── Admin ────────────────────────────────────────────────────────────────────

  function _adminHeaders(token) {
    return { 'Content-Type': 'application/json', 'X-Admin-Token': token };
  }

  function getAdminReviews(params, token) {
    if (MODE !== 'api') return Promise.resolve({ items: [], total: 0 });
    var qs = new URLSearchParams();
    if (params.status)     qs.set('status',     params.status);
    if (params.risk_level) qs.set('risk_level', params.risk_level);
    if (params.provider)   qs.set('provider',   params.provider);
    if (params.page)       qs.set('page',       String(params.page));
    if (params.limit)      qs.set('limit',      String(params.limit));
    if (params.sort)       qs.set('sort',       params.sort);
    if (params.order)      qs.set('order',      params.order);
    return apiFetch('/api/admin/reviews?' + qs.toString(), {
      headers: _adminHeaders(token)
    }).then(unwrap);
  }

  function decideAdminReview(giftId, payload, token) {
    if (MODE !== 'api') return Promise.resolve({ ok: true, mode: 'static' });
    return apiFetch('/api/admin/reviews/' + encodeURIComponent(giftId) + '/decision', {
      method: 'POST',
      headers: _adminHeaders(token),
      body: JSON.stringify({ decision: payload.decision, note: payload.note || '' })
    }).then(unwrap);
  }

  function getAdminReports(params, token) {
    if (MODE !== 'api') return Promise.resolve({ items: [], total: 0 });
    var qs = new URLSearchParams();
    if (params.status) qs.set('status', params.status);
    if (params.reason) qs.set('reason', params.reason);
    if (params.page)   qs.set('page',   String(params.page));
    if (params.limit)  qs.set('limit',  String(params.limit));
    if (params.sort)   qs.set('sort',   params.sort);
    if (params.order)  qs.set('order',  params.order);
    return apiFetch('/api/admin/reports?' + qs.toString(), {
      headers: _adminHeaders(token)
    }).then(unwrap);
  }

  function decideAdminReport(reportId, payload, token) {
    if (MODE !== 'api') return Promise.resolve({ ok: true, mode: 'static' });
    return apiFetch('/api/admin/reports/' + encodeURIComponent(reportId) + '/decision', {
      method: 'POST',
      headers: _adminHeaders(token),
      body: JSON.stringify({ decision: payload.decision, note: payload.note || '' })
    }).then(unwrap);
  }

  function getAdminReviewLogs(giftId, token) {
    if (MODE !== 'api') return Promise.resolve({ items: [], total: 0 });
    return apiFetch('/api/admin/reviews/' + encodeURIComponent(giftId) + '/logs', {
      headers: _adminHeaders(token)
    }).then(unwrap);
  }

  function getAdminActions(params, token) {
    if (MODE !== 'api') return Promise.resolve({ items: [], total: 0 });
    var qs = new URLSearchParams();
    if (params.target_type) qs.set('target_type', params.target_type);
    if (params.target_id)   qs.set('target_id',   params.target_id);
    if (params.action)      qs.set('action',      params.action);
    if (params.page)        qs.set('page',        String(params.page));
    if (params.limit)       qs.set('limit',       String(params.limit));
    return apiFetch('/api/admin/actions?' + qs.toString(), {
      headers: _adminHeaders(token)
    }).then(unwrap);
  }

  // ── Health check ────────────────────────────────────────────────────────────

  function checkHealth() {
    if (MODE !== 'api') return Promise.resolve({ status: 'static' });
    return apiFetch('/api/health').then(unwrap).catch(function () {
      return { status: 'unreachable' };
    });
  }

  // ── Auth ───────────────────────────────────────────────────────────────────

  /**
   * Create anonymous user identity.
   * POST /api/auth/anonymous
   * @returns {Promise<{user_id, anonymous_nickname, access_token, token_type}>}
   */
  function createAnonymousUser() {
    if (MODE === 'api') {
      return apiFetch('/api/auth/anonymous', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      }).then(unwrap);
    }
    // Static mode: return a demo identity
    return Promise.resolve({
      user_id: 'demo-user-001',
      anonymous_nickname: '匿名整理者 0001',
      access_token: 'demo-token-0001',
      token_type: 'Bearer'
    });
  }

  /**
   * Get current user info.
   * GET /api/auth/me
   * @param {string} token - Bearer token
   * @returns {Promise<{user_id, anonymous_nickname, status, created_at}>}
   */
  function getCurrentUser(token) {
    if (MODE === 'api') {
      return apiFetch('/api/auth/me', {
        headers: { 'Authorization': 'Bearer ' + token }
      }).then(unwrap);
    }
    return Promise.resolve({
      user_id: 'demo-user-001',
      anonymous_nickname: '匿名整理者 0001',
      status: 'active'
    });
  }

  /**
   * Get stored token from localStorage.
   */
  function getStoredToken() {
    try {
      return localStorage.getItem('aftergift_token') || null;
    } catch (e) {
      return null;
    }
  }

  /**
   * Store token in localStorage.
   */
  function storeToken(token) {
    try {
      localStorage.setItem('aftergift_token', token);
    } catch (e) {}
  }

  /**
   * Clear stored token.
   */
  function clearStoredToken() {
    try {
      localStorage.removeItem('aftergift_token');
    } catch (e) {}
  }

  /**
   * Build Authorization header value.
   */
  function authHeader(token) {
    return token ? 'Bearer ' + token : null;
  }

  function getMyGift(giftId) {
    if (MODE !== 'api') return Promise.reject(new Error('API mode required'));
    var token = getStoredToken();
    var headers = {};
    if (token) headers['Authorization'] = 'Bearer ' + token;
    return apiFetch('/api/me/gifts/' + encodeURIComponent(giftId), { headers: headers }).then(unwrap).then(normalizeGift);
  }

  function updateMyGift(giftId, payload) {
    if (MODE !== 'api') return Promise.reject(new Error('API mode required'));
    var token = getStoredToken();
    var headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = 'Bearer ' + token;
    return apiFetch('/api/me/gifts/' + encodeURIComponent(giftId), {
      method: 'PATCH',
      headers: headers,
      body: JSON.stringify(payload)
    }).then(unwrap).then(normalizeGift);
  }

  function resubmitMyGift(giftId) {
    if (MODE !== 'api') return Promise.reject(new Error('API mode required'));
    var token = getStoredToken();
    var headers = {};
    if (token) headers['Authorization'] = 'Bearer ' + token;
    return apiFetch('/api/me/gifts/' + encodeURIComponent(giftId) + '/resubmit', {
      method: 'POST',
      headers: headers
    }).then(unwrap);
  }

  function archiveMyGift(giftId) {
    if (MODE !== 'api') return Promise.reject(new Error('API mode required'));
    var token = getStoredToken();
    var headers = {};
    if (token) headers['Authorization'] = 'Bearer ' + token;
    return apiFetch('/api/me/gifts/' + encodeURIComponent(giftId) + '/archive', {
      method: 'POST',
      headers: headers
    }).then(unwrap);
  }

  function restoreMyGift(giftId) {
    if (MODE !== 'api') return Promise.reject(new Error('API mode required'));
    var token = getStoredToken();
    var headers = {};
    if (token) headers['Authorization'] = 'Bearer ' + token;
    return apiFetch('/api/me/gifts/' + encodeURIComponent(giftId) + '/restore', {
      method: 'POST',
      headers: headers
    }).then(unwrap);
  }

  function getMyActions(params) {
    if (MODE !== 'api') return Promise.reject(new Error('API mode required'));
    var token = getStoredToken();
    var headers = {};
    if (token) headers['Authorization'] = 'Bearer ' + token;
    var query = new URLSearchParams();
    if (params) {
      if (params.gift_id) query.set('gift_id', params.gift_id);
      if (params.action) query.set('action', params.action);
      if (params.page) query.set('page', String(params.page));
      if (params.limit) query.set('limit', String(params.limit));
    }
    var qs = query.toString();
    var url = '/api/me/actions' + (qs ? '?' + qs : '');
    return apiFetch(url, { headers: headers }).then(unwrap);
  }

  // ── Export ─────────────────────────────────────────────────────────────────

  window.AftergiftAPI = {
    MODE:       MODE,
    API_BASE:   API_BASE,
    // Auth
    createAnonymousUser: createAnonymousUser,
    getCurrentUser:      getCurrentUser,
    getStoredToken:      getStoredToken,
    storeToken:          storeToken,
    clearStoredToken:    clearStoredToken,
    authHeader:          authHeader,
    // Gifts
    listGifts:      listGifts,
    getGift:        getGift,
    createGift:     createGift,
    // My Gifts (Phase 2H-1)
    getMyGift:      getMyGift,
    updateMyGift:   updateMyGift,
    resubmitMyGift: resubmitMyGift,
    archiveMyGift:  archiveMyGift,
    restoreMyGift:  restoreMyGift,
    getMyActions:   getMyActions,
    // Discovery (Phase 2I-1)
    getDiscoveryRails: getDiscoveryRails,
    getStaticDiscoveryRails: getStaticDiscoveryRails,
    getSimilarGifts: getSimilarGifts,
    getSimilarStories: getSimilarGifts,  // alias for frontend convenience
    getStaticSimilarGifts: getStaticSimilarGifts,
    // Story
    reviewStory:    reviewStory,
    // Favorites
    favoriteGift:   favoriteGift,
    unfavoriteGift: unfavoriteGift,
    // Report
    reportGift:     reportGift,
    // Admin
    getAdminReviews:     getAdminReviews,
    decideAdminReview:   decideAdminReview,
    getAdminReports:     getAdminReports,
    decideAdminReport:   decideAdminReport,
    getAdminReviewLogs:  getAdminReviewLogs,
    getAdminActions:     getAdminActions,
    // Health
    checkHealth:    checkHealth,
    // Normalize
    normalizeGift:   normalizeGift,
  };

})();
