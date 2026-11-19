"""공개용 공모주·증권사 혜택 페이지 렌더 검증 (390x844 · 로컬)

usage: python3 work/ipo-events-public/check_render.py
data.json 을 로컬 HTTP 로 띄워 확인합니다(파일 직접 열면 fetch 가 막힘).

확인 항목
- 콘솔 에러·가로 스크롤·요소 잘림·개인정보 문구(privacy_terms.txt 의 검사어)
- 증권사 신규 개설 혜택 4건 렌더, 초대 코드 슬롯 0건(누락 0 / 복사 버튼 0)
- 화면에 '초대 코드·추천인' 문구가 남지 않았는지
- expiresAt 이 지난 테스트 항목은 숨기고, 오늘 만료·상시 항목은 노출
- (회귀용) 코드가 들어온(ready) 항목의 복사 버튼 동작
- 스크린샷: preview-mobile.png / preview-mobile-events.png / preview-mobile-dark.png / preview-toast.png
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
            "benefit": "expiresAt 이 null 이면 상시로 노출됩니다",
            "period": "상시",
            "expiresAt": None,
            "invite": {"status": "none"},
        },
        {
            "id": "test-ready",
            "type": "테스트",
            "title": "코드가 들어온 테스트 항목",
            "benefit": "복사 버튼이 동작해야 합니다",
            "period": "상시",
            "expiresAt": None,
            "invite": {"status": "ready", "code": "HUI1234"},
        },
    ]


async def run_once(browser, inject=None):
    ctx = await browser.new_context(
        viewport={"width": 390, "height": 844},
        device_scale_factor=2,
        is_mobile=True,
        has_touch=True,
        user_agent=UA,
        locale="ko-KR",
        timezone_id="Asia/Seoul",
        permissions=["clipboard-read", "clipboard-write"],
    )
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
    errors_ok = errors
    return ctx, page, errors_ok


async def main():
    httpd = serve()
    results = {}
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()

            # ── 1. 실제 데이터 그대로 ─────────────────────────────
            ctx, page, errors = await run_once(browser)
            results["title"] = await page.title()
            results["dateline"] = await page.inner_text("#dateline")
            results["ipo_cards"] = await page.locator(".pcard").count()
            results["events"] = await page.locator(".ev").count()
            results["invite_missing"] = await page.locator(".ev-code.is-pending").count()
            results["invite_none"] = await page.locator(".ev-code.is-none").count()
            results["copy_buttons"] = await page.locator(".ev-code .copy").count()
            results["always_badges"] = await page.locator(".ev-dday.is-always").count()
            results["howto_label"] = await page.locator(
                ".ev-code.is-none .inv-state").first.inner_text()
            results["no_invite_words"] = not await page.evaluate(
                "['초대 코드','초대코드','추천인','본인 초대'].some(t => document.body.innerText.includes(t))")
            results["ev_note"] = await page.inner_text("#ev-note")
            results["event_ids"] = await page.eval_on_selector_all(
                ".ev", "els => els.map(e => e.dataset.id)")
            results["doc_width"] = await page.evaluate("document.documentElement.scrollWidth")
            results["viewport_width"] = await page.evaluate("window.innerWidth")
            results["h_overflow"] = results["doc_width"] > results["viewport_width"]
            results["no_agri_terms"] = await page.evaluate(
                "terms => terms.some(t => document.body.innerText.includes(t))",
                PRIVACY_TERMS) if PRIVACY_TERMS else False
            results["privacy_terms_checked"] = len(PRIVACY_TERMS)
            results["clipped"] = await page.evaluate("""
                (() => {
                  const vw = window.innerWidth, bad = [];
                  document.querySelectorAll('.ev, .pcard, .foot, .ev-code, .copy, .inv-state, .howto')
                    .forEach(el => {
                      const r = el.getBoundingClientRect();
                      if (r.left < -1 || r.right > vw + 1) {
                        bad.push(el.className + ' ' + Math.round(r.left) + '~' + Math.round(r.right));
                      }
                    });
                  return bad;
                })()
            """)
            results["quick_chips"] = await page.locator(".qchip").count()

            await page.screenshot(path=str(ROOT / "preview-mobile.png"), full_page=True)
            await page.locator("#sec-events").scroll_into_view_if_needed()
            await page.wait_for_timeout(200)
            await page.locator("#sec-events").screenshot(
                path=str(ROOT / "preview-mobile-events.png"))

            results["errors"] = errors
            await ctx.close()

            # ── 2. 만료/오늘/상시/코드보유 테스트 주입 ────────────
            inject = test_events()
            ctx2, page2, errors2 = await run_once(browser, inject=inject)
            results["inject_events"] = await page2.locator(".ev").count()
            results["inject_ids"] = await page2.eval_on_selector_all(
                ".ev", "els => els.map(e => e.dataset.id)")
            body = await page2.inner_text("body")
            results["expired_hidden"] = "만료된 테스트 항목" not in body
            results["today_shown"] = "오늘까지 유효한 테스트 항목" in body
            results["always_shown"] = "상시 테스트 항목" in body
            results["note_mentions_hidden"] = "1건은 자동으로 숨겼어요" in await page2.inner_text("#ev-note")
            results["inject_errors"] = errors2
            results["ready_dday"] = await page2.locator(
                ".ev[data-id='test-today'] .ev-dday").inner_text()

            # 코드가 들어온 항목의 복사 경로
            await page2.locator(".ev[data-id='test-ready'] .copy").click()
            await page2.wait_for_timeout(350)
            results["copy_toast"] = await page2.inner_text("#toast")
            results["clipboard"] = await page2.evaluate("navigator.clipboard.readText()")
            await page2.screenshot(path=str(ROOT / "preview-toast.png"))
            await ctx2.close()

            # ── 3. 다크 모드 ───────────────────────────────────
            dark = await browser.new_context(
                viewport={"width": 390, "height": 844}, device_scale_factor=2,
                is_mobile=True, has_touch=True, color_scheme="dark",
                locale="ko-KR", timezone_id="Asia/Seoul")
            dpage = await dark.new_page()
            await dpage.goto(BASE, wait_until="networkidle")
            await dpage.wait_for_selector("#main:not([hidden])")
            await dpage.wait_for_timeout(300)
            await dpage.screenshot(path=str(ROOT / "preview-mobile-dark.png"), full_page=True)
            results["dark_page_h"] = await dpage.evaluate("document.documentElement.scrollHeight")
            await dark.close()
            await browser.close()
    finally:
        httpd.shutdown()

    ok = (results["events"] == 4
          and results["invite_missing"] == 0
          and results["invite_none"] == 4
          and results["copy_buttons"] == 0
          and results["howto_label"] == "신청 방법"
          and results["no_invite_words"]
          and results["inject_events"] == 7
          and results["expired_hidden"]
          and results["today_shown"]
          and results["always_shown"]
          and results["note_mentions_hidden"]
          and results["clipboard"] == "HUI1234"
          and not results["errors"]
          and not results["inject_errors"]
          and not results["h_overflow"]
          and not results["clipped"]
          and not results["no_agri_terms"])
    for k, v in results.items():
        print(f"{k}: {v}")
    print("\nRESULT:", "PASS" if ok else "CHECK")


if __name__ == "__main__":
    asyncio.run(main())
