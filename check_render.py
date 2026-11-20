"""공개용 공모주 1분 요약 페이지 렌더 검증 (모바일 390x844 + 데스크톱 · 로컬)

usage: python3 work/ipo-events-public/check_render.py
data.json 을 로컬 HTTP 로 띄워 확인합니다(파일 직접 열면 fetch 가 막힘).

확인 항목
- 콘솔 에러·가로 스크롤·요소 잘림·개인정보 문구(privacy_terms.txt 의 검사어)
- UI 위계: 히어로(1레벨)가 접힌 아코디언(2레벨)보다 위, 첫 화면(844px) 안에
  오늘 청약·상장 여부 / (청약일) 균등·비례 결론·주관사별 최소증거금·유튜브 요약 /
  다음 청약 D-day — 청약 없는 상장일에도 히어로는 상장 카드 + 다음 청약 띠로 검증
- 2레벨: 기본 접힘, 머리말 '주관사 계좌가 없으신가요? · 신규 개설 혜택 N건', 탭하면 펼쳐짐
  (얇은 행 → 상세 조건·신청 방법·공식 링크)
- 증권사 신규 개설 혜택 4건 렌더, 초대 코드 슬롯 0건(누락 0 / 복사 버튼 0)
- expiresAt 이 지난 테스트 항목은 숨기고, 오늘 만료·상시 항목은 노출
- (회귀용) 코드가 들어온(ready) 항목의 복사 버튼 동작
- 오늘 요약 공유 바(.share): 히어로와 철회·출처 사이에 버튼 2개(44px 이상),
  '오늘 요약 복사' → 클립보드에 3~5줄 요약+URL · 토스트 · 라벨 '복사됐어요' 되돌림,
  '공유하기' → navigator.share 로 {title,text,url} 전달, 미지원·거부 시 요약 복사로 폴백
- 스크린샷: preview-mobile.png / preview-mobile-events.png / preview-mobile-dark.png /
  preview-desktop.png / preview-toast.png / preview-mobile-schedule*.png /
  preview-mobile-share.png / preview-mobile-share-dark.png
- 상단 2탭: 기본 '오늘 요약', 탭하면 '전체 일정'(?tab=schedule) — 두 탭 모두 390px·다크·
  데스크톱에서 가로 스크롤·잘림 없이 렌더
"""
import asyncio
import datetime as dt
import functools
import http.server
import json
import socketserver
import threading
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent
PORT = 8791
SITE_URL = "https://ipo-events-public.vercel.app"
DATA = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
IPO = DATA.get("ipo", {})
BASE = f"http://127.0.0.1:{PORT}/"
UA = ("Mozilla/5.0 (Linux; Android 14; SM-S911N) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36")
KST = dt.timezone(dt.timedelta(hours=9))

# 개인정보 검사어 — 저장소에 올리지 않는 로컬 파일(privacy_terms.txt)에서 한 줄에 하나씩 읽습니다.
_TERMS_FILE = ROOT / "privacy_terms.txt"
PRIVACY_TERMS = ([ln.strip() for ln in _TERMS_FILE.read_text(encoding="utf-8").splitlines()
                  if ln.strip() and not ln.startswith("#")] if _TERMS_FILE.exists() else [])
TODAY = dt.datetime.now(KST).date()

# 개인정보 검사어가 없어도 항상 검사하는 기본 문구
ALWAYS_TERMS = ["야탑", "판교", "이매", "쌍둥이", "육아", "어린이집", "휴대폰", "배송지"]


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


async def opt_text(page, sel, default=""):
    """없을 수 있는 요소 — 없으면 타임아웃 대신 기본값(청약일·상장일 공용)."""
    loc = page.locator(sel)
    if await loc.count() == 0:
        return default
    return (await loc.first.inner_text()).replace("\n", " ")


