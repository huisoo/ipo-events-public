/* 공개용 공모주 1분 요약 페이지 — data.json 하나만 고치면 화면이 바뀝니다.
 *
 * 화면 위계
 *   1레벨  .hero      오늘의 공모주 1분 요약 (오늘 청약·상장 → 균등·비례 결론 →
 *                     주관사별 최소증거금 → 유튜브 요약 → 다음 청약 D-day)
 *   2레벨  .benefits  주관사 신규 개설 혜택 (기본 접힘 아코디언 + 얇은 행)
 *   3레벨  .support   커피 한 잔 응원하기 (푸터 위 조용한 카드, 카카오페이 링크)
 *
 * 오늘 요약 탭 히어로 아래  .share  청약 정보 복사 · 공유하기 (카톡 단톡방 공유용 — 청약 정보만)
 *
 * 상단 탭  .tabs  오늘 요약(#panel-today) | 전체 일정(#panel-schedule, data.json ipo.upcoming)
 */
(function () {
  'use strict';

  /* ── 공통 유틸 ─────────────────────────────── */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function $(id) { return document.getElementById(id); }
  function has(v) { return v != null && String(v) !== ''; }

  function parseDay(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ''));
    return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null;
  }
  /* 2026-11-18 → 11/18(수) */
  function shortDay(iso, fallback) {
    var d = parseDay(iso);
    if (!d) return fallback || '';
    return (d.getMonth() + 1) + '/' + d.getDate() + '(' + '일월화수목금토'.charAt(d.getDay()) + ')';
  }
  function longDay(iso) {
    var d = parseDay(iso);
    if (!d) return '';
    return d.getFullYear() + '.' + String(d.getMonth() + 1).padStart(2, '0') + '.' +
      String(d.getDate()).padStart(2, '0') + ' (' + '일월화수목금토'.charAt(d.getDay()) + ')';
  }
  /* 기기 기준 오늘 0시 */
  function todayDay() {
    var n = new Date();
    return new Date(n.getFullYear(), n.getMonth(), n.getDate());
  }
  /* expiresAt 이 오늘보다 이전이면 만료 (null/빈값 = 상시) */
  function isExpired(ev, today) {
    var d = parseDay(ev && ev.expiresAt);
    return !!(d && today && d < today);
  }

  /* 마감일 → D-43 / 오늘 마감 / 마감 (Date 또는 ISO 문자열) */
  function dday(target, base) {
    var d = target instanceof Date ? target : parseDay(target);
    if (!d || !base) return null;
    var diff = Math.round((d - base) / 86400000);
    if (diff < 0) return { text: '마감', cls: 'off' };
    if (diff === 0) return { text: '오늘 마감', cls: 'hot' };
    if (diff <= 7) return { text: 'D-' + diff, cls: 'hot' };
    return { text: 'D-' + diff, cls: '' };
  }

  /* '11/23(월)~11/24(화)' → 올해 11/23 (이미 지난 날짜면 내년) */
  function periodStart(period, base) {
    var m = /(\d{1,2})\s*\/\s*(\d{1,2})/.exec(String(period || ''));
    if (!m) return null;
    var mo = Number(m[1]), da = Number(m[2]);
    if (!(mo >= 1 && mo <= 12 && da >= 1 && da <= 31)) return null;
    var y = base ? base.getFullYear() : new Date().getFullYear();
    var d = new Date(y, mo - 1, da);
    if (base && (base - d) > 180 * 86400000) d = new Date(y + 1, mo - 1, da);
    return d;
  }

  /* 판단 문구 색 — 패스를 먼저 봄 */
  function tone(v) {
    var s = String(v == null ? '' : v);
    if (/패스|미참여|비추|보류/.test(s)) return 'pass';
    if (/청약|추천|참여/.test(s)) return 'go';
    return 'wait';
  }
  function scoreTone(v) {
    var s = String(v == null ? '' : v);
    if (/^A/i.test(s)) return 'go';
    if (/^B/i.test(s)) return 'wait';
    return 'pass';
  }
  function dirOf(v) {
    var s = String(v == null ? '' : v);
    if (/^-|하락|↓/.test(s)) return 'dn';
    if (/^\+|상승|↑/.test(s)) return 'up';
    return '';
  }

  /* ── 1레벨 · 오늘의 공모주 1분 요약 ───────── */

  function hanjanItem(ipo, name) {
    var items = (ipo.hanjan && ipo.hanjan.items) || [];
    for (var i = 0; i < items.length; i++) {
      if (items[i].name === name) return items[i];
    }
    return null;
  }

  /* 균등·비례 결론 — 같은 판단이면 큰 배지 하나, 다르면 나란히 */
  function verdictBlock(ipo, name) {
    var hit = hanjanItem(ipo, name);
    var eq = hit && has(hit.equal) ? hit.equal : '';
    var pr = hit && has(hit.proportional) ? hit.proportional : '';
    if (!eq && !pr) return '';

    var pills = '';
    if (eq && pr && eq === pr) {
      pills = '<span class="vbig ' + tone(eq) + '">' + esc(eq) + '</span>';
    } else {
      if (eq) pills += '<span class="vbig sm ' + tone(eq) + '"><i>균등</i>' + esc(eq) + '</span>';
      if (pr) pills += '<span class="vbig sm ' + tone(pr) + '"><i>비례</i>' + esc(pr) + '</span>';
    }
    return '<div class="verdict">' +
        '<span class="vk">균등·비례 결론</span>' + pills +
      '</div>';
  }

  /* 주관사별 균등 최소증거금 */
  function depositBlock(m) {
    if (!m) return '';
    var body = '';
    if (m.brokers && m.brokers.length) {
      body = m.brokers.map(function (b) {
        var bits = [];
        if (has(b.name)) bits.push('<em>' + esc(b.name) + '</em>');
        if (has(b.deposit)) bits.push('<b>' + esc(b.deposit) + '</b>');
        if (has(b.shares)) bits.push('<span class="sh">' + esc(b.shares) + '</span>');
        return '<span class="bi">' + bits.join('') + '</span>';
      }).join('');
    } else if (has(m.deposit)) {
      body = '<span class="bi"><b>' + esc(m.deposit) + '</b>' +
        (has(m.shares) ? '<span class="sh">' + esc(m.shares) + '</span>' : '') + '</span>';
    }
    if (!body) return '';
    return '<div class="deposit"' + (has(m.basis) ? ' title="' + esc(m.basis) + '"' : '') + '>' +
        '<span class="dk">주관사별 최소증거금</span>' + body + '</div>';
  }

  /* 청약 기간·환불·주관 */
  function metaRows(s) {
    var rows = '';
    if (has(s.period)) rows += '<div><dt>청약</dt><dd><b>' + esc(s.period) + '</b></dd></div>';
    if (has(s.refund)) rows += '<div><dt>환불</dt><dd>' + esc(s.refund) + '</dd></div>';
    if (has(s.brokers)) rows += '<div><dt>주관</dt><dd>' + esc(s.brokers) + '</dd></div>';
    return rows ? '<dl class="hmeta">' + rows + '</dl>' : '';
  }

  /* 유튜브 요약 — 공모주한잔 / 공모주린이 */
  function ytBlock(ipo, name) {
    var hanjan = ipo.hanjan || {};
    var gm = ipo.gongmorin || {};
    var hit = hanjanItem(ipo, name);
    var out = '';

    if (hit || has(hanjan.note) || (hanjan.video && hanjan.video.url)) {
      var vUrl = (hanjan.video && hanjan.video.url) || hanjan.channelUrl || '';
      var vs = '';
      if (hit && has(hit.equal)) vs += '<span class="v ' + tone(hit.equal) + '">균등 ' + esc(hit.equal) + '</span>';
      if (hit && has(hit.proportional)) vs += '<span class="v ' + tone(hit.proportional) + '">비례 ' + esc(hit.proportional) + '</span>';
      out += '<div class="yt-row">' +
          '<span class="yt-name">🍸 ' + esc(hanjan.channel || '공모주한잔') + '</span>' + vs +
          (vUrl ? '<a class="yt-link" href="' + esc(vUrl) + '" target="_blank" rel="noopener"' +
            (hanjan.video && hanjan.video.title ? ' title="' + esc(hanjan.video.title) + '"' : '') + '>' +
            (hanjan.video && hanjan.video.url ? '분석 영상' : '채널') + '<i aria-hidden="true">›</i></a>' : '') +
        '</div>' +
        (has(hanjan.note) ? '<p class="yt-note">' + esc(hanjan.note) + '</p>' : '');
    }

    if (has(gm.verdict) || has(gm.note) || (gm.video && gm.video.url)) {
      var gUrl = (gm.video && gm.video.url) || gm.channelUrl || '';
      out += '<div class="yt-row">' +
          '<span class="yt-name">📺 ' + esc(gm.name || '공모주린이') + '</span>' +
          (has(gm.verdict) ? '<span class="v ' + tone(gm.verdict) + '">' + esc(gm.verdict) + '</span>' : '') +
          (has(gm.score) ? '<span class="score ' + scoreTone(gm.score) + '">' + esc(gm.score) + '</span>' : '') +
          (gUrl ? '<a class="yt-link" href="' + esc(gUrl) + '" target="_blank" rel="noopener">분석 영상<i aria-hidden="true">›</i></a>' : '') +
        '</div>' +
        (has(gm.note) ? '<p class="yt-note">' + esc(gm.note) + '</p>' : '');
    }

    if (gm.live && gm.live.on && (gm.live.url || gm.channelUrl)) {
      out += '<a class="live" href="' + esc(gm.live.url || gm.channelUrl) + '" target="_blank" rel="noopener">' +
          '<span class="dot" aria-hidden="true"></span>' +
          '<span>' + esc(gm.live.label || '실시간 경쟁률 보기') + '</span>' +
          '<em>' + esc(gm.name || '공모주린이') + '</em>' +
        '</a>';
    }

    return out ? '<div class="yt"><div class="yt-h">유튜브 요약</div>' + out + '</div>' : '';
  }

  /* '오늘 신규 상장 없음 — 다음은 11/20(금) 하나에어로다이내믹스' → '11/20(금) 하나에어로다이내믹스' */
  function listingHint(body) {
    var s = String(body || '').trim();
    s = s.replace(/^오늘\s*신규?\s*상장\s*(이\s*)?없(음|습니다)?\s*[—–\-:·]?\s*/, '');
    s = s.replace(/^다음은\s*/, '');
    return s.trim();
  }

  /* 다음 청약(D-day) · 다음 상장 — 히어로 하단 띠 */
  function nextBand(ipo, today) {
    var rows = '';
    var n = ipo.next;
    if (n) {
      var start = periodStart(n.period, today);
      var dd = start ? dday(start, today) : null;
      var sub = [];
      if (has(n.price)) sub.push(esc(n.price));
      if (has(n.brokers)) sub.push(esc(n.brokers));
      if (has(n.memo)) sub.push(esc(n.memo));
      rows += '<div class="nrow">' +
          '<span class="nk">다음 청약</span>' +
          '<b>' + esc(n.name) + '</b>' +
          (dd ? '<span class="dday ' + dd.cls + '">' + dd.text + '</span>' : '') +
          (has(n.period) ? '<span class="nd">' + esc(n.period) + '</span>' : '') +
        '</div>' +
        (sub.length ? '<div class="nrow is-sub"><span class="nd">' + sub.join(' · ') + '</span></div>' : '');
    }
    if (ipo.listing && !ipo.listing.hasListing) {
      var hint = listingHint(ipo.listing.body);
      if (hint) {
        rows += '<div class="nrow is-sub">' +
            '<span class="nk is-list">다음 상장</span><span class="nd">' + esc(hint) + '</span>' +
          '</div>';
      }
    }
    return rows ? '<div class="hero-next">' + rows + '</div>' : '';
  }

  /* 오늘 청약 카드 — 1분 요약의 본문 */
  function heroCard(s, ipo, today) {
    var badge = String(s.badge || '').replace(/^오늘\s*청약\s*/, '');
    var priceNum = String(s.price || '').replace(/^확정\s*/, '');
    var listingToday = !!(ipo.listing && ipo.listing.hasListing);
    var flags = '<span class="flag">' + esc('오늘 청약' + (badge ? ' ' + badge : '')) + '</span>' +
      (listingToday
        ? '<span class="flag is-list-on">오늘 상장 1건</span>'
        : '<span class="flag is-off">오늘 상장 없음</span>');

    return '<article class="hero">' +
        '<div class="flags">' + flags + '</div>' +
        '<div class="hname">' + esc(s.name) +
          (has(s.market) ? '<span class="hmarket">' + esc(s.market) + '</span>' : '') +
        '</div>' +
        '<div class="hprice"><b>' + esc(priceNum) + '</b>' +
          (has(s.priceNote) ? '<span>' + esc(s.priceNote) + '</span>' : '') +
        '</div>' +
        verdictBlock(ipo, s.name) +
        depositBlock(s.minEqual) +
        metaRows(s) +
        ytBlock(ipo, s.name) +
        nextBand(ipo, today) +
      '</article>';
  }

  /* 오늘 상장 카드 — 청약이 없는 날의 1레벨 (하단 띠는 청약 카드와 동일하게 다음 청약·다음 상장) */
  function listingHero(l, ipo, today) {
    var badge = String(l.badge || '').replace(/^오늘\s*상장\s*/, '');
    var pts = (l.points && l.points.length)
      ? '<ul class="pts">' + l.points.map(function (p) { return '<li>' + esc(p) + '</li>'; }).join('') + '</ul>'
      : '';
    var meta = '';
    if (has(l.ipoPrice)) meta += '<div><dt>공모가</dt><dd><b>' + esc(l.ipoPrice) + '</b></dd></div>';
    if (has(l.openPrice)) {
      meta += '<div><dt>시초</dt><dd>' + esc(l.openPrice) +
        (has(l.openChange) ? ' <span class="chg sm ' + dirOf(l.openChange) + '">' + esc(l.openChange) + '</span>' : '') +
        '</dd></div>';
    }
    return '<article class="hero is-list">' +
        '<div class="flags"><span class="flag is-list">오늘 상장</span>' +
          (badge ? '<span class="flag is-soft">' + esc(badge) + '</span>' : '') +
        '</div>' +
        '<div class="hname">' + esc(l.name) +
          (has(l.code) ? '<span class="hmarket">' + esc(l.code) + '</span>' : '') +
          (has(l.market) ? '<span class="hmarket">' + esc(l.market) + '</span>' : '') +
        '</div>' +
        '<div class="hprice"><b>' + esc(l.earlyPrice) + '</b>' +
          (has(l.earlyChange) ? '<span class="chg ' + dirOf(l.earlyChange) + '">' + esc(l.earlyChange) + '</span>' : '') +
        '</div>' +
        (meta ? '<dl class="hmeta">' + meta + '</dl>' : '') +
        pts +
        nextBand(ipo, today) +
      '</article>';
  }

  function emptyHero(ipo, today) {
    return '<article class="hero is-empty">' +
        '<div class="flags"><span class="flag is-off">오늘 청약 없음</span></div>' +
        '<div class="hname sm">오늘은 청약하는 공모주가 없어요</div>' +
        '<p class="hempty">다음 청약 일정과 지난 결론만 확인하세요.</p>' +
        nextBand(ipo, today) +
      '</article>';
  }

  function smallRow(kind, label, name, detail) {
    return '<div class="srow">' +
        '<div class="srow-top"><span class="k ' + esc(kind) + '">' + esc(label) + '</span>' +
          (has(name) ? '<b>' + esc(name) + '</b>' : '') + '</div>' +
        (has(detail) ? '<div class="d">' + detail + '</div>' : '') +
      '</div>';
  }

  function ipoSection(ipo, today) {
    if (!ipo) return '<div class="empty">오늘 공모주 정보가 아직 없어요.</div>';

    var html = '';
    var subs = ipo.subscribe || [];
    if (subs.length) {
      subs.forEach(function (s) { html += heroCard(s, ipo, today); });
    } else if (!(ipo.listing && ipo.listing.hasListing)) {
      html += emptyHero(ipo, today);
    }
    if (ipo.listing && ipo.listing.hasListing) html += listingHero(ipo.listing, ipo, today);

    return html;
  }

  /* 히어로 아래(공유 버튼 다음) — 철회 종목과 출처 */
  function ipoFoot(ipo) {
    if (!ipo) return '';
    var html = '';
    var side = '';
    (ipo.cancelled || []).forEach(function (c) {
      side += smallRow('off', c.badge || '청약 취소', c.name, esc(c.body));
    });
    if (side) html += '<div class="srows">' + side + '</div>';

    if (ipo.source) {
      html += '<div class="src">출처 <a href="' + esc(ipo.source.url) + '" target="_blank" rel="noopener">' +
        esc(ipo.source.label) + '</a></div>';
    }
    return html;
  }

  /* ── 전체 일정 탭 ────────────────────────── */

  /* 청약 D-day — 기간 중이면 '청약 중', 지나면 '종료' */
  function subBadge(item, today) {
    var s = parseDay(item.start);
    var e = parseDay(item.end) || s;
    if (!s) return null;
    if (e && today > e) return { text: '청약 종료', cls: 'off' };
    if (today >= s) return { text: '청약 중', cls: 'hot' };
    var diff = Math.round((s - today) / 86400000);
    if (diff <= 4) return { text: 'D-' + diff, cls: 'hot' };
    return { text: 'D-' + diff, cls: '' };
  }

  function listBadge(item, today) {
    var d = parseDay(item.date);
    if (!d) return null;
    var diff = Math.round((d - today) / 86400000);
    if (diff < 0) return { text: '상장', cls: 'off' };
    if (diff === 0) return { text: '오늘 상장', cls: 'hot' };
    if (diff <= 4) return { text: 'D-' + diff, cls: 'hot' };
    return { text: 'D-' + diff, cls: '' };
  }

  /* 2026-11-24 ~ 2026-11-25 → 11/24(월)~11/25(화) */
  function dayRange(item) {
    var s = shortDay(item.start);
    if (!has(item.end) || item.end === item.start) return s;
    return s + '~' + shortDay(item.end);
  }

  /* 일정 카드 한 장 — D-day · 종목명 / 일정 · 공모가 / 시장 · 주관 · 환불 */
  function scheduleCard(item, kind, today) {
    var isList = kind === 'listing';
    var dd = isList ? listBadge(item, today) : subBadge(item, today);
    var when = isList
      ? (has(item.date) ? shortDay(item.date) + ' 상장' : '상장일 미정')
      : (has(item.start) ? dayRange(item) + ' 청약' : '일정 미정');

    var sub = [];
    if (has(item.market)) sub.push(esc(item.market));
    if (has(item.brokers)) sub.push(esc(item.brokers));
    if (!isList && has(item.refund)) sub.push('환불 ' + esc(shortDay(item.refund)));

    return '<li class="sc' + (isList ? ' is-list' : '') + '">' +
        '<div class="sc-top">' +
          (dd ? '<span class="sc-dd' + (dd.cls ? ' ' + dd.cls : '') + '">' + esc(dd.text) + '</span>' : '') +
          '<span class="sc-name">' + esc(item.name) + '</span>' +
          (item.spac ? '<span class="sc-tag">스팩</span>' : '') +
        '</div>' +
        '<div class="sc-mid">' +
          '<span class="sc-when">' + esc(when) + '</span>' +
          (has(item.price) ? '<span class="sc-price">' + esc(item.price) + '</span>' : '') +
        '</div>' +
        (sub.length ? '<div class="sc-sub">' + sub.join(' · ') + '</div>' : '') +
      '</li>';
  }

  function scheduleSection(ipo, today) {
    var up = (ipo && ipo.upcoming) || {};
    var subs = (up.subscribe || []).slice().sort(function (a, b) {
      return String(a.start || '9999').localeCompare(String(b.start || '9999'));
    });
    var lists = (up.listing || []).slice().sort(function (a, b) {
      return String(a.date || '9999').localeCompare(String(b.date || '9999'));
    });

    var html = '';

    html += '<div class="sch-head">' +
        '<span class="sch-kicker">앞으로 4주</span>' +
        '<h2 class="sch-h">청약 예정 <b>' + subs.length + '</b>건</h2>' +
        (has(up.windowLabel) ? '<p class="sch-n">' + esc(up.windowLabel) + ' · 희망 공모가 기준</p>' : '') +
      '</div>';
    html += subs.length
      ? '<ul class="sch-list" id="sch-subscribe">' +
          subs.map(function (it) { return scheduleCard(it, 'subscribe', today); }).join('') + '</ul>'
      : '<div class="empty">예정된 청약 일정이 아직 없어요.</div>';

    html += '<div class="sch-head is-2nd">' +
        '<h2 class="sch-h">상장 예정 <b>' + lists.length + '</b>건</h2>' +
        '<p class="sch-n">확정 공모가 기준 · 상장일이 나온 종목만</p>' +
      '</div>';
    html += lists.length
      ? '<ul class="sch-list" id="sch-listing">' +
          lists.map(function (it) { return scheduleCard(it, 'listing', today); }).join('') + '</ul>'
      : '<div class="empty">상장일이 확정된 종목이 아직 없어요.</div>';

    var cancelled = (ipo && ipo.cancelled) || [];
    if (cancelled.length) {
      html += '<div class="sch-cancel">' + cancelled.map(function (c) {
        return '<div class="sc-row">' +
            '<span class="sc-off">' + esc(c.badge || '철회') + '</span>' +
            '<b>' + esc(c.name) + '</b>' +
            (has(c.body) ? '<span class="sc-off-n">' + esc(c.body) + '</span>' : '') +
          '</div>';
      }).join('') + '</div>';
    }

    var src = up.source || (ipo && ipo.source) || {};
    html += '<div class="sch-src" id="sch-src">출처 ' +
        '<a href="' + esc(src.url || '#') + '" target="_blank" rel="noopener">' +
          esc(src.label || '38커뮤니케이션 공모주 청약일정') + '</a>' +
        ' · <a href="https://www.38.co.kr/html/fund/index.htm?o=nw" target="_blank" rel="noopener">신규상장 일정</a>' +
        (has(up.asOf) ? ' · ' + esc(shortDay(up.asOf)) + ' 확인' : '') +
      '</div>';
    if (has(up.sourceNote)) html += '<p class="sch-note">' + esc(up.sourceNote) + '</p>';

    return html;
  }

  /* ── 2레벨 · 증권사 신규 개설 혜택 ────────── */

  /*
   * 신청 방법 블록 — 초대 코드가 없는 이벤트는 방법만 한 줄로 보여 줍니다.
   * 코드/배포상 세 가지로 구분합니다.
   *   ready   : 본인 코드·링크가 data.json 에 들어가 복사할 수 있음
   *   missing : 슬롯만 있고 본인 코드가 아직 없음 → '본인 초대 코드 입력 필요'
   *   none    : 초대 코드가 필요 없는 이벤트(계좌개설만) → 복사 버튼 없음
   */
  function inviteState(ev) {
    var inv = ev.invite || {};
    if (inv.status === 'none') return 'none';
    if (inv.status === 'ready' && (has(inv.code) || has(inv.url))) return 'ready';
    if (!inv.status && has(ev.code) && !/여기에|입력|미정|TBD/i.test(ev.code)) return 'ready';
    return 'missing';
  }

  function inviteBlock(ev) {
    var inv = ev.invite || {};
    var state = inviteState(ev);
    var howto = has(inv.howTo)
      ? '<span class="howto">' + esc(inv.howTo) + '</span>'
      : '';

    if (state === 'none') {
      return '<div class="ev-code is-none">' +
          '<span class="inv-state">신청 방법</span>' +
          howto +
        '</div>';
    }
    if (state === 'missing') {
      return '<div class="ev-code is-pending">' +
          '<span class="inv-state">본인 초대 코드 입력 필요</span>' +
          '<code class="code-text">아직 등록 전</code>' +
          '<button type="button" class="copy" data-pending="1" data-copy=""' +
            ' aria-label="' + esc(ev.title) + ' 초대 코드는 아직 등록 전">복사</button>' +
          howto +
        '</div>';
    }
    var text = inv.code || inv.url;
    return '<div class="ev-code is-ready">' +
        '<span class="inv-state">내 초대 코드</span>' +
        '<code class="code-text">' + esc(text) + '</code>' +
        '<button type="button" class="copy" data-pending="0" data-copy="' + esc(text) + '"' +
          ' aria-label="' + esc(ev.title) + ' 초대 코드 복사">복사</button>' +
        howto +
      '</div>';
  }

  /* 얇은 한 줄 + 탭하면 상세 조건·공식 링크 */
  function eventRow(ev, today) {
    var always = !parseDay(ev.expiresAt);
    var dd = always ? null : dday(ev.expiresAt, today);
    var badge = always
      ? '<span class="ev-dday is-always">상시</span>'
      : (dd ? '<span class="ev-dday ' + dd.cls + '">' + dd.text + '</span>' : '');

    var prov = has(ev.provider) ? String(ev.provider).split('·')[0].trim() : (ev.type || '');

    var terms = (ev.terms && ev.terms.length)
      ? '<div class="ev-terms"><span class="k">유의사항</span><ul>' +
          ev.terms.map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') +
        '</ul></div>'
      : '';

    return '<details class="ev" data-id="' + esc(ev.id) + '" data-expires="' + esc(ev.expiresAt || 'always') + '">' +
        '<summary class="ev-sum">' +
          '<span class="ev-prov">' + esc(prov) + '</span>' +
          '<span class="ev-ben">' + esc(ev.benefit || ev.title) + '</span>' +
          (ev.sample ? '<span class="ev-sample">샘플</span>' : '') +
          badge +
          '<span class="ev-chev" aria-hidden="true"></span>' +
        '</summary>' +
        '<div class="ev-body">' +
          '<h3 class="ev-title">' + esc(ev.title) + '</h3>' +
          (has(ev.provider) ? '<div class="ev-prov-full">' + esc(ev.provider) + '</div>' : '') +
          '<div class="ev-benefit">' +
            '<span class="k">혜택</span>' +
            '<b>' + esc(ev.benefit) + '</b>' +
            (has(ev.benefitNote) ? '<span class="note">' + esc(ev.benefitNote) + '</span>' : '') +
          '</div>' +
          '<div class="ev-deadline">' +
            '<span class="k">마감</span>' +
            '<span class="val">' + esc(always ? '상시 진행' : (longDay(ev.expiresAt) || '미정')) + '</span>' +
            (has(ev.period) ? '<span class="per">' + esc(ev.period) + '</span>' : '') +
          '</div>' +
          terms +
          inviteBlock(ev) +
          (ev.link && ev.link.url
            ? '<a class="ev-link" href="' + esc(ev.link.url) + '" target="_blank" rel="noopener">' +
              esc(ev.link.label || '이벤트 자세히') + '<i aria-hidden="true">›</i></a>'
            : '') +
        '</div>' +
      '</details>';
  }

  /* ── 렌더 ─────────────────────────────── */
  function render(d) {
    var today = todayDay();
    var allEvents = d.events || [];
    var liveEvents = allEvents.filter(function (ev) { return !isExpired(ev, today); });
    var hiddenEvents = allEvents.length - liveEvents.length;
    var title = '오늘의 공모주 1분 요약';
    document.title = title + (d.date ? ' · ' + shortDay(d.date) : '');

    $('dateline').textContent = d.dateLabel || shortDay(d.date);
    $('updated').textContent = d.updatedLabel ? d.updatedLabel + ' 업데이트' : '';

    if (d.draft) {
      var badge = $('draft');
      badge.textContent = d.draftNote || '초안';
      badge.hidden = false;
    }

    $('ipo-body').innerHTML = ipoSection(d.ipo, today);
    $('ipo-foot').innerHTML = ipoFoot(d.ipo);
    $('schedule-body').innerHTML = scheduleSection(d.ipo, today);

    /* 2레벨: 개설 혜택 — 기본 접힘, 머리말에 건수만 */
    $('ev-count').textContent = liveEvents.length;
    var needCode = liveEvents.filter(function (ev) { return inviteState(ev) === 'missing'; }).length;
    var note = [];
    if (d.eventsAsOf) note.push(shortDay(d.eventsAsOf) + ' 확인 기준이에요.');
    if (needCode) note.push('초대 링크 ' + needCode + '곳은 본인 초대 코드를 넣어야 열려요.');
    note.push('가입 전 혜택·한도·마감일을 꼭 확인하세요.');
    if (hiddenEvents) note.push('기간이 끝난 이벤트 ' + hiddenEvents + '건은 자동으로 숨겼어요.');
    $('ev-note').textContent = note.join(' ');
    $('ev-list').innerHTML = liveEvents.length
      ? liveEvents.map(function (ev) { return eventRow(ev, today); }).join('')
      : '<div class="empty">지금 챙길 이벤트가 없어요.</div>';

    var notices = d.notice || [];
    $('notice-list').innerHTML = notices.map(function (n) { return '<li>' + esc(n) + '</li>'; }).join('');
    $('foot-src').innerHTML =
      '공모주 출처 <a href="' + esc(d.ipo && d.ipo.source ? d.ipo.source.url : '#') +
      '" target="_blank" rel="noopener">' +
      esc(d.ipo && d.ipo.source ? d.ipo.source.label : '38커뮤니케이션') + '</a>' +
      (d.updatedLabel ? ' · ' + esc(d.updatedLabel) + ' 기준' : '');

    setShare(d);

    $('loading').hidden = true;
    $('main').hidden = false;
    $('tabs').hidden = false;
    $('share').hidden = !shareText;
    $('support').hidden = false;
    $('foot').hidden = false;
    setTab(tabFromUrl(), { silent: true });
  }

  /* ── 탭 (오늘 요약 · 전체 일정) ───────────── */
  var TABS = ['today', 'schedule'];

  function tabFromUrl() {
    var q = (location.search.match(/[?&]tab=([a-zA-Z]+)/) || [])[1];
    var h = String(location.hash || '').replace(/^#!?\/?/, '').replace(/[?&].*$/, '');
    var t = q || h;
    return TABS.indexOf(t) >= 0 ? t : 'today';
  }

  function setTab(name, opts) {
    if (TABS.indexOf(name) < 0) name = 'today';
    TABS.forEach(function (t) {
      var btn = $('tab-' + t), panel = $('panel-' + t);
      if (!btn || !panel) return;
      var on = t === name;
      btn.classList.toggle('is-on', on);
      btn.setAttribute('aria-selected', on ? 'true' : 'false');
      panel.hidden = !on;
    });
    if (!(opts && opts.silent)) {
      var url = location.pathname + (name === 'schedule' ? '?tab=schedule' : '');
      try { history.replaceState(null, '', url); } catch (e) { /* file:// 등 */ }
    }
    if (!(opts && opts.noScroll)) {
      try { window.scrollTo(0, 0); } catch (e) { /* noop */ }
    }
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest ? e.target.closest('[data-tab]') : null;
    if (!btn) return;
    var name = btn.getAttribute('data-tab');
    if (TABS.indexOf(name) < 0) return;
    e.preventDefault();
    setTab(name);
  });

  document.addEventListener('keydown', function (e) {
    var cur = document.activeElement;
    if (!cur || !cur.getAttribute || !cur.hasAttribute('data-tab')) return;
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    var i = TABS.indexOf(cur.getAttribute('data-tab'));
    var next = TABS[(i + (e.key === 'ArrowRight' ? 1 : TABS.length - 1)) % TABS.length];
    e.preventDefault();
    setTab(next);
    var btn = $('tab-' + next);
    if (btn) btn.focus();
  });

  window.addEventListener('hashchange', function () {
    var t = tabFromUrl();
    setTab(t, { silent: true });
  });

  function fail(err) {
    if (err) console.error(err);
    $('loading').hidden = true;
    $('error').hidden = false;
  }

  /* ── 청약 정보 공유 · 복사 ─────────────────
   * 카톡 단톡방에 그대로 붙여넣는 '청약 정보' 텍스트(전체 요약 아님).
   *
   *   📌 {종목명} ({M/DD} 마감[ 예정])
   *
   *   * 공모가: …  * 확약률: …  * 시총: …  * 주관사: …  * 최소청약: …  * 수수료: …
   *   * 균등물량: …  * 예상 비례경쟁률: …  * 비례 10주: …  * 풀청약: …
   *   * 환불일: …  * 상장일: …
   *
   *   ✅ 청약 의견: …
   *
   * 오늘 청약 종목이 여러 개면 빈 줄로 구분해 순서대로, 오늘 청약이 없으면 ipo.next를
   * 같은 포맷으로 내보냅니다. 값이 없거나 '미정'·'확인 필요'인 항목은 줄을 만들지 않습니다.
   * 클립보드 복사본은 마지막 줄에 URL을 붙이고, navigator.share 는 url 을 따로 넘깁니다.
   */
  var SITE_URL = 'https://ipo-events-public.vercel.app';
  var SHARE_TITLE = '공모주 청약 정보';
  var shareText = '';
  var sharePayload = null;

  /* 공유문 순서·라벨 (data.json 필드명 → 사람이 읽는 이름) */
  var SHARE_FIELDS = [
    ['ipoPrice', '공모가'],
    ['lockupRate', '확약률'],
    ['marketCap', '시총'],
    ['brokers', '주관사'],
    ['minSubscription', '최소청약'],
    ['fee', '수수료'],
    ['equalShares', '균등물량'],
    ['expectedProRata', '예상 비례경쟁률'],
    ['proRata10Shares', '비례 10주'],
    ['fullSubscription', '풀청약'],
    ['refundDate', '환불일'],
    ['listingDate', '상장일']
  ];

  /* 값이 비었거나 미정으로 적힌 항목 — 추정 금지, 줄 자체를 뺍니다 */
  function shareUnknown(v) {
    var s = String(v == null ? '' : v).trim();
    if (!s) return true;
    return /^미정/.test(s) || /^확인\s*(필요|못|전)/.test(s) || /^(-+|tbd|n\/a)$/i.test(s);
  }

  /* '2026-11-27' · '11/27(금)' → '11/27' */
  function mdd(v) {
    var s = String(v == null ? '' : v).trim();
    var iso = /^(\d{4})-(\d{2})-(\d{2})/.exec(s);
    if (iso) return Number(iso[2]) + '/' + iso[3];
    return s.replace(/\([일월화수목금토]\)/g, '').trim();
  }

  /* 필드 값 — ipoPrice 는 price, refundDate 는 refund 로 대신할 수 있습니다 */
  function shareValue(item, key) {
    var raw = has(item[key]) ? item[key] : '';
    if (!has(raw) && key === 'ipoPrice') raw = item.price || '';
    if (!has(raw) && key === 'refundDate') raw = item.refund || '';
    var v = String(raw == null ? '' : raw).trim();
    if (key === 'ipoPrice') v = v.replace(/^확정\s*/, '');
    if (key === 'refundDate') v = v.replace(/^환불\s*/, '');
    if (key === 'refundDate' || key === 'listingDate') v = mdd(v);
    return shareUnknown(v) ? '' : v;
  }

  /* 마감일 M/DD — closeDateLabel · closeDate · period(마지막 M/D) */
  function closeText(item) {
    var v = has(item.closeDateLabel) ? item.closeDateLabel
      : (has(item.closeDate) ? item.closeDate : '');
    if (has(v)) return mdd(v);
    var src = String(item.period || '');
    var re = /(\d{1,2})\s*\/\s*(\d{1,2})/g, m, last = '';
    while ((m = re.exec(src))) last = Number(m[1]) + '/' + m[2];
    return last;
  }

  /* 마감일 Date — closeDate(ISO) 우선, 없으면 M/DD */
  function closeDay(item) {
    var d = parseDay(item.closeDate);
    if (d) return d;
    var label = closeText(item);
    return label ? periodStart(label, todayDay()) : null;
  }

  /* 괄호 안 '마감' 뒤 문구 — 다음 청약은 지나지 않았으면 '예정' */
  function closeNote(item, isNext) {
    if (has(item.closeNote)) return String(item.closeNote).trim();
    if (!isNext) return '';
    var d = closeDay(item);
    return (d && d <= todayDay()) ? '' : '예정';
  }

  /* 공유할 청약 목록 — 오늘 청약 종목들, 없으면 다음 청약 */
  function shareItems(d) {
    var ipo = d.ipo || {};
    var subs = ipo.subscribe || [];
    if (subs.length) return subs.map(function (s) { return { item: s, next: false }; });
    if (ipo.next && has(ipo.next.name)) return [{ item: ipo.next, next: true }];
    return [];
  }

  /* 종목 한 건 — 제목 / 항목 / 청약 의견 */
  function shareBlock(item, isNext) {
    var head = '📌 ' + String(item.name == null ? '' : item.name).trim();
    var close = closeText(item);
    var note = closeNote(item, isNext);
    if (close) head += ' (' + close + ' 마감' + (note ? ' ' + note : '') + ')';

    var bullets = [];
    SHARE_FIELDS.forEach(function (f) {
      var v = shareValue(item, f[0]);
      if (v) bullets.push('* ' + f[1] + ': ' + v);
    });
    var opinion = shareValue(item, 'opinion');

    var parts = [head];
    if (bullets.length) parts.push(bullets.join('\n'));
    if (opinion) parts.push('✅ 청약 의견: ' + opinion);
    return parts.join('\n\n');
  }

  function shareBody(d) {
    return shareItems(d).map(function (it) {
      return shareBlock(it.item, it.next);
    }).join('\n\n');
  }

  function setShare(d) {
    var body = shareBody(d);
    shareText = body ? body + '\n' + SITE_URL : '';
    sharePayload = body ? { title: SHARE_TITLE, text: body, url: SITE_URL } : null;
  }

  /* 버튼 라벨을 잠깐 바꿔 복사 피드백 */
  function flashLabel(btn, label) {
    if (!btn) return;
    if (!btn.dataset.label) btn.dataset.label = btn.innerHTML;
    btn.innerHTML = label;
    btn.classList.add('done');
    clearTimeout(btn._labelTimer);
    btn._labelTimer = setTimeout(function () {
      btn.innerHTML = btn.dataset.label;
      btn.classList.remove('done');
    }, 1800);
  }

  /* 공유 시트를 못 쓰는 환경 → 청약 정보 복사로 폴백 */
  function shareFallback(btn, msg) {
    copy(shareText).then(function (ok) {
      toast(ok ? (msg || '공유 기능이 없는 환경이라 청약 정보를 복사했어요')
        : '공유를 지원하지 않는 환경이에요. 청약 정보 복사 버튼을 눌러 주세요', ok ? 'ok' : '');
      if (ok) flashLabel(btn, '복사됐어요');
    });
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest ? e.target.closest('[data-share]') : null;
    if (!btn || !shareText) return;
    var kind = btn.getAttribute('data-share');

    if (kind === 'copy') {
      copy(shareText).then(function (ok) {
        if (!ok) { toast('복사가 안 됐어요. 길게 눌러 복사해 주세요'); return; }
        toast('청약 정보를 복사했어요 · 카톡에 붙여넣기', 'ok');
        flashLabel(btn, '복사됐어요');
      });
      return;
    }

    if (kind === 'share') {
      if (!navigator.share) { shareFallback(btn); return; }
      var p;
      try {
        p = navigator.share(sharePayload);
      } catch (err) {
        shareFallback(btn);
        return;
      }
      if (p && p.then) {
        p.then(function () { /* 공유 시트로 넘겼어요 */ }, function (err) {
          if (err && err.name === 'AbortError') return;  /* 사용자가 닫음 — 조용히 */
          shareFallback(btn, '공유가 안 돼서 청약 정보를 복사했어요');
        });
      }
    }
  });

  /* ── 코드 복사 ─────────────────────────── */
  var toastTimer = null;
  function toast(msg, kind) {
    var t = $('toast');
    if (!t) return;
    t.textContent = msg;
    t.className = 'toast on' + (kind ? ' ' + kind : '');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.className = 'toast'; }, 2200);
  }

  function legacyCopy(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.top = '-1000px';
    document.body.appendChild(ta);
    ta.select();
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    document.body.removeChild(ta);
    return ok;
  }

  function copy(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(function () { return true; }, function () {
        return legacyCopy(text);
      });
    }
    return Promise.resolve(legacyCopy(text));
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest ? e.target.closest('button.copy') : null;
    if (!btn) return;
    var code = btn.getAttribute('data-copy') || '';
    if (btn.getAttribute('data-pending') === '1') {
      toast('본인 초대 코드를 넣기 전이에요');
      return;
    }
    copy(code).then(function (ok) {
      if (!ok) { toast('복사가 안 됐어요. 길게 눌러 복사해 주세요'); return; }
      toast('초대 코드를 복사했어요', 'ok');
      var label = btn.textContent;
      btn.textContent = '복사됨';
      btn.classList.add('done');
      setTimeout(function () {
        btn.textContent = label;
        btn.classList.remove('done');
      }, 1800);
    });
  });

  /* ── 시작 ─────────────────────────────── */
  fetch('data.json?t=' + Math.floor(Date.now() / 60000), { cache: 'no-store' })
    .then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(render)
    .catch(fail);
})();
