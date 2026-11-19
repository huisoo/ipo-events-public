#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""공모주 채널 영상 + 38커뮤니케이션 청약 일정 수집기 (API 키 불필요).

가져오는 것
  1) YouTube 채널 RSS  — '공모주한잔', '공모주투자의법칙(공주)' 최신 영상 제목·URL·업로드 시각
  2) 38커뮤니케이션 공모주 청약일정 표 — 종목명·청약기간·확정/희망 공모가·경쟁률·주관사
     (+ IPO 신규상장 일정)

저장/출력
  기본은 feeds.json 을 갱신하고, 지난 실행(feeds.json)과 비교해 새 영상·새 일정만 요약 출력합니다.
  data.json(사람이 쓰는 화면 데이터)은 건드리지 않습니다.

사용법
  python3 scripts/fetch_ipo_feeds.py
  python3 scripts/fetch_ipo_feeds.py --dry-run          # 파일을 쓰지 않고 결과만
  python3 scripts/fetch_ipo_feeds.py --out feeds.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

KST = dt.timezone(dt.timedelta(hours=9))
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
CHANNELS = [
    {"name": "공모주한잔", "channel_id": "UC8kMkLj4kAqMTeOeVQgxyUg", "url": "https://www.youtube.com/@공모주한잔"},
    {"name": "공모주투자의법칙(공주)", "channel_id": "UCstq1xNCuEIR43dM3CMop3g", "url": "https://www.youtube.com/@공모주투자의법칙"},
]
SCHEDULE_URL = "http://www.38.co.kr/html/fund/index.htm?o=k"
SCHEDULE_SOURCE = "38커뮤니케이션 공모주 청약일정"


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
def youtube_videos(channel: dict, limit: int = 5) -> dict:
    feed = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel['channel_id']}"
    raw = http(feed)
    root = ET.fromstring(raw)
    ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    videos = []
    for entry in root.findall("a:entry", ns):
        video_id = (entry.findtext("yt:videoId", default="", namespaces=ns) or "").strip()
        title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
        published = (entry.findtext("a:published", default="", namespaces=ns) or "").strip()
        if not video_id:
            continue
        videos.append(
            {
                "videoId": video_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "published": published,
            }
        )
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


# ---------------------------------------------------------------- main
def main() -> int:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(here, "feeds.json"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    now = dt.datetime.now(KST)
    problems: list[str] = []

    channels = []
    for channel in CHANNELS:
        try:
            data = youtube_videos(channel)
            channels.append(data)
            latest = data.get("latest") or {}
            print(f"  · {channel['name']}: 최신 '{latest.get('title', '(없음)')[:60]}' ({latest.get('published', '')})")
        except Exception as exc:  # noqa: BLE001 - 한 채널 실패가 전체를 막지 않게
            problems.append(f"{channel['name']} RSS 실패: {exc}")
            print(f"  ! {channel['name']} RSS 실패: {exc}", file=sys.stderr)

    try:
        parsed = parse_38(decode_kr(http(SCHEDULE_URL)))
        print(f"  · 38커뮤니케이션: 청약일정 {len(parsed['schedule'])}건, 신규상장 {len(parsed['listings'])}건")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"38커뮤니케이션 실패: {exc}")
        parsed = {"schedule": [], "listings": []}
        print(f"  ! 38커뮤니케이션 실패: {exc}", file=sys.stderr)

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
