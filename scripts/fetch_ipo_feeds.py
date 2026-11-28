#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""공모주 채널 영상 + 38커뮤니케이션 청약 일정 수집기 (API 키 불필요).

가져오는 것
  1) YouTube 채널 RSS  — '공모주한잔', '공모주투자의법칙(공주)' 최신 영상 제목·URL·업로드 시각
  2) 38커뮤니케이션 공모주 청약일정 표 — 종목명·청약기간·확정/희망 공모가·경쟁률·주관사
     (+ IPO 신규상장 일정 `?o=nw` — 상장일·확정 공모가·시초가·첫날종가)

저장/출력
  기본은 feeds.json 을 갱신하고, 지난 실행(feeds.json)과 비교해 새 영상·새 일정만 요약 출력합니다.
  data.json(사람이 쓰는 화면 데이터)은 기본 동작에서 건드리지 않습니다.

  --sync-data 를 붙이면 data.json 의 공모주 전체 일정(ipo.upcoming)과 ipo.next,
  ipo.nextListing 을 38커뮤니케이션 최신 표 기준으로 자동 병합 갱신합니다.
  · 이미 채워진 정밀 필드(minShares·lockupRate·marketCap·minSubscription·fee·
    equalShares·expectedProRata·proRata10Shares·fullSubscription·opinion 등)는
    같은 종목명이면 지우지 않고 그대로 보존합니다.
    - minShares(증권신고서 기준 최소 청약 주수)는 표에 없으므로 병합 후에도 남습니다.
      새로 추가된 종목처럼 값이 비어 있으면 'minShares 미확인(10주 추정)' 으로 알려 줍니다.
  · 새로 나온 종목은 38 상세 페이지에서 시장구분·종목코드·환불일을 한 번 더 읽어 채웁니다.
  · 내용이 실제로 바뀌었을 때만 data.json 을 쓰고, scripts/generate_banner.py 로
    banner.png 도 함께 다시 만듭니다(--no-banner 로 생략).

사용법
  python3 scripts/fetch_ipo_feeds.py
  python3 scripts/fetch_ipo_feeds.py --dry-run          # 파일을 쓰지 않고 결과만
  python3 scripts/fetch_ipo_feeds.py --out feeds.json
  python3 scripts/fetch_ipo_feeds.py --sync-data        # + data.json 전체 일정 자동 병합
  python3 scripts/fetch_ipo_feeds.py --sync-data --dry-run
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

KST = dt.timezone(dt.timedelta(hours=9))
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
CHANNELS = [
    {"name": "공모주한잔", "channel_id": "UC8kMkLj4kAqMTeOeVQgxyUg", "url": "https://www.youtube.com/@공모주한잔"},
    {"name": "공모주투자의법칙(공주)", "channel_id": "UCstq1xNCuEIR43dM3CMop3g", "url": "https://www.youtube.com/@공모주투자의법칙"},
]
INSIGHT_CHANNELS = [
    {"name": "주식애소리", "channel_id": "UC6Dbyc-0DV-I-iUoS2KqNoA", "url": "https://www.youtube.com/@stock_babysound"},
    {"name": "경제적자유민족", "channel_id": "UCGQEzAvR0kOH5pj7aLI2f3w", "url": "https://www.youtube.com/@gyungja"},
    {"name": "소유보다 경험 - 아이언 / 공모주", "channel_id": "UCPHt56f4p6wVsPIDttxXZ2g", "url": "https://www.youtube.com/@iron_invest"},
]
SCHEDULE_URL = "http://www.38.co.kr/html/fund/index.htm?o=k"
NEW_LISTING_URL = "http://www.38.co.kr/html/fund/index.htm?o=nw"
DETAIL_URL = "http://www.38.co.kr/html/fund/?o=v&no={no}"
SCHEDULE_SOURCE = "38커뮤니케이션 공모주 청약일정"
WEEKDAY_KO = "일월화수목금토"          # date.weekday() 0=월

# ipo.next 에서 38표에서 나오지 않는 수동/AI 보강 필드 — 같은 종목명이면 보존
MANUAL_NEXT_KEYS = [
    "lockupRate", "marketCap", "minSubscription", "fee", "equalShares",
    "expectedProRata", "proRata10Shares", "fullSubscription", "listingDate", "opinion",
    "minShares",
]
NEXT_ORDER = [
    "name", "period", "price", "brokers", "memo", "closeDate", "closeDateLabel",
    "closeNote", "ipoPrice", "minShares", *MANUAL_NEXT_KEYS[:8], "refundDate", "listingDate", "opinion",
]
NEXTLISTING_ORDER = ["name", "period", "price", "brokers", "memo"]