def test_events():
    """만료/오늘/상시/코드보유 상태를 함께 확인할 테스트 항목."""
    return [
        {
            "id": "test-expired",
            "type": "테스트",
            "title": "만료된 테스트 항목",
            "provider": "테스트증권 · 계좌",
            "benefit": "이 카드는 화면에 나오면 안 됩니다",
            "period": "2026.10.01~11.01",
            "expiresAt": "2026-11-01",
            "invite": {"status": "none"},
            "link": {"label": "x", "url": "https://example.com/"},
        },
        {
            "id": "test-today",
            "type": "테스트",
            "title": "오늘까지 유효한 테스트 항목",
            "provider": "테스트증권 · 계좌",
            "benefit": "오늘 마감 항목은 노출되어야 합니다",
            "period": f"{TODAY.isoformat()} 까지",
            "expiresAt": TODAY.isoformat(),
            "invite": {"status": "none"},
            "link": {"label": "x", "url": "https://example.com/"},
        },
        {
            "id": "test-always",
            "type": "테스트",
            "title": "상시 테스트 항목",
            "provider": "테스트증권 · 계좌",
            "benefit": "expiresAt 이 null 이면 상시로 노출됩니다",
            "period": "상시",
            "expiresAt": None,
            "invite": {"status": "none"},
        },
        {
            "id": "test-ready",
            "type": "테스트",
            "title": "코드가 들어온 테스트 항목",
            "provider": "테스트증권 · 계좌",
            "benefit": "복사 버튼이 동작해야 합니다",
            "period": "상시",
            "expiresAt": None,
            "invite": {"status": "ready", "code": "HUI1234"},
        },
    ]


def subscribe_day(body):
    """청약일 화면 — 요약문이 '오늘 청약' 분기로 바뀌는지 보는 테스트 데이터."""
    body = json.loads(json.dumps(body))
    ipo = body.setdefault("ipo", {})
    ipo["subscribe"] = [
        {"name": "케이엠에프", "badge": "오늘 청약", "market": "코스닥",
         "price": "확정 16,000원", "period": "11/20(금)~11/21(토)",
         "refund": "11/25(화)", "brokers": "IBK투자증권"},
        {"name": "신영스팩12호", "badge": "오늘 청약", "market": "코스닥",
         "price": "확정 2,000원", "period": "11/20(금)~11/21(토)",
         "refund": "11/25(화)", "brokers": "신영증권"},
    ]
    ipo["listing"] = {"hasListing": False}
    return body


async def open_page(browser, inject=None, path="", init_script=None, mutate=None, **ctx_kw):
    ctx_args = dict(
        viewport={"width": 390, "height": 844},
        device_scale_factor=2,
        is_mobile=True,
        has_touch=True,
        user_agent=UA,
        locale="ko-KR",
        timezone_id="Asia/Seoul",
        permissions=["clipboard-read", "clipboard-write"],
    )
    ctx_args.update(ctx_kw)
    ctx = await browser.new_context(**ctx_args)
    page = await ctx.new_page()
    errors = []
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}")
            if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    if init_script:
        await page.add_init_script(init_script)

    if inject or mutate:
        async def handler(route):
            resp = await route.fetch()
            body = await resp.json()
            if inject:
                body["events"] = body.get("events", []) + inject
            if mutate:
                body = mutate(body)
            await route.fulfill(status=200, response=resp,
                                body=json.dumps(body, ensure_ascii=False))
        await page.route("**/data.json*", handler)

    await page.goto(BASE + path, wait_until="networkidle")
    await page.wait_for_selector("#main:not([hidden])", timeout=8000)
    await page.wait_for_timeout(300)
    return ctx, page, errors


