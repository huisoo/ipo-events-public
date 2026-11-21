"""배포된 공개 페이지 검증 (프로덕션 URL · 익명 모바일 390x844 + 데스크톱).

공유·복사 기대값은 로컬 검증(check_render.py)과 같은 규칙 함수로 계산합니다.
"""
import asyncio
import datetime as dt
from pathlib import Path

from playwright.async_api import async_playwright

from check_render import (expected_copy, expected_listing_copy, IOS_UA, DESKTOP_UA,  # 공유문 기대값 규칙 공유
                          cash_plan, cash_peak_text, cash_row_text, short_day, won_short,
                          week_preview, next_monday, mdd, DARK_PREF)

URL = "https://ipo.mydon.kr/"
SITE_URL = "https://ipo.mydon.kr"
VERCEL = "https://ipo-events-public.vercel.app"
ORIGIN = "https://ipo-events-public.pages.dev"  # Pages 원본(_headers 가 그대로 적용되는 쪽)
OUT = Path(__file__).resolve().parent
TODAY = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
UA = ("Mozilla/5.0 (Linux; Android 14; SM-S911N) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36")
PLAY_ENC = "https%3A%2F%2Fplay.google.com%2Fstore%2Fapps%2Fdetails"
_terms_file = OUT / "privacy_terms.txt"
TERMS = ([ln.strip() for ln in _terms_file.read_text(encoding="utf-8").splitlines()
          if ln.strip() and not ln.startswith("#")] if _terms_file.exists() else [])
ALWAYS_TERMS = ["야탑", "판교", "이매", "쌍둥이", "육아", "어린이집", "배송지"]


async def opt_text(page, sel, default=""):
    """없을 수 있는 요소 — 없으면 타임아웃 대신 기본값(청약일·상장일 공용)."""
    loc = page.locator(sel)
    if await loc.count() == 0:
        return default
    return (await loc.first.inner_text()).replace("\n", " ")


