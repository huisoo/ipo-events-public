#!/usr/bin/env python3
"""홈 화면에 추가(PWA) 아이콘 3종 생성기 — icons/ 아래에 PNG 로 저장합니다.

  python3 scripts/generate_icons.py

만드는 파일
  icons/icon-192.png          192×192  (manifest, Android 홈 화면)
  icons/icon-512.png          512×512  (manifest, 설치 스플래시·스토어)
  icons/apple-touch-icon.png  180×180  (iOS 홈 화면 — 투명 없이 꽉 찬 배경)

디자인
  사이트 헤더의 브랜드 마크(파란 둥근 사각형 + 흰 기둥 3개)를 아이콘 크기로 키운
  **꽉 찬 블루(#3182f6) 배경 + 흰 막대 3개**입니다. 글자를 넣지 않아 작은 크기에서도
  깨지지 않고, 파비콘·헤더 마크와 같은 인상이라 앱을 열었을 때 이어집니다.
  (운영체제가 모서리를 자기 모양대로 잘라 쓰므로 아이콘 자체는 각진 사각형으로 둡니다.)

폰트가 필요 없어 Pillow 만 있으면 어디서나 같은 결과가 나옵니다. 4배로 그린 뒤
줄여서(LANCZOS) 막대 가장자리를 부드럽게 만듭니다.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "icons"

BLUE = "#3182f6"
WHITE = "#ffffff"

SS = 4          # 4배 슈퍼샘플링
# 브랜드 마크(20 단위 좌표)의 막대 비율을 그대로 키운 값 — 폭 20 중 막대 3개 + 간격 2개
BAR_W = 0.140   # 아이콘 한 변 대비 막대 폭
GAP = 0.085     # 막대 사이 간격
BASE = 0.755    # 막대 아랫선(한 변 대비)
HEIGHTS = (0.265, 0.395, 0.520)   # 왼쪽부터 낮은 → 높은 (헤더 마크와 같은 오름차순)
RADIUS = 0.044  # 막대 모서리(한 변 대비)

SPECS = (
    ("icon-192.png", 192),
    ("icon-512.png", 512),
    ("apple-touch-icon.png", 180),
)


def draw_icon(size: int) -> Image.Image:
    """꽉 찬 블루 배경 + 흰 막대 3개 (한 변 size px)."""
    w = size * SS
    img = Image.new("RGB", (w, w), BLUE)
    d = ImageDraw.Draw(img)

    bar = BAR_W * w
    gap = GAP * w
    x0 = (w - (len(HEIGHTS) * bar + (len(HEIGHTS) - 1) * gap)) / 2
    base = BASE * w
    radius = RADIUS * w

    for i, h in enumerate(HEIGHTS):
        left = x0 + i * (bar + gap)
        top = base - h * w
        d.rounded_rectangle([left, top, left + bar, base], radius=radius, fill=WHITE)

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, size in SPECS:
        path = OUT_DIR / name
        draw_icon(size).save(path, format="PNG", optimize=True)
        print(f"{path.relative_to(ROOT)}  {size}×{size}  {path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
