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
- 전체 일정 최상단 필요 금액 카드(#cash-card): 증거금 = 공모가 × 최소청약주수 × 증거금률
  (일반 50%·스팩 100%, 최소 주수는 증권신고서 확인값, 없으면 10주 추정, 희망가면 상단) —
  종목 행마다 `균등 약 10만원 50주`(확인) / `균등 약 6.8만원 10주 추정`(미확인, 툴팁 `최소 청약 주수 미확인 · 10주 기준 추정`),
  날짜별 동시 묶임(start ≤ d < 환불일)의 최댓값(피크)·피크 날짜·겹치는 종목·단순 합계,
  이번 달/전체·스팩 제외 칩이 같은 데이터로 즉시 재계산(기대값은 data.json 에서 같은 규칙으로 계산),
  가로 잘림 없음, 다크·데스크톱 동일 값
- 상단 3탭: 기본 '오늘 요약', '전체 일정'(?tab=schedule) · '혜택'(?tab=benefits) —
  390px에서 3탭이 한 줄(같은 폭·잘림 없음), 다크·데스크톱에서도 가로 스크롤 없이 렌더
- 오늘 요약 하단 한 줄 배너(.ben-link): 증권사·금융 혜택 N건 · 누르면 혜택 탭 전환 · 혜택 상세는 없음
- 혜택 탭: 칩 3개(전체·증권사·금융·간편 이벤트·설문, 건수 포함) 즉시 필터링,
  카드마다 카테고리·D-day·혜택명·핵심 금액·대상·마감·기간·공식 링크(_blank)·
  '유의사항·신청 방법' 펼침, 만료 숨김(테스트 주입), 개인정보 문구 0건
- 주말 모드(`?date=토·일`, app.js 는 KST 기준 토·일 자동 판별): `오늘 요약` 첫 카드가
  `.hero.is-weekend` 로 바뀝니다. 배지 `주말 휴장` + `다음 주 청약 미리보기`, 날짜 줄은
  `2026년 11월 21일 토요일 · 주말 휴장`, 갱신 줄은 `직전 영업일(11/20) 수집 · 월요일 07:30 갱신`,
  히어로는 `다음 주 청약 N건` + 다음 주 월~일 `ipo.upcoming.subscribe` 종목(기간·공모가·
  주관·환불·스팩 태그)과 **다음 주 균등 최소증거금 피크**(날짜별 동시 묶임 최댓값 — 기대값은
  data.json 에서 같은 규칙으로 계산), 직전 영업일 상장은 `직전 영업일(11/20) 상장` 보조 카드로
  내려가고 `오늘 청약`·`오늘 상장` 문구는 0건 — 토·일 모두 같은 미리보기, 다음 주 0건이면 빈 상태 문구,
  다크·데스크톱 동일 값, 평일(`?date=수집일`)에는 주말 카드 없음, `?date` 없는 실제 오늘(KST)
  로딩이 그날(평일/주말)에 맞는 카드를 내는지까지 확인합니다.

검증 기준일은 data.json 의 수집일(마지막 영업일)로 고정(`?date=`)해, 검증을 어느 요일에
돌려도 같은 기대값으로 평일 화면을 보고 주말 화면은 따로 더합니다.
"""
import asyncio
import datetime as dt
import functools
import http.server
import json
import math
import re
import socketserver
import sys
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

# ── 홈 화면에 앱으로 추가(PWA) 검증용 ───────────────────
# 헤드리스 크롬은 설치 조건을 스스로 판단하지 않으므로( beforeinstallprompt 자동 발생 없음),
# 브라우저가 보내는 것과 같은 모양의 이벤트를 직접 던져 app.js 의 처리를 봅니다.
KAKAO_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Mobile/15E148 KAKAOTALK 10.4.5")
INSTALL_TIP = "하단 공유(□↑) 버튼 → '홈 화면에 추가'를 누르면 앱처럼 바로 열려요"
INSTALL_LABEL = "홈 화면에 앱으로 추가"

PROMPT_JS = """(() => {
  window.__prompted = 0;
  window.__installEvents = (window.__installEvents || 0) + 1;
  const e = new Event('beforeinstallprompt');
  e.prompt = () => { window.__prompted += 1; };
  e.userChoice = Promise.resolve({ outcome: window.__choice || 'accepted' });
  window.dispatchEvent(e);
  return true;
})()"""

IOS_PROMPT_JS = PROMPT_JS.replace("'accepted'", "'dismissed'")   # iOS 에서는 이벤트가 오지 않지만 대비

STANDALONE_JS = """(() => {
  const orig = window.matchMedia.bind(window);
  window.matchMedia = function (q) {
    if (String(q).indexOf('display-mode: standalone') >= 0) {
      return { matches: true, media: String(q), onchange: null,
               addListener() {}, removeListener() {},
               addEventListener() {}, removeEventListener() {},
               dispatchEvent() { return false; } };
    }
    return orig(q);
  };
})();"""

IOS_STANDALONE_JS = """(() => {
  try { Object.defineProperty(window.navigator, 'standalone', { get: () => true }); } catch (e) {}
})();"""


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

# ── 검증 기준일 고정 ──────────────────────────
# 화면과 기대값을 같은 날짜로 맞춰야 요일과 무관하게 결과가 같습니다.
# data.json 의 수집일(date)은 '직전 영업일'이라 평일 화면을 그대로 재현합니다.
# app.js 는 ?date=YYYY-MM-DD 로 오늘을 고정할 수 있습니다(기본은 실제 KST 날짜).
_m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(DATA.get("date") or ""))
DAY = (dt.date(int(_m[1]), int(_m[2]), int(_m[3])) if _m else TODAY)
TODAY = DAY
DAY_PARAM = f"date={DAY.isoformat()}"

# 개인정보 검사어가 없어도 항상 검사하는 기본 문구
ALWAYS_TERMS = ["야탑", "판교", "이매", "쌍둥이", "육아", "어린이집", "휴대폰", "배송지"]

# ── 블로그 배너 퍼가기 기대값 ──────────────────
# index.html · app.js 와 같은 문자열입니다(티스토리·워드프레스 HTML 모드에 붙이는 코드).
BANNER_URL = "https://ipo.mydon.kr/banner.png"
BANNER_HTML = ('<a href="https://ipo.mydon.kr" target="_blank" rel="noopener">'
               '<img src="' + BANNER_URL + '" alt="마이돈 — 오늘의 공모주 1분 요약" '
               'width="800" height="280" style="max-width:100%;height:auto"></a>')

# 배너 생성기(scripts/generate_banner.py) — 화면과 같은 규칙으로 금액을 고르는지 대조용
sys.path.insert(0, str(ROOT / "scripts"))
try:
    import generate_banner as banner_mod
except Exception:  # Pillow·폰트가 없는 환경에서는 이 대조만 건너뜁니다
    banner_mod = None


def png_size(path):
    """PNG 헤더만 읽어 (width, height) — PNG 가 아니면 None."""
    try:
        b = Path(path).read_bytes()[:24]
    except OSError:
        return None
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return (int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big"))


# ── 전체 일정 · 균등 최소증거금 기대값 ──────────────────────
# app.js 의 offerPrice·depositOf·lockUntil·wonShort·cashPlan 과 같은 규칙입니다.
# (check_prod.py 도 이 함수들을 가져다 씁니다.)
CASH_RATE = 0.5          # 일반 공모주(리츠 포함) — 청약증거금 50%
CASH_RATE_SPAC = 1.0     # 스팩(기업인수목적회사) — 청약증거금 100%
DEFAULT_MIN_SHARES = 10


def is_spac(item):
    """app.js isSpac — 종목명에 '스팩'·'기업인수목적'(리츠는 플래그만 있고 증거금률이 달라 제외)."""
    name = str((item or {}).get("name") or "")
    return ("스팩" in name) or ("기업인수목적" in name)


def cash_rate(item):
    return CASH_RATE_SPAC if is_spac(item) else CASH_RATE


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
    """최소청약 증거금 = 공모가 × 최소청약주수 × 증거금률 (없으면 10주)."""
    p = cash_price((item or {}).get("price"))
    if not p:
        return None
    try:
        raw = int((item or {}).get("minShares") or 0)
    except (TypeError, ValueError):
        raw = 0
    shares = raw if raw > 0 else DEFAULT_MIN_SHARES
    rate = cash_rate(item)
    return {
        "amount": int(round(p["value"] * shares * rate)),
        "price": p["value"], "shares": shares, "rate": rate,
        "spac": rate == CASH_RATE_SPAC,
        "shares_estimated": raw <= 0, "price_estimated": p["estimated"],
        "price_range": p["range"],
    }


def cash_shares_tag(dep, prefix="sc"):
    """app.js sharesTag — 확인된 주수는 '50주', 확인 전이면 '10주 추정' 칩."""
    if dep["shares_estimated"]:
        return "10주 추정"
    if dep["shares"] == DEFAULT_MIN_SHARES:
        return ""
    return f"{dep['shares']}주"


def cash_row_text(item):
    """종목 행의 `.sc-dep` 문자열 — '균등 약 10만원 50주' / '균등 약 6.8만원 10주 추정'."""
    dep = cash_deposit(item)
    if not dep:
        return None
    text = "균등 " + ("약 " if dep["price_estimated"] else "") + won_short(dep["amount"])
    tag = cash_shares_tag(dep)
    return (text + " " + tag) if tag else text


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
    scoped = [it for it in picked if not is_spac(it)] if no_spac else picked

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


def cash_dep_title(item):
    """app.js depositBasis — `.sc-dep` 툴팁 문자열."""
    dep = cash_deposit(item)
    if not dep:
        return None
    price = ("희망가 상단" if dep["price_range"]
             else ("희망가" if dep["price_estimated"] else "확정가"))
    shares = ("최소 청약 주수 미확인 · 10주 기준 추정" if dep["shares_estimated"]
              else f"증권신고서 최소 {dep['shares']}주")
    rate = int(round(dep["rate"] * 100))
    return (f"{price} · {shares} · 증거금 {rate}%" + ("(스팩)" if dep["spac"] else "") + " 기준")


def cash_shares_rows(items):
    """`.sc-shares` 칩이 붙는 행 — 확인된 최소 주수가 10주가 아닌 종목만."""
    out = []
    for it in sorted(items, key=lambda x: str(x.get("start") or "9999")):
        dep = cash_deposit(it)
        if dep and not dep["shares_estimated"] and dep["shares"] != DEFAULT_MIN_SHARES:
            out.append([it["name"], f"{dep['shares']}주",
                        f"증권신고서 최소 {dep['shares']}주 · {dep['shares']}주부터 청약"])
    return out


def cash_peak_text(plan):
    return ("약 " + won_short(plan["peak"][1]["amount"])) if plan["peak"] else "0원"


def short_day(d):
    """11/24(화) — JS shortDay 와 같은 표기(일요일=0)."""
    return f"{d.month}/{d.day}(" + "일월화수목금토"[(d.weekday() + 1) % 7] + ")"


def kor_day(d):
    """2026년 11월 22일 일요일 — JS korDay 와 같은 표기."""
    return (f"{d.year}년 {d.month}월 {d.day}일 "
            + "일월화수목금토"[(d.weekday() + 1) % 7] + "요일")


# ── 주말 모드 · 다음 주 청약 미리보기 기대값 ─────────────
# app.js 의 nextMonday·weekPreview·weekItem 과 같은 규칙입니다.
def next_monday(today):
    """토·일 다음 월요일."""
    return today + dt.timedelta(days=2 if today.weekday() == 5 else 1)


def cash_names(names):
    """3개까지만 이름, 더 많으면 '외 N'."""
    head = "·".join(names[:3])
    return f"{head} 외 {len(names) - 3}" if len(names) > 3 else head


def week_preview(ipo, today):
    """다음 주(월~일) 청약 종목 · 날짜별 동시 묶임 피크 · 기간 라벨."""
    mon = next_monday(today)
    end = mon + dt.timedelta(days=7)
    items = []
    for it in ((ipo or {}).get("upcoming") or {}).get("subscribe") or []:
        s = parse_iso(it.get("start"))
        if s and mon <= s < end:
            items.append(it)
    items.sort(key=lambda it: str(it.get("start") or ""))

    rows = []
    for it in items:
        dep, until, start = cash_deposit(it), cash_lock_until(it), parse_iso(it.get("start"))
        if dep and until and start:
            rows.append((it, dep, until, start))

    days = {}
    for it, dep, until, start in rows:
        d = start
        while d < until and d < end:
            if d >= mon:
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
        "mon": mon,
        "end": end,
        "items": items,
        "names": [it.get("name") for it in items],
        "spac": [it.get("name") for it in items if is_spac(it)],
        "label": short_day(mon) + "~" + short_day(mon + dt.timedelta(days=4)),
        "peak": peak,
        "peak_text": ("약 " + won_short(peak[1]["amount"])) if peak else None,
        "peak_names": cash_names(peak[1]["names"]) if peak else "",
        "deps": [cash_row_text(it) for it in items],
        "whens": [
            short_day(parse_iso(it.get("start")))
            + ("~" + short_day(parse_iso(it.get("end")))
               if it.get("end") and it.get("end") != it.get("start") else "")
            for it in items
        ],
        "total": sum(dep["amount"] for _it, dep, _u, _s in rows),
    }


def serve():
    # .webmanifest 를 Cloudflare Pages 와 같은 타입으로 내려 준다(기본은 octet-stream).
    http.server.SimpleHTTPRequestHandler.extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".webmanifest": "application/manifest+json",
    }
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


def min_shares_day(body):
    """최소 주수 표기 mock — 신영스팩12호는 증권신고서 50주(확인), 에이엔에이치스트럭쳐는 minShares 없음(추정).

    실제 data.json 은 예정 종목 전부의 minShares 가 채워져 있어 '10주 추정' 표기를 볼 수 없으므로,
    확인/미확인이 한 목록에서 구분되는지 이 mock 으로 고정합니다.
    """
    body = json.loads(json.dumps(body))
    for it in ((body.get("ipo") or {}).get("upcoming") or {}).get("subscribe") or []:
        if it.get("name") == "신영스팩12호":
            it["minShares"] = 50
            it["price"] = "희망 2,000원"
            it["spac"] = True
        elif it.get("name") == "에이엔에이치스트럭쳐":
            it.pop("minShares", None)
            it["price"] = "희망 11,200~13,600원"
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

# 장 시작 전(07:30~09:00) 상장 예정 mock — 시초·종가 줄 대신 상장 시각, 가격제한폭은 공모가에서 계산
MOCK_LISTING_PREMARKET = (
    "📈 하나에어로다이내믹스 (11/20 상장)\n"
    "\n"
    "* 상장 시각: 09:00 (장 시작 전)\n"
    "* 공모가: 5,700원\n"
    "* 최종 확약률: 72.69%\n"
    "* 상장일 유통물량: 17.30% (약 175억)\n"
    "* 가격제한폭: 3,420원 ~ 22,800원 (60~400%)\n"
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


def listing_premarket_day(body, band=""):
    """장 시작 전(07:30~09:00) 상장 예정 — 시초가·종가·직전 체결가가 모두 비어 있는 상태.
    data.json 의 07:30 수집분과 같은 모양(openPrice·closePrice·priceBand 빈 문자열)입니다."""
    body = json.loads(json.dumps(body))
    ipo = body.setdefault("ipo", {})
    ipo["subscribe"] = []
    ipo["next"] = {}
    ipo["listing"] = {
        "hasListing": True, "date": "2026-11-20", "name": "하나에어로다이내믹스",
        "code": "271160", "market": "코스닥 · 벤처기업부", "badge": "오늘 상장",
        "brokers": "IBK투자증권", "ipoPrice": "5,700원",
        "openPrice": "", "openChange": "", "closePrice": "", "closeChange": "",
        "earlyPrice": "", "earlyChange": "",
        "lockupRate": "72.69%", "floatSummary": "17.30% (약 175억)",
        "priceBand": band, "shareSummary": "",
        "points": [
            "오늘 흐름: 09:00 코스닥 상장 예정 · 공모가 5,700원 기준 가격제한폭 3,420~22,800원",
            "물량·확약: 첫날 유통 17.30%(약 175억) · 최종 확약 72.69%",
        ],
    }
    return body


def listing_premarket_band_day(body):
    """장 시작 전인데 priceBand 는 이미 적힌 날 — 같은 폭을 두 번 쓰지 않고 그대로 표시."""
    return listing_premarket_day(body, band="3,420원 ~ 22,800원 (60~400%)")


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


def week_empty_day(body):
    """다음 주 청약이 0건인 주말 — 빈 상태 문구 확인용."""
    body = json.loads(json.dumps(body))
    ipo = body.setdefault("ipo", {})
    mon = next_monday(TODAY)
    end = mon + dt.timedelta(days=7)
    up = ipo.setdefault("upcoming", {})
    up["subscribe"] = [it for it in up.get("subscribe") or []
                       if not (parse_iso(it.get("start"))
                               and mon <= parse_iso(it.get("start")) < end)]
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


def listing_pre(item):
    """장 시작 전(07:30~09:00) — 시초가·종가·직전 체결가가 모두 비어 있음(app.js isPreMarket)."""
    return not any(item.get(k) is not None and str(item.get(k)) != ""
                   for k in ("openPrice", "closePrice", "earlyPrice"))


def listing_band(item):
    """가격제한폭 — priceBand 그대로, 없으면 공모가×0.6~×4 (app.js bandText)."""
    band = str(item.get("priceBand") or "").strip()
    if band and not UNKNOWN.match(band):
        return band
    price = str(item.get("ipoPrice") or "")
    if not price or any(t in price for t in ("~", "∼", "희망")):
        return ""
    digits = re.sub(r"[^0-9]", "", price)
    if not digits or int(digits) <= 0:
        return ""
    n = int(digits)
    return f"{math.floor(n * 0.6):,}원 ~ {n * 4:,}원 (60~400%)"


def listing_block(data):
    ipo = data.get("ipo") or {}
    l = ipo.get("listing") or {}
    if not l.get("hasListing") or not str(l.get("name") or "").strip():
        return ""
    when = mdd(l.get("date") or l.get("listingDate") or ipo.get("date") or "")
    head = "📈 " + str(l.get("name")).strip() + (f" ({when} 상장)" if when else "")
    bullets = ["* 상장 시각: 09:00 (장 시작 전)"] if listing_pre(l) else []
    for key, label, chg in LISTING_FIELDS:
        v = (share_value(l, key) or (listing_band(l) if listing_pre(l) else "")) \
            if key == "priceBand" else listing_value(l, key, chg)
        if v:
            bullets.append(f"* {label}: {v}")
    return head + ("\n\n" + "\n".join(bullets) if bullets else "")


def expected_listing_copy(data):
    body = listing_block(data)
    return f"{body}\n{SITE_URL}" if body else ""


async def open_page(browser, inject=None, path=None, init_script=None, mutate=None,
                    pin=True, **ctx_kw):
    """pin=True(기본)면 수집일(평일)로 날짜를 고정해 연다 — 실제 요일과 무관하게 평일 화면을 검증.
    pin=False 면 파라미터 없이 실제 KST 날짜로 열어 프로덕션과 같은 동작을 본다."""
    if path is None:
        path = ""
    if pin and DAY_PARAM not in path:
        path += ("&" if "?" in path else "?") + DAY_PARAM
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

            # ── 블로그 배너 퍼가기 (오늘 요약 맨 아래 · 기본 접힘) ────
            # banner.png 는 scripts/generate_banner.py 가 data.json 으로 만드는 정적 이미지입니다.
            # 접힘 → 누르면 미리보기·코드·복사 버튼이 펼쳐지고, 복사는 클립보드로 확인합니다.
            await page.locator("#tab-today").click()
            await page.wait_for_timeout(250)
            be = page.locator("#banner-embed")
            results["be_visible"] = await be.is_visible()
            results["be_closed"] = {
                "expanded": await page.get_attribute("#be-toggle", "aria-expanded"),
                "body_hidden": await page.evaluate("document.querySelector('#be-body').hidden"),
                "label": (await page.inner_text("#be-toggle .be-txt")).strip(),
            }
            results["be_toggle_h"] = round(await page.evaluate(
                "document.querySelector('#be-toggle').getBoundingClientRect().height"))
            results["be_pos"] = await page.evaluate("""(() => {
                const r = s => document.querySelector(s).getBoundingClientRect();
                return { ben: Math.round(r('#ben-link').bottom),
                         be: Math.round(r('#banner-embed').top),
                         support: Math.round(r('#support').top) };
            })()""")
            results["be_emoji"] = await page.evaluate(
                "/[\\u{1F300}-\\u{1FAFF}\\u{2600}-\\u{27BF}]/u.test(document.querySelector('#banner-embed').textContent)")
            await be.scroll_into_view_if_needed()
            await page.wait_for_timeout(150)
            await be.screenshot(path=str(ROOT / "preview-mobile-banner-closed.png"))
            await page.click("#be-toggle")
            await page.wait_for_timeout(500)
            results["be_open"] = {
                "expanded": await page.get_attribute("#be-toggle", "aria-expanded"),
                "body_hidden": await page.evaluate("document.querySelector('#be-body').hidden"),
                "arrow": await page.evaluate(
                    "getComputedStyle(document.querySelector('.be-arrow')).transform"),
            }
            results["be_img"] = await page.evaluate("""(() => {
                const i = document.querySelector('.be-prev img');
                if (!i) return null;
                const r = i.getBoundingClientRect();
                return { nw: i.naturalWidth, nh: i.naturalHeight, complete: i.complete,
                         src: i.getAttribute('src'), w: Math.round(r.width),
                         h: Math.round(r.height) };
            })()""")
            results["be_preview_link"] = {
                "href": await page.get_attribute(".be-prev", "href"),
                "target": await page.get_attribute(".be-prev", "target"),
                "rel": await page.get_attribute(".be-prev", "rel"),
            }
            results["be_code"] = (await page.inner_text("#be-code")).strip()
            results["be_meta"] = (await page.inner_text(".be-meta")).replace("\n", " ").strip()
            results["be_download"] = await page.get_attribute(".be-meta a", "download")
            results["be_buttons"] = await page.eval_on_selector_all(
                "#banner-embed .be-btn", "els => els.map(e => e.textContent.trim())")
            results["be_btn_h"] = round(min(await page.eval_on_selector_all(
                "#banner-embed .be-btn", "els => els.map(e => e.getBoundingClientRect().height)")))
            results["be_btn_style"] = await page.evaluate("""(() => {
                const probe = v => { const d = document.createElement('div');
                    d.style.color = v; document.body.appendChild(d);
                    const c = getComputedStyle(d).color; d.remove(); return c; };
                const p = getComputedStyle(document.querySelector('#be-copy-html'));
                const s = getComputedStyle(document.querySelector('#be-copy-url'));
                return { primary_bg: p.backgroundColor === probe('var(--blue)'),
                         primary_fg: p.color === 'rgb(255, 255, 255)',
                         second_bg: s.backgroundColor === probe('var(--card)') };
            })()""")

            # 클립보드 — HTML 코드 / 이미지 주소
            await page.evaluate("navigator.clipboard.writeText('')")
            await page.click("#be-copy-html")
            await page.wait_for_timeout(250)
            results["be_clip_html"] = await page.evaluate("navigator.clipboard.readText()")
            results["be_toast_html"] = (await page.inner_text("#toast")).strip()
            results["be_label_html"] = (await page.inner_text("#be-copy-html")).strip()
            await page.wait_for_timeout(1900)
            results["be_label_back"] = (await page.inner_text("#be-copy-html")).strip()
            await page.evaluate("navigator.clipboard.writeText('')")
            await page.click("#be-copy-url")
            await page.wait_for_timeout(250)
            results["be_clip_url"] = await page.evaluate("navigator.clipboard.readText()")
            results["be_toast_url"] = (await page.inner_text("#toast")).strip()
            await be.screenshot(path=str(ROOT / "preview-mobile-banner.png"))
            results["be_clipped"] = await page.evaluate("""(() => {
                const vw = window.innerWidth, bad = [];
                document.querySelectorAll('#banner-embed, #banner-embed *')
                  .forEach(el => {
                    if (el.closest('.sr-only')) return;
                    const r = el.getBoundingClientRect();
                    if (r.width && (r.left < -1 || r.right > vw + 1)) {
                      bad.push(el.tagName + '.' + el.className + ' ' +
                               Math.round(r.left) + '~' + Math.round(r.right));
                    }
                  });
                return bad.slice(0, 5);
            })()""")
            results["be_overflow"] = await page.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            results["banner_png"] = png_size(ROOT / "banner.png")

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
            # 최소 주수 칩 — 확인된 값(50주·100주…)은 `.sc-shares`, 확인 전은 `.sc-est`('10주 추정')
            results["cash_shares_rows"] = await page.evaluate("""(() =>
                [...document.querySelectorAll('#sch-subscribe .sc')]
                  .filter(li => li.querySelector('.sc-shares'))
                  .map(li => [li.querySelector('.sc-name').textContent.trim(),
                              li.querySelector('.sc-shares').textContent.trim(),
                              li.querySelector('.sc-shares').title])
            )()""")
            results["cash_est_chips"] = await page.evaluate("""(() =>
                [...document.querySelectorAll('#sch-subscribe .sc-est')]
                  .map(e => [e.textContent.trim(), e.title])
            )()""")
            results["cash_dep_titles"] = await page.evaluate("""(() =>
                [...document.querySelectorAll('#sch-subscribe .sc .sc-dep')]
                  .map(e => e.title)
            )()""")
            # 스팩 행 — 금액 옆 `증거금 100%` 표시(일반 공모주 50%와 구분)
            results["cash_rate_rows"] = await page.evaluate("""(() =>
                [...document.querySelectorAll('#sch-subscribe .sc')]
                  .filter(li => li.querySelector('.sc-rate'))
                  .map(li => [li.querySelector('.sc-name').textContent.trim(),
                              li.querySelector('.sc-rate').textContent.trim(),
                              (li.querySelector('.sc-dep')?.textContent || '').replace(/\\s+/g, ' ').trim()])
            )()""")
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

            # ── 2.65 최소 주수 표기 — 확인된 50주와 미확인(10주 추정)이 한 목록에서 구분되는지 ──
            sctx, spage, s_errors = await open_page(
                browser, path="?tab=schedule", mutate=min_shares_day)
            await spage.wait_for_timeout(250)
            results["ms_rows"] = await spage.evaluate("""(() =>
                [...document.querySelectorAll('#sch-subscribe .sc')]
                  .map(li => [li.querySelector('.sc-name').textContent.trim(),
                              (li.querySelector('.sc-dep')?.textContent || '').replace(/\\s+/g, ' ').trim(),
                              li.querySelector('.sc-dep')?.title || '',
                              li.querySelector('.sc-shares')?.textContent.trim() || '',
                              li.querySelector('.sc-est')?.textContent.trim() || '',
                              li.querySelector('.sc-est')?.title || ''])
                  .filter(r => r[0] === '신영스팩12호' || r[0] === '에이엔에이치스트럭쳐')
            )()""")
            results["ms_note"] = await spage.inner_text("#cash-note")
            # 추정 행은 금액에서 빠지지 않고 '10주 추정'으로만 표시됩니다
            results["ms_estimate_peak"] = await spage.inner_text("#cash-peak")
            results["ms_estimate_plan"] = cash_peak_text(
                cash_plan(min_shares_day(json.loads(json.dumps(DATA)))["ipo"], TODAY))
            results["ms_errors"] = s_errors
            await sctx.close()

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
            results["lday_hprice_class"] = await gpage.get_attribute(".hero .hprice", "class")
            results["lday_price_text"] = (await gpage.inner_text(".hero .hprice b")).strip()
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

            # ── 2.7c 장 시작 전(07:30~09:00) 상장 예정 — 빈 가격 줄 대신 '09:00 상장 예정' ────
            # 시초가 전에는 openPrice·closePrice·earlyPrice 가 모두 비어 있다.
            # 예전에는 <div class="hprice"><b></b></div> 로 빈 줄이 생겼으니 그 자리를 대체 문구로 바꿨는지 봅니다.
            pctx, ppage, p_errors = await open_page(browser, mutate=listing_premarket_day)
            await ppage.wait_for_timeout(250)
            results["pre_hero_class"] = await ppage.get_attribute(".hero", "class")
            results["pre_hprice_class"] = await ppage.get_attribute(".hero .hprice", "class")
            results["pre_price_text"] = (await ppage.inner_text(".hero .hprice b")).strip()
            results["pre_band_text"] = (await ppage.inner_text(".hero .hprice span")).strip()
            results["pre_price_box"] = await ppage.evaluate("""(() => {
                const b = document.querySelector('.hero .hprice b');
                const s = document.querySelector('.hero .hprice span');
                const r = b.getBoundingClientRect(), h = document.querySelector('.hero .hprice');
                return {
                    w: Math.round(r.width), h: Math.round(r.height),
                    fs: getComputedStyle(b).fontSize,
                    b_fit: b.scrollWidth <= Math.round(r.width) + 1,
                    s_fit: s.scrollWidth <= h.clientWidth + 1,
                };
            })()""")
            results["pre_meta"] = (await ppage.inner_text(".hero .hmeta")).replace("\n", " ")
            results["pre_flags"] = await ppage.eval_on_selector_all(
                ".hero .flag", "els => els.map(e => e.textContent.trim())")
            results["pre_overflow"] = await ppage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            await ppage.locator(".hero").screenshot(
                path=str(ROOT / "preview-mobile-listing-premarket.png"))
            await ppage.locator("#share-listing").click()
            await ppage.wait_for_timeout(350)
            pclip = await ppage.evaluate("navigator.clipboard.readText()")
            results["pre_share"] = pclip
            results["pre_share_exact"] = pclip == f"{MOCK_LISTING_PREMARKET}{SITE_URL}"
            results["pre_share_band_once"] = pclip.count("* 가격제한폭:") == 1
            results["pre_share_no_blank"] = not any(
                ln.strip() == "*" for ln in pclip.split("\n"))
            results["pre_errors"] = p_errors
            await pctx.close()

            # priceBand 가 이미 적힌 장 시작 전 — 공모가에서 다시 계산해 두 번 쓰지 않음
            bctx, bpage, b_errors = await open_page(browser, mutate=listing_premarket_band_day)
            await bpage.wait_for_timeout(250)
            results["pre_band_day_text"] = (await bpage.inner_text(".hero .hprice span")).strip()
            await bpage.locator("#share-listing").click()
            await bpage.wait_for_timeout(350)
            results["pre_band_day_exact"] = (await bpage.evaluate(
                "navigator.clipboard.readText()")) == f"{MOCK_LISTING_PREMARKET}{SITE_URL}"
            results["pre_band_errors"] = b_errors
            await bctx.close()

            # 다크·데스크톱에서도 같은 자리·같은 문구 (카드 배경·글자색만 바뀜)
            dctx, dpage, d_errors = await open_page(browser, mutate=listing_premarket_day,
                                                    init_script=DARK_PREF)
            await dpage.wait_for_timeout(250)
            results["pre_dark"] = await dpage.evaluate("""(() => {
                const b = document.querySelector('.hero .hprice.is-pre b');
                const c = document.querySelector('.hero');
                return b ? { color: getComputedStyle(b).color,
                             bg: getComputedStyle(c).backgroundColor,
                             text: b.textContent.trim() } : null;
            })()""")
            results["pre_dark_overflow"] = await dpage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            await dpage.locator(".hero").screenshot(
                path=str(ROOT / "preview-mobile-listing-premarket-dark.png"))
            results["pre_dark_errors"] = d_errors
            await dctx.close()

            kctx, kpage, k_errors = await open_page(browser, mutate=listing_premarket_day,
                                                    viewport={"width": 1280, "height": 900},
                                                    is_mobile=False, has_touch=False,
                                                    user_agent=DESKTOP_UA)
            await kpage.wait_for_timeout(250)
            results["pre_desktop"] = await kpage.evaluate("""(() => {
                const b = document.querySelector('.hero .hprice.is-pre b');
                return b ? { fs: getComputedStyle(b).fontSize, text: b.textContent.trim() } : null;
            })()""")
            results["pre_desktop_overflow"] = await kpage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            await kpage.locator(".hero").screenshot(
                path=str(ROOT / "preview-desktop-listing-premarket.png"))
            results["pre_desktop_errors"] = k_errors
            await kctx.close()

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
            # 블로그 배너 퍼가기 — 다크에서도 같은 카드·같은 버튼 위계
            await dpage.locator("#tab-today").click()
            await dpage.wait_for_timeout(250)
            await dpage.click("#be-toggle")
            await dpage.wait_for_timeout(400)
            results["dark_be_visible"] = await dpage.locator("#be-body").is_visible()
            results["dark_be_img"] = await dpage.evaluate("""(() => {
                const i = document.querySelector('.be-prev img');
                return i ? [i.naturalWidth, i.naturalHeight] : null;
            })()""")
            results["dark_be_card"] = await dpage.evaluate("""(() => {
                const c = getComputedStyle(document.querySelector('#be-body'));
                return { bg: c.backgroundColor, radius: c.borderRadius };
            })()""")
            results["dark_be_overflow"] = await dpage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            await dpage.locator("#banner-embed").scroll_into_view_if_needed()
            await dpage.locator("#banner-embed").screenshot(
                path=str(ROOT / "preview-mobile-banner-dark.png"))
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
            await dp.locator("#tab-today").click()
            await dp.wait_for_timeout(250)
            await dp.click("#be-toggle")
            await dp.wait_for_timeout(400)
            results["desktop_be_visible"] = await dp.locator("#be-body").is_visible()
            results["desktop_be_img_w"] = round(await dp.evaluate(
                "document.querySelector('.be-prev img').getBoundingClientRect().width"))
            results["desktop_be_overflow"] = await dp.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            await dp.locator("#banner-embed").scroll_into_view_if_needed()
            await dp.locator("#banner-embed").screenshot(
                path=str(ROOT / "preview-desktop-banner.png"))
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

            # ── 홈 화면에 앱으로 추가 (PWA) ────────────────────────
            # 파일(매니페스트·서비스 워커·아이콘 3종)은 로컬 서버가 그대로 내려 주고,
            # 설치는 OS별 경로를 브라우저 이벤트(Android) / 공유 안내(iOS)로 나눠 확인합니다.
            ictx, ipage, i_errors = await open_page(browser)
            _mf_resp = await ictx.request.get(BASE + "manifest.webmanifest")
            results["pwa_manifest_status"] = _mf_resp.status
            results["pwa_manifest_type"] = _mf_resp.headers.get("content-type", "")
            try:
                _mf = await _mf_resp.json()
            except Exception:
                _mf = {}
            results["pwa_manifest"] = {k: _mf.get(k) for k in (
                "name", "short_name", "start_url", "scope", "display",
                "background_color", "theme_color", "lang")}
            results["pwa_manifest_icons"] = [
                (i.get("src"), i.get("sizes"), i.get("type"), i.get("purpose"))
                for i in (_mf.get("icons") or [])]

            def _png_size_bytes(b):
                return ((int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big"))
                        if len(b) > 24 and b[:8] == b"\x89PNG\r\n\x1a\n" else None)

            _icon_files = {}
            for _p in ("icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png"):
                _r = await ictx.request.get(BASE + _p)
                _b = await _r.body()
                _icon_files[_p] = {"status": _r.status,
                                   "type": _r.headers.get("content-type", ""),
                                   "size": _png_size_bytes(_b)}
            results["pwa_icons"] = _icon_files

            _sw_resp = await ictx.request.get(BASE + "sw.js")
            results["pwa_sw_status"] = _sw_resp.status
            _sw_text = await _sw_resp.text()
            results["pwa_sw_fetch"] = "addEventListener('fetch'" in _sw_text
            # 옛 HTML·data.json 을 고정하지 않는지 — Cache Storage 를 아예 쓰지 않아야 합니다
            results["pwa_sw_no_cache_storage"] = (
                "caches.open" not in _sw_text and "addAll" not in _sw_text
                and "cache.put" not in _sw_text)
            results["pwa_sw_passthrough"] = "fetch(req)" in _sw_text or "fetch(e.request)" in _sw_text

            # 앱 화면(모바일 안드로이드)의 <head> 연결과 기본 숨김 상태
            results["pwa_head"] = await ipage.evaluate("""(() => {
                const m = document.querySelector("link[rel='manifest']");
                const a = document.querySelector("link[rel='apple-touch-icon']");
                const f = document.querySelector("link[rel='icon']");
                const meta = n => { const e = document.querySelector(`meta[name='${n}']`);
                                    return e ? e.getAttribute('content') : null; };
                return {
                    manifest: m && m.getAttribute('href'),
                    apple: a && { href: a.getAttribute('href'), sizes: a.getAttribute('sizes') },
                    icon: f && { href: f.getAttribute('href'), type: f.getAttribute('type'),
                                 sizes: f.getAttribute('sizes') },
                    apple_capable: meta('apple-mobile-web-app-capable'),
                    apple_title: meta('apple-mobile-web-app-title'),
                    mobile_capable: meta('mobile-web-app-capable'),
                };
            })()""")
            await ipage.wait_for_timeout(700)
            results["pwa_sw_scopes"] = await ipage.evaluate(
                "navigator.serviceWorker ? navigator.serviceWorker.getRegistrations().then(rs => rs.map(r => r.scope)) : []")
            # 설치 안내는 beforeinstallprompt 가 오기 전(일반 방문)에는 숨김
            results["install_closed"] = await ipage.evaluate("""(() => {
                const c = document.querySelector('#install');
                const b = document.querySelector('#install-btn');
                return { hidden: c.hidden, visible: !!(c.offsetWidth && c.offsetHeight),
                         label: b.textContent.trim(),
                         expanded: b.getAttribute('aria-expanded') };
            })()""")

            # Android — 설치 창이 뜰 수 있는 상태가 되면 한 줄이 나타나고, 누르면 네이티브 prompt()
            await ipage.evaluate(PROMPT_JS)
            await ipage.wait_for_timeout(250)
            results["install_android"] = await ipage.evaluate("""(() => {
                const c = document.querySelector('#install');
                const b = document.querySelector('#install-btn');
                const r = c.getBoundingClientRect(), rb = b.getBoundingClientRect();
                const bl = document.querySelector('#ben-link').getBoundingClientRect();
                const be = document.querySelector('#banner-embed').getBoundingClientRect();
                return {
                    hidden: c.hidden, visible: !!(c.offsetWidth && c.offsetHeight),
                    label: b.textContent.trim(), btn_h: Math.round(rb.height),
                    tip_hidden: document.querySelector('#install-tip').hidden,
                    svg_icons: c.querySelectorAll('svg').length,
                    placed: bl.bottom <= r.top + 1 && r.bottom <= be.top + 1,
                    card_h: Math.round(r.height),
                    bg: getComputedStyle(c).backgroundColor,
                    radius: getComputedStyle(c).borderRadius,
                };
            })()""")
            results["install_emoji"] = await ipage.evaluate(
                "/[\\u{1F300}-\\u{1FAFF}\\u{2600}-\\u{27BF}]/u.test(document.querySelector('#install').textContent)")
            await ipage.locator("#install").scroll_into_view_if_needed()
            await ipage.wait_for_timeout(200)
            await ipage.locator("#install").screenshot(path=str(ROOT / "preview-mobile-install.png"))
            await ipage.screenshot(path=str(ROOT / "preview-mobile-install-context.png"))

            await ipage.click("#install-btn")
            await ipage.wait_for_timeout(300)
            results["install_prompt_called"] = await ipage.evaluate("window.__prompted")
            results["install_after_accept"] = await ipage.evaluate("""(() => ({
                hidden: document.querySelector('#install').hidden,
                stored: localStorage.getItem('mydon-install-hide'),
                toast: document.querySelector('#toast').textContent.trim()}))()""")
            # 가로 넘침 없음(설치 줄이 들어간 뒤에도)
            results["install_overflow"] = await ipage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            results["install_errors"] = i_errors
            await ictx.close()

            # 설치 창을 닫은 경우(거절) — 이번 화면에서만 숨기고 저장하지는 않는다
            rctx, rpage, _ = await open_page(browser)
            await rpage.evaluate(PROMPT_JS.replace("'accepted'", "'dismissed'"))
            await rpage.wait_for_timeout(200)
            await rpage.click("#install-btn")
            await rpage.wait_for_timeout(250)
            results["install_after_dismiss"] = await rpage.evaluate("""(() => ({
                hidden: document.querySelector('#install').hidden,
                stored: localStorage.getItem('mydon-install-hide')}))()""")
            await rctx.close()

            # × 로 닫으면 localStorage 에 남아 새로고침·재방문에도 다시 뜨지 않는다
            xctx, xpage, _ = await open_page(browser)
            await xpage.evaluate(PROMPT_JS)
            await xpage.wait_for_timeout(200)
            await xpage.click("#install-x")
            await xpage.wait_for_timeout(150)
            results["install_dismiss"] = await xpage.evaluate("""(() => ({
                hidden: document.querySelector('#install').hidden,
                stored: localStorage.getItem('mydon-install-hide')}))()""")
            await xpage.evaluate(PROMPT_JS)          # 설치 알림이 다시 와도
            await xpage.wait_for_timeout(200)
            results["install_dismiss_sticks"] = await xpage.evaluate(
                "document.querySelector('#install').hidden")
            await xpage.reload(wait_until="networkidle")
            await xpage.wait_for_selector("#main:not([hidden])", timeout=8000)
            await xpage.evaluate(PROMPT_JS)          # 새로고침 뒤에도
            await xpage.wait_for_timeout(200)
            results["install_dismiss_persist"] = await xpage.evaluate(
                "document.querySelector('#install').hidden")
            await xctx.close()

            # iOS(Safari) — 설치 API 가 없으니 버튼이 '공유 → 홈 화면에 추가' 안내를 편다
            cctx, cpage, c_errors = await open_page(browser, user_agent=IOS_UA)
            results["install_ios"] = await cpage.evaluate("""(() => {
                const c = document.querySelector('#install');
                const b = document.querySelector('#install-btn');
                return { hidden: c.hidden, visible: !!(c.offsetWidth && c.offsetHeight),
                         label: b.textContent.trim(), expanded: b.getAttribute('aria-expanded'),
                         tip_hidden: document.querySelector('#install-tip').hidden,
                         tip_text: document.querySelector('#install-tip').textContent.trim() };
            })()""")
            await cpage.click("#install-btn")
            await cpage.wait_for_timeout(250)
            results["install_ios_open"] = await cpage.evaluate("""(() => {
                const t = document.querySelector('#install-tip');
                const r = t.getBoundingClientRect();
                return { tip_hidden: t.hidden, tip_text: t.textContent.trim(),
                         tip_visible: !!(t.offsetWidth && t.offsetHeight),
                         tip_fit: t.scrollWidth <= t.clientWidth + 1,
                         expanded: document.querySelector('#install-btn').getAttribute('aria-expanded'),
                         tip_h: Math.round(r.height) };
            })()""")
            results["install_ios_overflow"] = await cpage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            await cpage.locator("#install").screenshot(
                path=str(ROOT / "preview-mobile-install-ios.png"))
            await cpage.click("#install-btn")          # 한 번 더 누르면 접힘
            await cpage.wait_for_timeout(200)
            results["install_ios_close"] = await cpage.evaluate("""(() => ({
                tip_hidden: document.querySelector('#install-tip').hidden,
                expanded: document.querySelector('#install-btn').getAttribute('aria-expanded')}))()""")
            results["install_ios_errors"] = c_errors
            await cctx.close()

            # 카톡·인스타 인앱 브라우저 — '홈 화면에 추가'가 없으니 안내를 꺼내지 않는다
            kctx, kpage, _ = await open_page(browser, user_agent=KAKAO_UA)
            results["install_kakao_hidden"] = await kpage.evaluate(
                "document.querySelector('#install').hidden")
            await kctx.close()

            # 이미 홈 화면(standalone)에서 열었으면 설치 안내는 필요 없음
            sctx, spage, _ = await open_page(browser, init_script=STANDALONE_JS)
            await spage.evaluate(PROMPT_JS)
            await spage.wait_for_timeout(200)
            results["install_standalone_hidden"] = await spage.evaluate(
                "document.querySelector('#install').hidden")
            await sctx.close()
            tctx, tpage, _ = await open_page(browser, user_agent=IOS_UA,
                                             init_script=IOS_STANDALONE_JS)
            results["install_ios_standalone_hidden"] = await tpage.evaluate(
                "document.querySelector('#install').hidden")
            await tctx.close()

            # 데스크톱 — 설치 창이 뜰 수 있는 브라우저(크롬)일 때만 보이고, 아니면 숨김
            gctx, gpage, g_errors = await open_page(
                browser, user_agent=DESKTOP_UA, viewport={"width": 1280, "height": 900},
                is_mobile=False, has_touch=False, device_scale_factor=1, permissions=[])
            results["install_desktop_default"] = await gpage.evaluate(
                "document.querySelector('#install').hidden")
            await gpage.evaluate(PROMPT_JS)
            await gpage.wait_for_timeout(250)
            results["install_desktop"] = await gpage.evaluate("""(() => {
                const c = document.querySelector('#install');
                return { hidden: c.hidden, visible: !!(c.offsetWidth && c.offsetHeight),
                         label: document.querySelector('#install-btn').textContent.trim() };
            })()""")
            results["install_desktop_overflow"] = await gpage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            results["install_desktop_errors"] = g_errors
            await gctx.close()

            # 다크 모드에서도 같은 한 줄·같은 위계
            vctx, vpage, v_errors = await open_page(browser, init_script=DARK_PREF)
            await vpage.evaluate(PROMPT_JS)
            await vpage.wait_for_timeout(250)
            results["install_dark"] = await vpage.evaluate("""(() => {
                const c = document.querySelector('#install');
                return { visible: !!(c.offsetWidth && c.offsetHeight),
                         bg: getComputedStyle(c).backgroundColor,
                         radius: getComputedStyle(c).borderRadius };
            })()""")
            results["install_dark_overflow"] = await vpage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            await vpage.locator("#install").screenshot(
                path=str(ROOT / "preview-mobile-install-dark.png"))
            results["install_dark_errors"] = v_errors
            await vctx.close()

            # 서비스 워커가 실제로 오프라인을 받아 주는지(캐시 없이 패스스루 + 안내 한 장)
            fctx, fpage, f_errors = await open_page(browser)
            await fpage.wait_for_timeout(1200)
            _ctrl = await fpage.evaluate(
                "navigator.serviceWorker.controller ? navigator.serviceWorker.controller.scriptURL : null")
            results["pwa_sw_controller"] = _ctrl
            if _ctrl:
                await fctx.set_offline(True)
                try:
                    await fpage.goto(BASE, wait_until="domcontentloaded", timeout=15000)
                    await fpage.wait_for_timeout(400)
                    results["pwa_offline_fallback"] = "인터넷 연결이 끊겼어요" in (
                        await fpage.inner_text("body"))
                except Exception as _e:
                    results["pwa_offline_fallback"] = f"error: {type(_e).__name__}"
                finally:
                    await fctx.set_offline(False)
            else:
                results["pwa_offline_fallback"] = None      # 컨트롤러가 없으면 판정 보류
            results["pwa_sw_errors"] = f_errors
            await fctx.close()

            # ── 주말 모드 · 다음 주 청약 미리보기 (?date=토·일) ─
            # 평일 화면은 위에서 수집일(금)로 고정해 검증했고, 여기서는 같은 data.json 으로
            # 토요일·일요일에 첫 카드가 '주말 휴장 · 다음 주 청약 미리보기'로 바뀌는지 본다.
            sat = TODAY + dt.timedelta(days=1)
            while sat.weekday() != 5:          # 5 = Saturday
                sat += dt.timedelta(days=1)
            sun = sat + dt.timedelta(days=1)
            wk = week_preview(IPO, sat)
            results["wk_day"] = sat.isoformat()
            results["wk_expect_names"] = wk["names"]
            results["wk_expect_label"] = wk["label"]
            results["wk_expect_peak"] = wk["peak_text"]

            wctx, wpage, w_errors = await open_page(
                browser, path="?date=" + sat.isoformat(), pin=False)
            results["wk_hero_class"] = await wpage.evaluate(
                "(() => { const h = document.querySelector('.hero');"
                " return h ? h.className : 'none'; })()")
            results["wk_hero_count"] = await wpage.locator(".hero").count()
            results["wk_flags"] = await wpage.eval_on_selector_all(
                ".hero .flag", "els => els.map(e => e.textContent.trim())")
            results["wk_title"] = await wpage.evaluate(
                "document.querySelector('.hero .hname').textContent.replace(/\\s+/g, ' ').trim()")
            results["wk_note"] = (await wpage.inner_text(".hero .hernote")).replace("\n", " ")
            results["wk_dateline"] = await wpage.inner_text("#dateline")
            results["wk_sched"] = (await wpage.inner_text("#sched-note")).replace("\n", " ")
            results["wk_doc_title"] = await wpage.title()
            results["wk_names"] = await wpage.eval_on_selector_all(
                "#wk-list .wk-name", "els => els.map(e => e.textContent.trim())")
            results["wk_whens"] = await wpage.eval_on_selector_all(
                "#wk-list .wk-when", "els => els.map(e => e.textContent.trim())")
            results["wk_deps"] = await wpage.eval_on_selector_all(
                "#wk-list .wk-dep", "els => els.map(e => e.textContent.replace(/\\s+/g, ' ').trim())")
            results["wk_spac_tags"] = await wpage.eval_on_selector_all(
                "#wk-list .wk-i",
                "els => els.map(e => e.querySelector('.wk-tag') ? e.querySelector('.wk-name').textContent.trim() : '')")
            results["wk_rate_names"] = await wpage.eval_on_selector_all(
                "#wk-list .wk-i",
                "els => els.map(e => e.querySelector('.wk-rate') ? e.querySelector('.wk-name').textContent.trim() : '')")
            results["wk_peak"] = await opt_text(wpage, "#wk-peak")
            results["wk_peak_when"] = (await opt_text(wpage, "#wk-peak-when")).replace("\n", " ")
            results["wk_cash_note"] = await opt_text(wpage, ".wk-note")
            results["wk_prev_label"] = await opt_text(wpage, "#prev-day .srow .k")
            results["wk_prev_name"] = await opt_text(wpage, "#prev-day .srow b")
            results["wk_prev_lines"] = await wpage.eval_on_selector_all(
                "#prev-day .srow .d", "els => els.map(e => e.textContent.replace(/\\s+/g,' ').trim())")
            results["wk_today_words"] = await wpage.evaluate("""(() => {
                const t = (document.querySelector('#sec-ipo').innerText + ' ' +
                           document.querySelector('#ipo-foot').innerText);
                return ['오늘 청약', '오늘 상장'].filter(w => t.includes(w));
            })()""")
            results["wk_share"] = await wpage.eval_on_selector_all(
                "#share .share-btn",
                "els => els.map(e => ({ id: e.id, label: e.querySelector('.lbl').textContent.trim(),"
                " disabled: e.disabled, h: Math.round(e.getBoundingClientRect().height) }))")
            results["wk_next_band"] = await wpage.locator(".hero-next").count()
            results["wk_overflow"] = await wpage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            results["wk_clipped"] = await wpage.evaluate("""(() => {
                const vw = window.innerWidth, bad = [];
                document.querySelectorAll('#sec-ipo .hero, #sec-ipo .hero *').forEach(el => {
                  const r = el.getBoundingClientRect();
                  if (r.width && (r.left < -1 || r.right > vw + 1)) bad.push(el.className);
                });
                return bad.slice(0, 5);
            })()""")
            results["wk_privacy_hits"] = [t for t in PRIVACY_TERMS + ALWAYS_TERMS
                                          if t in await wpage.evaluate("document.body.innerText")]
            results["wk_errors"] = w_errors
            await wpage.screenshot(path=str(ROOT / "preview-mobile-weekend-first.png"))
            await wpage.screenshot(path=str(ROOT / "preview-mobile-weekend.png"), full_page=True)
            await wctx.close()

            # 일요일도 같은 미리보기(다음 주 월요일 기준) — 토·일 판별이 둘 다 되는지
            suctx, supage, su_errors = await open_page(
                browser, path="?date=" + sun.isoformat(), pin=False)
            results["wk_sun_class"] = await supage.evaluate(
                "(() => { const h = document.querySelector('.hero');"
                " return h ? h.className : 'none'; })()")
            results["wk_sun_names"] = await supage.eval_on_selector_all(
                "#wk-list .wk-name", "els => els.map(e => e.textContent.trim())")
            results["wk_sun_dateline"] = await supage.inner_text("#dateline")
            results["wk_sun_errors"] = su_errors
            await suctx.close()

            # 다음 주 청약 0건 — 빈 상태 문구
            ectx, epage, e_errors = await open_page(
                browser, path="?date=" + sat.isoformat(), mutate=week_empty_day, pin=False)
            results["wk_empty_class"] = await epage.evaluate(
                "(() => { const h = document.querySelector('.hero');"
                " return h ? h.className : 'none'; })()")
            results["wk_empty_text"] = await opt_text(epage, "#wk-empty")
            results["wk_empty_peak"] = await epage.locator("#wk-peak").count()
            results["wk_empty_items"] = await epage.locator("#wk-list .wk-i").count()
            results["wk_empty_title"] = await epage.evaluate(
                "document.querySelector('.hero .hname').textContent.replace(/\\s+/g, ' ').trim()")
            results["wk_empty_errors"] = e_errors
            await epage.screenshot(path=str(ROOT / "preview-mobile-weekend-empty.png"))
            await ectx.close()

            # 다크 모드 · 데스크톱 폭 — 같은 카드가 무너지지 않는지
            wdctx, wdpage, wd_errors = await open_page(
                browser, path="?date=" + sat.isoformat(), pin=False,
                color_scheme="dark", init_script=DARK_PREF)
            results["wk_dark_visible"] = await wdpage.locator("#hero-weekend").is_visible()
            results["wk_dark_peak"] = await opt_text(wdpage, "#wk-peak")
            results["wk_dark_bg"] = await wdpage.evaluate(
                "getComputedStyle(document.querySelector('.hero.is-weekend')).backgroundColor")
            results["wk_dark_overflow"] = await wdpage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            results["wk_dark_errors"] = wd_errors
            await wdpage.screenshot(path=str(ROOT / "preview-mobile-weekend-dark.png"))
            await wdctx.close()

            wdkctx, wdkpage, wdk_errors = await open_page(
                browser, path="?date=" + sat.isoformat(), pin=False,
                viewport={"width": 1280, "height": 900}, is_mobile=False,
                has_touch=False, device_scale_factor=1, permissions=[])
            results["wk_desktop_visible"] = await wdkpage.locator("#hero-weekend").is_visible()
            results["wk_desktop_peak"] = await opt_text(wdkpage, "#wk-peak")
            results["wk_desktop_items"] = await wdkpage.locator("#wk-list .wk-i").count()
            results["wk_desktop_overflow"] = await wdkpage.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1")
            results["wk_desktop_errors"] = wdk_errors
            await wdkpage.screenshot(path=str(ROOT / "preview-desktop-weekend.png"), full_page=True)
            await wdkctx.close()

            # 평일 모드에는 주말 카드가 없어야 한다(수집일 고정 페이지에서 회귀 확인)
            pctx, ppage, p_errors = await open_page(browser)
            results["wk_weekday_absent"] = await ppage.locator("#hero-weekend, #wk-list, #prev-day").count()
            results["wk_weekday_hero"] = await ppage.evaluate(
                "(() => { const h = document.querySelector('.hero');"
                " return h ? h.className : 'none'; })()")
            results["wk_weekday_errors"] = p_errors
            await pctx.close()

            # 실제 오늘(KST)은 자동으로 그 날에 맞는 첫 카드가 떠야 한다 — ?date 없이 열기
            real_kst = dt.datetime.now(KST).date()
            rctx, rpage, r_errors = await open_page(browser, pin=False)
            results["real_kst_day"] = real_kst.isoformat()
            results["real_kst_weekend"] = real_kst.weekday() >= 5
            results["real_kst_class"] = await rpage.evaluate(
                "(() => { const h = document.querySelector('.hero');"
                " return h ? h.className : 'none'; })()")
            results["real_kst_errors"] = r_errors
            await rctx.close()

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
    # 배너 생성기 — 홈페이지와 같은 규칙으로 금액을 고르는지(평일=이번 달·스팩 제외, 주말=다음 주·스팩 포함)
    banner_weekday = banner_mod.build_content(DATA, DAY) if banner_mod else None
    banner_weekend = banner_mod.build_content(DATA, sat) if banner_mod else None

    _conds = [
        'True',
        # 브랜드·공유 제목: 마이돈 키워드와 캐시 버스터가 그대로 실렸는지
        'results["brand"] == "마이돈 · 공모주"',
        'results["brand_nowrap"] == "nowrap"',
        'results["brand_text_lines"] == 1',
        'results["title"].startswith("마이돈 — 공모주 청약 일정·상장일")',
        'results["og_title"] == "오늘의 공모주 청약 일정 — 마이돈"',
        'results["tw_title"] == "오늘의 공모주 청약 일정 — 마이돈"',
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
        '"증권신고서 기준" in results["cash_note"] and "10주 기준" in results["cash_note"]',
        'results["cash_chips"][0] == [plan_m["month_label"], "true"]',
        'results["cash_chips"][1] == [plan_m["all_label"], "false"]',
        'results["cash_chips"][2][1] == "true"',
        '"스팩 제외" in results["cash_chips"][2][0]',
        'results["cash_rows"] == [cash_row_text(it) for it in sorted(IPO["upcoming"]["subscribe"], key=lambda x: str(x.get("start") or "9999"))]',
        'results["cash_est_rows"] == len([1 for it in IPO["upcoming"]["subscribe"] if (cash_deposit(it) or {}).get("shares_estimated")])',
        'results["cash_est_chips"] == [["10주 추정", "최소 청약 주수 미확인 · 10주 기준 추정"]] * results["cash_est_rows"]',
        'results["cash_shares_rows"] == cash_shares_rows(IPO["upcoming"]["subscribe"])',
        'results["cash_dep_titles"] == [cash_dep_title(it) for it in sorted(IPO["upcoming"]["subscribe"], key=lambda x: str(x.get("start") or "9999")) if cash_deposit(it)]',
        'results["cash_rate_rows"] == [[it["name"], "증거금 100%", cash_row_text(it)] for it in sorted(IPO["upcoming"]["subscribe"], key=lambda x: str(x.get("start") or "9999")) if is_spac(it) and cash_row_text(it)]',
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
        # ── 장 시작 전(07:30~09:00) 상장 예정 — 빈 가격 줄 대신 상장 시각·가격제한폭 ────
        'results["lday_hprice_class"] == "hprice"',
        'results["lday_price_text"] == "6,050원"',
        'results["pre_hero_class"] == "hero is-list"',
        'results["pre_hprice_class"] == "hprice is-pre"',
        'results["pre_price_text"] == "09:00 상장 예정"',
        'results["pre_band_text"] == "가격제한폭 3,420원 ~ 22,800원 (60~400%)"',
        'results["pre_price_box"]["w"] > 100 and results["pre_price_box"]["h"] > 0',
        'results["pre_price_box"]["fs"] == "20px"',
        'results["pre_price_box"]["b_fit"] and results["pre_price_box"]["s_fit"]',
        '"공모가" in results["pre_meta"] and "5,700원" in results["pre_meta"]',
        'results["pre_flags"] == ["오늘 상장"]',
        'not results["pre_overflow"]',
        'results["pre_share_exact"]',
        'results["pre_share_band_once"]',
        'results["pre_share_no_blank"]',
        'not results["pre_errors"]',
        'results["pre_band_day_text"] == "가격제한폭 3,420원 ~ 22,800원 (60~400%)"',
        'results["pre_band_day_exact"]',
        'not results["pre_band_errors"]',
        'results["pre_dark"]["text"] == "09:00 상장 예정"',
        'results["pre_dark"]["bg"] == "rgb(23, 23, 28)"',
        'not results["pre_dark_overflow"]',
        'not results["pre_dark_errors"]',
        'results["pre_desktop"]["text"] == "09:00 상장 예정"',
        'results["pre_desktop"]["fs"] == "22px"',
        'not results["pre_desktop_overflow"]',
        'not results["pre_desktop_errors"]',
        'results["no_ipo_share_visible"]',
        'results["no_ipo_disabled"] == [True, True]',
        'results["no_ipo_btns"][0] == "오늘 청약 없음"',
        'results["no_ipo_btns"][1] == "오늘 상장 없음"',
        'results["no_ipo_clipboard_empty"]',
        'results["no_ipo_toast_empty"]',
        'not results["sub_errors"]',
        'not results["ms_errors"]',
        '''results["ms_rows"] == [
            ["신영스팩12호", "균등 약 10만원 50주",
             "희망가 · 증권신고서 최소 50주 · 증거금 100%(스팩) 기준", "50주", "", ""],
            ["에이엔에이치스트럭쳐", "균등 약 6.8만원 10주 추정",
             "희망가 상단 · 최소 청약 주수 미확인 · 10주 기준 추정 · 증거금 50% 기준",
             "", "10주 추정", "최소 청약 주수 미확인 · 10주 기준 추정"]]''',
        '"증권신고서 기준" in results["ms_note"] and "10주 기준 추정치" in results["ms_note"]',
        'results["ms_estimate_peak"] == results["ms_estimate_plan"]',
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
        # ── 블로그 배너 퍼가기 (banner.png + 오늘 요약 맨 아래 접힘) ──────
        'results["banner_png"] == (800, 280)',
        '(banner_weekday or {}).get("card", {}).get("amount") == cash_peak_text(plan_m)',
        '(banner_weekend or {}).get("card", {}).get("amount") == wk["peak_text"]',
        'results["be_visible"]',
        'results["be_closed"]["expanded"] == "false"',
        'results["be_closed"]["body_hidden"]',
        'results["be_closed"]["label"] == "블로그 배너 퍼가기"',
        'results["be_toggle_h"] >= 44',
        'results["be_pos"]["ben"] <= results["be_pos"]["be"] <= results["be_pos"]["support"]',
        'not results["be_emoji"]',
        'results["be_open"]["expanded"] == "true"',
        'not results["be_open"]["body_hidden"]',
        'results["be_open"]["arrow"] not in ("none", "")',
        'results["be_img"]["nw"] == 800 and results["be_img"]["nh"] == 280',
        'results["be_img"]["complete"]',
        'results["be_img"]["src"] == "banner.png"',
        'results["be_img"]["w"] > 200 and results["be_img"]["h"] > 60',
        'results["be_preview_link"]["href"] == BANNER_URL',
        'results["be_preview_link"]["target"] == "_blank"',
        '"noopener" in (results["be_preview_link"]["rel"] or "")',
        'results["be_code"] == BANNER_HTML',
        '"800 × 280" in results["be_meta"]',
        'results["be_download"] == "mydon-ipo-banner.png"',
        'results["be_buttons"] == ["HTML 코드 복사", "이미지 URL 복사"]',
        'results["be_btn_h"] >= 44',
        'results["be_btn_style"]["primary_bg"] and results["be_btn_style"]["primary_fg"]',
        'results["be_btn_style"]["second_bg"]',
        'results["be_clip_html"] == BANNER_HTML',
        'results["be_toast_html"] == "HTML 코드를 복사했어요"',
        'results["be_label_html"] == "복사됐어요"',
        'results["be_label_back"] == "HTML 코드 복사"',
        'results["be_clip_url"] == BANNER_URL',
        'results["be_toast_url"] == "배너 이미지 주소를 복사했어요"',
        'not results["be_clipped"]',
        'not results["be_overflow"]',
        'results["dark_be_visible"]',
        'results["dark_be_img"] == [800, 280]',
        'results["dark_be_card"]["bg"] == "rgb(23, 23, 28)"',
        'results["dark_be_card"]["radius"] == "14px"',
        'not results["dark_be_overflow"]',
        'results["desktop_be_visible"]',
        'results["desktop_be_img_w"] > 400',
        'not results["desktop_be_overflow"]',
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
        # ── 홈 화면에 앱으로 추가 (PWA) ─────────────────────
        'results["pwa_manifest_status"] == 200',
        '"manifest" in results["pwa_manifest_type"] or "json" in results["pwa_manifest_type"]',
        'results["pwa_manifest"]["name"] == "마이돈 — 오늘의 공모주 1분 요약"',
        'results["pwa_manifest"]["short_name"] == "마이돈 공모주"',
        'results["pwa_manifest"]["start_url"] == "/"',
        'results["pwa_manifest"]["scope"] == "/"',
        'results["pwa_manifest"]["display"] == "standalone"',
        'results["pwa_manifest"]["background_color"] == "#f4f6f8"',
        'results["pwa_manifest"]["theme_color"] == "#3182f6"',
        'results["pwa_manifest_icons"] == [("/icons/icon-192.png", "192x192", "image/png", "any"), '
        '("/icons/icon-512.png", "512x512", "image/png", "any")]',
        'results["pwa_icons"]["icons/icon-192.png"]["status"] == 200',
        'results["pwa_icons"]["icons/icon-192.png"]["size"] == (192, 192)',
        'results["pwa_icons"]["icons/icon-512.png"]["status"] == 200',
        'results["pwa_icons"]["icons/icon-512.png"]["size"] == (512, 512)',
        'results["pwa_icons"]["icons/apple-touch-icon.png"]["status"] == 200',
        'results["pwa_icons"]["icons/apple-touch-icon.png"]["size"] == (180, 180)',
        'all("image/png" in v["type"] for v in results["pwa_icons"].values())',
        'results["pwa_sw_status"] == 200',
        'results["pwa_sw_fetch"]',
        'results["pwa_sw_no_cache_storage"]',
        'results["pwa_sw_passthrough"]',
        'results["pwa_head"]["manifest"] == "/manifest.webmanifest"',
        'results["pwa_head"]["apple"] == {"href": "/icons/apple-touch-icon.png", "sizes": "180x180"}',
        'results["pwa_head"]["icon"] == {"href": "/icons/icon-192.png", "type": "image/png", "sizes": "192x192"}',
        'results["pwa_head"]["apple_capable"] == "yes"',
        'results["pwa_head"]["mobile_capable"] == "yes"',
        'results["pwa_head"]["apple_title"] == "마이돈 공모주"',
        'results["pwa_sw_scopes"] in ([SITE_URL + "/"], [BASE])',
        'results["pwa_offline_fallback"] in (True, None)',
        # 설치 안내 한 줄 — 기본 숨김 → Android 는 이벤트 뒤 표시·누르면 prompt()
        'results["install_closed"]["hidden"] and not results["install_closed"]["visible"]',
        'results["install_closed"]["label"] == INSTALL_LABEL',
        'not results["install_android"]["hidden"]',
        'results["install_android"]["visible"]',
        'results["install_android"]["label"] == INSTALL_LABEL',
        'results["install_android"]["btn_h"] >= 44',
        'results["install_android"]["tip_hidden"]',
        'results["install_android"]["svg_icons"] >= 2',
        'results["install_android"]["placed"]',
        'results["install_android"]["card_h"] <= 72',
        'results["install_android"]["bg"] == "rgb(255, 255, 255)"',
        'results["install_android"]["radius"] == "14px"',
        'not results["install_emoji"]',
        'results["install_prompt_called"] == 1',
        'results["install_after_accept"]["hidden"]',
        'results["install_after_accept"]["stored"] == "1"',
        '"홈 화면에 추가" in results["install_after_accept"]["toast"]',
        'not results["install_overflow"]',
        'not results["install_errors"]',
        'results["install_after_dismiss"]["hidden"]',
        'results["install_after_dismiss"]["stored"] is None',
        'results["install_dismiss"]["hidden"]',
        'results["install_dismiss"]["stored"] == "1"',
        'results["install_dismiss_sticks"]',
        'results["install_dismiss_persist"]',
        # iOS — 버튼을 누를 때만 공유 안내가 펼쳐지고, 다시 누르면 접힘
        'results["install_ios"]["visible"]',
        'results["install_ios"]["label"] == INSTALL_LABEL',
        'results["install_ios"]["expanded"] == "false"',
        'results["install_ios"]["tip_hidden"]',
        'not results["install_ios_open"]["tip_hidden"]',
        'results["install_ios_open"]["tip_visible"]',
        'results["install_ios_open"]["tip_text"] == INSTALL_TIP',
        'results["install_ios_open"]["tip_fit"]',
        'results["install_ios_open"]["expanded"] == "true"',
        'results["install_ios_open"]["tip_h"] > 0',
        'not results["install_ios_overflow"]',
        'results["install_ios_close"] == {"tip_hidden": True, "expanded": "false"}',
        'not results["install_ios_errors"]',
        'results["install_kakao_hidden"]',
        'results["install_standalone_hidden"]',
        'results["install_ios_standalone_hidden"]',
        'results["install_desktop_default"]',
        'results["install_desktop"]["visible"]',
        'results["install_desktop"]["label"] == INSTALL_LABEL',
        'not results["install_desktop_overflow"]',
        'not results["install_desktop_errors"]',
        'results["install_dark"]["visible"]',
        'results["install_dark"]["bg"] == "rgb(23, 23, 28)"',
        'results["install_dark"]["radius"] == "14px"',
        'not results["install_dark_overflow"]',
        'not results["install_dark_errors"]',
        'not results["pwa_sw_errors"]',
        # ── 주말 모드 · 다음 주 청약 미리보기 ────────────────────
        'results["wk_hero_class"] == "hero is-weekend"',
        'results["wk_hero_count"] == 1',
        'results["wk_flags"] == ["주말 휴장", "다음 주 청약 미리보기"]',
        'results["wk_dateline"] == kor_day(sat) + " · 주말 휴장"',
        '"직전 영업일" in results["wk_sched"]',
        '"월요일 07:30" in results["wk_sched"]',
        'mdd(IPO.get("date")) in results["wk_sched"]',
        'results["wk_doc_title"].endswith(short_day(sat))',
        'results["wk_title"] == "다음 주 청약 " + str(len(wk["items"])) + "건"',
        'results["wk_note"] == wk["label"] + " · 직전 영업일(" + mdd(IPO.get("date")) + ") 수집"',
        'results["wk_names"] == wk["names"]',
        'results["wk_whens"] == wk["whens"]',
        'results["wk_deps"] == wk["deps"]',
        'all(t in results["wk_spac_tags"] for t in wk["spac"])',
        '[n for n in results["wk_rate_names"] if n] == wk["spac"]',
        'results["wk_peak"] == wk["peak_text"]',
        'results["wk_peak_when"].startswith(short_day(wk["peak"][0]))',
        'all(n in results["wk_peak_when"] for n in wk["peak"][1]["names"][:3])',
        '"추정" in results["wk_cash_note"] and "스팩 포함" in results["wk_cash_note"]',
        'results["wk_prev_label"] == "직전 영업일(" + mdd(IPO["listing"].get("date")) + ") 상장"',
        'results["wk_prev_name"] == IPO["listing"]["name"]',
        'any("공모가" in ln for ln in results["wk_prev_lines"])',
        'results["wk_today_words"] == []',
        '[b["label"] for b in results["wk_share"]] == ["청약 정보 공유", "상장 정보 공유"]',
        'min(b["h"] for b in results["wk_share"]) >= 44',
        'results["wk_next_band"] == 0',
        'not results["wk_overflow"]',
        'not results["wk_clipped"]',
        'not results["wk_privacy_hits"]',
        'not results["wk_errors"]',
        'results["wk_sun_class"] == "hero is-weekend"',
        'results["wk_sun_names"] == wk["names"]',
        'results["wk_sun_dateline"] == kor_day(sun) + " · 주말 휴장"',
        'not results["wk_sun_errors"]',
        'results["wk_empty_class"] == "hero is-weekend"',
        'results["wk_empty_title"] == "다음 주 청약 0건"',
        '"청약 예정 종목이 없어요" in results["wk_empty_text"]',
        'results["wk_empty_peak"] == 0',
        'results["wk_empty_items"] == 0',
        'not results["wk_empty_errors"]',
        'results["wk_dark_visible"]',
        'results["wk_dark_peak"] == wk["peak_text"]',
        'results["wk_dark_bg"] == "rgb(23, 23, 28)"',
        'not results["wk_dark_overflow"]',
        'not results["wk_dark_errors"]',
        'results["wk_desktop_visible"]',
        'results["wk_desktop_peak"] == wk["peak_text"]',
        'results["wk_desktop_items"] == len(wk["items"])',
        'not results["wk_desktop_overflow"]',
        'not results["wk_desktop_errors"]',
        'results["wk_weekday_absent"] == 0',        'results["wk_weekday_hero"] in ("hero is-list", "hero is-empty", "hero")',
        'not results["wk_weekday_errors"]',
        '("is-weekend" in results["real_kst_class"]) == results["real_kst_weekend"]',
        'not results["real_kst_errors"]',
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