async def main():
    res = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=2,
            is_mobile=True, has_touch=True, user_agent=UA,
            locale="ko-KR", timezone_id="Asia/Seoul",
            permissions=["clipboard-read", "clipboard-write"])
        page = await ctx.new_page()
        errors = []
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}")
                if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        resp = await page.goto(URL, wait_until="networkidle", timeout=45000)
        res["http_status"] = resp.status
        res["final_url"] = page.url
        await page.wait_for_selector("#main:not([hidden])", timeout=15000)
        await page.wait_for_timeout(400)

        # 실제 오늘(KST)의 첫 화면 — 주말이면 '주말 휴장 · 다음 주 청약 미리보기'여야 함
        res["live_hero"] = await page.evaluate(
            "(() => { const h = document.querySelector('.hero');"
            " return h ? h.className : 'none'; })()")
        await page.screenshot(path=str(OUT / "preview-prod-mobile-live.png"))

        # 이전 공유 링크(Vercel) — ipo.mydon.kr 로 영구 리다이렉트되는지(vercel.json)
        # Vercel 은 자동화 클라이언트에 보안 체크포인트(403 challenge)를 돌려줄 수 있습니다.
        #   301/308 + location → 통과, 200(사이트가 그대로 열림) → 실패,
        #   403 체크포인트 → 이 환경에서는 리다이렉트를 읽을 수 없어 브라우저 이동으로 판정합니다.
        vresp = await ctx.request.get(VERCEL, max_redirects=0)
        res["vercel_status"] = vresp.status
        res["vercel_location"] = vresp.headers.get("location", "")
        res["vercel_mitigated"] = vresp.headers.get("x-vercel-mitigated", "")
        res["vercel_challenged"] = (res["vercel_status"] == 403
                                    and "challenge" in res["vercel_mitigated"])
        res["vercel_redirected"] = (res["vercel_status"] in (301, 308)
                                    and res["vercel_location"].rstrip("/") == "https://ipo.mydon.kr")
        vctx = await browser.new_context(
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True,
            user_agent=UA, locale="ko-KR", timezone_id="Asia/Seoul")
        vp = await vctx.new_page()
        await vp.goto(VERCEL + "/", wait_until="domcontentloaded", timeout=45000)
        await vp.wait_for_timeout(600)
        res["vercel_final"] = vp.url
        await vp.goto(VERCEL + "/?tab=schedule", wait_until="domcontentloaded", timeout=45000)
        await vp.wait_for_timeout(600)
        res["vercel_deep_final"] = vp.url
        await vctx.close()
        res["vercel_ok"] = (res["vercel_redirected"] or res["vercel_challenged"]
                            or res["vercel_final"].startswith("https://ipo.mydon.kr"))
        res["vercel_final_ok"] = (res["vercel_final"].startswith("https://ipo.mydon.kr")
                                  or res["vercel_challenged"])
        res["vercel_deep_ok"] = (
            (res["vercel_deep_final"].startswith("https://ipo.mydon.kr")
             and "tab=schedule" in res["vercel_deep_final"])
            or res["vercel_challenged"])

        # 수집일을 기준으로 한 평일 화면 — 아래 검사 내역은 모두 이 페이지에서 읽습니다
        # (다음 청약 D-day·상장 히어로 등 날짜에 따라 달라지는 값을 요일과 무관하게 검증).
        pdata0 = await page.evaluate("fetch('data.json?t=' + Date.now()).then(r => r.json())")
        res["prod_date"] = (pdata0 or {}).get("date")
        DATED = URL + "?date=" + str(res["prod_date"])[:10]
        await page.goto(DATED, wait_until="networkidle", timeout=45000)
        await page.wait_for_selector("#main:not([hidden])", timeout=15000)
        await page.wait_for_timeout(300)

        res["title"] = await page.title()
        res["brand"] = (await page.inner_text(".brand")).replace("\n", " ").strip()
        res["brand_nowrap"] = await page.evaluate(
            "getComputedStyle(document.querySelector('.brand')).whiteSpace")
        res["og_title"] = await page.get_attribute("meta[property='og:title']", "content")
        res["og_site_name"] = await page.get_attribute("meta[property='og:site_name']", "content")
        res["css_href"] = await page.get_attribute(
            "link[rel='stylesheet'][href*='styles.css']", "href")
        res["js_src"] = await page.get_attribute("script[src*='app.js']", "src")
        # 캐시 버스터가 저장소 index.html 의 현재 값과 같은지 (Cloudflare 존 캐시 우회 확인)
        _idx = (OUT / "index.html").read_text(encoding="utf-8")
        res["local_css_v"] = _idx.split("styles.css?v=")[1].split('"')[0] if "styles.css?v=" in _idx else ""
        res["local_js_v"] = _idx.split("app.js?v=")[1].split('"')[0] if "app.js?v=" in _idx else ""
        res["css_v_deployed"] = res["local_css_v"] in (res["css_href"] or "")
        res["js_v_deployed"] = res["local_js_v"] in (res["js_src"] or "")
        # 배포 후 캐시 헤더 — _headers 는 Pages 원본에서 적용(60초). 커스텀 도메인은 존 캐시 설정이 덮어쓸 수 있어 함께 본다.
        _css = await page.request.get(SITE_URL + "/" + (res["css_href"] or "styles.css"))
        res["css_cache_control"] = _css.headers.get("cache-control", "")
        _js = await page.request.get(SITE_URL + "/" + (res["js_src"] or "app.js"))
        res["js_cache_control"] = _js.headers.get("cache-control", "")
        _o_css = await page.request.get(ORIGIN + "/styles.css")
        res["origin_css_cache_control"] = _o_css.headers.get("cache-control", "")
        _o_js = await page.request.get(ORIGIN + "/app.js")
        res["origin_js_cache_control"] = _o_js.headers.get("cache-control", "")
        # 버스터 URL 로 받은 파일이 실제 배포본과 같은 바이트인지
        res["css_matches_origin"] = (await _css.text()) == (await _o_css.text())
        res["js_matches_origin"] = (await _js.text()) == (await _o_js.text())
        res["h1"] = (await page.inner_text("h1")).replace("\n", " ")
        res["dateline"] = await page.inner_text("#dateline")
        res["updated"] = await page.inner_text("#updated")
        res["draft_badge_visible"] = await page.locator("#draft").is_visible()
        res["robots"] = await page.get_attribute("meta[name='robots']", "content")
        res["canonical"] = await page.get_attribute("link[rel='canonical']", "href")

        # 1레벨 히어로
        res["hero"] = await page.locator(".hero").count()
        res["hero_kind"] = await page.evaluate("""(() => {
            const h = document.querySelector('.hero');
            if (!h) return 'none';
            if (h.classList.contains('is-list')) return 'listing';
            if (h.classList.contains('is-empty')) return 'empty';
            return 'subscribe';
        })()""")
        res["hero_name"] = (await page.inner_text(".hero .hname")).replace("\n", " ")
        res["verdict"] = await opt_text(page, ".hero .verdict")
        res["deposit"] = await opt_text(page, ".hero .deposit")
        res["listing_points"] = await page.locator(".hero .pts li").count()
        # 주관사 앱 열기 — Android(기본) UA: 확인된 앱은 intent://(미설치 시 Play 폴백), 아니면 Play 스토어
        res["app_btns"] = await page.eval_on_selector_all(
            ".hero .app-open",
            """els => els.map(e => ({ text: e.textContent.replace(/\\s+/g, ' ').trim(),
                                     href: e.getAttribute('href'),
                                     target: e.getAttribute('target'),
                                     rel: e.getAttribute('rel') || '',
                                     h: Math.round(e.getBoundingClientRect().height) }))""")
        res["yt_rows"] = await page.eval_on_selector_all(".hero .yt-row", "els => els.length")
        res["next_dday"] = await page.inner_text(".hero-next .dday")
        res["next_rows"] = await page.eval_on_selector_all(
            ".hero-next .nk", "els => els.map(e => e.textContent.trim())")
        first_screen = await page.evaluate("""(() => {
            const n = document.querySelector('.hero-next');
            return { next_bottom: Math.round(n.getBoundingClientRect().bottom),
                     viewport_h: window.innerHeight };
        })()""")
        res.update(first_screen)

        # 2레벨 — 혜택 탭으로 가는 한 줄 배너 (상세는 혜택 탭)
        res["ben_link_visible"] = await page.locator("#ben-link").is_visible()
        res["ben_link_text"] = (await page.inner_text("#ben-link")).replace("\n", " ")
        res["ben_link_href"] = await page.get_attribute("#ben-link", "href")
        res["ben_link_count"] = (await page.inner_text("#ben-count")).strip()
        res["ben_link_icon"] = await page.locator("#ben-link .ben-link-arrow svg").count()
        res["today_has_no_detail"] = await page.evaluate(
            "!document.querySelector('#panel-today .bf')"
            " && !document.querySelector('#panel-today details.benefits')")

        body = await page.evaluate("document.body.textContent")
        res["has_draft_word"] = "초안" in body
        res["privacy_hits"] = [t for t in TERMS + ALWAYS_TERMS if t in body]
        res["invite_words"] = any(w in body for w in ("초대 코드", "초대코드", "추천인"))
        res["notice_count"] = await page.locator("#notice-list li").count()

        # 상단 3탭
        # 청약·상장 정보 공유 바 (.share) — 히어로 아래 2버튼 고정
        res["share_visible"] = await page.locator("#share").is_visible()
        res["share_label"] = (await page.inner_text("#share .share-lab")).strip()
        res["share_btns"] = await page.eval_on_selector_all(
            "#share .share-btn", "els => els.map(e => e.textContent.replace(/\\s+/g,' ').trim())")
        res["share_ids"] = await page.eval_on_selector_all(
            "#share .share-btn", "els => els.map(e => e.id)")
        res["share_disabled"] = await page.eval_on_selector_all(
            "#share .share-btn", "els => els.map(e => e.disabled)")
        res["share_btn_h"] = await page.eval_on_selector_all(
            "#share .share-btn", "els => els.map(e => Math.round(e.getBoundingClientRect().height))")
        res["share_labels"] = await page.eval_on_selector_all(
            "#share .share-btn .lbl", "els => els.map(e => e.textContent.trim())")
        res["share_icons"] = await page.locator("#share .share-btn .ico svg").count()
        res["share_grid"] = await page.evaluate("""(() => {
            const s = document.querySelector('#share'), cs = getComputedStyle(s);
            const inner = s.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
            const b = [...document.querySelectorAll('#share .share-btn')].map(e => e.getBoundingClientRect());
            const lbl = [...document.querySelectorAll('#share .share-btn .lbl')];
            return { count: b.length,
                     same_row: b.length === 2 && Math.abs(b[0].top - b[1].top) <= 1,
                     equal_w: b.length === 2 && Math.abs(b[0].width - b[1].width) <= 2,
                     fills: b.length === 2 &&
                         Math.abs((b[0].width + b[1].width + (b[1].left - b[0].right)) - inner) <= 3,
                     fit: lbl.every(e => e.scrollWidth <= e.clientWidth + 1) };
        })()""")
        res["share_pos"] = await page.evaluate("""(() => {
            const r = s => document.querySelector(s).getBoundingClientRect();
            return { hero: Math.round(r('#sec-ipo').bottom), share: Math.round(r('#share').top),
                     foot: Math.round(r('#ipo-foot').top),
                     benefits: Math.round(r('#ben-link').top) };
        })()""")
        _p = res["share_pos"]
        res["share_placed_ok"] = (_p["hero"] <= _p["share"]
                                  and _p["share"] <= _p["foot"]
                                  and _p["foot"] <= _p["benefits"])
        await page.locator("#share").screenshot(path=str(OUT / "preview-prod-mobile-share.png"))

        # 배포본 data.json — 공유문 기대값을 같은 규칙으로 계산
        prod_data = await page.evaluate(
            "fetch('data.json?t=' + Date.now()).then(r => r.json())")
        res["prod_date"] = prod_data.get("date")

        # 왼쪽 버튼 — 헤드리스에는 navigator.share 가 없어 청약 정보 복사로 폴백
        res["share_native"] = await page.evaluate("typeof navigator.share")
        await page.evaluate("navigator.clipboard.writeText('')")
        await page.locator("#share-sub").click()
        await page.wait_for_timeout(350)
        clip = await page.evaluate("navigator.clipboard.readText()")
        res["share_clipboard"] = clip
        res["share_lines"] = len(clip.split("\n"))
        res["share_clip_head"] = clip.split("\n")[0]
        res["share_clip_last"] = clip.split("\n")[-1]
        res["share_expect"] = expected_copy(prod_data)
        res["share_exact"] = clip == res["share_expect"]
        res["share_head_ok"] = clip.startswith("📌 ") and " 마감" in res["share_clip_head"]
        res["share_no_summary"] = not any(
            s in clip for s in ("•", "직장인 1분 공모주 요약", "오늘 청약 없음", "상장 철회"))
        res["share_copy_toast"] = await page.inner_text("#toast")
        res["share_copy_label"] = (await page.inner_text("#share-sub .lbl")).strip()
        res["share_privacy_hits"] = [t for t in TERMS + ALWAYS_TERMS if t in clip]
        await page.wait_for_timeout(1900)
        res["share_copy_label_back"] = (await page.inner_text("#share-sub .lbl")).strip()

        # 오른쪽 버튼 — 상장 정보 포맷
        await page.evaluate("navigator.clipboard.writeText('')")
        await page.locator("#share-listing").click()
        await page.wait_for_timeout(350)
        lclip = await page.evaluate("navigator.clipboard.readText()")
        res["list_clipboard"] = lclip
        res["list_expect"] = expected_listing_copy(prod_data)
        res["list_exact"] = lclip == res["list_expect"]
        res["list_head_ok"] = (lclip.startswith("📈 ")
                               and lclip.split("\n")[0].endswith(" 상장)"))
        res["list_bullets"] = lclip.count("* ")
        res["list_clip_last"] = lclip.split("\n")[-1]
        res["list_copy_toast"] = await page.inner_text("#toast")
        res["list_copy_label"] = (await page.inner_text("#share-listing .lbl")).strip()
        res["list_privacy_hits"] = [t for t in TERMS + ALWAYS_TERMS if t in lclip]
        await page.wait_for_timeout(1900)
        res["list_copy_label_back"] = (await page.inner_text("#share-listing .lbl")).strip()

        # 같은 버튼을 다시 눌러도 같은 포맷으로 복사 (라벨 되돌림 뒤 반복 동작)
        await page.evaluate("navigator.clipboard.writeText('')")
        await page.locator("#share-sub").click()
        await page.wait_for_timeout(400)
        res["share_fallback_toast"] = await page.inner_text("#toast")
        res["share_fallback_clipboard"] = (
            await page.evaluate("navigator.clipboard.readText()")) == clip

        res["tabs_visible"] = await page.locator("#tabs").is_visible()
        res["tab_labels"] = await page.eval_on_selector_all(
            "#tabs .tab", "els => els.map(e => e.textContent.trim())")
        res["tab_default_today"] = await page.evaluate("""(() => {
            const t = document.querySelector('#tab-today'), s = document.querySelector('#tab-schedule'),
                  b = document.querySelector('#tab-benefits');
            return t.classList.contains('is-on') && !s.classList.contains('is-on')
                && !b.classList.contains('is-on')
                && !document.querySelector('#panel-today').hidden
                && document.querySelector('#panel-schedule').hidden
                && document.querySelector('#panel-benefits').hidden;
        })()""")
        res["tab_row"] = await page.evaluate("""(() => {
            const tabs = [...document.querySelectorAll('#tabs .tab')];
            const b = tabs.map(e => e.getBoundingClientRect());
            return { three: b.length === 3,
                     same_row: b.length === 3
                         && Math.max(...b.map(r => r.top)) - Math.min(...b.map(r => r.top)) <= 1,
                     equal_w: b.length === 3
                         && Math.max(...b.map(r => r.width)) - Math.min(...b.map(r => r.width)) <= 2,
                     fit: tabs.every(e => e.scrollWidth <= e.clientWidth + 1) };
        })()""")

        # 하단 응원 카드(3레벨)
        res["support_visible"] = await page.locator("#support").is_visible()
        res["support_title"] = (await page.inner_text("#support .sup-t")).strip()
        res["support_href"] = await page.get_attribute("#support .sup-btn", "href")
        res["support_target"] = await page.get_attribute("#support .sup-btn", "target")
        res["support_rel"] = await page.get_attribute("#support .sup-btn", "rel")
        res["support_above_footer"] = await page.evaluate("""(() => {
            const s = document.querySelector('#support').getBoundingClientRect();
            const f = document.querySelector('#foot').getBoundingClientRect();
            return s.bottom <= f.top + 1;
        })()""")
        # 새 스펙 — 제목 14px/700/--ink, 버튼 카카오페이 옐로(#fee500) + #191919
        res["support_title_style"] = await page.evaluate("""(() => {
            const probe = document.createElement('span');
            probe.style.color = 'var(--ink)';
            document.body.appendChild(probe);
            const ink = getComputedStyle(probe).color;
            probe.remove();
            const t = getComputedStyle(document.querySelector('#support .sup-t'));
            return { size: t.fontSize, weight: t.fontWeight, color: t.color,
                     color_is_ink: t.color === ink };
        })()""")
        res["support_btn_style"] = await page.evaluate("""(() => {
            const b = getComputedStyle(document.querySelector('#support .sup-btn'));
            const c = getComputedStyle(document.querySelector('#support'));
            return { bg: b.backgroundColor, color: b.color, weight: b.fontWeight,
                     border_w: b.borderTopWidth, radius: b.borderRadius,
                     card_border: c.borderTopWidth + ' ' + c.borderTopColor,
                     card_radius: c.borderRadius };
        })()""")
        await page.locator("#support").scroll_into_view_if_needed()
        await page.wait_for_timeout(200)
        await page.locator("#support").screenshot(path=str(OUT / "preview-prod-mobile-support.png"))
        await page.locator("#foot").scroll_into_view_if_needed()
        await page.wait_for_timeout(150)
        await page.screenshot(path=str(OUT / "preview-prod-mobile-bottom.png"))
        res["doc_width"] = await page.evaluate("document.documentElement.scrollWidth")
        res["viewport_width"] = await page.evaluate("window.innerWidth")
        res["console_errors"] = errors

        await page.screenshot(path=str(OUT / "preview-prod-mobile.png"), full_page=True)
        await page.locator("#ben-link").screenshot(
            path=str(OUT / "preview-prod-mobile-ben-link.png"))

        # ── 혜택 탭 ─────────────────────────────────────
        await page.locator("#ben-link").click()
        await page.wait_for_timeout(350)
        res["ben_link_switch"] = await page.evaluate("""(() => {
            const b = document.querySelector('#tab-benefits');
            return b.classList.contains('is-on') && b.getAttribute('aria-selected') === 'true'
                && !document.querySelector('#panel-benefits').hidden
                && document.querySelector('#panel-today').hidden;
        })()""")
        res["ben_link_url_ok"] = "tab=benefits" in page.url
        res["bf_visible"] = await page.locator("#panel-benefits").is_visible()
        res["bf_note"] = (await page.locator("#bf-note").text_content()).strip()
        res["bf_chips"] = await page.eval_on_selector_all(
            "#bf-chips .bf-chip",
            """els => els.map(e => ({ id: e.dataset.bf, text: e.textContent.trim(),
                                      on: e.classList.contains('is-on'),
                                      pressed: e.getAttribute('aria-pressed') }))""")
        res["bf_chip_row"] = await page.evaluate("""(() => {
            const c = [...document.querySelectorAll('#bf-chips .bf-chip')];
            const b = c.map(e => e.getBoundingClientRect());
            return { count: c.length,
                     fit: c.every(e => e.scrollWidth <= e.clientWidth + 1),
                     one_row: b.length > 0
                         && Math.max(...b.map(r => r.top)) - Math.min(...b.map(r => r.top)) <= 1 };
        })()""")
        res["bf_cards"] = await page.eval_on_selector_all(
            "#bf-list .bf",
            r"""els => els.map(e => ({
                id: e.dataset.id, cat: e.dataset.cat,
                prov: e.querySelector('.bf-prov')?.textContent.trim() || '',
                title: e.querySelector('.bf-title')?.textContent.trim(),
                amt: e.querySelector('.bf-amt')?.textContent.trim(),
                dday: e.querySelector('.bf-dd')?.textContent.trim(),
                meta: [...e.querySelectorAll('.bf-meta .bf-row')]
                    .map(r => r.textContent.replace(/\s+/g,' ').trim()),
                link: e.querySelector('.bf-link')?.getAttribute('href') || '',
                link_target: e.querySelector('.bf-link')?.getAttribute('target') || '',
                link_text: e.querySelector('.bf-link')?.textContent.trim() || '',
                terms: e.querySelectorAll('.bf-more li').length
            }))""")
        bc = res["bf_cards"]
        res["bf_count"] = len(bc)
        res["bf_cats"] = sorted({c["cat"] for c in bc})
        res["bf_securities"] = [c["id"] for c in bc if c["cat"] == "securities"]
        res["bf_simple"] = [c["id"] for c in bc if c["cat"] == "simple"]
        res["bf_all_fields"] = all(
            c["prov"] and c["title"] and c["amt"] and c["dday"]
            and any(k.startswith("마감") for k in c["meta"])
            and c["link"].startswith("https://") and c["link_target"] == "_blank"
            and c["link_text"].endswith("↗")
            for c in bc)
        res["bf_ddays"] = [c["dday"] for c in bc]
        res["bf_links"] = [c["link"] for c in bc]
        res["bf_links_unique"] = len(set(res["bf_links"])) == len(bc)
        res["bf_privacy_hits"] = [t for t in TERMS + ALWAYS_TERMS
                                  if t in await page.evaluate("document.body.innerText")]
        await page.screenshot(path=str(OUT / "preview-prod-mobile-benefits.png"), full_page=True)
        await page.screenshot(path=str(OUT / "preview-prod-mobile-benefits-first.png"))
        res["bf_clipped"] = await page.evaluate("""(() => {
            const vw = window.innerWidth, bad = [];
            document.querySelectorAll('#panel-benefits .bf, #panel-benefits .bf *, #panel-benefits .bf-chip')
              .forEach(el => {
                const r = el.getBoundingClientRect();
                if (r.width && (r.left < -1 || r.right > vw + 1)) {
                  bad.push(el.tagName + '.' + el.className + ' ' +
                           Math.round(r.left) + '~' + Math.round(r.right));
                }
              });
            return bad.slice(0, 5);
        })()""")
        await page.locator("#bf-chips [data-bf='securities']").click()
        await page.wait_for_timeout(250)
        res["bf_filter_securities"] = await page.eval_on_selector_all(
            "#bf-list .bf", "els => els.map(e => e.dataset.cat)")
        await page.locator("#bf-chips [data-bf='simple']").click()
        await page.wait_for_timeout(250)
        res["bf_filter_simple"] = await page.eval_on_selector_all(
            "#bf-list .bf", "els => els.map(e => e.dataset.cat)")
        await page.locator("#bf-chips [data-bf='all']").click()
        await page.wait_for_timeout(250)
        res["bf_chip_counts"] = await page.eval_on_selector_all(
            "#bf-chips .bf-chip b", "els => els.map(e => e.textContent.trim())")

        # ── 전체 일정 탭 ────────────────────────────────
        await page.locator("#tab-schedule").click()
        await page.wait_for_timeout(350)
        res["tab_switch_on"] = await page.evaluate("""(() => {
            const s = document.querySelector('#tab-schedule');
            return s.classList.contains('is-on')
                && document.querySelector('#panel-schedule').hidden === false
                && document.querySelector('#panel-today').hidden === true;
        })()""")
        res["tab_url_has_query"] = "tab=schedule" in page.url
        res["sch_counts"] = {
            "subscribe": await page.locator("#sch-subscribe .sc").count(),
            "listing": await page.locator("#sch-listing .sc").count(),
        }
        res["sch_heads"] = await page.eval_on_selector_all(
            ".sch-h", "els => els.map(e => e.textContent.replace(/\\s+/g,' ').trim())")
        res["sch_first"] = await page.evaluate("""(() => {
            const li = document.querySelector('#sch-subscribe .sc');
            if (!li) return null;
            return {
                dday: li.querySelector('.sc-dd')?.textContent.trim(),
                name: li.querySelector('.sc-name')?.textContent.trim(),
                when: li.querySelector('.sc-when')?.textContent.trim(),
                price: li.querySelector('.sc-price')?.textContent.trim(),
                sub: li.querySelector('.sc-sub')?.textContent.trim()
            };
        })()""")
        res["sch_list_items"] = await page.eval_on_selector_all(
            "#sch-listing .sc", "els => els.map(e => e.textContent.replace(/\\s+/g,' ').trim())")
        res["sch_src_urls"] = await page.eval_on_selector_all(
            "#sch-src a", "els => els.map(e => e.getAttribute('href'))")
        res["sch_src_text"] = (await page.inner_text("#sch-src")).replace("\n", " ")
        res["sch_has_cancel"] = await page.locator(".sch-cancel").count() > 0

        # ── 필요 금액 카드 (균등 최소증거금) ──────────────
        # 기대값은 프로덕션의 data.json 을 직접 받아 같은 규칙으로 계산
        pdata = await page.evaluate("fetch('data.json?ts=' + Date.now()).then(r => r.json())")
        IPO_PROD = (pdata or {}).get("ipo") or {}
        plan_m = cash_plan(IPO_PROD, TODAY)
        plan_a = cash_plan(IPO_PROD, TODAY, "all")
        plan_ms = cash_plan(IPO_PROD, TODAY, "month", no_spac=False)
        plan_as = cash_plan(IPO_PROD, TODAY, "all", no_spac=False)
        res["cash_exists"] = await page.locator("#cash-card").count()
        res["cash_above_list"] = await page.evaluate("""(() => {
            const c = document.querySelector('#cash-card').getBoundingClientRect();
            const h = document.querySelector('.sch-head').getBoundingClientRect();
            const l = document.querySelector('#sch-subscribe .sc').getBoundingClientRect();
            return c.top < h.top && h.top < l.top + 1;
        })()""")
        res["cash_peak"] = await page.inner_text("#cash-peak")
        res["cash_when"] = (await page.inner_text("#cash-peak-when")).replace("\n", " ")
        res["cash_total"] = await page.inner_text("#cash-total")
        res["cash_count"] = await page.inner_text("#cash-count")
        res["cash_scope"] = await page.inner_text("#cash-scope")
        res["cash_note"] = await page.inner_text("#cash-note")
        res["cash_chips"] = await page.eval_on_selector_all(
            "#cash-chips .cash-chip",
            "els => els.map(e => [e.textContent.trim(), e.getAttribute('aria-pressed')])")
        res["cash_rows"] = await page.eval_on_selector_all(
            "#sch-subscribe .sc .sc-dep",
            "els => els.map(e => e.textContent.replace(/\\s+/g, ' ').trim())")
        res["cash_clipped"] = await page.evaluate("""(() => {
            const vw = window.innerWidth, bad = [];
            document.querySelectorAll('#cash-card, #cash-card *').forEach(el => {
              const r = el.getBoundingClientRect();
              if (r.width && (r.left < -1 || r.right > vw + 1)) {
                bad.push(el.className + ' ' + Math.round(r.left) + '~' + Math.round(r.right));
              }
            });
            return bad.slice(0, 5);
        })()""")
        res["sch_doc_width"] = await page.evaluate("document.documentElement.scrollWidth")
        res["sch_h_overflow"] = res["sch_doc_width"] > res["viewport_width"]
        res["sch_privacy_hits"] = [t for t in TERMS + ALWAYS_TERMS
                                   if t in await page.evaluate("document.body.innerText")]
        res["sch_errors"] = errors
        await page.screenshot(path=str(OUT / "preview-prod-mobile-schedule.png"), full_page=True)
        await page.screenshot(path=str(OUT / "preview-prod-mobile-schedule-first.png"))
        await page.locator("#sch-src").scroll_into_view_if_needed()
        await page.wait_for_timeout(200)
        await page.screenshot(path=str(OUT / "preview-prod-mobile-schedule-bottom.png"))
        await page.locator("#cash-card").scroll_into_view_if_needed()
        await page.wait_for_timeout(150)
        await page.locator("#cash-card").screenshot(path=str(OUT / "preview-prod-mobile-cash.png"))

        # 칩 — 이번 달/전체 · 스팩 제외 즉시 재계산
        await page.locator("[data-cash-range='all']").click()
        await page.wait_for_timeout(250)
        res["cash_all_peak"] = await page.inner_text("#cash-peak")
        res["cash_all_when"] = (await page.inner_text("#cash-peak-when")).replace("\n", " ")
        res["cash_all_total"] = await page.inner_text("#cash-total")
        res["cash_all_count"] = await page.inner_text("#cash-count")
        res["cash_all_scope"] = await page.inner_text("#cash-scope")
        res["cash_all_pressed"] = await page.eval_on_selector_all(
            "#cash-chips .cash-chip", "els => els.map(e => e.getAttribute('aria-pressed'))")
        await page.locator("#cash-spac").click()
        await page.wait_for_timeout(250)
        res["cash_spac_off_peak"] = await page.inner_text("#cash-peak")
        res["cash_spac_off_total"] = await page.inner_text("#cash-total")
        res["cash_spac_off_count"] = await page.inner_text("#cash-count")
        res["cash_spac_pressed"] = await page.get_attribute("#cash-spac", "aria-pressed")
        await page.locator("[data-cash-range='month']").click()
        await page.wait_for_timeout(250)
        res["cash_month_spac_peak"] = await page.inner_text("#cash-peak")
        res["cash_month_spac_total"] = await page.inner_text("#cash-total")
        res["cash_month_spac_count"] = await page.inner_text("#cash-count")
        res["cash_rows_after"] = await page.eval_on_selector_all(
            "#sch-subscribe .sc .sc-dep",
            "els => els.map(e => e.textContent.replace(/\\s+/g, ' ').trim())")
        await page.locator("#cash-spac").click()
        await page.wait_for_timeout(250)
        res["cash_restored"] = await page.evaluate("""(() => ({
            peak: document.querySelector('#cash-peak').textContent.trim(),
            chip: document.querySelector('[data-cash-range=\"month\"]').getAttribute('aria-pressed'),
            spac: document.querySelector('#cash-spac').getAttribute('aria-pressed')
        }))()""")
        await ctx.close()

        # 테마: 기본 라이트 고정 + 상단 다크 토글 (시스템 설정과 무관)
        thctx = await browser.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
            has_touch=True, user_agent=UA, locale="ko-KR", timezone_id="Asia/Seoul")
        thp = await thctx.new_page()
        th_errors = []
        thp.on("console", lambda m: th_errors.append(f"console.{m.type}: {m.text}")
                if m.type == "error" else None)
        thp.on("pageerror", lambda e: th_errors.append(f"pageerror: {e}"))
        await thp.goto(DATED, wait_until="networkidle", timeout=45000)
        await thp.wait_for_selector("#main:not([hidden])", timeout=15000)
        await thp.wait_for_timeout(300)
        res["theme_attr_default"] = await thp.evaluate(
            "document.documentElement.getAttribute('data-theme')")
        res["theme_bg_default"] = await thp.evaluate(
            "getComputedStyle(document.body).backgroundColor")
        res["theme_meta_default"] = await thp.get_attribute("#theme-color", "content")
        res["theme_btn_visible"] = await thp.locator("#theme-toggle").is_visible()
        res["theme_btn_label"] = await thp.get_attribute("#theme-toggle", "aria-label")
        res["theme_btn_pressed"] = await thp.get_attribute("#theme-toggle", "aria-pressed")
        res["theme_btn_svgs"] = await thp.locator("#theme-toggle svg").count()
        res["theme_head_row"] = await thp.evaluate("""(() => {
            const b = document.querySelector('.brand').getBoundingClientRect();
            const u = document.querySelector('.updated').getBoundingClientRect();
            const t = document.querySelector('#theme-toggle').getBoundingClientRect();
            const bar = document.querySelector('.brandbar').getBoundingClientRect();
            const cy = r => Math.round(r.top + r.height / 2);
            return { toggle_w: Math.round(t.width),
                     same_row: Math.abs(cy(b) - cy(t)) <= 6 && Math.abs(cy(u) - cy(t)) <= 6,
                     right_of_updated: t.left >= u.right - 1,
                     last_in_row: t.right <= bar.right + 2,
                     inside_bar: t.top >= bar.top - 2 && t.bottom <= bar.bottom + 2,
                     bar_h: Math.round(bar.height) };
        })()""")
        await thp.locator(".site-head").screenshot(
            path=str(OUT / "preview-prod-mobile-header.png"))
        await thp.locator("#theme-toggle").click()
        await thp.wait_for_timeout(250)
        res["theme_dark_attr"] = await thp.evaluate(
            "document.documentElement.getAttribute('data-theme')")
        res["theme_dark_bg"] = await thp.evaluate(
            "getComputedStyle(document.body).backgroundColor")
        res["theme_dark_stored"] = await thp.evaluate("localStorage.getItem('mydon-theme')")
        res["theme_dark_label"] = await thp.get_attribute("#theme-toggle", "aria-label")
        res["theme_dark_pressed"] = await thp.get_attribute("#theme-toggle", "aria-pressed")
        res["theme_dark_meta"] = await thp.get_attribute("#theme-color", "content")
        await thp.locator(".site-head").screenshot(
            path=str(OUT / "preview-prod-mobile-header-dark.png"))
        await thp.reload(wait_until="networkidle")
        await thp.wait_for_selector("#main:not([hidden])", timeout=15000)
        await thp.wait_for_timeout(200)
        res["theme_persist_attr"] = await thp.evaluate(
            "document.documentElement.getAttribute('data-theme')")
        res["theme_persist_bg"] = await thp.evaluate(
            "getComputedStyle(document.body).backgroundColor")
        await thp.locator("#theme-toggle").click()
        await thp.wait_for_timeout(250)
        res["theme_light_back_attr"] = await thp.evaluate(
            "document.documentElement.getAttribute('data-theme')")
        res["theme_light_back_stored"] = await thp.evaluate("localStorage.getItem('mydon-theme')")
        res["theme_errors"] = th_errors
        await thctx.close()

        dark = await browser.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
            has_touch=True, user_agent=UA, locale="ko-KR", timezone_id="Asia/Seoul",
            color_scheme="dark")
        dpage = await dark.new_page()
        # 시스템이 다크여도 기본은 라이트 — 저장값이 dark 일 때만 다크로 뜨는지
        sd_errors = []
        dpage.on("console", lambda m: sd_errors.append(f"console.{m.type}: {m.text}")
                 if m.type == "error" else None)
        await dpage.goto(DATED, wait_until="networkidle", timeout=45000)
        await dpage.wait_for_selector("#main:not([hidden])", timeout=15000)
        await dpage.wait_for_timeout(300)
        res["sysdark_attr"] = await dpage.evaluate(
            "document.documentElement.getAttribute('data-theme')")
        res["sysdark_bg"] = await dpage.evaluate(
            "getComputedStyle(document.body).backgroundColor")
        await dpage.locator(".site-head").screenshot(
            path=str(OUT / "preview-prod-mobile-header-sysdark.png"))
        await dpage.add_init_script(DARK_PREF)
        await dpage.reload(wait_until="networkidle", timeout=45000)
        await dpage.wait_for_selector("#main:not([hidden])", timeout=15000)
        await dpage.wait_for_timeout(300)
        res["dark_theme_attr"] = await dpage.evaluate(
            "document.documentElement.getAttribute('data-theme')")
        res["dark_theme_bg"] = await dpage.evaluate(
            "getComputedStyle(document.body).backgroundColor")
        res["sysdark_errors"] = sd_errors
        await dpage.screenshot(path=str(OUT / "preview-prod-mobile-dark.png"), full_page=True)
        res["dark_ok"] = await dpage.locator(".ev").count()
        res["dark_share_visible"] = await dpage.locator("#share").is_visible()
        res["dark_share_count"] = await dpage.locator("#share .share-btn").count()
        res["dark_share_btns"] = await dpage.eval_on_selector_all(
            "#share .share-btn", "els => els.map(e => Math.round(e.getBoundingClientRect().height))")
        res["dark_share_labels"] = await dpage.eval_on_selector_all(
            "#share .share-btn .lbl", "els => els.map(e => e.textContent.trim())")
        res["dark_share_grid"] = await dpage.evaluate("""(() => {
            const b = [...document.querySelectorAll('#share .share-btn')].map(e => e.getBoundingClientRect());
            const lbl = [...document.querySelectorAll('#share .share-btn .lbl')];
            return { same_row: b.length === 2 && Math.abs(b[0].top - b[1].top) <= 1,
                     fit: lbl.every(e => e.scrollWidth <= e.clientWidth + 1) };
        })()""")
        await dpage.locator("#share").scroll_into_view_if_needed()
        await dpage.wait_for_timeout(150)
        await dpage.locator("#share").screenshot(
            path=str(OUT / "preview-prod-mobile-share-dark.png"))
        await dpage.locator("#tab-schedule").click()
        await dpage.wait_for_timeout(300)
        res["dark_sch_visible"] = await dpage.locator("#panel-schedule").is_visible()
        res["dark_sch_cards"] = await dpage.locator("#sch-subscribe .sc").count()
        res["dark_cash_visible"] = await dpage.locator("#cash-card").is_visible()
        res["dark_cash_peak"] = await dpage.inner_text("#cash-peak")
        res["dark_sch_overflow"] = await dpage.evaluate(
            "document.documentElement.scrollWidth > window.innerWidth + 1")
        await dpage.screenshot(path=str(OUT / "preview-prod-mobile-schedule-dark.png"), full_page=True)
        await dpage.locator("#tab-benefits").click()
        await dpage.wait_for_timeout(300)
        res["dark_bf_visible"] = await dpage.locator("#panel-benefits").is_visible()
        res["dark_bf_cards"] = await dpage.locator("#bf-list .bf").count()
        res["dark_bf_overflow"] = await dpage.evaluate(
            "document.documentElement.scrollWidth > window.innerWidth + 1")
        await dpage.screenshot(path=str(OUT / "preview-prod-mobile-benefits-dark.png"), full_page=True)
        # 응원 카드 — 다크 모드에서도 카카오페이 옐로 유지
        await dpage.locator("#support").scroll_into_view_if_needed()
        await dpage.wait_for_timeout(150)
        res["dark_support_visible"] = await dpage.locator("#support").is_visible()
        res["dark_support_btn_style"] = await dpage.evaluate("""(() => {
            const b = getComputedStyle(document.querySelector('#support .sup-btn'));
            return { bg: b.backgroundColor, color: b.color };
        })()""")
        await dpage.locator("#support").screenshot(
            path=str(OUT / "preview-prod-mobile-support-dark.png"))
        await dark.close()

        # 데스크톱 폭에서도 확인
        desk = await browser.new_context(viewport={"width": 1280, "height": 900},
                                        locale="ko-KR", timezone_id="Asia/Seoul")
        dp = await desk.new_page()
        await dp.goto(DATED, wait_until="networkidle", timeout=45000)
        await dp.wait_for_selector("#main:not([hidden])", timeout=15000)
        await dp.wait_for_timeout(300)
        res["desktop_hero"] = await dp.locator(".hero").count()
        res["desktop_share_visible"] = await dp.locator("#share").is_visible()
        res["desktop_share_labels"] = await dp.eval_on_selector_all(
            "#share .share-btn .lbl", "els => els.map(e => e.textContent.trim())")
        res["desktop_ben_link"] = await dp.locator("#ben-link").is_visible()
        res["desktop_h_overflow"] = await dp.evaluate(
            "document.documentElement.scrollWidth > window.innerWidth + 1")
        res["desktop_theme_btn"] = await dp.locator("#theme-toggle").is_visible()
        res["desktop_theme_row"] = await dp.evaluate("""(() => {
            const u = document.querySelector('.updated').getBoundingClientRect();
            const t = document.querySelector('#theme-toggle').getBoundingClientRect();
            const bar = document.querySelector('.brandbar').getBoundingClientRect();
            return { same_row: Math.abs((u.top + u.height / 2) - (t.top + t.height / 2)) <= 6,
                     right_of_updated: t.left >= u.right - 1,
                     inside_bar: t.top >= bar.top - 2 && t.bottom <= bar.bottom + 2 };
        })()""")
        await dp.locator(".site-head").screenshot(
            path=str(OUT / "preview-prod-desktop-header.png"))
        await dp.screenshot(path=str(OUT / "preview-prod-desktop.png"))
        await dp.locator("#tab-schedule").click()
        await dp.wait_for_timeout(300)
        res["desktop_sch_cards"] = await dp.locator("#sch-subscribe .sc").count()
        res["desktop_cash_peak"] = await dp.inner_text("#cash-peak")
        res["desktop_sch_overflow"] = await dp.evaluate(
            "document.documentElement.scrollWidth > window.innerWidth + 1")
        await dp.screenshot(path=str(OUT / "preview-prod-desktop-schedule.png"), full_page=True)
        await dp.locator("#tab-benefits").click()
        await dp.wait_for_timeout(300)
        res["desktop_bf_cards"] = await dp.locator("#bf-list .bf").count()
        res["desktop_bf_overflow"] = await dp.evaluate(
            "document.documentElement.scrollWidth > window.innerWidth + 1")
        await dp.screenshot(path=str(OUT / "preview-prod-desktop-benefits.png"), full_page=True)
        await desk.close()

        # ?tab=schedule 딥링크
        deepl = await browser.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
            has_touch=True, user_agent=UA, locale="ko-KR", timezone_id="Asia/Seoul")
        lp = await deepl.new_page()
        await lp.goto(DATED + "&tab=schedule", wait_until="networkidle", timeout=45000)
        await lp.wait_for_selector("#main:not([hidden])", timeout=15000)
        await lp.wait_for_timeout(300)
        res["deeplink_schedule"] = await lp.locator("#panel-schedule").is_visible()
        res["deeplink_cards"] = await lp.locator("#sch-subscribe .sc").count()
        await deepl.close()
        deeplb = await browser.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
            has_touch=True, user_agent=UA, locale="ko-KR", timezone_id="Asia/Seoul")
        bp = await deeplb.new_page()
        await bp.goto(DATED + "&tab=benefits", wait_until="networkidle", timeout=45000)
        await bp.wait_for_selector("#main:not([hidden])", timeout=15000)
        await bp.wait_for_timeout(300)
        res["deeplink_benefits"] = await bp.locator("#panel-benefits").is_visible()
        res["deeplink_bf_cards"] = await bp.locator("#bf-list .bf").count()
        await deeplb.close()

        # 주관사 앱 열기 — iPhone UA 에서는 같은 버튼이 App Store 로 바뀌는지
        iosctx = await browser.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
            has_touch=True, user_agent=IOS_UA, locale="ko-KR", timezone_id="Asia/Seoul")
        ip = await iosctx.new_page()
        await ip.goto(DATED, wait_until="networkidle", timeout=45000)
        await ip.wait_for_selector("#main:not([hidden])", timeout=15000)
        await ip.wait_for_timeout(300)
        res["ios_app_btns"] = await ip.eval_on_selector_all(
            ".hero .app-open",
            "els => els.map(e => ({ text: e.textContent.replace(/\\s+/g, ' ').trim(),"
            " href: e.getAttribute('href') }))")
        res["ios_h_overflow"] = await ip.evaluate(
            "document.documentElement.scrollWidth > window.innerWidth + 1")
        await iosctx.close()

        # 주관사 앱 열기 — 데스크톱 UA 에서는 그대로 Google Play 스토어 링크
        dctx = await browser.new_context(viewport={"width": 1280, "height": 900},
                                        user_agent=DESKTOP_UA,
                                        locale="ko-KR", timezone_id="Asia/Seoul")
        dsp = await dctx.new_page()
        await dsp.goto(DATED, wait_until="networkidle", timeout=45000)
        await dsp.wait_for_selector("#main:not([hidden])", timeout=15000)
        await dsp.wait_for_timeout(300)
        res["desktop_app_btns"] = await dsp.eval_on_selector_all(
            ".hero .app-open",
            "els => els.map(e => ({ text: e.textContent.replace(/\\s+/g, ' ').trim(),"
            " href: e.getAttribute('href'), target: e.getAttribute('target'),"
            " rel: e.getAttribute('rel') || '' }))")
        await dctx.close()
        # ── 주말 모드 — 다음 주 청약 미리보기 (?date=토요일) ─────────────
        pd = dt.date.fromisoformat(str(res["prod_date"])[:10])
        sat = pd + dt.timedelta(days=1)
        while sat.weekday() != 5:
            sat += dt.timedelta(days=1)
        wk = week_preview(IPO_PROD, sat)
        res["wk_expect"] = {"names": wk["names"], "peak": wk["peak_text"], "label": wk["label"]}
        wctx = await browser.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=2,
            is_mobile=True, has_touch=True, user_agent=UA,
            locale="ko-KR", timezone_id="Asia/Seoul")
        wpage = await wctx.new_page()
        wk_errors = []
        wpage.on("console", lambda m: wk_errors.append(f"console.{m.type}: {m.text}")
                 if m.type == "error" else None)
        wpage.on("pageerror", lambda e: wk_errors.append(f"pageerror: {e}"))
        await wpage.goto(URL + "?date=" + sat.isoformat(), wait_until="networkidle", timeout=45000)
        await wpage.wait_for_selector("#main:not([hidden])", timeout=15000)
        await wpage.wait_for_timeout(400)
        res["wk_class"] = await wpage.evaluate(
            "(() => { const h = document.querySelector('.hero');"
            " return h ? h.className : 'none'; })()")
        res["wk_flags"] = await wpage.eval_on_selector_all(
            ".hero .flag", "els => els.map(e => e.textContent.trim())")
        res["wk_title"] = await wpage.evaluate(
            "document.querySelector('.hero .hname').textContent.replace(/\\s+/g, ' ').trim()")
        res["wk_note"] = (await wpage.inner_text(".hero .hernote")).replace("\n", " ")
        res["wk_dateline"] = await wpage.inner_text("#dateline")
        res["wk_sched"] = (await wpage.inner_text("#sched-note")).replace("\n", " ")
        res["wk_names"] = await wpage.eval_on_selector_all(
            "#wk-list .wk-name", "els => els.map(e => e.textContent.trim())")
        res["wk_whens"] = await wpage.eval_on_selector_all(
            "#wk-list .wk-when", "els => els.map(e => e.textContent.trim())")
        res["wk_deps"] = await wpage.eval_on_selector_all(
            "#wk-list .wk-dep", "els => els.map(e => e.textContent.replace(/\\s+/g, ' ').trim())")
        res["wk_peak"] = await opt_text(wpage, "#wk-peak")
        res["wk_peak_when"] = (await opt_text(wpage, "#wk-peak-when")).replace("\n", " ")
        res["wk_prev_label"] = await opt_text(wpage, "#prev-day .srow .k")
        res["wk_today_words"] = await wpage.evaluate("""(() => {
            const t = document.querySelector('#sec-ipo').innerText + ' ' +
                      document.querySelector('#ipo-foot').innerText;
            return ['오늘 청약', '오늘 상장'].filter(w => t.includes(w));
        })()""")
        res["wk_share_labels"] = await wpage.eval_on_selector_all(
            "#share .share-btn .lbl", "els => els.map(e => e.textContent.trim())")
        res["wk_share_h"] = await wpage.eval_on_selector_all(
            "#share .share-btn", "els => els.map(e => Math.round(e.getBoundingClientRect().height))")
        res["wk_overflow"] = await wpage.evaluate(
            "document.documentElement.scrollWidth > window.innerWidth + 1")
        res["wk_privacy_hits"] = [t for t in TERMS + ALWAYS_TERMS
                                  if t in await wpage.evaluate("document.body.innerText")]
        res["wk_errors"] = wk_errors
        await wpage.screenshot(path=str(OUT / "preview-prod-mobile-weekend-first.png"))
        await wpage.screenshot(path=str(OUT / "preview-prod-mobile-weekend.png"), full_page=True)

        # 주말 화면의 다크 모드 · 전체 일정 탭·혜택 탭도 그대로 동작하는지
        await wpage.add_init_script(DARK_PREF)
        await wpage.reload(wait_until="networkidle", timeout=45000)
        await wpage.wait_for_selector("#main:not([hidden])", timeout=15000)
        await wpage.wait_for_timeout(300)
        res["wk_dark_class"] = await wpage.evaluate(
            "(() => { const h = document.querySelector('.hero');"
            " return h ? h.className : 'none'; })()")
        res["wk_dark_peak"] = await opt_text(wpage, "#wk-peak")
        res["wk_dark_overflow"] = await wpage.evaluate(
            "document.documentElement.scrollWidth > window.innerWidth + 1")
        await wpage.screenshot(path=str(OUT / "preview-prod-mobile-weekend-dark.png"))
        await wpage.locator("#tab-schedule").click()
        await wpage.wait_for_timeout(300)
        res["wk_sch_cards"] = await wpage.locator("#sch-subscribe .sc").count()
        res["wk_sch_cash"] = await wpage.inner_text("#cash-peak")
        await wpage.locator("#tab-benefits").click()
        await wpage.wait_for_timeout(300)
        res["wk_bf_cards"] = await wpage.locator("#bf-list .bf").count()
        await wpage.locator("#tab-today").click()
        await wpage.wait_for_timeout(200)
        res["wk_back_today"] = await wpage.locator("#hero-weekend").is_visible()
        await wctx.close()

        # 실제 오늘(KST)이 주말이면 처음 연 기본 URL(live) 화면이 미리보기여야 합니다
        real_kst = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
        res["real_kst_day"] = real_kst.isoformat()
        res["real_weekend"] = real_kst.weekday() >= 5
        await browser.close()


    # 청약일이면 유튜브 요약까지, 상장일이면 상장 포인트로 히어로를 검증
    hero_ok = ((res["hero_kind"] == "subscribe" and res["yt_rows"] >= 2)
               or (res["hero_kind"] == "listing" and res["listing_points"] >= 1))

    kst_today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()

    def _live(items):
        out = []
        for b in items or []:
            exp = (b or {}).get("expiresAt")
            if exp and dt.date.fromisoformat(str(exp)[:10]) < kst_today:
                continue
            out.append(b)
        return out

    live_b = _live(prod_data.get("benefits"))
    sec_b = [b for b in live_b if (b.get("category") or "securities") != "simple"]
    simple_b = [b for b in live_b if b.get("category") == "simple"]

    # 조건을 한 줄씩 따로 평가합니다 — 실패한 조건만 이름 그대로 찍혀서
    # 어느 확인이 깨졌는지 바로 보입니다(조건 자체는 예전 and 체인과 같습니다).
    _conds = [
        'res["http_status"] == 200',
        # 이전 Vercel 주소는 ipo.mydon.kr 로 영구 리다이렉트(308/301) — 200 이면 실패
        'res["vercel_ok"]',
        'res["vercel_final_ok"]',
        'res["vercel_deep_ok"]',
        'res["vercel_status"] != 200',
        'res["share_visible"]',
        'res["share_label"].startswith("단톡방에")',
        '"상장" in res["share_label"]',
        'len(res["share_btns"]) == 2',
        'res["share_ids"] == ["share-sub", "share-listing"]',
        'res["share_disabled"] == [False, False]',
        'res["share_btns"][0] == "청약 정보 공유"',
        'res["share_btns"][1] == "상장 정보 공유"',
        'min(res["share_btn_h"]) >= 44',
        'res["share_grid"]["count"] == 2',
        'res["share_grid"]["same_row"]',
        'res["share_grid"]["equal_w"]',
        'res["share_grid"]["fills"]',
        'res["share_grid"]["fit"]',
        'res["share_placed_ok"]',
        # 테마: 기본 라이트 고정 + 상단 다크 토글 (시스템 다크여도 라이트)
        'res["theme_attr_default"] is None',
        'res["theme_bg_default"] == "rgb(244, 246, 248)"',
        'res["theme_meta_default"] == "#f4f6f8"',
        'res["theme_btn_visible"]',
        'res["theme_btn_label"] == "다크 모드로 전환"',
        'res["theme_btn_pressed"] == "false"',
        'res["theme_btn_svgs"] == 2',
        'res["theme_head_row"]["same_row"]',
        'res["theme_head_row"]["right_of_updated"]',
        'res["theme_head_row"]["last_in_row"]',
        'res["theme_head_row"]["inside_bar"]',
        'res["theme_head_row"]["toggle_w"] >= 24',
        'res["theme_head_row"]["bar_h"] <= 28',
        'res["theme_dark_attr"] == "dark"',
        'res["theme_dark_bg"] == "rgb(16, 16, 18)"',
        'res["theme_dark_stored"] == "dark"',
        'res["theme_dark_label"] == "라이트 모드로 전환"',
        'res["theme_dark_pressed"] == "true"',
        'res["theme_dark_meta"] == "#101012"',
        'res["theme_persist_attr"] == "dark"',
        'res["theme_persist_bg"] == "rgb(16, 16, 18)"',
        'res["theme_light_back_attr"] is None',
        'res["theme_light_back_stored"] == "light"',
        'not res["theme_errors"]',
        'res["sysdark_attr"] is None',
        'res["sysdark_bg"] == "rgb(244, 246, 248)"',
        'res["dark_theme_attr"] == "dark"',
        'res["dark_theme_bg"] == "rgb(16, 16, 18)"',
        'res["desktop_theme_btn"]',
        'res["desktop_theme_row"]["same_row"]',
        'res["desktop_theme_row"]["right_of_updated"]',
        'res["desktop_theme_row"]["inside_bar"]',
        'res["share_native"] == "undefined"',
        'res["share_lines"] >= 3',
        'res["share_head_ok"]',
        'res["share_clip_last"] == SITE_URL',
        'res["share_exact"]',
        'res["share_no_summary"]',
        'not res["share_privacy_hits"]',
        '"청약 정보" in res["share_copy_toast"]',
        'res["share_copy_label"] == "복사됐어요"',
        'res["share_copy_label_back"] == "청약 정보 공유"',
        'res["share_fallback_clipboard"]',
        '"복사" in res["share_fallback_toast"]',
        'res["list_exact"]',
        'res["list_head_ok"]',
        'res["list_bullets"] >= 1',
        'res["list_clip_last"] == SITE_URL',
        'not res["list_privacy_hits"]',
        '"상장 정보" in res["list_copy_toast"]',
        'res["list_copy_label"] == "복사됐어요"',
        'res["list_copy_label_back"] == "상장 정보 공유"',
        'res["dark_share_visible"]',
        'res["dark_share_count"] == 2',
        'min(res["dark_share_btns"]) >= 44',
        'res["dark_share_labels"] == ["청약 정보 공유", "상장 정보 공유"]',
        'res["dark_share_grid"]["same_row"]',
        'res["dark_share_grid"]["fit"]',
        'res["desktop_share_visible"]',
        'res["desktop_share_labels"] == ["청약 정보 공유", "상장 정보 공유"]',
        'res["app_btns"] and all( (b["href"].startswith("intent://") and ";S.browser_fallback_url=" + PLAY_ENC in b["href"] and b["href"].endswith(";end") and not b["target"] and b["h"] >= 36) or (b["href"].startswith("https://play.google.com/store/apps/details?id=") and b["target"] == "_blank" and "noopener" in b["rel"] and b["h"] >= 36) for b in res["app_btns"])',
        'all("com.ibks.ione.mts" not in b["href"] or b["href"].startswith( "https://play.google.com/store/apps/details?id=") for b in res["app_btns"])',
        'res["ios_app_btns"] and all( b["href"].startswith("https://apps.apple.com/kr/app/id") for b in res["ios_app_btns"])',
        'not res["ios_h_overflow"]',
        'res["desktop_app_btns"] and all( b["href"].startswith("https://play.google.com/store/apps/details?id=") and b["target"] == "_blank" and "noopener" in b["rel"] for b in res["desktop_app_btns"])',
        '"1분 요약" in res["title"]',
        # 마이돈 브랜드·공유 제목·캐시 버스터가 라이브에 실렸는지
        'res["brand"] == "마이돈 · 공모주"',
        'res["brand_nowrap"] == "nowrap"',
        'res["title"].startswith("마이돈 — 오늘의 공모주 1분 요약")',
        'res["og_title"] == "마이돈 — 오늘의 공모주 1분 요약"',
        'res["og_site_name"] == "마이돈"',
        '"?v=" in (res["css_href"] or "")',
        '"?v=" in (res["js_src"] or "")',
        '"max-age=60" in res["origin_css_cache_control"]',
        '"must-revalidate" in res["origin_css_cache_control"]',
        '"max-age=60" in res["origin_js_cache_control"]',
        '"must-revalidate" in res["origin_js_cache_control"]',
        '"must-revalidate" in res["css_cache_control"]',
        'res["css_matches_origin"]',
        'res["js_matches_origin"]',
        'res["robots"]',
        '"noindex" not in res["robots"]',
        '"index" in res["robots"]',
        'res["canonical"] == URL',
        'not res["draft_badge_visible"]',
        'not res["has_draft_word"]',
        'res["hero"] == 1',
        'hero_ok',
        '"다음 청약" in res["next_rows"]',
        'res["next_dday"].startswith("D-")',
        'res["next_bottom"] <= res["viewport_h"]',
        'res["today_has_no_detail"]',
        'res["ben_link_visible"]',
        'res["ben_link_text"] == "증권사 개설·현금성 혜택 " + res["ben_link_count"] + "건 보기"',
        'res["share_icons"] == 2',
        'res["ben_link_icon"] == 1',
        'res["ben_link_href"] == "?tab=benefits"',
        'res["ben_link_count"] == str(len(sec_b))',
        'res["ben_link_switch"]',
        'res["ben_link_url_ok"]',
        'res["tabs_visible"]',
        'res["tab_labels"] == ["오늘 요약", "전체 일정", "혜택"]',
        'res["tab_default_today"]',
        'res["tab_row"]["three"]',
        'res["tab_row"]["same_row"]',
        'res["tab_row"]["equal_w"]',
        'res["tab_row"]["fit"]',
        'res["tab_switch_on"]',
        'res["tab_url_has_query"]',
        'res["bf_visible"]',
        '[c["id"] for c in res["bf_chips"]] == ["all", "securities", "simple"]',
        'res["bf_chips"][0]["on"]',
        'res["bf_chip_row"]["count"] == 3',
        'res["bf_chip_row"]["fit"]',
        'res["bf_chip_row"]["one_row"]',
        'res["bf_chip_counts"] == [str(len(live_b)), str(len(sec_b)), str(len(simple_b))]',
        'res["bf_count"] == len(live_b)',
        'len(res["bf_securities"]) == len(sec_b) >= 4',
        'len(res["bf_simple"]) == len(simple_b) >= 3',
        'res["bf_cats"] == ["securities", "simple"]',
        'res["bf_all_fields"]',
        'res["bf_links_unique"]',
        'all(d.startswith("D-") or d in ("오늘 마감", "상시") for d in res["bf_ddays"])',
        'res["bf_filter_securities"] == ["securities"] * len(sec_b)',
        'res["bf_filter_simple"] == ["simple"] * len(simple_b)',
        'not res["bf_clipped"]',
        'not res["bf_privacy_hits"]',
        'res["dark_bf_visible"]',
        'res["dark_bf_cards"] == len(live_b)',
        'not res["dark_bf_overflow"]',
        'res["desktop_bf_cards"] == len(live_b)',
        'not res["desktop_bf_overflow"]',
        'res["deeplink_benefits"]',
        'res["deeplink_bf_cards"] == len(live_b)',
        'res["sch_counts"]["subscribe"] >= 10',
        'res["sch_counts"]["listing"] >= 1',
        'res["sch_first"]',
        'res["sch_first"]["dday"].startswith("D-")',
        'res["sch_first"]["when"].endswith("청약")',
        '"희망" in (res["sch_first"]["price"] or "")',
        'any("38.co.kr" in (u or "") for u in res["sch_src_urls"])',
        'not res["sch_h_overflow"]',
        'not res["sch_privacy_hits"]',
        'not res["sch_errors"]',
        'res["dark_sch_visible"]',
        'not res["dark_sch_overflow"]',
        'res["desktop_sch_cards"] >= 10',
        'not res["desktop_sch_overflow"]',
        'res["deeplink_schedule"]',
        'res["deeplink_cards"] >= 10',
        'res["cash_exists"] == 1',
        'res["cash_above_list"]',
        'res["cash_peak"] == cash_peak_text(plan_m)',
        'res["cash_when"].startswith(short_day(plan_m["peak"][0]))',
        'all(n in res["cash_when"] for n in plan_m["peak"][1]["names"][:3])',
        'res["cash_total"] == won_short(plan_m["total"])',
        'res["cash_count"] == str(plan_m["count"])',
        'res["cash_scope"] == plan_m["month_label"]',
        '"추정치입니다" in res["cash_note"]',
        'res["cash_chips"][0] == [plan_m["month_label"], "true"]',
        'res["cash_chips"][1] == [plan_m["all_label"], "false"]',
        'res["cash_chips"][2][1] == "true"',
        '"스팩 제외" in res["cash_chips"][2][0]',
        'res["cash_rows"] == [cash_row_text(it) for it in sorted(IPO_PROD["upcoming"]["subscribe"], key=lambda x: str(x.get("start") or "9999"))]',
        'res["cash_all_peak"] == cash_peak_text(plan_a)',
        'res["cash_all_when"].startswith(short_day(plan_a["peak"][0]))',
        'res["cash_all_total"] == won_short(plan_a["total"])',
        'res["cash_all_count"] == str(plan_a["count"])',
        'res["cash_all_scope"] == plan_a["all_label"]',
        'res["cash_all_pressed"] == ["false", "true", "true"]',
        'res["cash_spac_off_peak"] == cash_peak_text(plan_as)',
        'res["cash_spac_off_total"] == won_short(plan_as["total"])',
        'res["cash_spac_off_count"] == str(plan_as["count"])',
        'res["cash_spac_pressed"] == "false"',
        'res["cash_month_spac_peak"] == cash_peak_text(plan_ms)',
        'res["cash_month_spac_total"] == won_short(plan_ms["total"])',
        'res["cash_month_spac_count"] == str(plan_ms["count"])',
        'res["cash_rows_after"] == res["cash_rows"]',
        'res["cash_restored"] == {"peak": cash_peak_text(plan_m), "chip": "true", "spac": "true"}',
        'not res["cash_clipped"]',
        'res["dark_cash_visible"]',
        'res["dark_cash_peak"] == cash_peak_text(plan_m)',
        'res["desktop_cash_peak"] == cash_peak_text(plan_m)',
        'not res["privacy_hits"]',
        'not res["invite_words"]',
        # ── 주말 모드 · 다음 주 청약 미리보기 ────────────────
        '("is-weekend" in res["live_hero"]) == res["real_weekend"]',
        'res["wk_class"] == "hero is-weekend"',
        'res["wk_flags"] == ["주말 휴장", "다음 주 청약 미리보기"]',
        'res["wk_dateline"] == f"{sat.year}년 {sat.month}월 {sat.day}일 토요일 · 주말 휴장"',
        'res["wk_title"] == "다음 주 청약 " + str(len(wk["items"])) + "건"',
        'res["wk_note"] == wk["label"] + " · 직전 영업일(" + mdd(res["prod_date"]) + ") 수집"',
        '"직전 영업일" in res["wk_sched"]',
        '"월요일 07:30" in res["wk_sched"]',
        'res["wk_names"] == wk["names"]',
        'res["wk_whens"] == wk["whens"]',
        'res["wk_deps"] == wk["deps"]',
        'res["wk_peak"] == (wk["peak_text"] or "")',
        'res["wk_peak_when"].startswith(short_day(wk["peak"][0]))',
        'all(n in res["wk_peak_when"] for n in wk["peak"][1]["names"][:3])',
        'res["wk_prev_label"] == "직전 영업일(" + mdd(IPO_PROD["listing"].get("date")) + ") 상장"',
        'res["wk_today_words"] == []',
        'res["wk_share_labels"] == ["청약 정보 공유", "상장 정보 공유"]',
        'min(res["wk_share_h"]) >= 44',
        'not res["wk_overflow"]',
        'not res["wk_privacy_hits"]',
        'not res["wk_errors"]',
        'res["wk_dark_class"] == "hero is-weekend"',
        'res["wk_dark_peak"] == (wk["peak_text"] or "")',
        'not res["wk_dark_overflow"]',
        'res["wk_sch_cards"] >= 10',
        'res["wk_bf_cards"] >= 1',
        'res["wk_back_today"]',
        'res["support_visible"]',
        'res["support_href"] == "https://qr.kakaopay.com/Ej7j2Gwco"',
        'res["support_target"] == "_blank"',
        '"noopener" in (res["support_rel"] or "")',
        'res["support_above_footer"]',
        'res["css_v_deployed"]',
        'res["js_v_deployed"]',
        'res["support_title_style"]["size"] == "14px"',
        'res["support_title_style"]["weight"] == "700"',
        'res["support_title_style"]["color_is_ink"]',
        'res["support_btn_style"]["bg"] == "rgb(254, 229, 0)"',
        'res["support_btn_style"]["color"] == "rgb(25, 25, 25)"',
        'res["support_btn_style"]["weight"] == "700"',
        'res["support_btn_style"]["border_w"] == "1px"',
        'res["support_btn_style"]["radius"] == "10px"',
        'res["support_btn_style"]["card_radius"] == "14px"',
        'res["dark_support_visible"]',
        'res["dark_support_btn_style"]["bg"] == "rgb(254, 229, 0)"',
        'res["dark_support_btn_style"]["color"] == "rgb(25, 25, 25)"',
        'not res["console_errors"]',
        'res["doc_width"] == res["viewport_width"]',
        'not res["desktop_h_overflow"]',
    ]
    ok = True
    _env = dict(globals())
    _env.update({_k: _v for _k, _v in locals().items() if not _k.startswith('_')})
    for _c in _conds:
        try:
            _v = bool(eval(_c, _env))
        except Exception as _e:
            _v = False
            _c = _c + f'  [{type(_e).__name__}: {_e}]'
        if not _v:
            ok = False
            print('FAIL:', _c)
    for k, v in res.items():
        print(f"{k}: {v}")
    print("\nRESULT:", "PASS" if ok else "CHECK")


if __name__ == "__main__":
    asyncio.run(main())
