/**
 * Aftergift — app.js
 * 故事型旧物流转平台 · 前端交互逻辑
 * Phase 1D: AI 编辑建议 · 自动匿名化 · 故事质量 · 收藏 · 阅读更多
 */

(function () {
  'use strict';

  // ── State ──
  var gifts = [];
  var currentFilter = 'all';
  var currentSearch = '';
  var nextTempId = 9000;
  var lastFocusedElement = null;
  var displayedCount = 8;       // initial visible cards
  var INITIAL_DISPLAY = 8;
  var MAX_DISPLAY = 100;
  var favorites = {};           // { id: true } synced with localStorage
  var favoritesMeta = {};       // { id: { favorite_created_at: '...', favorite_count: N } }
  var favoritesCount = 0;       // cached total for badge display
  var searchMeta = { total: 0, page: 1, limit: 12, total_pages: 0, has_more: false };
  var currentView = 'home';     // 'home' | 'favorites' | 'my_space'

  // ── Story Tip Prompts ──
  var STORY_TIPS = [
    '这件礼物是在什么时候来到你身边的？',
    '它曾经让你想起什么？承载了什么？',
    '为什么现在想让它离开？',
    '你希望下一个拥有它的人如何使用它？'
  ];

  // ── DOM refs ──
  var giftGrid      = document.getElementById('giftGrid');
  var emptyState    = document.getElementById('emptyState');
  var emptyStateLine = document.getElementById('emptyStateLine');
  var modalOverlay  = document.getElementById('modalOverlay');
  var modal         = document.getElementById('modal');
  var modalBody     = document.getElementById('modalBody');
  var modalClose    = document.getElementById('modalClose');
  var publishForm   = document.getElementById('publishForm');
  var filterTabs    = document.querySelectorAll('.filter-tab');
  var emotionBtns   = document.querySelectorAll('.emotion-tag');
  var excerptInput  = document.getElementById('excerpt');
  var excerptCount  = document.getElementById('excerptCount');
  var fullStoryInput = document.getElementById('fullStory');
  var fullStoryCount = document.getElementById('fullStoryCount');
  var precheckBtn   = document.getElementById('precheckBtn');
  var precheckCard  = document.getElementById('precheckCard');
  var previewBtn    = document.getElementById('previewBtn');
  var loadMoreBtn   = document.getElementById('loadMoreBtn');
  var aiReviewPanel = document.getElementById('aiReviewPanel');
  var storyQualityHint = document.getElementById('storyQualityHint');
  var searchInput   = document.getElementById('searchInput');
  var searchBtn     = document.getElementById('searchBtn');
  var searchClearBtn = document.getElementById('searchClearBtn');
  var searchHint    = document.getElementById('searchHint');

  // ── Init ──
  document.addEventListener('DOMContentLoaded', function () {
    loadFavorites();
    loadFavoritesMeta();
    updateHeroFavoritesBadge(); // Phase 2K-2: compute count and show badge
    checkUrlView();
    loadGifts();
    loadDiscoveryRails();
    bindEvents();
    initTextareas();
    initDevAuthPanel();
    bindDevAuthEvents();
    initAdminPanel();
    updateHeroMySpaceButton(); // Phase 2L-2: show my-space button when logged in
  });

  // ── Favorites (localStorage) ──
  function loadFavorites() {
    try {
      var stored = localStorage.getItem('aftergift_favorites');
      favorites = stored ? JSON.parse(stored) : {};
    } catch (e) {
      favorites = {};
    }
  }

  function loadFavoritesMeta() {
    try {
      var stored = localStorage.getItem('aftergift_favorites_meta');
      favoritesMeta = stored ? JSON.parse(stored) : {};
    } catch (e) {
      favoritesMeta = {};
    }
  }

  function saveFavorites() {
    try {
      localStorage.setItem('aftergift_favorites', JSON.stringify(favorites));
    } catch (e) {}
  }

  function saveFavoritesMeta() {
    try {
      localStorage.setItem('aftergift_favorites_meta', JSON.stringify(favoritesMeta));
    } catch (e) {}
  }

  window.toggleFavorite = function (id) {
    var isFav = !!favorites[id];
    var mode = window.__AF_MODE || 'static';

    if (isFav) {
      delete favorites[id];
      delete favoritesMeta[id];
    } else {
      favorites[id] = true;
      // Store local favorite_created_at for static mode
      if (mode !== 'api') {
        favoritesMeta[id] = {
          favorite_created_at: new Date().toISOString().slice(0, 16).replace('T', ' '),
          favorite_count: 1
        };
      }
    }
    saveFavorites();
    saveFavoritesMeta();

    // Update heart icon optimistically
    var cardHeart = document.querySelector('.gift-card[data-id="' + id + '"] .card-favorite-btn');
    if (cardHeart) updateHeartIcon(cardHeart, !isFav);
    var modalHeart = document.getElementById('modalFavoriteBtn');
    if (modalHeart) updateHeartIcon(modalHeart, !isFav);

    if (mode === 'api' && window.AftergiftAPI) {
      var apiCall = isFav
        ? window.AftergiftAPI.unfavoriteGift(id)
        : window.AftergiftAPI.favoriteGift(id);

      apiCall.then(function (res) {
        // Sync with server truth: server may return different state after action
        // e.g. idempotent call returns is_favorited correctly
        var serverFav = !!(res && res.is_favorited);
        favorites[id] = serverFav;
        saveFavorites();
        updateHeartIcon(cardHeart, serverFav);
        if (modalHeart) updateHeartIcon(modalHeart, serverFav);
        window.updateHeroFavoritesBadge(); // Phase 2K-2: update badge
        // Phase 2L-1: gentle guide message
        showToast(serverFav
          ? '已收藏。稍后可在「我的收藏」中重新找到它。'
          : '已从我的收藏移除。');
      }).catch(function (err) {
        // Revert optimistic update on failure
        if (isFav) {
          favorites[id] = true;
        } else {
          delete favorites[id];
        }
        saveFavorites();
        updateHeartIcon(cardHeart, isFav);
        if (modalHeart) updateHeartIcon(modalHeart, isFav);
        window.updateHeroFavoritesBadge(); // Phase 2K-2: revert badge

        var msg = (err && err.status === 401)
          ? '请先创建匿名身份，再收藏这个故事。'
          : '收藏操作失败了，请稍后重试。';
        showToast(msg);
      });
    } else {
      // Static mode: localStorage already saved above
      window.updateHeroFavoritesBadge(); // Phase 2K-2: update badge
      showToast('已收藏。稍后可在「我的收藏」中重新找到它。');
    }
  };

  function updateHeartIcon(btn, isFav) {
    if (isFav) {
      btn.innerHTML = '<svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16" aria-hidden="true"><path d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z"/></svg>';
      btn.classList.add('favorited');
      btn.setAttribute('aria-label', '取消收藏');
    } else {
      btn.innerHTML = '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16" aria-hidden="true"><path d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z"/></svg>';
      btn.classList.remove('favorited');
      btn.setAttribute('aria-label', '收藏故事');
    }
  }

  // ── Data ──
  function loadGifts() {
    // Detect mode from global set by inline <script> in index.html
    var mode = window.__AF_MODE || 'static';

    // Phase 2H-2: my_actions uses a separate flow
    if (currentFilter === 'my_actions') {
      if (mode === 'api' && window.AftergiftAPI) {
        loadMyActions();
      } else {
        gifts = [];
        renderGifts();
      }
      return;
    }

    var params = buildListParams();
    if (mode === 'api' && window.AftergiftAPI) {
      // API mode: call FastAPI backend
      window.AftergiftAPI.listGifts(params, []).then(function (result) {
        gifts = result.items;
        searchMeta = {
          total: result.total || 0,
          page: result.page || 1,
          limit: result.limit || 12,
          total_pages: result.total_pages || 0,
          has_more: result.has_more || false
        };
        showModeIndicator('api', result.total || result.items.length);
        renderGifts();
      }).catch(function () {
        // API unreachable: fall back to static data
        loadStaticGifts();
        showModeIndicator('fallback', 0);
      });
    } else {
      // Static mode: read local JSON
      loadStaticGifts();
      if (mode !== 'api') {
        showModeIndicator('static', -1);
      }
    }
  }

  function buildListParams() {
    var params = {
      q: currentSearch || undefined,
      page: 1,
      limit: 12
    };
    if (currentFilter !== 'all' && currentFilter !== 'favorites' && currentFilter !== 'mine' && currentFilter !== 'my_favorites') {
      params.action_type = currentFilter;
    }
    if (currentFilter === 'mine') {
      params.mine = true;
    }
    if (currentFilter === 'my_favorites') {
      params.favorites_of = 'me';
    }
    if (currentFilter === 'my_actions') {
      // my_actions is handled separately
      return null;
    }
    return params;
  }

  function loadStaticGifts() {
    fetch('./data/gifts.json')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        // Store for discovery + similar
        window.__AF_STATIC_DATA = data;
        // Apply static search + filter locally
        var params = buildListParams();
        window.AftergiftAPI.listGifts(params, data).then(function (result) {
          gifts = result.items;
          searchMeta = {
            total: result.total || 0,
            page: result.page || 1,
            limit: result.limit || 12,
            total_pages: result.total_pages || 0,
            has_more: result.has_more || false
          };
          showModeIndicator('static', result.total);
          renderGifts();
        });
      })
      .catch(function () {
        giftGrid.innerHTML = '<div class="empty-state"><p class="empty-state-line">无法加载礼物数据，请通过本地服务器打开（python3 -m http.server 8080）。</p></div>';
      });
  }


  // ── Phase 2I-1: Discovery Rails ───────────────────────────────────────────
  function loadDiscoveryRails() {
    var mode = window.__AF_MODE || 'static';
    if (mode === 'api' && window.AftergiftAPI) {
      window.AftergiftAPI.getDiscoveryRails().then(function (data) {
        renderDiscoveryRails(data);
      }).catch(function () {
        // Silently skip discovery rails on API error
      });
    } else {
      // Static mode: compute rails from local data
      var staticData = window.__AF_STATIC_DATA;
      if (staticData && staticData.length > 0) {
        var rails = computeStaticRails(staticData);
        renderDiscoveryRails(rails);
      } else {
        // Data not loaded yet, try again after a delay
        setTimeout(function () {
          var sd = window.__AF_STATIC_DATA;
          if (sd && sd.length > 0) {
            renderDiscoveryRails(computeStaticRails(sd));
          }
        }, 500);
      }
    }
  }

  function computeStaticRails(data) {
    // latest: sort by created_at desc
    var latest = data.slice().sort(function (a, b) {
      return (b.created_at || '').localeCompare(a.created_at || '');
    }).slice(0, 4);

    // popular: sort by favorite_count desc
    var popular = data.slice().sort(function (a, b) {
      return (b.favorite_count || 0) - (a.favorite_count || 0);
    }).slice(0, 4);

    // gentle: filter by mood (放下, 释怀, 平静, 治愈)
    var gentleMoods = ['放下', '释怀', '平静', '治愈'];
    var gentle = data.filter(function (g) {
      return gentleMoods.indexOf(g.mood || g.emotion || '') !== -1;
    }).slice(0, 4);

    return {
      rails: [
        { key: 'latest', title: '最新故事', subtitle: '刚刚来到这里的礼物', items: latest.map(normalizeGift) },
        { key: 'popular', title: '最多收藏', subtitle: '被最多人记住的故事', items: popular.map(normalizeGift) },
        { key: 'gentle', title: '温柔告别', subtitle: '已经放下的，轻轻送走', items: gentle.map(normalizeGift) }
      ]
    };
  }

  function renderDiscoveryRails(data) {
    var container = document.getElementById('discoveryRails');
    if (!container) return;
    var rails = (data && data.rails) ? data.rails : [];
    if (rails.length === 0) {
      container.style.display = 'none';
      return;
    }
    container.style.display = '';
    var html = rails.map(function (rail) {
      var itemsHtml = rail.items.map(function (g) {
        return discoveryCardHTML(g);
      }).join('');
      return '<div class="discovery-rail" data-rail="' + escHtml(rail.key) + '">' +
        '<div class="discovery-rail-header">' +
          '<h3 class="discovery-rail-title">' + escHtml(rail.title) + '</h3>' +
          '<span class="discovery-rail-subtitle">' + escHtml(rail.subtitle) + '</span>' +
        '</div>' +
        '<div class="discovery-rail-scroll">' + itemsHtml + '</div>' +
      '</div>';
    }).join('');
    container.innerHTML = html;
    bindDiscoveryEvents();
  }

  function discoveryCardHTML(g) {
    var actionClass = 'action-' + (g.action || g.action_type || 'keep');
    var emotionIcon = emotionIconSVG(g.emotion || g.mood || '放下');
    return '<article class="discovery-card" data-id="' + g.id + '" tabindex="0" role="button">' +
      '<div class="discovery-card-header">' +
        '<h4 class="discovery-card-title">' + escHtml(g.name || g.title || '') + '</h4>' +
        '<span class="gift-card-action ' + actionClass + '">' + escHtml(g.actionLabel || g.action_label || '') + '</span>' +
      '</div>' +
      '<div class="discovery-card-meta">' +
        '<span class="gift-card-tag">' + escHtml(g.type || g.category || '') + '</span>' +
        '<span class="gift-card-emotion">' + emotionIcon + escHtml(g.emotion || g.mood || '') + '</span>' +
      '</div>' +
      '<p class="discovery-card-excerpt">' + escHtml(g.excerpt || g.short_story || '') + '</p>' +
      '<div class="discovery-card-footer">' +
        '<span class="discovery-card-price">' + escHtml(g.price || g.price_or_exchange || '') + '</span>' +
        '<span class="discovery-card-fav">' + (g.favorite_count || 0) + ' 收藏</span>' +
      '</div>' +
    '</article>';
  }

  function bindDiscoveryEvents() {
    var container = document.getElementById('discoveryRails');
    if (!container) return;
    container.querySelectorAll('.discovery-card').forEach(function (card) {
      card.addEventListener('click', function () {
        var id = card.getAttribute('data-id');
        if (id) openModal(id);
      });
      card.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          card.click();
        }
      });
    });
  }

  // ── Phase 2I-1: Similar Stories ───────────────────────────────────────────
  function loadSimilarStories(giftId) {
    var mode = window.__AF_MODE || 'static';
    if (mode === 'api' && window.AftergiftAPI) {
      window.AftergiftAPI.getSimilarStories(giftId).then(function (data) {
        renderSimilarStories(data);
      }).catch(function () {
        // Silently skip on error
      });
    } else {
      var staticData = window.__AF_STATIC_DATA;
      if (staticData && staticData.length > 0) {
        var current = findGiftById(giftId);
        if (!current) return;
        var similar = computeStaticSimilar(current, staticData);
        renderSimilarStories({ items: similar });
      }
    }
  }

  function computeStaticSimilar(current, allData) {
    var currentMood = current.emotion || current.mood || '';
    var currentRelation = current.relation || current.relation_type || '';
    var currentTags = current.tags || [];
    var scored = allData.filter(function (g) {
      return g.id !== current.id;
    }).map(function (g) {
      var score = 0;
      var reasons = [];
      if ((g.mood || g.emotion || '') === currentMood && currentMood) {
        score += 2.0;
        reasons.push('相同情绪');
      }
      if ((g.relation_type || g.relation || '') === currentRelation && currentRelation) {
        score += 2.0;
        reasons.push('相同关系');
      }
      var gTags = g.tags || [];
      currentTags.forEach(function (t) {
        if (gTags.indexOf(t) !== -1) {
          score += 1.0;
          reasons.push('相同标签「' + t + '」');
        }
      });
      return {
        gift: normalizeGift(g),
        score: score,
        matched_reasons: reasons
      };
    });
    scored.sort(function (a, b) { return b.score - a.score; });
    return scored.slice(0, 3).map(function (s) {
      return {
        gift: s.gift,
        similarity_score: s.score,
        matched_reasons: s.matched_reasons
      };
    });
  }

  function renderSimilarStories(data) {
    var container = document.getElementById('similarStories');
    if (!container) return;
    var items = (data && data.items) ? data.items : [];
    if (items.length === 0) {
      container.style.display = 'none';
      return;
    }
    container.style.display = '';
    var html = '<div class="similar-stories-header">' +
      '<h3 class="similar-stories-title">相似故事</h3>' +
      '<span class="similar-stories-subtitle">也许这些礼物，和你正在看的这件，有着相似的心情</span>' +
    '</div>' +
    '<div class="similar-stories-list">';
    html += items.map(function (item) {
      var g = item.gift;
      var actionClass = 'action-' + (g.action || g.action_type || 'keep');
      var reasons = (item.matched_reasons || []).join(' · ');
      return '<article class="similar-story-card" data-id="' + g.id + '" tabindex="0" role="button">' +
        '<div class="similar-story-header">' +
          '<h4 class="similar-story-title">' + escHtml(g.name || g.title || '') + '</h4>' +
          '<span class="gift-card-action ' + actionClass + '">' + escHtml(g.actionLabel || g.action_label || '') + '</span>' +
        '</div>' +
        '<p class="similar-story-excerpt">' + escHtml(g.excerpt || g.short_story || '') + '</p>' +
        '<div class="similar-story-reason">' + escHtml(reasons) + '</div>' +
      '</article>';
    }).join('');
    html += '</div>';
    container.innerHTML = html;
    container.querySelectorAll('.similar-story-card').forEach(function (card) {
      card.addEventListener('click', function () {
        var id = card.getAttribute('data-id');
        if (id) {
          closeModal();
          setTimeout(function () { openModal(id); }, 300);
        }
      });
      card.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          card.click();
        }
      });
    });
  }

  // ── Mode indicator (footer) ──
  function showModeIndicator(mode, count) {
    var el = document.getElementById('footerModeIndicator');
    if (!el) return;
    var labels = {
      static:   '示例数据模式 · ' + (count >= 0 ? count + ' 件礼物' : ''),
      api:       '本地 API 联调模式 · ' + count + ' 件礼物',
      fallback:  'API 连接失败，已回退到示例数据',
    };
    var msgs = {
      static:   '当前：静态示例数据（GitHub Pages 原型）',
      api:       '当前：本地 FastAPI 联调模式',
      fallback:  'API 无法连接，已回退到示例数据',
    };
    el.textContent = msgs[mode] || '';
    el.style.display = '';
  }

  // ── Render ──
  function renderGifts() {
    var filtered = gifts.filter(function (g) {
      if (currentFilter === 'all') return true;
      if (currentFilter === 'favorites') return !!favorites[g.id];
      if (currentFilter === 'mine') return true; // backend already filtered
      if (currentFilter === 'my_favorites') return true; // backend already filtered
      if (currentFilter === 'my_actions') return true; // handled separately
      return g.action === currentFilter;
    });

    if (filtered.length === 0) {
      giftGrid.innerHTML = '';
      giftGrid.style.display = 'none';
      emptyState.style.display = 'flex';
      var msgs = {
        all:       '这里还没有礼物故事。',
        favorites: '你还没有收藏任何故事。\u003cbr\u003e也许有些旧物，会在某个时刻与你相遇。',
        mine:      '你还没有发布过礼物。\u003cbr\u003e也许现在就是写下第一个故事的时刻。',
        my_favorites: '你还没有收藏任何故事。\u003cbr\u003e也许有些旧物，会在某个时刻与你相遇。',
        my_actions: '你还没有任何操作记录。\u003cbr\u003e当你编辑、提交、归档或恢复礼物时，这里会留下痕迹。',
        sell:      '这一类礼物暂时还没有故事。',
        exchange:  '这一类礼物暂时还没有故事。',
        giveaway:  '这一类礼物暂时还没有故事。',
        donate:    '这一类礼物暂时还没有故事。',
        keep:      '这一类礼物暂时还没有故事。'
      };
      // Override for search empty state
      if (currentSearch) {
        emptyStateLine.innerHTML = '没有找到匹配的礼物。也许换一个词，它会以另一种方式出现。';
      } else {
        emptyStateLine.innerHTML = msgs[currentFilter] || '这一类礼物暂时还没有故事。';
      }
      if (loadMoreBtn) loadMoreBtn.style.display = 'none';
      return;
    }

    emptyState.style.display = 'none';
    giftGrid.style.display = '';

    // Paginate
    var toShow = filtered.slice(0, displayedCount);
    giftGrid.innerHTML = toShow.map(function (g) { return giftCardHTML(g); }).join('');

    // Load more button
    if (loadMoreBtn) {
      if (displayedCount >= filtered.length) {
        loadMoreBtn.style.display = 'none';
      } else {
        loadMoreBtn.style.display = '';
        var remaining = filtered.length - displayedCount;
        loadMoreBtn.textContent = '阅读更多故事（还剩 ' + remaining + ' 件）';
      }
    }

    bindCardEvents();
    updateFavoriteHearts();
  }

  function updateFavoriteHearts() {
    document.querySelectorAll('.card-favorite-btn').forEach(function (btn) {
      var id = btn.getAttribute('data-id');
      if (id) updateHeartIcon(btn, !!favorites[id]);
    });
  }

  function bindCardEvents() {
    giftGrid.querySelectorAll('.gift-card').forEach(function (card) {
      card.addEventListener('click', function (e) {
        if (e.target.closest('.card-favorite-btn')) return;
        if (e.target.closest('.mine-action-btn')) return;
        var id = card.getAttribute('data-id');
        openModal(id);
      });
    });
    giftGrid.querySelectorAll('.card-favorite-btn').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var id = btn.getAttribute('data-id');
        if (id) toggleFavorite(id);
      });
    });
    // Phase 2H-1: Mine action buttons
    giftGrid.querySelectorAll('.mine-action-btn').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var action = btn.getAttribute('data-action');
        var id = btn.getAttribute('data-id');
        if (action && id) handleMineAction(action, id);
      });
    });
  }

  function giftCardHTML(g) {
    var actionClass = 'action-' + g.action;
    var emotionIcon = emotionIconSVG(g.emotion);
    var isFav = !!favorites[g.id] || g.is_favorited;
    var favClass = isFav ? 'favorited' : '';
    // Status badge for mine view
    var statusBadge = '';
    if (currentFilter === 'mine' && g.status) {
      var statusLabels = {
        published: '已发布',
        pending_review: '待审核',
        needs_edit: '需修改',
        rejected: '已拒绝',
        draft: '草稿',
        archived: '已归档'
      };
      var statusClass = 'status-' + g.status;
      statusBadge = '<span class="gift-card-status-badge ' + statusClass + '" data-status="' + g.status + '">' + escHtml(statusLabels[g.status] || g.status) + '</span>';
    }
    // Favorite created at for my_favorites view
    var favTime = '';
    if (currentFilter === 'my_favorites' && g.favorite_created_at) {
      favTime = '<span class="gift-card-fav-time">收藏于 ' + escHtml(g.favorite_created_at) + '</span>';
    }
    // Phase 2H-1/2H-2: Action buttons for mine view
    var mineActions = '';
    if (currentFilter === 'mine' && g.status) {
      var editable = { draft: true, pending_review: true, needs_edit: true };
      var resubmittable = { draft: true, needs_edit: true };
      var archivable = { published: true, pending_review: true, needs_edit: true };
      var restorable = { archived: true };
      var btns = [];
      if (editable[g.status]) {
        btns.push('<button class="btn btn-sm btn-ghost mine-action-btn" data-action="edit" data-id="' + escHtml(g.id) + '">编辑故事</button>');
      }
      if (resubmittable[g.status]) {
        btns.push('<button class="btn btn-sm btn-secondary mine-action-btn" data-action="resubmit" data-id="' + escHtml(g.id) + '">重新提交</button>');
      }
      if (archivable[g.status]) {
        btns.push('<button class="btn btn-sm btn-ghost mine-action-btn" data-action="archive" data-id="' + escHtml(g.id) + '">暂时收起</button>');
      }
      if (restorable[g.status]) {
        btns.push('<button class="btn btn-sm btn-primary mine-action-btn restore" data-action="restore" data-id="' + escHtml(g.id) + '">恢复审核</button>');
      }
      if (btns.length) {
        mineActions = '<div class="gift-card-mine-actions">' + btns.join('') + '</div>';
      }
    }
    return '<article class="gift-card" data-id="' + g.id + '" tabindex="0" role="button" aria-label="查看礼物「' + escHtml(g.name) + '」的完整故事">' +
      '<button class="card-favorite-btn ' + favClass + '" data-id="' + g.id + '" aria-label="' + (isFav ? '取消收藏' : '收藏故事') + '" tabindex="0">' +
        '<svg viewBox="0 0 20 20" fill="' + (isFav ? 'currentColor' : 'none') + '" stroke="currentColor" stroke-width="1.5" width="16" height="16" aria-hidden="true"><path d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z"/></svg>' +
      '</button>' +
      '<div class="gift-card-header">' +
        '<h3 class="gift-card-title">' + escHtml(g.name) + '</h3>' +
        '<span class="gift-card-action ' + actionClass + '">' + escHtml(g.actionLabel) + '</span>' +
      '</div>' +
      '<div class="gift-card-meta">' +
        '<span class="gift-card-tag">' + escHtml(g.type) + '</span>' +
        '<span class="gift-card-tag">' + escHtml(g.relationLabel || g.relation || '') + '</span>' +
        '<span class="gift-card-emotion">' + emotionIcon + escHtml(g.emotion) + '</span>' +
      '</div>' +
      '<p class="gift-card-excerpt">' + escHtml(g.excerpt) + '</p>' +
      '<div class="gift-card-footer">' +
        '<span class="gift-card-price">' + escHtml(g.price) + '</span>' +
        statusBadge +
        favTime +
      '</div>' +
      mineActions +
    '</article>';
  }

  function emptyStateHTML(msg) {
    return '<div class="empty-state" role="status">' +
      '<div class="empty-state-icon" aria-hidden="true"></div>' +
      '<p class="empty-state-line">' + escHtml(msg) + '</p>' +
      '<p class="empty-state-sub">也许下一件被温柔送走的旧物，就会出现在这里。</p>' +
    '</div>';
  }

  function emotionIconSVG(emotion) {
    var icons = {
      '放下':  '<svg viewBox="0 0 16 16" fill="none" width="12" height="12" aria-hidden="true"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.2"/><path d="M5 8h6" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>',
      '遗憾':  '<svg viewBox="0 0 16 16" fill="none" width="12" height="12" aria-hidden="true"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.2"/><path d="M8 5v3l2 2" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>',
      '感谢':  '<svg viewBox="0 0 16 16" fill="none" width="12" height="12" aria-hidden="true"><path d="M8 3l1.5 3 3.5.5-2.5 2.5.5 3.5L8 11.5 4.5 13l.5-3.5L3 8.5l3.5-.5z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg>',
      '释怀':  '<svg viewBox="0 0 16 16" fill="none" width="12" height="12" aria-hidden="true"><path d="M3 8h10M10 5l3 3-3 3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
      '重启':  '<svg viewBox="0 0 16 16" fill="none" width="12" height="12" aria-hidden="true"><path d="M13 8A5 5 0 1 1 8 3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/><path d="M11 3h3v3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
      '纪念':  '<svg viewBox="0 0 16 16" fill="none" width="12" height="12" aria-hidden="true"><path d="M8 3v10M5 6l3-3 3 3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
      '治愈':  '<svg viewBox="0 0 16 16" fill="none" width="12" height="12" aria-hidden="true"><path d="M8 3c-2 2-2 5 0 7s2 5 0 7" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>',
      '平静':  '<svg viewBox="0 0 16 16" fill="none" width="12" height="12" aria-hidden="true"><path d="M2 10c2-3 4-3 6 0s4 3 6 0" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>'
    };
    return icons[emotion] || '';
  }

  // ── Modal ──
  function openModal(id) {
    var g = findGiftById(id);
    if (!g) return;

    lastFocusedElement = document.activeElement;

    var actionClass = 'action-' + g.action;
    var safetyNoteMap = {
      keep:     '这件礼物的主人选择只分享故事，不进行流转。如故事中有可识别信息，欢迎举报。',
      sell:     '出售中 · 平台不参与真实交易，不托管资金。如有交易纠纷请自行承担风险。',
      exchange: '交换意向 · 平台不参与真实交换撮合，双方需自行约定交换方式。',
      giveaway: '免费赠送 · 请仔细阅读故事描述，确认你真的需要它再联系发布者。',
      donate:   '捐赠物 · 这件礼物由发布者免费捐出，欢迎有需要的人认领。'
    };
    var safetyNote = safetyNoteMap[g.action] || '平台不参与真实交易，如有问题请联系发布者。';
    var relationDisplay = (g.anonymous || !g.relationLabel) ? '' : escHtml(g.relationLabel);
    var isFav = !!favorites[g.id];

    modalBody.innerHTML =
      '<div class="modal-gift-header">' +
        '<h2 class="modal-gift-title" id="modalTitle">' + escHtml(g.name) + '</h2>' +
        '<div class="modal-gift-meta">' +
          '<span class="gift-card-action ' + actionClass + '">' + escHtml(g.actionLabel) + '</span>' +
          '<span class="gift-card-tag">' + escHtml(g.type) + '</span>' +
          (relationDisplay ? '<span class="gift-card-tag">' + relationDisplay + '</span>' : '') +
          '<span class="modal-gift-emotion">' + emotionIconSVG(g.emotion) + ' ' + escHtml(g.emotion) + '</span>' +
        '</div>' +
        '<div class="modal-gift-price">' + escHtml(g.price) + '</div>' +
      '</div>' +
      '<div class="modal-divider"></div>' +
      '<p class="modal-story-label">礼物故事</p>' +
      '<div class="modal-story">' + escHtml(g.fullStory) + '</div>' +
      '<div class="modal-safety-note" role="note">' +
        '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 2L3 5v5c0 4.4 3 7.5 7 8.5 4-1 7-4.1 7-8.5V5L10 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>' +
        '<span>' + escHtml(safetyNote) + '</span>' +
      '</div>' +
      '<div class="modal-actions">' +
        (g.action === 'sell'     ? '<button class="btn btn-primary" data-action-btn="take"><svg viewBox="0 0 20 20" fill="none" width="16" height="16" aria-hidden="true"><path d="M10 2v11l4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="10" cy="10" r="8" stroke="currentColor" stroke-width="1.5"/></svg>我想带走它</button>' : '') +
        (g.action === 'exchange'  ? '<button class="btn btn-primary" data-action-btn="exchange"><svg viewBox="0 0 20 20" fill="none" width="16" height="16" aria-hidden="true"><path d="M4 10h12M14 6l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>我想交换</button>' : '') +
        (g.action === 'giveaway'  ? '<button class="btn btn-primary" data-action-btn="claim"><svg viewBox="0 0 20 20" fill="none" width="16" height="16" aria-hidden="true"><path d="M10 3v14M5 12l5-5 5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>我想领取</button>' : '') +
        (g.action === 'donate'    ? '<button class="btn btn-primary" data-action-btn="claim"><svg viewBox="0 0 20 20" fill="none" width="16" height="16" aria-hidden="true"><path d="M3 10h14M10 3v14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>我想认领</button>' : '') +
        '<button class="btn btn-secondary' + (isFav ? ' favorited' : '') + '" id="modalFavoriteBtn" data-action-btn="save" data-id="' + escHtml(g.id) + '">' +
          '<svg viewBox="0 0 20 20" fill="' + (isFav ? 'currentColor' : 'none') + '" stroke="currentColor" stroke-width="1.5" width="16" height="16" aria-hidden="true"><path d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z"/></svg>' +
          (isFav ? '已收藏' : '收藏故事') +
        '</button>' +
        '<button class="btn btn-ghost" data-action-btn="report" style="color:var(--accent-2)"><svg viewBox="0 0 20 20" fill="none" width="16" height="16" aria-hidden="true"><path d="M3 10c0-4 3-7 7-7s7 3 7 7-3 7-7 7-7-3-7-7z" stroke="currentColor" stroke-width="1.5"/><path d="M10 7v3l2 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>举报隐私问题</button>' +
      '</div>' +
      // Phase 2L-1: gentle hint for favorited items
      (isFav ? '<div class="modal-fav-hint" aria-live="polite">这个故事已经被放进你的收藏。</div>' : '');

    modalBody.querySelectorAll('[data-action-btn]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var action = btn.getAttribute('data-action-btn');
        var id = btn.getAttribute('data-id') || g.id;
        handleModalAction(action, g, id);
      });
    });

    modalOverlay.classList.add('open');
    modalOverlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

    var firstBtn = modalBody.querySelector('[data-action-btn]') || modalClose;
    if (firstBtn) firstBtn.focus();

    // Phase 2I-1: Load similar stories
    loadSimilarStories(g.id);
  }

  function handleModalAction(action, gift, id) {
    if (action === 'save') {
      toggleFavorite(id || gift.id);
      return;
    }
    if (action === 'report') {
      var mode = window.__AF_MODE || 'static';
      if (mode === 'api' && window.AftergiftAPI) {
        window.AftergiftAPI.reportGift(id || gift.id, { reason: 'privacy_risk', detail: '' }).then(function () {
          showToast('感谢反馈，我们已收到举报，会尽快审核该故事');
        }).catch(function () {
          showToast('举报已记录（本地演示）');
        });
      } else {
        showToast('感谢反馈，我们已收到举报，会尽快审核该故事');
      }
      return;
    }
    var messages = {
      take:     '意向已记录：你想带走「' + gift.name + '」（原型阶段，无真实交易）',
      exchange: '交换意向已记录：你想用礼物交换「' + gift.name + '」（原型阶段，请自行约定）',
      claim:    '领取意向已记录：「' + gift.name + '」（原型阶段，请自行联系发布者）',
    };
    showToast(messages[action] || '已收到你的操作');
  }

  // ── Phase 2H-1: My Gift Management Actions ──
  function handleMineAction(action, id) {
    var mode = window.__AF_MODE || 'static';
    if (mode !== 'api' || !window.AftergiftAPI) {
      showToast('此功能仅在 API 模式下可用');
      return;
    }
    if (action === 'edit') {
      openEditModal(id);
      return;
    }
    if (action === 'resubmit') {
      window.AftergiftAPI.resubmitMyGift(id).then(function () {
        showToast('已重新进入审核队列');
        loadGifts();
      }).catch(function (err) {
        showToast('重新提交失败：' + (err.message || ''));
      });
      return;
    }
    if (action === 'archive') {
      window.AftergiftAPI.archiveMyGift(id).then(function () {
        showToast('这件礼物已暂时收起');
        loadGifts();
      }).catch(function (err) {
        showToast('归档失败：' + (err.message || ''));
      });
      return;
    }
    if (action === 'restore') {
      window.AftergiftAPI.restoreMyGift(id).then(function () {
        showToast('这件礼物已重新进入审核');
        loadGifts();
      }).catch(function (err) {
        showToast('恢复失败：' + (err.message || ''));
      });
      return;
    }
  }

  // ── Phase 2H-1: Edit Modal ──
  function openEditModal(giftId) {
    var mode = window.__AF_MODE || 'static';
    if (mode !== 'api' || !window.AftergiftAPI) {
      showToast('此功能仅在 API 模式下可用');
      return;
    }
    window.AftergiftAPI.getMyGift(giftId).then(function (g) {
      lastFocusedElement = document.activeElement;
      modalBody.innerHTML = buildEditFormHTML(g);
      modalOverlay.classList.add('open');
      modalOverlay.setAttribute('aria-hidden', 'false');
      document.body.style.overflow = 'hidden';
      bindEditFormEvents(giftId);
      var firstInput = modalBody.querySelector('input, textarea, select');
      if (firstInput) firstInput.focus();
    }).catch(function (err) {
      showToast('加载礼物详情失败：' + (err.message || ''));
    });
  }

  function buildEditFormHTML(g) {
    var actionOptions = [
      { value: 'sell', label: '出售' },
      { value: 'exchange', label: '交换' },
      { value: 'giveaway', label: '赠送' },
      { value: 'donate', label: '捐出' },
      { value: 'keep', label: '只讲故事' }
    ];
    var actionSelect = actionOptions.map(function (opt) {
      return '<option value="' + opt.value + '"' + (g.action === opt.value ? ' selected' : '') + '>' + opt.label + '</option>';
    }).join('');

    var relationOptions = [
      { value: 'lover', label: '恋人' },
      { value: 'spouse', label: '夫妻' },
      { value: 'friend', label: '朋友' },
      { value: 'family', label: '家人' },
      { value: 'colleague', label: '同事' },
      { value: 'other', label: '其他' }
    ];
    var relationSelect = relationOptions.map(function (opt) {
      return '<option value="' + opt.value + '"' + (g.relation === opt.value ? ' selected' : '') + '>' + opt.label + '</option>';
    }).join('');

    var emotionOptions = ['放下', '遗憾', '感谢', '释怀', '重启', '纪念', '治愈', '平静'];
    var emotionSelect = emotionOptions.map(function (opt) {
      return '<option value="' + opt + '"' + (g.emotion === opt ? ' selected' : '') + '>' + opt + '</option>';
    }).join('');

    var reviewNoteHtml = '';
    if (g.review_note) {
      reviewNoteHtml = '<div class="edit-review-note"><strong>审核备注：</strong> ' + escHtml(g.review_note) + '</div>';
    }

    // Phase 2H-2: Draft auto-save notice
    var draftKey = 'aftergift_edit_draft_' + g.id;
    var draftNotice = '';
    try {
      var draft = localStorage.getItem(draftKey);
      if (draft) {
        draftNotice = '<div class="edit-draft-notice"><span>发现未保存的编辑草稿。</span><div class="edit-draft-actions"><button type="button" class="btn btn-sm btn-primary" id="editRestoreDraftBtn">恢复草稿</button><button type="button" class="btn btn-sm btn-ghost" id="editDiscardDraftBtn">丢弃草稿</button></div></div>';
      }
    } catch (e) {}

    var html = '<div class="edit-modal-header">' +
      '<h2 class="edit-modal-title">编辑故事</h2>' +
      '<span class="edit-modal-status">状态：' + escHtml(g.status || '') + '</span>' +
    '</div>' +
    reviewNoteHtml +
    draftNotice +
    '<form id="editGiftForm" class="edit-form">' +
      '<div class="form-group"><label class="form-label">礼物名称</label><input type="text" class="form-input" name="title" value="' + escHtml(g.name || '') + '" required></div>' +
      '<div class="form-group"><label class="form-label">礼物类型</label><input type="text" class="form-input" name="category" value="' + escHtml(g.type || '') + '" required></div>' +
      '<div class="form-group"><label class="form-label">关系类型</label><select class="form-select" name="relation_type">' + relationSelect + '</select></div>' +
      '<div class="form-group"><label class="form-label">处理方式</label><select class="form-select" name="action_type">' + actionSelect + '</select></div>' +
      '<div class="form-group"><label class="form-label">情绪标签</label><select class="form-select" name="emotion">' + emotionSelect + '</select></div>' +
      '<div class="form-group"><label class="form-label">价格或交换意向</label><input type="text" class="form-input" name="price_or_exchange" value="' + escHtml(g.price || '') + '"></div>' +
      '<div class="form-group"><label class="form-label">一句话故事</label><textarea class="form-textarea" name="short_story" rows="3" required>' + escHtml(g.excerpt || g.shortStory || '') + '</textarea></div>' +
      '<div class="form-group"><label class="form-label">完整故事</label><textarea class="form-textarea" name="full_story" rows="6" required>' + escHtml(g.fullStory || '') + '</textarea></div>' +
      '<div class="form-group form-checkbox"><label><input type="checkbox" name="is_anonymous"' + (g.anonymous ? ' checked' : '') + '> 匿名发布</label></div>' +
      '<div class="edit-form-actions">' +
        '<button type="submit" class="btn btn-primary">保存修改</button>' +
        '<button type="button" class="btn btn-ghost" id="editCancelBtn">取消</button>' +
      '</div>' +
    '</form>';
    return html;
  }

  function bindEditFormEvents(giftId) {
    var form = document.getElementById('editGiftForm');
    var cancelBtn = document.getElementById('editCancelBtn');
    var draftKey = 'aftergift_edit_draft_' + giftId;
    var draftTimer = null;

    // Phase 2H-2: Auto-save draft on input
    if (form) {
      form.addEventListener('input', function () {
        if (draftTimer) clearTimeout(draftTimer);
        draftTimer = setTimeout(function () {
          try {
            var fd = new FormData(form);
            var draft = {};
            fd.forEach(function (v, k) {
              if (k === 'is_anonymous') draft[k] = true;
              else draft[k] = v;
            });
            if (!draft.hasOwnProperty('is_anonymous')) draft.is_anonymous = false;
            localStorage.setItem(draftKey, JSON.stringify(draft));
          } catch (e) {}
        }, 800);
      });
    }

    // Restore draft button
    var restoreDraftBtn = document.getElementById('editRestoreDraftBtn');
    if (restoreDraftBtn) {
      restoreDraftBtn.addEventListener('click', function () {
        try {
          var draft = JSON.parse(localStorage.getItem(draftKey) || '{}');
          for (var k in draft) {
            var el = form.querySelector('[name="' + k + '"]');
            if (!el) continue;
            if (el.type === 'checkbox') {
              el.checked = !!draft[k];
            } else {
              el.value = draft[k];
            }
          }
          showToast('草稿已恢复');
        } catch (e) {}
      });
    }

    // Discard draft button
    var discardDraftBtn = document.getElementById('editDiscardDraftBtn');
    if (discardDraftBtn) {
      discardDraftBtn.addEventListener('click', function () {
        try {
          localStorage.removeItem(draftKey);
          var notice = document.querySelector('.edit-draft-notice');
          if (notice) notice.remove();
        } catch (e) {}
      });
    }

    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var fd = new FormData(form);
        var payload = {};
        fd.forEach(function (v, k) {
          if (k === 'is_anonymous') {
            payload[k] = true;
          } else {
            payload[k] = v;
          }
        });
        if (!payload.hasOwnProperty('is_anonymous')) payload.is_anonymous = false;
        window.AftergiftAPI.updateMyGift(giftId, payload).then(function () {
          // Clear draft on success
          try { localStorage.removeItem(draftKey); } catch (e) {}
          showToast('修改已保存');
          closeModal();
          loadGifts();
        }).catch(function (err) {
          showToast('保存失败：' + (err.message || ''));
        });
      });
    }
    if (cancelBtn) {
      cancelBtn.addEventListener('click', function () {
        closeModal();
      });
    }
  }

  function findGiftById(id) {
    for (var i = 0; i < gifts.length; i++) {
      if (gifts[i].id === id) return gifts[i];
    }
    return null;
  }

  function closeModal() {
    modalOverlay.classList.remove('open');
    modalOverlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    if (lastFocusedElement && lastFocusedElement.focus) {
      lastFocusedElement.focus();
    }
  }

  // ── Toast ──
  window.showToast = function (msg) {
    var existing = document.querySelector('.toast');
    if (existing) existing.remove();
    var t = document.createElement('div');
    t.className = 'toast';
    t.setAttribute('role', 'status');
    t.setAttribute('aria-live', 'polite');
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.classList.add('show'); }, 10);
    setTimeout(function () {
      t.classList.remove('show');
      setTimeout(function () { t.remove(); }, 300);
    }, 2800);
  };

  // ── Story Quality Check ──
  function checkStoryQuality(fullStory) {
    var len = (fullStory || '').length;
    var issues = [];
    if (len < 50) {
      issues.push({ type: 'too_short', msg: '这个故事有点短（' + len + ' 字），再写一点点，别人会更理解这件礼物为什么重要。' });
    }
    if (!/来|得到|收到|赠|送|买|带|到/.test(fullStory)) {
      issues.push({ type: 'no_origin', msg: '你已经写到了告别，但也许可以补充一下：这件礼物最初是怎么来到你手上的。' });
    }
    if (!/重要|喜欢|陪伴|记得|想起|当时|曾经|意义|珍惜/.test(fullStory)) {
      issues.push({ type: 'no_meaning', msg: '如果能再写一句它曾经对你意味着什么，这个故事会更完整。' });
    }
    if (!/现在|离开|告别|不再|结束|分手|走了|想让|要让|捐|送|换|卖/.test(fullStory)) {
      issues.push({ type: 'no_departure', msg: '你已经表达了感情，也许可以再写一句：为什么现在想让这件礼物离开。' });
    }
    if (!/希望|愿|以后|将来|下一位|新主人|继续|用到|使用/.test(fullStory)) {
      issues.push({ type: 'no_destination', msg: '如果你愿意，可以再补一句：希望这件礼物去往怎样的下一站。' });
    }
    return issues;
  }

  // ── Anonymization Suggestions ──
  var ANONYMIZATION_RULES = [
    { pattern: /[A-Za-z\u4e00-\u9fa5]{2,4}(?:\s*)(?:叫|name|named)[\s:：]+[A-Za-z\u4e00-\u9fa5]{2,4}/g,
      type: 'real_name', label: '暴露真实姓名',
      reason: '真实姓名会让读者识别出当事人',
      suggest: '那个人 / TA / 我曾在乎的人' },
    { pattern: /1[3-9]\d[\s\-]?\d{4}[\s\-]?\d{4}/g,
      type: 'phone', label: '手机号码',
      reason: '手机号可以直接联系到当事人',
      suggest: '后来我们不再联系了' },
    { pattern: /(?:微[信号渠道公众号]|wechat|weixin|wx)[^\s，,。！!]{0,20}/g,
      type: 'wechat', label: '微信号',
      reason: '微信号是私密社交账号，不应公开',
      suggest: '我们后来失去了联系' },
    { pattern: /[qqQ]{2}[^\u4e00-\u9fa5]{0,5}[0-9]{5,}/g,
      type: 'qq', label: 'QQ 号',
      reason: 'QQ 号可以定位到具体个人',
      suggest: '我们后来失去了联系' },
    { pattern: /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g,
      type: 'email', label: '邮箱地址',
      reason: '邮箱是私人联系方式',
      suggest: '我们后来失去了联系' },
    { pattern: /渣男|渣女|报复|曝光|挂人|人肉/g,
      type: 'revenge', label: '报复性表达',
      reason: '这类表达可能引发网暴或伤害他人',
      suggest: '这段关系让我失去了信任 / 让我感到受伤' },
    { pattern: /去死|该死|恨死|恶心死了|想打|想杀|想弄死/g,
      type: 'curse', label: '诅咒性表达',
      reason: '在愤怒时写下的诅咒往往不是真实意愿，但可能引发传播风险',
      suggest: '把感受写出来，但不要用伤害性的语言' },
    { pattern: /(?:他|她|TA|那个人)\s*(?:住在|在|工作于|任职于)\s*[^\s，,。]{2,20}(?:公司|大厦|广场|医院|学校|小区|街道|路|街)/g,
      type: 'location', label: '可识别地点',
      reason: '具体地点+公司/学校等组合可以定位到具体个人',
      suggest: '那个人工作的地方 / 我们曾住在同一座城市' },
    { pattern: /(?:我们|我)住(?:在|于)?([^\s，,。]{2,10})(?:小区|公寓|楼|家|宿舍|房子)/g,
      type: 'address', label: '住址信息',
      reason: '小区名称+楼栋单元可以精确定位住址',
      suggest: '我们曾经住得很近 / 后来搬到了不同的地方' }
  ];

  function getAnonymizationSuggestions(text) {
    var suggestions = [];
    ANONYMIZATION_RULES.forEach(function (rule) {
      var matches = text.match(rule.pattern);
      if (matches) {
        matches.forEach(function (match) {
          suggestions.push({
            type: rule.type,
            label: rule.label,
            original: match,
            reason: rule.reason,
            suggest: rule.suggest
          });
        });
      }
    });
    return suggestions;
  }

  // ── AI Review Panel ──
  function runAIReview() {
    var excerpt = (document.getElementById('excerpt') || {}).value || '';
    var fullStory = (document.getElementById('fullStory') || {}).value || '';
    var combined = excerpt + '\n' + fullStory;

    var mode = window.__AF_MODE || 'static';

    // Phase 2C: Try API review first in api mode
    if (mode === 'api' && window.AftergiftAPI) {
      window.AftergiftAPI.reviewStory(excerpt, fullStory).then(function (apiResult) {
        if (apiResult) {
          renderAPIReview(apiResult, combined);
        } else {
          runLocalReview(combined);
        }
      }).catch(function () {
        runLocalReview(combined);
      });
    } else {
      runLocalReview(combined);
    }
  }

  function renderAPIReview(apiResult, combined) {
    // Render results from FastAPI backend review endpoint
    var level = apiResult.risk_level || 'safe';
    var issues = apiResult.issues || [];
    var totalRisks = issues.length;
    var levelText, levelClass;
    if (level === 'safe') { levelText = '适合公开'; levelClass = 'level-safe'; }
    else if (level === 'caution') { levelText = '建议修改后公开'; levelClass = 'level-caution'; }
    else { levelText = '不建议直接公开'; levelClass = 'level-risk'; }

    var icons = {
      safe:   '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/><path d="M8 12l3 3 5-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
      caution: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/><path d="M12 8v4M12 14.5v.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
      risk:   '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/><path d="M12 7v5M12 15.5v.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'
    };

    var html = '<div class="ai-review-header ' + levelClass + '">' +
      icons[level] + '<span>' + levelText + '</span>' +
      '<span class="ai-review-count">（' + totalRisks + ' 处风险）</span>' +
      '</div>';

    if (issues.length > 0) {
      html += '<div class="ai-review-section">';
      html += '<div class="ai-review-subject">审核意见</div>';
      issues.forEach(function (issue) {
        var issueClass = issue.type === 'identity' ? 'ai-issue-warn' : (issue.type === 'attack' ? 'ai-issue-risk' : 'ai-issue-warn');
        html += '<div class="ai-review-issue ' + issueClass + '">' + escHtml(issue.msg || issue) + '</div>';
      });
      html += '</div>';
    } else {
      html += '<div class="ai-review-section"><div class="ai-review-issue ai-issue-safe">未检测到明显风险内容。</div></div>';
    }

    if (apiResult.suggestions && apiResult.suggestions.length > 0) {
      html += '<div class="ai-review-section"><div class="ai-review-subject">修改建议</div>';
      apiResult.suggestions.forEach(function (s) {
        html += '<div class="ai-review-issue ai-issue-note">' + escHtml(s) + '</div>';
      });
      html += '</div>';
    }

    aiReviewPanel.innerHTML = html;
    aiReviewPanel.classList.add('show');
  }

  function runLocalReview(combined) {

    // Gather findings
    var identityFindings = [];
    var revengeFindings = [];
    var identifiableFindings = [];

    var identityPatterns = [
      { pattern: /1[3-9]\d[\s\-]?\d{4}[\s\-]?\d{4}/g, msg: '检测到手机号码格式' },
      { pattern: /微[信渠道公众号号]|wechat|weixin|wx\.|WX\.|加我微信|微信号/g, msg: '检测到微信号信息' },
      { pattern: /[qqQ]{2}[\s\-]?[0-9]{5,}/g, msg: '检测到 QQ 号格式' },
      { pattern: /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g, msg: '检测到邮箱地址' },
      { pattern: /\d{3}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{2}[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d/g, msg: '检测到身份证格式数字' },
      { pattern: /[小区楼栋单元门牌住址家宅搬家公司宿舍学校医院街道路号弄]/g, msg: '检测到地址关键词' },
      { pattern: /微博账号|抖音号|小红书号|Instagram|Twitter|X账号|Telegram|电报群/g, msg: '检测到社交平台账号' },
      { pattern: /[省市县区街路道][a-zA-Z0-9\u4e00-\u9fa5]{2,10}(?:大厦|广场|中心|大楼|花园|公寓|学校|医院|公司)/g, msg: '检测到具体场所名称' }
    ];

    var revengePatterns = [
      { pattern: /渣男|渣女|报复|曝光|挂人|人肉搜索|人肉|骗子|毁掉/g, msg: '检测到报复性或控诉性词汇' },
      { pattern: /去死|该死|恨死|恶心死了|想打|想杀|想弄死/g, msg: '检测到诅咒类表达' },
      { pattern: /贱|不要脸|无耻|恶心|下头|下头男|下头女/g, msg: '检测到攻击性词汇' }
    ];

    var identifiablePatterns = [
      { pattern: /(?:他|她|TA|那个人|前任|老公|老婆|男朋友|女朋友|父亲|母亲|爸爸|妈妈|哥哥|姐姐|弟弟|妹妹)\s*叫\s*[A-Za-z\u4e00-\u9fa5]{2,4}/g, msg: '检测到"XXX 叫 XXX"姓名暴露格式' },
      { pattern: /姓名[:：]\s*[A-Za-z\u4e00-\u9fa5]{2,4}/g, msg: '检测到"姓名：XXX"格式' },
      { pattern: /全名\s*[A-Za-z\u4e00-\u9fa5]{2,4}/g, msg: '检测到全名暴露' }
    ];

    identityPatterns.forEach(function (p) {
      if (p.pattern.test(combined)) identityFindings.push(p.msg);
    });
    revengePatterns.forEach(function (p) {
      if (p.pattern.test(combined)) revengeFindings.push(p.msg);
    });
    identifiablePatterns.forEach(function (p) {
      if (p.pattern.test(combined)) identifiableFindings.push(p.msg);
    });

    var qualityIssues = checkStoryQuality(fullStory);
    var anonSuggestions = getAnonymizationSuggestions(combined);

    var totalRisks = identityFindings.length + revengeFindings.length + identifiableFindings.length;
    var level, levelText, levelClass;
    if (totalRisks === 0) {
      level = 'safe'; levelText = '适合公开'; levelClass = 'level-safe';
    } else if (totalRisks <= 2) {
      level = 'caution'; levelText = '建议修改后公开'; levelClass = 'level-caution';
    } else {
      level = 'risk'; levelText = '不建议直接公开'; levelClass = 'level-risk';
    }

    var icons = {
      safe:   '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/><path d="M8 12l3 3 5-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
      caution: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/><path d="M12 8v4M12 14.5v.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
      risk:   '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/><path d="M12 7v5M12 15.5v.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'
    };

    var html = '<div class="ai-review-header ' + levelClass + '">' +
      icons[level] + '<span>' + levelText + '</span>' +
      '<span class="ai-review-count">（' + totalRisks + ' 处风险）</span>' +
      '</div>';

    // Identity section
    html += '<div class="ai-review-section">';
    if (identityFindings.length > 0) {
      html += '<div class="ai-review-subject">身份信息风险</div>';
      identityFindings.forEach(function (m) { html += '<div class="ai-review-issue ai-issue-warn">' + escHtml(m) + '</div>'; });
    }
    if (revengeFindings.length > 0) {
      html += '<div class="ai-review-subject">报复 / 攻击性表达</div>';
      revengeFindings.forEach(function (m) { html += '<div class="ai-review-issue ai-issue-risk">' + escHtml(m) + '</div>'; });
    }
    if (identifiableFindings.length > 0) {
      html += '<div class="ai-review-subject">可识别关系对象</div>';
      identifiableFindings.forEach(function (m) { html += '<div class="ai-review-issue ai-issue-warn">' + escHtml(m) + '</div>'; });
    }
    if (identityFindings.length === 0 && revengeFindings.length === 0 && identifiableFindings.length === 0) {
      html += '<div class="ai-review-issue ai-issue-safe">未检测到明显的身份信息、报复性表达或可识别个人身份的内容。</div>';
    }
    html += '</div>';

    // Anonymization suggestions
    if (anonSuggestions.length > 0) {
      html += '<div class="ai-review-section"><div class="ai-review-subject">匿名化建议</div>';
      anonSuggestions.slice(0, 5).forEach(function (s) {
        html += '<div class="anon-suggestion">' +
          '<div class="anon-original"><span class="anon-badge anon-badge-' + escHtml(s.type) + '">' + escHtml(s.label) + '</span> ' + escHtml(s.original) + '</div>' +
          '<div class="anon-reason">→ ' + escHtml(s.reason) + '</div>' +
          '<div class="anon-suggest">建议改为：<strong>' + escHtml(s.suggest) + '</strong></div>' +
          '</div>';
      });
      if (anonSuggestions.length > 5) {
        html += '<div class="ai-review-note">还有 ' + (anonSuggestions.length - 5) + ' 处建议，已在上方高亮提示。</div>';
      }
      html += '</div>';
    }

    // Quality suggestions
    if (qualityIssues.length > 0) {
      html += '<div class="ai-review-section"><div class="ai-review-subject">故事完整度</div>';
      qualityIssues.forEach(function (q) {
        html += '<div class="ai-review-issue ai-issue-note">' + escHtml(q.msg) + '</div>';
      });
      html += '</div>';
    } else if (fullStory.length >= 50) {
      html += '<div class="ai-review-section"><div class="ai-review-issue ai-issue-safe">故事结构完整，包含来历、意义和告别理由。</div></div>';
    }

    // Copy suggestions button
    if (anonSuggestions.length > 0) {
      var copyText = anonSuggestions.map(function (s) {
        return '"' + s.original + '" → ' + s.suggest;
      }).join('\n');
      html += '<button class="ai-copy-btn" onclick="copyAIRewriteSuggestions()">复制匿名化建议</button>';
      window._currentRewriteSuggestions = copyText;
    }

    aiReviewPanel.innerHTML = html;
    aiReviewPanel.classList.add('show');
  }

  window.copyAIRewriteSuggestions = function () {
    var text = window._currentRewriteSuggestions || '';
    if (!text) return;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(function () {
        showToast('匿名化建议已复制到剪贴板');
      }).catch(function () {
        showToast('复制失败，请手动选择复制');
      });
    } else {
      showToast('复制失败，你的浏览器不支持剪贴板 API');
    }
  };

  // ── Story Pre-Check (Phase 1C compatibility) ──
  function runPreCheck() {
    runAIReview();
  }

  // ── Story Preview ──
  function getFormData() {
    var name      = (document.getElementById('giftName') || {}).value || '';
    var type      = (document.getElementById('giftType') || {}).value || '';
    var relation  = (document.getElementById('relation') || {}).value || '';
    var action    = (document.getElementById('action') || {}).value || '';
    var emotion   = (document.getElementById('emotion') || {}).value || '';
    var price     = (document.getElementById('price') || {}).value || '';
    var excerpt   = (document.getElementById('excerpt') || {}).value || '';
    var fullStory = (document.getElementById('fullStory') || {}).value || '';
    var anonymous = (document.getElementById('anonymous') || {}).checked || false;
    return { name: name, type: type, relation: relation, action: action, emotion: emotion, price: price, excerpt: excerpt, fullStory: fullStory, anonymous: anonymous };
  }

  function openPreviewModal() {
    var d = getFormData();
    if (!d.name || !d.type || !d.action || !d.excerpt) {
      showToast('请先填写礼物名称、类型、处理方式和故事摘录');
      return;
    }

    lastFocusedElement = document.activeElement;

    var actionLabels = { sell: '出售', exchange: '交换', giveaway: '赠送', donate: '捐出', keep: '只展示故事' };
    var actionClass = 'action-' + d.action;
    var relationDisplay = (d.anonymous || !d.relation) ? '' : escHtml(d.relation);
    var displayPrice = d.price || (d.action === 'keep' ? '非卖品，只讲故事' : '待定');

    modalBody.innerHTML =
      '<div class="modal-preview-banner">' +
        '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.5"/></svg>' +
        '<span><strong>这是别人将看到的样子。</strong>发布前，请再确认是否暴露了不该公开的信息。</span>' +
      '</div>' +
      '<span class="modal-preview-badge">预览效果</span>' +
      '<div class="modal-gift-header">' +
        '<h2 class="modal-gift-title" id="modalTitle">' + escHtml(d.name) + '</h2>' +
        '<div class="modal-gift-meta">' +
          '<span class="gift-card-action ' + actionClass + '">' + escHtml(actionLabels[d.action] || d.action) + '</span>' +
          '<span class="gift-card-tag">' + escHtml(d.type) + '</span>' +
          (relationDisplay ? '<span class="gift-card-tag">' + relationDisplay + '</span>' : '') +
          '<span class="modal-gift-emotion">' + emotionIconSVG(d.emotion) + ' ' + escHtml(d.emotion) + '</span>' +
        '</div>' +
        '<div class="modal-gift-price">' + escHtml(displayPrice) + '</div>' +
      '</div>' +
      '<div class="modal-divider"></div>' +
      '<p class="modal-story-label">礼物故事</p>' +
      '<div class="modal-story">' + escHtml(d.fullStory || d.excerpt) + '</div>' +
      '<div class="modal-safety-note" role="note">' +
        '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 2L3 5v5c0 4.4 3 7.5 7 8.5 4-1 7-4.1 7-8.5V5L10 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>' +
        '<span>故事发布后将公开可见，请确认内容适合公开阅读。</span>' +
      '</div>' +
      '<div class="modal-actions" style="margin-top:8px">' +
        '<button class="btn btn-secondary" id="previewCloseBtn" aria-label="关闭预览"><svg viewBox="0 0 20 20" fill="none" width="16" height="16" aria-hidden="true"><path d="M6 6l8 8M14 6l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>关闭预览</button>' +
      '</div>';

    document.getElementById('previewCloseBtn').addEventListener('click', closeModal);

    modalOverlay.classList.add('open');
    modalOverlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    document.getElementById('previewCloseBtn').focus();
  }

  // ── Phase 2I-1: Discovery Rails ───────────────────────────────────────────

  // ── Story Tips ──
  window.insertStoryTip = function (index) {
    var tip = STORY_TIPS[index];
    var ta = document.getElementById('fullStory');
    var current = (ta.value || '').trim();
    var insert = '\n\n— ' + tip + '\n';
    if (current.length === 0) {
      ta.value = tip + '\n\n';
    } else {
      ta.value = current + insert;
    }
    ta.focus();
    showToast('提示已添加，继续书写吧');
  };

  // ── Textarea auto-resize ──
  function initTextareas() {
    var textareas = document.querySelectorAll('textarea');
    textareas.forEach(function (ta) {
      function resize() {
        ta.style.height = 'auto';
        ta.style.height = ta.scrollHeight + 'px';
      }
      ta.addEventListener('input', resize);
      resize();
    });

    // Full story character count
    if (fullStoryInput && fullStoryCount) {
      fullStoryInput.addEventListener('input', function () {
        var len = fullStoryInput.value.length;
        fullStoryCount.textContent = len;
        if (storyQualityHint) {
          if (len > 0 && len < 50) {
            storyQualityHint.style.display = '';
            storyQualityHint.textContent = '再写一点点，别人会更理解这件礼物为什么重要。';
          } else {
            storyQualityHint.style.display = 'none';
          }
        }
      });
    }
  }

  // ── Publish Form ──
  function handleFormSubmit(e) {
    e.preventDefault();

    var c1 = (document.getElementById('confirm1') || {}).checked;
    var c2 = (document.getElementById('confirm2') || {}).checked;
    var c3 = (document.getElementById('confirm3') || {}).checked;

    if (!c1 || !c2 || !c3) {
      showToast('请先确认这个故事适合被公开阅读');
      return;
    }

    var d = getFormData();

    if (!d.name || !d.type || !d.action || !d.excerpt) {
      showToast('请填写礼物名称、类型、处理方式和故事摘录');
      return;
    }

    var actionLabels = { sell: '出售', exchange: '交换', giveaway: '赠送', donate: '捐出', keep: '只展示故事' };
    var statusMap = { sell: '出售中', exchange: '待流转', giveaway: '待认领', donate: '待捐出', keep: '故事保留' };

    var newGift = {
      id: 'temp-' + (nextTempId++),
      name: d.name,
      type: d.type,
      relation: d.relation || '',
      relationLabel: d.anonymous ? '' : (d.relation || ''),
      action: d.action,
      actionLabel: actionLabels[d.action] || d.action,
      emotion: d.emotion || '放下',
      excerpt: d.excerpt,
      fullStory: d.fullStory || d.excerpt,
      price: d.price || (d.action === 'keep' ? '非卖品，只讲故事' : '待定'),
      status: statusMap[d.action] || '待定',
      anonymous: d.anonymous,
      tags: [d.type]
    };

    // Phase 2C: API mode publish
    var mode = window.__AF_MODE || 'static';
    if (mode === 'api' && window.AftergiftAPI) {
      window.AftergiftAPI.createGift(d).then(function (result) {
        // Update temp gift with real ID if returned
        if (result && result.gift_id) {
          newGift.id = result.gift_id;
          if (result.status) {
            newGift.status = result.status === 'published' ? statusMap[d.action] : '审核中';
          }
        }
        var publishMsg = '礼物已发布';
        if (result && result.review) {
          if (result.review.risk_level === 'safe') {
            publishMsg = '礼物已发布';
          } else if (result.review.risk_level === 'caution') {
            publishMsg = '礼物已暂存，建议修改后再提交';
          } else {
            publishMsg = '礼物已提交审核';
          }
        }
        gifts.unshift(newGift);
        displayedCount = INITIAL_DISPLAY;
        renderGifts();
        publishForm.reset();
        resetFormState();
        scrollToSection('stories');
        showToast(publishMsg + '，愿你与它好好告别');
      }).catch(function () {
        // API error: still show locally
        gifts.unshift(newGift);
        displayedCount = INITIAL_DISPLAY;
        renderGifts();
        publishForm.reset();
        resetFormState();
        scrollToSection('stories');
        showToast('礼物已发布（本地演示），API 提交失败');
      });
      return;
    }

    // Static mode: local demo
    gifts.unshift(newGift);
    displayedCount = INITIAL_DISPLAY;
    renderGifts();
    publishForm.reset();
    resetFormState();
    scrollToSection('stories');
    showToast('礼物已发布，愿你与它好好告别');
  }

  function resetFormState() {
    emotionBtns.forEach(function (b) {
      b.classList.remove('selected');
      b.setAttribute('aria-pressed', 'false');
    });
    document.getElementById('emotion').value = '';
    if (excerptCount) excerptCount.textContent = '0';
    if (fullStoryCount) fullStoryCount.textContent = '0';
    document.getElementById('confirm1').checked = false;
    document.getElementById('confirm2').checked = false;
    document.getElementById('confirm3').checked = false;
    if (precheckCard) precheckCard.classList.remove('show');
    if (aiReviewPanel) aiReviewPanel.classList.remove('show');
    if (storyQualityHint) storyQualityHint.style.display = 'none';
    if (fullStoryInput) fullStoryInput.style.height = 'auto';
  }

  // ── Filter ──
  function handleFilterClick(e) {
    var btn = e.currentTarget;
    var filter = btn.getAttribute('data-filter');

    if (btn.classList.contains('active')) return;

    // Phase 2G-2: mine / my_favorites require auth in api mode
    var mode = window.__AF_MODE || 'static';
    if (mode === 'api' && (filter === 'mine' || filter === 'my_favorites' || filter === 'my_actions')) {
      var token = (window.AftergiftAPI && window.AftergiftAPI.getStoredToken) ? window.AftergiftAPI.getStoredToken() : null;
      if (!token) {
        var labelMap = { mine: '发布', my_favorites: '收藏', my_actions: '操作历史' };
        showToast('请先创建匿名身份，再查看你的' + (labelMap[filter] || '内容'));
        return;
      }
    }

    currentFilter = filter;
    displayedCount = INITIAL_DISPLAY;
    filterTabs.forEach(function (t) {
      t.classList.remove('active');
      t.setAttribute('aria-selected', 'false');
    });
    btn.classList.add('active');
    btn.setAttribute('aria-selected', 'true');

    if (mode === 'api' && window.AftergiftAPI) {
      if (filter === 'my_actions') {
        loadMyActions();
      } else {
        var params = buildListParams();
        window.AftergiftAPI.listGifts(params, []).then(function (result) {
          gifts = result.items;
          searchMeta = {
            total: result.total || 0,
            page: result.page || 1,
            limit: result.limit || 12,
            total_pages: result.total_pages || 0,
            has_more: result.has_more || false
          };
          renderGifts();
        }).catch(function (err) {
          if (err && err.message && err.message.indexOf('匿名身份') !== -1) {
            showToast(err.message);
          } else {
            showToast('无法加载筛选结果，请检查 API 连接');
          }
        });
      }
    } else {
      // Static mode: reload with filter + search
      loadStaticGifts();
    }
  }

  // ── Search ──
  function handleSearch() {
    var q = searchInput ? searchInput.value.trim() : '';
    currentSearch = q;
    displayedCount = INITIAL_DISPLAY;
    if (searchClearBtn) {
      searchClearBtn.style.display = q ? '' : 'none';
    }
    if (searchHint) {
      searchHint.style.display = q ? '' : 'none';
    }
    loadGifts();
  }

  function handleSearchClear() {
    if (searchInput) {
      searchInput.value = '';
    }
    currentSearch = '';
    displayedCount = INITIAL_DISPLAY;
    if (searchClearBtn) searchClearBtn.style.display = 'none';
    if (searchHint) searchHint.style.display = 'none';
    loadGifts();
  }

  function handleSearchKeydown(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSearch();
    }
  }

  // ── Load More ──
  function handleLoadMore() {
    displayedCount += INITIAL_DISPLAY;
    renderGifts();
    if (displayedCount >= MAX_DISPLAY) displayedCount = MAX_DISPLAY;
  }

  // ── Emotion Tags ──
  function handleEmotionClick(e) {
    var btn = e.currentTarget;
    var emotion = btn.getAttribute('data-emotion');
    var isSelected = btn.classList.contains('selected');

    emotionBtns.forEach(function (b) {
      b.classList.remove('selected');
      b.setAttribute('aria-pressed', 'false');
    });

    if (!isSelected) {
      btn.classList.add('selected');
      btn.setAttribute('aria-pressed', 'true');
      document.getElementById('emotion').value = emotion;
    } else {
      document.getElementById('emotion').value = '';
    }
  }

  // ── Char Count ──
  function handleExcerptInput() {
    if (excerptCount) excerptCount.textContent = excerptInput.value.length;
  }

  // ── Scroll helper ──
  window.scrollToSection = function (id) {
    var el = document.getElementById(id);
    if (el) {
      var offset = 72;
      var top = el.getBoundingClientRect().top + window.pageYOffset - offset;
      window.scrollTo({ top: top, behavior: 'smooth' });
    }
  };

  // ── Bind Events ──
  function bindEvents() {
    filterTabs.forEach(function (tab) {
      tab.addEventListener('click', handleFilterClick);
    });

    if (searchBtn) searchBtn.addEventListener('click', handleSearch);
    if (searchClearBtn) searchClearBtn.addEventListener('click', handleSearchClear);
    if (searchInput) searchInput.addEventListener('keydown', handleSearchKeydown);

    emotionBtns.forEach(function (btn) {
      btn.addEventListener('click', handleEmotionClick);
    });

    if (excerptInput) excerptInput.addEventListener('input', handleExcerptInput);

    if (precheckBtn) precheckBtn.addEventListener('click', runAIReview);
    if (previewBtn) previewBtn.addEventListener('click', openPreviewModal);
    if (loadMoreBtn) loadMoreBtn.addEventListener('click', handleLoadMore);
    if (publishForm) publishForm.addEventListener('submit', handleFormSubmit);

    if (modalClose) modalClose.addEventListener('click', closeModal);
    if (modalOverlay) {
      modalOverlay.addEventListener('click', function (e) {
        if (e.target === modalOverlay) closeModal();
      });
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && modalOverlay.classList.contains('open')) {
        closeModal();
      }
    });

    // Card keyboard accessibility
    if (giftGrid) {
      giftGrid.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          var card = e.target.closest('.gift-card');
          if (card && !e.target.closest('.card-favorite-btn')) {
            e.preventDefault();
            card.click();
          }
        }
      });
    }

    // Story tip keyboard
    document.querySelectorAll('.story-tip-item').forEach(function (item) {
      item.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          item.click();
        }
      });
    });

    // Phase 2G-2: Show mine tabs in api mode
    var mode = window.__AF_MODE || 'static';
    if (mode === 'api') {
      document.querySelectorAll('.filter-tab-mine').forEach(function (tab) {
        tab.style.display = '';
      });
    }
  }

  // ── Escape HTML ──
  function escHtml(str) {
    if (str === undefined || str === null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

    // ── Phase 2D: Dev Auth Panel ─────────────────────────────────────────────

    function initDevAuthPanel() {
      var mode = window.__AF_MODE || 'static';
      if (mode !== 'api') return;
      var section = document.getElementById('devAuthSection');
      var body = document.getElementById('devAuthBody');
      var actions = document.getElementById('devAuthActions');
      if (!section || !body || !actions) return;
      section.style.display = '';
      var token = (window.AftergiftAPI && window.AftergiftAPI.getStoredToken) ? window.AftergiftAPI.getStoredToken() : null;
      if (token) {
        if (window.AftergiftAPI) {
          window.AftergiftAPI.getCurrentUser(token).then(function(user) {
            showDevAuthIdentity(user.anonymous_nickname, token);
          }).catch(function() {
            if (window.AftergiftAPI && window.AftergiftAPI.clearStoredToken) window.AftergiftAPI.clearStoredToken();
            showDevAuthNoIdentity();
          });
        } else {
          showDevAuthNoIdentity();
        }
      } else {
        showDevAuthNoIdentity();
      }
    }

    function showDevAuthIdentity(nickname) {
      var body = document.getElementById('devAuthBody');
      var actions = document.getElementById('devAuthActions');
      if (!body || !actions) return;
      body.innerHTML = '<div class="dev-auth-identity">' +
        '<svg viewBox="0 0 20 20" fill="none" width="14" height="14" aria-hidden="true"><circle cx="10" cy="8" r="4" stroke="currentColor" stroke-width="1.5"/><path d="M3 18c0-3.3 3.1-6 7-6s7 2.7 7 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>' +
        '<span>当前身份：<strong>' + escHtml(nickname) + '</strong></span>' +
        '</div>';
      actions.style.display = '';
    }

    function showDevAuthNoIdentity() {
      var body = document.getElementById('devAuthBody');
      var actions = document.getElementById('devAuthActions');
      if (!body || !actions) return;
      body.innerHTML = '<div class="dev-auth-no-identity">' +
        '<svg viewBox="0 0 20 20" fill="none" width="14" height="14" aria-hidden="true"><circle cx="10" cy="8" r="4" stroke="currentColor" stroke-width="1.5"/><path d="M3 18c0-3.3 3.1-6 7-6s7 2.7 7 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>' +
        '<span>当前身份：<em>未创建匿名身份</em></span>' +
        '</div>';
      actions.style.display = '';
    }

    function bindDevAuthEvents() {
      var createBtn = document.getElementById('devCreateIdentity');
      var clearBtn = document.getElementById('devClearIdentity');
      if (createBtn) {
        createBtn.addEventListener('click', function() {
          if (!window.AftergiftAPI) { showToast('API 客户端未初始化'); return; }
          createBtn.disabled = true;
          createBtn.textContent = '创建中…';
          window.AftergiftAPI.createAnonymousUser().then(function(result) {
            window.AftergiftAPI.storeToken(result.access_token);
            showDevAuthIdentity(result.anonymous_nickname);
            showToast('匿名身份已创建：' + result.anonymous_nickname);
            updateHeroMySpaceButton();
            createBtn.disabled = false;
            createBtn.innerHTML = '<svg viewBox="0 0 20 20" fill="none" width="14" height="14" aria-hidden="true"><path d="M10 4v12M4 10h12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>创建匿名身份';
          }).catch(function() {
            showToast('创建匿名身份失败，请检查 API 连接');
            createBtn.disabled = false;
            createBtn.innerHTML = '<svg viewBox="0 0 20 20" fill="none" width="14" height="14" aria-hidden="true"><path d="M10 4v12M4 10h12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>创建匿名身份';
          });
        });
      }
      if (clearBtn) {
        clearBtn.addEventListener('click', function() {
          if (window.AftergiftAPI && window.AftergiftAPI.clearStoredToken) window.AftergiftAPI.clearStoredToken();
          showDevAuthNoIdentity();
          showToast('本地身份已清除');
          updateHeroMySpaceButton();
        });
      }
    }

    // ── Phase 2F: Admin Review Panel ──────────────────────────────────────────

    var _adminToken = null;
    var _adminCurrentTab = 'reviews';
    var _adminCurrentPage = 1;
    var _adminTotalPages = 1;

    function initAdminPanel() {
      if (!window.__AF_ADMIN) return;
      var section = document.getElementById('adminReviewSection');
      if (!section) return;
      section.style.display = '';

      var loadBtn = document.getElementById('adminLoadQueue');
      if (loadBtn) loadBtn.addEventListener('click', loadAdminQueue);

      // Tab switching
      document.querySelectorAll('.admin-tab').forEach(function(tab) {
        tab.addEventListener('click', function() {
          document.querySelectorAll('.admin-tab').forEach(function(t) {
            t.classList.remove('active');
            t.setAttribute('aria-selected', 'false');
          });
          tab.classList.add('active');
          tab.setAttribute('aria-selected', 'true');
          _adminCurrentTab = tab.getAttribute('data-tab');
          _adminCurrentPage = 1;
          loadAdminTab();
        });
      });

      // Filter apply
      var filterBtn = document.getElementById('adminApplyFilter');
      if (filterBtn) filterBtn.addEventListener('click', function() {
        _adminCurrentPage = 1;
        loadAdminTab();
      });

      // Pagination
      var prevBtn = document.getElementById('adminPagePrev');
      var nextBtn = document.getElementById('adminPageNext');
      if (prevBtn) prevBtn.addEventListener('click', function() {
        if (_adminCurrentPage > 1) { _adminCurrentPage--; loadAdminTab(); }
      });
      if (nextBtn) nextBtn.addEventListener('click', function() {
        if (_adminCurrentPage < _adminTotalPages) { _adminCurrentPage++; loadAdminTab(); }
      });

      // Auto-load if token stored
      try {
        var stored = sessionStorage.getItem('aftergift_admin_token');
        if (stored) {
          var input = document.getElementById('adminTokenInput');
          if (input) input.value = stored;
          _adminToken = stored;
          loadAdminQueue();
        }
      } catch (e) {}
    }

    function loadAdminQueue() {
      var tokenInput = document.getElementById('adminTokenInput');
      var token = (tokenInput && tokenInput.value) ? tokenInput.value.trim() : '';
      if (!token) { showToast('请输入 Admin Token'); return; }
      _adminToken = token;
      try { sessionStorage.setItem('aftergift_admin_token', token); } catch (e) {}

      var area = document.getElementById('adminTokenArea');
      var tabs = document.getElementById('adminTabs');
      var filterBar = document.getElementById('adminFilterBar');
      var pagination = document.getElementById('adminPagination');

      if (area) area.style.display = 'none';
      if (tabs) tabs.style.display = '';
      if (filterBar) filterBar.style.display = '';
      if (pagination) pagination.style.display = '';

      _adminCurrentPage = 1;
      loadAdminTab();
    }

    function getAdminFilterParams() {
      var status = document.getElementById('adminFilterStatus');
      var risk = document.getElementById('adminFilterRisk');
      var provider = document.getElementById('adminFilterProvider');
      var sort = document.getElementById('adminFilterSort');
      var order = document.getElementById('adminFilterOrder');
      return {
        status: status && status.value ? status.value : undefined,
        risk_level: risk && risk.value ? risk.value : undefined,
        provider: provider && provider.value ? provider.value : undefined,
        sort: sort && sort.value ? sort.value : 'created_at',
        order: order && order.value ? order.value : 'desc',
        page: _adminCurrentPage,
        limit: 10
      };
    }

    function loadAdminTab() {
      var queue = document.getElementById('adminQueue');
      if (queue) { queue.innerHTML = '<div class="admin-queue-loading">加载中…</div>'; queue.style.display = ''; }
      document.getElementById('adminQueueEmpty').style.display = 'none';

      if (_adminCurrentTab === 'reviews') {
        loadAdminReviews();
      } else if (_adminCurrentTab === 'reports') {
        loadAdminReports();
      } else if (_adminCurrentTab === 'actions') {
        loadAdminActions();
      }
    }

    function loadAdminReviews() {
      var params = getAdminFilterParams();
      if (window.AftergiftAPI && window.AftergiftAPI.getAdminReviews) {
        window.AftergiftAPI.getAdminReviews(params, _adminToken).then(function(data) {
          renderAdminReviews(data);
        }).catch(function(err) {
          showAdminError(err);
        });
      } else {
        // Fallback to direct fetch
        var qs = new URLSearchParams();
        Object.keys(params).forEach(function(k) { if (params[k] !== undefined) qs.set(k, String(params[k])); });
        adminFetchGet('/api/admin/reviews?' + qs.toString(), _adminToken).then(renderAdminReviews).catch(showAdminError);
      }
    }

    function loadAdminReports() {
      var params = { page: _adminCurrentPage, limit: 10, sort: 'created_at', order: 'desc' };
      if (window.AftergiftAPI && window.AftergiftAPI.getAdminReports) {
        window.AftergiftAPI.getAdminReports(params, _adminToken).then(function(data) {
          renderAdminReports(data);
        }).catch(showAdminError);
      } else {
        var qs = new URLSearchParams();
        Object.keys(params).forEach(function(k) { qs.set(k, String(params[k])); });
        adminFetchGet('/api/admin/reports?' + qs.toString(), _adminToken).then(renderAdminReports).catch(showAdminError);
      }
    }

    function loadAdminActions() {
      var params = { page: _adminCurrentPage, limit: 10 };
      if (window.AftergiftAPI && window.AftergiftAPI.getAdminActions) {
        window.AftergiftAPI.getAdminActions(params, _adminToken).then(function(data) {
          renderAdminActions(data);
        }).catch(showAdminError);
      } else {
        var qs = new URLSearchParams();
        Object.keys(params).forEach(function(k) { qs.set(k, String(params[k])); });
        adminFetchGet('/api/admin/actions?' + qs.toString(), _adminToken).then(renderAdminActions).catch(showAdminError);
      }
    }

    function showAdminError(err) {
      var queue = document.getElementById('adminQueue');
      if (queue) queue.innerHTML = '<div class="admin-queue-loading">加载失败：' + escHtml(err.message || '未知错误') + '</div>';
    }

    function updatePagination(data) {
      _adminTotalPages = data.total_pages || 1;
      var info = document.getElementById('adminPageInfo');
      var prev = document.getElementById('adminPagePrev');
      var next = document.getElementById('adminPageNext');
      if (info) info.textContent = '第 ' + data.page + ' 页 / 共 ' + data.total_pages + ' 页';
      if (prev) prev.disabled = data.page <= 1;
      if (next) next.disabled = data.page >= data.total_pages;
    }

    function adminFetchGet(path, token) {
      return fetch('http://127.0.0.1:8091' + path, {
        headers: { 'X-Admin-Token': token }
      }).then(function(r) {
        return r.json().then(function(json) {
          if (!r.ok) throw new Error((json && json.detail) || 'Request failed (' + r.status + ')');
          return json.data || json;
        });
      });
    }

    function adminFetchPost(path, token, payload) {
      return fetch('http://127.0.0.1:8091' + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Admin-Token': token },
        body: JSON.stringify(payload)
      }).then(function(r) {
        return r.json().then(function(json) {
          if (!r.ok) throw new Error((json && json.detail) || 'Request failed (' + r.status + ')');
          return json.data || json;
        });
      });
    }

    // ── Render Reviews ──
    function renderAdminReviews(data) {
      var queue = document.getElementById('adminQueue');
      var empty = document.getElementById('adminQueueEmpty');
      if (!queue) return;
      var items = (data && data.items) ? data.items : [];
      var total = (data && data.total) ? data.total : 0;
      if (items.length === 0) {
        queue.style.display = 'none';
        if (empty) { empty.style.display = ''; empty.querySelector('p').textContent = '当前没有符合条件的审核记录。'; }
        updatePagination({ page: _adminCurrentPage, total_pages: 1 });
        return;
      }
      if (empty) empty.style.display = 'none';
      queue.style.display = '';
      queue.innerHTML = '<div class="admin-queue-count">共 ' + total + ' 条</div>';
      items.forEach(function(item) {
        var riskLabel = { safe: '安全', caution: '注意', high_risk: '高风险' };
        var riskClass = { safe: 'risk-safe', caution: 'risk-caution', high_risk: 'risk-high' };
        var risk = item.risk_level || 'safe';
        var statusLabel = { pending_review: '待审', needs_edit: '需修改', published: '已发布', rejected: '已拒绝', archived: '已归档' };
        var st = item.status || 'pending_review';
        var suggestions = (item.review_suggestions || []).map(function(s) {
          var txt = typeof s === 'string' ? s : (s.suggestion || JSON.stringify(s));
          return '<li>' + escHtml(txt) + '</li>';
        }).join('');
        var card = document.createElement('div');
        card.className = 'admin-review-item';
        card.setAttribute('data-gift-id', item.gift_id || '');
        var providerBadge = item.provider ? '<span class="admin-provider-badge">' + escHtml(item.provider) + '</span>' : '';
        var redactionBadge = item.redaction_summary ? '<span class="admin-redaction-badge" title="' + escHtml(JSON.stringify(item.redaction_summary)) + '">已脱敏</span>' : '';
        var badges = '<span class="admin-risk-badge ' + escHtml(riskClass[risk] || 'risk-safe') + '">' + escHtml(riskLabel[risk] || risk) + '</span>' +
          '<span class="admin-status-badge">' + escHtml(statusLabel[st] || st) + '</span>' +
          '<span class="admin-emotion-badge">' + escHtml(item.emotion || '') + '</span>' +
          providerBadge + redactionBadge;
        var meta = '<div class="admin-review-meta"><span>' + escHtml(item.category || '') + '</span><span>' + escHtml(item.relation_label || item.relation_type || '') + '</span><span>' + escHtml(item.action_type || '') + '</span></div>';
        var sugBlock = suggestions ? '<div class="admin-review-suggestions"><div class="admin-review-story-label">审核建议</div><ul>' + suggestions + '</ul></div>' : '';
        var aiNotes = item.ai_review_notes ? '<div class="admin-review-ai-notes">' + escHtml(item.ai_review_notes) + '</div>' : '';
        var noteId = 'note-' + (item.gift_id || Math.random());
        card.innerHTML =
          '<div class="admin-review-header">' +
            '<div class="admin-review-title">' + escHtml(item.title || '') + '</div>' +
            '<div class="admin-review-badges">' + badges + '</div>' +
          '</div>' +
          meta +
          '<div class="admin-review-story-label">一句话故事</div>' +
          '<div class="admin-review-story-excerpt">' + escHtml(item.short_story || '') + '</div>' +
          '<div class="admin-review-story-label">完整故事</div>' +
          '<div class="admin-review-story-full">' + escHtml(item.full_story || '') + '</div>' +
          sugBlock + aiNotes +
          '<div class="admin-review-note-row">' +
            '<label for="' + noteId + '" class="admin-note-label">审核备注</label>' +
            '<textarea id="' + noteId + '" class="admin-note-input" rows="2" placeholder="可选：给发布者的说明或内部备注"></textarea>' +
          '</div>' +
          '<div class="admin-review-actions">' +
            '<button class="btn btn-primary btn-sm admin-decision-btn" data-action="approve" data-gift-id="' + escHtml(item.gift_id || '') + '" data-note-id="' + noteId + '">批准公开</button>' +
            '<button class="btn btn-secondary btn-sm admin-decision-btn" data-action="needs_edit" data-gift-id="' + escHtml(item.gift_id || '') + '" data-note-id="' + noteId + '">退回修改</button>' +
            '<button class="btn btn-ghost btn-sm admin-decision-btn admin-reject-btn" data-action="reject" data-gift-id="' + escHtml(item.gift_id || '') + '" data-note-id="' + noteId + '">拒绝发布</button>' +
            '<button class="btn btn-ghost btn-sm admin-logs-btn" data-gift-id="' + escHtml(item.gift_id || '') + '">查看日志</button>' +
          '</div>' +
          '<div class="admin-decision-feedback"></div>';
        queue.appendChild(card);
      });
      queue.querySelectorAll('.admin-decision-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
          var action = btn.getAttribute('data-action');
          var giftId = btn.getAttribute('data-gift-id');
          var noteId = btn.getAttribute('data-note-id');
          var note = noteId ? (document.getElementById(noteId) || {}).value || '' : '';
          submitAdminDecision(giftId, action, note, btn);
        });
      });
      queue.querySelectorAll('.admin-logs-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
          var giftId = btn.getAttribute('data-gift-id');
          loadAdminReviewLogs(giftId);
        });
      });
      updatePagination(data);
    }

    function submitAdminDecision(giftId, decision, note, btnEl) {
      var label = { approve: '批准', needs_edit: '退回修改', reject: '拒绝' };
      if (!confirm('确认要' + (label[decision] || decision) + '这个故事吗？')) return;
      btnEl.disabled = true;
      btnEl.textContent = '处理中…';
      var payload = { decision: decision, note: note };
      adminFetchPost('/api/admin/reviews/' + encodeURIComponent(giftId) + '/decision', _adminToken, payload).then(function(data) {
        var feedback = btnEl.parentNode.nextElementSibling;
        if (feedback && feedback.className === 'admin-decision-feedback') {
          feedback.innerHTML = '<span class="admin-decision-ok">&#10003; ' + escHtml(label[decision]) + '成功（' + escHtml(data.new_status || '') + '）</span>';
        }
        btnEl.textContent = '已处理';
        btnEl.disabled = true;
        setTimeout(loadAdminTab, 1500);
      }).catch(function(err) {
        var feedback = btnEl.parentNode.nextElementSibling;
        if (feedback && feedback.className === 'admin-decision-feedback') {
          feedback.innerHTML = '<span class="admin-decision-err">&#10007; 失败：' + escHtml(err.message || '未知错误') + '</span>';
        }
        btnEl.disabled = false;
        btnEl.textContent = label[decision] || decision;
      });
    }

    function loadAdminReviewLogs(giftId) {
      if (window.AftergiftAPI && window.AftergiftAPI.getAdminReviewLogs) {
        window.AftergiftAPI.getAdminReviewLogs(giftId, _adminToken).then(function(data) {
          showAdminLogsModal(giftId, data.items || []);
        }).catch(function(err) { showToast('加载日志失败：' + (err.message || '')); });
      } else {
        adminFetchGet('/api/admin/reviews/' + encodeURIComponent(giftId) + '/logs', _adminToken).then(function(data) {
          showAdminLogsModal(giftId, data.items || []);
        }).catch(function(err) { showToast('加载日志失败：' + (err.message || '')); });
      }
    }

    function showAdminLogsModal(giftId, items) {
      var body = '';
      if (items.length === 0) {
        body = '<p>暂无审核日志。</p>';
      } else {
        body = '<div class="admin-logs-list">';
        items.forEach(function(log) {
          body += '<div class="admin-log-item">' +
            '<div class="admin-log-header"><span class="admin-log-risk">' + escHtml(log.risk_level) + '</span><span class="admin-log-provider">' + escHtml(log.reviewer_type) + '</span><span class="admin-log-time">' + escHtml(log.created_at) + '</span></div>' +
            '<div class="admin-log-details">身份风险:' + (log.identity_risk || 0) + ' | 攻击风险:' + (log.attack_risk || 0) + ' | 可识别风险:' + (log.identifiable_person_risk || 0) + '</div>' +
            (log.redaction_summary ? '<div class="admin-log-redaction">脱敏: ' + escHtml(JSON.stringify(log.redaction_summary)) + '</div>' : '') +
            '</div>';
        });
        body += '</div>';
      }
      modalBody.innerHTML = '<div class="modal-gift-header"><h2 class="modal-gift-title">审核日志 #' + escHtml(giftId.slice(0, 8)) + '</h2></div><div class="modal-divider"></div>' + body;
      modalOverlay.classList.add('open');
      modalOverlay.setAttribute('aria-hidden', 'false');
      document.body.style.overflow = 'hidden';
    }

    // ── Render Reports ──
    function renderAdminReports(data) {
      var queue = document.getElementById('adminQueue');
      var empty = document.getElementById('adminQueueEmpty');
      if (!queue) return;
      var items = (data && data.items) ? data.items : [];
      var total = (data && data.total) ? data.total : 0;
      if (items.length === 0) {
        queue.style.display = 'none';
        if (empty) { empty.style.display = ''; empty.querySelector('p').textContent = '当前没有举报记录。'; }
        updatePagination({ page: _adminCurrentPage, total_pages: 1 });
        return;
      }
      if (empty) empty.style.display = 'none';
      queue.style.display = '';
      queue.innerHTML = '<div class="admin-queue-count">共 ' + total + ' 条举报</div>';
      items.forEach(function(item) {
        var statusLabel = { pending: '待处理', reviewing: '审核中', resolved_dismissed: '已驳回', resolved_action_taken: '已处理' };
        var st = item.status || 'pending';
        var card = document.createElement('div');
        card.className = 'admin-review-item';
        var noteId = 'rnote-' + (item.report_id || Math.random());
        card.innerHTML =
          '<div class="admin-review-header">' +
            '<div class="admin-review-title">' + escHtml(item.gift_title || '礼物') + '</div>' +
            '<div class="admin-review-badges"><span class="admin-status-badge">' + escHtml(statusLabel[st] || st) + '</span><span class="admin-emotion-badge">' + escHtml(item.reason || '') + '</span></div>' +
          '</div>' +
          '<div class="admin-review-meta"><span>举报者: ' + escHtml(item.reporter_user_id || '匿名') + '</span><span>礼物状态: ' + escHtml(item.current_gift_status || '') + '</span></div>' +
          '<div class="admin-review-story-label">举报详情</div>' +
          '<div class="admin-review-story-excerpt">' + escHtml(item.detail || '无详情') + '</div>' +
          '<div class="admin-review-note-row">' +
            '<label for="' + noteId + '" class="admin-note-label">处理备注</label>' +
            '<textarea id="' + noteId + '" class="admin-note-input" rows="2" placeholder="可选：处理说明"></textarea>' +
          '</div>' +
          '<div class="admin-review-actions">' +
            '<button class="btn btn-primary btn-sm admin-report-btn" data-action="dismiss" data-report-id="' + escHtml(item.report_id || '') + '" data-note-id="' + noteId + '">驳回</button>' +
            '<button class="btn btn-secondary btn-sm admin-report-btn" data-action="needs_review" data-report-id="' + escHtml(item.report_id || '') + '" data-note-id="' + noteId + '">需审核</button>' +
            '<button class="btn btn-ghost btn-sm admin-report-btn admin-reject-btn" data-action="take_action" data-report-id="' + escHtml(item.report_id || '') + '" data-note-id="' + noteId + '">采取行动</button>' +
          '</div>' +
          '<div class="admin-decision-feedback"></div>';
        queue.appendChild(card);
      });
      queue.querySelectorAll('.admin-report-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
          var action = btn.getAttribute('data-action');
          var reportId = btn.getAttribute('data-report-id');
          var noteId = btn.getAttribute('data-note-id');
          var note = noteId ? (document.getElementById(noteId) || {}).value || '' : '';
          submitReportDecision(reportId, action, note, btn);
        });
      });
      updatePagination(data);
    }

    function submitReportDecision(reportId, decision, note, btnEl) {
      var label = { dismiss: '驳回', needs_review: '需审核', take_action: '采取行动' };
      if (!confirm('确认要' + (label[decision] || decision) + '这条举报吗？')) return;
      btnEl.disabled = true;
      btnEl.textContent = '处理中…';
      var payload = { decision: decision, note: note };
      adminFetchPost('/api/admin/reports/' + encodeURIComponent(reportId) + '/decision', _adminToken, payload).then(function(data) {
        var feedback = btnEl.parentNode.nextElementSibling;
        if (feedback && feedback.className === 'admin-decision-feedback') {
          feedback.innerHTML = '<span class="admin-decision-ok">&#10003; ' + escHtml(label[decision]) + '成功</span>';
        }
        btnEl.textContent = '已处理';
        btnEl.disabled = true;
        setTimeout(loadAdminTab, 1500);
      }).catch(function(err) {
        var feedback = btnEl.parentNode.nextElementSibling;
        if (feedback && feedback.className === 'admin-decision-feedback') {
          feedback.innerHTML = '<span class="admin-decision-err">&#10007; 失败：' + escHtml(err.message || '未知错误') + '</span>';
        }
        btnEl.disabled = false;
        btnEl.textContent = label[decision] || decision;
      });
    }

    // ── Phase 2H-2: Load My Actions ───────────────────────────────────────────
    function loadMyActions() {
      var mode = window.__AF_MODE || 'static';
      if (mode !== 'api' || !window.AftergiftAPI) {
        gifts = [];
        renderGifts();
        return;
      }
      var token = window.AftergiftAPI.getStoredToken ? window.AftergiftAPI.getStoredToken() : null;
      if (!token) {
        showToast('请先创建匿名身份，再查看操作历史。');
        gifts = [];
        renderGifts();
        return;
      }
      window.AftergiftAPI.getMyActions({ page: 1, limit: 50 }).then(function (result) {
        var items = (result && result.items) ? result.items : [];
        // Transform user actions into gift-like cards for renderGifts reuse
        gifts = items.map(function (a) {
          var actionLabelMap = {
            edit: '编辑故事',
            resubmit: '重新提交',
            archive: '暂时收起',
            restore: '恢复审核'
          };
          return {
            id: a.id,
            title: a.gift_title || '未命名礼物',
            category: '操作记录',
            relation_type: 'my_action',
            action_type: a.action,
            action_label: actionLabelMap[a.action] || a.action,
            emotion: '',
            price_or_exchange: '',
            short_story: a.note || '',
            full_story: a.note || '',
            status: 'my_action',
            created_at: a.created_at,
            updated_at: a.created_at,
            is_anonymous: true,
            anonymous_nickname: '我',
            condition_note: '',
            city_blur: '',
            _is_action_record: true,
            _action_meta: a
          };
        });
        searchMeta = { total: gifts.length, page: 1, limit: 50, total_pages: 1, has_more: false };
        showModeIndicator('api', gifts.length);
        renderGifts();
      }).catch(function () {
        showToast('操作历史暂时加载失败，请稍后再试。');
        gifts = [];
        renderGifts();
      });
    }

    // ── Render Actions ──
    function renderAdminActions(data) {
      var queue = document.getElementById('adminQueue');
      var empty = document.getElementById('adminQueueEmpty');
      if (!queue) return;
      var items = (data && data.items) ? data.items : [];
      var total = (data && data.total) ? data.total : 0;
      if (items.length === 0) {
        queue.style.display = 'none';
        if (empty) { empty.style.display = ''; empty.querySelector('p').textContent = '当前没有操作记录。'; }
        updatePagination({ page: _adminCurrentPage, total_pages: 1 });
        return;
      }
      if (empty) empty.style.display = 'none';
      queue.style.display = '';
      queue.innerHTML = '<div class="admin-queue-count">共 ' + total + ' 条操作记录</div>';
      items.forEach(function(item) {
        var actionLabel = { approve: '批准', reject: '拒绝', needs_edit: '退回修改', suspend_user: '封禁用户', dismiss_report: '驳回举报', take_action: '采取行动' };
        var card = document.createElement('div');
        card.className = 'admin-review-item';
        card.innerHTML =
          '<div class="admin-review-header">' +
            '<div class="admin-review-title">' + escHtml(actionLabel[item.action] || item.action) + ' — ' + escHtml(item.target_type) + '</div>' +
            '<div class="admin-review-badges"><span class="admin-status-badge">' + escHtml(item.target_id ? item.target_id.slice(0, 8) : '') + '</span></div>' +
          '</div>' +
          '<div class="admin-review-meta"><span>管理员: ' + escHtml(item.admin_id || '') + '</span><span>' + escHtml(item.created_at || '') + '</span></div>' +
          (item.note ? '<div class="admin-review-story-excerpt">' + escHtml(item.note) + '</div>' : '');
        queue.appendChild(card);
      });
      updatePagination(data);
    }

    // ── Phase 2D: Auth Gates ─────────────────────────────────────────────────

    function _checkAuth() {
      var mode = window.__AF_MODE || 'static';
      if (mode !== 'api') return true;
      if (!window.AftergiftAPI) return true;
      var token = window.AftergiftAPI.getStoredToken();
      return !!token;
    }

    function _getAuthToken() {
      if (!window.AftergiftAPI) return null;
      return window.AftergiftAPI.getStoredToken();
    }

    // ── Phase 2K-1: Favorites View ────────────────────────────────────────────

    function checkUrlView() {
      var params = new URLSearchParams(window.location.search);
      if (params.get('view') === 'favorites') {
        enterFavoritesView();
      }
      // Phase 2L-2: handle ?view=me
      if (params.get('view') === 'me') {
        enterMySpaceView();
      }
    }

    window.enterFavoritesView = function () {
      var mode = window.__AF_MODE || 'static';
      if (mode === 'api') {
        var token = (window.AftergiftAPI && window.AftergiftAPI.getStoredToken)
          ? window.AftergiftAPI.getStoredToken() : null;
        if (!token) {
          showToast('请先创建匿名身份，再查看你的收藏。');
          return;
        }
      }
      currentView = 'favorites';
      document.body.classList.add('favorites-view');
      window.scrollTo({ top: 0, behavior: 'smooth' });
      currentFilter = 'my_favorites';
      displayedCount = INITIAL_DISPLAY;
      var params = buildListParams();
      if (mode === 'api' && window.AftergiftAPI) {
        window.AftergiftAPI.listGifts(params, []).then(function (result) {
          gifts = result.items;
          searchMeta = {
            total: result.total || 0,
            page: result.page || 1,
            limit: result.limit || 12,
            total_pages: result.total_pages || 0,
            has_more: result.has_more || false
          };
          favoritesCount = result.total || 0;
          updateFavoritesViewHeader();
          showModeIndicator('api', result.total || 0);
          renderGifts();
        }).catch(function (err) {
          // Phase 2K-2: differentiate auth failure from network failure
          var isAuthError = (err && (err.status === 401 || err.status === 403));
          showToast(isAuthError
            ? '身份已失效，请重新创建匿名身份。'
            : '无法加载收藏列表，请检查 API 连接');
          // Show gentle empty state for auth failure
          updateFavoritesViewHeader();
          renderGifts();
        });
      } else {
        if (window.__AF_STATIC_DATA) {
          window.AftergiftAPI.listGifts(params, window.__AF_STATIC_DATA).then(function (result) {
            gifts = result.items;
            searchMeta = {
              total: result.total || 0,
              page: result.page || 1,
              limit: result.limit || 12,
              total_pages: result.total_pages || 0,
              has_more: result.has_more || false
            };
            updateFavoritesViewHeader();
            renderGifts();
          });
        } else {
          updateFavoritesViewHeader();
          renderGifts();
        }
      }
    };

    window.exitFavoritesView = function () {
      currentView = 'home';
      document.body.classList.remove('favorites-view');
      currentFilter = 'all';
      displayedCount = INITIAL_DISPLAY;
      var params = new URLSearchParams(window.location.search);
      params.delete('view');
      var newUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
      window.history.replaceState({}, '', newUrl);
      loadGifts();
      document.querySelectorAll('.filter-tab').forEach(function (t) {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });
      var allTab = document.querySelector('.filter-tab[data-filter="all"]');
      if (allTab) {
        allTab.classList.add('active');
        allTab.setAttribute('aria-selected', 'true');
      }
    };

    function updateFavoritesViewHeader() {
      var subtitle = document.getElementById('favoritesViewSubtitle');
      if (!subtitle) return;
      var total = searchMeta.total || 0;
      if (total === 0) {
        subtitle.textContent = '你还没有收藏任何故事。也许下一件打动你的旧物，就在下面的故事里。';
      } else {
        subtitle.textContent = '已收藏 ' + total + ' 个故事';
      }
    }

    window.updateHeroFavoritesButton = function () {
      var btn = document.getElementById('heroFavoritesBtn');
      if (!btn) return;
      var mode = window.__AF_MODE || 'static';
      if (mode === 'api') {
        var token = (window.AftergiftAPI && window.AftergiftAPI.getStoredToken)
          ? window.AftergiftAPI.getStoredToken() : null;
        btn.style.display = token ? '' : 'none';
      } else {
        btn.style.display = '';
      }
    };

    // Phase 2L-2: Show my-space button only when logged in (API mode)
    window.updateHeroMySpaceButton = function () {
      var btn = document.getElementById('heroMySpaceBtn');
      if (!btn) return;
      var mode = window.__AF_MODE || 'static';
      if (mode === 'api') {
        var token = (window.AftergiftAPI && window.AftergiftAPI.getStoredToken)
          ? window.AftergiftAPI.getStoredToken() : null;
        btn.style.display = token ? '' : 'none';
      } else {
        btn.style.display = 'none'; // hidden in static mode
      }
    };

    // ── Phase 2K-2: Update Hero Favorites Badge ─────────────────────────────
    // Shows badge count on hero favorites button.
    // API mode: calls GET /api/gifts?favorites_of=me&limit=1 to get total count.
    // Static mode: counts from localStorage favorites.
    // Call after any favorite/unfavorite action or init.
    window.updateHeroFavoritesBadge = function () {
      var badge = document.getElementById('heroFavoritesBadge');
      if (!badge) return;
      var mode = window.__AF_MODE || 'static';

      if (mode === 'api') {
        var token = (window.AftergiftAPI && window.AftergiftAPI.getStoredToken)
          ? window.AftergiftAPI.getStoredToken() : null;
        if (!token) {
          badge.style.display = 'none';
          return;
        }
        // Fetch total count (limit=1, no items needed)
        var params = { favorites_of: 'me', limit: 1, page: 1 };
        window.AftergiftAPI.listGifts(params, []).then(function (res) {
          var total = res && (res.total || res.items ? res.items.length : 0);
          favoritesCount = total;
          if (total > 0) {
            badge.textContent = total > 99 ? '99+' : String(total);
            badge.style.display = '';
          } else {
            badge.style.display = 'none';
          }
        }).catch(function () {
          badge.style.display = 'none';
        });
      } else {
        // Static mode: count from localStorage
        var stored = null;
        try { stored = localStorage.getItem('aftergift_favorites'); } catch (e) {}
        var favs = stored ? JSON.parse(stored) : {};
        var count = Object.keys(favs).filter(function (id) { return !!favs[id]; }).length;
        favoritesCount = count;
        if (count > 0) {
          badge.textContent = count > 99 ? '99+' : String(count);
          badge.style.display = '';
        } else {
          badge.style.display = 'none';
        }
      }
    };

    // Update badge after every toggleFavorite
    // Patch toggleFavorite to call updateHeroFavoritesBadge at the end
    var _origToggleFavorite = window.toggleFavorite;
    // (We will insert the badge update at the end of toggleFavorite — see there)

    window.updateHeroFavoritesBadge(); // initial call during init

    // ── Phase 2L-2: My Space ────────────────────────────────────────────────

    window.enterMySpaceView = function () {
      var mode = window.__AF_MODE || 'static';
      if (mode === 'api') {
        var token = (window.AftergiftAPI && window.AftergiftAPI.getStoredToken)
          ? window.AftergiftAPI.getStoredToken() : null;
        if (!token) {
          showToast('请先创建匿名身份，再进入我的空间。');
          return;
        }
      }
      currentView = 'my_space';
      document.body.classList.add('my-space-active');
      window.scrollTo({ top: 0, behavior: 'smooth' });
      loadMySpace();
    };

    window.exitMySpaceView = function () {
      currentView = 'home';
      document.body.classList.remove('my-space-active');
      var params = new URLSearchParams(window.location.search);
      params.delete('view');
      var newUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
      window.history.replaceState({}, '', newUrl);
      loadGifts();
    };

    function loadMySpace() {
      var mode = window.__AF_MODE || 'static';
      var mySpaceViewEl = document.getElementById('mySpaceView');
      if (!mySpaceViewEl) return;
      mySpaceViewEl.style.display = 'block';

      if (mode !== 'api') {
        renderMySpaceStatic();
        return;
      }

      renderMySpaceIdentity();
      renderMySpaceStats({ published: '–', pending: '–', favorites: '–', drafts: '–' });
      loadMySpaceData();
    }

    function renderMySpaceIdentity() {
      var body = document.getElementById('mySpaceIdentityBody');
      if (!body) return;
      body.innerHTML = '<div class="msic-loading">正在读取身份信息...</div>';

      var token = (window.AftergiftAPI && window.AftergiftAPI.getStoredToken)
        ? window.AftergiftAPI.getStoredToken() : null;

      if (!token) {
        body.innerHTML = '<div class="msic-nickname">未登录</div><div class="msic-token-status"><span class="msic-token-dot invalid"></span> 无效</div>';
        return;
      }

      window.AftergiftAPI.getCurrentUser(token).then(function (user) {
        body.innerHTML =
          '<div class="msic-nickname">' + escHtml(user.anonymous_nickname || user.nickname || '匿名用户') + '</div>' +
          '<div class="msic-token-status"><span class="msic-token-dot valid"></span> 身份有效 · ' + escHtml(user.user_id || '') + '</div>';
      }).catch(function () {
        body.innerHTML = '<div class="msic-nickname">已登录</div><div class="msic-token-status"><span class="msic-token-dot valid"></span> 身份有效</div>';
      });
    }

    function renderMySpaceStats(stats) {
      var el;
      el = document.getElementById('mySpacePublishedCount');
      if (el) el.textContent = stats.published;
      el = document.getElementById('mySpacePendingCount');
      if (el) el.textContent = stats.pending;
      el = document.getElementById('mySpaceFavoritesCount');
      if (el) el.textContent = stats.favorites;
      el = document.getElementById('mySpaceDraftsCount');
      if (el) el.textContent = stats.drafts;
    }

    function loadMySpaceData() {
      var token = (window.AftergiftAPI && window.AftergiftAPI.getStoredToken)
        ? window.AftergiftAPI.getStoredToken() : null;
      if (!token) return;

      var draftsCount = 0;
      try {
        var keys = Object.keys(localStorage);
        draftsCount = keys.filter(function (k) { return k.indexOf('aftergift_edit_draft_') === 0; }).length;
      } catch (e) {}

      window.AftergiftAPI.listGifts({ mine: true, limit: 1 }, []).then(function (result) {
        var publishedCount = result.total || 0;
        return window.AftergiftAPI.listGifts({ mine: true, action_type: 'pending', limit: 1 }, []);
      }).then(function (result) {
        var pendingCount = result.total || 0;
        return window.AftergiftAPI.listGifts({ favorites_of: 'me', limit: 1 }, []);
      }).then(function (result) {
        var favoritesCount = result.total || 0;
        renderMySpaceStats({
          published: window._ms_publishedCount || '–',
          pending: window._ms_pendingCount || '–',
          favorites: favoritesCount,
          drafts: draftsCount
        });
        return window.AftergiftAPI.listGifts({ mine: true, limit: 3 }, []);
      }).then(function (result) {
        renderMySpaceGiftList(result.items || []);
        return window.AftergiftAPI.getMyActions({ limit: 5 });
      }).then(function (actions) {
        renderMySpaceActionList(actions || []);
      }).catch(function (err) {
        renderMySpaceStats({ published: '–', pending: '–', favorites: '–', drafts: draftsCount });
        var gl = document.getElementById('mySpaceGiftList');
        if (gl) gl.innerHTML = '<div class="my-space-loading">无法加载数据，请检查 API 连接。</div>';
        var al = document.getElementById('mySpaceActionList');
        if (al) al.innerHTML = '<div class="my-space-loading">无法加载操作历史。</div>';
      });
    }

    // Pre-load counts for stats display
    (function () {
      var token = (window.AftergiftAPI && window.AftergiftAPI.getStoredToken)
        ? window.AftergiftAPI.getStoredToken() : null;
      if (!token) return;
      window.AftergiftAPI.listGifts({ mine: true, limit: 1 }, []).then(function (r) {
        window._ms_publishedCount = r.total || 0;
        return window.AftergiftAPI.listGifts({ mine: true, action_type: 'pending', limit: 1 }, []);
      }).then(function (r) {
        window._ms_pendingCount = r.total || 0;
      }).catch(function () {});
    })();

    function renderMySpaceStatic() {
      renderMySpaceIdentity();
      var draftsCount = 0;
      try {
        var keys = Object.keys(localStorage);
        draftsCount = keys.filter(function (k) { return k.indexOf('aftergift_edit_draft_') === 0; }).length;
      } catch (e) {}
      var favCount = 0;
      try {
        var stored = localStorage.getItem('aftergift_favorites');
        var favs = stored ? JSON.parse(stored) : {};
        favCount = Object.keys(favs).filter(function (id) { return !!favs[id]; }).length;
      } catch (e) {}
      renderMySpaceStats({ published: '–', pending: '–', favorites: String(favCount), drafts: String(draftsCount) });
      var gl = document.getElementById('mySpaceGiftList');
      if (gl) gl.innerHTML = '<div class="my-space-loading">本地模式暂不支持查看我的发布，请切换到 API 模式。</div>';
      var al = document.getElementById('mySpaceActionList');
      if (al) al.innerHTML = '<div class="my-space-loading">本地模式暂不支持查看操作历史。</div>';
    }

    function renderMySpaceGiftList(gifts) {
      var container = document.getElementById('mySpaceGiftList');
      if (!container) return;
      if (!gifts || gifts.length === 0) {
        container.innerHTML = '<div class="my-space-loading">你还没有发布任何礼物故事。</div>';
        return;
      }
      var html = '';
      var statusLabel = { published: '已发布', pending_review: '待审核', needs_revision: '需修改', archived: '已归档' };
      var statusColor = { published: '#22c55e', pending_review: '#f59e0b', needs_revision: '#ef4444', archived: '#9ca3af' };
      gifts.slice(0, 3).forEach(function (g) {
        var status = g.status || 'published';
        var sText = statusLabel[status] || status;
        var sColor = statusColor[status] || '#9ca3af';
        html +=
          '<div class="msa-item" style="cursor:pointer" onclick="openDetail(\'' + g.id + '\')">' +
          '<div class="msa-icon publish">' +
          '<svg viewBox="0 0 16 16" fill="none" width="14" height="14"><path d="M8 2v8M4 6l4 4 4-4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
          '</div>' +
          '<div class="msa-text"><div class="msa-title">' + escHtml(g.name || g.title || '') + '</div>' +
          '<div class="msa-meta"><span style="color:' + sColor + '">● ' + sText + '</span> · ' + escHtml(g.actionLabel || g.action || '') + '</div></div>' +
          '<div class="msa-time">' + escHtml(g.created_at ? g.created_at.slice(0, 10) : '') + '</div>' +
          '</div>';
      });
      container.innerHTML = html;
    }

    function renderMySpaceActionList(actions) {
      var container = document.getElementById('mySpaceActionList');
      if (!container) return;
      if (!actions || actions.length === 0) {
        container.innerHTML = '<div class="my-space-loading">还没有任何操作记录。</div>';
        return;
      }
      var iconMap = { edit: 'edit', resubmit: 'resubmit', archive: 'archive', restore: 'restore', publish: 'publish', delete: 'edit' };
      var labelMap = { edit: '编辑故事', resubmit: '重新提交', archive: '暂时收起', restore: '恢复审核', publish: '发布故事', delete: '删除' };
      var html = '';
      actions.slice(0, 5).forEach(function (a) {
        var icon = iconMap[a.action] || 'edit';
        var label = labelMap[a.action] || a.action || '操作';
        html +=
          '<div class="msa-item">' +
          '<div class="msa-icon ' + icon + '">' +
          '<svg viewBox="0 0 16 16" fill="none" width="12" height="12"><path d="M11 2l3 3-8 8H3v-3l8-8z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg>' +
          '</div>' +
          '<div class="msa-text"><div class="msa-title">' + escHtml(a.gift_title || a.gift_name || '—') + '</div>' +
          '<div class="msa-meta">' + label + '</div></div>' +
          '<div class="msa-time">' + escHtml(a.created_at ? a.created_at.slice(0, 10) : '') + '</div>' +
          '</div>';
      });
      container.innerHTML = html;
    }

    document.getElementById('mySpaceBackBtn').addEventListener('click', exitMySpaceView);

    document.getElementById('mySpaceViewAllPublished').addEventListener('click', function () {
      exitMySpaceView();
      var mineTab = document.querySelector('.filter-tab[data-filter="mine"]');
      if (mineTab) mineTab.click();
    });

    // ── End Favorites View ──────────────────────────────────────────────────

  })();
