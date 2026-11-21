"""프로덕션 390px 첫 화면(뷰포트 390x844) 스크린샷 저장.

usage: LD_LIBRARY_PATH=/workspace/work/.chromium-libs/root/usr/lib/x86_64-linux-gnu \
       python3 work/ipo-events-public/scripts/shot_prod_first_screen.py [출력경로]
"""
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

URL = "https://ipo.mydon.kr/"
DEFAULT_OUT = Path("downloads/ipo-prod-first-390.png")
UA = ("Mozilla/5.0 (Linux; Android 14; SM-S911N) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36")


async def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=2,
            is_mobile=True, has_touch=True, user_agent=UA,
            locale="ko-KR", timezone_id="Asia/Seoul")
        page = await ctx.new_page()
        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(600)
        await page.screenshot(path=str(out), full_page=False)
        print("saved:", out.resolve())
        await browser.close()


asyncio.run(main())
