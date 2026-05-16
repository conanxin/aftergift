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
  var nextTempId = 9000;
  var lastFocusedElement = null;
  var displayedCount = 8;       // initial visible cards
  var INITIAL_DISPLAY = 8;
  var MAX_DISPLAY = 100;
  var favorites = {};           // { id: true } synced with localStorage

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

  // ── Init ──
  document.addEventListener('DOMContentLoaded', function () {
    loadFavorites();
    loadGifts();
    bindEvents();
    initTextareas();
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

  function saveFavorites() {
    try {
      localStorage.setItem('aftergift_favorites', JSON.stringify(favorites));
    } catch (e) {}
  }

  window.toggleFavorite = function (id) {
    if (favorites[id]) {
      delete favorites[id];
      var mode = window.__AF_MODE || 'static';
      if (mode === 'api' && window.AftergiftAPI) {
        window.AftergiftAPI.unfavoriteGift(id).catch(function () {});
      }
    } else {
      favorites[id] = true;
      var mode2 = window.__AF_MODE || 'static';
      if (mode2 === 'api' && window.AftergiftAPI) {
        window.AftergiftAPI.favoriteGift(id).catch(function () {});
      }
    }
    saveFavorites();
    // Update heart icon on current card
    var cardHeart = document.querySelector('.gift-card[data-id="' + id + '"] .card-favorite-btn');
    if (cardHeart) updateHeartIcon(cardHeart, !!favorites[id]);
    // Update modal heart if open
    var modalHeart = document.getElementById('modalFavoriteBtn');
    if (modalHeart) updateHeartIcon(modalHeart, !!favorites[id]);
    showToast(favorites[id] ? '已收藏这个故事' : '已取消收藏');
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

    if (mode === 'api' && window.AftergiftAPI) {
      // API mode: call FastAPI backend
      window.AftergiftAPI.listGifts({}, []).then(function (result) {
        gifts = result.items;
        showModeIndicator('api', result.items.length);
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
        showModeIndicator('static', -1); // -1 = unknown count (loadGifts called before fetch)
      }
    }
  }

  function loadStaticGifts() {
    fetch('./data/gifts.json')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        gifts = data;
        showModeIndicator('static', data.length);
        renderGifts();
      })
      .catch(function () {
        giftGrid.innerHTML = '<div class="empty-state"><p class="empty-state-line">无法加载礼物数据，请通过本地服务器打开（python3 -m http.server 8080）。</p></div>';
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
      return g.action === currentFilter;
    });

    if (filtered.length === 0) {
      giftGrid.innerHTML = '';
      giftGrid.style.display = 'none';
      emptyState.style.display = 'flex';
      var msgs = {
        all:       '这里还没有礼物故事。',
        favorites: '你还没有收藏任何故事。<br>也许有些旧物，会在某个时刻与你相遇。',
        sell:      '这一类礼物暂时还没有故事。',
        exchange:  '这一类礼物暂时还没有故事。',
        giveaway:  '这一类礼物暂时还没有故事。',
        donate:    '这一类礼物暂时还没有故事。',
        keep:      '这一类礼物暂时还没有故事。'
      };
      emptyStateLine.innerHTML = msgs[currentFilter] || '这一类礼物暂时还没有故事。';
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
  }

  function giftCardHTML(g) {
    var actionClass = 'action-' + g.action;
    var emotionIcon = emotionIconSVG(g.emotion);
    var isFav = !!favorites[g.id];
    var favClass = isFav ? 'favorited' : '';
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
        '<span class="gift-card-status">' + escHtml(g.status) + '</span>' +
      '</div>' +
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
      '</div>';

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

    currentFilter = filter;
    displayedCount = INITIAL_DISPLAY;
    filterTabs.forEach(function (t) {
      t.classList.remove('active');
      t.setAttribute('aria-selected', 'false');
    });
    btn.classList.add('active');
    btn.setAttribute('aria-selected', 'true');

    var mode = window.__AF_MODE || 'static';
    if (mode === 'api' && window.AftergiftAPI) {
      // API mode: re-query with new filter
      var filterParam = (filter === 'all' || filter === 'favorites') ? {} : { action_type: filter };
      window.AftergiftAPI.listGifts(filterParam, []).then(function (result) {
        gifts = result.items;
        renderGifts();
      }).catch(function () {
        showToast('无法加载筛选结果，请检查 API 连接');
      });
    } else {
      renderGifts();
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

    // ── Phase 2D: Init ────────────────────────────────────────────────────────

    function initPhase2D() {
      initDevAuthPanel();
      bindDevAuthEvents();
      initAdminPanel();
    }

    // Run Phase 2D init
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initPhase2D);
    } else {
      initPhase2D();
    }
})();
