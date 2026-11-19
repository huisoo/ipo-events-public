/* 공개용 공모주 · 금융 이벤트 페이지 — data.json 하나만 고치면 화면이 바뀝니다. */
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

  /* 마감일 → D-43 / 오늘 마감 / 마감 */
  function dday(deadline, base) {
    var d = parseDay(deadline);
    if (!d || !base) return null;
    var diff = Math.round((d - base) / 86400000);
    if (diff < 0) return { text: '마감', cls: 'off' };
    if (diff === 0) return { text: '오늘 마감', cls: 'hot' };
    if (diff <= 7) return { text: 'D-' + diff, cls: 'hot' };
    return { text: 'D-' + diff, cls: '' };
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

  /* ── 1. 오늘의 공모주 ─────────────────────── */

  function minEqualBar(m) {
    if (!m) return '';
    var body = '';
    if (m.brokers && m.brokers.length) {
      body = m.brokers.map(function (b) {
        var bits = [];
        if (has(b.name)) bits.push('<em>' + esc(b.name) + '</em>');
        if (has(b.shares)) bits.push(esc(b.shares));
        if (has(b.deposit)) bits.push('<b>' + esc(b.deposit) + '</b>');
        return '<span class="bi">' + bits.join(' ') + '</span>';
      }).join('');
    } else if (has(m.deposit)) {
      body = '<span class="bi"><b>' + esc(m.deposit) + '</b>' +
        (has(m.shares) ? ' ' + esc(m.shares) : '') + '</span>';
    }
    if (!body) return '';
    return '<div class="mineq"' + (has(m.basis) ? ' title="' + esc(m.basis) + '"' : '') + '>' +
      '<span class="k">균등 최소증거금</span>' + body + '</div>';
  }

  function opinionRows(ipo, name) {
    var hanjan = ipo.hanjan || {};
    var gm = ipo.gongmorin || {};
    var hit = null;
    (hanjan.items || []).forEach(function (it) {
      if (!hit && it.name === name) hit = it;
    });

    var out = '';

    /* 공모주한잔 */
    if (hit || hanjan.note) {
      var vs = '';
      if (hit && has(hit.equal)) vs += '<span class="v ' + tone(hit.equal) + '">균등 ' + esc(hit.equal) + '</span>';
      if (hit && has(hit.proportional)) vs += '<span class="v ' + tone(hit.proportional) + '">비례 ' + esc(hit.proportional) + '</span>';
      var vUrl = (hanjan.video && hanjan.video.url) || hanjan.channelUrl || '';
      out += '<div class="op-row">' +
          '<span class="op-name">🍸 ' + esc(hanjan.channel || '공모주한잔') + '</span>' + vs +
          (vUrl ? '<a class="op-link" href="' + esc(vUrl) + '" target="_blank" rel="noopener"' +
            (hanjan.video && hanjan.video.title ? ' title="' + esc(hanjan.video.title) + '"' : '') + '>' +
            (hanjan.video && hanjan.video.url ? '분석 영상' : '채널') + '<i aria-hidden="true">›</i></a>' : '') +
        '</div>' +
        (hanjan.note ? '<div class="op-note">' + esc(hanjan.note) + '</div>' : '');
    }

    /* 공모주린이 */
    if (has(gm.verdict) || has(gm.note)) {
      var gUrl = (gm.video && gm.video.url) || gm.channelUrl || '';
      out += '<div class="op-row">' +
          '<span class="op-name">📺 ' + esc(gm.name || '공모주린이') + '</span>' +
          (has(gm.verdict) ? '<span class="v ' + tone(gm.verdict) + '">' + esc(gm.verdict) + '</span>' : '') +
          (gUrl ? '<a class="op-link" href="' + esc(gUrl) + '" target="_blank" rel="noopener">분석 영상<i aria-hidden="true">›</i></a>' : '') +
        '</div>' +
        (has(gm.note)
          ? '<div class="op-note">' +
              (has(gm.score) ? '<b class="sc ' + scoreTone(gm.score) + '">종합점수 ' + esc(gm.score) + '</b> · ' : '') +
              esc(gm.note) + '</div>'
          : '');
    }

    if (gm.live && gm.live.on && (gm.live.url || gm.channelUrl)) {
      out += '<a class="live" href="' + esc(gm.live.url || gm.channelUrl) + '" target="_blank" rel="noopener">' +
          '<span class="dot" aria-hidden="true"></span>' +
          '<span>' + esc(gm.live.label || '실시간 경쟁률 보기') + '</span>' +
          '<em>' + esc(gm.name || '공모주린이') + '</em>' +
        '</a>';
    }

    return out ? '<div class="ops">' + out + '</div>' : '';
  }

  function subscribeCard(s, ipo) {
    var badge = String(s.badge || '').replace(/^오늘\s*청약\s*/, '');
    var price = String(s.price || '');
    var priceNum = price.replace(/^확정\s*/, '');

    return '<article class="pcard accent-ipo">' +
        '<div class="ptop"><span class="plbl">오늘 청약</span>' +
          (badge ? '<span class="ptag">' + esc(badge) + '</span>' : '') +
        '</div>' +
        '<div class="pname">' + esc(s.name) +
          (has(s.market) ? '<span class="pmarket">' + esc(s.market) + '</span>' : '') +
        '</div>' +
        '<div class="pbig"><b>' + esc(priceNum) + '</b>' +
          (has(s.priceNote) ? '<span class="pnote">' + esc(s.priceNote) + '</span>' : '') +
        '</div>' +
        minEqualBar(s.minEqual) +
        '<dl class="pmeta">' +
          (has(s.period) ? '<div><dt>청약</dt><dd><b>' + esc(s.period) + '</b></dd></div>' : '') +
          (has(s.refund) ? '<div><dt>환불</dt><dd>' + esc(s.refund) + '</dd></div>' : '') +
          (has(s.brokers) ? '<div><dt>주관</dt><dd>' + esc(s.brokers) + '</dd></div>' : '') +
        '</dl>' +
        opinionRows(ipo, s.name) +
      '</article>';
  }

  function listingCard(l) {
    var badge = String(l.badge || '').replace(/^오늘\s*상장\s*/, '');
    var pts = (l.points && l.points.length)
      ? '<ul class="pts">' + l.points.map(function (p) { return '<li>' + esc(p) + '</li>'; }).join('') + '</ul>'
      : '';
    var chgCls = dirOf(l.earlyChange);
    return '<article class="pcard accent-list">' +
        '<div class="ptop"><span class="plbl">오늘 상장</span>' +
          (badge ? '<span class="ptag is-list">' + esc(badge) + '</span>' : '') +
        '</div>' +
        '<div class="pname">' + esc(l.name) +
          (has(l.code) ? '<span class="pcode">' + esc(l.code) + '</span>' : '') +
          (has(l.market) ? '<span class="pmarket">' + esc(l.market) + '</span>' : '') +
        '</div>' +
        '<div class="pbig"><b>' + esc(l.earlyPrice) + '</b>' +
          (has(l.earlyChange) ? '<span class="chg ' + chgCls + '">' + esc(l.earlyChange) + '</span>' : '') +
        '</div>' +
        '<dl class="pmeta">' +
          (has(l.ipoPrice) ? '<div><dt>공모가</dt><dd><b>' + esc(l.ipoPrice) + '</b></dd></div>' : '') +
          (has(l.openPrice) ? '<div><dt>시초</dt><dd>' + esc(l.openPrice) +
            (has(l.openChange) ? ' <span class="chg sm ' + dirOf(l.openChange) + '">' + esc(l.openChange) + '</span>' : '') +
            '</dd></div>' : '') +
        '</dl>' +
        pts +
      '</article>';
  }

  function smallRow(kind, label, name, detail) {
    return '<div class="srow">' +
        '<div class="srow-top"><span class="k ' + esc(kind) + '">' + esc(label) + '</span>' +
          (has(name) ? '<b>' + esc(name) + '</b>' : '') + '</div>' +
        (has(detail) ? '<div class="d">' + detail + '</div>' : '') +
      '</div>';
  }

  function ipoSection(ipo) {
    if (!ipo) return '<div class="empty">오늘 공모주 정보가 아직 없어요.</div>';

    var main = '';
    (ipo.subscribe || []).forEach(function (s) { main += subscribeCard(s, ipo); });
    if (ipo.listing && ipo.listing.hasListing) main += listingCard(ipo.listing);
    if (!main) {
      main = '<article class="pcard accent-ipo"><div class="ptop"><span class="plbl">오늘 청약</span></div>' +
        '<div class="empty">오늘은 진행 중인 청약이 없어요.</div></article>';
    }

    var side = '';
    (ipo.cancelled || []).forEach(function (c) {
      side += smallRow('off', c.badge || '청약 취소', c.name, esc(c.body));
    });
    if (ipo.listing && !ipo.listing.hasListing) {
      side += smallRow('off', '오늘 상장', '', esc(ipo.listing.body || '오늘 신규 상장 종목은 없어요.'));
    }
    if (ipo.next) {
      var n = ipo.next;
      var bits = [];
      if (has(n.period)) bits.push(esc(n.period));
      if (has(n.price)) bits.push(esc(n.price));
      if (has(n.brokers)) bits.push(esc(n.brokers));
      if (has(n.memo)) bits.push(esc(n.memo));
      side += smallRow('next', '다음 청약', n.name, bits.join(' · '));
    }
    var sideHtml = side ? '<div class="srows">' + side + '</div>' : '';

    var src = ipo.source
      ? '<div class="src">출처 <a href="' + esc(ipo.source.url) + '" target="_blank" rel="noopener">' +
        esc(ipo.source.label) + '</a></div>'
      : '';

    return main + sideHtml + src;
  }

  /* ── 2. 증권사 신규 개설 혜택 ────────────── */

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

  function eventCard(ev, today) {
    var always = !parseDay(ev.expiresAt);
    var dd = always ? null : dday(ev.expiresAt, today);
    var badge = always
      ? '<span class="ev-dday is-always">상시</span>'
      : (dd ? '<span class="ev-dday ' + dd.cls + '">' + dd.text + '</span>' : '');

    var terms = (ev.terms && ev.terms.length)
      ? '<div class="ev-terms"><span class="k">유의사항</span><ul>' +
          ev.terms.map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') +
        '</ul></div>'
      : '';

    return '<article class="ev" data-id="' + esc(ev.id) + '" data-expires="' + esc(ev.expiresAt || 'always') + '">' +
        '<div class="ev-top">' +
          '<span class="ev-type">' + esc(ev.type) + '</span>' +
          (ev.sample ? '<span class="ev-sample">샘플</span>' : '') +
          badge +
        '</div>' +
        '<h3 class="ev-title">' + esc(ev.title) + '</h3>' +
        (has(ev.provider) ? '<div class="ev-prov">' + esc(ev.provider) + '</div>' : '') +
        '<div class="ev-benefit">' +
          '<span class="k">혜택</span>' +
          '<b>' + esc(ev.benefit) + '</b>' +
          (has(ev.benefitNote) ? '<span class="note">' + esc(ev.benefitNote) + '</span>' : '') +
        '</div>' +
        '<div class="ev-deadline">' +
          '<span class="k">마감일</span>' +
          '<span class="val">' + esc(always ? '상시 진행' : (longDay(ev.expiresAt) || '미정')) + '</span>' +
          (has(ev.period) ? '<span class="per">' + esc(ev.period) + '</span>' : '') +
        '</div>' +
        terms +
        inviteBlock(ev) +
        (ev.link && ev.link.url
          ? '<a class="ev-link" href="' + esc(ev.link.url) + '" target="_blank" rel="noopener">' +
            esc(ev.link.label || '이벤트 자세히') + '<i aria-hidden="true">›</i></a>'
          : '') +
      '</article>';
  }

  /* ── 렌더 ─────────────────────────────── */
  function render(d) {
    var base = parseDay(d.date);
    var today = todayDay();
    var allEvents = d.events || [];
    var liveEvents = allEvents.filter(function (ev) { return !isExpired(ev, today); });
    var hiddenEvents = allEvents.length - liveEvents.length;
    var title = '오늘의 공모주 · 증권사 혜택';
    document.title = title + (d.date ? ' · ' + shortDay(d.date) : '');

    $('dateline').textContent = d.dateLabel || shortDay(d.date);
    $('updated').textContent = d.updatedLabel ? d.updatedLabel + ' 업데이트' : '';

    /* 한눈에 보는 요약 칩 */
    var quick = $('quick');
    var chips = [];
    (d.ipo && d.ipo.subscribe ? d.ipo.subscribe : []).forEach(function (s) {
      chips.push('<a class="qchip" href="#sec-ipo"><span class="qd"></span>청약 <b>' + esc(s.name) + '</b></a>');
    });
    if (d.ipo && d.ipo.listing && d.ipo.listing.hasListing) {
      chips.push('<a class="qchip is-list" href="#sec-ipo"><span class="qd"></span>상장 <b>' +
        esc(d.ipo.listing.name) + '</b></a>');
    }
    if (liveEvents.length) {
      chips.push('<a class="qchip is-ev" href="#sec-events"><span class="qd"></span>증권사 혜택 <b>' +
        liveEvents.length + '건</b></a>');
    }
    if (chips.length) {
      quick.innerHTML = chips.join('');
      quick.hidden = false;
    }

    if (d.draft) {
      var badge = $('draft');
      badge.textContent = d.draftNote || '초안';
      badge.hidden = false;
    }

    $('ipo-body').innerHTML = ipoSection(d.ipo);

    var evs = d.events || [];
    var needCode = liveEvents.filter(function (ev) { return inviteState(ev) === 'missing'; }).length;
    var note = [];
    if (d.eventsAsOf) note.push(shortDay(d.eventsAsOf) + ' 확인 기준이에요.');
    if (needCode) note.push('초대 링크 ' + needCode + '곳은 본인 초대 코드를 넣어야 열려요.');
    note.push('가입 전 혜택·한도·마감일을 꼭 확인하세요.');
    if (hiddenEvents) note.push('기간이 끝난 이벤트 ' + hiddenEvents + '건은 자동으로 숨겼어요.');
    $('ev-note').textContent = note.join(' ');
    $('ev-list').innerHTML = liveEvents.length
      ? liveEvents.map(function (ev) { return eventCard(ev, today); }).join('')
      : '<div class="empty">지금 챙길 이벤트가 없어요.</div>';

    var notices = d.notice || [];
    $('notice-list').innerHTML = notices.map(function (n) { return '<li>' + esc(n) + '</li>'; }).join('');
    $('foot-src').innerHTML =
      '공모주 출처 <a href="' + esc(d.ipo && d.ipo.source ? d.ipo.source.url : '#') +
      '" target="_blank" rel="noopener">' +
      esc(d.ipo && d.ipo.source ? d.ipo.source.label : '38커뮤니케이션') + '</a>' +
      (d.updatedLabel ? ' · ' + esc(d.updatedLabel) + ' 기준' : '');

    $('loading').hidden = true;
    $('main').hidden = false;
    $('foot').hidden = false;
  }

  function fail(err) {
    if (err) console.error(err);
    $('loading').hidden = true;
    $('error').hidden = false;
  }

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
