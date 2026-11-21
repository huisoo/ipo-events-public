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
- 청약·상장 정보 공유 바(.share): 히어로와 철회·출처 사이에 **2버튼 고정(2열 그리드)** —
  왼쪽 `청약 정보 공유`(오늘 청약 또는 ipo.next 가 있을 때, 없으면 `:disabled` + `오늘 청약 없음`),
  오른쪽 `상장 정보 공유`(ipo.listing.hasListing 일 때, 없으면 `:disabled` + `오늘 상장 없음`).
  두 버튼 44px 이상·같은 줄·같은 폭·글자 잘림 없음·아이콘은 이모지가 아닌 인라인 SVG,
  주 액션은 블루 솔리드·보조 액션은 화이트/1px 실선, 비활성은 커서 default + 흐린 회색 배경,
  navigator.share 로 {title,text,url} 전달(url 은 text 에 중복 없음),
  미지원(헤드리스)·AbortError 이외 오류 시 클립보드에 해당 정보 포맷
  (청약: 📌 {종목} ({M/DD} 마감) / * 항목 12개 / ✅ 청약 의견,
   상장: 📈 {종목} ({M/DD} 상장) / * 항목 7개) · 토스트 · 라벨 '복사됐어요' 되돌림,
  AbortError(사용자가 닫음)에는 아무 것도 하지 않음
- 공유문 포맷: 풀 필드 mock 2건(빈 줄 구분·정확한 문자열 일치), 값이 없는 항목은 줄 생략,
  오늘 청약 0건이면 ipo.next 폴백('11/25 마감 예정'),
  상장 정보 mock(풀 필드·빈 항목 생략), 상장 없는 날 → 오른쪽 버튼 비활성 '오늘 상장 없음',
  청약·다음 청약 모두 없는 날 → 왼쪽 버튼 비활성 '오늘 청약 없음' + 눌러도 복사되지 않음
- 스크린샷: preview-mobile.png / preview-mobile-events.png / preview-mobile-dark.png /
  preview-desktop.png / preview-toast.png / preview-mobile-schedule*.png / preview-mobile-cash.png /
  preview-mobile-share.png / preview-mobile-share-dark.png / preview-mobile-share-full.png /
  preview-mobile-share-off.png (양쪽 비활성)
- 전체 일정 최상단 필요 금액 카드(#cash-card): 증거금 = 공모가 × 최소청약주수 × 0.5
  (minShares 없으면 10주·추정, 희망가면 상단) — 종목 행마다 `균등 약 8.9만원 추정`,
  날짜별 동시 묶임(start ≤ d < 환불일)의 최댓값(피크)·피크 날짜·겹치는 종목·단순 합계,
  이번 달/전체·스팩 제외 칩이 같은 데이터로 즉시 재계산(기대값은 data.json 에서 같은 규칙으로 계산),
  가로 잘림 없음, 다크·데스크톱 동일 값
- 상단 3탭: 기본 '오늘 요약', '전체 일정'(?tab=schedule) · '혜택'(?tab=benefits) —
  390px에서 3탭이 한 줄(같은 폭·잘림 없음), 다크·데스크톱에서도 가로 스크롤 없이 렌더
- 오늘 요약 하단 한 줄 배너(.ben-link): 증권사·금융 혜택 N건 · 누르면 혜택 탭 전환 · 혜택 상세는 없음
- 혜택 탭: 칩 3개(전체·증권사·금융·간편 이벤트·설문, 건수 포함) 즉시 필터링,
  카드마다 카테고리·D-day·혜택명·핵심 금액·대상·마감·기간·공식 링크(_blank)·
  '유의사항·신청 방법' 펼침, 만료 숨김(테스트 주입), 개인정보 문구 0건
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
SITE_URL = "https://ipo.mydon.kr"
DATA = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
IPO = DATA.get("ipo", {})
BASE = f"http://127.0.0.1:{PORT}/"
UA = ("Mozilla/5.0 (Linux; Android 14; SM-S911N) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36")
KST = dt.timezone(dt.timedelta(hours=9))

# 주관사 앱 열기 버튼 — OS 판별 확인용 iPhone·데스크톱 UA
IOS_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
          "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")
DESKTOP_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
PLAY = "https://play.google.com/store/apps/details?id="
APPSTORE = "https://apps.apple.com/kr/app/id"
PLAY_ENC = "https%3A%2F%2Fplay.google.com%2Fstore%2Fapps%2Fdetails"

# 다크 모드는 이제 시스템 설정이 아니라 사용자 토글(localStorage)로만 켜진다.
# 다크 화면을 보려면 문서 스크립트보다 먼저 저장값을 심어 둔다(인라인 head 스크립트가 곧 data-theme 부여).
DARK_PREF = "try{localStorage.setItem('mydon-theme','dark')}catch(e){}"


def play_url(pkg):
    """앱 BROWSABLE 딥링크를 확인하지 못한 증권사 — Play 스토어 앱 페이지."""
    return PLAY + pkg


def intent_url(pkg, scheme, host=""):
    """app.js 의 androidIntentUrl 과 같은 규칙 — 앱이 BROWSABLE 로 선언한 스킴."""
    from urllib.parse import quote
    return ("intent://" + host + "/#Intent;scheme=" + scheme + ";package=" + pkg
            + ";S.browser_fallback_url=" + quote(PLAY + pkg, safe="") + ";end")


def app_link_intent(site, pkg):
    """사이트 assetlinks 로 확인된 https 앱 링크 — scheme=https 로 열고 미설치 시 Play."""
    from urllib.parse import quote
    return ("intent://" + re.sub(r"^https?://", "", site) + "#Intent;scheme=https;package="
            + pkg + ";S.browser_fallback_url=" + quote(PLAY + pkg, safe="") + ";end")

# 개인정보 검사어 — 저장소에 올리지 않는 로컬 파일(privacy_terms.txt)에서 한 줄에 하나씩 읽습니다.
_TERMS_FILE = ROOT / "privacy_terms.txt"
PRIVACY_TERMS = ([ln.strip() for ln in _TERMS_FILE.read_text(encoding="utf-8").splitlines()
                  if ln.strip() and not ln.startswith("#")] if _TERMS_FILE.exists() else [])
TODAY = dt.datetime.now(KST).date()

# 개인정보 검사어가 없어도 항상 검사하는 기본 문구
ALWAYS_TERMS = ["야탑", "판교", "이매", "쌍둥이", "육아", "어린이집", "휴대폰", "배송지"]


# ── 전체 일정 · 균등 최소증거금 기대값 ──────────────────────
# app.js 의 offerPrice·depositOf·lockUntil·wonShort·cashPlan 과 같은 규칙입니다.
# (check_prod.py 도 이 함수들을 가져다 씁니다.)
CASH_RATE = 0.5
DEFAULT_MIN_SHARES = 10


def parse_iso(v):
    """'2026-11-24' → date (없으면 None)."""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(v or ""))
    return dt.date(int(m[1]), int(m[2]), int(m[3])) if m else None


