-- Aftergift 种子数据
-- Phase 2A | 虚构数据，无真实人物

PRAGMA foreign_keys = ON;

-- ── Users ──────────────────────────────────────────────────────────────────
INSERT INTO users (id, anonymous_nickname, phone_hash, email_hash, is_admin, status) VALUES
(
    'user-001',
    '安静的旧物收藏者 #4827',
    'a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456',
    NULL,
    0,
    'active'
),
(
    'user-002',
    '路过的时间拾荒者 #3910',
    'b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef12',
    NULL,
    0,
    'active'
),
(
    'user-003',
    '深夜档案管理员 #7291',
    NULL,
    NULL,
    1,
    'active'
);

-- ── Gifts ──────────────────────────────────────────────────────────────────
INSERT INTO gifts (id, user_id, title, category, relation_type, relation_label, action_type, emotion, price_or_exchange, condition_note, city_blur, is_anonymous, status) VALUES
(
    'gift-001',
    'user-001',
    '星空投影灯',
    '家居装饰',
    '前任',
    '前任',
    'sell',
    '放下',
    '￥280',
    '九成新，配件齐全，遥控器正常',
    '上海',
    1,
    'published'
),
(
    'gift-002',
    'user-002',
    '皮质笔记本',
    '文具',
    '挚友',
    '挚友',
    'exchange',
    '感谢',
    '想换一本类似主题的手账本，或直接赠送',
    '有使用痕迹，内页写了约三分之一',
    '北京',
    1,
    'published'
),
(
    'gift-003',
    'user-001',
    '机械键盘',
    '数码',
    '夫妻',
    '夫妻',
    'sell',
    '释怀',
    '￥650',
    '几乎没用过，包装都在',
    '上海',
    1,
    'pending_review'
);

-- ── Gift Stories ───────────────────────────────────────────────────────────
INSERT INTO gift_stories (id, gift_id, short_story, full_story, story_quality_score, risk_level) VALUES
(
    'story-001',
    'gift-001',
    '在一起三年，分手后每次看到它都会想起那段时间，但留着也只会让自己更难放下。',
    '这只星空投影灯是他当时的生日礼物。我们在一起的三年里，每次加班回家打开它，房间就像被星光包裹。他说，「以后我们有了自己的房子，要把它放在卧室的天花板上。」

后来我们分开了。不是因为谁对谁错，只是走着走着发现彼此的终点不一样了。

这只灯在柜子里放了半年。每次打开抽屉看见它，心里都会咯噔一下。我知道它值得被一个会喜欢它的人继续使用，而不是跟着我一起封存在这段已经结束的关系里。

我希望它能去到一个喜欢星空的人那里。如果能换一套小音箱也很好，或者直接卖掉也好。

我不会祝他不好，但我也不需要再留着这只灯来提醒自己那段过去了。它应该属于下一个喜欢看星星的人，而不是留在我的柜子里。',
    0.85,
    'safe'
),
(
    'story-002',
    'gift-002',
    '她在我最低落的时候送了我这本笔记本，说「把不开心的事写下来，然后继续往前走」。',
    '那段时间工作压力很大，每天加班到凌晨，周末也睡不踏实。她看在眼里，有天突然把这本笔记本放在我桌上，说「把不开心的事写下来，然后继续往前走。」

我一开始觉得有点好笑，觉得写东西能解决什么问题。但那天晚上还是翻开了它，开始零零碎碎地写。写工作、写迷茫、写那些不好意思跟人说的焦虑。

后来慢慢发现，写着写着，心里那些堵的地方好像找到了一些出口。

她后来去了另一个城市发展，我们联系渐渐少了，但每次看到这本笔记本，我还是会想起那个愿意在深夜给我买笔记本的朋友。

现在我自己也慢慢走出来了，这本笔记本我想让它去到下一个需要它的朋友那里。如果有人刚好在经历类似的阶段，欢迎交换或者直接拿走。',
    0.78,
    'safe'
),
(
    'story-003',
    'gift-003',
    '离婚的时候分的，当时想着这东西留着他也用不上，没想到一放就是两年。',
    '离婚的时候，家具家电都分完了，这把机械键盘他没要，我也没想着要。后来整理东西的时候发现它还在，又想着这键盘也不便宜，扔了可惜，用了吧每次看见又想起来。

就这样放了两年。

现在想想，这把键盘本身没有错，它只是一个工具。是我把它跟那段记忆绑在了一起。但说到底，它就是一把键盘而已。

我想让它去到一个会真正使用它的人那里。价格可以商量，或者交换一些实用的家居用品也行。如果没有人要，也可以直接拿走，我只需要确定它能被用起来，而不是继续在这个柜子里放着。',
    0.72,
    'caution'
);

-- ── Review Logs ─────────────────────────────────────────────────────────────
INSERT INTO review_logs (id, gift_id, risk_level, identity_risk, attack_risk, identifiable_person_risk, quality_notes, suggestions_json, reviewer_type, decision, decided_by, decided_at) VALUES
(
    'review-001',
    'gift-001',
    'safe',
    0,
    0,
    0,
    '{"word_count": 312, "has_origin": true, "has_meaning": true, "has_farewell_reason": true, "has_next_hope": true}',
    '[]',
    'ai_rule_engine',
    'approve',
    NULL,
    '2026-04-15 10:30:00'
),
(
    'review-002',
    'gift-002',
    'safe',
    0,
    0,
    0,
    '{"word_count": 287, "has_origin": true, "has_meaning": true, "has_farewell_reason": true, "has_next_hope": true}',
    '[]',
    'ai_rule_engine',
    'approve',
    NULL,
    '2026-04-15 11:00:00'
);

-- ── Favorites ───────────────────────────────────────────────────────────────
INSERT INTO favorites (id, user_id, gift_id) VALUES
(
    'fav-001',
    'user-002',
    'gift-001'
);

-- ── Reports ─────────────────────────────────────────────────────────────────
INSERT INTO reports (id, gift_id, reporter_user_id, reason, detail, status) VALUES
(
    'report-001',
    'gift-003',
    NULL,
    'other',
    '故事内容提到离婚，可能引发负面情绪。建议平台增加对这类故事的审核指引。',
    'resolved_dismissed'
);