# ---------------------------------------------------------------- HTTP
def http(url: str, timeout: int = 30, tries: int = 3) -> bytes:
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt < tries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"요청 실패: {url} ({last})")


def decode_kr(raw: bytes) -> str:
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


# ---------------------------------------------------------------- YouTube RSS
def youtube_durations(video_ids):
    durations = {}
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        print("YouTube duration lookup: YOUTUBE_API_KEY missing")
        return durations
    for offset in range(0, len(video_ids), 50):
        ids = video_ids[offset:offset + 50]
        query = urllib.parse.urlencode({"id": ",".join(ids), "part": "contentDetails,snippet",
                                        "fields": "items(id,contentDetails/duration,snippet/liveBroadcastContent)"})
        request = urllib.request.Request("https://www.googleapis.com/youtube/v3/videos?" + query,
                                         headers={"X-Goog-Api-Key": key})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                items = json.load(response).get("items", [])
        except (OSError, ValueError) as exc:
            print("YouTube duration lookup failed:", getattr(exc, "code", type(exc).__name__))
            break
        for item in items:
            if item.get("id") not in ids or item.get("snippet", {}).get("liveBroadcastContent") in ("live", "upcoming"):
                continue
            raw = item.get("contentDetails", {}).get("duration", "")
            match = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", raw)
            if match:
                days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
                total = ((days * 24 + hours) * 60 + minutes) * 60 + seconds
                if total:
                    durations[item["id"]] = total
    print(f"YouTube durations: {len(durations)}/{len(video_ids)}")
    return durations


