/* 공개용 공모주 1분 요약 페이지 — data.json 하나만 고치면 화면이 바뀝니다.
 *
 * 화면 위계
 *   1레벨  .hero      오늘의 공모주 1분 요약 (오늘 청약·상장 → 균등·비례 결론 →
 *                     주관사별 최소증거금 → 유튜브 요약 → 다음 청약 D-day)
 *   2레벨  .benefits  주관사 신규 개설 혜택 (기본 접힘 아코디언 + 얇은 행)
 *   3레벨  .support   커피 한 잔 응원하기 (푸터 위 조용한 카드, 카카오페이 링크)
 *
 * 오늘 요약 탭 히어로 아래  .share  '청약 정보 공유' | '상장 정보 공유' 2버튼 고정
 *                                  (카톡 단톡방 공유용 — 없는 쪽은 이유 적힌 비활성.
 *                                   공유 시트 없음·오류면 링크까지 복사로 폴백)
 *
 * 상단 탭  .tabs  오늘 요약(#panel-today) | 전체 일정(#panel-schedule, data.json ipo.upcoming)
 *                   | 혜택(#panel-benefits, data.json benefits[] — 증권사·금융 / 간편 이벤트·설문)
 * 전체 일정 맨 위 .cash  균등 최소증거금(이번 달/전체 · 스팩 제외) — 피크 자금 강조 + 종목별 예상 증거금
 *   증거금률은 일반 공모주 50%, 스팩(기업인수목적회사) 100% — 종목별로 다르게 계산합니다.
 * 오늘 요약 하단  .ben-link  '증권사 개설·현금성 혜택 N건 보기 →' 한 줄 배너 (혜택 탭으로 전환)
 * 오늘 요약 하단  .install  '홈 화면에 앱으로 추가' 한 줄 (standalone 이면 숨김 /
 *                            Android 는 beforeinstallprompt 가 뜰 때만 네이티브 설치 창,
 *                            iOS 는 공유 → '홈 화면에 추가' 안내 / × 는 localStorage 에 저장)
 * 오늘 요약 맨 아래 .banner-embed  '블로그 배너 퍼가기' (기본 접힘 — banner.png 미리보기 +
 *                                  HTML 코드/이미지 URL 복사·저장. banner.png 는
 *                                  scripts/generate_banner.py 가 data.json 으로 매일 다시 만든다)
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

  /* ── 테마 (기본 라이트 고정 · 상단 토글) ──────────
   * - 저장값 mydon-theme(light/dark, 기본 light)만 신뢰한다. 시스템 다크는 무시.
   * - 첫 페인트 전 data-theme 부여는 index.html <head> 인라인 스크립트가 맡는다(깜빡임 방지).
   *   여기서는 아이콘·aria 동기화와 토글 클릭 처리만. */
  var THEME_KEY = 'mydon-theme';
  function currentTheme() {
    return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }
  function applyTheme(theme) {
    var dark = theme === 'dark';
    var root = document.documentElement;
    if (dark) root.setAttribute('data-theme', 'dark');
    else root.removeAttribute('data-theme');
    var meta = $('theme-color');
    if (meta) meta.setAttribute('content', dark ? '#101012' : '#f4f6f8');
    var btn = $('theme-toggle');
    if (btn) {
      var label = dark ? '라이트 모드로 전환' : '다크 모드로 전환';
      btn.setAttribute('aria-pressed', dark ? 'true' : 'false');
      btn.setAttribute('aria-label', label);
      btn.setAttribute('title', label);
    }
  }
  function initTheme() {
    applyTheme(currentTheme());
    var btn = $('theme-toggle');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var next = currentTheme() === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      try { localStorage.setItem(THEME_KEY, next); } catch (e) { /* 저장 불가(사생활 모드)면 이번 화면만 전환 */ }
    });
  }

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
  /* ── 오늘 0시 (KST 고정) ───────────────────
   * 브라우저 타임존과 무관하게 Asia/Seoul(UTC+9) 날짜를 씁니다.
   * UTC 게터로 읽으면 기기 설정이 무엇이든 KST 벽시계가 나옵니다.
   * ?date=YYYY-MM-DD 로 날짜를 고정할 수 있습니다(검증·디버그용 — 기본 동작은 현재 KST 시각). */
  var FIXED_DAY = null;
  function kstToday() {
    var t = new Date(Date.now() + 9 * 3600000);
    return new Date(t.getUTCFullYear(), t.getUTCMonth(), t.getUTCDate());
  }
  function urlParam(name) {
    var m = new RegExp('[?&]' + name + '=([^&#]*)').exec(location.search || '');
    return m ? decodeURIComponent(m[1].replace(/\+/g, ' ')) : '';
  }
  function todayDay() {
    return FIXED_DAY || kstToday();
  }
  FIXED_DAY = parseDay(urlParam('date'));

  /* 토·일 = 주말(시장 휴장) */
  function isWeekend(d) {
    var w = (d || todayDay()).getDay();
    return w === 0 || w === 6;
  }
  function addDays(d, n) {
    return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
  }
  /* 2026-11-22 → 2026년 11월 22일 일요일 */
  function korDay(d) {
    return d.getFullYear() + '년 ' + (d.getMonth() + 1) + '월 ' + d.getDate() + '일 ' +
      ['일', '월', '화', '수', '목', '금', '토'][d.getDay()] + '요일';
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

  /* ── 주관사 앱 열기 (OS 자동 구분) ───────────
   * 증권사 공식 MTS 의 스토어 ID — 앱 이름·개발자를 스토어 페이지에서 확인한 것만.
   *   play  : Google Play 패키지명 / app : App Store 숫자 ID
   *   scheme(+host) : Android 앱이 BROWSABLE 로 선언한 커스텀 스킴 — 앱 매니페스트에서 확인한 것만
   *   site  : 앱이 https 앱 링크(App Links)로 등록한 주소 — 사이트가 assetlinks.json 으로 공개한 것만
   * 셋 다 없는 앱은 억지 intent 를 만들지 않고 Play 스토어 앱 페이지로 보냅니다.
   *   앱 미설치 시에도 Play 스토어가 열리니, “앱이 있으면 열고 없으면 설치” 동작은 그대로입니다.
   * 확인되지 않은 증권사는 넣지 않습니다(버튼도 만들지 않음).
   */
  var BROKER_APPS = {
    'IBK투자증권':  { play: 'com.ibks.ione.mts',                 app: '6612018102' },  /* IBK투자증권 (대표MTS) — BROWSABLE 딥링크·앱 링크 확인 안 됨 */
    '삼성증권':     { play: 'com.samsungpop.android.mpop',       app: '1150231646',
                      site: 'https://www.samsungpop.com/' },                          /* mPOP — www.samsungpop.com 앱 링크 */
    '미래에셋증권': { play: 'com.miraeasset.trade',              app: '1248716281' },  /* 미래에셋증권 MAPS */
    '한국투자증권': { play: 'com.truefriend.neosmartarenewal',    app: '1621986905' },  /* 한투-한국투자증권 */
    'KB증권':       { play: 'com.kbsec.mts.iplustarngm2',        app: '350742701' },   /* KB M-able */
    'NH투자증권':   { play: 'com.wooriwm.txsmart',               app: '486312400',
                      scheme: 'txsmart', host: 'txrun' },                             /* 나무증권 — txsmart://txrun (BROWSABLE) */
    '하나증권':     { play: 'com.hanasec.pro',                   app: '6755097570' },  /* 하나증권V-대표MTS(NEW) */
    '신한투자증권': { play: 'com.shinhaninvest.nsmts',            app: '1168512940' },  /* 신한 SOL증권 */
    '키움증권':     { play: 'com.kiwoom.heromts',                app: '1570370057' },  /* 키움증권 영웅문S# */
    '신영증권':     { play: 'com.shinyoung.mts',                 app: '1619250855' },  /* 신영증권 그린 */
    '유진투자증권': { play: 'com.eugenefn.smartchampion2',        app: '1080300592' },  /* 유진투자증권 */
    '대신증권':     { play: 'com.daishin',                       app: '414850336' },   /* 대신증권 CYBOS Touch */
    '우리투자증권': { play: 'com.wooriib.wonmts',                app: '6745938978' },  /* 우리WON MTS(증권) */
    'DB증권':       { play: 'com.dbfi.xts',                      app: '1603371564',
                      site: 'https://m.dbsec.co.kr/' },                                /* 알파증권 — m.dbsec.co.kr 앱 링크 */
    'DB금융투자':   { play: 'com.dbfi.xts',                      app: '1603371564',
                      site: 'https://m.dbsec.co.kr/' },                                /* DB증권의 옛 이름 표기 */
    '한화투자증권': { play: 'plus.steps.sapp',                   app: '1200606784' },  /* 한화투자증권 MTS */
    'BNK투자증권':  { play: 'com.bnkfn.mtsplus',                 app: '1170374515' }   /* BNK투자증권 */
  };

  /* iOS(아이폰·아이패드·터치 지원 맥) → App Store, Android → intent:// 직접 실행(미설치 시 Play 폴백),
     그 외(PC) → Google Play */
  function isIOS() {
    var ua = navigator.userAgent || '';
    if (/iPhone|iPad|iPod/i.test(ua)) return true;
    return navigator.platform === 'MacIntel' && (navigator.maxTouchPoints || 0) > 1;
  }

  function isAndroid() {
    return /Android/i.test(navigator.userAgent || '');
  }

  function playUrl(pkg) {
    return 'https://play.google.com/store/apps/details?id=' + pkg;
  }

  /* Android 크롬은 웹 링크로 앱을 열 때 CATEGORY_BROWSABLE 을 강제하므로,
     MAIN/LAUNCHER 만 선언한 앱은 intent:// 로 열리지 않고 바로 폴백(Play 스토어)으로 떨어집니다.
     그래서 BROWSABLE 로 확인된 스킴(또는 앱이 등록한 https 앱 링크)만 intent:// 로 실행하고,
     확인되지 않은 앱은 Play 스토어 앱 페이지로 바로 보냅니다. */
  function androidIntentUrl(a) {
    var fallback = playUrl(a.play);
    var intent = '';
    if (a.scheme) {
      intent = 'intent://' + (a.host || '') + '/#Intent' +
        ';scheme=' + a.scheme +
        ';package=' + a.play +
        ';S.browser_fallback_url=' + encodeURIComponent(fallback) + ';end';
    } else if (a.site) {
      intent = 'intent://' + String(a.site).replace(/^https?:\/\//, '') + '#Intent' +
        ';scheme=https' +
        ';package=' + a.play +
        ';S.browser_fallback_url=' + encodeURIComponent(fallback) + ';end';
    }
    return intent || fallback;
  }

  function brokerAppUrl(name) {
    var a = BROKER_APPS[name];
    if (!a) return '';
    if (isIOS()) return 'https://apps.apple.com/kr/app/id' + a.app;
    if (isAndroid()) return androidIntentUrl(a);
    return playUrl(a.play);
  }

  /* brokers 문자열('KB증권 · NH투자증권') → {증권사} 앱 열기 칩(매핑된 증권사만) */
  function brokerAppLinks(brokers) {
    var out = '';
    var seen = {};
    String(brokers == null ? '' : brokers).split(/[·,、\/]/).forEach(function (raw) {
      var name = raw.trim();
      if (!name || seen[name]) return;
      var url = brokerAppUrl(name);
      if (!url) return;
      seen[name] = 1;
      /* Android intent:// 는 같은 창에서 열어야 빈 새 탭이 남지 않고 앱/폴백으로 넘어갑니다.
         스토어·App Store 링크는 새 탭으로 열어 원래 페이지를 남겨 둡니다. */
      var blank = (isAndroid() && url.indexOf('intent://') === 0)
        ? '' : ' target="_blank" rel="noopener"';
      out += '<a class="app-open" href="' + esc(url) + '"' + blank +
        ' aria-label="' + esc(name) + ' 앱 열기">' +
        '<span class="ico" aria-hidden="true">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"' +
          ' stroke-linecap="round" stroke-linejoin="round">' +
          '<rect x="6.5" y="2.8" width="11" height="18.4" rx="2.6"/><path d="M10.8 18.6h2.4"/>' +
          '</svg></span>' + esc(name) + ' 앱 열기</a>';
    });
    return out ? '<div class="app-open-row">' + out + '</div>' : '';
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

  /* 청약 기간·환불·주관 — 폰에서 한두 줄로 접히는 컴팩트 요약 (3행 dl 대신) */
  function specBits(pairs) {
    var bits = [];
    pairs.forEach(function (p) {
      if (!has(p[1])) return;
      bits.push('<span class="hs"><em>' + esc(p[0]) + '</em>' +
        (p[2] ? '<b>' + esc(p[1]) + '</b>' : esc(p[1])) + '</span>');
    });
    return bits.length ? '<div class="hspec">' + bits.join('<i aria-hidden="true">·</i>') + '</div>' : '';
  }

  function metaRows(s) {
    return specBits([
      ['청약', String(s.period || '').replace(/\s*~\s*/g, '~'), true],
      ['환불', s.refund, false],
      ['주관', s.brokers, false]
    ]);
  }

  /* ── 유튜버 1줄 요약 (feeds.json 최신 영상 ↔ 오늘 종목명 매칭) ─────
   * data.json 의 공모주한잔·공주 큐레이션(items·verdict)이 있으면 그 판단을 먼저 쓰고,
   * 없으면 수집기(feeds.json)가 모은 최신 영상 중 종목명이 제목에 있는 것을 찾아
   *   채널 · 제목에서 읽은 톤 · 영상 바로가기 · 영상 제목 한 줄  로 보여 줍니다.
   * 예상 매도가·목표가 같은 숫자는 옮기지 않습니다(제목에 원화 금액·목표가가 있으면 요약을 생략). */
  var FEEDS = null;
  var FEED_MAX_AGE_DAYS = 75;

  function normName(s) {
    return String(s == null ? '' : s).replace(/[\s\-–·,.'"()]/g, '').toLowerCase();
  }

  function shortChannel(name) {
    var s = String(name == null ? '' : name);
    var m = s.match(/\(([^)]{1,6})\)/);
    return m ? m[1] : s.replace(/\s+/g, '');
  }

  /* 영상 제목 → 한 줄 요약 (괄호 안 문구 우선, 없으면 대괄호 머리표만 제거) */
  function videoLine(title) {
    var t = String(title == null ? '' : title).trim();
    if (!t) return '';
    var m = t.match(/[（(]([^)）]{2,60})[)）]\s*$/);
    var s = m ? m[1] : t.replace(/^\[[^\]]*\]\s*/, '');
    /* 목표가·매도가·원화 금액이 들어간 문구는 요약으로 쓰지 않는다 */
    if (/(목표\s*가|매도\s*가|예상\s*매도|익절|수익\s*실현)/.test(s)) return '';
    if (/\d[\d,]*\s*원/.test(s)) return '';
    s = s.replace(/\s+/g, ' ').trim();
    return s.length > 42 ? s.slice(0, 41).trim() + '…' : s;
  }

  /* 제목에서만 읽히는 톤 — 판단이 아니라 영상 제목의 낱말 분류라는 뜻으로 짧게 */
  function videoTone(text) {
    var s = String(text == null ? '' : text);
    if (/(철회|리스크|주의|우려|조심|신중|불확실|아쉬|힘\s*조절|부진|약세)/.test(s)) return { t: '신중', c: 'wait' };
    if (/(경쟁률|수급|유통|확약|비례|물량|배정)/.test(s)) return { t: '수급', c: 'pass' };
    if (/(기회|성공|희망|기대|관심|강세|훈풍|호조)/.test(s)) return { t: '기대', c: 'go' };
    return null;
  }

  /* feeds.json → 종목명이 제목에 있는 채널별 최신 영상 (오래된 영상은 제외) */
  function feedHits(name) {
    var channels = (FEEDS && FEEDS.channels) || [];
    var key = normName(name);
    if (!key || !channels.length) return [];
    var now = Date.now();
    var out = [];
    channels.forEach(function (ch) {
      var best = null;
      (ch.videos || []).forEach(function (v) {
        if (!v || !v.title || !v.url) return;
        if (normName(v.title).indexOf(key) < 0) return;
        var ts = Date.parse(v.published || '');
        if (!isFinite(ts)) ts = 0;
        if (ts && (now - ts) > FEED_MAX_AGE_DAYS * 86400000) return;
        if (!best || ts > best.ts) best = { v: v, ts: ts };
      });
      if (!best) return;
      out.push({
        name: shortChannel(ch.name || ch.channelTitle),
        channel: ch.name || ch.channelTitle || '',
        url: best.v.url,
        title: best.v.title,
        date: best.ts ? mdd(new Date(best.ts).toISOString()) : ''
      });
    });
    return out;
  }

  /* 유튜브 요약 — 공모주한잔 / 공모주투자의법칙(공주)
   * opts.listing: 상장 카드에서는 종목 단위로 매칭되는 feeds 영상만 쌓습니다
   * (ipo.gongmorin 의 판단은 청약 종목 기준이라 상장 카드에 붙이지 않습니다). */
  function ytBlock(ipo, name, opts) {
    var hanjan = ipo.hanjan || {};
    var gm = ipo.gongmorin || {};
    var hit = hanjanItem(ipo, name);
    var hits = feedHits(name);
    var used = {};
    var out = '';
    var rows = 0;
    var hanjanName = shortChannel(hanjan.channel) || '공모주한잔';
    var gmName = shortChannel(gm.name) || '공주';

    /* 큐레이션 판단이 있는 종목만 '영상 없음' 대신 판단 배지를 보입니다.
       영상이 하나도 없으면 맨 아래에서 한 줄로 조용히 적습니다. */
    if (hit) {
      var vObj = hit.video || hanjan.video || {};
      var vUrl = vObj.url || '';
      var vs = '';
      if (has(hit.equal)) vs += '<span class="v ' + tone(hit.equal) + '">균등 ' + esc(hit.equal) + '</span>';
      if (has(hit.proportional)) vs += '<span class="v ' + tone(hit.proportional) + '">비례 ' + esc(hit.proportional) + '</span>';
      out += '<div class="yt-row">' +
          '<span class="yt-name">' + esc(hanjanName) + '</span>' +
          vs +
          (vUrl ? '<a class="yt-link" href="' + esc(vUrl) + '" target="_blank" rel="noopener"' +
            (vObj && vObj.title ? ' title="' + esc(vObj.title) + '"' : '') + '>' +
            '영상<i aria-hidden="true">›</i></a>' : '') +
        '</div>' +
        (has(hanjan.note) ? '<p class="yt-note">' + esc(hanjan.note) + '</p>' : '');
      used[hanjanName] = 1;
      rows++;
    }

    if (!(opts && opts.listing) && (has(gm.verdict) || has(gm.note) || (gm.video && gm.video.url))) {
      var gUrl = (gm.video && gm.video.url) || '';
      out += '<div class="yt-row">' +
          '<span class="yt-name">' + esc(gmName) + '</span>' +
          (has(gm.verdict) ? '<span class="v ' + tone(gm.verdict) + '">' + esc(gm.verdict) + '</span>' : '') +
          (has(gm.score) ? '<span class="score ' + scoreTone(gm.score) + '">' + esc(gm.score) + '</span>' : '') +
          (gUrl ? '<a class="yt-link" href="' + esc(gUrl) + '" target="_blank" rel="noopener">영상<i aria-hidden="true">›</i></a>' : '') +
        '</div>' +
        (has(gm.note) ? '<p class="yt-note">' + esc(gm.note) + '</p>' : '');
      used[gmName] = 1;
      rows++;
    }

    /* 큐레이션이 비어 있는 채널은 feeds.json 최신 영상으로 채웁니다 */
    hits.forEach(function (h) {
      if (used[h.name]) return;
      used[h.name] = 1;
      var line = videoLine(h.title);
      var tn = videoTone(h.title);
      out += '<div class="yt-row">' +
          '<span class="yt-name">' + esc(h.name) + '</span>' +
          (tn ? '<span class="v ' + tn.c + '" title="영상 제목에서 읽은 톤">' + tn.t + '</span>' : '') +
          (h.date ? '<span class="yt-date">' + esc(h.date) + '</span>' : '') +
          '<a class="yt-link" href="' + esc(h.url) + '" target="_blank" rel="noopener" title="' + esc(h.title) + '">' +
            '영상<i aria-hidden="true">›</i></a>' +
        '</div>' +
        (line ? '<p class="yt-note">“' + esc(line) + '”</p>' : '');
      rows++;
    });

    if (gm.live && gm.live.on && (gm.live.url || gm.channelUrl)) {
      out += '<a class="live" href="' + esc(gm.live.url || gm.channelUrl) + '" target="_blank" rel="noopener">' +
          '<span class="dot" aria-hidden="true"></span>' +
          '<span>' + esc(gm.live.label || '실시간 경쟁률 보기') + '</span>' +
          '<em>' + esc(gmName) + '</em>' +
        '</a>';
    }

    if (rows) return out ? '<div class="yt">' + out + '</div>' : '';

    /* 어느 채널에도 관련 영상이 없을 때 — 한 줄로 조용히 */
    return '<div class="yt"><div class="yt-row"><span class="yt-none">' +
        esc(hanjanName + '·' + gmName) + ' 관련 영상 없음</span></div></div>';
  }

  /* '오늘 신규 상장 없음 — 다음은 11/20(금) 하나에어로다이내믹스' → '11/20(금) 하나에어로다이내믹스' */
  function listingHint(body) {
    var s = String(body || '').trim();
    s = s.replace(/^오늘\s*신규?\s*상장\s*(이\s*)?없(음|습니다)?\s*[—–\-:·]?\s*/, '');
    s = s.replace(/^다음은\s*/, '');
    return s.trim();
  }

  /* 다음 청약(D-day) · 다음 상장 — 히어로 하단 띠
   * opts.skipSub: 바로 위 청약 카드가 이미 '다음 청약'을 보여 준 경우 상장 카드에서는 생략 */
  function nextBand(ipo, today, opts) {
    var rows = '';
    var n = (opts && opts.skipSub) ? null : ipo.next;
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

  /* 청약 기간 중 오늘 위치 — 1일차 / 2일차 · 마감 / 오늘 마감
   *   · 하루짜리 청약(s === e)      : '오늘 마감'
   *   · 마지막 날(today === e)      : '(총일수)일차 · 마감'
   *   · 기간 중 나머지 날           : '(경과일수+1)일차' (진행 중)
   * 기간 밖이면 null — 배지에 날짜 상태를 붙이지 않습니다. */
  function periodDay(start, end, today) {
    if (!start || !today) return null;
    var e = end || start;
    if (today < start || today > e) return null;
    if (start.getTime() === e.getTime()) return { text: '오늘 마감', cls: 'is-close' };
    var day = Math.round((today - start) / 86400000) + 1;
    if (today.getTime() === e.getTime()) return { text: day + '일차 · 마감', cls: 'is-close' };
    return { text: day + '일차', cls: 'is-day' };
  }

  /* 오늘 청약 카드 상단 배지 — data.json 의 dayBadge('청약 2일차 · 마감')를 먼저 쓰고,
   * 없으면 청약 기간(period · closeDate)으로 오늘 위치를 계산합니다. */
  function heroDay(s, today) {
    var raw = has(s.dayBadge) ? String(s.dayBadge).replace(/^청약\s*/, '').trim() : '';
    if (raw) return { text: raw, cls: /마감/.test(raw) ? 'is-close' : 'is-day' };
    return periodDay(periodStart(s.period, today), parseDay(s.closeDate), today);
  }

  /* 오늘 청약 카드 — 1분 요약의 본문 */
  function heroCard(s, ipo, today) {
    var badge = String(s.badge || '').replace(/^오늘\s*청약\s*/, '');
    var day = heroDay(s, today);
    var priceNum = String(s.price || '').replace(/^확정\s*/, '');
    var listingToday = !!(ipo.listing && ipo.listing.hasListing);
    /* 날짜 상태(1일차 / 2일차 · 마감)가 있으면 '오늘 청약' 배지에 붙여 한눈에 보이게 하고,
       마감일은 배지 전체를 빨간 계열로 바꿉니다(is-close). 없으면 예전처럼 s.badge 로 폴백. */
    var flagText = '오늘 청약' + (day ? ' ' + day.text : (badge ? ' ' + badge : ''));
    var flags = '<span class="flag' + (day ? ' ' + day.cls : '') + '">' + esc(flagText) + '</span>' +
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
        brokerAppLinks(s.brokers) +
        ytBlock(ipo, s.name) +
        nextBand(ipo, today) +
      '</article>';
  }

  /* 장 시작 전(07:30~09:00) 상장 예정 — 시초가·종가·직전 체결가가 모두 아직 없다.
   * 이때는 큰 가격 자리에 '09:00 상장 예정'을 두고, 공모가 기준 가격제한폭을 함께 적습니다. */
  function isPreMarket(l) {
    return !has(l.openPrice) && !has(l.closePrice) && !has(l.earlyPrice);
  }

  /* 가격제한폭 — priceBand 가 있으면 그대로, 없으면 공모가×0.6 ~ ×4 로 계산.
   * 상장일 07:30 수집분은 아직 시초가 전이라 priceBand 도 비어 있어 공모가에서 만듭니다
   * (공모가가 범위·희망가처럼 한 값이 아니면 계산하지 않습니다). */
  function bandText(l) {
    var band = has(l.priceBand) ? String(l.priceBand).trim() : '';
    if (band && !shareUnknown(band)) return band;
    var price = String(l.ipoPrice == null ? '' : l.ipoPrice);
    if (!price || /[~∼]|희망/.test(price)) return '';
    var n = parseInt(price.replace(/[^0-9]/g, ''), 10);
    if (!(n > 0)) return '';
    return Math.floor(n * 0.6).toLocaleString('ko-KR') + '원 ~ '
      + (n * 4).toLocaleString('ko-KR') + '원 (60~400%)';
  }

  /* 오늘 상장 카드 — 청약이 없는 날의 1레벨 (하단 띠는 청약 카드와 동일하게 다음 청약·다음 상장) */
  function listingHero(l, ipo, today) {
    var badge = String(l.badge || '').replace(/^오늘\s*상장\s*/, '');
    var pts = (l.points && l.points.length)
      ? '<ul class="pts">' + l.points.map(function (p) { return '<li>' + esc(p) + '</li>'; }).join('') + '</ul>'
      : '';
    var specPairs = [];
    if (has(l.ipoPrice)) specPairs.push(['공모가', l.ipoPrice, true]);
    /* 큰 가격이 시초가면 시초를 또 적지 않는다(종가·직전가면 시초를 남긴다) */
    var lastIsOpen = !has(l.closePrice) && !has(l.earlyPrice) && has(l.openPrice);
    if (has(l.openPrice) && !lastIsOpen) specPairs.push(['시초', l.openPrice, false]);
    if (has(l.brokers)) specPairs.push(['주관', l.brokers, false]);
    var meta = specBits(specPairs);
    /* 큰 가격은 종가(장 마감 뒤) — 없으면 직전 체결가(earlyPrice), 시초가만 있으면 시초가(openPrice).
       장 시작 전에는 셋 다 없으므로 빈 가격 대신 상장 시각·가격제한폭을 보여 줍니다. */
    var lastPrice = has(l.closePrice) ? l.closePrice : (has(l.earlyPrice) ? l.earlyPrice : (l.openPrice || ''));
    var lastChange = has(l.closePrice) ? (l.closeChange || '')
      : (has(l.earlyPrice) ? (l.earlyChange || '') : (l.openChange || ''));
    var band = bandText(l);
    var priceHtml = has(lastPrice)
      ? '<div class="hprice"><b>' + esc(lastPrice) + '</b>' +
          (lastChange ? '<span class="chg ' + dirOf(lastChange) + '">' + esc(lastChange) + '</span>' : '') +
        '</div>'
      : '<div class="hprice is-pre"><b>09:00 상장 예정</b>' +
          (band ? '<span>가격제한폭 ' + esc(band) + '</span>' : '') +
        '</div>';
    return '<article class="hero is-list">' +
        '<div class="flags"><span class="flag is-list">오늘 상장</span>' +
          (badge ? '<span class="flag is-soft">' + esc(badge) + '</span>' : '') +
        '</div>' +
        '<div class="hname">' + esc(l.name) +
          (has(l.code) ? '<span class="hmarket">' + esc(l.code) + '</span>' : '') +
          (has(l.market) ? '<span class="hmarket">' + esc(l.market) + '</span>' : '') +
        '</div>' +
        priceHtml +
        meta +
        pts +
        brokerAppLinks(l.brokers) +
        ytBlock(ipo, l.name, { listing: true }) +
        nextBand(ipo, today, { skipSub: ((ipo.subscribe || []).length > 0) }) +
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

  /* ── 주말 모드 · 다음 주 청약 미리보기 ────────
   * 토·일에는 시장이 쉬므로 '오늘 요약'의 첫 카드를 다음 주 청약 미리보기로 바꿉니다.
   *   · 대상 : ipo.upcoming.subscribe 중 start 가 다음 주(월~일)인 종목
   *   · 금액 : 종목별 균등 최소증거금(depositOf — 공모가×최소청약주수(신고서 확인, 없으면 10주 추정)×증거금률 50%/스팩 100%)을
   *            다음 주 안에서 날짜별로 더해 가장 많이 묶이는 날(피크)을 보여 줍니다
   *            (start ≤ d < 환불일 — 환불일 당일 돈이 돌아옴)
   *   · 직전 영업일(수집일)의 상장·철회는 히어로 아래 보조 카드로 라벨을 낮춰 둡니다.
   */
  function nextMonday(d) {
    return addDays(d, d.getDay() === 6 ? 2 : 1);
  }

  function weekPreview(ipo, today) {
    var mon = nextMonday(today);
    var end = addDays(mon, 7);
    var items = (((ipo || {}).upcoming || {}).subscribe || []).filter(function (it) {
      var s = parseDay(it.start);
      return s && s >= mon && s < end;
    }).sort(function (a, b) {
      return String(a.start || '').localeCompare(String(b.start || ''));
    });

    var rows = [];
    items.forEach(function (it) {
      var dep = depositOf(it), until = lockUntil(it), start = parseDay(it.start);
      if (!dep || !until || !start) return;
      rows.push({ item: it, dep: dep, until: until, start: start });
    });

    var days = {};
    rows.forEach(function (r) {
      for (var d = r.start; d < r.until && d < end; d = addDays(d, 1)) {
        if (d < mon) continue;
        var cell = days[dayKey(d)] || (days[dayKey(d)] = { day: new Date(d), amount: 0, names: [] });
        cell.amount += r.dep.amount;
        if (cell.names.indexOf(r.item.name) < 0) cell.names.push(r.item.name);
      }
    });
    var peak = null;
    Object.keys(days).sort().forEach(function (k) {
      if (!peak || days[k].amount > peak.amount) peak = days[k];
    });

    return {
      mon: mon,
      end: end,
      items: items,
      rows: rows,
      peak: peak,
      total: rows.reduce(function (n, r) { return n + r.dep.amount; }, 0),
      label: shortDay(dayKey(mon)) + '~' + shortDay(dayKey(addDays(mon, 4)))
    };
  }

  /* 미리보기 종목 한 줄 — 기간 · 종목명 / 공모가 · 균등 증거금 / 주관 · 환불 */
  function weekItem(it) {
    var dep = depositOf(it);
    var mid = '';
    if (has(it.price)) mid += '<span class="wk-price">' + esc(it.price) + '</span>';
    if (dep) {
      mid += '<span class="wk-dep" title="' + esc(depositBasis(dep)) + '">' +
        depositText(dep, 'wk') + '</span>' + rateTag(dep, 'wk-rate');
    }
    var sub = [];
    if (has(it.brokers)) sub.push(esc(it.brokers));
    if (has(it.market)) sub.push(esc(it.market));
    if (has(it.refund)) sub.push('환불 ' + esc(shortDay(it.refund)));

    return '<li class="wk-i">' +
        '<div class="wk-top">' +
          (has(it.start) ? '<span class="wk-when">' + esc(dayRange(it)) + '</span>' : '') +
          '<b class="wk-name">' + esc(it.name) + '</b>' +
          (it.spac ? '<span class="wk-tag">스팩</span>' : '') +
        '</div>' +
        (mid ? '<div class="wk-mid">' + mid + '</div>' : '') +
        (sub.length ? '<div class="wk-sub">' + sub.join(' · ') + '</div>' : '') +
      '</li>';
  }

  function weekendHero(ipo, today) {
    var w = weekPreview(ipo, today);
    var n = w.items.length;
    var asOf = mdd(ipo.date || ipo.updatedAt || dayKey(today));

    var peak = '';
    if (w.peak) {
      peak = '<div class="wk-cash" id="wk-cash">' +
          '<span class="wk-k">다음 주 균등 최소증거금 피크</span>' +
          '<b class="wk-amt" id="wk-peak">약 ' + wonShort(w.peak.amount) + '</b>' +
          '<span class="wk-day" id="wk-peak-when">' + esc(shortDay(dayKey(w.peak.day))) +
            (w.peak.names.length > 1 ? ' · ' + w.peak.names.length + '종목 겹침' : '') +
            ' <em>' + esc(cashNames(w.peak.names)) + '</em></span>' +
        '</div>' +
        '<p class="wk-note">※ 최소 주수 확인 종목은 신고서 기준, 미확인은 10주 추정 · ' +
          '희망가 상단 · 일반 50%·스팩 100% · 스팩 포함</p>';
    }

    var body = n
      ? '<ul class="wk-list" id="wk-list">' + w.items.map(weekItem).join('') + '</ul>'
      : '<p class="hempty wk-empty" id="wk-empty">다음 주에는 청약 예정 종목이 없어요.' +
          ' 월요일 07:30 갱신 뒤 다시 확인하세요.</p>';

    return '<article class="hero is-weekend" id="hero-weekend">' +
        '<div class="flags">' +
          '<span class="flag is-week">주말 휴장</span>' +
          '<span class="flag is-next">다음 주 청약 미리보기</span>' +
        '</div>' +
        '<div class="hname sm">다음 주 청약 <b class="wk-cnt">' + n + '건</b></div>' +
        '<p class="hernote">' +
          (n ? esc(w.label) + ' · ' : '') +
          '직전 영업일(' + esc(asOf) + ') 수집</p>' +
        peak +
        body +
      '</article>';
  }

  /* 직전 영업일 상장 — 주말에 '오늘 상장'으로 읽히지 않게 라벨을 낮춘 보조 카드 */
  function prevDayCard(ipo) {
    var l = ipo.listing || {};
    var when = mdd(l.date || ipo.date);
    var flow = [];
    if (has(l.ipoPrice)) flow.push('공모가 ' + esc(l.ipoPrice));
    if (has(l.openPrice)) {
      flow.push('시초 ' + esc(l.openPrice) +
        (has(l.openChange) ? ' <span class="chg sm ' + dirOf(l.openChange) + '">' + esc(l.openChange) + '</span>' : ''));
    }
    var lastP = has(l.closePrice) ? l.closePrice : (l.earlyPrice || '');
    var lastC = has(l.closeChange) ? l.closeChange
      : (has(l.closePrice) ? '' : (l.earlyChange || ''));
    if (has(lastP)) {
      flow.push('종가 ' + esc(lastP) +
        (lastC ? ' <span class="chg sm ' + dirOf(lastC) + '">' + esc(lastC) + '</span>' : ''));
    }
    var facts = [];
    if (has(l.lockupRate)) facts.push('확약 ' + esc(l.lockupRate));
    if (has(l.floatSummary)) facts.push('유통 ' + esc(l.floatSummary));

    return '<div class="srows prevday" id="prev-day">' +
        '<div class="srow">' +
          '<div class="srow-top">' +
            '<span class="k is-list">직전 영업일(' + esc(when) + ') 상장</span>' +
            '<b>' + esc(l.name) + '</b>' +
          '</div>' +
          (flow.length ? '<div class="d">' + flow.join(' · ') + '</div>' : '') +
          (facts.length ? '<div class="d">' + facts.join(' · ') + '</div>' : '') +
        '</div>' +
      '</div>';
  }

  function ipoSection(ipo, today) {
    if (!ipo) return '<div class="empty">오늘 공모주 정보가 아직 없어요.</div>';
    if (isWeekend(today)) return weekendHero(ipo, today);

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

  /* 히어로 아래(공유 버튼 다음) — (주말) 직전 영업일 상장 · 철회 종목 · 출처 */
  function ipoFoot(ipo, today) {
    if (!ipo) return '';
    var html = '';
    if (isWeekend(today || todayDay()) && ipo.listing && ipo.listing.hasListing) {
      html += prevDayCard(ipo);
    }
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

  /* 청약 배지 — 예정이면 D-N, 기간 중이면 '1일차 / 2일차 · 마감', 지나면 '청약 종료'
   * 기간이 여러 날이면 마지막 날을 '· 마감'(is-close)으로 강조해 하루짜리 청약의 '오늘 마감'과
   * 같은 색으로 보이게 합니다. 진행 중인 날은 is-day(파랑)입니다. */
  function subBadge(item, today) {
    var s = parseDay(item.start);
    var e = parseDay(item.end) || s;
    if (!s) return null;
    if (e && today > e) return { text: '청약 종료', cls: 'off' };
    if (today < s) {
      var diff = Math.round((s - today) / 86400000);
      return { text: 'D-' + diff, cls: diff <= 4 ? 'hot' : '' };
    }
    return periodDay(s, e, today);
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

  /* ── 균등 최소증거금 요약 (전체 일정 최상단) ─────────────
   * ipo.upcoming.subscribe[] 종목마다
   *   증거금 = 공모가 × 최소청약주수 × 증거금률
   *     · 일반 공모주 50% · 스팩(기업인수목적회사) 100%
   * 을 계산합니다. 최소청약주수는 증권신고서에서 확인된 값(minShares)을 쓰고,
   * 확인되지 않은 종목만 10주로 추정해 금액 옆에 '10주 추정'을 붙입니다.
   * 공모가가 아직 희망가면 상단을 쓰고 금액 앞에 '약'을 붙입니다.
   *
   * 자금은 청약 시작일 ~ 환불일 전날까지 묶이는 것으로 봅니다
   * (start <= d < refund — 환불일 당일 돈이 돌아와 그날 청약에 쓸 수 있음).
   * 날짜별로 동시에 묶이는 금액을 더해 최댓값(피크)과 그날 겹치는 종목,
   * 선택 범위의 단순 합계를 함께 보여 줍니다.
   */
  var DEPOSIT_RATE = 0.5;        /* 일반 공모주(리츠 포함) — 청약증거금 50% */
  var DEPOSIT_RATE_SPAC = 1;     /* 스팩(기업인수목적회사) — 청약증거금 100% */
  var DEFAULT_MIN_SHARES = 10;
  var cashRange = '';      /* '' = 자동(이번 달 → 이번 달 일정이 없으면 전체) */
  var cashNoSpac = true;   /* 스팩 제외 기본 ON */

  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  function dayKey(d) { return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate()); }
  function nextDay(d) { return new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1); }
  function sameMonth(a, b) {
    return !!(a && b && a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth());
  }

  /* '확정 7,000원' · '희망 15,000~17,800원' · '희망 2,000원' → { value, estimated, range }
     범위면 보수적으로 상단(최댓값)을 씁니다. */
  function offerPrice(price) {
    var s = String(price == null ? '' : price).replace(/\s+/g, '');
    if (!s) return null;
    var found = s.match(/\d[\d,]*/g) || [];
    var values = found.map(function (x) { return Number(String(x).replace(/,/g, '')); })
      .filter(function (n) { return n > 0; });
    if (!values.length) return null;
    return {
      value: Math.max.apply(null, values),
      estimated: !/확정/.test(s) || /희망/.test(s),
      range: values.length > 1
    };
  }

  /* 스팩인가 — 종목명에 '스팩'·'기업인수목적' (data.json 의 spac 플래그는 리츠도 포함하므로
     증거금률은 이름으로만 판별합니다. 리츠는 증거금률이 종목마다 달라 기본 50%로 둡니다) */
  function isSpac(item) {
    if (!item) return false;
    return /스팩|기업인수목적/.test(String(item.name == null ? '' : item.name));
  }

  /* 종목별 청약증거금률 — 스팩은 공모가 전액(100%), 일반 공모주는 50% */
  function depositRate(item) {
    return isSpac(item) ? DEPOSIT_RATE_SPAC : DEPOSIT_RATE;
  }

  /* 종목 하나의 최소청약 증거금 — 값이 없으면 null(금액에서 제외) */
  function depositOf(item) {
    var p = offerPrice(item && item.price);
    if (!p) return null;
    var raw = Number(item.minShares);
    var shares = raw > 0 ? Math.round(raw) : DEFAULT_MIN_SHARES;
    var rate = depositRate(item);
    return {
      amount: Math.round(p.value * shares * rate),
      price: p.value,
      shares: shares,
      rate: rate,
      spac: rate === DEPOSIT_RATE_SPAC,
      sharesEstimated: !(raw > 0),
      priceEstimated: p.estimated,
      priceRange: p.range
    };
  }

  /* 금액의 근거 — 툴팁용. '희망가 상단 · 증권신고서 최소 50주 · 증거금 100%(스팩) 기준'
     주수를 못 찾은 종목은 '최소 청약 주수 미확인 · 10주 기준 추정'으로 적습니다. */
  function depositBasis(dep) {
    if (!dep) return '';
    var price = dep.priceRange ? '희망가 상단' : (dep.priceEstimated ? '희망가' : '확정가');
    var shares = dep.sharesEstimated
      ? '최소 청약 주수 미확인 · ' + dep.shares + '주 기준 추정'
      : '증권신고서 최소 ' + dep.shares + '주';
    return price + ' · ' + shares + ' · 증거금 ' + Math.round(dep.rate * 100) + '%' +
      (dep.spac ? '(스팩)' : '') + ' 기준';
  }

  /* 금액 앞 '약' — 공모가가 아직 희망가일 때만 (주수가 확인되면 금액의 근거는 확정) */
  function amountApprox(dep) {
    return dep && dep.priceEstimated ? '약 ' : '';
  }

  /* 최소 주수 표시 — 확인된 값은 '50주', 확인 전이면 '10주 추정' 칩.
     10주(확인)면 금액이 곧 기준이라 칩을 붙이지 않습니다. */
  function sharesTag(dep, prefix) {
    if (!dep) return '';
    if (dep.sharesEstimated) {
      return '<span class="' + prefix + '-est" title="최소 청약 주수 미확인 · 10주 기준 추정">' +
        '10주 추정</span>';
    }
    if (dep.shares === DEFAULT_MIN_SHARES) return '';
    return '<span class="' + prefix + '-shares" title="증권신고서 최소 ' + dep.shares +
      '주 · ' + dep.shares + '주부터 청약">' + dep.shares + '주</span>';
  }

  /* 금액 한 덩어리 — '균등 약 10만원 50주' / '균등 약 6.8만원 10주 추정' */
  function depositText(dep, prefix) {
    return '균등 ' + amountApprox(dep) + wonShort(dep.amount) + ' ' + sharesTag(dep, prefix);
  }

  /* 스팩 금액 옆에 붙는 증거금률 표시 */
  function rateTag(dep, cls) {
    if (!dep || !dep.spac) return '';
    return '<span class="' + cls + '" title="스팩은 청약증거금률이 100%입니다">증거금 100%</span>';
  }

  /* 자금이 묶이는 끝(다음 날 = 환불일, 그날 돈이 돌아옴). 환불일이 없으면 마감일까지. */
  function lockUntil(item) {
    var r = parseDay(item && item.refund);
    if (r) return r;
    var e = parseDay(item && item.end) || parseDay(item && item.start);
    return e ? nextDay(e) : null;
  }

  /* 89000 → 8.9만원 · 99000 → 9.9만원 · 8250 → 8,250원 */
  function wonShort(v) {
    if (!(v > 0)) return '0원';
    function tenths(n) {
      var s = (Math.round(n * 10) / 10).toFixed(1);
      return s.replace(/\.0$/, '');
    }
    if (v >= 100000000) return tenths(v / 100000000) + '억원';
    if (v >= 10000) return tenths(v / 10000) + '만원';
    return v.toLocaleString('ko-KR') + '원';
  }

  /* 일정 전체의 청약 월 범위 — 11~12월 / 11월 */
  function cashSpan(items) {
    var first = null, last = null;
    items.forEach(function (it) {
      var s = parseDay(it.start), u = lockUntil(it);
      if (s && (!first || s < first)) first = s;
      if (u && (!last || u > last)) last = u;
    });
    if (!first || !last) return '';
    var a = first.getMonth() + 1, b = last.getMonth() + 1;
    return (a === b ? String(a) : a + '~' + b) + '월';
  }

  /* 선택 범위(이번 달/전체) × 스팩 제외 → 계산 결과 */
  function cashPlan(ipo) {
    var up = (ipo && ipo.upcoming) || {};
    var today = todayDay();
    var all = (up.subscribe || []).filter(function (it) {
      var until = lockUntil(it);
      return until && until > today;   /* 이미 환불된 일정은 금액에서 뺀다 */
    });
    var month = all.filter(function (it) { return sameMonth(parseDay(it.start), today); });
    var range = cashRange || (month.length ? 'month' : 'all');
    var picked = range === 'month' ? month : all;
    var scoped = cashNoSpac ? picked.filter(function (it) { return !it.spac; }) : picked;

    var rows = [];
    scoped.forEach(function (it) {
      var dep = depositOf(it), until = lockUntil(it);
      if (!dep || !until) return;
      rows.push({ item: it, dep: dep, until: until });
    });
    /* 계산에서 뺀 건수는 스팩 제외가 아니라 '공모가를 못 읽은' 경우만 */
    var noPrice = picked.filter(function (it) { return !depositOf(it); }).length;

    /* 날짜별 동시 묶임 — start <= d < 환불일 */
    var days = {};
    rows.forEach(function (r) {
      var start = parseDay(r.item.start);
      if (!start) return;
      for (var d = start; d < r.until; d = nextDay(d)) {
        if (d < today) continue;
        var k = dayKey(d);
        var cell = days[k] || (days[k] = { day: new Date(d), amount: 0, names: [] });
        cell.amount += r.dep.amount;
        if (cell.names.indexOf(r.item.name) < 0) cell.names.push(r.item.name);
      }
    });
    var peak = null;
    Object.keys(days).sort().forEach(function (k) {
      var cell = days[k];
      if (!peak || cell.amount > peak.amount) peak = cell;
    });

    return {
      range: range,
      rows: rows,
      count: rows.length,
      missing: noPrice,   /* 공모가를 못 읽어 계산에서 뺀 건수 */
      spacOut: picked.length - scoped.length,   /* 스팩 제외로 뺀 건수 */
      total: rows.reduce(function (n, r) { return n + r.dep.amount; }, 0),
      peak: peak,
      monthLabel: '이번 달 (' + (today.getMonth() + 1) + '월)',
      allLabel: '전체 예정' + (cashSpan(all) ? ' (' + cashSpan(all) + ')' : '')
    };
  }

  function cashNames(names) {
    var head = names.slice(0, 3).join('·');
    return names.length > 3 ? head + ' 외 ' + (names.length - 3) : head;
  }

  function cashChip(range, label, on) {
    return '<button type="button" class="cash-chip' + (on ? ' is-on' : '') + '"' +
      ' data-cash-range="' + range + '" aria-pressed="' + (on ? 'true' : 'false') + '">' +
      esc(label) + '</button>';
  }

  /* 카드 한 장 — 피크 자금(크게) · 피크 날짜·겹치는 종목 · 단순 합계 · 기간/스팩 칩 · 안내 1줄 */
  function cashCard(ipo) {
    var plan = cashPlan(ipo);
    var peak = plan.peak;
    var when = peak
      ? esc(shortDay(dayKey(peak.day))) +
        (peak.names.length > 1
          ? ' · ' + peak.names.length + '종목 겹침 <span class="cash-names">' + esc(cashNames(peak.names)) + '</span>'
          : ' · <span class="cash-names">' + esc(cashNames(peak.names)) + '</span>')
      : '이 기간에 묶이는 청약이 없어요.';

    return '<div class="cash" id="cash-card">' +
        '<div class="cash-top">' +
          '<span class="cash-kick">균등 최소증거금</span>' +
          '<span class="cash-scope" id="cash-scope">' +
            esc(plan.range === 'month' ? plan.monthLabel : plan.allLabel) + '</span>' +
        '</div>' +
        '<div class="cash-peak">' +
          '<span class="cash-lab">동시에 묶이는 최대 자금</span>' +
          '<b class="cash-amt" id="cash-peak">' + (peak ? '약 ' + wonShort(peak.amount) : '0원') + '</b>' +
        '</div>' +
        '<p class="cash-day" id="cash-peak-when">' + when + '</p>' +
        '<div class="cash-sum">' +
          '<span>단순 합계 <b id="cash-total">' + wonShort(plan.total) + '</b></span>' +
          '<span>청약 <b id="cash-count">' + plan.count + '</b>건' +
            (plan.spacOut ? ' · 스팩 ' + plan.spacOut + '건 제외' : '') +
            (plan.missing ? ' · 공모가 미정 ' + plan.missing + '건 제외' : '') + '</span>' +
        '</div>' +
        '<div class="cash-chips" id="cash-chips" role="group" aria-label="필요 금액 범위와 스팩">' +
          cashChip('month', plan.monthLabel, plan.range === 'month') +
          cashChip('all', plan.allLabel, plan.range === 'all') +
          '<button type="button" class="cash-chip is-spac' + (cashNoSpac ? ' is-on' : '') + '"' +
            ' id="cash-spac" data-cash-spac="' + (cashNoSpac ? '1' : '0') + '"' +
            ' aria-pressed="' + (cashNoSpac ? 'true' : 'false') + '">' +
            (cashNoSpac ? '<span class="ck" aria-hidden="true">✓</span>' : '') +
            '스팩 제외</button>' +
        '</div>' +
        '<p class="cash-note" id="cash-note">※ 최소 주수 확인 종목은 증권신고서 기준, ' +
          '미확인 종목은 10주 기준 추정치입니다 · 희망가면 상단 · 일반 50%·스팩 100%.</p>' +
      '</div>';
  }

  /* 일정 카드 한 장 — D-day · 종목명 / 일정 · 공모가 · 균등 증거금 / 시장 · 주관 · 환불 */
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

    /* 종목별 예상 균등 증거금 — 왜 이 금액인지 '추정' 표시까지 */
    var depHtml = '';
    if (!isList) {
      var dep = depositOf(item);
      if (dep) {
        depHtml = '<span class="sc-dep" title="' + esc(depositBasis(dep)) + '">' +
          depositText(dep, 'sc') + '</span>' + rateTag(dep, 'sc-rate');
      }
    }

    return '<li class="sc' + (isList ? ' is-list' : '') + '">' +
        '<div class="sc-top">' +
          (dd ? '<span class="sc-dd' + (dd.cls ? ' ' + dd.cls : '') + '">' + esc(dd.text) + '</span>' : '') +
          '<span class="sc-name">' + esc(item.name) + '</span>' +
          (item.spac ? '<span class="sc-tag">스팩</span>' : '') +
        '</div>' +
        '<div class="sc-mid">' +
          '<span class="sc-when">' + esc(when) + '</span>' +
          (has(item.price) ? '<span class="sc-price">' + esc(item.price) + '</span>' : '') +
          depHtml +
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

    html += cashCard(ipo);   /* 이달/향후 균등 공모주 필요 금액 — 목록 바로 위 */

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

  /* ── 혜택 탭 · 증권사·금융 / 간편 이벤트·설문 ──────────
   *
   * data.json benefits[] 한 배열을 category 로 나눠 보여 줍니다.
   *   securities : 증권사 신규 개설·거래 혜택, 금융 이벤트
   *   simple     : 블로그·본인인증 없이 웹 폼으로 참여하는 경품·기프티콘·설문
   * 마감일(expiresAt)이 지난 항목은 자동으로 숨기고, 남은 건수를 칩과 머리말에 적습니다.
   * 카드 하나에 혜택명 · 핵심 금액/조건 · 대상 · 마감(D-day) · 유의사항·신청 방법 · 공식 링크.
   */
  var BF_CATS = [
    { id: 'all', label: '전체' },
    { id: 'securities', label: '증권사·금융' },
    { id: 'simple', label: '간편 이벤트·설문' }
  ];
  var BF_LABEL = { securities: '증권사·금융', simple: '간편 이벤트·설문' };
  var bfFilter = 'all';
  var bfLive = [];

  function benefitCat(ev) {
    return ev && ev.category === 'simple' ? 'simple' : 'securities';
  }

  function benefitCard(ev, today) {
    var always = !parseDay(ev.expiresAt);
    var dd = always ? { text: '상시', cls: 'is-always' } : dday(ev.expiresAt, today);
    var cat = benefitCat(ev);
    var terms = (ev.terms && ev.terms.length)
      ? '<ul>' + ev.terms.map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul>'
      : '';

    return '<article class="bf" data-id="' + esc(ev.id) + '" data-cat="' + cat + '"' +
        ' data-expires="' + esc(ev.expiresAt || 'always') + '">' +
        '<div class="bf-top">' +
          '<span class="bf-cat is-' + cat + '">' + esc(BF_LABEL[cat]) + '</span>' +
          '<span class="bf-dd ' + esc(dd.cls) + '">' + esc(dd.text) + '</span>' +
        '</div>' +
        (has(ev.provider) ? '<div class="bf-prov">' + esc(ev.provider) + '</div>' : '') +
        '<h3 class="bf-title">' + esc(ev.title) + '</h3>' +
        '<p class="bf-amt">' + esc(ev.benefit) + '</p>' +
        (has(ev.benefitNote) ? '<p class="bf-note">' + esc(ev.benefitNote) + '</p>' : '') +
        '<div class="bf-meta">' +
          (has(ev.target)
            ? '<div class="bf-row"><span class="bf-k">대상</span>' +
              '<span class="bf-v">' + esc(ev.target) + '</span></div>'
            : '') +
          '<div class="bf-row"><span class="bf-k">마감</span>' +
            '<span class="bf-v">' + esc(always ? '상시 진행' : (longDay(ev.expiresAt) || '미정')) +
            '</span></div>' +
          (has(ev.period)
            ? '<div class="bf-row"><span class="bf-k">기간</span>' +
              '<span class="bf-v is-per">' + esc(ev.period) + '</span></div>'
            : '') +
        '</div>' +
        ((terms || has(ev.howTo))
          ? '<details class="bf-more"><summary><span>유의사항·신청 방법</span>' +
              '<span class="bf-chev" aria-hidden="true"></span></summary>' +
              '<div class="bf-body">' +
                (has(ev.howTo) ? '<p class="bf-how"><span class="bf-k">신청</span>' +
                  esc(ev.howTo) + '</p>' : '') +
                terms +
              '</div></details>'
          : '') +
        (ev.link && ev.link.url
          ? '<a class="bf-link" href="' + esc(ev.link.url) + '" target="_blank" rel="noopener">' +
            esc(ev.link.label || '자세히 보기') + '<i aria-hidden="true">↗</i></a>'
          : '') +
      '</article>';
  }

  /* 칩(필터)과 카드 목록 — 칩을 누르면 같은 데이터로 즉시 다시 그립니다 */
  function benefitsBody(live, today) {
    var counts = { all: live.length, securities: 0, simple: 0 };
    live.forEach(function (ev) { counts[benefitCat(ev)] += 1; });

    $('bf-chips').innerHTML = BF_CATS.map(function (c) {
      var on = bfFilter === c.id;
      return '<button type="button" class="bf-chip' + (on ? ' is-on' : '') + '"' +
          ' data-bf="' + c.id + '" aria-pressed="' + (on ? 'true' : 'false') + '">' +
          esc(c.label) + '<b>' + counts[c.id] + '</b></button>';
    }).join('');

    var list = live.filter(function (ev) {
      return bfFilter === 'all' || benefitCat(ev) === bfFilter;
    });
    $('bf-list').innerHTML = list.length
      ? list.map(function (ev) { return benefitCard(ev, today); }).join('')
      : '<div class="empty">지금 챙길 혜택이 없어요.</div>';
  }

  var lastIpo = null;

  /* 범위·스팩 칩을 누를 때 전체 일정 본문만 다시 그립니다(탭·스크롤 유지) */
  function renderSchedule() {
    $('schedule-body').innerHTML = scheduleSection(lastIpo, todayDay());
  }

  /* ── 렌더 ─────────────────────────────── */
  function render(d) {
    var today = todayDay();
    var allEvents = d.benefits || [];
    var liveEvents = allEvents.filter(function (ev) { return !isExpired(ev, today); });
    var hiddenEvents = allEvents.length - liveEvents.length;
    var liveSec = liveEvents.filter(function (ev) { return benefitCat(ev) === 'securities'; }).length;
    var title = '마이돈 — 공모주 청약 일정·상장일';
    var weekend = isWeekend(today);
    document.title = title + (weekend || d.date ? ' · ' + shortDay(dayKey(today)) : '');

    /* 주말에는 날짜 줄에 주말임을 분명히 적고, 갱신 안내는 '직전 영업일 수집 · 월요일 갱신'으로 바꿉니다 */
    $('dateline').textContent = weekend
      ? korDay(today) + ' · 주말 휴장'
      : (d.dateLabel || shortDay(d.date));
    var schedNote = $('sched-note');
    if (schedNote) {
      schedNote.innerHTML = weekend
        ? '직전 영업일(<b>' + esc(mdd((d.ipo && d.ipo.date) || d.date)) + '</b>) 수집 · <b>월요일 07:30</b> 갱신'
        : '평일 <b>07:30</b> · <b>16:05</b> 자동 갱신';
    }
    $('updated').textContent = d.updatedLabel ? d.updatedLabel + ' 업데이트' : '';

    if (d.draft) {
      var badge = $('draft');
      badge.textContent = d.draftNote || '초안';
      badge.hidden = false;
    }

    $('ipo-body').innerHTML = ipoSection(d.ipo, today);
    $('ipo-foot').innerHTML = ipoFoot(d.ipo, today);
    lastIpo = d.ipo;
    $('schedule-body').innerHTML = scheduleSection(d.ipo, today);

    /* 2레벨: 혜택 탭으로 가는 한 줄 배너 — 증권사·금융 혜택 건수만 적습니다 */
    $('ben-count').textContent = liveSec;
    var note = [];
    if (d.benefitsAsOf) note.push(shortDay(d.benefitsAsOf) + ' 확인 기준이에요.');
    note.push('가입·응모 전 공식 페이지에서 혜택·마감일을 확인하세요.');
    if (hiddenEvents) note.push('기간이 끝난 혜택 ' + hiddenEvents + '건은 자동으로 숨겼어요.');
    $('bf-note').textContent = note.join(' ');
    bfLive = liveEvents;
    benefitsBody(liveEvents, today);

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
    $('share').hidden = false;
    $('support').hidden = false;
    $('foot').hidden = false;
    setTab(tabFromUrl(), { silent: true });
  }

  /* ── 탭 (오늘 요약 · 전체 일정 · 혜택) ──────── */
  var TABS = ['today', 'schedule', 'benefits'];

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
      /* 탭을 바꾸며 새로고침해도 ?date(검증용 날짜 고정)는 유지합니다 */
      var q = [];
      var fixed = urlParam('date');
      if (fixed) q.push('date=' + encodeURIComponent(fixed));
      if (name !== 'today') q.push('tab=' + name);
      var url = location.pathname + (q.length ? '?' + q.join('&') : '');
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

  /* 혜택 탭 필터 칩 — 누르면 같은 데이터로 즉시 다시 그립니다 */
  document.addEventListener('click', function (e) {
    var chip = e.target.closest ? e.target.closest('[data-bf]') : null;
    if (!chip) return;
    var id = chip.getAttribute('data-bf');
    if (!BF_CATS.some(function (c) { return c.id === id; })) return;
    e.preventDefault();
    if (bfFilter === id) return;
    bfFilter = id;
    benefitsBody(bfLive, todayDay());
  });

  /* 전체 일정 · 필요 금액 범위(이번 달/전체) · 스팩 제외 칩 — 즉시 재계산 */
  document.addEventListener('click', function (e) {
    var chip = e.target.closest ? e.target.closest('[data-cash-range], [data-cash-spac]') : null;
    if (!chip) return;
    e.preventDefault();
    var range = chip.getAttribute('data-cash-range');
    if (range === 'month' || range === 'all') {
      if (cashRange === range) return;
      cashRange = range;
    } else {
      cashNoSpac = !cashNoSpac;
    }
    renderSchedule();
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

  /* ── 정보 공유(복사 폴백) ──────────────────
   * 카톡 단톡방에 그대로 붙여넣는 두 가지 텍스트 — 청약 정보 / 상장 정보.
   * .share 안의 버튼은 항상 2개 고정이고, 그날 없는 쪽은 이유를 적은 :disabled 로 남습니다.
   *
   * 1) 청약 정보 — ipo.subscribe[](오늘 청약 종목) 순서대로, 오늘 청약이 없으면 ipo.next.
   *
   *   📌 {종목명} ({M/DD} 마감[ 예정])
   *
   *   * 공모가: …  * 확약률: …  * 시총: …  * 주관사: …  * 최소청약: …  * 수수료: …
   *   * 균등물량: …  * 예상 비례경쟁률: …  * 비례 10주: …  * 풀청약: …
   *   * 환불일: …  * 상장일: …
   *
   *   ✅ 청약 의견: …
   *
   * 2) 상장 정보 — ipo.listing(오늘 상장 종목)이 있을 때만.
   *
   *   📈 {종목명} ({M/DD} 상장)
   *
   *   * 공모가: …  * 시초가: … (…)  * 종가: … (…)  * 최종 확약률: …
   *   * 상장일 유통물량: …  * 가격제한폭: …  * 한줄 요약: …
   *
   * 값이 없거나 '미정'·'확인 필요'인 항목은 줄을 만들지 않습니다.
   * navigator.share 가 있으면 공유 시트로 { title, text, url } 을 넘기고 (text 에는 URL 없음),
   * 미지원(데스크톱 등)이거나 AbortError 이외의 오류면 클립보드 복사본(마지막 줄에 URL)으로
   * 폴백합니다.
   */
  var SITE_URL = 'https://ipo.mydon.kr';
  var SHARE_TITLE = '공모주 청약 정보';
  var LISTING_TITLE = '공모주 상장 정보';
  var subText = '';
  var subPayload = null;
  var listText = '';
  var listPayload = null;

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

  /* 상장 정보 공유문 순서·라벨 — 세 번째 값은 괄호에 붙일 등락 필드 */
  var LISTING_FIELDS = [
    ['ipoPrice', '공모가'],
    ['openPrice', '시초가', 'openChange'],
    ['closePrice', '종가', 'closeChange'],
    ['lockupRate', '최종 확약률'],
    ['floatSummary', '상장일 유통물량'],
    ['priceBand', '가격제한폭'],
    ['shareSummary', '한줄 요약']
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

  /* 필드 값 — ipoPrice 는 price, refundDate 는 refund, closePrice·closeChange 는
     earlyPrice·earlyChange 로 대신할 수 있습니다 */
  function shareValue(item, key) {
    var raw = has(item[key]) ? item[key] : '';
    if (!has(raw) && key === 'ipoPrice') raw = item.price || '';
    if (!has(raw) && key === 'refundDate') raw = item.refund || '';
    if (!has(raw) && key === 'closePrice') raw = item.earlyPrice || '';
    if (!has(raw) && key === 'closeChange') raw = item.earlyChange || '';
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

  /* 등락 필드가 있으면 '값 (등락)' 으로 */
  function listingValue(l, key, chgKey) {
    var v = shareValue(l, key);
    if (!v || !chgKey) return v;
    var c = shareValue(l, chgKey);
    return c ? v + ' (' + c + ')' : v;
  }

  /* 상장 정보 공유문 — ipo.listing 이 오늘 상장이 아니면 빈 문자열 */
  function listingBody(d) {
    var ipo = (d && d.ipo) || {};
    var l = ipo.listing;
    if (!l || !l.hasListing || !has(l.name)) return '';
    var when = mdd(l.date || l.listingDate || ipo.date || '');
    var head = '📈 ' + String(l.name).trim() + (when ? ' (' + when + ' 상장)' : '');

    var bullets = [];
    /* 장 시작 전 — 시초·종가가 없어 아래에 가격 줄이 없으므로 상장 시각을 먼저 적습니다 */
    if (isPreMarket(l)) bullets.push('* 상장 시각: 09:00 (장 시작 전)');
    LISTING_FIELDS.forEach(function (f) {
      var v = f[0] === 'priceBand'
        ? (shareValue(l, f[0]) || (isPreMarket(l) ? bandText(l) : ''))
        : listingValue(l, f[0], f[2]);
      if (v) bullets.push('* ' + f[1] + ': ' + v);
    });
    return bullets.length ? head + '\n\n' + bullets.join('\n') : head;
  }

  /* 버튼 상태 — payload 가 없으면 이유 라벨을 단 비활성 버튼으로 */
  function shareReady(btn, payload, onLabel, offLabel) {
    if (!btn) return;
    var off = !payload;
    btn.disabled = off;
    btn.setAttribute('aria-disabled', off ? 'true' : 'false');
    btn.classList.toggle('is-off', off);
    var label = off ? offLabel : onLabel;
    if (btn.getAttribute('data-label') !== label) {
      btn.setAttribute('data-label', label);
      var el = btn.querySelector('.lbl');
      if (el) el.textContent = label;
    }
    /* 비활성이면 스크린리더에도 이유를 알려 줍니다 */
    var base = btn.getAttribute('data-aria');
    if (base == null) { base = btn.getAttribute('aria-label') || ''; btn.setAttribute('data-aria', base); }
    btn.setAttribute('aria-label', off ? label : base);
    btn.classList.remove('done');
  }

  function setShare(d) {
    var body = shareBody(d);
    subText = body ? body + '\n' + SITE_URL : '';
    subPayload = body ? { title: SHARE_TITLE, text: body, url: SITE_URL } : null;

    var lbody = listingBody(d);
    listText = lbody ? lbody + '\n' + SITE_URL : '';
    listPayload = lbody ? { title: LISTING_TITLE, text: lbody, url: SITE_URL } : null;

    shareReady($('share-sub'), subPayload, '청약 정보 공유', '오늘 청약 없음');
    shareReady($('share-listing'), listPayload, '상장 정보 공유', '오늘 상장 없음');
  }

  /* 버튼 라벨을 잠깐 바꿔 복사 피드백 */
  /* 버튼 라벨을 잠간 바꿔 복사 피드백 (원래 라벨 = data-label) */
  function flashLabel(btn, label) {
    var el = btn && btn.querySelector('.lbl');
    if (!el) return;
    el.textContent = label;
    btn.classList.add('done');
    clearTimeout(btn._labelTimer);
    btn._labelTimer = setTimeout(function () {
      el.textContent = btn.getAttribute('data-label') || label;
      btn.classList.remove('done');
    }, 1800);
  }

  /* 공유 시트를 못 쓰는 환경·공유 오류 → 같은 버튼으로 그 정보 복사(URL 포함) 폴백 */
  function shareFallback(btn, text, what, msg) {
    copy(text).then(function (ok) {
      if (!ok) { toast('복사가 안 됐어요. 길게 눌러 복사해 주세요'); return; }
      toast(msg || '공유 기능이 없는 환경이라 ' + what + '를 복사했어요', 'ok');
      flashLabel(btn, '복사됐어요');
    });
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest ? e.target.closest('#share .share-btn') : null;
    if (!btn || btn.disabled) return;

    /* 버튼 2개(청약·상장) — 공유 시트 우선, 없거나 실패하면 같은 버튼이 복사로 폴백 */
    var isList = btn.getAttribute('data-share') === 'listing';
    var payload = isList ? listPayload : subPayload;
    var text = isList ? listText : subText;
    var what = isList ? '상장 정보' : '청약 정보';
    if (!payload || !text) return;

    if (!navigator.share) { shareFallback(btn, text, what); return; }
    var p;
    try {
      p = navigator.share(payload);
    } catch (err) {
      shareFallback(btn, text, what);
      return;
    }
    if (p && p.then) {
      p.then(function () { /* 공유 시트로 넘겼어요 */ }, function (err) {
        if (err && err.name === 'AbortError') return;  /* 사용자가 닫음 — 조용히 */
        shareFallback(btn, text, what, '공유가 안 돼서 ' + what + '를 복사했어요');
      });
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

  /* ── 블로그 배너 퍼가기 ─────────────────────
   * banner.png 는 scripts/generate_banner.py 가 data.json 으로 매일 다시 만듭니다.
   * 여기서는 미리보기 그림과 붙여넣을 코드·주소만 다룹니다.
   *   · HTML 코드 : 티스토리·워드프레스·웹사이트 HTML 모드
   *   · 이미지 URL : 네이버 블로그(URL 붙여넣기·저장 후 사진 첨부)
   * 접힌 채로 두고, 누를 때만 미리보기를 펼칩니다(첫 화면 무게를 키우지 않음).
   */
  var BANNER_URL = SITE_URL + '/banner.png';
  var BANNER_HTML = '<a href="' + SITE_URL + '" target="_blank" rel="noopener">' +
    '<img src="' + BANNER_URL + '" alt="마이돈 — 오늘의 공모주 1분 요약" ' +
    'width="800" height="280" style="max-width:100%;height:auto"></a>';

  function initBanner() {
    var toggle = $('be-toggle'), body = $('be-body'), code = $('be-code');
    if (!toggle || !body) return;
    if (code) code.textContent = BANNER_HTML;
    toggle.addEventListener('click', function () {
      var open = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', open ? 'false' : 'true');
      body.hidden = open;
    });
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest ? e.target.closest('[data-be-copy]') : null;
    if (!btn) return;
    var isUrl = btn.getAttribute('data-be-copy') === 'url';
    copy(isUrl ? BANNER_URL : BANNER_HTML).then(function (ok) {
      if (!ok) { toast('복사가 안 됐어요. 코드를 길게 눌러 복사해 주세요'); return; }
      toast(isUrl ? '배너 이미지 주소를 복사했어요' : 'HTML 코드를 복사했어요', 'ok');
      var label = btn.getAttribute('data-label') || btn.textContent;
      btn.textContent = '복사됐어요';
      btn.classList.add('done');
      clearTimeout(btn._copyTimer);
      btn._copyTimer = setTimeout(function () {
        btn.textContent = label;
        btn.classList.remove('done');
      }, 1800);
    });
  });

  /* ── 홈 화면에 앱으로 추가 (PWA) ───────────────
   * 표시 조건
   *   · 이미 홈 화면(standalone)에서 열었으면 설치할 것이 없으니 숨긴다.
   *   · ×로 닫으면 localStorage('mydon-install-hide')에 남겨 다시 띄우지 않는다.
   *   · Android·데스크톱 크롬: beforeinstallprompt 가 올 때만 보이고, 누르면 네이티브 설치 창.
   *   · iOS(Safari): 설치 API 가 없으므로 버튼을 누르면 아래에 공유 → '홈 화면에 추가' 안내를 편다.
   *   · 그 밖(설치 불가 환경)은 조용히 숨긴 채로 둔다.
   */
  var INSTALL_HIDE_KEY = 'mydon-install-hide';
  var deferredInstall = null;

  function isStandalone() {
    try {
      if (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) return true;
    } catch (e) { /* noop */ }
    return window.navigator.standalone === true;
  }

  /* 아이패드(iPadOS 13+)는 UA 가 Macintosh 로 오므로 터치 지원까지 함께 본다 */
  function isIOS() {
    var ua = navigator.userAgent || '';
    if (/iPhone|iPad|iPod/.test(ua)) return true;
    return navigator.platform === 'MacIntel' && (navigator.maxTouchPoints || 0) > 1;
  }

  /* 카톡·인스타·네이버 같은 인앱 브라우저는 '홈 화면에 추가'가 없으므로 iOS 에서는 안내를 꺼내지 않는다 */
  function isInAppBrowser() {
    return /KAKAOTALK|Instagram|FBAN|FB_IAB|FBAV|NAVER\(inapp|Line\/|DaumApps/i.test(navigator.userAgent || '');
  }

  function installDismissed() {
    try { return localStorage.getItem(INSTALL_HIDE_KEY) === '1'; } catch (e) { return false; }
  }

  function rememberInstallDismissed() {
    try { localStorage.setItem(INSTALL_HIDE_KEY, '1'); } catch (e) { /* noop */ }
  }

  function initInstall() {
    var card = $('install');
    if (!card) return;
    if (isStandalone() || installDismissed()) { card.hidden = true; return; }

    var btn = $('install-btn'), tip = $('install-tip'), x = $('install-x');

    function show() {
      card.hidden = false;
      if (tip) { tip.hidden = true; }
      if (btn) { btn.setAttribute('aria-expanded', 'false'); }
    }
    function hide() { card.hidden = true; }

    /* Android·데스크톱 크롬 — 설치 가능해지는 순간 브라우저가 알려 준다 */
    window.addEventListener('beforeinstallprompt', function (e) {
      e.preventDefault();
      deferredInstall = e;
      if (isStandalone() || installDismissed()) return;
      show();
    });

    /* 실제로 설치되면 더 보여 줄 이유가 없다 */
    window.addEventListener('appinstalled', function () {
      deferredInstall = null;
      rememberInstallDismissed();
      hide();
    });

    if (btn) {
      btn.addEventListener('click', function () {
        if (deferredInstall) {
          var p = deferredInstall;
          deferredInstall = null;
          try { p.prompt(); } catch (err) { hide(); return; }
          var choice = p.userChoice;
          if (!choice || !choice.then) { hide(); return; }
          choice.then(function (r) {
            if (r && r.outcome === 'accepted') {
              rememberInstallDismissed();
              hide();
              toast('홈 화면에 추가하고 있어요', 'ok');
            } else {
              /* 사용자가 설치 창을 닫음 — 한 번 더 재촉하지 않고 이번 화면에서만 숨긴다 */
              hide();
            }
          }, hide);
          return;
        }
        if (!tip) { hide(); return; }
        /* iOS — 설치 API 가 없으니 공유 버튼 → '홈 화면에 추가' 안내를 편다 */
        var open = btn.getAttribute('aria-expanded') === 'true';
        btn.setAttribute('aria-expanded', open ? 'false' : 'true');
        tip.hidden = open;
      });
    }

    if (x) {
      x.addEventListener('click', function () {
        rememberInstallDismissed();
        hide();
      });
    }

    /* iOS 는 beforeinstallprompt 가 없으므로 바로 안내를 꺼내 둔다 (Safari 일 때만) */
    if (isIOS() && !isInAppBrowser()) show();
  }

  /* 서비스 워커 등록 — Android 크롬 설치 조건. https(또는 localhost)에서만 동작한다. */
  function initServiceWorker() {
    if (!('serviceWorker' in navigator)) return;
    try {
      navigator.serviceWorker.register('/sw.js').catch(function () { /* 설치 배너는 SW 없이도 동작 */ });
    } catch (e) { /* noop */ }
  }

  /* ── 시작 ─────────────────────────────── */
  initTheme();
  initBanner();
  initInstall();
  initServiceWorker();

  /* data.json(사람이 쓰는 오늘 요약) + feeds.json(수집기가 모은 최신 유튜브 영상)
     — 영상 목록을 먼저 받아 두고 한 번에 그립니다. feeds 가 실패해도 화면은 그대로 뜸니다. */
  var stamp = '?t=' + Math.floor(Date.now() / 60000);
  var pData = fetch('data.json' + stamp, { cache: 'no-store' }).then(function (r) {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  });
  var pFeeds = fetch('feeds.json' + stamp)
    .then(function (r) { return r.ok ? r.json() : null; })
    .catch(function () { return null; });

  Promise.all([pData, pFeeds])
    .then(function (res) {
      FEEDS = res[1];
      render(res[0]);
    })
    .catch(fail);
})();
