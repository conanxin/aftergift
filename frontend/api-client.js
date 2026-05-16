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
   * API 模式：GET /api/gifts?action_type=...&emotion=...&page=1&limit=50
   * Static 模式：读取 ./data/gifts.json（全量，内存中过滤）
   *
   * @param {Object} filters  - { action_type, emotion, page, limit }
   * @param {Array}  staticData - static 模式下的全量数据（由 app.js 传入）
   * @returns {Promise<{items: Array, total: number, has_more: boolean, mode: string}>}
   */
  function listGifts(filters, staticData) {
    filters = filters || {};
    if (MODE === 'api') {
      var params = new URLSearchParams();
      if (filters.action_type) params.set('action_type', filters.action_type);
      if (filters.emotion)     params.set('emotion',     filters.emotion);
      params.set('page',  String(filters.page  || 1));
      params.set('limit', String(filters.limit || 50));
      var qs = params.toString();
      return apiFetch('/api/gifts' + (qs ? '?' + qs : '')).then(unwrap).then(function (data) {
        return {
          items:   (data.items || []).map(normalizeGift),
          total:   data.pagination ? data.pagination.total : (data.items || []).length,
          has_more: data.pagination ? data.pagination.has_more : false,
          mode:    'api'
        };
      });
    }

    // Static mode: filter in-memory
    var items = (staticData || []).filter(function (g) {
      if (filters.action_type && filters.action_type !== 'all') {
        if (g.action !== filters.action_type && g.action_type !== filters.action_type) return false;
      }
      if (filters.emotion && g.emotion !== filters.emotion) return false;
      return true;
    });
    return Promise.resolve({
      items:   items.map(normalizeGift),
      total:   items.length,
      has_more: false,
      mode:    'static'
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
      var headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = 'Bearer ' + token;
      return apiFetch('/api/gifts/' + encodeURIComponent(id) + '/favorite', {
        method:  'POST',
        headers:  headers
      }).then(unwrap);
    }
    return Promise.resolve({ ok: true, mode: 'static' });
  }

  function unfavoriteGift(id) {
    if (MODE === 'api') {
      var token = getStoredToken();
      var headers = {};
      if (token) headers['Authorization'] = 'Bearer ' + token;
      return apiFetch('/api/gifts/' + encodeURIComponent(id) + '/favorite', {
        method:  'DELETE',
        headers:  headers
      }).then(unwrap);
    }
    return Promise.resolve({ ok: true, mode: 'static' });
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
