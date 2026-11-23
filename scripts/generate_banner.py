#!/usr/bin/env python3
"""블로그·티스토리·깃허브에 붙이는 요약 배너(banner.png) 생성기.

data.json 을 읽어 800×280 PNG 한 장을 만듭니다. 블로그 본문 상단에 넣어도
한 줄로 읽히도록 **라벨 · 기준일 · 핵심 요약(오늘 청약/상장 또는 다음 청약 일정) ·
균등 최소증거금 피크 · 주소**만 담습니다.

  python3 scripts/generate_banner.py            # 오늘(KST) 기준
  python3 scripts/generate_banner.py --date 2026-11-24   # 기준일 고정(확인용)
  python3 scripts/generate_banner.py --out /tmp/b.png    # 경로 바꾸기

계산 규칙은 app.js · check_render.py 와 같습니다.
  · 증거금 = 공모가 × 최소청약주수(minShares, 없으면 10주) × 증거금률 / 희망가면 상단
    (일반 공모주 50%, 스팩·기업인수목적회사 100%)
  · 자금이 묶이는 구간은 청약 시작일 ≤ d < 환불일
  · 피크 = 날짜별로 동시에 묶이는 금액의 최댓값
  · 평일은 '이번 달 · 스팩 제외'(전체 일정 탭 카드와 같은 조건),
    주말은 '다음 주(월~일) · 스팩 포함'(주말 히어로와 같은 조건)을 씁니다.

폰트: `scripts/fonts/NanumGothic-Bold.ttf`(저장소 동봉) 우선, 없으면 시스템 한글 폰트.
한글이 깨지지 않도록 폰트를 찾지 못하면 만들지 않고 종료합니다(빈 네모 배너 방지).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = Path(__file__).resolve().parent / "fonts"
KST = dt.timezone(dt.timedelta(hours=9))

W, H = 800, 280          # 최종 크기(블로그 본문 폭에 맞춘 가로형)
S = 2                    # 2배로 그린 뒤 줄여서 글자 가장자리를 부드럽게

BG = "#ffffff"
SUNKEN = "#f7f8f9"
LINE = "#eef1f4"
LINE2 = "#e5e8eb"
INK = "#191f28"
INK2 = "#4e5968"
INK3 = "#8b95a1"
BLUE = "#3182f6"
BLUE_INK = "#1b64da"

DEPOSIT_RATE = 0.5
DEPOSIT_RATE_SPAC = 1.0          # 스팩(기업인수목적회사) — 청약증거금 100%
DEFAULT_MIN_SHARES = 10
WEEKDAY_KO = "월화수목금토일"          # date.weekday() 0=월

# ── 폰트 ────────────────────────────────────────────────────────────────
BOLD_CANDIDATES = [
    FONT_DIR / "NanumGothic-Bold.ttf",
    Path("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    Path("C:/Windows/Fonts/malgunbd.ttf"),
    Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
]
REG_CANDIDATES = [
    FONT_DIR / "NotoSansKR-Regular.otf",
    Path("/usr/share/fonts/pickle-hwp/NotoSansCJKkr-Regular.otf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    Path("C:/Windows/Fonts/malgun.ttf"),
    Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
]


def _first_existing(paths):
    for p in paths:
        try:
            if Path(p).exists():
                return Path(p)
        except OSError:
            continue
    return None


FONT_BOLD_PATH = _first_existing(BOLD_CANDIDATES)
FONT_REG_PATH = _first_existing(REG_CANDIDATES) or FONT_BOLD_PATH
_font_cache: dict[tuple[int, bool], ImageFont.FreeTypeFont] = {}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold)
    if key not in _font_cache:
        path = FONT_BOLD_PATH if bold else FONT_REG_PATH
        _font_cache[key] = ImageFont.truetype(str(path), size * S)
    return _font_cache[key]


# ── 값 계산 (app.js 와 같은 규칙) ────────────────────────────────────────
def parse_day(v):
    """'2026-11-24' → date."""
    s = str(v or "")
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            return dt.date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
        except ValueError:
            return None
    return None


def mdd(v):
    """'2026-11-24' · '11/24(화)' → '11/24'."""
    d = parse_day(v)
    if d:
        return f"{d.month}/{d.day}"
    s = str(v or "").strip()
    return s.split("(")[0].strip()


def short_day(v):
    """'2026-11-24' → '11/24(화)'."""
    d = parse_day(v)
    if not d:
        return mdd(v)
    return f"{d.month}/{d.day}({WEEKDAY_KO[d.weekday()]})"


def day_range(item):
    s = short_day(item.get("start"))
    e = short_day(item.get("end"))
    if not item.get("end") or item.get("end") == item.get("start"):
        return s
    return f"{s}~{e}"


def offer_price(text):
    """'확정 7,000원' · '희망 15,000~17,800원' → {value, estimated} (범위면 상단)."""
    import re

    s = re.sub(r"\s+", "", str(text or ""))
    if not s:
        return None
    vals = [int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", s)]
    vals = [v for v in vals if v > 0]
    if not vals:
        return None
    return {"value": max(vals), "estimated": ("확정" not in s) or ("희망" in s)}


def is_spac(item):
    """종목명에 '스팩'·'기업인수목적' — app.js isSpac 과 같은 규칙(리츠는 증거금률이 달라 기본 50%)."""
    name = str((item or {}).get("name") or "")
    return ("스팩" in name) or ("기업인수목적" in name)


def deposit_of(item):
    """종목 하나의 최소청약 증거금 — 공모가 × 주수 × 증거금률(일반 50%·스팩 100%)."""
    p = offer_price((item or {}).get("price"))
    if not p:
        return None
    try:
        raw = int((item or {}).get("minShares") or 0)
    except (TypeError, ValueError):
        raw = 0
    shares = raw if raw > 0 else DEFAULT_MIN_SHARES
    rate = DEPOSIT_RATE_SPAC if is_spac(item) else DEPOSIT_RATE
    return {"amount": int(round(p["value"] * shares * rate)),
            "shares": shares, "shares_estimated": raw <= 0,
            "price_estimated": p["estimated"],
            "estimated": p["estimated"] or raw <= 0}


def lock_until(item):
    """자금이 묶이는 끝(환불일). 없으면 마감일 다음 날."""
    r = parse_day((item or {}).get("refund"))
    if r:
        return r
    e = parse_day((item or {}).get("end")) or parse_day((item or {}).get("start"))
    return e + dt.timedelta(days=1) if e else None


def won_short(v):
    """89000 → 9.9만원 (JS wonShort 와 같은 표기 — 0.05 단위는 반올림)."""
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


def names_short(names, limit=3):
    head = " · ".join(names[:limit])
    return f"{head} 외 {len(names) - limit}" if len(names) > limit else head


def peak_of(rows, first_day=None, last_day=None):
    """날짜별 동시 묶임의 최댓값 — rows = [(item, dep, until, [start])]."""
    days = {}
    for item, dep, until in rows:
        start = parse_day(item.get("start"))
        if not start:
            continue
        d = start
        while d < until:
            if (first_day is None or d >= first_day) and (last_day is None or d < last_day):
                cell = days.setdefault(d, {"amount": 0, "names": []})
                cell["amount"] += dep["amount"]
                if item.get("name") not in cell["names"]:
                    cell["names"].append(item.get("name"))
            d += dt.timedelta(days=1)
    best = None
    for d in sorted(days):
        if best is None or days[d]["amount"] > best[1]["amount"]:
            best = (d, days[d])
    return best


def month_peak(ipo, today):
    """평일 — 이번 달 · 스팩 제외 피크(전체 일정 탭 카드와 같은 조건)."""
    subs = ((ipo or {}).get("upcoming") or {}).get("subscribe") or []
    live = [it for it in subs if (lock_until(it) or dt.date.min) > today]
    month = [it for it in live
             if (parse_day(it.get("start")) or dt.date.min).month == today.month
             and (parse_day(it.get("start")) or dt.date.min).year == today.year]
    picked = month if month else live
    scoped = [it for it in picked if not is_spac(it)]
    rows = []
    for it in scoped:
        dep, until = deposit_of(it), lock_until(it)
        if dep and until:
            rows.append((it, dep, until))
    peak = peak_of(rows, first_day=today)
    return {"scope": f"이번 달 ({today.month}월)" if month else "전체 예정",
            "peak": peak, "count": len(rows), "rows": rows}


def week_peak(ipo, today):
    """주말 — 다음 주(월~일) 미리보기 피크(주말 히어로와 같은 조건, 스팩 포함)."""
    mon = today + dt.timedelta(days=2 if today.weekday() == 5 else 1)
    end = mon + dt.timedelta(days=7)
    items = []
    for it in ((ipo or {}).get("upcoming") or {}).get("subscribe") or []:
        s = parse_day(it.get("start"))
        if s and mon <= s < end:
            items.append(it)
    items.sort(key=lambda it: str(it.get("start") or ""))
    rows = []
    for it in items:
        dep, until = deposit_of(it), lock_until(it)
        if dep and until and parse_day(it.get("start")):
            rows.append((it, dep, until))
    peak = peak_of(rows, first_day=mon, last_day=end)
    label = f"{short_day(mon)}~{short_day(mon + dt.timedelta(days=4))}"
    return {"items": items, "rows": rows, "peak": peak, "label": label,
            "names": [it.get("name") for it in items]}


def unique_brokers(items):
    out = []
    for it in items:
        for b in str(it.get("brokers") or "").replace(",", "·").split("·"):
            b = b.strip()
            if b and b not in out:
                out.append(b)
    return out


# ── 배너에 들어갈 글 ────────────────────────────────────────────────────
def build_content(data, today):
    """상황별 kicker · headline · line1 · line2 · 카드(피크)."""
    ipo = data.get("ipo") or {}
    subs = [s for s in (ipo.get("subscribe") or []) if s.get("name")]
    listing = ipo.get("listing") or {}
    has_listing = bool(listing.get("hasListing") and listing.get("name"))
    nxt = ipo.get("next") or {}
    weekend = today.weekday() >= 5

    # 기준일 — data.json 이 실제로 갱신된 날(주말이면 직전 영업일)
    basis = parse_day(ipo.get("date")) or parse_day(data.get("date"))
    meta = "기준 " + (short_day(basis) if basis else "—")
    if basis and ipo.get("updatedLabel"):
        meta += " " + str(ipo.get("updatedLabel"))
    if weekend and basis:
        meta += " 수집"

    card = None
    if weekend:
        wk = week_peak(ipo, today)
        n = len(wk["items"])
        if n:
            head = f"다음 주 청약 {n}건"
            line1 = names_short(wk["names"])
            br = unique_brokers(wk["items"])
            days = [parse_day(it.get("start")) for it in wk["items"]]
            ends = [parse_day(it.get("end")) or parse_day(it.get("start")) for it in wk["items"]]
            days = [d for d in days if d]
            ends = [d for d in ends if d]
            span = (f"{short_day(min(days))}~{short_day(max(ends))}" if days and ends else wk["label"])
            line2 = span + (" · " + " · ".join(br[:3]) + (f" 외 {len(br) - 3}" if len(br) > 3 else "") if br else "")
            card = _peak_card(wk["peak"], "다음 주 균등 증거금 피크", rows=wk["rows"])
        else:
            head = "다음 주 청약 0건"
            line1 = "월요일 07:30 갱신 뒤 다시 확인하세요"
            line2 = "전체 일정은 ipo.mydon.kr 에서"
        return {"kicker": "주말 휴장 · 다음 주 미리보기", "headline": head,
                "line1": line1, "line2": line2, "meta": meta, "card": card}

    if subs:
        names = [s.get("name") for s in subs]
        head = names[0] + (f" 외 {len(names) - 1}건" if len(names) > 1 else "")
        ranges = []
        for s in subs:
            r = day_range(s)
            if r and r not in ranges:
                ranges.append(r)
        br = unique_brokers(subs)
        bits = list(ranges[:2])
        if br:
            bits.append(" · ".join(br[:2]) + (f" 외 {len(br) - 2}" if len(br) > 2 else ""))
        line1 = " · ".join(bits)
        refunds = [str(s.get("refundDate") or mdd(s.get("refund"))).strip() for s in subs]
        refunds = [r for r in refunds if r]
        line2 = "환불 " + refunds[0] if refunds else ""
        mp = month_peak(ipo, today)
        card = _peak_card(mp["peak"], "균등 최소증거금 피크", scope=mp["scope"], rows=mp["rows"])
        return {"kicker": "오늘 청약", "headline": head,
                "line1": line1, "line2": line2, "meta": meta, "card": card}

    if has_listing:
        head = str(listing.get("name"))
        price_bits = []
        if listing.get("ipoPrice"):
            price_bits.append("공모가 " + str(listing["ipoPrice"]))
        close = listing.get("closePrice") or listing.get("earlyPrice")
        change = listing.get("closeChange") or (listing.get("earlyChange") if not listing.get("closePrice") else "")
        if close:
            price_bits.append(("종가 " if listing.get("closePrice") else "현재 ") + str(close) + (f"({change})" if change else ""))
        elif listing.get("openPrice"):
            price_bits.append("시초 " + str(listing["openPrice"]))
        line1 = " · ".join(price_bits)
        lock = []
        if listing.get("openPrice") and close:
            lock.append("시초 " + str(listing["openPrice"]) + (f"({listing['openChange']})" if listing.get("openChange") else ""))
        if listing.get("lockupRate"):
            lock.append("확약 " + str(listing["lockupRate"]))
        if listing.get("floatSummary"):
            lock.append("유통 " + str(listing["floatSummary"]))
        line2 = " · ".join(lock)
        if not line2 and nxt.get("name"):
            line2 = f"다음 청약 {nxt['name']} {nxt.get('period') or ''}".strip()
        mp = month_peak(ipo, today)
        card = _peak_card(mp["peak"], "균등 최소증거금 피크", scope=mp["scope"], rows=mp["rows"])
        return {"kicker": "오늘 상장", "headline": head,
                "line1": line1, "line2": line2, "meta": meta, "card": card}

    if nxt.get("name"):
        head = "다음 청약 " + str(nxt["name"])
        line1 = " · ".join([x for x in [nxt.get("period"), nxt.get("price")] if x])
        line2 = " · ".join([x for x in [nxt.get("brokers"), ("환불 " + str(nxt["refund"])) if nxt.get("refund") else ""] if x])
        mp = month_peak(ipo, today)
        card = _peak_card(mp["peak"], "균등 최소증거금 피크", scope=mp["scope"], rows=mp["rows"])
        return {"kicker": "오늘 청약·상장 없음", "headline": head,
                "line1": line1, "line2": line2, "meta": meta, "card": card}

    return {"kicker": "오늘 청약·상장 없음", "headline": "다음 일정 준비 중",
            "line1": "전체 일정은 ipo.mydon.kr 에서", "line2": "",
            "meta": meta, "card": None}


def _peak_card(peak, label, scope="", rows=None):
    if not peak:
        return None
    day, cell = peak
    when = f"{short_day(day)} · {len(cell['names'])}종목 겹침" if len(cell["names"]) > 1 else f"{short_day(day)} · {cell['names'][0]}"
    names = cell["names"]
    return {"label": label, "scope": scope, "amount": "약 " + won_short(cell["amount"]),
            "when": when,
            "names": (names_short(names, 3) if len(names) > 1 else ""),
            "basis": deposit_basis_note(rows)}


def deposit_basis_note(rows):
    """카드 아래 기준 줄 — 최소 주수가 모두 확인됐는지에 따라 말이 달라집니다.

    app.js 의 '10주 추정' 표기와 같: 하나라도 미확인이면 추정이 섞였다고 적습니다.
    """
    if not rows:
        return "신고서 최소 주수 · 희망가 상단 기준"
    est = sum(1 for _it, dep, _u in rows if dep.get("shares_estimated"))
    price_est = any(dep.get("price_estimated") for _it, dep, _u in rows)
    head = "10주 추정 포함" if est else "신고서 최소 주수"
    return head + (" · 희망가 상단 기준" if price_est else " · 확정가 기준")


# ── 그리기 ──────────────────────────────────────────────────────────────
def _fit(draw, text, max_w, size, bold, min_size):
    """폭에 맞는 크기로 줄이고, 그래도 넘치면 말줄임."""
    size = int(size)
    while size > min_size:
        f = font(size, bold)
        if draw.textlength(text, font=f) <= max_w * S:
            return size, text
        size -= 1
    f = font(min_size, bold)
    while text and draw.textlength(text + "…", font=f) > max_w * S:
        text = text[:-1]
    return min_size, (text + "…" if text else "")


def render(content, out: Path):
    img = Image.new("RGB", (W * S, H * S), BG)
    d = ImageDraw.Draw(img)

    pad_x = 40
    card = content.get("card")
    card_x0, card_x1 = 496, 764
    card_y0, card_y1 = 72, 200
    left_max = (card_x0 - 24 - pad_x) if card else (W - pad_x * 2)

    # 테두리 — 블로그 흰 배경에서도 카드로 보이게
    d.rounded_rectangle([0, 0, W * S - 1, H * S - 1], radius=16 * S,
                        outline=LINE2, width=max(1, S))

    # 브랜드 마크 + 이름
    mx, my, ms = pad_x, 30, 18
    d.rounded_rectangle([mx * S, my * S, (mx + ms) * S, (my + ms) * S], radius=4.7 * S, fill=BLUE)
    for bx, by, bw, bh in [(4.5, 10.6, 2.5, 5.0), (8.75, 7.8, 2.5, 7.8), (13.0, 4.9, 2.5, 10.7)]:
        k = ms / 20.0
        d.rounded_rectangle([(mx + bx * k) * S, (my + by * k) * S,
                             (mx + (bx + bw) * k) * S, (my + (by + bh) * k) * S],
                            radius=1.1 * k * S, fill="#ffffff")
    d.text((mx * S + (ms + 8) * S, (my + ms / 2) * S), "마이돈 · 공모주",
           font=font(13, True), fill=INK2, anchor="lm")

    # 기준일 (오른쪽 위)
    d.text(((W - pad_x) * S, (my + ms / 2) * S), content.get("meta") or "",
           font=font(11.5, False), fill=INK3, anchor="rm")

    # 구분선
    d.line([pad_x * S, 62 * S, (W - pad_x) * S, 62 * S], fill=LINE, width=max(1, S))

    # kicker
    kicker = content.get("kicker") or ""
    if kicker:
        d.text((pad_x * S, 76 * S), kicker, font=font(13, True), fill=BLUE_INK, anchor="la")

    # headline
    size, text = _fit(d, content.get("headline") or "", left_max, 31, True, 21)
    d.text((pad_x * S, 96 * S), text, font=font(size, True), fill=INK, anchor="la")

    # line1 · line2
    if content.get("line1"):
        size, text = _fit(d, content["line1"], left_max, 16, False, 11)
        d.text((pad_x * S, 138 * S), text, font=font(size, False), fill=INK2, anchor="la")
    if content.get("line2"):
        size, text = _fit(d, content["line2"], left_max, 13, False, 10)
        d.text((pad_x * S, 162 * S), text, font=font(size, False), fill=INK3, anchor="la")

    # 피크 카드
    if card:
        d.rounded_rectangle([card_x0 * S, card_y0 * S, card_x1 * S, card_y1 * S],
                            radius=14 * S, fill=SUNKEN, outline=LINE2, width=max(1, S))
        cx = card_x0 + 16
        inner = (card_x1 - 16) - cx
        d.text((cx * S, 84 * S), card["label"], font=font(11.5, True), fill=BLUE_INK, anchor="la")
        if card.get("scope"):
            d.text(((card_x1 - 16) * S, 84 * S), card["scope"], font=font(10, False), fill=INK3, anchor="ra")
        size, text = _fit(d, card["amount"], inner, 25, True, 17)
        d.text((cx * S, 104 * S), text, font=font(size, True), fill=INK, anchor="la")
        size, text = _fit(d, card["when"], inner, 12, False, 10)
        d.text((cx * S, 142 * S), text, font=font(size, False), fill=INK2, anchor="la")
        size, text = _fit(d, card.get("names") or "", inner, 11, False, 9)
        if text:
            d.text((cx * S, 162 * S), text, font=font(size, False), fill=INK3, anchor="la")
        d.text((cx * S, 182 * S), card.get("basis") or "신고서 최소 주수 기준",
               font=font(9.5, False), fill=INK3, anchor="la")

    # 아래 띠 — 주소 · 갱신 안내
    d.line([0, 220 * S, W * S, 220 * S], fill=LINE, width=max(1, S))
    d.rectangle([0, 220 * S, W * S, H * S], fill=SUNKEN)
    d.line([0, 220 * S, W * S, 220 * S], fill=LINE, width=max(1, S))
    d.text((pad_x * S, 250 * S), "ipo.mydon.kr", font=font(16, True), fill=BLUE, anchor="lm")
    d.text(((W - pad_x) * S, 250 * S), "평일 07:30 · 16:05 자동 갱신",
           font=font(11.5, False), fill=INK3, anchor="rm")

    img = img.resize((W, H), Image.LANCZOS)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    return out


def _self_test():
    """상황별 글·금액이 app.js 규칙대로 나오는지 네 가지로 확인합니다(임시 폴더에 그림)."""
    import tempfile

    sub = {"name": "케이엠에프", "start": "2026-11-24", "end": "2026-11-25",
           "period": "11/24(화)~11/25(수)", "price": "희망 15,000~17,800원",
           "brokers": "IBK투자증권", "refund": "2026-11-27", "refundDate": "11/27"}
    other = {"name": "에이엔에이치스트럭쳐", "start": "2026-11-27", "end": "2026-11-30",
             "price": "희망 11,200~13,600원", "brokers": "NH투자증권", "refund": "2026-12-02"}
    listing = {"hasListing": True, "name": "하나에어로다이내믹스", "date": "2026-11-20",
               "ipoPrice": "5,700원", "openPrice": "10,130원", "openChange": "+77.7%",
               "closePrice": "6,050원", "closeChange": "+6.14%", "lockupRate": "72.69%",
               "floatSummary": "17.30% (약 175억)"}
    nxt = {"name": "케이엠에프", "period": "11/24(화)~11/25(수)",
           "price": "희망 15,000~17,800원", "brokers": "IBK투자증권", "refund": "11/27"}

    def data(subscribe=None, has_listing=False, upcoming=None, updated="07:35", date="2026-11-24"):
        return {"date": date, "updatedLabel": updated,
                "ipo": {"date": date, "updatedLabel": updated,
                        "subscribe": subscribe or [],
                        "listing": listing if has_listing else {"hasListing": False},
                        "next": nxt,
                        "upcoming": {"subscribe": [other] if upcoming is None else upcoming}}}

    cases = [
        ("평일 청약", data([sub], upcoming=[sub, other]), dt.date(2026, 11, 24),
         {"kicker": "오늘 청약", "headline": "케이엠에프", "card": "약 8.9만원",
          "basis": "10주 추정 포함"}),
        ("평일 청약 · 최소 주수 확인",
         data([dict(sub, minShares=50)],
              upcoming=[dict(sub, minShares=50), dict(other, minShares=20)]),
         dt.date(2026, 11, 24),
         {"kicker": "오늘 청약", "headline": "케이엠에프", "card": "약 44.5만원",
          "basis": "신고서 최소 주수"}),
        ("평일 상장", data(has_listing=True, updated="16:15", date="2026-11-20"), dt.date(2026, 11, 20),
         {"kicker": "오늘 상장", "headline": "하나에어로다이내믹스", "line1": "6,050원"}),
        ("평일 일정 없음", data(), dt.date(2026, 11, 23),
         {"kicker": "오늘 청약·상장 없음", "headline": "다음 청약 케이엠에프"}),
        ("주말 미리보기", data(has_listing=True, date="2026-11-20"), dt.date(2026, 11, 22),
         {"kicker": "주말", "headline": "다음 주 청약 1건", "card": "약 6.8만원"}),
    ]

    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        for name, payload, today, expect in cases:
            content = build_content(payload, today)
            out = render(content, Path(tmp) / "b.png")
            size = Image.open(out).size
            got = {"kicker": content.get("kicker", ""), "headline": content.get("headline", ""),
                   "line1": content.get("line1", ""), "line2": content.get("line2", ""),
                   "card": (content.get("card") or {}).get("amount", ""),
                   "basis": (content.get("card") or {}).get("basis", "")}
            misses = []
            for k, want in expect.items():
                if want not in got[k]:
                    misses.append(f"{k}: {got[k]!r} 에 {want!r} 없음")
            if size != (W, H):
                misses.append(f"크기 {size} (기대 {W}x{H})")
            print(("PASS" if not misses else "FAIL") + f"  {name}: {got['kicker']} / {got['headline']}"
                  + (f" / {got['card']}" if got["card"] else ""))
            for m in misses:
                print("      " + m)
                ok = False
    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="블로그용 요약 배너(banner.png) 생성")
    ap.add_argument("--data", default=str(ROOT / "data.json"), help="data.json 경로")
    ap.add_argument("--out", default=str(ROOT / "banner.png"), help="출력 PNG 경로")
    ap.add_argument("--date", default="", help="기준일 고정(YYYY-MM-DD, 확인용)")
    ap.add_argument("--self-test", action="store_true",
                    help="평일 청약·상장·일정 없음·주말 4가지 상황을 가짜 데이터로 그려 확인")
    args = ap.parse_args(argv)

    if not FONT_BOLD_PATH:
        print("한글 폰트를 찾지 못했습니다 — scripts/fonts/NanumGothic-Bold.ttf 를 확인하세요.",
              file=sys.stderr)
        return 1

    if args.self_test:
        return _self_test()

    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    today = parse_day(args.date) if args.date else dt.datetime.now(KST).date()
    content = build_content(data, today)
    out = render(content, Path(args.out))

    print(f"[banner] {out}  {W}x{H}")
    print(f"[banner] {content['kicker']} / {content['headline']}")
    for k in ("line1", "line2", "meta"):
        if content.get(k):
            print(f"[banner] {k}: {content[k]}")
    if content.get("card"):
        c = content["card"]
        print(f"[banner] card: {c['label']} {c['amount']} ({c['when']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
