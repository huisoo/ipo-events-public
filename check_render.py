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
- 청약 정보 공유 바(.share): 히어로와 철회·출처 사이에 **버튼 1개**(1열 풀폭·44px·--sun-soft/--sun),
  '청약 정보 공유하기' → navigator.share 로 {title,text,url} 전달(url 은 text 에 중복 없음),
  미지원(헤드리스·데스크톱)·AbortError 이외 오류 시 클립보드에 청약 정보 포맷
  (📌 {종목} ({M/DD} 마감) / * 항목 12개 / ✅ 청약 의견 / URL) · 토스트 · 라벨 '복사됐어요' 되돌림,
  AbortError(사용자가 닫음)에는 아무 것도 하지 않음
- 공유문 포맷: 풀 필드 mock 2건(빈 줄 구분·정확한 문자열 일치), 값이 없는 항목은 줄 생략,
  오늘 청약 0건이면 ipo.next 폴백('11/25 마감 예정'), 청약·다음 청약 모두 없으면 공유 바 숨김
- 스크린샷: preview-mobile.png / preview-mobile-events.png / preview-mobile-dark.png /
  preview-desktop.png / preview-toast.png / preview-mobile-schedule*.png /
  preview-mobile-share.png / preview-mobile-share-dark.png / preview-mobile-share-full.png
- 상단 2탭: 기본 '오늘 요약', 탭하면 '전체 일정'(?tab=schedule) — 두 탭 모두 390px·다크·
  데스크톱에서 가로 스크롤·잘림 없이 렌더
