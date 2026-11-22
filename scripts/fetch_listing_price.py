#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""상장일 시초가·종가 조회기 (네이버 금융 실시간 API, API 키 불필요).

종목코드와 공모가를 받아 네이버 금융 실시간 시세에서 시초가(ov)·현재가(nv)·
고가(hv)·저가(lv)를 읽고, 공모가 대비 등락률을 계산합니다.

  python3 scripts/fetch_listing_price.py 271160 --ipo-price 5700          # JSON 으로만 출력
  python3 scripts/fetch_listing_price.py 271160 --mode open --apply-data  # data.json ipo.listing.openPrice* 갱신
  python3 scripts/fetch_listing_price.py --mode close --apply-data        # 종목코드·공모가를 data.json 에서 읽어 종가 갱신

적용 규칙
  · --mode open  → ipo.listing.openPrice / openChange 를 시초가로 갱신
  · --mode close → ipo.listing.closePrice / closeChange 를 종가(또는 현재가)로 갱신
    - 15:30 전(장중)이면 현재가가 종가는 아니므로 경고를 출력합니다. 마감 뒤(16:05 루틴 등)에만
      close 모드로 적용하는 것을 권합니다.
  · 그 밖의 필드(lockupRate·floatSummary·points 등)는 절대 건드리지 않습니다.
  · --banner 를 붙이면 적용 뒤 scripts/generate_banner.py 로 banner.png 도 다시 만듭니다.
  · --stamp HH:MM 을 붙이면 ipo.updatedAt/updatedLabel(과 최상위 updatedLabel)을 그 시각으로 갱신합니다.

등락률은 공모가 기준(상장일 기준가 = 공모가)으로 직접 계산합니다. 공모가를 주지 않으면
data.json 의 ipo.listing.ipoPrice('5,700원' 표기도 인식)를 쓰고, 그마저 없으면 네이버의
기준가(sv)를 대신 사용합니다(결과에 basis 로 표시).
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
import urllib.request

KST = dt.timezone(dt.timedelta(hours=9))
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REALTIME_URL = "https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{code}"
BANNER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generate_banner.py")


def fetch_realtime(code: str, timeout: int = 20, tries: int = 3) -> dict:
    """SERVICE_ITEM:{code} → datas[0] (ov 시초가 · nv 현재가 · hv 고가 · lv 저가 · sv 기준가)."""
    last: Exception | None = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                REALTIME_URL.format(code=code),
                headers={"User-Agent": UA, "Referer": "https://finance.naver.com",
                         "Accept-Language": "ko-KR,ko;q=0.9"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            text = None
            for enc in ("utf-8", "euc-kr", "cp949"):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if text is None:
                text = raw.decode("utf-8", "replace")
            payload = json.loads(text)
            datas = ((payload.get("result") or {}).get("areas") or [{}])[0].get("datas") or []
            if not datas:
                raise ValueError(f"시세 데이터가 비어 있습니다: {text[:200]}")
            return datas[0]
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt < tries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"네이버 실시간 시세 요청 실패({code}): {last}")