def cash_price(text):
    """공모가 문자열 → {value, estimated, range}. 희망 A~B원이면 상단 B."""
    s = re.sub(r"\s+", "", str(text or ""))
    if not s:
        return None
    vals = [int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", s)]
    vals = [v for v in vals if v > 0]
    if not vals:
        return None
    return {"value": max(vals),
            "estimated": ("확정" not in s) or ("희망" in s),
            "range": len(vals) > 1}


def cash_deposit(item):
    """최소청약 증거금 = 공모가 × 최소청약주수 × 0.5 (없으면 10주)."""
    p = cash_price((item or {}).get("price"))
    if not p:
        return None
    try:
        raw = int((item or {}).get("minShares") or 0)
    except (TypeError, ValueError):
        raw = 0
    shares = raw if raw > 0 else DEFAULT_MIN_SHARES
    return {
        "amount": int(round(p["value"] * shares * CASH_RATE)),
        "price": p["value"], "shares": shares,
        "shares_estimated": raw <= 0, "price_estimated": p["estimated"],
        "price_range": p["range"],
    }


def cash_reason(dep):
    """app.js depositReason — 희망가 / 10주 가정."""
    if dep["price_estimated"] and dep["shares_estimated"]:
        return "희망가·10주 가정"
    if dep["price_estimated"]:
        return "희망가 가정"
    if dep["shares_estimated"]:
        return "10주 가정"
    return ""


def cash_lock_until(item):
    """자금이 묶이는 끝(제외 구간 끝 = 환불일). 환불일이 없으면 마감일 다음 날."""
    r = parse_iso(item.get("refund"))
    if r:
        return r
    e = parse_iso(item.get("end")) or parse_iso(item.get("start"))
    return e + dt.timedelta(days=1) if e else None


def won_short(v):
    """JS wonShort 와 같은 표기 — 89000 → 8.9만원 (0.05 단위는 반올림)."""
    from fractions import Fraction

    def tenths(fr):
        n = int(fr + Fraction(1, 2))
        s = f"{n // 10}.{n % 10}"
        return s[:-2] if s.endswith(".0") else s

    if not (v > 0):
        return "0원"
    if v >= 100000000:
        return tenths(Fraction(v * 10, 100000000)) + "억원"
    if v >= 10000:
        return tenths(Fraction(v * 10, 10000)) + "만원"
    return f"{v:,}원"


def cash_span(items):
    first = last = None
    for it in items:
        s = parse_iso(it.get("start"))
        u = cash_lock_until(it)
        if s and (first is None or s < first):
            first = s
        if u and (last is None or u > last):
            last = u
    if not first or not last:
        return ""
    a, b = first.month, last.month
    return (f"{a}" if a == b else f"{a}~{b}") + "월"


def cash_plan(ipo, today, range_=None, no_spac=True):
    """선택 범위·스팩 제외별 피크 자금 · 단순 합계 기대값."""
    subs = ((ipo or {}).get("upcoming") or {}).get("subscribe") or []
    allitems = [it for it in subs if (cash_lock_until(it) or dt.date.min) > today]
    month = [it for it in allitems
             if (parse_iso(it.get("start")) or dt.date.min).month == today.month
             and (parse_iso(it.get("start")) or dt.date.min).year == today.year]
    rng = range_ or ("month" if month else "all")
    picked = month if rng == "month" else allitems
    scoped = [it for it in picked if not it.get("spac")] if no_spac else picked

    rows = []
    for it in scoped:
        dep, until = cash_deposit(it), cash_lock_until(it)
        if dep and until:
            rows.append((it, dep, until))

    days = {}
    for it, dep, until in rows:
        start = parse_iso(it.get("start"))
        if not start:
            continue
        d = start
        while d < until:
            if d >= today:
                cell = days.setdefault(d, {"amount": 0, "names": []})
                cell["amount"] += dep["amount"]
                if it.get("name") not in cell["names"]:
                    cell["names"].append(it.get("name"))
            d += dt.timedelta(days=1)

    peak = None
    for d in sorted(days):
        if peak is None or days[d]["amount"] > peak[1]["amount"]:
            peak = (d, days[d])

    return {
        "range": rng, "rows": rows, "count": len(rows),
        "missing": sum(1 for it in picked if not cash_deposit(it)),
        "spac_out": len(picked) - len(scoped),
        "total": sum(r[1]["amount"] for r in rows), "peak": peak,
        "month_label": f"이번 달 ({today.month}월)",
        "all_label": "전체 예정" + (f" ({cash_span(allitems)})" if cash_span(allitems) else ""),
    }


def cash_peak_text(plan):
    return ("약 " + won_short(plan["peak"][1]["amount"])) if plan["peak"] else "0원"


def short_day(d):
    """11/24(화) — JS shortDay 와 같은 표기(일요일=0)."""
    return f"{d.month}/{d.day}(" + "일월화수목금토"[(d.weekday() + 1) % 7] + ")"


def cash_row_text(item):
    dep = cash_deposit(item)
    if not dep:
        return None
    reason = cash_reason(dep)
    return ("균등 " + ("약 " if reason else "") + won_short(dep["amount"])
            + (" 추정" if reason else ""))


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
    """만료/오늘/상시/링크 유무를 함께 확인할 테스트 혜택 항목."""
    return [
        {
            "id": "test-expired",
            "category": "simple",
            "title": "만료된 테스트 혜택",
            "provider": "테스트기관",
            "benefit": "이 카드는 화면에 나오면 안 됩니다",
            "target": "누구나",
            "period": "2026.10.01~11.01",
            "expiresAt": "2026-11-01",
            "link": {"label": "자세히 보기", "url": "https://example.com/"},
        },
        {
            "id": "test-today",
            "category": "simple",
            "title": "오늘까지 유효한 테스트 혜택",
            "provider": "테스트기관",
            "benefit": "오늘 마감 항목은 노출되어야 합니다",
            "target": "누구나",
            "period": f"{TODAY.isoformat()} 까지",
            "expiresAt": TODAY.isoformat(),
            "link": {"label": "자세히 보기", "url": "https://example.com/"},
        },
        {
            "id": "test-always",
            "category": "securities",
            "title": "상시 테스트 혜택",
            "provider": "테스트증권",
            "benefit": "expiresAt 이 null 이면 상시로 노출됩니다",
            "target": "신규 고객",
            "period": "상시",
            "expiresAt": None,
            "terms": ["상시 항목의 유의사항입니다."],
        },
        {
            "id": "test-link",
            "category": "securities",
            "title": "공식 링크가 있는 테스트 혜택",
            "provider": "테스트증권",
            "benefit": "공식 링크 버튼이 새 탭으로 열려야 합니다",
            "target": "신규 고객",
            "period": "상시",
            "expiresAt": None,
            "howTo": "앱에서 이벤트 신청",
            "terms": ["신청해야 지급됩니다."],
            "link": {"label": "자세히 보기", "url": "https://example.com/event"},
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


# 풀 필드 mock 의 기대 상장 공유문 — 포맷 자체를 고정합니다.
MOCK_LISTING_COPY = (
    "📈 하나에어로다이내믹스 (11/20 상장)\n"
    "\n"
    "* 공모가: 5,700원\n"
    "* 시초가: 10,130원 (+77.7%)\n"
    "* 종가: 6,050원 (+6.14%)\n"
    "* 최종 확약률: 72.69%\n"
    "* 상장일 유통물량: 17.30% (약 175억)\n"
    "* 가격제한폭: 3,420원 ~ 22,800원 (60~400%)\n"
    "* 한줄 요약: 장 초반 +98% 급등 후 마감 · 12/5 15일 확약 물량 주의\n"
)

# 값이 빠진 상장 mock — 확인 못 한 항목은 줄을 만들지 않고, closePrice 는 earlyPrice 로 대신
MOCK_LISTING_SPARSE = (
    "📈 엠비디 (11/24 상장)\n"
    "\n"
    "* 공모가: 7,000원\n"
    "* 종가: 8,900원 (+27.1%)\n"
)


def listing_day(body):
    """오늘 상장만 있는 날 — 왼쪽(청약)은 비활성, 오른쪽(상장)은 풀 필드."""
    body = json.loads(json.dumps(body))
    ipo = body.setdefault("ipo", {})
    ipo["subscribe"] = []
    ipo["next"] = {}
    ipo["listing"] = {
        "hasListing": True, "date": "2026-11-20", "name": "하나에어로다이내믹스",
        "code": "271160", "market": "코스닥", "badge": "오늘 상장",
        "ipoPrice": "5,700원",
        "openPrice": "10,130원", "openChange": "+77.7%",
        "closePrice": "6,050원", "closeChange": "+6.14%",
        "lockupRate": "72.69%", "floatSummary": "17.30% (약 175억)",
        "priceBand": "3,420원 ~ 22,800원 (60~400%)",
        "shareSummary": "장 초반 +98% 급등 후 마감 · 12/5 15일 확약 물량 주의",
    }
    return body


def listing_sparse_day(body):
    """상장 정보에 확인된 값만 있는 날 — 빈 항목·미정은 줄 생략."""
    body = json.loads(json.dumps(body))
    ipo = body.setdefault("ipo", {})
    ipo["subscribe"] = []
    ipo["next"] = {}
    ipo["listing"] = {
        "hasListing": True, "date": "2026-11-24", "name": "엠비디",
        "ipoPrice": "7,000원", "openPrice": "미정", "openChange": "",
        "earlyPrice": "8,900원", "earlyChange": "+27.1%",
        "lockupRate": "확인 필요", "floatSummary": "", "priceBand": "",
        "shareSummary": "",
    }
    return body


def broker_day(body):
    """청약 당일 mock — 복수 주관사('KB증권 · NH투자증권') 카드에 앱 열기 버튼 2개가 뜨는지."""
    body = json.loads(json.dumps(body))
    ipo = body.setdefault("ipo", {})
    ipo["listing"] = {"hasListing": False}
    ipo["subscribe"] = [
        {"name": "마더스제약", "badge": "오늘 청약", "market": "코스닥",
         "price": "희망 11,000~14,500원", "period": "12/08(월)~12/09(화)",
         "refund": "12/11(목)", "brokers": "KB증권 · NH투자증권"},
        {"name": "케이엠에프", "badge": "오늘 청약", "market": "코스닥",
         "price": "희망 15,000~17,800원", "period": "12/09(화)~12/10(수)",
         "refund": "12/14(월)", "brokers": "IBK투자증권"},
    ]
    return body


def no_listing_day(body):
    """오늘 청약은 있지만 상장은 없는 날 — 오른쪽 버튼만 비활성."""
    body = subscribe_day(body)
    body["ipo"]["listing"] = {"hasListing": False}
    return body


def no_ipo_day(body):
    """청약도 다음 청약도 없는 날 — 두 버튼 모두 이유를 적은 비활성."""
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
    if not raw and key == "closePrice":
        raw = item.get("earlyPrice") or ""
    if not raw and key == "closeChange":
        raw = item.get("earlyChange") or ""
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


# ── 상장 정보 공유문 기대값 (app.js 의 listingBody 와 같은 규칙) ──────────
LISTING_FIELDS = [
    ("ipoPrice", "공모가", None),
    ("openPrice", "시초가", "openChange"),
    ("closePrice", "종가", "closeChange"),
    ("lockupRate", "최종 확약률", None),
    ("floatSummary", "상장일 유통물량", None),
    ("priceBand", "가격제한폭", None),
    ("shareSummary", "한줄 요약", None),
]


def listing_value(item, key, chg_key):
    v = share_value(item, key)
    if not v or not chg_key:
        return v
    c = share_value(item, chg_key)
    return f"{v} ({c})" if c else v


def listing_block(data):
    ipo = data.get("ipo") or {}
    l = ipo.get("listing") or {}
    if not l.get("hasListing") or not str(l.get("name") or "").strip():
        return ""
    when = mdd(l.get("date") or l.get("listingDate") or ipo.get("date") or "")
    head = "📈 " + str(l.get("name")).strip() + (f" ({when} 상장)" if when else "")
    bullets = [f"* {label}: {v}" for key, label, chg in LISTING_FIELDS
               if (v := listing_value(l, key, chg))]
    return head + ("\n\n" + "\n".join(bullets) if bullets else "")


def expected_listing_copy(data):
    body = listing_block(data)
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
                body["benefits"] = body.get("benefits", []) + inject
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
            results["brand"] = (await page.inner_text(".brand")).replace("\n", " ").strip()
            results["brand_nowrap"] = await page.evaluate(
                "getComputedStyle(document.querySelector('.brand')).whiteSpace")
            results["brand_text_lines"] = await page.evaluate("""(() => {
                const b = document.querySelector('.brand');
                const t = [...b.childNodes].find(n => n.nodeType === 3 && n.textContent.trim());
                const r = document.createRange();
                r.selectNodeContents(t);
                return r.getClientRects().length;
            })()""")
            results["og_title"] = await page.get_attribute("meta[property='og:title']", "content")
            results["og_site_name"] = await page.get_attribute("meta[property='og:site_name']", "content")
            results["tw_title"] = await page.get_attribute("meta[name='twitter:title']", "content")
            results["css_href"] = await page.get_attribute(
                "link[rel='stylesheet'][href*='styles.css']", "href")
            results["js_src"] = await page.get_attribute("script[src*='app.js']", "src")
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
                const ben = document.querySelector('#ben-link').getBoundingClientRect();
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

            # ── 청약·상장 정보 공유 바(.share) — 항상 2버튼 고정 ────────────
            share = page.locator("#share")
            results["share_visible"] = await share.is_visible()
            results["share_label"] = (await page.inner_text("#share .share-lab")).strip()
            results["share_btns"] = await page.eval_on_selector_all(
                "#share .share-btn", "els => els.map(e => e.textContent.replace(/\\s+/g,' ').trim())")
            results["share_ids"] = await page.eval_on_selector_all(
                "#share .share-btn", "els => els.map(e => e.id)")
            results["share_disabled"] = await page.eval_on_selector_all(
                "#share .share-btn", "els => els.map(e => e.disabled)")
            results["share_btn_h"] = await page.eval_on_selector_all(
                "#share .share-btn", "els => els.map(e => Math.round(e.getBoundingClientRect().height))")
            results["share_white_space"] = await page.eval_on_selector_all(
                "#share .share-btn", "els => els.map(e => getComputedStyle(e).whiteSpace)")
            # 2열 그리드 — 같은 줄·같은 폭으로 .share 안쪽 폭을 꽉 채우고, 글자가 잘리지 않음
            results["share_grid"] = await page.evaluate("""(() => {
                const s = document.querySelector('#share'), cs = getComputedStyle(s);
                const inner = s.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
                const b = [...document.querySelectorAll('#share .share-btn')].map(e => e.getBoundingClientRect());
                const lbl = [...document.querySelectorAll('#share .share-btn .lbl')];
                return {
                    count: b.length,
                    same_row: b.length === 2 && Math.abs(b[0].top - b[1].top) <= 1,
                    equal_w: b.length === 2 && Math.abs(b[0].width - b[1].width) <= 2,
                    fills: b.length === 2 &&
                        Math.abs((b[0].width + b[1].width + (b[1].left - b[0].right)) - inner) <= 3,
                    gap: b.length === 2 ? Math.round(b[1].left - b[0].right) : -1,
                    widths: b.map(r => Math.round(r.width)),
                    fit: lbl.every(e => e.scrollWidth <= e.clientWidth + 1),
                };
            })()""")
            # 버튼 위계 — 주 액션(청약)은 블루 솔리드+흰 글씨, 보조 액션(상장)은 흰 카드+잉크 글씨/실선 보더
            results["share_btn_style"] = await page.evaluate("""(() => {
                const probe = v => { const d = document.createElement('div');
                    d.style.color = v; document.body.appendChild(d);
                    const c = getComputedStyle(d).color; d.remove(); return c; };
                const st = (sel, bgVar, fgVar) => {
                    const cs = getComputedStyle(document.querySelector(sel));
                    return { bg_ok: cs.backgroundColor === probe(bgVar),
                             fg_ok: cs.color === probe(fgVar),
                             border_ok: cs.borderTopColor === probe('var(--line2)'),
                             weight: Number(cs.fontWeight) };
                };
                return { sub: st('#share-sub', 'var(--blue)', '#ffffff'),
                         listing: st('#share-listing', 'var(--card)', 'var(--ink)') };
            })()""")
            # 버튼 아이콘은 이모지가 아니라 인라인 SVG
            results["share_icons"] = await page.locator("#share .share-btn .ico svg").count()
            results["ben_link_icon"] = await page.locator("#ben-link .ben-link-arrow svg").count()
            results["share_pos"] = await page.evaluate("""(() => {
                const r = s => document.querySelector(s).getBoundingClientRect();
                return { hero: Math.round(r('#sec-ipo').bottom), share: Math.round(r('#share').top),
                         foot: Math.round(r('#ipo-foot').top),
                         benefits: Math.round(r('#ben-link').top) };
            })()""")
            pos = results["share_pos"]
            results["share_placed_ok"] = (pos["hero"] <= pos["share"]
                                         and pos["share"] <= pos["foot"]
                                         and pos["foot"] <= pos["benefits"])
            results["share_native"] = await page.evaluate("typeof navigator.share")
            await share.screenshot(path=str(ROOT / "preview-mobile-share.png"))

            # 왼쪽 버튼 — navigator.share 없는 환경(헤드리스)은 청약 정보 복사로 폴백
            await page.evaluate("navigator.clipboard.writeText('')")
            await page.locator("#share-sub").click()
            await page.wait_for_timeout(350)
            clip = await page.evaluate("navigator.clipboard.readText()")
            results["share_clipboard"] = clip
            lines = clip.split("\n")
            results["share_lines"] = len(lines)
            results["share_line_head"] = lines[0]
            results["share_last_line"] = lines[-1]
            results["share_copy_toast"] = await page.inner_text("#toast")
            results["share_copy_label"] = (await page.inner_text("#share-sub .lbl")).strip()
            await page.wait_for_timeout(1900)
            results["share_copy_label_back"] = (
                await page.inner_text("#share-sub .lbl")).strip()

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

            # 오른쪽 버튼 — 상장 정보 복사 포맷
            await page.evaluate("navigator.clipboard.writeText('')")
            await page.locator("#share-listing").click()
            await page.wait_for_timeout(350)
            lclip = await page.evaluate("navigator.clipboard.readText()")
            llines = lclip.split("\n")
            results["list_clipboard"] = lclip
            results["list_expect"] = expected_listing_copy(DATA)
            results["list_exact"] = lclip == results["list_expect"]
            results["list_head_ok"] = bool(
                re.match(r"^📈 \S+ \(\d{1,2}/\d{1,2} 상장\)$", llines[0]))
            results["list_bullets"] = lclip.count("* ")
            results["list_last_line"] = llines[-1]
            results["list_url_once"] = (lclip.count(SITE_URL) == 1
                                        and lclip.endswith("\n" + SITE_URL))
            results["list_no_subscribe_name"] = not any(
                str(it.get("name")) in lclip for it, _ in share_items(DATA))
            results["list_copy_toast"] = await page.inner_text("#toast")
            results["list_copy_label"] = (await page.inner_text("#share-listing .lbl")).strip()
            await page.wait_for_timeout(1900)
            results["list_copy_label_back"] = (
                await page.inner_text("#share-listing .lbl")).strip()
            results["list_privacy_hits"] = [t for t in terms_all if t in lclip]

            # 같은 버튼을 다시 눌러도 같은 포맷으로 복사 (라벨 되돌림 뒤 반복 동작)
            await page.evaluate("navigator.clipboard.writeText('')")
            await page.locator("#share-sub").click()
            await page.wait_for_timeout(400)
            results["share_fallback_toast"] = await page.inner_text("#toast")
            results["share_fallback_clipboard"] = (
                await page.evaluate("navigator.clipboard.readText()")) == clip
            results["share_fallback_label"] = (
                await page.inner_text("#share-sub .lbl")).strip()

            # ── 상단 3탭: 기본은 오늘 요약, ?tab=schedule / ?tab=benefits ──
            results["tabs_visible"] = await page.locator("#tabs").is_visible()
            results["tab_labels"] = await page.eval_on_selector_all(
                "#tabs .tab", "els => els.map(e => e.textContent.trim())")
            results["tab_count"] = await page.locator("#tabs .tab").count()
            results["tab_default_today"] = await page.evaluate("""(() => {
                const t = document.querySelector('#tab-today'), s = document.querySelector('#tab-schedule'),
                      b = document.querySelector('#tab-benefits');
                return t.classList.contains('is-on') && t.getAttribute('aria-selected') === 'true'
                    && !s.classList.contains('is-on') && !b.classList.contains('is-on')
                    && !document.querySelector('#panel-today').hidden
                    && document.querySelector('#panel-schedule').hidden
                    && document.querySelector('#panel-benefits').hidden;
            })()""")
            results["tab_height"] = round(await page.evaluate(
                "document.querySelector('#tabs .tab').getBoundingClientRect().height"))
            # 390px 한 줄에 3탭 — 같은 줄 · 같은 폭 · 글자 잘림 없음
            results["tab_row"] = await page.evaluate("""(() => {
                const tabs = [...document.querySelectorAll('#tabs .tab')];
                const b = tabs.map(e => e.getBoundingClientRect());
                return { three: b.length === 3,
                         same_row: b.length === 3
                             && Math.max(...b.map(r => r.top)) - Math.min(...b.map(r => r.top)) <= 1,
                         equal_w: b.length === 3
                             && Math.max(...b.map(r => r.width)) - Math.min(...b.map(r => r.width)) <= 2,
                         fit: tabs.every(e => e.scrollWidth <= e.clientWidth + 1) };
            })()""")
            # 오늘 요약 탭에는 혜택 상세가 없고, 한 줄 배너만 있습니다
            results["today_has_no_detail"] = await page.evaluate(
                "!document.querySelector('#panel-today .bf') && !document.querySelector('#panel-today .bf-list')")
            results["today_has_no_accordion"] = await page.evaluate(
                "!document.querySelector('#panel-today details.benefits')")

            # 2레벨: 혜택 탭으로 가는 한 줄 배너 — 증권사·금융 혜택 건수
            results["ben_link_visible"] = await page.locator("#ben-link").is_visible()
            results["ben_link_text"] = (await page.inner_text("#ben-link")).replace("\n", " ")
            results["ben_link_href"] = await page.get_attribute("#ben-link", "href")
            results["ben_link_tab"] = await page.get_attribute("#ben-link", "data-tab")
            results["ben_link_count"] = (await page.inner_text("#ben-count")).strip()
            results["ben_link_pos"] = await page.evaluate("""(() => {
                const r = s => document.querySelector(s).getBoundingClientRect();
                return { foot: Math.round(r('#ipo-foot').bottom),
                         ben: Math.round(r('#ben-link').top),
                         support: Math.round(r('#support').top) };
            })()""")
            _bl = results["ben_link_pos"]
            results["ben_link_placed"] = (_bl["foot"] <= _bl["ben"] <= _bl["support"])

            await page.screenshot(path=str(ROOT / "preview-mobile.png"), full_page=True)
            await page.screenshot(path=str(ROOT / "preview-mobile-first-screen.png"))
            await page.locator("#ben-link").screenshot(path=str(ROOT / "preview-mobile-ben-link.png"))

            # 배너를 탭하면 혜택 탭으로 전환 (URL ?tab=benefits)
            await page.locator("#ben-link").click()
            await page.wait_for_timeout(350)
            results["ben_link_switch"] = await page.evaluate("""(() => {
                const b = document.querySelector('#tab-benefits');
                return b.classList.contains('is-on') && b.getAttribute('aria-selected') === 'true'
                    && !document.querySelector('#panel-benefits').hidden
                    && document.querySelector('#panel-today').hidden;
            })()""")
            results["ben_link_url_ok"] = "tab=benefits" in page.url

            # ── 혜택 탭 — 필터 칩 · 카드 ──────────────────
            results["bf_visible"] = await page.locator("#panel-benefits").is_visible()
            results["bf_note"] = (await page.locator("#bf-note").text_content()).strip()
            results["bf_chips"] = await page.eval_on_selector_all(
                "#bf-chips .bf-chip",
                """els => els.map(e => ({ id: e.dataset.bf, text: e.textContent.trim(),
                                          on: e.classList.contains('is-on'),
                                          pressed: e.getAttribute('aria-pressed') }))""")
            results["bf_chip_row"] = await page.evaluate("""(() => {
                const c = [...document.querySelectorAll('#bf-chips .bf-chip')];
                const b = c.map(e => e.getBoundingClientRect());
                return { count: c.length,
                         fit: c.every(e => e.scrollWidth <= e.clientWidth + 1),
                         one_row: b.length > 0
                             && Math.max(...b.map(r => r.top)) - Math.min(...b.map(r => r.top)) <= 1 };
            })()""")
            results["bf_cards"] = await page.eval_on_selector_all(
                "#bf-list .bf",
                """els => els.map(e => ({
                    id: e.dataset.id, cat: e.dataset.cat,
                    prov: e.querySelector('.bf-prov')?.textContent.trim() || '',
                    title: e.querySelector('.bf-title')?.textContent.trim(),
                    amt: e.querySelector('.bf-amt')?.textContent.trim(),
                    dday: e.querySelector('.bf-dd')?.textContent.trim(),
                    meta: [...e.querySelectorAll('.bf-meta .bf-row')]
                        .map(r => r.textContent.replace(/\\s+/g,' ').trim()),
                    link: e.querySelector('.bf-link')?.getAttribute('href') || '',
                    link_target: e.querySelector('.bf-link')?.getAttribute('target') || '',
                    link_rel: e.querySelector('.bf-link')?.getAttribute('rel') || '',
                    link_text: e.querySelector('.bf-link')?.textContent.trim() || '',
                    terms: e.querySelectorAll('.bf-more li').length,
                    how: e.querySelector('.bf-how')?.textContent.trim() || ''
                }))""")
            cards = results["bf_cards"]
            results["bf_count"] = len(cards)
            results["bf_cats"] = sorted({c["cat"] for c in cards})
            results["bf_securities"] = [c["id"] for c in cards if c["cat"] == "securities"]
            results["bf_simple"] = [c["id"] for c in cards if c["cat"] == "simple"]
            results["bf_all_fields"] = all(
                c["prov"] and c["title"] and c["amt"] and c["dday"] and len(c["meta"]) >= 1
                and c["link"].startswith("https://") and c["link_target"] == "_blank"
                and c["link_text"].endswith("↗")
                and any(k.startswith("마감") for k in c["meta"])
                for c in cards)
            results["bf_ddays"] = [c["dday"] for c in cards]
            results["bf_links_unique"] = len({c["link"] for c in cards}) == len(cards)
            await page.screenshot(path=str(ROOT / "preview-mobile-benefits.png"), full_page=True)
            await page.screenshot(path=str(ROOT / "preview-mobile-benefits-first.png"))
            await page.locator("#bf-list .bf").first.screenshot(
                path=str(ROOT / "preview-mobile-benefit-card.png"))

            # 유의사항·신청 방법 펼치기
            first_card = page.locator("#bf-list .bf").first
            await first_card.locator(".bf-more > summary").click()
            await page.wait_for_timeout(200)
            results["bf_terms_open"] = await first_card.locator(".bf-more").evaluate("el => el.open")
            results["bf_terms_items"] = await first_card.locator(".bf-more li").count()
            results["bf_terms_text"] = (await first_card.locator(".bf-more").inner_text()).replace("\n", " ")
            await page.locator("#bf-list .bf").first.screenshot(
                path=str(ROOT / "preview-mobile-benefit-card-open.png"))
            await first_card.locator(".bf-more > summary").click()
            await page.wait_for_timeout(150)

            # 필터 칩 — 카테고리별 즉시 필터링 + 건수 일치
            async def chip_filter(cat):
                await page.locator(f"#bf-chips [data-bf='{cat}']").click()
                await page.wait_for_timeout(200)
                return await page.eval_on_selector_all(
                    "#bf-list .bf", "els => els.map(e => e.dataset.cat)")

            results["bf_filter_securities"] = await chip_filter("securities")
            results["bf_filter_simple"] = await chip_filter("simple")
            results["bf_filter_all"] = await chip_filter("all")
            results["bf_chip_counts"] = await page.eval_on_selector_all(
                "#bf-chips .bf-chip b", "els => els.map(e => e.textContent.trim())")
            results["bf_scroll_top"] = await page.evaluate(
                "document.documentElement.scrollWidth")
            await page.locator("#support").scroll_into_view_if_needed()
            await page.wait_for_timeout(150)
            await page.screenshot(path=str(ROOT / "preview-mobile-benefits-bottom.png"))
            results["bf_clipped"] = await page.evaluate("""(() => {
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
            # 새 스펙 — 제목 14px/700/--ink, 버튼 카카오페이 옐로(#fee500) + #191919
            results["support_title_style"] = await page.evaluate("""(() => {
                const probe = document.createElement('span');
                probe.style.color = 'var(--ink)';
                document.body.appendChild(probe);
                const ink = getComputedStyle(probe).color;
                probe.remove();
                const t = getComputedStyle(document.querySelector('#support .sup-t'));
                return { size: t.fontSize, weight: t.fontWeight, color: t.color,
                         ink: ink, color_is_ink: t.color === ink };
            })()""")
            results["support_btn_style"] = await page.evaluate("""(() => {
                const b = getComputedStyle(document.querySelector('#support .sup-btn'));
                const c = getComputedStyle(document.querySelector('#support'));
                return { bg: b.backgroundColor, color: b.color, weight: b.fontWeight,
                         border_w: b.borderTopWidth, border_c: b.borderTopColor,
                         radius: b.borderRadius,
                         card_border: c.borderTopWidth + ' ' + c.borderTopColor,
                         card_radius: c.borderRadius };
            })()""")
            _sup_css = (ROOT / "styles.css").read_text(encoding="utf-8")
            results["support_css_hover"] = ".sup-btn:hover{background:#f5dc00}" in _sup_css
            results["support_css_dark"] = 'html[data-theme="dark"] .sup-btn{' in _sup_css
            results["support_btn_emoji"] = await page.evaluate(
                "/[\\u{1F300}-\\u{1FAFF}\\u{2600}-\\u{27BF}]/u.test(document.querySelector('#support .sup-btn').textContent)")
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

            # ── 필요 금액 카드 (균등 최소증거금) — 계산값·칩 ─────
            plan_m = cash_plan(IPO, TODAY)                       # 기본: 이번 달 · 스팩 제외
            plan_a = cash_plan(IPO, TODAY, "all")                 # 전체 · 스팩 제외
            plan_ms = cash_plan(IPO, TODAY, "month", no_spac=False)  # 이번 달 · 스팩 포함
            plan_as = cash_plan(IPO, TODAY, "all", no_spac=False)
            results["cash_exists"] = await page.locator("#cash-card").count()
            results["cash_above_list"] = await page.evaluate("""(() => {
                const c = document.querySelector('#cash-card').getBoundingClientRect();
                const h = document.querySelector('.sch-head').getBoundingClientRect();
                const l = document.querySelector('#sch-subscribe .sc').getBoundingClientRect();
                return c.top < h.top && h.top < l.top + 1;
            })()""")
            results["cash_peak"] = await page.inner_text("#cash-peak")
            results["cash_when"] = (await page.inner_text("#cash-peak-when")).replace("\n", " ")
            results["cash_total"] = await page.inner_text("#cash-total")
            results["cash_count"] = await page.inner_text("#cash-count")
            results["cash_scope"] = await page.inner_text("#cash-scope")
            results["cash_note"] = await page.inner_text("#cash-note")
            results["cash_chips"] = await page.eval_on_selector_all(
                "#cash-chips .cash-chip",
                "els => els.map(e => [e.textContent.trim(), e.getAttribute('aria-pressed')])")
            results["cash_rows"] = await page.eval_on_selector_all(
                "#sch-subscribe .sc .sc-dep",
                "els => els.map(e => e.textContent.replace(/\\s+/g, ' ').trim())")
            results["cash_est_rows"] = await page.locator("#sch-subscribe .sc .sc-est").count()
            results["cash_chip_h"] = await page.eval_on_selector_all(
                "#cash-chips .cash-chip", "els => els.map(e => Math.round(e.getBoundingClientRect().height))")
            results["cash_clipped"] = await page.evaluate("""(() => {
                const vw = window.innerWidth, bad = [];
                document.querySelectorAll('#cash-card, #cash-card *').forEach(el => {
                  const r = el.getBoundingClientRect();
                  if (r.width && (r.left < -1 || r.right > vw + 1)) {
                    bad.push(el.className + ' ' + Math.round(r.left) + '~' + Math.round(r.right));
                  }
                });
                return bad.slice(0, 5);
            })()""")
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

            # 카드만 다른 그림으로도 남깁니다(보고용)
            await page.locator("#cash-card").scroll_into_view_if_needed()
            await page.wait_for_timeout(150)
            await page.locator("#cash-card").screenshot(path=str(ROOT / "preview-mobile-cash.png"))

            # 칩 — 누르면 같은 데이터로 즉시 재계산(스팩 제외 → 포함, 이번 달 → 전체)
            await page.locator("[data-cash-range='all']").click()
            await page.wait_for_timeout(250)
            results["cash_all_peak"] = await page.inner_text("#cash-peak")
            results["cash_all_when"] = (await page.inner_text("#cash-peak-when")).replace("\n", " ")
            results["cash_all_total"] = await page.inner_text("#cash-total")
            results["cash_all_count"] = await page.inner_text("#cash-count")
            results["cash_all_scope"] = await page.inner_text("#cash-scope")
            results["cash_all_pressed"] = await page.eval_on_selector_all(
                "#cash-chips .cash-chip", "els => els.map(e => e.getAttribute('aria-pressed'))")
            await page.locator("#cash-spac").click()
            await page.wait_for_timeout(250)
            results["cash_spac_off_peak"] = await page.inner_text("#cash-peak")
            results["cash_spac_off_total"] = await page.inner_text("#cash-total")
            results["cash_spac_off_count"] = await page.inner_text("#cash-count")
            results["cash_spac_pressed"] = await page.get_attribute("#cash-spac", "aria-pressed")
            await page.locator("[data-cash-range='month']").click()
            await page.wait_for_timeout(250)
            results["cash_month_spac_peak"] = await page.inner_text("#cash-peak")
            results["cash_month_spac_total"] = await page.inner_text("#cash-total")
            results["cash_month_spac_count"] = await page.inner_text("#cash-count")
            results["cash_rows_after"] = await page.eval_on_selector_all(
                "#sch-subscribe .sc .sc-dep",
                "els => els.map(e => e.textContent.replace(/\\s+/g, ' ').trim())")
            # 기본 상태(이번 달 · 스팩 제외)로 되돌립니다
            await page.locator("#cash-spac").click()
            await page.wait_for_timeout(250)
            results["cash_restored"] = await page.evaluate("""(() => ({
                peak: document.querySelector('#cash-peak').textContent.trim(),
                chip: document.querySelector('[data-cash-range=\"month\"]').getAttribute('aria-pressed'),
                spac: document.querySelector('#cash-spac').getAttribute('aria-pressed')
            }))()""")

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
            await page2.locator("#tab-benefits").click()
            await page2.wait_for_timeout(300)
            results["inject_cards"] = await page2.locator("#bf-list .bf").count()
            results["inject_ids"] = await page2.eval_on_selector_all(
                "#bf-list .bf", "els => els.map(e => e.dataset.id)")
            body = await page2.evaluate("document.body.textContent")
            results["expired_hidden"] = "만료된 테스트 혜택" not in body
            results["today_shown"] = "오늘까지 유효한 테스트 혜택" in body
            results["always_shown"] = "상시 테스트 혜택" in body
            results["note_mentions_hidden"] = "1건은 자동으로 숨겼어요" in await page2.locator(
                "#bf-note").text_content()
            results["inject_errors"] = errors2
            results["ready_dday"] = await page2.locator(
                ".bf[data-id='test-today'] .bf-dd").inner_text()
            # 공식 링크 카드 — 새 탭 링크 + 유의사항·신청 방법
            link_card = page2.locator(".bf[data-id='test-link']")
            results["inject_link_href"] = await link_card.locator(".bf-link").get_attribute("href")
            results["inject_link_target"] = await link_card.locator(".bf-link").get_attribute("target")
            results["inject_link_how"] = (await link_card.locator(".bf-how").text_content()).strip()
            await link_card.screenshot(path=str(ROOT / "preview-mobile-benefit-inject.png"))
            await ctx2.close()

            # ── 2.5 공유 시트(navigator.share) 경로 ──────────
            sctx, spage, s_errors = await open_page(browser, init_script="""
                window.__shared = null;
                navigator.share = function (d) { window.__shared = d; return Promise.resolve(); };
            """)
            results["stub_share_type"] = await spage.evaluate("typeof navigator.share")
            await spage.locator("#share-sub").click()
            await spage.wait_for_timeout(300)
            results["shared_payload"] = await spage.evaluate("window.__shared")
            results["stub_share_label"] = (
                await spage.inner_text("#share-sub .lbl")).strip()
            results["stub_share_toast"] = (await spage.inner_text("#toast")).strip()
            # 오른쪽 버튼도 공유 시트로 — title 은 '공모주 상장 정보'
            await spage.evaluate("window.__shared = null")
            await spage.locator("#share-listing").click()
            await spage.wait_for_timeout(300)
            results["shared_listing_payload"] = await spage.evaluate("window.__shared")
            results["stub_list_label"] = (
                await spage.inner_text("#share-listing .lbl")).strip()
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
            await apage.locator("#share-sub").click()
            await apage.wait_for_timeout(450)
            results["abort_clipboard_empty"] = (
                await apage.evaluate("navigator.clipboard.readText()")) == ""
            results["abort_toast_empty"] = (await apage.inner_text("#toast")).strip() == ""
            results["abort_label"] = (await apage.inner_text("#share-sub .lbl")).strip()
            results["abort_errors"] = a_errors
            await actx.close()

            # 공유가 거부(reject)되면 조용히 죽지 않고 복사 폴백 (오른쪽 버튼도 상장 정보로)
            rctx, rpage, r_errors = await open_page(browser, init_script="""
                navigator.share = function () {
                    const e = new Error('denied'); e.name = 'NotAllowedError';
                    return Promise.reject(e);
                };
            """)
            await rpage.locator("#share-sub").click()
            await rpage.wait_for_timeout(450)
            results["share_reject_toast"] = await rpage.inner_text("#toast")
            results["share_reject_clipboard"] = (
                await rpage.evaluate("navigator.clipboard.readText()")) == expected_copy(DATA)
            await rpage.evaluate("navigator.clipboard.writeText('')")
            await rpage.locator("#share-listing").click()
            await rpage.wait_for_timeout(450)
            results["list_reject_toast"] = await rpage.inner_text("#toast")
            results["list_reject_clipboard"] = (
                await rpage.evaluate("navigator.clipboard.readText()")) == expected_listing_copy(DATA)
            results["reject_errors"] = r_errors
            await rctx.close()

            # ── 2.6 청약일 — 풀 필드 mock 2건, 포맷 정확히 일치 (오른쪽은 비활성) ────
            vctx, vpage, v_errors = await open_page(browser, mutate=subscribe_day)
            await vpage.wait_for_timeout(250)
            results["mock_disabled"] = await vpage.eval_on_selector_all(
                "#share .share-btn", "els => els.map(e => e.disabled)")
            results["mock_labels"] = await vpage.eval_on_selector_all(
                "#share .share-btn .lbl", "els => els.map(e => e.textContent.trim())")
            await vpage.locator("#share-sub").click()
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

            # ── 2.7 상장일 — 오른쪽 버튼 활성/포맷 일치, 왼쪽은 '오늘 청약 없음' ────
            gctx, gpage, g_errors = await open_page(browser, mutate=listing_day)
            await gpage.wait_for_timeout(250)
            results["ldisabled"] = await gpage.eval_on_selector_all(
                "#share .share-btn", "els => els.map(e => e.disabled)")
            results["llabels"] = await gpage.eval_on_selector_all(
                "#share .share-btn .lbl", "els => els.map(e => e.textContent.trim())")
            await gpage.locator("#share-listing").click()
            await gpage.wait_for_timeout(350)
            gclip = await gpage.evaluate("navigator.clipboard.readText()")
            results["lmock_clipboard"] = gclip
            results["lmock_exact"] = gclip == f"{MOCK_LISTING_COPY}{SITE_URL}"
            results["lmock_bullets"] = gclip.count("* ")
            results["lmock_url_once"] = (gclip.count(SITE_URL) == 1
                                         and gclip.endswith("\n" + SITE_URL))
            # 비활성 버튼은 눌러도 복사되지 않음 (이벤트를 직접 보내도 가드가 막음)
            await gpage.evaluate("navigator.clipboard.writeText('')")
            await gpage.locator("#share-sub").dispatch_event("click")
            await gpage.wait_for_timeout(250)
            results["ldisabled_no_copy"] = (await gpage.evaluate(
                "navigator.clipboard.readText()")) == ""
            results["disabled_cursor"] = await gpage.eval_on_selector(
                "#share-sub", "e => getComputedStyle(e).cursor")
            results["disabled_border"] = await gpage.eval_on_selector(
                "#share-sub", "e => getComputedStyle(e).borderTopStyle")
            results["disabled_muted"] = await gpage.evaluate("""(() => {
                const probe = v => { const d = document.createElement('div');
                    d.style.color = v; document.body.appendChild(d);
                    const c = getComputedStyle(d).color; d.remove(); return c; };
                const cs = getComputedStyle(document.querySelector('#share-sub'));
                return cs.color === probe('var(--ink3)')
                    && cs.backgroundColor === probe('var(--bg2)');
            })()""")
            await gpage.locator("#share").screenshot(
                path=str(ROOT / "preview-mobile-share-off.png"))
            results["listing_mock_errors"] = g_errors
            await gctx.close()

            # 값이 빠진 상장 — 빈 항목·미정은 줄 생략, closePrice 는 earlyPrice 로 대신
            sctx2, spage2, s2_errors = await open_page(browser, mutate=listing_sparse_day)
            await spage2.wait_for_timeout(250)
            await spage2.locator("#share-listing").click()
            await spage2.wait_for_timeout(350)
            sclip = await spage2.evaluate("navigator.clipboard.readText()")
            results["lsparse_exact"] = sclip == f"{MOCK_LISTING_SPARSE}{SITE_URL}"
            results["lsparse_dropped"] = not any(
                s in sclip for s in ("미정", "확인 필요", "None", "undefined"))
            results["sparse_errors"] = s2_errors
            await sctx2.close()

            # ── 2.8 청약도 다음 청약도 없음 → 왼쪽 '오늘 청약 없음' 비활성 ────────
            nctx, npage, _ = await open_page(browser, mutate=no_ipo_day)
            results["no_ipo_share_visible"] = await npage.locator("#share").is_visible()
            results["no_ipo_btns"] = await npage.eval_on_selector_all(
                "#share .share-btn", "els => els.map(e => e.textContent.replace(/\\s+/g,' ').trim())")
            results["no_ipo_disabled"] = await npage.eval_on_selector_all(
                "#share .share-btn", "els => els.map(e => e.disabled)")
            await npage.evaluate("navigator.clipboard.writeText('')")
            await npage.locator("#share-sub").dispatch_event("click")
            await npage.locator("#share-listing").dispatch_event("click")
            await npage.wait_for_timeout(300)
            results["no_ipo_clipboard_empty"] = (await npage.evaluate(
                "navigator.clipboard.readText()")) == ""
            results["no_ipo_toast_empty"] = (await npage.inner_text("#toast")).strip() == ""
            await npage.locator("#share").screenshot(
                path=str(ROOT / "preview-mobile-share-off.png"))
            await nctx.close()

            # ── 2.9 테마: 기본 라이트 고정 + 상단 다크 토글 ───────────────
            # 시스템이 라이트인 기기에서 기본값·버튼·전환이 모두 라이트 기준으로 동작하는지
            thc, thp, th_errors = await open_page(browser)
            results["theme_attr_default"] = await thp.evaluate(
                "document.documentElement.getAttribute('data-theme')")
            results["theme_bg_default"] = await thp.evaluate(
                "getComputedStyle(document.body).backgroundColor")
            results["theme_color_default"] = await thp.evaluate(
                "getComputedStyle(document.body).color")
            results["theme_meta_default"] = await thp.get_attribute("#theme-color", "content")
            results["theme_head_script"] = await thp.evaluate("""(() => {
                const s = [...document.querySelectorAll('head script:not([src])')]
                    .map(e => e.textContent).join(' ');
                return { has_key: s.includes('mydon-theme'), sets_attr: s.includes('data-theme') };
            })()""")
            results["theme_css_no_auto_dark"] = "@media (prefers-color-scheme" not in (
                ROOT / "styles.css").read_text(encoding="utf-8")
            results["theme_btn_visible"] = await thp.locator("#theme-toggle").is_visible()
            results["theme_btn_label"] = await thp.get_attribute("#theme-toggle", "aria-label")
            results["theme_btn_pressed"] = await thp.get_attribute("#theme-toggle", "aria-pressed")
            results["theme_btn_svgs"] = await thp.locator("#theme-toggle svg").count()
            results["theme_btn_emoji"] = await thp.evaluate(
                "/[\\u{1F300}-\\u{1FAFF}\\u{2600}-\\u{27BF}]/u.test(document.querySelector('#theme-toggle').textContent)")
            results["theme_head_row"] = await thp.evaluate("""(() => {
                const b = document.querySelector('.brand').getBoundingClientRect();
                const u = document.querySelector('.updated').getBoundingClientRect();
                const t = document.querySelector('#theme-toggle').getBoundingClientRect();
                const bar = document.querySelector('.brandbar').getBoundingClientRect();
                const cy = r => Math.round(r.top + r.height / 2);
                return { toggle_w: Math.round(t.width), toggle_h: Math.round(t.height),
                         same_row: Math.abs(cy(b) - cy(t)) <= 6 && Math.abs(cy(u) - cy(t)) <= 6,
                         right_of_updated: t.left >= u.right - 1,
                         /* 26px 버튼이 22px 줄에 -2px 마진으로 2px씩 삐져나옴(줄 높이는 그대로 22px) */
                         last_in_row: t.right <= bar.right + 2,
                         inside_bar: t.top >= bar.top - 2 && t.bottom <= bar.bottom + 2,
                         bar_h: Math.round(bar.height) };
            })()""")
            await thp.locator(".site-head").screenshot(
                path=str(ROOT / "preview-mobile-header.png"))
            # 토글 → 다크 (아이콘·접근성·저장값·테마컬러 함께)
            await thp.locator("#theme-toggle").click()
            await thp.wait_for_timeout(250)
            results["theme_dark_attr"] = await thp.evaluate(
                "document.documentElement.getAttribute('data-theme')")
            results["theme_dark_bg"] = await thp.evaluate(
                "getComputedStyle(document.body).backgroundColor")
            results["theme_dark_stored"] = await thp.evaluate(
                "localStorage.getItem('mydon-theme')")
            results["theme_dark_label"] = await thp.get_attribute("#theme-toggle", "aria-label")
            results["theme_dark_pressed"] = await thp.get_attribute("#theme-toggle", "aria-pressed")
            results["theme_dark_meta"] = await thp.get_attribute("#theme-color", "content")
            results["theme_dark_icon"] = await thp.evaluate("""(() => {
                const vis = s => getComputedStyle(document.querySelector('#theme-toggle .' + s)).display !== 'none';
                return { moon: vis('tt-moon'), sun: vis('tt-sun') };
            })()""")
            await thp.locator(".site-head").screenshot(
                path=str(ROOT / "preview-mobile-header-dark.png"))
            # 새로고침해도 다크 유지(인라인 스크립트가 첫 페인트 전에 적용)
            await thp.reload(wait_until="networkidle")
            await thp.wait_for_selector("#main:not([hidden])", timeout=8000)
            await thp.wait_for_timeout(200)
            results["theme_persist_attr"] = await thp.evaluate(
                "document.documentElement.getAttribute('data-theme')")
            results["theme_persist_bg"] = await thp.evaluate(
                "getComputedStyle(document.body).backgroundColor")
            # 다시 토글 → 라이트 복귀
            await thp.locator("#theme-toggle").click()
            await thp.wait_for_timeout(250)
            results["theme_light_back_attr"] = await thp.evaluate(
                "document.documentElement.getAttribute('data-theme')")
            results["theme_light_back_bg"] = await thp.evaluate(
                "getComputedStyle(document.body).backgroundColor")
            results["theme_light_back_stored"] = await thp.evaluate(
                "localStorage.getItem('mydon-theme')")
            results["theme_errors"] = th_errors
            await thc.close()

            # 시스템이 다크여도 기본은 라이트(자동 다크 해제)
            sdc, sdp, sd_errors = await open_page(browser, color_scheme="dark")
            results["sysdark_attr"] = await sdp.evaluate(
                "document.documentElement.getAttribute('data-theme')")
            results["sysdark_bg"] = await sdp.evaluate(
                "getComputedStyle(document.body).backgroundColor")
            results["sysdark_label"] = await sdp.get_attribute("#theme-toggle", "aria-label")
            await sdp.locator(".site-head").screenshot(
                path=str(ROOT / "preview-mobile-header-sysdark.png"))
            results["sysdark_errors"] = sd_errors
            await sdc.close()

            # ── 3. 다크 모드 ──────────────────────────────
            dark, dpage, dark_errors = await open_page(
                browser, color_scheme="dark", init_script=DARK_PREF)
            results["dark_theme_attr"] = await dpage.evaluate(
                "document.documentElement.getAttribute('data-theme')")
            results["dark_theme_bg"] = await dpage.evaluate(
                "getComputedStyle(document.body).backgroundColor")
            await dpage.screenshot(path=str(ROOT / "preview-mobile-dark.png"), full_page=True)
            results["dark_page_h"] = await dpage.evaluate("document.documentElement.scrollHeight")
            results["dark_share_visible"] = await dpage.locator("#share").is_visible()
            results["dark_share_count"] = await dpage.locator("#share .share-btn").count()
            results["dark_share_btns"] = await dpage.eval_on_selector_all(
                "#share .share-btn", "els => els.map(e => Math.round(e.getBoundingClientRect().height))")
            results["dark_share_labels"] = await dpage.eval_on_selector_all(
                "#share .share-btn .lbl", "els => els.map(e => e.textContent.trim())")
            results["dark_share_grid"] = await dpage.evaluate("""(() => {
                const b = [...document.querySelectorAll('#share .share-btn')].map(e => e.getBoundingClientRect());
                const lbl = [...document.querySelectorAll('#share .share-btn .lbl')];
                return { same_row: b.length === 2 && Math.abs(b[0].top - b[1].top) <= 1,
                         fit: lbl.every(e => e.scrollWidth <= e.clientWidth + 1) };
            })()""")
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
            results["dark_cash_visible"] = await dpage.locator("#cash-card").is_visible()
            results["dark_cash_peak"] = await dpage.inner_text("#cash-peak")
            results["dark_cash_clipped"] = await dpage.evaluate("""(() => {
                const vw = window.innerWidth, bad = [];
                document.querySelectorAll('#cash-card, #cash-card *').forEach(el => {
                  const r = el.getBoundingClientRect();
                  if (r.width && (r.left < -1 || r.right > vw + 1)) {
                    bad.push(el.className + ' ' + Math.round(r.left) + '~' + Math.round(r.right));
                  }
                });
                return bad.slice(0, 5);
            })()""")
            results["dark_sch_overflow"] = await dpage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            await dpage.screenshot(path=str(ROOT / "preview-mobile-schedule-dark.png"), full_page=True)
            await dpage.locator("#tab-benefits").click()
            await dpage.wait_for_timeout(300)
            results["dark_bf_visible"] = await dpage.locator("#panel-benefits").is_visible()
            results["dark_bf_cards"] = await dpage.locator("#bf-list .bf").count()
            results["dark_bf_overflow"] = await dpage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            await dpage.screenshot(path=str(ROOT / "preview-mobile-benefits-dark.png"), full_page=True)
            # 응원 카드 — 다크 모드에서도 카카오페이 옐로 유지
            await dpage.locator("#support").scroll_into_view_if_needed()
            await dpage.wait_for_timeout(150)
            results["dark_support_visible"] = await dpage.locator("#support").is_visible()
            results["dark_support_btn_style"] = await dpage.evaluate("""(() => {
                const b = getComputedStyle(document.querySelector('#support .sup-btn'));
                return { bg: b.backgroundColor, color: b.color, weight: b.fontWeight };
            })()""")
            await dpage.locator("#support").screenshot(
                path=str(ROOT / "preview-mobile-support-dark.png"))
            await dark.close()

            # ── 4. 데스크톱 1280 ──────────────────────────────
            desk, dp, desk_errors = await open_page(
                browser, viewport={"width": 1280, "height": 900},
                is_mobile=False, has_touch=False, device_scale_factor=1,
                permissions=[])
            results["desktop_hero"] = await dp.locator(".hero").count()
            results["desktop_ben_link"] = await dp.locator("#ben-link").is_visible()
            results["desktop_share_visible"] = await dp.locator("#share").is_visible()
            results["desktop_share_labels"] = await dp.eval_on_selector_all(
                "#share .share-btn .lbl", "els => els.map(e => e.textContent.trim())")
            results["desktop_share_disabled"] = await dp.eval_on_selector_all(
                "#share .share-btn", "els => els.map(e => e.disabled)")
            results["desktop_share_fit"] = await dp.eval_on_selector_all(
                "#share .share-btn .lbl",
                "els => els.every(e => e.scrollWidth <= e.clientWidth + 1)")
            results["desktop_h_overflow"] = await dp.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            results["desktop_theme_btn"] = await dp.locator("#theme-toggle").is_visible()
            results["desktop_theme_row"] = await dp.evaluate("""(() => {
                const u = document.querySelector('.updated').getBoundingClientRect();
                const t = document.querySelector('#theme-toggle').getBoundingClientRect();
                const bar = document.querySelector('.brandbar').getBoundingClientRect();
                return { same_row: Math.abs((u.top + u.height / 2) - (t.top + t.height / 2)) <= 6,
                         right_of_updated: t.left >= u.right - 1,
                         inside_bar: t.top >= bar.top - 2 && t.bottom <= bar.bottom + 2 };
            })()""")
            await dp.locator(".site-head").screenshot(
                path=str(ROOT / "preview-desktop-header.png"))
            results["desktop_errors"] = desk_errors
            await dp.screenshot(path=str(ROOT / "preview-desktop.png"))
            await dp.locator("#tab-schedule").click()
            await dp.wait_for_timeout(300)
            results["desktop_sch_cards"] = await dp.locator("#sch-subscribe .sc").count()
            results["desktop_cash_peak"] = await dp.inner_text("#cash-peak")
            results["desktop_sch_overflow"] = await dp.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            await dp.screenshot(path=str(ROOT / "preview-desktop-schedule.png"), full_page=True)
            await dp.locator("#tab-benefits").click()
            await dp.wait_for_timeout(300)
            results["desktop_bf_cards"] = await dp.locator("#bf-list .bf").count()
            results["desktop_bf_overflow"] = await dp.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            await dp.screenshot(path=str(ROOT / "preview-desktop-benefits.png"), full_page=True)
            await desk.close()

            # ── 5. ?tab=schedule 딥링크 ──────────────────────
            deepl, lpage, _ = await open_page(browser, path="?tab=schedule")
            results["deeplink_schedule"] = await lpage.locator("#panel-schedule").is_visible()
            results["deeplink_cards"] = await lpage.locator("#sch-subscribe .sc").count()
            await deepl.close()
            deepl2, lpage2, _ = await open_page(browser, path="?tab=benefits")
            results["deeplink_benefits"] = await lpage2.locator("#panel-benefits").is_visible()
            results["deeplink_bf_cards"] = await lpage2.locator("#bf-list .bf").count()
            results["deeplink_bf_chip"] = " ".join(
                (await lpage2.inner_text("#bf-chips .bf-chip.is-on")).split())
            await deepl2.close()

            # ── 6. 주관사 앱 열기 버튼 — OS 자동 구분 (상장 · 청약 카드) ────────
            # (a) 실제 데이터 — 오늘 상장(하나에어로다이내믹스, 대표주관 IBK투자증권), Android UA
            appctx, apppage, app_errors = await open_page(browser)
            results["app_hero_name"] = (await apppage.inner_text(".hero.is-list .hname")).strip()
            GET_APP = """els => els.map(e => ({
                text: e.textContent.replace(/\\s+/g, ' ').trim(),
                href: e.getAttribute('href'),
                target: e.getAttribute('target'),
                rel: e.getAttribute('rel') || '',
                h: Math.round(e.getBoundingClientRect().height),
                shown: !!(e.offsetWidth && e.offsetHeight)
            }))"""
            listing_apps = await apppage.eval_on_selector_all(
                ".hero.is-list .app-open", GET_APP)
            results["listing_app_btns"] = listing_apps
            results["listing_app_count"] = len(listing_apps)
            results["listing_app_icons"] = await apppage.locator(
                ".hero.is-list .app-open .ico svg").count()
            # Android UA — IBK투자증권은 BROWSABLE 딥링크가 확인되지 않아 Play 스토어 앱 페이지로
            results["listing_app_ok"] = bool(listing_apps) and all([
                listing_apps[0]["text"] == "IBK투자증권 앱 열기",
                results["listing_app_icons"] == 1,
                listing_apps[0]["href"] == play_url("com.ibks.ione.mts"),
                listing_apps[0]["target"] == "_blank",
                "noopener" in listing_apps[0]["rel"],
                listing_apps[0]["h"] >= 36,
                listing_apps[0]["shown"],
            ])
            # 위치: 3줄 요약(.pts) 아래 · 다음 청약 띠(.hero-next) 위
            results["listing_app_pos"] = await apppage.evaluate("""(() => {
                const r = s => { const e = document.querySelector(s); return e ? e.getBoundingClientRect() : null; };
                const pts = r('.hero.is-list .pts'), app = r('.hero.is-list .app-open-row'),
                      nxt = r('.hero.is-list .hero-next');
                return { pts_bottom: pts ? Math.round(pts.bottom) : null,
                         app: app ? Math.round(app.top) : null,
                         next_top: nxt ? Math.round(nxt.top) : null };
            })()""")
            pos = results["listing_app_pos"]
            results["listing_app_placed"] = (
                pos["app"] is not None
                and (pos["pts_bottom"] is None or pos["pts_bottom"] <= pos["app"])
                and (pos["next_top"] is None or pos["app"] < pos["next_top"]))
            results["app_overflow"] = await apppage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            results["app_clipped"] = await apppage.evaluate("""(() => {
                const vw = window.innerWidth, bad = [];
                document.querySelectorAll('.app-open-row, .app-open-row *').forEach(el => {
                  const r = el.getBoundingClientRect();
                  if (r.width && (r.left < -1 || r.right > vw + 1)) bad.push(el.tagName + '.' + el.className);
                });
                return bad.slice(0, 5);
            })()""")
            results["app_errors"] = app_errors
            await apppage.locator(".hero.is-list").screenshot(
                path=str(ROOT / "preview-mobile-app.png"))
            await appctx.close()

            # (b) 같은 페이지를 iPhone UA 로 — 같은 버튼의 href 가 App Store 로 바뀌는지
            iosctx, iospage, ios_errors = await open_page(browser, user_agent=IOS_UA)
            ios_apps = await iospage.eval_on_selector_all(".hero.is-list .app-open", GET_APP)
            results["ios_app_btns"] = ios_apps
            results["ios_app_ok"] = bool(ios_apps) and all([
                ios_apps[0]["text"].endswith("IBK투자증권 앱 열기"),
                ios_apps[0]["href"] == APPSTORE + "6612018102",
                ios_apps[0]["target"] == "_blank",
                "noopener" in ios_apps[0]["rel"],
                ios_apps[0]["shown"],
            ])
            results["ios_overflow"] = await iospage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            results["ios_errors"] = ios_errors
            await iosctx.close()

            # (b-2) 같은 페이지를 데스크톱 UA(Windows Chrome)로 — 그대로 Google Play 스토어 링크
            dsctx, dspage, ds_errors = await open_page(
                browser, user_agent=DESKTOP_UA, viewport={"width": 1280, "height": 900},
                is_mobile=False, has_touch=False, device_scale_factor=1, permissions=[])
            ds_apps = await dspage.eval_on_selector_all(".hero.is-list .app-open", GET_APP)
            results["desktop_app_btns"] = ds_apps
            results["desktop_app_ok"] = bool(ds_apps) and all([
                ds_apps[0]["text"].endswith("IBK투자증권 앱 열기"),
                ds_apps[0]["href"] == PLAY + "com.ibks.ione.mts",
                ds_apps[0]["target"] == "_blank",
                "noopener" in ds_apps[0]["rel"],
                ds_apps[0]["shown"],
            ])
            results["desktop_app_platform"] = await dspage.evaluate("navigator.platform")
            results["desktop_errors"] = ds_errors
            await dsctx.close()

            # (c) 청약 당일 mock — 복수 주관사('KB증권 · NH투자증권') 카드에 버튼 2개
            brctx, brpage, br_errors = await open_page(browser, mutate=broker_day)
            results["br_cards"] = await brpage.locator(".hero").count()
            results["br_apps_by_card"] = await brpage.evaluate("""(() =>
                [...document.querySelectorAll('.hero')].map(c =>
                  [...c.querySelectorAll('.app-open')].map(a => ({
                    text: a.textContent.replace(/\\s+/g, ' ').trim(),
                    href: a.getAttribute('href'),
                    target: a.getAttribute('target'),
                    rel: a.getAttribute('rel') || '',
                    h: Math.round(a.getBoundingClientRect().height),
                    shown: !!(a.offsetWidth && a.offsetHeight)
                  }))))()""")
            by_card = results["br_apps_by_card"]
            # KB증권은 Play 스토어로, NH투자증권은 앱 매니페스트에서 확인한 txsmart://txrun 로
            results["br_two_on_multi"] = (
                len(by_card) == 2
                and [b["text"] for b in by_card[0]] == ["KB증권 앱 열기", "NH투자증권 앱 열기"]
                and by_card[0][0]["href"] == play_url("com.kbsec.mts.iplustarngm2")
                and by_card[0][0]["target"] == "_blank"
                and by_card[0][1]["href"] == intent_url("com.wooriwm.txsmart", "txsmart", "txrun"))
            results["br_one_on_single"] = (
                len(by_card[1]) == 1
                and by_card[1][0]["text"] == "IBK투자증권 앱 열기"
                and by_card[1][0]["href"] == play_url("com.ibks.ione.mts")
                and by_card[1][0]["target"] == "_blank")
            # 확인된 앱은 intent://(같은 창) + Play 폴백, 확인 안 된 앱은 Play 스토어(새 탭)
            results["br_links_ok"] = all(
                a["shown"] and a["h"] >= 36
                and (
                    (a["href"].startswith("intent://")
                     and ";S.browser_fallback_url=" + PLAY_ENC in a["href"]
                     and a["href"].endswith(";end")
                     and not a["target"])
                    or (a["href"].startswith(PLAY)
                        and a["target"] == "_blank" and "noopener" in a["rel"])
                )
                for card in by_card for a in card)
            results["br_overflow"] = await brpage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            results["br_clipped"] = await brpage.evaluate("""(() => {
                const vw = window.innerWidth, bad = [];
                document.querySelectorAll('.hero, .hero *').forEach(el => {
                  if (el.closest('.sr-only')) return;
                  const r = el.getBoundingClientRect();
                  if (r.width && (r.left < -1 || r.right > vw + 1)) bad.push(el.tagName + '.' + el.className);
                });
                return bad.slice(0, 5);
            })()""")
            results["br_errors"] = br_errors
            await brpage.screenshot(path=str(ROOT / "preview-mobile-app-multi.png"))

            # 다크 모드에서도 같은 버튼이 보이고 가로 넘침이 없는지
            dkctx, dkpage, dk_errors = await open_page(
                browser, color_scheme="dark", init_script=DARK_PREF)
            results["dark_app_count"] = await dkpage.locator(".hero.is-list .app-open").count()
            results["dark_app_h"] = round(await dkpage.evaluate(
                "(() => { const e = document.querySelector('.hero .app-open');"
                " return e ? e.getBoundingClientRect().height : 0; })()"))
            results["dark_app_overflow"] = await dkpage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            results["dark_app_errors"] = dk_errors
            await dkctx.close()
            await brctx.close()

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

    def _live(items):
        out = []
        for b in items or []:
            exp = (b or {}).get("expiresAt")
            if exp and dt.date.fromisoformat(str(exp)[:10]) < TODAY:
                continue
            out.append(b)
        return out

    live_benefits = _live(DATA.get("benefits"))
    sec_benefits = [b for b in live_benefits if (b.get("category") or "securities") != "simple"]
    simple_benefits = [b for b in live_benefits if b.get("category") == "simple"]
    inj_live = _live(test_events())

    # 조건을 한 줄씩 따로 평가합니다 — 실패한 조건만 이름 그대로 찍혀서
    # 어느 확인이 깨졌는지 바로 보입니다(조건 자체는 예전 and 체인과 같습니다).
    _conds = [
        'True',
        # 브랜드·공유 제목: 마이돈 키워드와 캐시 버스터가 그대로 실렸는지
        'results["brand"] == "마이돈 · 공모주"',
        'results["brand_nowrap"] == "nowrap"',
        'results["brand_text_lines"] == 1',
        'results["title"].startswith("마이돈 — 오늘의 공모주 1분 요약")',
        'results["og_title"] == "마이돈 — 오늘의 공모주 1분 요약"',
        'results["tw_title"] == "마이돈 — 오늘의 공모주 1분 요약"',
        'results["og_site_name"] == "마이돈"',
        '"?v=" in (results["css_href"] or "")',
        '"?v=" in (results["js_src"] or "")',
        # 테마: 기본 라이트 고정 + 상단 다크 토글 (시스템 다크는 무시)
        'results["theme_css_no_auto_dark"]',
        'results["theme_attr_default"] is None',
        'results["theme_bg_default"] == "rgb(244, 246, 248)"',
        'results["theme_color_default"] == "rgb(25, 31, 40)"',
        'results["theme_meta_default"] == "#f4f6f8"',
        'results["theme_head_script"]["has_key"]',
        'results["theme_head_script"]["sets_attr"]',
        'results["theme_btn_visible"]',
        'results["theme_btn_label"] == "다크 모드로 전환"',
        'results["theme_btn_pressed"] == "false"',
        'results["theme_btn_svgs"] == 2',
        'not results["theme_btn_emoji"]',
        'results["theme_head_row"]["same_row"]',
        'results["theme_head_row"]["right_of_updated"]',
        'results["theme_head_row"]["last_in_row"]',
        'results["theme_head_row"]["inside_bar"]',
        'results["theme_head_row"]["toggle_w"] >= 24',
        'results["theme_head_row"]["bar_h"] <= 28',
        'results["theme_dark_attr"] == "dark"',
        'results["theme_dark_bg"] == "rgb(16, 16, 18)"',
        'results["theme_dark_stored"] == "dark"',
        'results["theme_dark_label"] == "라이트 모드로 전환"',
        'results["theme_dark_pressed"] == "true"',
        'results["theme_dark_meta"] == "#101012"',
        'results["theme_dark_icon"] == {"moon": False, "sun": True}',
        'results["theme_persist_attr"] == "dark"',
        'results["theme_persist_bg"] == "rgb(16, 16, 18)"',
        'results["theme_light_back_attr"] is None',
        'results["theme_light_back_bg"] == "rgb(244, 246, 248)"',
        'results["theme_light_back_stored"] == "light"',
        'not results["theme_errors"]',
        'results["sysdark_attr"] is None',
        'results["sysdark_bg"] == "rgb(244, 246, 248)"',
        'results["sysdark_label"] == "다크 모드로 전환"',
        'not results["sysdark_errors"]',
        'results["dark_theme_attr"] == "dark"',
        'results["dark_theme_bg"] == "rgb(16, 16, 18)"',
        'results["desktop_theme_btn"]',
        'results["desktop_theme_row"]["same_row"]',
        'results["desktop_theme_row"]["right_of_updated"]',
        'results["desktop_theme_row"]["inside_bar"]',
        '"하나에어로다이내믹스" in results["app_hero_name"]',
        'results["listing_app_count"] == 1',
        'results["listing_app_ok"]',
        'results["listing_app_placed"]',
        'not results["app_overflow"]',
        'not results["app_clipped"]',
        'not results["app_errors"]',
        'results["ios_app_ok"]',
        'not results["ios_overflow"]',
        'not results["ios_errors"]',
        'results["desktop_app_ok"]',
        'not results["desktop_errors"]',
        'results["br_cards"] == 2',
        'results["br_two_on_multi"]',
        'results["br_one_on_single"]',
        'results["br_links_ok"]',
        'not results["br_overflow"]',
        'not results["br_clipped"]',
        'not results["br_errors"]',
        'results["dark_app_count"] == 1',
        'results["dark_app_h"] >= 36',
        'not results["dark_app_overflow"]',
        'not results["dark_app_errors"]',
        'results["tabs_visible"]',
        'results["tab_count"] == 3',
        'results["tab_labels"] == ["오늘 요약", "전체 일정", "혜택"]',
        'results["tab_row"]["three"]',
        'results["tab_row"]["same_row"]',
        'results["tab_row"]["equal_w"]',
        'results["tab_row"]["fit"]',
        'results["tab_default_today"]',
        'results["tab_height"] >= 40',
        'results["tab_switch_on"]',
        'results["tab_url_has_query"]',
        'results["sch_counts"]["subscribe"] >= 10',
        'results["sch_counts"]["listing"] >= 1',
        'results["sch_first"]',
        'results["sch_first"]["dday"].startswith("D-")',
        'results["sch_first"]["when"].endswith("청약")',
        '"희망" in (results["sch_first"]["price"] or "")',
        'results["sch_first"]["sub"]',
        '"증권" in results["sch_first"]["sub"]',
        'all(d.startswith("D-") or d in ("청약 중", "청약 종료") for d in results["sch_ddays"])',
        'len(results["sch_list_items"]) >= 1',
        'all("상장" in it for it in results["sch_list_items"])',
        'any("38.co.kr" in (u or "") for u in results["sch_src_urls"])',
        'results["sch_has_38"]',
        'not results["sch_h_overflow"]',
        'not results["sch_clipped"]',
        'results["sch_privacy_hits"] == []',
        'results["cash_exists"] == 1',
        'results["cash_above_list"]',
        'results["cash_peak"] == cash_peak_text(plan_m)',
        'results["cash_when"].startswith(short_day(plan_m["peak"][0]))',
        'all(n in results["cash_when"] for n in plan_m["peak"][1]["names"][:3])',
        'results["cash_total"] == won_short(plan_m["total"])',
        'results["cash_count"] == str(plan_m["count"])',
        'results["cash_scope"] == plan_m["month_label"]',
        '"추정치입니다" in results["cash_note"]',
        'results["cash_chips"][0] == [plan_m["month_label"], "true"]',
        'results["cash_chips"][1] == [plan_m["all_label"], "false"]',
        'results["cash_chips"][2][1] == "true"',
        '"스팩 제외" in results["cash_chips"][2][0]',
        'results["cash_rows"] == [cash_row_text(it) for it in sorted(IPO["upcoming"]["subscribe"], key=lambda x: str(x.get("start") or "9999"))]',
        'results["cash_est_rows"] >= 1',
        'results["cash_all_peak"] == cash_peak_text(plan_a)',
        'results["cash_all_when"].startswith(short_day(plan_a["peak"][0]))',
        'results["cash_all_total"] == won_short(plan_a["total"])',
        'results["cash_all_count"] == str(plan_a["count"])',
        'results["cash_all_scope"] == plan_a["all_label"]',
        'results["cash_all_pressed"] == ["false", "true", "true"]',
        'results["cash_spac_off_peak"] == cash_peak_text(plan_as)',
        'results["cash_spac_off_total"] == won_short(plan_as["total"])',
        'results["cash_spac_off_count"] == str(plan_as["count"])',
        'results["cash_spac_pressed"] == "false"',
        'results["cash_month_spac_peak"] == cash_peak_text(plan_ms)',
        'results["cash_month_spac_total"] == won_short(plan_ms["total"])',
        'results["cash_month_spac_count"] == str(plan_ms["count"])',
        'results["cash_rows_after"] == results["cash_rows"]',
        'results["cash_restored"] == {"peak": cash_peak_text(plan_m), "chip": "true", "spac": "true"}',
        'all(h >= 28 for h in results["cash_chip_h"])',
        'not results["cash_clipped"]',
        'not results["dark_cash_clipped"]',
        'results["dark_cash_visible"]',
        'results["dark_cash_peak"] == cash_peak_text(plan_m)',
        'results["desktop_cash_peak"] == cash_peak_text(plan_m)',
        'not results["sch_errors"]',
        'results["tab_back_today"]',
        'results["dark_sch_visible"]',
        'not results["dark_sch_overflow"]',
        'results["desktop_sch_cards"] >= 10',
        'not results["desktop_sch_overflow"]',
        'results["deeplink_schedule"]',
        'results["deeplink_cards"] >= 10',
        'results["share_visible"]',
        'results["share_label"].startswith("단톡방에")',
        '"상장" in results["share_label"]',
        'len(results["share_btns"]) == 2',
        'results["share_ids"] == ["share-sub", "share-listing"]',
        'results["share_icons"] == 2',
        'results["share_btns"][0] == "청약 정보 공유"',
        'results["share_btns"][1] == "상장 정보 공유"',
        'results["share_disabled"] == [False, False]',
        'min(results["share_btn_h"]) >= 44',
        'all(ws == "nowrap" for ws in results["share_white_space"])',
        'results["share_grid"]["count"] == 2',
        'results["share_grid"]["same_row"]',
        'results["share_grid"]["equal_w"]',
        'results["share_grid"]["fills"]',
        'results["share_grid"]["fit"]',
        'results["share_btn_style"]["sub"]["bg_ok"]',
        'results["share_btn_style"]["sub"]["fg_ok"]',
        'results["share_btn_style"]["sub"]["weight"] >= 700',
        'results["share_btn_style"]["listing"]["bg_ok"]',
        'results["share_btn_style"]["listing"]["fg_ok"]',
        'results["share_btn_style"]["listing"]["border_ok"]',
        'results["share_btn_style"]["listing"]["weight"] >= 600',
        'results["share_placed_ok"]',
        'results["share_native"] == "undefined"',
        'results["share_lines"] >= 3',
        'results["share_head_ok"]',
        'results["share_last_line"] == SITE_URL',
        'results["share_exact"]',
        'results["share_next_fallback"]',
        'results["share_no_summary"]',
        'results["share_no_listing"]',
        'results["share_only_subscribe_names"]',
        'not results["share_privacy_hits"]',
        '"청약 정보" in results["share_copy_toast"]',
        'results["share_copy_label"] == "복사됐어요"',
        'results["share_copy_label_back"] == "청약 정보 공유"',
        'results["share_fallback_clipboard"]',
        '"복사" in results["share_fallback_toast"]',
        'results["list_exact"]',
        'results["list_head_ok"]',
        'results["list_bullets"] == 7',
        'results["list_last_line"] == SITE_URL',
        'results["list_url_once"]',
        'results["list_no_subscribe_name"]',
        'not results["list_privacy_hits"]',
        '"상장 정보" in results["list_copy_toast"]',
        'results["list_copy_label"] == "복사됐어요"',
        'results["list_copy_label_back"] == "상장 정보 공유"',
        'results["stub_share_type"] == "function"',
        'results["stub_share_label"] == "청약 정보 공유"',
        'results["stub_share_toast"] == ""',
        'results["stub_list_label"] == "상장 정보 공유"',
        'results["abort_clipboard_empty"]',
        'results["abort_toast_empty"]',
        'results["abort_label"] == "청약 정보 공유"',
        'not results["abort_errors"]',
        'results["mock_exact"]',
        'results["mock_blocks"] == 2',
        'results["mock_bullets"] == 15',
        'results["mock_opinion"]',
        'results["mock_blank_between"]',
        'results["mock_dropped_unknown"]',
        'results["mock_url_once"]',
        'results["mock_disabled"] == [False, True]',
        'results["mock_labels"] == ["청약 정보 공유", "오늘 상장 없음"]',
        'results["ldisabled"] == [True, False]',
        'results["llabels"] == ["오늘 청약 없음", "상장 정보 공유"]',
        'results["lmock_exact"]',
        'results["lmock_bullets"] == 7',
        'results["lmock_url_once"]',
        'results["ldisabled_no_copy"]',
        'results["disabled_cursor"] == "default"',
        'results["disabled_border"] == "solid"',
        'results["disabled_muted"]',
        'results["lsparse_exact"]',
        'results["lsparse_dropped"]',
        'results["no_ipo_share_visible"]',
        'results["no_ipo_disabled"] == [True, True]',
        'results["no_ipo_btns"][0] == "오늘 청약 없음"',
        'results["no_ipo_btns"][1] == "오늘 상장 없음"',
        'results["no_ipo_clipboard_empty"]',
        'results["no_ipo_toast_empty"]',
        'not results["sub_errors"]',
        'not results["listing_mock_errors"]',
        'not results["sparse_errors"]',
        'bool(results["shared_payload"])',
        'results["shared_payload"].get("url") == SITE_URL',
        'results["shared_payload"].get("title") == "공모주 청약 정보"',
        'results["shared_payload"].get("text") == expected_body(DATA)',
        'SITE_URL not in (results["shared_payload"].get("text") or "")',
        'bool(results["shared_listing_payload"])',
        'results["shared_listing_payload"].get("url") == SITE_URL',
        'results["shared_listing_payload"].get("title") == "공모주 상장 정보"',
        'results["shared_listing_payload"].get("text") == listing_block(DATA)',
        'SITE_URL not in (results["shared_listing_payload"].get("text") or "")',
        '"복사" in results["share_reject_toast"]',
        'results["share_reject_clipboard"]',
        '"복사" in results["list_reject_toast"]',
        'results["list_reject_clipboard"]',
        'results["dark_share_visible"]',
        'results["dark_share_count"] == 2',
        'min(results["dark_share_btns"]) >= 44',
        'results["dark_share_labels"] == ["청약 정보 공유", "상장 정보 공유"]',
        'results["dark_share_grid"]["same_row"]',
        'results["dark_share_grid"]["fit"]',
        'not results["dark_share_overflow"]',
        'results["desktop_share_visible"]',
        'results["desktop_share_labels"] == ["청약 정보 공유", "상장 정보 공유"]',
        'results["desktop_share_disabled"] == [False, False]',
        'results["desktop_share_fit"]',
        'not results["stub_errors"]',
        'not results["reject_errors"]',
        'results["hero_count"] == 1',
        'hero_ok',
        '"다음 청약" in results["next_rows"]',
        'results["next_dday"].startswith("D-")',
        'results["hierarchy_ok"]',
        'results["no_invite_words"]',
        'results["today_has_no_detail"]',
        'results["today_has_no_accordion"]',
        'results["ben_link_visible"]',
        'results["ben_link_text"] == "증권사 개설·현금성 혜택 " + results["ben_link_count"] + "건 보기"',
        'results["ben_link_icon"] == 1',
        'results["ben_link_href"] == "?tab=benefits"',
        'results["ben_link_tab"] == "benefits"',
        'results["ben_link_count"] == str(len(sec_benefits))',
        'results["ben_link_placed"]',
        'results["ben_link_switch"]',
        'results["ben_link_url_ok"]',
        'results["bf_visible"]',
        '[c["id"] for c in results["bf_chips"]] == ["all", "securities", "simple"]',
        'results["bf_chips"][0]["on"]',
        'results["bf_chips"][0]["pressed"] == "true"',
        'results["bf_chips"][1]["pressed"] == "false"',
        'results["bf_chip_row"]["count"] == 3',
        'results["bf_chip_row"]["fit"]',
        'results["bf_chip_row"]["one_row"]',
        'results["bf_chip_counts"] == [str(len(live_benefits)), str(len(sec_benefits)), str(len(simple_benefits))]',
        'results["bf_count"] == len(live_benefits)',
        'len(results["bf_securities"]) == len(sec_benefits) >= 4',
        'len(results["bf_simple"]) == len(simple_benefits) >= 3',
        'results["bf_cats"] == ["securities", "simple"]',
        'results["bf_all_fields"]',
        'results["bf_links_unique"]',
        'all(d.startswith("D-") or d in ("오늘 마감", "상시") for d in results["bf_ddays"])',
        'results["bf_terms_open"]',
        'results["bf_terms_items"] >= 1',
        'results["bf_filter_securities"] == ["securities"] * len(sec_benefits)',
        'results["bf_filter_simple"] == ["simple"] * len(simple_benefits)',
        'results["bf_filter_all"] == (["securities"] * len(sec_benefits) + ["simple"] * len(simple_benefits))',
        'not results["bf_clipped"]',
        'results["bf_scroll_top"] == results["viewport_width"]',
        'results["inject_cards"] == len(live_benefits) + len(inj_live)',
        'results["expired_hidden"]',
        'results["today_shown"]',
        'results["always_shown"]',
        'results["note_mentions_hidden"]',
        'results["inject_link_href"].startswith("https://example.com/")',
        'results["inject_link_target"] == "_blank"',
        '"앱에서 이벤트 신청" in results["inject_link_how"]',
        'results["dark_bf_visible"]',
        'results["dark_bf_cards"] == len(live_benefits)',
        'not results["dark_bf_overflow"]',
        'results["desktop_ben_link"]',
        'results["desktop_bf_cards"] == len(live_benefits)',
        'not results["desktop_bf_overflow"]',
        'results["deeplink_benefits"]',
        'results["deeplink_bf_cards"] == len(live_benefits)',
        'results["deeplink_bf_chip"] == f"전체 {len(live_benefits)}"',
        'not results["errors"]',
        'results["support_visible"]',
        'results["support_title"].endswith("커피 한 잔 응원하기")',
        'results["support_href"] == "https://qr.kakaopay.com/Ej7j2Gwco"',
        'results["support_target"] == "_blank"',
        '"noopener" in (results["support_rel"] or "")',
        '"noreferrer" in (results["support_rel"] or "")',
        'results["support_links"] == 1',
        'results["support_above_footer"]',
        'results["support_btn_h"] >= 36',
        'results["support_title_style"]["size"] == "14px"',
        'results["support_title_style"]["weight"] == "700"',
        'results["support_title_style"]["color_is_ink"]',
        'results["support_btn_style"]["bg"] == "rgb(254, 229, 0)"',
        'results["support_btn_style"]["color"] == "rgb(25, 25, 25)"',
        'results["support_btn_style"]["weight"] == "700"',
        'results["support_btn_style"]["border_w"] == "1px"',
        'results["support_btn_style"]["radius"] == "10px"',
        'results["support_btn_style"]["card_border"] == "1px rgb(229, 232, 235)"',
        'results["support_btn_style"]["card_radius"] == "14px"',
        'results["support_css_hover"]',
        'results["support_css_dark"]',
        'not results["support_btn_emoji"]',
        'results["dark_support_visible"]',
        'results["dark_support_btn_style"]["bg"] == "rgb(254, 229, 0)"',
        'results["dark_support_btn_style"]["color"] == "rgb(25, 25, 25)"',
        'not results["inject_errors"]',
        'not results["dark_errors"]',
        'not results["desktop_errors"]',
        'not results["h_overflow"]',
        'not results["clipped"]',
        'not results["privacy_hits"]',
        'not results["desktop_h_overflow"]',
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
    for k, v in results.items():
        print(f"{k}: {v}")
    print("\nRESULT:", "PASS" if ok else "CHECK")


if __name__ == "__main__":
    asyncio.run(main())
