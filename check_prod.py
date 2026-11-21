"""배포된 공개 페이지 검증 (프로덕션 URL · 익명 모바일 390x844 + 데스크톱).

공유·복사 기대값은 로컬 검증(check_render.py)과 같은 규칙 함수로 계산합니다.
"""
import asyncio
import datetime as dt
from pathlib import Path

from playwright.async_api import async_playwright

from check_render import (expected_copy, expected_listing_copy, IOS_UA, DESKTOP_UA,  # 공유문 기대값 규칙 공유
                          cash_plan, cash_peak_text, cash_row_text, short_day, won_short)

URL = "https://ipo.mydon.kr/"
SITE_URL = "https://ipo.mydon.kr"
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

        res["title"] = await page.title()
        res["brand"] = (await page.inner_text(".brand")).replace("\n", " ").strip()
        res["brand_nowrap"] = await page.evaluate(
            "getComputedStyle(document.querySelector('.brand')).whiteSpace")
        res["og_title"] = await page.get_attribute("meta[property='og:title']", "content")
        res["og_site_name"] = await page.get_attribute("meta[property='og:site_name']", "content")
        res["css_href"] = await page.get_attribute(
            "link[rel='stylesheet'][href*='styles.css']", "href")
        res["js_src"] = await page.get_attribute("script[src*='app.js']", "src")
        # 배포 후 캐시 헤더 — styles.css·app.js 는 60초 캐시(_headers)
        res["css_cache_control"] = (await page.request.get(SITE_URL + "/styles.css")).headers.get(
            "cache-control", "")
        res["js_cache_control"] = (await page.request.get(SITE_URL + "/app.js")).headers.get(
            "cache-control", "")
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

        dark = await browser.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
            has_touch=True, user_agent=UA, locale="ko-KR", timezone_id="Asia/Seoul",
            color_scheme="dark")
        dpage = await dark.new_page()
        await dpage.goto(URL, wait_until="networkidle", timeout=45000)
        await dpage.wait_for_selector("#main:not([hidden])", timeout=15000)
        await dpage.wait_for_timeout(300)
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
        await dark.close()

        # 데스크톱 폭에서도 확인
        desk = await browser.new_context(viewport={"width": 1280, "height": 900},
                                        locale="ko-KR", timezone_id="Asia/Seoul")
        dp = await desk.new_page()
        await dp.goto(URL, wait_until="networkidle", timeout=45000)
        await dp.wait_for_selector("#main:not([hidden])", timeout=15000)
        await dp.wait_for_timeout(300)
        res["desktop_hero"] = await dp.locator(".hero").count()
        res["desktop_share_visible"] = await dp.locator("#share").is_visible()
        res["desktop_share_labels"] = await dp.eval_on_selector_all(
            "#share .share-btn .lbl", "els => els.map(e => e.textContent.trim())")
        res["desktop_ben_link"] = await dp.locator("#ben-link").is_visible()
        res["desktop_h_overflow"] = await dp.evaluate(
            "document.documentElement.scrollWidth > window.innerWidth + 1")
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
        await lp.goto(URL + "?tab=schedule", wait_until="networkidle", timeout=45000)
        await lp.wait_for_selector("#main:not([hidden])", timeout=15000)
        await lp.wait_for_timeout(300)
        res["deeplink_schedule"] = await lp.locator("#panel-schedule").is_visible()
        res["deeplink_cards"] = await lp.locator("#sch-subscribe .sc").count()
        await deepl.close()
        deeplb = await browser.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
            has_touch=True, user_agent=UA, locale="ko-KR", timezone_id="Asia/Seoul")
        bp = await deeplb.new_page()
        await bp.goto(URL + "?tab=benefits", wait_until="networkidle", timeout=45000)
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
        await ip.goto(URL, wait_until="networkidle", timeout=45000)
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
        await dsp.goto(URL, wait_until="networkidle", timeout=45000)
        await dsp.wait_for_selector("#main:not([hidden])", timeout=15000)
        await dsp.wait_for_timeout(300)
        res["desktop_app_btns"] = await dsp.eval_on_selector_all(
            ".hero .app-open",
            "els => els.map(e => ({ text: e.textContent.replace(/\\s+/g, ' ').trim(),"
            " href: e.getAttribute('href'), target: e.getAttribute('target'),"
            " rel: e.getAttribute('rel') || '' }))")
        await dctx.close()
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
        '"max-age=60" in res["css_cache_control"]',
        '"must-revalidate" in res["css_cache_control"]',
        '"max-age=60" in res["js_cache_control"]',
        '"must-revalidate" in res["js_cache_control"]',
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
        'res["support_visible"]',
        'res["support_href"] == "https://qr.kakaopay.com/Ej7j2Gwco"',
        'res["support_target"] == "_blank"',
        '"noopener" in (res["support_rel"] or "")',
        'res["support_above_footer"]',
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