def youtube_videos(channel: dict, limit: int = 5, with_description: bool = False) -> dict:
    feed = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel['channel_id']}"
    raw = http(feed)
    root = ET.fromstring(raw)
    ns = {
        "a": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    videos = []
    for entry in root.findall("a:entry", ns):
        video_id = (entry.findtext("yt:videoId", default="", namespaces=ns) or "").strip()
        title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
        published = (entry.findtext("a:published", default="", namespaces=ns) or "").strip()
        if not video_id:
            continue
        video = {
            "videoId": video_id,
            "title": title,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "published": published,
        }
        media = entry.find("media:group/media:content", ns)
        if media is not None and media.get("duration"):
            video["lengthSeconds"] = media.get("duration")
        if with_description:
            description = entry.findtext("media:group/media:description", default="", namespaces=ns) or ""
            lines = [" ".join(line.split()) for line in description.splitlines() if line.strip()]
            video["description"] = "\n".join(lines)[:2000]
        videos.append(video)
        if len(videos) >= limit:
            break
    channel_name = (root.findtext("a:title", default="", namespaces=ns) or channel["name"]).strip()
    return {
        "name": channel["name"],
        "channelTitle": channel_name,
        "channelId": channel["channel_id"],
        "channelUrl": channel["url"],
        "latest": videos[0] if videos else None,
        "videos": videos,
    }


# ---------------------------------------------------------------- 38커뮤니케이션
class _Tables(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tables.append([])
        elif tag == "tr" and self.tables:
            self._row = []
            self.tables[-1].append(self._row)
        elif tag in ("td", "th"):
            self._cell = []
        elif tag == "br" and self._cell is not None:
            self._cell.append(" ")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            text = re.sub(r"\s+", " ", "".join(self._cell)).replace("\xa0", " ").strip()
            self._row.append(text)
            self._cell = None
        elif tag == "tr":
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()


def parse_38(html: str) -> dict:
    p = _Tables()
    p.feed(html)
    schedule: list[dict] = []
    listings: list[dict] = []
    for table in p.tables:
        header = [clean(c) for c in (table[0] if table else [])]
        if "종목명" in header and any("공모주" in c and "일정" in c for c in header):
            for row in table[1:]:
                cells = [clean(c) for c in row]
                if len(cells) < 6 or not cells[0]:
                    continue
                schedule.append(
                    {
                        "name": cells[0],
                        "period": cells[1],
                        "price_fixed": cells[2],
                        "price_band": cells[3],
                        "competition": cells[4],
                        "brokers": cells[5],
                    }
                )
        for idx, row in enumerate(table):
            if row and "신규상장" in row[0]:
                for follow in table[idx + 1 :]:
                    text = clean(follow[0] if follow else "")
                    m = re.match(r"^(\d{2}/\d{2})\s+(.+)$", text)
                    if m:
                        listings.append({"date": m.group(1), "name": m.group(2).strip()})

    def sort_key(item: dict) -> str:
        m = re.search(r"\d{4}\.\d{2}\.\d{2}", item.get("period", ""))
        return m.group(0) if m else "9999.99.99"

    schedule.sort(key=sort_key)
    return {"schedule": schedule, "listings": listings}


def schedule_end(item: dict) -> str:
    """'2026.11.18~11.19' → '2026-11-19' (연도가 없으면 청약 시작 연도를 씁니다)."""
    period = item.get("period", "")
    years = re.findall(r"\d{4}", period)
    m = re.match(r"(\d{4})\.(\d{2})\.(\d{2})\s*~\s*(?:(\d{4})\.)?(\d{2})\.(\d{2})", period)
    if not m:
        return ""
    year = m.group(4) or m.group(1)
    return f"{year}-{m.group(5)}-{m.group(6)}"


def schedule_start(item: dict) -> str:
    """'2026.11.18~11.19' → '2026-11-18'."""
    m = re.match(r"(\d{4})\.(\d{2})\.(\d{2})", item.get("period", ""))
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""


def iso(date: dt.date) -> str:
    return date.isoformat()


def parse_iso(value: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def short_day(date: dt.date) -> str:
    """2026-11-24 → '11/24(화)' — app.js shortDay 와 같은 표기."""
    return f"{date.month}/{date.day}(" + WEEKDAY_KO[(date.weekday() + 1) % 7] + ")"


def short_label(value: str) -> str:
    """'2026-11-24' → '11/24(화)' (못 읽으면 원문 반환)."""
    d = parse_iso(value)
    return short_day(d) if d else (value or "")


def add_business_days(date: dt.date, days: int) -> dt.date:
    """영업일(월~금)만 세어 며칠 뒤 — 공휴일은 못 세므로 상세 페이지 환불일을 우선합니다."""
    added = 0
    while added < days:
        date += dt.timedelta(days=1)
        if date.weekday() < 5:
            added += 1
    return date


def brokers_label(raw: str) -> str:
    """'한국투자증권,유안타증권' → '한국투자증권 · 유안타증권'."""
    parts = [p.strip() for p in re.split(r"[,·]", raw or "") if p.strip()]
    return " · ".join(parts)


def price_label(fixed: str, band: str) -> str:
    """표의 확정/희망 공모가 → 화면 표기('확정 7,000원' · '희망 15,000~17,800원')."""
    fixed = (fixed or "").strip()
    band = (band or "").strip()
    if fixed not in ("", "-"):
        return f"확정 {fixed}원"
    if band and band != "-":
        low, _, high = band.partition("~")
        if high and low.replace(",", "") == high.replace(",", ""):
            return f"희망 {low.strip()}원"
        return f"희망 {band}원"
    return ""


def parse_new_listings(html: str) -> list[dict]:
    """IPO 신규상장 일정 표(?o=nw) → [{name, date, ipoPrice, open, openChange, close}].

    열: 기업명 · 신규상장일 · 현재가 · 전일비 · 공모가 · 공모가대비등락률 ·
        시초가 · 시초/공모(%) · 첫날종가. 아직 상장 전이면 '-'·'예정'.
    """
    p = _Tables()
    p.feed(html)
    out: list[dict] = []
    for table in p.tables:
        head_idx = None
        for idx, row in enumerate(table[:4]):
            cells = [clean(c) for c in row]
            if "기업명" in cells and "신규상장일" in cells:
                head_idx = idx
                break
        if head_idx is None:
            continue
        for row in table[head_idx + 1 :]:
            cells = [clean(c) for c in row]
            if len(cells) < 5 or not cells[0] or cells[0] == "기업명":
                continue
            m = re.match(r"(\d{4})/(\d{2})/(\d{2})", cells[1])
            if not m:
                continue
            out.append(
                {
                    "name": cells[0],
                    "date": f"{m.group(1)}-{m.group(2)}-{m.group(3)}",
                    "ipoPrice": cells[4].strip() if len(cells) > 4 else "",
                    "open": cells[6].strip() if len(cells) > 6 else "",
                    "openChange": cells[7].strip() if len(cells) > 7 else "",
                    "close": cells[8].strip() if len(cells) > 8 else "",
                }
            )
    return out


def detail_nos(html: str) -> dict[str, str]:
    """페이지의 종목 상세 링크(o=v&no=…) → {종목명: no}."""
    return {
        name.strip(): no
        for no, name in re.findall(r"o=v&(?:amp;)?no=(\d+)[^>]*>\s*(?:<font[^>]*>)?([^<]+)", html)
        if name.strip()
    }


def parse_detail(html: str) -> dict:
    """38 종목 상세 페이지 → {market, code, refund} (못 읽은 키는 빠집니다)."""
    text = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text.replace("\xa0", " "))
    text = re.sub(r"\s+", " ", text)
    out: dict = {}
    m = re.search(r"시장구분\s+([가-힣]+)\s+종목코드\s+(\d{6})", text)
    if m:
        out["market"] = m.group(1)
        out["code"] = m.group(2)
    m = re.search(r"환불일\s+(\d{4})\.(\d{2})\.(\d{2})", text)
    if m:
        out["refund"] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return out


def fetch_detail(no: str) -> dict:
    if not no:
        return {}
    try:
        return parse_detail(decode_kr(http(DETAIL_URL.format(no=no), timeout=20, tries=2)))
    except Exception as exc:  # noqa: BLE001 — 상세 페이지 실패는 전체를 막지 않게
        print(f"  ! 상세 페이지(no={no}) 실패: {exc}", file=sys.stderr)
        return {}


def merge_by_name(old_items: list, new_items: list, base_keys: list,
                  details: dict[str, dict]) -> tuple[list, list]:
    """종목명 기준 병합 — 기존 항목의 키 순서와 base_keys 밖 필드(정밀 보강)를 보존합니다.

    반환: (병합 목록, 새 일정에 없어서 뺀 기존 항목 목록)
    """
    old_by_name: dict[str, dict] = {}
    for it in old_items:
        name = it.get("name")
        if name:
            old_by_name.setdefault(name, it)
    merged: list = []
    for ni in new_items:
        old = old_by_name.pop(ni["name"], None)
        item = dict(old) if old else {"name": ni["name"]}
        extra = details.get(ni["name"], {})
        for key in base_keys:
            value = ni.get(key, "")
            if key == "market":
                value = value or extra.get("market", "") or item.get("market", "")
            if key == "refund":
                # 환불일: 상세 페이지(공휴일 반영) > 기존 값 > 마감+2영업일 추정
                value = extra.get("refund") or item.get("refund") or value
            item[key] = value
        code = extra.get("code") or item.get("code") or ""
        if code:
            item["code"] = code
        if ni.get("spac") or item.get("spac"):
            item["spac"] = True
        merged.append(item)
    return merged, list(old_by_name.values())


def build_subscribe(schedule: list, today: dt.date) -> list[dict]:
    """38 청약일정 표 → 전체 일정 탭의 청약 예정(마감 전 종목만, 시작일 순)."""
    items: list[dict] = []
    for s in schedule:
        end_iso = schedule_end(s)
        if not end_iso or end_iso < iso(today):
            continue
        items.append(
            {
                "name": s["name"],
                "start": schedule_start(s),
                "end": end_iso,
                "price": price_label(s["price_fixed"], s["price_band"]),
                "brokers": brokers_label(s["brokers"]),
                "market": "",
                "refund": iso(add_business_days(parse_iso(end_iso) or today, 2)),
                "spac": bool(re.search(r"스팩|리츠", s["name"])),
            }
        )
    items.sort(key=lambda it: (it.get("start") or "9999", it.get("name")))
    return items


def build_upcoming_listings(new_listings: list, today: dt.date) -> list[dict]:
    """신규상장 표 → 상장 예정(상장일이 오늘 뒤인 종목만, 상장일 순)."""
    items: list[dict] = []
    for row in new_listings:
        if not row.get("date") or row["date"] <= iso(today):
            continue
        price = f"확정 {row['ipoPrice']}원" if row.get("ipoPrice") not in ("", "-", None) else ""
        items.append(
            {
                "name": row["name"],
                "date": row["date"],
                "price": price,
                "brokers": "",
                "market": "",
            }
        )
    items.sort(key=lambda it: (it.get("date") or "9999", it.get("name")))
    return items


def build_next(subs: list, old_next: dict | None, today: dt.date) -> dict | None:
    """다음 청약 히어로 띠(ipo.next) — 아직 시작 안 한 종목 중 가장 이른 것(스팩은 뒤로)."""
    future = sorted(
        [it for it in subs if (it.get("start") or "") > iso(today)],
        key=lambda it: (it.get("start") or "", bool(it.get("spac")), it["name"]))
    pick = future[0] if future else (subs[0] if subs else None)
    if pick is None:
        return None
    start = parse_iso(pick.get("start"))
    end = parse_iso(pick.get("end"))
    others = [it["name"] for it in subs
              if it.get("start") == pick.get("start") and it["name"] != pick["name"]]
    values = {
        "name": pick["name"],
        "period": short_label(pick.get("start")) + ("" if start == end else "~" + short_label(pick.get("end"))),
        "price": pick.get("price", ""),
        "brokers": pick.get("brokers", ""),
        "memo": ("같은 날 " + ", ".join(others) + "도 청약") if others else "",
        "closeDate": pick.get("end", ""),
        "closeDateLabel": pick.get("end", "")[5:].replace("-", "/") if pick.get("end") else "",
        "closeNote": "예정",
        "ipoPrice": pick.get("price", ""),
        "refundDate": pick.get("refund", "")[5:].replace("-", "/") if pick.get("refund") else "",
    }
    manual = old_next or {}
    keep = bool(manual.get("name") == pick["name"])
    new: dict = {}
    for key in NEXT_ORDER:
        if key in values:
            new[key] = values[key]
        else:
            new[key] = manual.get(key, "") if keep else ""
    return new


def build_next_listing(lists: list, old: dict | None) -> dict | None:
    """다음 상장 히어로 띠(ipo.nextListing) — 가장 이른 상장 예정 종목."""
    if not lists:
        return None
    pick = lists[0]
    date = parse_iso(pick.get("date"))
    manual = old or {}
    keep = bool(manual.get("name") == pick["name"])
    new: dict = {}
    for key in NEXTLISTING_ORDER:
        if key == "name":
            new[key] = pick["name"]
        elif key == "period":
            new[key] = short_label(pick.get("date"))
        elif key == "price":
            new[key] = pick.get("price", "")
        elif key == "brokers":
            new[key] = pick.get("brokers", "") or (manual.get("brokers", "") if keep else "")
        elif key == "memo":
            new[key] = (WEEKDAY_KO[(date.weekday() + 1) % 7] + "요일 상장") if date else ""
    return new


def sync_ipo_data(data: dict, schedule: list, new_listings: list, link_nos: dict,
                  today: dt.date) -> tuple[bool, list[str]]:
    """data.json 의 ipo.upcoming · ipo.next · ipo.nextListing 을 38 최신 표로 병합.

    반환: (내용이 실제로 바뀌었는지, 요약 문장 목록)
    """
    notes: list[str] = []
    ipo = data.setdefault("ipo", {})
    up = ipo.setdefault("upcoming", {})

    brokers_map = {s["name"]: brokers_label(s["brokers"]) for s in schedule if s.get("brokers")}

    sub_items = build_subscribe(schedule, today)
    list_items = build_upcoming_listings(new_listings, today)

    # 철회(ipo.cancelled)된 종목은 38 표에 잠시 남아 있어도 다시 넣지 않습니다.
    # (예: 케이엠에프 — 2026-11-23 철회신고서 제출 후에도 38 청약일정 표에는 며칠 더 남음.
    #  다시 추적하려면 ipo.cancelled 에서 그 항목을 지우면 됩니다.)
    cancelled_names = {c.get("name") for c in (ipo.get("cancelled") or []) if c.get("name")}
    if cancelled_names:
        sub_items = [it for it in sub_items if it["name"] not in cancelled_names]

    old_subs = up.get("subscribe") or []
    old_lists = up.get("listing") or []

    # 새 종목(기존에 없던 이름)만 상세 페이지를 한 번 더 읽어 시장구분·종목코드·환불일을 채웁니다.
    known = {it.get("name") for it in old_subs} | {it.get("name") for it in old_lists}
    details: dict[str, dict] = {}
    for item in sub_items + list_items:
        name = item["name"]
        if name in known or name in details:
            continue
        details[name] = fetch_detail(link_nos.get(name, ""))
        time.sleep(0.4)

    subs, dropped_subs = merge_by_name(
        old_subs, sub_items,
        ["name", "start", "end", "price", "brokers", "market", "refund"], details)
    for it in subs:
        if not it.get("brokers"):
            it["brokers"] = brokers_map.get(it["name"], "")
    lists, dropped_lists = merge_by_name(
        old_lists, list_items,
        ["name", "date", "price", "brokers", "market"], details)
    for it in lists:
        if not it.get("brokers"):
            it["brokers"] = brokers_map.get(it["name"], "")

    for it in dropped_subs:
        notes.append(f"청약 예정에서 뺌: {it['name']} (마감·표에서 제외)")
    for it in dropped_lists:
        notes.append(f"상장 예정에서 뺌: {it['name']} (상장일 지남)")
    for it in sub_items:
        if it["name"] not in {x.get("name") for x in old_subs}:
            notes.append(f"청약 예정에 추가: {it['name']} ({it['start']}~{it['end']}, {it['price']})")
    # 최소 청약 주수를 못 채운 종목 — 화면은 10주 추정으로 그리므로, 증권신고서 확인이 필요하다고 알립니다
    for it in subs:
        if not (isinstance(it.get("minShares"), (int, float)) and it.get("minShares") > 0):
            notes.append(f"minShares 미확인(10주 추정): {it['name']} — 증권신고서 최소 청약 주수 확인 필요")
    for it in list_items:
        if it["name"] not in {x.get("name") for x in old_lists}:
            notes.append(f"상장 예정에 추가: {it['name']} ({it['date']}, {it['price']})")

    starts = [parse_iso(it.get("start")) for it in subs]
    ends = [parse_iso(it.get("end")) for it in subs]
    first = min([d for d in starts if d], default=None)
    last = max([d for d in ends if d], default=None)

    before = json.dumps(up, sort_keys=True, ensure_ascii=False)
    up["asOf"] = iso(today)
    up["windowLabel"] = (short_day(first) + " ~ " + short_day(last)) if first and last else ""
    up["subscribe"] = subs
    up["listing"] = lists
    if not up.get("source"):
        up["source"] = {"label": SCHEDULE_SOURCE, "url": SCHEDULE_URL}
    if not up.get("sourceNote"):
        up["sourceNote"] = "청약 일정은 38커뮤니케이션 공모주 청약일정, 상장 일정은 38커뮤니케이션 신규상장 일정 기준이에요."
    changed = before != json.dumps(up, sort_keys=True, ensure_ascii=False)

    old_next = ipo.get("next") or {}
    new_next = build_next(subs, old_next, today)
    if new_next is not None:
        if new_next.get("name") != old_next.get("name"):
            notes.append(f"다음 청약 변경: {old_next.get('name', '(없음)')} → {new_next['name']}")
        changed = (json.dumps(old_next, sort_keys=True, ensure_ascii=False)
                   != json.dumps(new_next, sort_keys=True, ensure_ascii=False)) or changed
        ipo["next"] = new_next

    old_nl = ipo.get("nextListing") or {}
    new_nl = build_next_listing(lists, old_nl)
    if new_nl is not None:
        if new_nl.get("name") != old_nl.get("name"):
            notes.append(f"다음 상장 변경: {old_nl.get('name', '(없음)')} → {new_nl['name']}")
        changed = (json.dumps(old_nl, sort_keys=True, ensure_ascii=False)
                   != json.dumps(new_nl, sort_keys=True, ensure_ascii=False)) or changed
        ipo["nextListing"] = new_nl

    return changed, notes


def touch_sitemap_lastmod(here: str, day: str) -> bool:
    """sitemap.xml 의 <lastmod> 를 수집일(day, YYYY-MM-DD)로 맞춥니다.

    화면 내용이 바뀔 때만 부르므로 lastmod 가 실제 갱신일과 어긋나지 않습니다.
    (파일이 없거나 바꿀 것이 없으면 False)
    """
    path = os.path.join(here, "sitemap.xml")
    try:
        with open(path, encoding="utf-8") as fp:
            body = fp.read()
    except FileNotFoundError:
        return False
    new = re.sub(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>", f"<lastmod>{day}</lastmod>", body, count=1)
    if new == body:
        if "<lastmod>" not in body:
            new = body.replace("</loc>", f"</loc>\n    <lastmod>{day}</lastmod>", 1)
        if new == body:
            return False
    with open(path, "w", encoding="utf-8") as fp:
        fp.write(new)
    return True


def regenerate_banner(here: str) -> bool:
    """generate_banner.py 로 banner.png 를 다시 만듭니다 (성공하면 True)."""
    script = os.path.join(here, "scripts", "generate_banner.py")
    try:
        proc = subprocess.run(
            [sys.executable, script], capture_output=True, text=True, timeout=120)
        out = (proc.stdout or "").strip()
        if out:
            print(out)
        if proc.returncode != 0:
            print(f"banner.png 재생성 실패(exit {proc.returncode}): {(proc.stderr or '').strip()}", file=sys.stderr)
            return False
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"banner.png 재생성 실패: {exc}", file=sys.stderr)
        return False


# ---------------------------------------------------------------- main
def main() -> int:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(here, "feeds.json"))
    ap.add_argument("--data", default=os.path.join(here, "data.json"), help="--sync-data 대상 data.json 경로")
    ap.add_argument("--sync-data", action="store_true",
                    help="data.json 의 ipo.upcoming·ipo.next·ipo.nextListing 도 38 최신 표로 병합 갱신")
    ap.add_argument("--no-banner", action="store_true", help="--sync-data 로 data.json 을 고친 뒤에도 banner.png 를 다시 만들지 않음")
    ap.add_argument("--insights", action="store_true", help="수집한 YouTube 영상으로 insights.json 갱신")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    now = dt.datetime.now(KST)
    problems: list[str] = []

    channels = []
    insight_channels = []
    feed_channel_ids = {channel["channel_id"] for channel in CHANNELS}
    sources = CHANNELS + INSIGHT_CHANNELS if args.insights else CHANNELS
    insight_ids = {channel["channel_id"] for channel in INSIGHT_CHANNELS}
    for channel in sources:
        try:
            data = youtube_videos(
                channel,
                limit=15 if args.insights else 5,
                with_description=args.insights and channel["channel_id"] in insight_ids,
            )
            if args.insights:
                insight_channels.append(data)
            if data["channelId"] in feed_channel_ids:
                channels.append({**data, "videos": data["videos"][:5]})
            latest = data.get("latest") or {}
            print(f"  · {channel['name']}: 최신 '{latest.get('title', '(없음)')[:60]}' ({latest.get('published', '')})")
        except Exception as exc:  # noqa: BLE001 - 한 채널 실패가 전체를 막지 않게
            problems.append(f"{channel['name']} RSS 실패: {exc}")
            print(f"  ! {channel['name']} RSS 실패: {exc}", file=sys.stderr)

    try:
        parsed = parse_38(decode_kr(http(SCHEDULE_URL)))
        schedule_ok = True
        full_schedule = parsed["schedule"]      # 마감 종목까지 포함(주관사 매칭용)
        print(f"  · 38커뮤니케이션: 청약일정 {len(parsed['schedule'])}건, 신규상장 {len(parsed['listings'])}건")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"38커뮤니케이션 실패: {exc}")
        parsed = {"schedule": [], "listings": []}
        schedule_ok = False
        print(f"  ! 38커뮤니케이션 실패: {exc}", file=sys.stderr)

    link_nos: dict[str, str] = {}
    nw_listings: list[dict] = []
    if schedule_ok and args.sync_data:
        try:
            nw_html = decode_kr(http(NEW_LISTING_URL))
            nw_listings = parse_new_listings(nw_html)
            link_nos = detail_nos(nw_html)
            print(f"  · 신규상장 표(?o=nw): {len(nw_listings)}건")
        except Exception as exc:  # noqa: BLE001 — 표를 못 읽으면 상장 예정은 기존 값 유지
            problems.append(f"38 신규상장 표 실패: {exc}")
            print(f"  ! 신규상장 표(?o=nw) 실패: {exc}", file=sys.stderr)

    if insight_channels and not args.dry_run:
        try:
            from update_insights import update_insights

            update_insights(insight_channels, now, os.path.join(here, "insights.json"), youtube_durations)
        except Exception as exc:  # 인사이트 오류가 기존 피드 갱신을 막지 않게 한다.
            print(f"인사이트 갱신 실패: {type(exc).__name__}", file=sys.stderr)

    if not channels and not parsed["schedule"]:
        print("수집된 내용이 없습니다. feeds.json 을 쓰지 않습니다.", file=sys.stderr)
        return 1

    days_ago = now.date() - dt.timedelta(days=1)
    upcoming = [s for s in parsed["schedule"] if (schedule_end(s) or "9999-12-31") >= days_ago.isoformat()]
    parsed["schedule"] = upcoming

    feeds = {
        "updated_at": now.isoformat(timespec="seconds"),
        "channels": channels,
        "schedule": {"source": SCHEDULE_SOURCE, "url": SCHEDULE_URL, "items": parsed["schedule"]},
        "listings": parsed["listings"],
    }

    previous: dict = {}
    if os.path.exists(args.out):
        try:
            with open(args.out, encoding="utf-8") as fp:
                previous = json.load(fp)
        except json.JSONDecodeError:
            previous = {}

    old_videos = {
        v["videoId"]
        for ch in previous.get("channels", [])
        for v in (ch.get("videos") or [])
        if v.get("videoId")
    }
    old_names = {s.get("name") for s in (previous.get("schedule") or {}).get("items", [])}
    first_run = not previous

    new_videos = [
        (ch["name"], v) for ch in channels for v in ch["videos"] if v["videoId"] not in old_videos
    ]
    new_schedule = [s for s in parsed["schedule"] if s.get("name") not in old_names]
    new_listings = [l for l in parsed["listings"] if l.get("name") not in {o.get("name") for o in previous.get("listings", [])}]

    print("\n== 새 소식 ==" + (" (첫 수집 — 앞으로의 일정만 표시)" if first_run else ""))
    if new_videos:
        for channel_name, video in (new_videos if not first_run else new_videos[:2]):
            print(f"  [영상] {channel_name} — {video['title']} ({video['published'][:10]})\n         {video['url']}")
        if first_run and len(new_videos) > 2:
            print(f"  … 그 밖 {len(new_videos) - 2}개 영상은 feeds.json 에 저장")
    else:
        print("  새 영상: 없음 (이미 수집한 영상뿐)")
    if new_schedule:
        for item in new_schedule[:10]:
            price = item["price_fixed"] if item["price_fixed"] not in ("", "-") else item["price_band"]
            print(f"  [일정] {item['name']} | 청약 {item['period']} | {price} | {item['brokers']}")
        if len(new_schedule) > 10:
            print(f"  … 그 밖 {len(new_schedule) - 10}건은 feeds.json 에 저장")
    else:
        print("  새 청약일정: 없음")
    if new_listings:
        for item in new_listings[:6]:
            print(f"  [상장] {item['date']} {item['name']}")

    if problems:
        print(f"\n경고 {len(problems)}건: " + " / ".join(problems), file=sys.stderr)

    # ------------------------------------------------ data.json 병합 (--sync-data)
    if args.sync_data:
        if not schedule_ok or not parsed["schedule"]:
            print("\n38 청약일정을 못 읽어 data.json 병합을 건너뜁니다 (기존 값 유지).", file=sys.stderr)
        else:
            try:
                with open(args.data, encoding="utf-8") as fp:
                    data = json.load(fp)
            except FileNotFoundError:
                print(f"\n{args.data} 이(가) 없어 data.json 병합을 건너뜁니다.", file=sys.stderr)
                data = None
            except json.JSONDecodeError as exc:
                print(f"\n{args.data} JSON 파싱 실패({exc}) — 병합을 건너뜁니다.", file=sys.stderr)
                data = None
            if data is not None:
                changed, notes = sync_ipo_data(data, full_schedule, nw_listings, link_nos, now.date())
                if notes:
                    print("\n== data.json 병합 ==")
                    for note in notes:
                        print(f"  {note}")
                if not changed:
                    print("\ndata.json 바뀐 내용 없음 — 쓰지 않습니다.")
                elif args.dry_run:
                    print("\n--dry-run: data.json 을 쓰지 않았습니다 (banner.png 도 그대로).")
                else:
                    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
                    with open(args.data, "w", encoding="utf-8") as fp:
                        fp.write(payload)
                    print(f"\n저장: {args.data} (전체 일정 {len(data['ipo']['upcoming']['subscribe'])}건 · 상장 예정 {len(data['ipo']['upcoming']['listing'])}건)")
                    if touch_sitemap_lastmod(here, now.strftime("%Y-%m-%d")):
                        print("sitemap.xml lastmod 갱신")
                    if args.no_banner:
                        print("banner.png 는 --no-banner 로 그대로 뒀습니다.")
                    else:
                        regenerate_banner(here)

    if args.dry_run:
        print("\n--dry-run: 파일을 쓰지 않았습니다.")
        return 0

    payload = json.dumps(feeds, ensure_ascii=False, indent=1) + "\n"
    if previous:
        prev_body = {k: v for k, v in previous.items() if k != "updated_at"}
        new_body = {k: v for k, v in feeds.items() if k != "updated_at"}
        if json.dumps(prev_body, sort_keys=True, ensure_ascii=False) == json.dumps(
            new_body, sort_keys=True, ensure_ascii=False
        ):
            print("\n바뀐 내용 없음 — feeds.json 을 쓰지 않습니다.")
            return 0
    with open(args.out, "w", encoding="utf-8") as fp:
        fp.write(payload)
    print(f"\n저장: {args.out} (새 영상 {len(new_videos)}건, 새 일정 {len(new_schedule)}건)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