"""
import asyncio
import datetime as dt
import functools
import http.server
import json
import re
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
    """청약일 화면 + 공유문 풀 필드 mock — 12개 항목·청약 의견이 모두 찍히는지 보는 테스트 데이터."""
    body = json.loads(json.dumps(body))
    ipo = body.setdefault("ipo", {})
    ipo["subscribe"] = [
        {"name": "하나에어로다이내믹스", "badge": "오늘 청약", "market": "코스닥",
         "price": "확정 5,700원", "period": "11/19(수)~11/20(목)",
         "refund": "11/24(월)", "brokers": "IBK투자증권",
         "closeDate": "2026-11-20", "closeDateLabel": "11/20",
         "ipoPrice": "5,700원", "lockupRate": "4.1%", "marketCap": "1,010억",
         "minSubscription": "10주 / 28,500원", "fee": "2,000원",
         "equalShares": "55만 주", "expectedProRata": "3,500:1",
         "proRata10Shares": "약 1억 청약", "fullSubscription": "2억 1,375만 원",
         "refundDate": "11/13", "listingDate": "11/20",
         "opinion": "균등 + 비례 풀청약 추천"},
        # 값이 빠진 종목 — 미정/확인 필요 항목은 줄을 만들지 않고, price·refund 로 대신합니다
        {"name": "신영스팩12호", "badge": "오늘 청약", "market": "코스닥",
         "price": "확정 2,000원", "period": "11/20(금)~11/21(토)",
         "refund": "2026-11-24", "brokers": "신영증권",
         "lockupRate": "미정", "marketCap": "확인 필요", "expectedProRata": ""},
    ]
    ipo["listing"] = {"hasListing": False}
    return body


# 풀 필드 mock 의 기대 공유문 — 화면이 아니라 포맷 자체를 고정합니다.
MOCK_COPY = (
    "📌 하나에어로다이내믹스 (11/20 마감)\n"
    "\n"
    "* 공모가: 5,700원\n"
    "* 확약률: 4.1%\n"
    "* 시총: 1,010억\n"
    "* 주관사: IBK투자증권\n"
    "* 최소청약: 10주 / 28,500원\n"
    "* 수수료: 2,000원\n"
    "* 균등물량: 55만 주\n"
    "* 예상 비례경쟁률: 3,500:1\n"
    "* 비례 10주: 약 1억 청약\n"
    "* 풀청약: 2억 1,375만 원\n"
    "* 환불일: 11/13\n"
    "* 상장일: 11/20\n"
    "\n"
    "✅ 청약 의견: 균등 + 비례 풀청약 추천\n"
    "\n"
    "📌 신영스팩12호 (11/21 마감)\n"
    "\n"
    "* 공모가: 2,000원\n"
    "* 주관사: 신영증권\n"
    "* 환불일: 11/24\n"
)


def no_ipo_day(body):
    """청약도 다음 청약도 없는 날 — 공유 바는 숨겨야 합니다."""
    body = json.loads(json.dumps(body))
    ipo = body.setdefault("ipo", {})
    ipo["subscribe"] = []
    ipo["next"] = {}
    ipo["listing"] = {"hasListing": False}
    return body


# ── 공유문 기대값 계산 (app.js 의 shareBlock 과 같은 규칙) ──────────────
SHARE_FIELDS = [
    ("ipoPrice", "공모가"), ("lockupRate", "확약률"), ("marketCap", "시총"),
    ("brokers", "주관사"), ("minSubscription", "최소청약"), ("fee", "수수료"),
    ("equalShares", "균등물량"), ("expectedProRata", "예상 비례경쟁률"),
    ("proRata10Shares", "비례 10주"), ("fullSubscription", "풀청약"),
    ("refundDate", "환불일"), ("listingDate", "상장일"),
]
UNKNOWN = re.compile(r"^(미정|확인\s*(필요|못|전)|-+|tbd|n/a)$", re.I)


def mdd(v):
    s = str(v or "").strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{int(m.group(2))}/{m.group(3)}"
    return re.sub(r"\([일월화수목금토]\)", "", s).strip()


def share_value(item, key):
    raw = item.get(key) if item.get(key) not in (None, "") else ""
    if not raw and key == "ipoPrice":
        raw = item.get("price") or ""
    if not raw and key == "refundDate":
        raw = item.get("refund") or ""
    v = str(raw or "").strip()
    if key == "ipoPrice":
        v = re.sub(r"^확정\s*", "", v)
    if key == "refundDate":
        v = re.sub(r"^환불\s*", "", v)
    if key in ("refundDate", "listingDate"):
        v = mdd(v)
    if not v or UNKNOWN.match(v):
        return ""
    return v


def close_text(item):
    v = item.get("closeDateLabel") or item.get("closeDate") or ""
    if v:
        return mdd(v)
    pairs = re.findall(r"(\d{1,2})\s*/\s*(\d{1,2})", str(item.get("period") or ""))
    return f"{int(pairs[-1][0])}/{pairs[-1][1]}" if pairs else ""


def close_day(item):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(item.get("closeDate") or ""))
    if m:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    label = close_text(item)
    mo, da = label.split("/")
    d = dt.date(TODAY.year, int(mo), int(da))
    if (TODAY - d).days > 180:
        d = dt.date(TODAY.year + 1, int(mo), int(da))
    return d


def share_block(item, is_next=False):
    head = "📌 " + str(item.get("name") or "").strip()
    close = close_text(item)
    note = str(item.get("closeNote") or "").strip()
    if not note and is_next:
        d = close_day(item)
        note = "" if (d and d <= TODAY) else "예정"
    if close:
        head += f" ({close} 마감" + (f" {note}" if note else "") + ")"
    bullets = [f"* {label}: {v}" for key, label in SHARE_FIELDS
               if (v := share_value(item, key))]
    parts = [head]
    if bullets:
        parts.append("\n".join(bullets))
    if op := share_value(item, "opinion"):
        parts.append("✅ 청약 의견: " + op)
    return "\n\n".join(parts)


def share_items(data):
    ipo = data.get("ipo") or {}
    if ipo.get("subscribe"):
        return [(s, False) for s in ipo["subscribe"]]
    nxt = ipo.get("next") or {}
    return [(nxt, True)] if nxt.get("name") else []


def expected_body(data):
    return "\n\n".join(share_block(it, is_next) for it, is_next in share_items(data))


def expected_copy(data):
    body = expected_body(data)
    return f"{body}\n{SITE_URL}" if body else ""


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
            # 1열 풀폭(버튼 폭 = .share 안쪽 폭) · 주 버튼 색(--sun-soft 배경 · --sun 글자)
            results["share_full_width"] = await page.evaluate("""(() => {
                const s = document.querySelector('#share'), b = document.querySelector('#share .share-btn');
                const cs = getComputedStyle(s);
                const inner = s.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
                return Math.abs(b.getBoundingClientRect().width - inner) <= 2;
            })()""")
            results["share_primary_style"] = await page.evaluate("""(() => {
                const cs = getComputedStyle(document.querySelector('#share .share-btn'));
                const probe = v => { const d = document.createElement('div');
                    d.style.color = v; document.body.appendChild(d);
                    const c = getComputedStyle(d).color; d.remove(); return c; };
                return { bg_ok: cs.backgroundColor === probe('var(--sun-soft)'),
                         fg_ok: cs.color === probe('var(--sun)'),
                         bold: Number(cs.fontWeight) >= 700 };
            })()""")
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

            # 버튼 1개 — navigator.share 없는 환경(헤드리스)은 클립보드 복사로 폴백
            await page.evaluate("navigator.clipboard.writeText('')")
            await page.locator("#share .share-btn").click()
            await page.wait_for_timeout(350)
            clip = await page.evaluate("navigator.clipboard.readText()")
            results["share_clipboard"] = clip
            lines = clip.split("\n")
            results["share_lines"] = len(lines)
            results["share_line_head"] = lines[0]
            results["share_last_line"] = lines[-1]
            results["share_copy_toast"] = await page.inner_text("#toast")
            results["share_copy_label"] = (await page.inner_text("#share .share-btn")).strip()
            await page.wait_for_timeout(1900)
            results["share_copy_label_back"] = (
                await page.inner_text("#share .share-btn")).strip()

            # 공유문 = 청약 정보만 — 현재 data.json 기준 기대값과 정확히 일치해야 함
            results["share_expect"] = expected_copy(DATA)
            results["share_exact"] = clip == results["share_expect"]
            nxt = IPO.get("next") or {}
            listing = (IPO.get("listing") or {})
            results["share_head_ok"] = bool(re.match(r"^📌 \S+ \(\d{1,2}/\d{1,2} 마감", clip))
            if not (IPO.get("subscribe")) and nxt.get("name"):
                # 청약 없는 날은 다음 청약을 폴백으로, '마감 예정' 표기
                results["share_next_fallback"] = (
                    clip.startswith(f"📌 {nxt['name']} (") and "예정" in lines[0])
            else:
                results["share_next_fallback"] = True
            # 전체 요약·상장·철회 문구는 빠져야 합니다
            results["share_no_summary"] = not any(
                s in clip for s in ("•", "직장인 1분 공모주 요약", "오늘 청약 없음", "상장 철회"))
            head_names = [str(it.get("name")) for it, _ in share_items(DATA)]
            other = []
            if listing.get("hasListing"):
                other.append(listing["name"])
            other += [c.get("name") for c in (IPO.get("cancelled") or [])]
            results["share_no_listing"] = not any(
                n and n not in head_names and n in clip for n in other)
            results["share_only_subscribe_names"] = head_names == [
                ln[2:].split(" (")[0] for ln in clip.split("\n") if ln.startswith("📌 ")]
            terms_all = PRIVACY_TERMS + ALWAYS_TERMS
            results["share_privacy_hits"] = [t for t in terms_all if t in clip]

            # 공유하기 — 헤드리스에는 navigator.share 가 없어 같은 버튼이 청약 정보 복사로 폴백
            await page.evaluate("navigator.clipboard.writeText('')")
            await page.locator("#share .share-btn").click()
            await page.wait_for_timeout(400)
            results["share_fallback_toast"] = await page.inner_text("#toast")
            results["share_fallback_clipboard"] = (
                await page.evaluate("navigator.clipboard.readText()")) == clip
            results["share_fallback_label"] = (
                await page.inner_text("#share .share-btn")).strip()

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
            await spage.locator("#share .share-btn").click()
            await spage.wait_for_timeout(300)
            results["shared_payload"] = await spage.evaluate("window.__shared")
            results["stub_share_label"] = (
                await spage.inner_text("#share .share-btn")).strip()
            results["stub_share_toast"] = (await spage.inner_text("#toast")).strip()
            results["stub_errors"] = s_errors
            await sctx.close()

            # 사용자가 공유 시트를 닫은 경우(AbortError) — 복사·토스트 없이 조용히
            actx, apage, a_errors = await open_page(browser, init_script="""
                navigator.share = function () {
                    const e = new Error('cancel'); e.name = 'AbortError';
                    return Promise.reject(e);
                };
            """)
            await apage.evaluate("navigator.clipboard.writeText('')")
            await apage.locator("#share .share-btn").click()
            await apage.wait_for_timeout(450)
            results["abort_clipboard_empty"] = (
                await apage.evaluate("navigator.clipboard.readText()")) == ""
            results["abort_toast_empty"] = (await apage.inner_text("#toast")).strip() == ""
            results["abort_label"] = (await apage.inner_text("#share .share-btn")).strip()
            results["abort_errors"] = a_errors
            await actx.close()

            # 공유가 거부(reject)되면 조용히 죽지 않고 청약 정보 복사로 폴백
            rctx, rpage, r_errors = await open_page(browser, init_script="""
                navigator.share = function () {
                    const e = new Error('denied'); e.name = 'NotAllowedError';
                    return Promise.reject(e);
                };
            """)
            await rpage.locator("#share .share-btn").click()
            await rpage.wait_for_timeout(450)
            results["share_reject_toast"] = await rpage.inner_text("#toast")
            results["share_reject_clipboard"] = (
                await rpage.evaluate("navigator.clipboard.readText()")) == expected_copy(DATA)
            results["reject_errors"] = r_errors
            await rctx.close()

            # ── 2.6 청약일 — 풀 필드 mock 2건, 포맷 정확히 일치 ─────────
            vctx, vpage, v_errors = await open_page(browser, mutate=subscribe_day)
            await vpage.wait_for_timeout(250)
            await vpage.locator("#share .share-btn").click()
            await vpage.wait_for_timeout(350)
            vclip = await vpage.evaluate("navigator.clipboard.readText()")
            results["mock_clipboard"] = vclip
            results["mock_exact"] = vclip == f"{MOCK_COPY}{SITE_URL}"
            results["mock_blocks"] = vclip.count("📌 ")
            results["mock_bullets"] = vclip.count("* ")
            results["mock_opinion"] = "✅ 청약 의견: 균등 + 비례 풀청약 추천" in vclip
            results["mock_blank_between"] = "✅ 청약 의견: 균등 + 비례 풀청약 추천\n\n📌 신영스팩12호" in vclip
            results["mock_dropped_unknown"] = not any(
                s in vclip for s in ("미정", "확인 필요", "없음", "None"))
            results["mock_url_once"] = vclip.count(SITE_URL) == 1 and vclip.endswith("\n" + SITE_URL)
            await vpage.locator("#share").screenshot(
                path=str(ROOT / "preview-mobile-share-full.png"))
            results["sub_errors"] = v_errors
            await vctx.close()

            # ── 2.7 청약 0건 + 다음 청약 0건 → 공유 바 숨김 ──────
            nctx, npage, _ = await open_page(browser, mutate=no_ipo_day)
            results["no_ipo_share_hidden"] = not await npage.locator("#share").is_visible()
            await nctx.close()

            # ── 3. 다크 모드 ──────────────────────────────
            dark, dpage, dark_errors = await open_page(browser, color_scheme="dark")
            await dpage.screenshot(path=str(ROOT / "preview-mobile-dark.png"), full_page=True)
            results["dark_page_h"] = await dpage.evaluate("document.documentElement.scrollHeight")
            results["dark_share_visible"] = await dpage.locator("#share").is_visible()
            results["dark_share_count"] = await dpage.locator("#share .share-btn").count()
            results["dark_share_btns"] = await dpage.eval_on_selector_all(
                "#share .share-btn", "els => els.map(e => Math.round(e.getBoundingClientRect().height))")
            results["dark_share_labels"] = await dpage.eval_on_selector_all(
                "#share .share-btn", "els => els.map(e => e.textContent.replace(/\\s+/g,' ').trim())")
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
          and "청약 정보" in results["share_label"]
          and len(results["share_btns"]) == 1
          and results["share_btns"][0].startswith("📤")
          and results["share_btns"][0].endswith("청약 정보 공유하기")
          and min(results["share_btn_h"]) >= 44
          and results["share_full_width"]
          and results["share_primary_style"]["bg_ok"]
          and results["share_primary_style"]["fg_ok"]
          and results["share_primary_style"]["bold"]
          and results["share_placed_ok"]
          and results["share_native"] == "undefined"
          and results["share_lines"] >= 3
          and results["share_head_ok"]
          and results["share_last_line"] == SITE_URL
          and results["share_exact"]
          and results["share_next_fallback"]
          and results["share_no_summary"]
          and results["share_no_listing"]
          and results["share_only_subscribe_names"]
          and not results["share_privacy_hits"]
          and "청약 정보" in results["share_copy_toast"]
          and results["share_copy_label"] == "복사됐어요"
          and results["share_copy_label_back"].endswith("청약 정보 공유하기")
          and results["share_fallback_clipboard"]
          and "복사" in results["share_fallback_toast"]
          and results["stub_share_type"] == "function"
          and results["stub_share_label"].endswith("청약 정보 공유하기")
          and results["stub_share_toast"] == ""
          and results["abort_clipboard_empty"]
          and results["abort_toast_empty"]
          and results["abort_label"].endswith("청약 정보 공유하기")
          and not results["abort_errors"]
          and results["mock_exact"]
          and results["mock_blocks"] == 2
          and results["mock_bullets"] == 15
          and results["mock_opinion"]
          and results["mock_blank_between"]
          and results["mock_dropped_unknown"]
          and results["mock_url_once"]
          and results["no_ipo_share_hidden"]
          and not results["sub_errors"]
          and bool(results["shared_payload"])
          and results["shared_payload"].get("url") == SITE_URL
          and results["shared_payload"].get("title") == "공모주 청약 정보"
          and results["shared_payload"].get("text") == expected_body(DATA)
          and SITE_URL not in (results["shared_payload"].get("text") or "")
          and "복사" in results["share_reject_toast"]
          and results["share_reject_clipboard"]
          and results["dark_share_visible"]
          and results["dark_share_count"] == 1
          and min(results["dark_share_btns"]) >= 44
          and results["dark_share_labels"][0].endswith("청약 정보 공유하기")
          and not results["dark_share_overflow"]
          and results["desktop_share_visible"]
          and len(results["desktop_share_labels"]) == 1
          and results["desktop_share_labels"][0].endswith("청약 정보 공유하기")
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
