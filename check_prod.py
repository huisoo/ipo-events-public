"""배포된 공개 페이지 검증 (프로덕션 URL · 익명 모바일 390x844 + 데스크톱)."""
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

URL = "https://ipo-events-public.vercel.app/"
OUT = Path(__file__).resolve().parent
UA = ("Mozilla/5.0 (Linux; Android 14; SM-S911N) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36")
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
            locale="ko-KR", timezone_id="Asia/Seoul")
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

        # 2레벨 접힘
        res["benefits_collapsed"] = not await page.locator("#sec-events").evaluate("el => el.open")
        res["ben_head"] = (await page.inner_text("#sec-events .ben-txt")).replace("\n", " ")
        res["events"] = await page.locator("#ev-list .ev").count()
        res["event_ids"] = await page.eval_on_selector_all("#ev-list .ev", "els => els.map(e => e.dataset.id)")
        res["ev_note"] = (await page.locator("#ev-note").text_content()).strip()

        body = await page.evaluate("document.body.textContent")
        res["has_draft_word"] = "초안" in body
        res["privacy_hits"] = [t for t in TERMS + ALWAYS_TERMS if t in body]
        res["invite_words"] = any(w in body for w in ("초대 코드", "초대코드", "추천인"))
        res["notice_count"] = await page.locator("#notice-list li").count()

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
        await page.locator("#sec-events > summary").click()
        await page.wait_for_timeout(350)
        res["accordion_opens"] = await page.locator("#sec-events").evaluate("el => el.open")
        await page.locator("#ev-list .ev").first.locator("summary").click()
        await page.wait_for_timeout(250)
        res["row_opens"] = await page.locator("#ev-list .ev").first.evaluate("el => el.open")
        await page.locator("#sec-events").screenshot(
            path=str(OUT / "preview-prod-mobile-events.png"))
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
        await dark.close()

        # 데스크톱 폭에서도 확인
        desk = await browser.new_context(viewport={"width": 1280, "height": 900},
                                        locale="ko-KR", timezone_id="Asia/Seoul")
        dp = await desk.new_page()
        await dp.goto(URL, wait_until="networkidle", timeout=45000)
        await dp.wait_for_selector("#main:not([hidden])", timeout=15000)
        await dp.wait_for_timeout(300)
        res["desktop_hero"] = await dp.locator(".hero").count()
        res["desktop_events"] = await dp.locator("#ev-list .ev").count()
        res["desktop_h_overflow"] = await dp.evaluate(
            "document.documentElement.scrollWidth > window.innerWidth + 1")
        await dp.screenshot(path=str(OUT / "preview-prod-desktop.png"))
        await desk.close()
        await browser.close()

    # 청약일이면 유튜브 요약까지, 상장일이면 상장 포인트로 히어로를 검증
    hero_ok = ((res["hero_kind"] == "subscribe" and res["yt_rows"] >= 2)
               or (res["hero_kind"] == "listing" and res["listing_points"] >= 1))

    ok = (res["http_status"] == 200
          and "1분 요약" in res["title"]
          and res["robots"] and "noindex" not in res["robots"]
          and "index" in res["robots"]
          and res["canonical"] == URL
          and not res["draft_badge_visible"]
          and not res["has_draft_word"]
          and res["hero"] == 1
          and hero_ok
          and "다음 청약" in res["next_rows"]
          and res["next_dday"].startswith("D-")
          and res["next_bottom"] <= res["viewport_h"]
          and res["benefits_collapsed"]
          and res["accordion_opens"]
          and res["row_opens"]
          and res["events"] == 4
          and not res["privacy_hits"]
          and not res["invite_words"]
          and res["support_visible"]
          and res["support_href"] == "https://qr.kakaopay.com/Ej7j2Gwco"
          and res["support_target"] == "_blank"
          and "noopener" in (res["support_rel"] or "")
          and res["support_above_footer"]
          and not res["console_errors"]
          and res["doc_width"] == res["viewport_width"]
          and not res["desktop_h_overflow"])
    for k, v in res.items():
        print(f"{k}: {v}")
    print("\nRESULT:", "PASS" if ok else "CHECK")


if __name__ == "__main__":
    asyncio.run(main())