async def main():
    httpd = serve()
    results = {}
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()

            # ── 1. 실제 데이터 그대로 (모바일) ─────────────────────
            ctx, page, errors = await open_page(browser)
            results["title"] = await page.title()
            results["h1"] = (await page.inner_text("h1")).replace("\n", " ")
            results["dateline"] = await page.inner_text("#dateline")
            results["hero_count"] = await page.locator(".hero").count()
            results["hero_name"] = await page.inner_text(".hero .hname")
            results["flags"] = await page.eval_on_selector_all(
                ".hero .flag", "els => els.map(e => e.textContent.trim())")
            # 청약일(청약 카드) / 상장일(상장 카드) / 둘 다 없는 날을 모두 견디도록
            results["hero_kind"] = await page.evaluate("""(() => {
                const h = document.querySelector('.hero');
                if (!h) return 'none';
                if (h.classList.contains('is-list')) return 'listing';
                if (h.classList.contains('is-empty')) return 'empty';
                return 'subscribe';
            })()""")
            results["verdict_label"] = await opt_text(page, ".hero .vk")
            results["verdict_pills"] = await page.eval_on_selector_all(
                ".hero .vbig", "els => els.map(e => e.textContent.trim())")
            results["deposit"] = await opt_text(page, ".hero .deposit")
            results["listing_points"] = await page.locator(".hero .pts li").count()
            results["yt_rows"] = await page.eval_on_selector_all(
                ".hero .yt-row", "els => els.map(e => e.textContent.replace(/\\s+/g,' ').trim())")
            results["next_line"] = (await page.inner_text(".hero-next")).replace("\n", " ")
            results["next_dday"] = await page.inner_text(".hero-next .dday")
            results["next_rows"] = await page.eval_on_selector_all(
                ".hero-next .nk", "els => els.map(e => e.textContent.trim())")

            # 위계: 히어로가 아코디언보다 위 + 히어로가 첫 화면 안에
            hierarchy = await page.evaluate("""(() => {
                const hero = document.querySelector('#sec-ipo').getBoundingClientRect();
                const ben = document.querySelector('#sec-events').getBoundingClientRect();
                const next = document.querySelector('.hero-next').getBoundingClientRect();
                return {
                    hero_top: Math.round(hero.top), hero_bottom: Math.round(hero.bottom),
                    benefits_top: Math.round(ben.top), next_bottom: Math.round(next.bottom),
                    viewport_h: window.innerHeight
                };
            })()""")
            results.update(hierarchy)
            results["hierarchy_ok"] = (
                hierarchy["hero_bottom"] <= hierarchy["benefits_top"]
                and hierarchy["next_bottom"] <= hierarchy["viewport_h"])

            # ── 오늘 요약 공유 바(.share) ──────────────────
            share = page.locator("#share")
            results["share_visible"] = await share.is_visible()
            results["share_label"] = (await page.inner_text("#share .share-lab")).strip()
            results["share_btns"] = await page.eval_on_selector_all(
                "#share .share-btn", "els => els.map(e => e.textContent.replace(/\\s+/g,' ').trim())")
            results["share_btn_h"] = await page.eval_on_selector_all(
                "#share .share-btn", "els => els.map(e => Math.round(e.getBoundingClientRect().height))")
            results["share_pos"] = await page.evaluate("""(() => {
                const r = s => document.querySelector(s).getBoundingClientRect();
                return { hero: Math.round(r('#sec-ipo').bottom), share: Math.round(r('#share').top),
                         foot: Math.round(r('#ipo-foot').top),
                         benefits: Math.round(r('#sec-events').top) };
            })()""")
            pos = results["share_pos"]
            results["share_placed_ok"] = (pos["hero"] <= pos["share"]
                                         and pos["share"] <= pos["foot"]
                                         and pos["foot"] <= pos["benefits"])
            results["share_native"] = await page.evaluate("typeof navigator.share")
            await share.screenshot(path=str(ROOT / "preview-mobile-share.png"))

            # '오늘 요약 복사' → 클립보드 3~5줄 + URL, 토스트, 라벨 되돌림
            await page.locator("#share [data-share='copy']").click()
            await page.wait_for_timeout(350)
            clip = await page.evaluate("navigator.clipboard.readText()")
            results["share_clipboard"] = clip
            lines = clip.split("\n")
            results["share_lines"] = len(lines)
            results["share_line_head"] = lines[0]
            results["share_last_line"] = lines[-1]
            results["share_copy_toast"] = await page.inner_text("#toast")
            results["share_copy_label"] = (await page.inner_text("#share [data-share='copy']")).strip()
            await page.wait_for_timeout(1900)
            results["share_copy_label_back"] = (
                await page.inner_text("#share [data-share='copy']")).strip()

            # 요약문 내용 — 오늘 청약/상장·철회·다음 청약·URL
            subs = IPO.get("subscribe") or []
            listing = (IPO.get("listing") or {})
            cancel = (IPO.get("cancelled") or [{}])[0]
            nxt = IPO.get("next") or {}
            want = [SITE_URL]
            if subs:
                want.append(subs[0]["name"])
            else:
                want.append("오늘 청약 없음")
                if nxt.get("name"):
                    want.append(nxt["name"])
            if listing.get("hasListing"):
                want.append(listing["name"])
            if cancel.get("name"):
                want.append(cancel["name"])
            results["share_text_has"] = {w: (w in clip) for w in want}
            results["share_text_ok"] = all(w in clip for w in want)
            terms_all = PRIVACY_TERMS + ALWAYS_TERMS
            results["share_privacy_hits"] = [t for t in terms_all if t in clip]

            # '공유하기' — navigator.share 없는 환경(헤드리스)은 요약 복사로 폴백
            await page.evaluate("navigator.clipboard.writeText('')")
            await page.locator("#share [data-share='share']").click()
            await page.wait_for_timeout(400)
            results["share_fallback_toast"] = await page.inner_text("#toast")
            results["share_fallback_clipboard"] = (
                await page.evaluate("navigator.clipboard.readText()")) == clip
            results["share_fallback_label"] = (
                await page.inner_text("#share [data-share='share']")).strip()

            # ── 상단 2탭: 기본은 오늘 요약, ?tab=schedule 로 전체 일정 ──
            results["tabs_visible"] = await page.locator("#tabs").is_visible()
            results["tab_labels"] = await page.eval_on_selector_all(
                "#tabs .tab", "els => els.map(e => e.textContent.trim())")
            results["tab_count"] = await page.locator("#tabs .tab").count()
            results["tab_default_today"] = await page.evaluate("""(() => {
                const t = document.querySelector('#tab-today'), s = document.querySelector('#tab-schedule');
                return t.classList.contains('is-on') && t.getAttribute('aria-selected') === 'true'
                    && !s.classList.contains('is-on')
                    && !document.querySelector('#panel-today').hidden
                    && document.querySelector('#panel-schedule').hidden;
            })()""")
            results["tab_height"] = round(await page.evaluate(
                "document.querySelector('#tabs .tab').getBoundingClientRect().height"))

            # 2레벨: 기본 접힘 → 탭하면 펼침
            results["accordion_open_by_default"] = await page.locator("#sec-events").evaluate(
                "el => el.open")
            results["ev_visible_before"] = await page.locator("#ev-list .ev").first.is_visible()
            results["ben_head"] = (await page.inner_text("#sec-events .ben-txt")).replace("\n", " ")

            # 이벤트 수·초대 코드 0건
            results["events"] = await page.locator("#ev-list .ev").count()
            results["invite_missing"] = await page.locator(".ev-code.is-pending").count()
            results["invite_none"] = await page.locator(".ev-code.is-none").count()
            results["copy_buttons"] = await page.locator(".ev-code .copy").count()
            results["always_badges"] = await page.locator(".ev-dday.is-always").count()
            results["ev_note"] = (await page.locator("#ev-note").text_content()).strip()
            results["event_ids"] = await page.eval_on_selector_all(
                "#ev-list .ev", "els => els.map(e => e.dataset.id)")

            await page.screenshot(path=str(ROOT / "preview-mobile.png"), full_page=True)
            await page.screenshot(path=str(ROOT / "preview-mobile-first-screen.png"))

            # 아코디언 펼치기 → 얇은 행 → 행 상세 펼치기
            await page.locator("#sec-events > summary").click()
            await page.wait_for_timeout(300)
            results["accordion_open_after_click"] = await page.locator("#sec-events").evaluate(
                "el => el.open")
            results["ev_visible_after"] = await page.locator("#ev-list .ev").first.is_visible()
            first_row = page.locator("#ev-list .ev").first
            results["row_summary"] = (await first_row.locator("summary").inner_text()).replace("\n", " ")
            await first_row.locator("summary").click()
            await page.wait_for_timeout(200)
            results["row_detail_visible"] = await first_row.evaluate("el => el.open")
            results["row_has_terms"] = await first_row.locator(".ev-terms").count() > 0
            results["row_has_howto"] = (await first_row.locator(".ev-code.is-none").count()) > 0
            results["row_has_link"] = (await first_row.locator(".ev-link").count()) > 0
            await page.locator("#sec-events").screenshot(
                path=str(ROOT / "preview-mobile-events.png"))

            results["no_invite_words"] = not await page.evaluate(
                "['초대 코드','초대코드','추천인','본인 초대'].some(t => document.body.innerText.includes(t))")
            results["doc_width"] = await page.evaluate("document.documentElement.scrollWidth")
            results["viewport_width"] = await page.evaluate("window.innerWidth")
            results["h_overflow"] = results["doc_width"] > results["viewport_width"]
            terms = PRIVACY_TERMS + ALWAYS_TERMS
            results["privacy_hits"] = await page.evaluate("""terms =>
                terms.filter(t => document.body.innerText.includes(t))""", terms)
            results["privacy_terms_checked"] = len(terms)
            results["clipped"] = await page.evaluate("""
                (() => {
                  const vw = window.innerWidth, bad = [];
                  document.querySelectorAll('.hero, .hero *, .support, .support *, .share, .share *')
                    .forEach(el => {
                      if (el.closest('.sr-only')) return;
                      const r = el.getBoundingClientRect();
                      if (r.width && (r.left < -1 || r.right > vw + 1)) {
                        bad.push(el.tagName + '.' + el.className + ' ' +
                                 Math.round(r.left) + '~' + Math.round(r.right));
                      }
                    });
                  return bad.slice(0, 5);
                })()
            """)
            results["errors"] = errors

            # ── 하단 응원 카드(3레벨) ──────────────────────────
            sup = page.locator("#support")
            results["support_visible"] = await sup.is_visible()
            results["support_title"] = (await page.inner_text("#support .sup-t")).strip()
            results["support_note"] = (await page.inner_text("#support .sup-n")).strip()
            sup_a = page.locator("#support .sup-btn")
            results["support_btn_text"] = (await sup_a.inner_text()).strip()
            results["support_href"] = await sup_a.get_attribute("href")
            results["support_target"] = await sup_a.get_attribute("target")
            results["support_rel"] = await sup_a.get_attribute("rel")
            results["support_links"] = await page.locator("#support a").count()
            results["support_above_footer"] = await page.evaluate("""(() => {
                const s = document.querySelector('#support').getBoundingClientRect();
                const f = document.querySelector('#foot').getBoundingClientRect();
                return s.bottom <= f.top + 1;
            })()""")
            results["support_btn_h"] = round(await page.evaluate(
                "document.querySelector('#support .sup-btn').getBoundingClientRect().height"))
            await sup.scroll_into_view_if_needed()
            await page.wait_for_timeout(200)
            await sup.screenshot(path=str(ROOT / "preview-mobile-support.png"))
            await page.locator("#foot").scroll_into_view_if_needed()
            await page.wait_for_timeout(150)
            await page.screenshot(path=str(ROOT / "preview-mobile-bottom.png"))

            # ── 전체 일정 탭 ────────────────────────────────
            await page.locator("#tab-schedule").click()
            await page.wait_for_timeout(300)
            results["tab_switch_on"] = await page.evaluate("""(() => {
                const s = document.querySelector('#tab-schedule');
                return s.classList.contains('is-on') && s.getAttribute('aria-selected') === 'true'
                    && document.querySelector('#panel-schedule').hidden === false
                    && document.querySelector('#panel-today').hidden === true;
            })()""")
            results["tab_url"] = page.url
            results["tab_url_has_query"] = "tab=schedule" in page.url
            results["sch_counts"] = {
                "subscribe": await page.locator("#sch-subscribe .sc").count(),
                "listing": await page.locator("#sch-listing .sc").count(),
            }
            results["sch_heads"] = await page.eval_on_selector_all(
                ".sch-h", "els => els.map(e => e.textContent.replace(/\\s+/g,' ').trim())")
            results["sch_first"] = await page.evaluate("""(() => {
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
            results["sch_names"] = await page.eval_on_selector_all(
                "#sch-subscribe .sc .sc-name", "els => els.map(e => e.textContent.trim())")
            results["sch_ddays"] = await page.eval_on_selector_all(
                "#sch-subscribe .sc .sc-dd", "els => els.map(e => e.textContent.trim())")
            results["sch_list_items"] = await page.eval_on_selector_all(
                "#sch-listing .sc", "els => els.map(e => e.textContent.replace(/\\s+/g,' ').trim())")
            results["sch_src_urls"] = await page.eval_on_selector_all(
                "#sch-src a", "els => els.map(e => e.getAttribute('href'))")
            results["sch_src_text"] = (await page.inner_text("#sch-src")).replace("\n", " ")
            results["sch_cancel_text"] = (await page.inner_text(".sch-cancel")).replace("\n", " ")
            results["sch_has_38"] = "38커뮤니케이션" in await page.evaluate("document.body.innerText")
            results["sch_doc_width"] = await page.evaluate("document.documentElement.scrollWidth")
            results["sch_h_overflow"] = results["sch_doc_width"] > results["viewport_width"]
            results["sch_clipped"] = await page.evaluate("""
                (() => {
                  const vw = window.innerWidth, bad = [];
                  document.querySelectorAll('#panel-schedule .sc, #panel-schedule .sc *, #panel-schedule .sch-cancel *')
                    .forEach(el => {
                      const r = el.getBoundingClientRect();
                      if (r.width && (r.left < -1 || r.right > vw + 1)) {
                        bad.push(el.tagName + '.' + el.className + ' ' +
                                 Math.round(r.left) + '~' + Math.round(r.right));
                      }
                    });
                  return bad.slice(0, 5);
                })()
            """)
            await page.screenshot(path=str(ROOT / "preview-mobile-schedule.png"), full_page=True)
            await page.screenshot(path=str(ROOT / "preview-mobile-schedule-first.png"))
            await page.locator("#sch-src").scroll_into_view_if_needed()
            await page.wait_for_timeout(200)
            await page.screenshot(path=str(ROOT / "preview-mobile-schedule-bottom.png"))

            # 전체 일정 화면에서 개인정보 문구가 새지 않는지 한 번 더
            results["sch_privacy_hits"] = await page.evaluate("""terms =>
                terms.filter(t => document.body.innerText.includes(t))""", terms)
            results["sch_errors"] = errors

            # 탭을 되돌리면 다시 오늘 요약(1레벨)이 보인다
            await page.locator("#tab-today").click()
            await page.wait_for_timeout(250)
            results["tab_back_today"] = await page.evaluate("""(() => {
                return !document.querySelector('#panel-today').hidden
                    && document.querySelector('#panel-schedule').hidden
                    && document.querySelector('#tab-today').classList.contains('is-on');
            })()""")
            results["tab_back_url"] = page.url
            await ctx.close()

            # ── 2. 만료/오늘/상시/코드보유 테스트 주입 ────────────
            ctx2, page2, errors2 = await open_page(browser, inject=test_events())
            await page2.locator("#sec-events > summary").click()
            await page2.wait_for_timeout(250)
            results["inject_events"] = await page2.locator("#ev-list .ev").count()
            results["inject_ids"] = await page2.eval_on_selector_all(
                "#ev-list .ev", "els => els.map(e => e.dataset.id)")
            body = await page2.evaluate("document.body.textContent")
            results["expired_hidden"] = "만료된 테스트 항목" not in body
            results["today_shown"] = "오늘까지 유효한 테스트 항목" in body
            results["always_shown"] = "상시 테스트 항목" in body
            results["note_mentions_hidden"] = "1건은 자동으로 숨겼어요" in await page2.locator(
                "#ev-note").text_content()
            results["inject_errors"] = errors2
            results["ready_dday"] = await page2.locator(
                ".ev[data-id='test-today'] .ev-dday").inner_text()

            # 코드가 들어온 항목의 복사 경로
            ready = page2.locator(".ev[data-id='test-ready']")
            await ready.locator("summary").click()
            await page2.wait_for_timeout(150)
            await ready.locator(".copy").click()
            await page2.wait_for_timeout(350)
            results["copy_toast"] = await page2.inner_text("#toast")
            results["clipboard"] = await page2.evaluate("navigator.clipboard.readText()")
            await page2.screenshot(path=str(ROOT / "preview-toast.png"))
            await ctx2.close()

            # ── 2.5 공유 시트(navigator.share) 경로 ──────────
            sctx, spage, s_errors = await open_page(browser, init_script="""
                window.__shared = null;
                navigator.share = function (d) { window.__shared = d; return Promise.resolve(); };
            """)
            results["stub_share_type"] = await spage.evaluate("typeof navigator.share")
            await spage.locator("#share [data-share='share']").click()
            await spage.wait_for_timeout(300)
            results["shared_payload"] = await spage.evaluate("window.__shared")
            results["stub_share_label"] = (
                await spage.inner_text("#share [data-share='share']")).strip()
            results["stub_errors"] = s_errors
            await sctx.close()

            # 공유가 거부(reject)되면 조용히 죽지 않고 요약 복사로 폴백
            rctx, rpage, r_errors = await open_page(browser, init_script="""
                navigator.share = function () {
                    const e = new Error('denied'); e.name = 'NotAllowedError';
                    return Promise.reject(e);
                };
            """)
            await rpage.locator("#share [data-share='share']").click()
            await rpage.wait_for_timeout(450)
            results["share_reject_toast"] = await rpage.inner_text("#toast")
            results["share_reject_clipboard"] = (
                "직장인 1분 공모주 요약" in await rpage.evaluate("navigator.clipboard.readText()"))
            results["reject_errors"] = r_errors
            await rctx.close()

            # ── 2.6 청약일 요약 — '오늘 청약' 분기 ─────────────
            vctx, vpage, v_errors = await open_page(browser, mutate=subscribe_day)
            await vpage.wait_for_timeout(250)
            await vpage.locator("#share [data-share='copy']").click()
            await vpage.wait_for_timeout(350)
            vclip = await vpage.evaluate("navigator.clipboard.readText()")
            results["sub_clipboard"] = vclip
            results["sub_lines"] = len(vclip.split("\n"))
            results["sub_line2"] = vclip.split("\n")[1] if len(vclip.split("\n")) > 1 else ""
            results["sub_last"] = vclip.split("\n")[-1]
            results["sub_has_next"] = "다음 청약" in vclip
            results["sub_errors"] = v_errors
            await vctx.close()

            # ── 3. 다크 모드 ──────────────────────────────
            dark, dpage, dark_errors = await open_page(browser, color_scheme="dark")
            await dpage.screenshot(path=str(ROOT / "preview-mobile-dark.png"), full_page=True)
            results["dark_page_h"] = await dpage.evaluate("document.documentElement.scrollHeight")
            results["dark_share_visible"] = await dpage.locator("#share").is_visible()
            results["dark_share_btns"] = await dpage.eval_on_selector_all(
                "#share .share-btn", "els => els.map(e => Math.round(e.getBoundingClientRect().height))")
            results["dark_share_overflow"] = await dpage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            await dpage.locator("#share").scroll_into_view_if_needed()
            await dpage.wait_for_timeout(150)
            await dpage.locator("#share").screenshot(
                path=str(ROOT / "preview-mobile-share-dark.png"))
            results["dark_errors"] = dark_errors
            await dpage.locator("#tab-schedule").click()
            await dpage.wait_for_timeout(300)
            results["dark_sch_visible"] = await dpage.locator("#panel-schedule").is_visible()
            results["dark_sch_cards"] = await dpage.locator("#sch-subscribe .sc").count()
            results["dark_sch_overflow"] = await dpage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            await dpage.screenshot(path=str(ROOT / "preview-mobile-schedule-dark.png"), full_page=True)
            await dark.close()

            # ── 4. 데스크톱 1280 ──────────────────────────────
            desk, dp, desk_errors = await open_page(
                browser, viewport={"width": 1280, "height": 900},
                is_mobile=False, has_touch=False, device_scale_factor=1,
                permissions=[])
            results["desktop_hero"] = await dp.locator(".hero").count()
            results["desktop_events"] = await dp.locator("#ev-list .ev").count()
            results["desktop_share_visible"] = await dp.locator("#share").is_visible()
            results["desktop_share_labels"] = await dp.eval_on_selector_all(
                "#share .share-btn", "els => els.map(e => e.textContent.replace(/\\s+/g,' ').trim())")
            results["desktop_h_overflow"] = await dp.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            results["desktop_errors"] = desk_errors
            await dp.screenshot(path=str(ROOT / "preview-desktop.png"))
            await dp.locator("#tab-schedule").click()
            await dp.wait_for_timeout(300)
            results["desktop_sch_cards"] = await dp.locator("#sch-subscribe .sc").count()
            results["desktop_sch_overflow"] = await dp.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            await dp.screenshot(path=str(ROOT / "preview-desktop-schedule.png"), full_page=True)
            await desk.close()

            # ── 5. ?tab=schedule 딥링크 ──────────────────────
            deepl, lpage, _ = await open_page(browser, path="?tab=schedule")
            results["deeplink_schedule"] = await lpage.locator("#panel-schedule").is_visible()
            results["deeplink_cards"] = await lpage.locator("#sch-subscribe .sc").count()
            await deepl.close()

            await browser.close()
    finally:
        httpd.shutdown()

    # 청약일이면 결론·최소증거금·유튜브 요약, 상장일이면 상장 포인트를 확인
    hero_ok = ((results["hero_kind"] == "subscribe"
                and bool(results["verdict_pills"])
                and results["deposit"].startswith("주관사별 최소증거금")
                and len(results["yt_rows"]) >= 2)
               or (results["hero_kind"] == "listing" and results["listing_points"] >= 1)
               or (results["hero_kind"] == "empty" and bool(results["next_rows"])))

    ok = (results["events"] == 4
          and results["tabs_visible"]
          and results["tab_count"] == 2
          and results["tab_labels"] == ["오늘 요약", "전체 일정"]
          and results["tab_default_today"]
          and results["tab_height"] >= 40
          and results["tab_switch_on"]
          and results["tab_url_has_query"]
          and results["sch_counts"]["subscribe"] >= 10
          and results["sch_counts"]["listing"] >= 1
          and results["sch_first"] and results["sch_first"]["dday"].startswith("D-")
          and results["sch_first"]["when"].endswith("청약")
          and "희망" in (results["sch_first"]["price"] or "")
          and results["sch_first"]["sub"] and "증권" in results["sch_first"]["sub"]
          and all(d.startswith("D-") or d in ("청약 중", "청약 종료") for d in results["sch_ddays"])
          and len(results["sch_list_items"]) >= 1
          and all("상장" in it for it in results["sch_list_items"])
          and any("38.co.kr" in (u or "") for u in results["sch_src_urls"])
          and results["sch_has_38"]
          and not results["sch_h_overflow"]
          and not results["sch_clipped"]
          and not results["sch_privacy_hits"]
          and not results["sch_errors"]
          and results["tab_back_today"]
          and results["dark_sch_visible"]
          and not results["dark_sch_overflow"]
          and results["desktop_sch_cards"] >= 10
          and not results["desktop_sch_overflow"]
          and results["deeplink_schedule"]
          and results["deeplink_cards"] >= 10
          # 오늘 요약 공유 바
          and results["share_visible"]
          and results["share_label"].startswith("단톡방에")
          and len(results["share_btns"]) == 2
          and "오늘 요약 복사" in results["share_btns"][0]
          and results["share_btns"][1].endswith("공유하기")
          and min(results["share_btn_h"]) >= 40
          and results["share_placed_ok"]
          and results["share_native"] == "undefined"
          and 3 <= results["share_lines"] <= 5
          and results["share_line_head"].startswith("📈 직장인 1분 공모주 요약")
          and results["share_last_line"] == SITE_URL
          and results["share_text_ok"]
          and not results["share_privacy_hits"]
          and "복사" in results["share_copy_toast"]
          and results["share_copy_label"] == "복사됐어요"
          and results["share_copy_label_back"].endswith("오늘 요약 복사")
          and results["share_fallback_clipboard"]
          and "복사" in results["share_fallback_toast"]
          and results["stub_share_type"] == "function"
          and results["sub_lines"] == 4
          and results["sub_line2"].startswith("• 오늘 청약 케이엠에프 16,000원")
          and results["sub_line2"].endswith("외 1건")
          and not results["sub_has_next"]
          and results["sub_last"] == SITE_URL
          and not results["sub_errors"]
          and bool(results["shared_payload"])
          and results["shared_payload"].get("url") == SITE_URL
          and results["shared_payload"].get("title") == "오늘의 공모주 1분 요약"
          and "직장인 1분 공모주 요약" in (results["shared_payload"].get("text") or "")
          and SITE_URL not in (results["shared_payload"].get("text") or "")
          and "복사" in results["share_reject_toast"]
          and results["share_reject_clipboard"]
          and results["dark_share_visible"]
          and min(results["dark_share_btns"]) >= 40
          and not results["dark_share_overflow"]
          and results["desktop_share_visible"]
          and len(results["desktop_share_labels"]) == 2
          and not results["stub_errors"]
          and not results["reject_errors"]
          and results["invite_missing"] == 0
          and results["invite_none"] == 4
          and results["copy_buttons"] == 0
          and results["hero_count"] == 1
          and hero_ok
          and "다음 청약" in results["next_rows"]
          and results["next_dday"].startswith("D-")
          and results["hierarchy_ok"]
          and not results["accordion_open_by_default"]
          and not results["ev_visible_before"]
          and results["accordion_open_after_click"]
          and results["ev_visible_after"]
          and results["row_detail_visible"]
          and results["row_has_terms"]
          and results["row_has_howto"]
          and results["row_has_link"]
          and results["no_invite_words"]
          and results["inject_events"] == 7
          and results["expired_hidden"]
          and results["today_shown"]
          and results["always_shown"]
          and results["note_mentions_hidden"]
          and results["clipboard"] == "HUI1234"
          and not results["errors"]
          and results["support_visible"]
          and results["support_title"].endswith("커피 한 잔 응원하기")
          and results["support_href"] == "https://qr.kakaopay.com/Ej7j2Gwco"
          and results["support_target"] == "_blank"
          and "noopener" in (results["support_rel"] or "")
          and "noreferrer" in (results["support_rel"] or "")
          and results["support_links"] == 1
          and results["support_above_footer"]
          and results["support_btn_h"] >= 36
          and not results["inject_errors"]
          and not results["dark_errors"]
          and not results["desktop_errors"]
          and not results["h_overflow"]
          and not results["clipped"]
          and not results["privacy_hits"]
          and not results["desktop_h_overflow"])
    for k, v in results.items():
        print(f"{k}: {v}")
    print("\nRESULT:", "PASS" if ok else "CHECK")


if __name__ == "__main__":
    asyncio.run(main())
