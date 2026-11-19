# 공모주 데일리 · 증권사 혜택

오늘 청약·상장 공모주 일정과 분석 요약, 지금 챙길 증권사 신규 개설 혜택을 모바일 한 장으로 보여 주는 정적 페이지입니다.
빌드 도구 없이 `index.html` + `app.js` + `data.json` 만으로 동작하고, Vercel 같은 정적 호스팅에 그대로 올릴 수 있습니다.

공개 URL: <https://ipo-events-public.vercel.app>

## 구성

| 파일 | 역할 |
| --- | --- |
| `index.html` | 화면 뼈대 (헤더 · 섹션 1 공모주 · 섹션 2 증권사 혜택 · 고지문) |
| `styles.css` | 모바일 390px 기준 스타일, 시스템 다크 모드 대응 |
| `app.js` | `data.json` 렌더 + 신청 방법 안내(데이터에 코드가 있으면 복사 버튼도 동작) |
| `data.json` | 표시할 모든 데이터 (공모주 + 이벤트 + 고지문) |
| `check_render.py` | 390×844 Playwright 검증 + 스크린샷 생성 (스크린샷은 `.gitignore`, 저장소에 올리지 않음) |
| `scripts/fetch_ipo_feeds.py` | 공모주 유튜브 2채널 RSS + 38커뮤니케이션 청약일정 수집기 (API 키 불필요) |
| `feeds.json` | 수집기가 만드는 최신 영상·청약일정·신규상장 스냅샷 (사람이 쓰는 `data.json` 과 분리) |
| `.github/workflows/update-ipo-feeds.yml` | 매일 07:30 KST 자동 수집·커밋 |

## 미리보기

```bash
python3 -m http.server 8000
# → http://localhost:8000/
```

`fetch('data.json')`을 쓰기 때문에 파일을 직접 열지 말고 로컬 서버로 열어야 합니다.

## 검증

```bash
python3 check_render.py
```

콘솔 에러·가로 스크롤·요소 잘림·개인정보 문구 포함 여부에 더해,
`expiresAt` 만료 숨김(만료/오늘/상시 테스트 항목 주입)과 혜택 카드 렌더 수,
화면에 '초대 코드·추천인' 문구가 남지 않았는지까지 확인하고 `RESULT: PASS`를 출력합니다.
(데이터에 코드를 넣었을 때의 복사 버튼 동작은 테스트 항목을 주입해 함께 검사합니다.)
검증 스크린샷 4장(`preview-mobile*.png`, `preview-toast.png`)도 함께 갱신되지만 저장소에는 커밋하지 않습니다.
개인정보 검사어는 `privacy_terms.txt`(한 줄에 하나)에서 읽으며, 이 파일은 `.gitignore` 로 저장소에 올리지 않습니다.

## 데이터 갱신 방법

- **공모주**: `data.json`의 `ipo` 블록만 교체.
- **이벤트**: `events` 배열에 객체 추가.
  - `expiresAt`: `YYYY-MM-DD`. **상시 이벤트는 `null`**. 기기 기준 오늘 날짜가 이 날짜를 지나면
    카드가 화면에서 자동으로 빠지고, 섹션 머리말에 "N건 숨겼어요"로만 표시됩니다.
  - `period`: 화면에 같이 보여줄 사람이 읽는 기간 문자열(예: `2026.11.02~11.30`).
  - `verifiedAt`: 혜택을 마지막으로 확인한 날짜.
  - `invite.status`
    - `none`: 초대 코드가 필요 없는 이벤트(계좌개설 후 직접 신청) — **신청 방법** 칩과 `invite.howTo` 한 줄만 보입니다.
    - `ready`: `invite.code`(또는 `invite.url`)를 넣으면 복사 버튼이 살아납니다.
    - `missing`: 슬롯만 있고 코드가 없을 때 → **본인 초대 코드 입력 필요** + 비활성 복사 버튼.
  - `invite.howTo`: 어느 앱의 어느 메뉴에서 신청하는지 한 줄 안내.
  - `ev-note`(섹션 머리말)는 `eventsAsOf` 기준일, 미등록 슬롯 수, 숨긴 건수를 자동으로 계산합니다.
- `draft`: `true` 면 날짜 옆에 `draftNote` 배지가 붙습니다. 현재는 `false`.

## 자동 수집 (`scripts/fetch_ipo_feeds.py`)

API 키 없이 도는 수집기입니다. 화면 데이터(`data.json`)는 건드리지 않고 `feeds.json` 만 씁니다.

```bash
python3 scripts/fetch_ipo_feeds.py            # feeds.json 갱신 + 새 영상·새 일정 요약 출력
python3 scripts/fetch_ipo_feeds.py --dry-run  # 파일을 쓰지 않고 확인만
```

- **유튜브**: `공모주한잔`(UC8kMkLj4kAqMTeOeVQgxyUg), `공모주투자의법칙(공주)`(UCstq1xNCuEIR43dM3CMop3g) RSS에서
  최신 5개 영상의 제목·URL·업로드 시각을 가져옵니다.
- **38커뮤니케이션**(`http://www.38.co.kr/html/fund/index.htm?o=k`, EUC-KR): 공모주 청약일정 표
  (종목명·청약기간·확정/희망 공모가·경쟁률·주관사)와 IPO 신규상장 일정을 파싱합니다.
- 지난 `feeds.json` 과 비교해 새로 올라온 영상·일정만 stdout 에 요약하고, 바뀐 내용이 없으면
  파일을 다시 쓰지 않습니다. 청약기간이 끝난 일정은 저장에서 뺍니다.

## 데이터 기준

- `data.json`은 2026-11-19 기준입니다.
- 증권사 혜택은 각 사 공식 이벤트 페이지에서 확인한 내용이며, 혜택·마감일·보상 한도는 예고 없이 바뀔 수 있습니다.
- 공모주 일정·경쟁률은 38커뮤니케이션과 각 유튜브 채널 공개 내용을 기준으로 합니다.

## 고지

이 페이지는 공개된 정보를 개인적으로 정리한 것으로, 투자 권유나 청약 권유가 아닙니다.
투자 판단과 책임은 이용자 본인에게 있습니다.
