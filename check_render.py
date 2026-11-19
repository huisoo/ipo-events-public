"""공개용 공모주 1분 요약 페이지 렌더 검증 (모바일 390x844 + 데스크톱 · 로컬)

usage: python3 work/ipo-events-public/check_render.py
data.json 을 로컬 HTTP 로 띄워 확인합니다(파일 직접 열면 fetch 가 막힘).

확인 항목
- 콘솔 에러·가로 스크롤·요소 잘림·개인정보 문구(privacy_terms.txt 의 검사어)
- UI 위계: 히어로(1레벨)가 접힌 아코디언(2레벨)보다 위, 첫 화면(844px) 안에
  오늘 청약·상장 여부 / 균등·비례 결론 / 주관사별 최소증거금 / 유튜브 요약 / 다음 청약 D-day
- 2레벨: 기본 접힘, 머리말 '주관사 계좌가 없으신가요? · 신규 개설 혜택 N건', 탭하면 펼쳐짐
  (얇은 행 → 상세 조건·신청 방법·공식 링크)
- 증권사 신규 개설 혜택 4건 렌더, 초대 코드 슬롯 0건(누락 0 / 복사 버튼 0)
- expiresAt 이 지난 테스트 항목은 숨기고, 오늘 만료·상시 항목은 노출
- (회귀용) 코드가 들어온(ready) 항목의 복사 버튼 동작
- 스크린샷: preview-mobile.png / preview-mobile-events.png / preview-mobile-dark.png /
  preview-desktop.png / preview-toast.png
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


async def open_page(browser, inject=None, **ctx_kw):
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

    if inject:
        async def handler(route):
            resp = await route.fetch()
            body = await resp.json()
            body["events"] = body.get("events", []) + inject
            await route.fulfill(status=200, response=resp,
                                body=json.dumps(body, ensure_ascii=False))
        await page.route("**/data.json*", handler)

    await page.goto(BASE, wait_until="networkidle")
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
            results["verdict_label"] = await page.inner_text(".hero .vk")
            results["verdict_pills"] = await page.eval_on_selector_all(
                ".hero .vbig", "els => els.map(e => e.textContent.trim())")
            results["deposit"] = (await page.inner_text(".hero .deposit")).replace("\n", " ")
            results["yt_rows"] = await page.eval_on_selector_all(
                ".hero .yt-row", "els => els.map(e => e.textContent.replace(/\\s+/g,' ').trim())")
            results["next_line"] = (await page.inner_text(".hero-next")).replace("\n", " ")
            results["next_dday"] = await page.inner_text(".hero-next .dday")

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
                  document.querySelectorAll('.hero, .hero *', )
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

            # ── 3. 다크 모드 ───────────────────────────────────
            dark, dpage, dark_errors = await open_page(browser, color_scheme="dark")
            await dpage.screenshot(path=str(ROOT / "preview-mobile-dark.png"), full_page=True)
            results["dark_page_h"] = await dpage.evaluate("document.documentElement.scrollHeight")
            results["dark_errors"] = dark_errors
            await dark.close()

            # ── 4. 데스크톱 1280 ───────────────────────────────
            desk, dp, desk_errors = await open_page(
                browser, viewport={"width": 1280, "height": 900},
                is_mobile=False, has_touch=False, device_scale_factor=1,
                permissions=[])
            results["desktop_hero"] = await dp.locator(".hero").count()
            results["desktop_events"] = await dp.locator("#ev-list .ev").count()
            results["desktop_h_overflow"] = await dp.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            results["desktop_errors"] = desk_errors
            await dp.screenshot(path=str(ROOT / "preview-desktop.png"))
            await desk.close()
            await browser.close()
    finally:
        httpd.shutdown()

    ok = (results["events"] == 4
          and results["invite_missing"] == 0
          and results["invite_none"] == 4
          and results["copy_buttons"] == 0
          and results["hero_count"] == 1
          and results["verdict_pills"]
          and results["deposit"].startswith("주관사별 최소증거금")
          and len(results["yt_rows"]) >= 2
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