def parse_won(value) -> int | None:
    """'5,700원' · 5700 · '5700' → 5700."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    m = re.search(r"\d[\d,]*", str(value))
    return int(m.group(0).replace(",", "")) if m else None


def won(value: int | None) -> str:
    return f"{value:,}원" if value is not None else ""


def pct(price: int | None, base: int | None) -> str:
    """공모가 대비 등락률 '+77.72%' · '-0.53%' · '0.00%' (기준가 없으면 '')."""
    if not price or not base:
        return ""
    v = round((price / base - 1) * 100, 2)
    text = f"{v:+.2f}%"
    if v == int(v):
        text = f"{int(v):+d}%"
    return text


def snapshot(item: dict, ipo_price: int | None) -> dict:
    base = ipo_price or parse_won(item.get("sv"))
    open_p = parse_won(item.get("ov"))
    cur = parse_won(item.get("nv"))
    high = parse_won(item.get("hv"))
    low = parse_won(item.get("lv"))
    return {
        "code": item.get("cd"),
        "name": (item.get("nm") or "").strip(),
        "ipoPrice": won(ipo_price) if ipo_price else "",
        "basis": "data/지정 공모가" if ipo_price else "네이버 기준가(sv)",
        "open": won(open_p),
        "openChange": pct(open_p, base),
        "current": won(cur),
        "currentChange": pct(cur, base),
        "high": won(high),
        "highChange": pct(high, base),
        "low": won(low),
        "lowChange": pct(low, base),
        "marketStatus": item.get("ms", ""),
        "source": "polling.finance.naver.com SERVICE_ITEM",
    }


def apply_mode(snap: dict, mode: str) -> dict:
    """data.json ipo.listing 에 채울 필드만 뽑습니다."""
    fields: dict = {}
    if mode == "open":
        if snap.get("open"):
            fields["openPrice"] = snap["open"]
            fields["openChange"] = snap["openChange"]
    elif mode == "close":
        if snap.get("current"):
            fields["closePrice"] = snap["current"]
            fields["closeChange"] = snap["currentChange"]
    return fields


def load_data(path: str) -> dict:
    with open(path, encoding="utf-8") as fp:
        return json.load(fp)


def save_data(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as fp:
        fp.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def regenerate_banner() -> bool:
    try:
        proc = subprocess.run([sys.executable, BANNER_SCRIPT], capture_output=True, text=True, timeout=120)
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


def main() -> int:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    now = dt.datetime.now(KST)
    ap = argparse.ArgumentParser(description="상장일 시초가·종가 조회 (네이버 금융 실시간)")
    ap.add_argument("code", nargs="?", default="", help="종목코드 6자리 (없으면 data.json ipo.listing.code 사용)")
    ap.add_argument("--ipo-price", default="", help="공모가('5,700' · '5,700원') — 없으면 data.json 에서 읽음")
    ap.add_argument("--mode", choices=("open", "close"), default="", help="open=시초가, close=종가(현재가)")
    ap.add_argument("--data", default=os.path.join(here, "data.json"))
    ap.add_argument("--apply-data", action="store_true", help="--mode 로 읽은 값을 data.json ipo.listing 에 반영")
    ap.add_argument("--banner", action="store_true", help="--apply-data 성공 뒤 banner.png 재생성")
    ap.add_argument("--stamp", default="", metavar="HH:MM", help="--apply-data 성공 뒤 updatedAt/updatedLabel 갱신")
    args = ap.parse_args()

    data = None
    listing: dict = {}
    if args.apply_data or not args.code or not args.ipo_price:
        try:
            data = load_data(args.data)
        except FileNotFoundError:
            if args.apply_data or not args.code:
                print(f"{args.data} 이(가) 없습니다. 종목코드와 --ipo-price 를 직접 주세요.", file=sys.stderr)
                return 1
        except json.JSONDecodeError as exc:
            print(f"{args.data} JSON 파싱 실패: {exc}", file=sys.stderr)
            return 1
        listing = ((data or {}).get("ipo") or {}).get("listing") or {}

    code = args.code or str(listing.get("code") or "")
    if not re.fullmatch(r"\d{6}", code):
        print("종목코드(6자리)가 필요합니다. 인자로 주거나 data.json ipo.listing.code 에 넣어 주세요.", file=sys.stderr)
        return 1

    ipo_price = parse_won(args.ipo_price) if args.ipo_price else parse_won(listing.get("ipoPrice"))
    if not ipo_price:
        print("공모가를 못 읽었습니다. --ipo-price 를 주면 등락률을 직접 계산합니다.", file=sys.stderr)

    item = fetch_realtime(code)
    snap = snapshot(item, ipo_price)

    warnings: list[str] = []
    if args.mode == "close" and now.weekday() < 5 and now.time() < dt.time(15, 30):
        warnings.append(f"장중({now:%H:%M} KST)이라 current 는 종가가 아닌 최근 체결가입니다 — close 적용은 15:30 뒤를 권합니다.")
    if snap.get("marketStatus") and "OPEN" in str(snap["marketStatus"]).upper():
        warnings.append(f"시장 상태 ms={snap['marketStatus']} — 장중이라 open/close 값이 확정치가 아닐 수 있습니다.")

    fields = apply_mode(snap, args.mode) if args.mode else {}
    if args.apply_data:
        if data is None:
            print("--apply-data 에 필요한 data.json 을 못 읽었습니다.", file=sys.stderr)
            return 1
        if not listing:
            print("data.json 에 ipo.listing 이 비어 있습니다 — 적용할 곳이 없습니다.", file=sys.stderr)
            return 1
        if listing.get("code") and str(listing["code"]) != code:
            print(f"data.json ipo.listing.code({listing['code']})와 요청 코드({code})가 다릅니다 — 적용을 중단합니다.", file=sys.stderr)
            return 1
        if not fields:
            print(f"--mode {args.mode} 로 읽은 값이 비어 적용하지 않습니다(상장 전이거나 시세 없음).", file=sys.stderr)
            return 1
        before = json.dumps(listing, sort_keys=True, ensure_ascii=False)
        listing.update(fields)
        if args.stamp and re.fullmatch(r"\d{1,2}:\d{2}", args.stamp):
            stamp_iso = f"{now.date().isoformat()}T{int(args.stamp.split(':')[0]):02d}:{args.stamp.split(':')[1]}:00+09:00"
            ipo_block = data.setdefault("ipo", {})
            ipo_block["updatedAt"] = stamp_iso
            ipo_block["updatedLabel"] = args.stamp
            data["updatedLabel"] = args.stamp
        save_data(args.data, data)
        changed = json.dumps(listing, sort_keys=True, ensure_ascii=False) != before
        print(f"적용: {args.data} ipo.listing ← {json.dumps(fields, ensure_ascii=False)}"
              + ("" if changed else " (바뀐 내용 없음)"))
        if args.banner:
            regenerate_banner()

    report = dict(snap)
    if args.mode:
        report["mode"] = args.mode
    if fields:
        report["applied"] = fields
    report["warnings"] = warnings
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
