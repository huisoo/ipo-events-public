# 공모주 데일리 · 오늘의 공모주 1분 요약

오늘 청약·상장 공모주와 균등·비례 결론, 주관사별 최소 증거금, 유튜브 요약, 다음 청약 D-day를
첫 화면 한 장에 보여 주고, 각종 혜택은 `혜택` 탭에 모아 둔 정적 페이지입니다.
상단 **`오늘 요약` | `전체 일정` | `혜택` 3탭**으로 나뉘며, `전체 일정` 탭은 38커뮤니케이션 기준
향후 4주 청약·상장 예정 종목을 D-day 카드로, `혜택` 탭은 **증권사·금융**과
**간편 이벤트·설문**(블로그·본인인증 없이 웹 폼으로 참여하는 경품·기프티콘)을
필터 칩과 카드로 보여 줍니다. `오늘 요약` 탭 맨 아래에는 `증권사 개설·현금성 혜택 N건 보기 ›`
한 줄 배너만 두어 첫 화면 무게를 해치지 않습니다.
빌드 도구 없이 `index.html` + `app.js` + `data.json` 만으로 동작하고, Vercel 같은 정적 호스팅에 그대로 올릴 수 있습니다.

공개 URL: <https://ipo.mydon.kr>
(Cloudflare Pages 기본 주소 `https://ipo-events-public.pages.dev`도 그대로 동작하는 별칭입니다. 공유·OG·canonical 기준은 `https://ipo.mydon.kr`.)

- 기준 배포는 **Cloudflare Pages**(`huisoo/ipo-events-public` GitHub 연동, `main` 푸시 시 자동 배포)입니다. Cloudflare Web Analytics 스크립트는 Pages가 HTML에 자동 삽입합니다.
- 이전 Vercel 배포(`ipo-events-public.vercel.app`)는 기존 공유 링크가 깨지지 않도록 주소만 유지하고, `vercel.json` 의 호스트 기반 `redirects` 규칙으로 모든 경로를 `https://ipo.mydon.kr/:path*` 로 308 리다이렉트합니다(Cloudflare Pages 는 `vercel.json` 을 읽지 않으므로 `ipo.mydon.kr`·`pages.dev` 에는 영향 없음).
- `_headers`의 `/data.json` 60초 캐시 설정은 Cloudflare Pages에서만 적용됩니다.

## 디자인 기준 (국내 핀테크 톤)

`styles.css` 상단의 토큰만 바꾸면 전체 톤이 따라옵니다.

| 토큰 | 라이트 | 다크 | 쓰임 |
| --- | --- | --- | --- |
| `--bg` | `#f4f6f8` | `#101012` | 페이지 배경(평탄, 그라데이션 없음) |
| `--card` | `#ffffff` | `#17171c` | 카드 |
| `--sunken` / `--bg2` / `--track` | `#f7f8f9` / `#f2f4f6` / `#e9edf1` | `#1b1b21` / `#23232b` / `#1d1d24` | 카드 안쪽 띠·칩·탭 트랙 |
| `--line` / `--line2` | `#e5e8eb` / `#d1d6db` | `#2c2c35` / `#3a3a44` | 1px 실선·보더 |
| `--ink` / `--ink2` / `--ink3` | `#191f28` / `#4e5968` / `#8b95a1` | `#f2f4f6` / `#c3c9d1` / `#8b95a1` | 본문·보조·캡션 |
| `--blue` / `--blue-soft` | `#3182f6` / `#e8f3ff` | `#4b93ff` / `#16243a` | 액센트·주 액션·정보 블록 |
| `--green` / `--red` | `#02a262` / `#f04452` | `#3ecf8e` / `#ff6b75` | 추천·상승(빨강)/마감 임박 |

- 글꼴은 **Pretendard Variable**(jsDelivr CDN) + `font-variant-numeric: tabular-nums`.
- **테마는 기본 라이트 고정**입니다. `@media (prefers-color-scheme: dark)` 는 쓰지 않으므로 기기가 다크여도 화면은 밝게 뜨고, 헤더 오른쪽(`16:15 업데이트` 옆) 해/달 아이콘 버튼을 누를 때만 `html[data-theme="dark"]` 가 붙습니다. 선택은 `localStorage: mydon-theme`(`light`/`dark`, 기본 `light`)에 남고, `index.html` `<head>` 인라인 스크립트가 저장값이 `dark` 일 때 첫 페인트 전에 속성을 붙여 깜박임을 막습니다. `theme-color` 메타도 함께 바뀝니다.
- 그림자는 `0 1px 2px` 수준만, 점선 테두리·파스텔 알약·이모지는 쓰지 않습니다. 아이콘은 인라인 SVG(15~17px).
- 주 액션(청약 정보 공유)은 블루 솔리드, 보조 액션(상장 정보 공유·앱 열기)은 화이트 + 1px 실선. 커피 응원 카드의 `카카오페이로 보내기`만 예외로 카카오페이 브랜드 옐로(`#fee500` 바탕 · `#191919` 글자 · hover `#f5dc00`)이고, 다크 모드에서도 같은 색을 유지합니다.
- 상승/하락은 국내 관례대로 상승 빨강(`--red`)·하락 블루(`--blue`).

## 화면 위계

상단에 **`오늘 요약` | `전체 일정` | `혜택` 3탭**이 있고, 헤더·커피 응원 카드·고지문은 세 탭 공통입니다.

| 레벨 | 자리 | 내용 |
| --- | --- | --- |
| 탭 | `#tabs` (헤더 아래) | 오늘 요약(`?tab=today`, 기본) · 전체 일정(`?tab=schedule`) · 혜택(`?tab=benefits`) — 각 탭 딥링크와 해시(`#schedule`, `#benefits`) 지원. 390px에서 3탭이 한 줄(3열 그리드)로 들어갑니다 |
| 1 | `h1` + `.hero` | 오늘의 공모주 1분 요약 — 오늘 청약/상장 여부 · 균등·비례 결론 · 주관사별 최소증거금 · 유튜브 요약 · 다음 청약 D-day. 상장 카드는 장 시작 전(07:30~09:00)이면 큰 가격 대신 `09:00 상장 예정` + 공모가 기준 가격제한폭을 보여 줍니다. **모바일(375~430px)에서 청약 카드 + 상장 카드가 첫 화면(812~932px)에 함께 들어오도록** 카드 패딩 14px · 종목명 22px · 가격 26px, 청약 기간·환불·주관은 3행 표 대신 `.hspec` 한 줄 요약, `points` 는 핵심 3줄 이내로 유지합니다 |
| 1.5 | `.share` (히어로 바로 아래) | **항상 2버튼 고정(2열)** — 왼쪽 `청약 정보 공유`(블루 솔리드), 오른쪽 `상장 정보 공유`(화이트 실선). 각각 카톡 단톡방에 그대로 붙여넣는 **청약 정보**(종목·공모가·확약률·시총·최소청약·균등물량·경쟁률·환불일·상장일·청약 의견)와 **상장 정보**(공모가·시초가·종가·최종 확약률·상장일 유통물량·가격제한폭·한줄 요약)를 내보냅니다. 그날 없는 쪽은 이유를 적은 비활성 버튼(`오늘 청약 없음` / `오늘 상장 없음`)으로 남고, 공유 시트가 없거나 실패하면 같은 버튼이 복사로 폴백합니다. 아래에 철회 종목·출처(`#ipo-foot`)가 이어집니다 |
| 2 | `.ben-link` (한 줄 배너) | `증권사 개설·현금성 혜택 N건 보기 ›` — 누르면 `혜택` 탭으로 전환됩니다. 혜택 상세 목록은 `오늘 요약`에 두지 않습니다 |
| 2.5 | `.banner-embed` (오늘 요약 맨 아래) | `블로그 배너 퍼가기` — 기본 **접힘** 보조 버튼. 누르면 `banner.png` 미리보기와 함께 `HTML 코드 복사`(티스토리·워드프레스·웹사이트) · `이미지 URL 복사`(네이버 블로그) · `이미지 저장`(800 × 280 PNG) · 붙여넣을 코드 원문이 펼쳐집니다. 접힌 상태에서는 한 줄(44px)이라 첫 화면 무게를 키우지 않습니다 |
| 설치 | `.install` (`#ben-link` 아래) | `홈 화면에 앱으로 추가` — PWA 설치 한 줄. Android 는 `beforeinstallprompt` 뒤에만 보이고 누르면 브라우저 설치 창, iOS 는 공유 → '홈 화면에 추가' 안내 펼침, `standalone` 이면 숨김, × 는 `localStorage` 저장 |
| 혜택 탭 | `#panel-benefits` | 지금 챙길 혜택 — 필터 칩 `전체` \| `증권사·금융` \| `간편 이벤트·설문`(건수 표시, 즉시 필터링) + 카드(카테고리 태그·D-day, 혜택명, 핵심 금액/조건, 대상·마감·기간, `유의사항·신청 방법` 접힘, `자세히 보기` 공식 링크). 마감이 지난 항목은 자동으로 숨기고 머리말에 건수를 적습니다 |
| 3 | `.support` (푸터 위) | 커피 한 잔 응원하기 — 운영 응원 카드. 카드 자체는 낮은 대비로 두되 제목은 14px/700 `--ink`로 올리고, 버튼 하나(`카카오페이로 보내기`)를 카카오페이 옐로(`#fee500` · 글자 `#191919`, 다크 모드 동일)로 둬서 푸터에 묻히지 않게 합니다 |
| 전체 일정 | `#panel-schedule` | 38커뮤니케이션 `ipo.upcoming` — 맨 위 **균등 최소증거금 카드**(이번 달/전체 · 스팩 제외, 동시에 묶이는 최대 자금·피크 날짜·단순 합계), 이어서 **청약 예정**(D-day·청약 기간·희망 공모가·주관사·환불일·종목별 예상 균등 증거금)과 **상장 예정**(상장일·확정 공모가·주관사) 카드 리스트 + 철회 종목 + 출처 링크 |
| 주말(토·일) | `.hero.is-weekend` (`#panel-today` 첫 카드) | 시장이 쉬는 토·일에는 `오늘 요약` 첫 카드가 **다음 주 청약 미리보기**로 바뀝니다. 배지 `주말 휴장` · `다음 주 청약 미리보기`, 제목 `다음 주 청약 N건`, 날짜 줄 `2026년 11월 22일 일요일 · 주말 휴장`, 갱신 줄 `직전 영업일(11/20) 수집 · 월요일 07:30 갱신`. 카드 안에는 ① 다음 주(월~일) `ipo.upcoming.subscribe` 종목(청약 기간·공모가·균등 증거금·주관·환불·스팩 태그) ② **다음 주 균등 최소증거금 피크**(날짜별 동시 묶임 최댓값 — 그날 겹치는 종목과 함께, 최소 주수는 증권신고서 기준·미확인은 10주 추정, 희망가 상단, 일반 50%·스팩 100% 기준) ③ 다음 주 0건이면 빈 상태 문구. 직전 영업일 상장은 `직전 영업일(11/20) 상장` 라벨의 보조 카드(`#prev-day`, 공유 버튼 아래)로 내려가 `오늘 상장` 오해가 없게 합니다. 판별은 브라우저 타임존과 무관하게 **KST 기준 토·일**이며, 검증·디버그용으로 `?date=YYYY-MM-DD`(예: `?date=2026-11-22`)를 받습니다 |

### 공유문 포맷(`.share`)

히어로 아래 **2버튼 고정**입니다. 왼쪽은 청약 정보, 오른쪽은 상장 정보를 내보내고,
그날 없는 쪽은 이유를 적은 비활성 버튼(`오늘 청약 없음` / `오늘 상장 없음`)으로 남습니다.
버튼은 항상 2개라서 레이아웃이 날마다 흔들리지 않습니다.

#### 청약 정보 (`청약 정보 공유` · `ipo.subscribe[]`, 없으면 `ipo.next`)

공유·복사는 전체 요약이 아니라 **청약 정보만** 내보냅니다. `ipo.subscribe[]`(오늘 청약 종목)를
순서대로, 오늘 청약이 없으면 `ipo.next`(다음 청약)를 같은 포맷으로 만듭니다.

```
📌 {종목명} ({M/DD} 마감[ 예정])

* 공모가: 5,700원
* 확약률: 4.1%
* 시총: 1,010억
* 주관사: IBK투자증권
* 최소청약: 10주 / 28,500원
* 수수료: 1,500원
* 균등물량: 55만 주
* 예상 비례경쟁률: 3,500:1
* 비례 10주: 약 1억 청약
* 풀청약: 2억 1,375만 원
* 환불일: 11/13
* 상장일: 11/20

✅ 청약 의견: 균등 + 비례 풀청약 추천
https://ipo.mydon.kr   ← 클립보드 복사본에만(공유 시 url 필드로 따로 전달)
```

- 종목이 여러 개면 빈 줄 하나로 구분해 이어 붙입니다.
- 항목은 위 **순서와 라벨 그대로** 나가고, 값이 비었거나 `미정`·`확인 필요`로 적힌 항목은
  **줄을 만들지 않습니다**(숫자를 지어내지 않음). 그래서 수요예측 전 종목은 공모가·주관사·환불일
  정도만 나옵니다.
- `청약 의견`(`opinion`)도 없으면 `✅` 줄을 뺍니다.
- 클립보드 복사본은 마지막 줄에 사이트 URL이 붙고, `navigator.share`는 `{ title, text, url }`로
  `text`에 URL을 넣지 않고 `url` 필드로 넘깁니다(미리보기 중복 방지).
- 버튼은 **두 개 고정**(`청약 정보 공유` | `상장 정보 공유`, 2열 그리드·높이 44px 이상)입니다.
  누르면 ① `navigator.share` 가 있으면 공유 시트를 열고(`{ title: '공모주 청약 정보' | '공모주 상장 정보', text, url }`),
  ② 없으면(데스크톱·구형 브라우저) 또는 `AbortError` 이외의 오류면 클립보드에 복사(마지막 줄 URL 포함)한 뒤
  토스트와 버튼 라벨 `복사됐어요`(1.8초 뒤 되돌림)로 알려 줍니다. 사용자가 공유 시트를 그냥 닫은
  경우(`AbortError`)에는 아무 것도 하지 않습니다. 그날 없는 쪽은 눌리지 않는 비활성 버튼
  (커서 default·연한 회색 배경·아이콘 흐리게)으로 남고 라벨이 `오늘 청약 없음` / `오늘 상장 없음`으로 바뀝니다.

#### 상장 정보 (`📈` · `ipo.listing`)

`ipo.listing.hasListing` 이 `true`인 날에만 나갑니다(오늘 상장 종목 1건).

```
📈 {종목명} ({M/DD} 상장)

* 공모가: 5,700원
* 시초가: 10,130원 (+77.7%)
* 종가: 6,050원 (+6.14%)
* 최종 확약률: 72.69%
* 상장일 유통물량: 17.30% (약 175억)
* 가격제한폭: 3,420원 ~ 22,800원 (60~400%)
* 한줄 요약: 장 초반 +98% 급등 후 마감 · 12/5 15일 확약 물량 주의
https://ipo.mydon.kr   ← 클립보드 복사본에만(공유 시 url 필드로 따로 전달)
```

**장 시작 전(07:30~09:00, 시초가 전)** 에는 시초가·종가 줄이 아예 없으므로 그 앞에 상장 시각을 적고,
비어 있는 `priceBand` 는 공모가 기준으로 계산해 넣습니다(공모가×0.6 ~ ×4 = 60~400%).

```
📈 {종목명} ({M/DD} 상장)

* 상장 시각: 09:00 (장 시작 전)
* 공모가: 5,700원
* 최종 확약률: 72.69%
* 상장일 유통물량: 17.30% (약 175억)
* 가격제한폭: 3,420원 ~ 22,800원 (60~400%)   ← 공모가에서 계산
```

- 괄호의 날짜는 `ipo.listing.date`(없으면 `listingDate` → `ipo.date`)를 `M/DD`로 바꿔 씁니다.
- 시초가·종가는 값이 있을 때만 `값 (등락)` 형태로 나가고, 등락 값이 없으면 값만 나갑니다.
- 값이 비었거나 `미정`·`확인 필요`인 항목은 **줄을 만들지 않습니다**(숫자를 지어내지 않음).
  종가가 아직 없으면(장중) `earlyPrice`·`earlyChange`로 대신합니다.
- `openPrice`·`closePrice`·`earlyPrice` 가 모두 비어 있으면 **장 시작 전**으로 보고
  `* 상장 시각: 09:00 (장 시작 전)` 한 줄과, `priceBand` 가 비었을 때만 공모가에서 계산한 가격제한폭을 넣습니다
  (계산값은 `app.js` `bandText` · `check_render.py` `listing_band` 가 같은 규칙).
- 공유 시트 `text`에는 URL을 넣지 않고 `url` 필드로 넘깁니다(미리보기 중복 방지).

### 청약 정보 필드(`ipo.subscribe[]` · `ipo.next`)

두 블록 모두 같은 필드명을 씁니다. 화면 카드가 쓰는 `price`·`refund`는 그대로 두고,
공유문용 값은 아래 필드에 따로 적습니다.

| 필드 | 공유문 라벨 | 예 | 출처·규칙 |
| --- | --- | --- | --- |
| `closeDate` | (괄호의 마감일) | `2026-11-25` | 청약 마지막 날(ISO) |
| `closeDateLabel` | `{M/DD} 마감` | `11/25` | 없으면 `period`의 마지막 `M/D`를 씁니다 |
| `closeNote` | `마감` 뒤 문구 | `예정` | 다음 청약(`ipo.next`)은 비어 있으면 `예정`으로 자동 표기 |
| `ipoPrice` | 공모가 | `5,700원` · `희망 15,000~17,800원` | 확정 전에는 `희망 …`. 없으면 `price`로 대신 |
| `lockupRate` | 확약률 | `4.1%` | 수요예측 결과의 의무보유확약 비율 |
| `marketCap` | 시총 | `1,010억` | 공모가 기준 시가총액 |
| `brokers` | 주관사 | `IBK투자증권` | 대표주관(여러 곳이면 ` · `로 연결) |
| `minSubscription` | 최소청약 | `10주 / 28,500원` | 최소 청약 주수 / 그 증거금 |
| `fee` | 수수료 | `1,500원` | 증권사 청약 수수료 |
| `equalShares` | 균등물량 | `55만 주` | 균등배정 물량 |
| `expectedProRata` | 예상 비례경쟁률 | `3,500:1` | 증권사 예상/직전 경쟁률 |
| `proRata10Shares` | 비례 10주 | `약 1억 청약` | 비례 10주 배정에 필요한 청약 금액 |
| `fullSubscription` | 풀청약 | `2억 1,375만 원` | 청약 한도까지 넣는 금액 |
| `refundDate` | 환불일 | `11/13` | 없으면 `refund`로 대신(ISO도 `M/DD`로 변환) |
| `listingDate` | 상장일 | `11/20` | 상장일이 공시되기 전이면 비웁니다 |
| `opinion` | `✅ 청약 의견` | `균등 + 비례 풀청약 추천` | 공모주한잔·공주 분석을 종합한 한 줄 |

```jsonc
"next": {
  "name": "케이엠에프", "period": "11/24(화)~11/25(수)",
  "price": "희망 15,000~17,800원", "brokers": "IBK투자증권",
  "closeDate": "2026-11-25", "closeDateLabel": "11/25", "closeNote": "예정",
  "ipoPrice": "희망 15,000~17,800원",
  "lockupRate": "", "marketCap": "", "minSubscription": "", "fee": "",
  "equalShares": "", "expectedProRata": "", "proRata10Shares": "",
  "fullSubscription": "",
  "refundDate": "11/27", "listingDate": "", "opinion": ""
}
```

위 예시(케이엠에프)처럼 수요예측 전 종목은 확인된 값만 채우고 나머지는 빈 문자열로 둡니다.
실제 공유문은 `📌 케이엠에프 (11/25 마감 예정)` + `공모가·주관사·환불일` 세 줄만 나갑니다.

### 상장 정보 필드(`ipo.listing`)

화면 카드가 쓰는 `name`·`code`·`market`·`points`는 그대로 두고, 상장 정보 공유문용 값은 아래 필드에 따로 적습니다.

| 필드 | 공유문 라벨 | 예 | 출처·규칙 |
| --- | --- | --- | --- |
| `hasListing` | (버튼 활성 여부) | `true` | `false`면 오른쪽 버튼은 `오늘 상장 없음` 비활성 |
| `brokers` | (앱 열기 버튼) | `IBK투자증권` | 상장 주관사(대표주관). 카드 하단 `📱 {증권사} 앱 열기` 버튼을 만드는 값 — **상장일마다 반드시 채웁니다**. 복수면 ` · `로 연결 |
| `date` | `{M/DD} 상장` | `2026-11-20` | 상장일(ISO). 없으면 `listingDate` → `ipo.date` |
| `ipoPrice` | 공모가 | `5,700원` | 확정 공모가 |
| `openPrice` | 시초가 | `10,130원` | 상장일 시초가 |
| `openChange` | (시초가 괄호) | `+77.7%` | 공모가 대비 등락률 |
| `closePrice` | 종가 | `6,050원` | 상장일 종가(장중이면 `earlyPrice`로 대신) |
| `closeChange` | (종가 괄호) | `+6.14%` | 공모가 대비 등락률(장중이면 `earlyChange`) |
| `lockupRate` | 최종 확약률 | `72.69%` | 수요예측 최종 의무보유확약 비율 |
| `floatSummary` | 상장일 유통물량 | `17.30% (약 175억)` | 첫날 매도가능 물량(비율·금액) |
| `priceBand` | 가격제한폭 | `3,420원 ~ 22,800원 (60~400%)` | 상장일 가격제한폭. 비어 있으면 공모가×0.6~×4로 계산해 표시(장 시작 전) |
| `shareSummary` | 한줄 요약 | `장 초반 +98% 급등 후 마감 · 12/5 15일 확약 물량 주의` | 단톡방에 보탤 한 줄 |

```jsonc
"listing": {
  "hasListing": true, "date": "2026-11-20",
  "name": "하나에어로다이내믹스", "code": "271160", "market": "코스닥 · 벤처기업부",
  "brokers": "IBK투자증권",
  "ipoPrice": "5,700원", "openPrice": "10,130원", "openChange": "+77.7%",
  "closePrice": "6,050원", "closeChange": "+6.14%", "lockupRate": "72.69%",
  "floatSummary": "17.30% (약 175억)",
  "priceBand": "3,420원 ~ 22,800원 (60~400%)",
  "shareSummary": "장 초반 +98% 급등 후 마감 · 12/5 15일 확약 물량 주의",
  "points": ["…"]
}
```

`points`는 화면 카드에 그대로 나가는 핵심 요약입니다. **3줄 이내**(① 오늘 흐름: 시초·최고·종가 ② 물량·확약: 첫날 유통·최종 확약 ③ 주의할 점: 확약 해제 등)로만 쓰고, 매출·영업익이나 장 마감 뒤 의미 없는 목표가·장중 등락률 나열·거래대금은 넣지 않습니다.

상장 당일 07:30에는 시초가 전이라 `openPrice`·`closePrice`·`priceBand`를 비워 두고(그 줄이 빠짐),
09:05·16:05 확인에서 확인된 값만 채웁니다.
그때 화면 카드는 큰 가격 자리에 **`09:00 상장 예정`**(`.hprice.is-pre`)을 두고 그 아래
`가격제한폭 3,420원 ~ 22,800원 (60~400%)`(공모가×0.6~×4)를 작게 적습니다 — 빈 가격 줄이 생기지 않습니다.
`points` 첫 줄은 시각·가격제한폭을 카드와 똑같이 반복하지 말고, 확인된 물량·확약·주의할 점 중심으로 씁니다.

### 📱 주관사 앱 열기 버튼 (OS 자동 구분)

상장 카드(3줄 요약 아래)와 청약 카드(주관·환불 줄 아래)에 **`📱 {증권사} 앱 열기`** 버튼이 붙습니다.
주관사 문자열(`ipo.listing.brokers` · `ipo.subscribe[].brokers`)을 ` · `, `,` 기준으로 나눠
매핑된 증권사마다 칩 하나를 만들고, 복수 주관사면 칩이 나란히(좁은 화면에서는 다음 줄로) 놓입니다.

- **OS 판별**(`app.js`) — 기기별로 여는 방식이 다릅니다.
  - **Android** (`/Android/i.test(navigator.userAgent)`): 앱이 **BROWSABLE 로 공개한 딥링크가 확인된 경우에만** `intent://{host}/#Intent;scheme={스킴};package={Play 패키지};S.browser_fallback_url={Play 스토어 URL(URL 인코딩)};end` 로 앱을 열고(같은 창 — `target` 없음 — 빈 새 탭 방지), 미설치면 `browser_fallback_url` 로 Play 스토어로 갑니다. 확인된 딥링크가 없으면 억지 intent 를 만들지 않고 **Play 스토어 앱 페이지**(`target="_blank" rel="noopener"`)로 바로 보냅니다.
    - 크롬은 웹 링크로 앱을 열 때 `CATEGORY_BROWSABLE` 을 강제하기 때문에, `MAIN/LAUNCHER` 만 선언한 앱은 `intent://` 로 열리지 않고 바로 폴백으로 떨어진다(예전 `action=MAIN;category=LAUNCHER` 방식이 항상 Play 스토어로 가던 이유).
    - 앱이 `data android:host` 를 함께 선언했으면 **host 까지 맞춰야** 한다(예: 나무증권 `txsmart://txrun` — `txsmart://` 만으로는 매칭 안 됨).
  - **iOS** (`iPhone|iPad|iPod` UA 또는 터치 지원 Mac): **App Store** `https://apps.apple.com/kr/app/id{App Store ID}` (`target="_blank" rel="noopener"`).
  - **Desktop(그 외)**: **Google Play** `https://play.google.com/store/apps/details?id={Play 패키지}` (`target="_blank" rel="noopener"`).

BROWSABLE 딥링크가 확인된 앱(2026-11-21 기준 — 근거는 `handoffs/…/evidence.md`):

| 증권사 | 값 | 출처 |
| --- | --- | --- |
| NH투자증권 | `scheme: 'txsmart'`, `host: 'txrun'` | 나무증권 APK 8.53 `AndroidManifest.xml` 의 BROWSABLE 인텐트 필터 |
| 삼성증권 | `site: 'https://www.samsungpop.com/'` (https 앱 링크, `scheme=https` intent) | Digital Asset Links — `com.samsungpop.android.mpop` 위임 공개 |
| DB증권 / DB금융투자 | `site: 'https://m.dbsec.co.kr/'` (https 앱 링크) | Digital Asset Links — `com.dbfi.xts` 위임 공개 |

나머지 증권사는 위 근거를 확인하지 못해 Play 스토어로 보냅니다. 딥링크를 확인하면 `BROKER_APPS` 의 `scheme`/`host`(또는 `site`)만 채우면 되고, **추측값은 넣지 않습니다**.
- 버튼은 `BROKER_APPS`에 들어 있는 증권사만 만듭니다(확인되지 않은 증권사는 버튼 없음 — 추정 링크를 만들지 않음).
- 크기: 높이 38px(최소 36px 이상), 12px 굵은 글씨, `--blue-soft` 배경 · `--blue` 글자, 다크 모드 대응,
  가로 스크롤 없음(390px 기준).

현재 매핑(2026-11-20 스토어 페이지에서 앱 이름·개발자까지 확인):

| 증권사 | Google Play 패키지 | App Store ID | 앱 |
| --- | --- | --- | --- |
| IBK투자증권 | `com.ibks.ione.mts` | `6612018102` | IBK투자증권 (대표MTS) |
| 삼성증권 | `com.samsungpop.android.mpop` | `1150231646` | 삼성증권 mPOP |
| 미래에셋증권 | `com.miraeasset.trade` | `1248716281` | 미래에셋증권 MAPS |
| 한국투자증권 | `com.truefriend.neosmartarenewal` | `1621986905` | 한투-한국투자증권 |
| KB증권 | `com.kbsec.mts.iplustarngm2` | `350742701` | KB M-able |
| NH투자증권 | `com.wooriwm.txsmart` | `486312400` | 나무증권-NH투자증권 MTS |
| 하나증권 | `com.hanasec.pro` | `6755097570` | 하나증권V-대표MTS(NEW) |
| 신한투자증권 | `com.shinhaninvest.nsmts` | `1168512940` | 신한 SOL증권 |
| 키움증권 | `com.kiwoom.heromts` | `1570370057` | 키움증권 영웅문S# |
| 신영증권 | `com.shinyoung.mts` | `1619250855` | 신영증권 그린 |
| 유진투자증권 | `com.eugenefn.smartchampion2` | `1080300592` | 유진투자증권 |
| 대신증권 | `com.daishin` | `414850336` | 대신증권 CYBOS Touch |
| 우리투자증권 | `com.wooriib.wonmts` | `6745938978` | 우리WON MTS(증권) |
| DB증권 | `com.dbfi.xts` | `1603371564` | DB증권 MTS(알파증권) |
| 한화투자증권 | `plus.steps.sapp` | `1200606784` | 한화투자증권 MTS |
| BNK투자증권 | `com.bnkfn.mtsplus` | `1170374515` | BNK투자증권 |

새 증권사를 넣을 때는 두 스토어 페이지(`https://play.google.com/store/apps/details?id=…`,
`https://apps.apple.com/kr/app/id…`)를 실제로 열어 **앱 이름과 개발자가 그 증권사인지** 확인한 뒤 `app.js`의
`BROKER_APPS`에 추가합니다.

### 전체 일정 데이터(`ipo.upcoming`)

```jsonc
"upcoming": {
  "asOf": "2026-11-20",              // 38커뮤니케이션에서 확인한 날짜
  "windowLabel": "11/24(화) ~ 12/17(목)",
  "source": { "label": "38커뮤니케이션 공모주 청약일정", "url": "https://www.38.co.kr/html/fund/index.htm?o=k" },
  "subscribe": [
    { "name": "케이엠에프", "start": "2026-11-24", "end": "2026-11-25",
      "price": "희망 15,000~17,800원", "brokers": "IBK투자증권",
      "market": "코스닥", "refund": "2026-11-27", "spac": false,
      "minShares": 10 }
  ],
  "listing": [
    { "name": "엠비디", "date": "2026-11-24", "price": "확정 7,000원",
      "brokers": "하나증권", "market": "코스닥" }
  ],
  "sourceNote": "..."
}
```

- 청약 카드의 D-day는 `start` 기준으로 계산합니다(`청약 중`·`청약 종료` 자동 표시).
- **`minShares`(최소청약주수)**: **증권신고서(투자설명서)의 일반청약자 최소 청약 수량·청약단위 표에서 확인한 값**을 적습니다
  (2026-11-23 사용자 확정: 신고서상 최소가 있으면 그 값, 없으면 10주 추정). 예: 신영스팩12호 50 · 엔키화이트햇 50 · 우리투자스팩1호 100 · 일반 종목 대부분 10~20.
  값이 없으면 10주로 계산하고 금액 옆에 `10주 추정` 칩 + 툴팁 `최소 청약 주수 미확인 · 10주 기준 추정`을 붙입니다(값을 지어내지 않습니다).
  확인된 주수가 10주가 아니면 금액 옆에 `50주`·`100주` 칩으로 근거를 함께 보여 줍니다.
- **균등 최소증거금 카드**(`#cash-card`) 계산: `공모가 × 최소청약주수 × 증거금률`.
  증거금률은 **일반 공모주 50%, 스팩(기업인수목적회사) 100%** 입니다(`data.json` 의 `spac` 플래그 또는
  종목명에 `스팩`·`기업인수목적`이 들어가면 100%). 스팩 종목은 금액 옆에 `증거금 100%` 표시를 붙입니다.
  공모가가 `희망 A~B원`이면 보수적으로 상단 B를 씁니다. 자금은 `start ≤ d < refund`(환불일 전날까지) 묶이는 것으로 보고,
  날짜별 동시 묶임의 최댓값(피크)과 그날 겹치는 종목, 선택 범위의 단순 합계를 보여 줍니다.
  칩은 `이번 달 (M월)` / `전체 예정 (M~M월)` / `스팩 제외`(기본 ON)이고, 누르면 같은 데이터로 즉시 다시 계산합니다.
  일정 카드에서 스팩·이미 환불된 종목은 목록에 그대로 두고 금액에서만 뺍니다.
- `ipo.cancelled`(예: 아델 상장 철회)는 오늘 요약 탭의 작은 행과 전체 일정 탭 하단에 함께 나옵니다.
- 값은 38커뮤니케이션 공개 표·상세 페이지에서 확인한 것만 넣고, 확정 전 공모가는 `희망 …`으로 적습니다.

1레벨은 큰 이름·가격과 강조색(히어로 카드)으로, 2레벨은 작은 글씨·얇은 행·낮은 대비로 무게감을 분리했습니다.
3레벨 응원 카드는 고지문 바로 위에 한 장만 두고, 누르면 카카오페이 송금 QR 링크가 새 탭으로 열립니다(`_blank`, `rel="noopener noreferrer"`).
검색 노출을 위해 `robots: index, follow` 와 canonical URL 을 두었습니다.

### 검색엔진 대비 (SEO)

| 항목 | 내용 |
| --- | --- |
| `<title>` | `공모주 청약 일정·균등 최소증거금 — 마이돈 오늘의 공모주` (검색 키워드를 앞에) |
| `description` · `og:*` · `twitter:*` | 청약 일정·상장일 시초가·균등 최소 필요금액(증거금)·증권사 앱 바로가기 키워드를 담은 90자 안팎 설명 |
| `og:image` | `https://ipo.mydon.kr/banner.png` (800×280, `generate_banner.py` 가 매일 다시 만드는 배너) · `twitter:image` 는 아이콘 512 |
| JSON-LD | `WebSite` + `Organization` + `WebApplication`(`FinanceApplication`, 무료) — 화면에는 영향 없음 |
| `robots.txt` | 전체 허용 + `Sitemap: https://ipo.mydon.kr/sitemap.xml` |
| `sitemap.xml` | 루트 1건 · `<lastmod>` 는 `fetch_ipo_feeds.py --sync-data` 가 data.json 이 바뀔 때 수집일로 갱신 |
| `sw.js` | `robots.txt`·`sitemap.xml` 요청은 가로채지 않고 네트워크로 그대로 보냄 |

검색엔진 등록(구글 서치콘솔·네이버 서치어드바이저)은 사이트 소유 확인이 필요해 계정 주인이 직접 해야 합니다.
`https://ipo.mydon.kr/sitemap.xml` 을 제출하면 됩니다.

## 헤더의 갱신 시각

| 표시 | 값의 출처 | 의미 |
| --- | --- | --- |
| 우상단 `09:06 업데이트` | `data.json` 의 `updatedLabel` (`#updated`) | 마지막으로 데이터를 실제로 갱신한 시각 |
| 날짜 줄 아래 `평일 07:30 · 16:05 자동 갱신` | `index.html` 의 정적 문구 (`.sched`) | 자동 갱신이 도는 고정 시각 — 평일 07:30·16:05 KST (`📈 당일 공모주 청약 & 공모주한잔 브리핑` 루틴) |

두 값은 역할이 다릅니다. 마지막 갱신 시각은 데이터가 정하고, 자동 갱신 시각은 `index.html` 의 한 줄을 고치면 바뀝니다.
루틴 실행 시각을 바꿀 때는 `index.html` 의 `.sched` 문구도 함께 맞춰 주세요.

## 구성

| 파일 | 역할 |
| --- | --- |
| `index.html` | 화면 뼈대 (헤더 · 1레벨 히어로 컨테이너 · 2레벨 접힘 혜택 · 고지문) |
| `styles.css` | 모바일 390px 기준 스타일, 기본 라이트 고정 + 상단 토글 다크(`html[data-theme="dark"]`) |
| `app.js` | `data.json` 렌더 — 히어로 요약과 접힘 혜택 행 (데이터에 코드가 있으면 복사 버튼도 동작) |
| `data.json` | 표시할 모든 데이터 (공모주 + 이벤트 + 고지문) |
| `manifest.webmanifest` | 홈 화면에 추가(PWA) 매니페스트 — 이름·`start_url`·`scope`·`standalone`·아이콘·테마 색 |
| `sw.js` | 최소 서비스 워커(설치 조건 + fetch 패스스루). **캐시를 두지 않아** 매일 바뀌는 `data.json`·디자인이 바로 반영된다 |
| `icons/` | 홈 화면 아이콘 3종(192·512·apple-touch 180) — `scripts/generate_icons.py` 가 만든다 |
| `banner.png` | 블로그·티스토리에 붙이는 요약 배너 (800×280) — `scripts/generate_banner.py` 가 `data.json` 으로 매일 다시 만든다 |
| `scripts/generate_banner.py` | 배너 생성기 (Pillow · 한글 폰트 동봉) — `--self-test` 로 네 가지 상황을 확인 |
| `check_render.py` | 390×844 Playwright 검증 + 스크린샷 생성 (스크린샷은 `.gitignore`, 저장소에 올리지 않음) |
| `scripts/generate_icons.py` | 홈 화면 아이콘 생성기 (Pillow · 폰트 불필요, 블루 배경 + 흰 막대 3개) |
| `scripts/fetch_ipo_feeds.py` | 공모주 유튜브 2채널 RSS + 38커뮤니케이션 청약·신규상장 일정 수집기. `--sync-data` 로 `data.json` 전체 일정까지 자동 병합 (API 키 불필요) |
| `feeds.json` | 수집기가 만드는 최신 영상·청약일정·신규상장 스냅샷 (사람이 쓰는 `data.json` 과 분리). `app.js` 가 화면에서 함께 읽어 **유튜버 1줄 요약**을 채웁니다 |
| `scripts/fetch_listing_price.py` | 상장일 시초가·종가 조회기 — 네이버 금융 실시간 API에서 `ov`·`nv`·`hv`를 읽어 공모가 대비 등락률과 함께 JSON으로 출력하고, `--mode open·close --apply-data` 로 `ipo.listing`에 반영 |
| `.github/workflows/update-ipo-feeds.yml` | 평일 06:13·16:13 KST 자동 수집·병합·커밋 |

## 홈 화면에 앱으로 추가 (PWA)

앱스토어 없이 **홈 화면 아이콘으로 열리는 웹앱**입니다. 주소 표시줄 없이 `standalone`으로 뜨고,
화면·데이터는 평소와 똑같이 매일 갱신됩니다.

| 파일 | 내용 |
| --- | --- |
| `manifest.webmanifest` | `name` `마이돈 — 오늘의 공모주 1분 요약` · `short_name` `마이돈 공모주` · `start_url`/`scope` `/` · `display` `standalone` · `background_color` `#f4f6f8` · `theme_color` `#3182f6` · 아이콘 192·512(`purpose: any`) |
| `sw.js` | 설치 조건용 fetch 핸들러 하나. **network-first(사실상 패스스루)** 이고 `caches.open`/`addAll`/`cache.put` 을 쓰지 않는다 — 옛 HTML·`data.json` 이 기기에 고정되면 하루 종일 어제 요약이 뜨기 때문. 오프라인일 때만 안내 한 장을 돌려준다 |
| `icons/icon-192.png` · `icons/icon-512.png` · `icons/apple-touch-icon.png` | `#3182f6` 꽉 찬 배경 + 흰 막대 3개(헤더 브랜드 마크와 같은 모양). 글자를 넣지 않아 작은 크기에서도 깨지지 않는다 — `python3 scripts/generate_icons.py` 로 다시 만든다 |
| `_headers` | `/manifest.webmanifest`·`/sw.js` 는 60초(`must-revalidate`), `/icons/*` 는 7일 캐시 |

화면에는 `오늘 요약` 탭 하단(`.ben-link` 아래·`블로그 배너 퍼가기` 위)에 **얇은 한 줄**로만 둡니다.

- 이미 홈 화면(`standalone`)에서 열었으면 보이지 않습니다.
- **Android·데스크톱 크롬**: `beforeinstallprompt` 가 올 때만 나타나고, 누르면 브라우저의 설치 창(`prompt()`)이 뜹니다. 설치는 사용자가 그 창에서 결정합니다.
- **iOS(Safari)**: 설치 API 가 없으므로 누르면 `하단 공유(□↑) 버튼 → '홈 화면에 추가'를 누르면 앱처럼 바로 열려요` 안내를 펼칩니다(다시 누르면 접힘). 카톡·인스타 같은 인앱 브라우저에서는 홈 화면 추가가 없어 띄우지 않습니다.
- **×** 로 닫으면 `localStorage('mydon-install-hide')` 에 남겨 다시 띄우지 않습니다.

## 미리보기

```bash
python3 -m http.server 8000
# → http://localhost:8000/
```

`fetch('data.json')`을 쓰기 때문에 파일을 직접 열지 말고 로컬 서버로 열어야 합니다.

## 블로그 배너 (`banner.png`)

블로그 글 상단에 붙이는 **가로형 요약 이미지**입니다. 사이트의 `오늘 요약` 맨 아래
`블로그 배너 퍼가기`가 이 파일을 그대로 내보냅니다.

```bash
python3 scripts/generate_banner.py                 # data.json 으로 banner.png 다시 만들기
python3 scripts/generate_banner.py --date 2026-11-24   # 기준일 고정(확인용)
python3 scripts/generate_banner.py --self-test     # 평일 청약·상장·일정 없음·주말 네 가지를 임시 폴더에 그려 확인
```

- **표시 내용**: `마이돈 · 공모주` 라벨 · 기준일(`11/20(금) 16:15`, 주말이면 `수집`) · 핵심 요약
  (평일 = `오늘 청약 종목`/`오늘 상장 종목`, 주말 = `다음 주 청약 N건`) · 기간·주관사·환불일 ·
  **균등 최소증거금 피크**(날짜·겹치는 종목) · `ipo.mydon.kr`.
- **계산 규칙은 화면과 같습니다**(`app.js`): 증거금 = 공모가 × 최소청약주수(증권신고서 `minShares`, 확인 전이면 10주 추정) × 증거금률(일반 50%·스팩 100%),
  희망가면 상단 — 피크는 날짜별 동시 묶임(청약 시작일 ≤ d < 환불일)의 최댓값.
  카드 아래 기준 줄도 데이터에서 계산합니다: 모두 확인되면 `신고서 최소 주수`, 하나라도 추정이면 `10주 추정 포함`.
  평일은 `이번 달 · 스팩 제외`(전체 일정 탭 카드와 같은 조건), 주말은 `다음 주(월~일) · 스팩 포함`(주말 히어로와 같은 조건)입니다.
- **생성 시점의 오늘(KST)** 을 기준으로 상황을 고릅니다 — `data.json` 갱신 직후(평일 07:30·16:05) 만들면
  그날 화면과 같은 내용이 됩니다. `--date` 는 확인용으로만 씁니다.
- **한글 폰트**: `scripts/fonts/NanumGothic-Bold.ttf`(본문은 시스템 Noto Sans CJK KR)를 쓰고,
  폰트를 찾지 못하면 빈 네모가 찍힌 배너를 만들지 않고 exit 1 로 멈춥니다.
- **캐시**: `_headers` 의 `/banner.png` 는 `max-age=60, must-revalidate` — 블로그에 박힌 이미지가
  하루 종일 옛 요약으로 남지 않습니다.
- **갱신**: `📈 당일 공모주 청약 & 공모주한잔 브리핑` 루틴이 `data.json` 과 **같은 커밋**에 `banner.png` 를 넣습니다
  (생성 → 확인 → 커밋 순서).

## 검증

```bash
python3 check_render.py
```

콘솔 에러·가로 스크롤·요소 잘림·개인정보 문구 포함 여부에 더해,
**테마**(기본 라이트 고정 — 시스템 다크에서도 `--bg` `#f4f6f8`·`data-theme` 없음 / 헤더 오른쪽 해·달 버튼이
`업데이트` 옆 같은 줄·26px·이모지 아님·24px 높이 유지 / 누르면 `data-theme="dark"`·`--bg` `#101012`·
`mydon-theme=dark` 저장·아이콘·`aria-label`·`aria-pressed`·`theme-color` 동기화 / 새로고침 후에도 다크 유지 /
다시 누르면 라이트 복귀),
**위계**(히어로가 접힌 아코디언보다 위, 오늘 청약/상장·결론·최소증거금·유튜브 요약·다음 청약 D-day가
첫 화면 844px 안), **2레벨 기본 접힘과 펼침 동작**(행 상세에 조건·신청 방법·공식 링크),
하단 응원 카드의 링크·`target`/`rel`·잘림 여부, **3탭 전환**(기본 오늘 요약 → `?tab=schedule`,
`?tab=benefits`, 되돌리기, 딥링크, 390px 한 줄 3열·같은 폭·글자 잘림 없음)과
**전체 일정 화면**(카드 수·D-day·희망 공모가·주관사·38 출처 링크·가로 스크롤/잘림 없음),
**혜택 탭**(`오늘 요약`에는 혜택 상세가 없고 배너만 / 배너 문구·건수·링크·탭 전환 / 칩 3개와 건수 /
카드마다 카테고리·D-day·혜택명·금액·대상·마감·기간·공식 링크(`_blank`)/ `유의사항·신청 방법` 펼침 /
카테고리 필터 결과 / 개인정보 문구 0건 / 가로 스크롤·요소 잘림 없음)을
모바일·다크 모드·데스크톱(1280) 모두에서 확인하고 `RESULT: PASS`를 출력합니다.
`expiresAt` 만료 숨김은 만료/오늘/상시 테스트 혜택을 주입해 검사합니다.

**주말 모드**도 함께 검사합니다. 평일 화면은 data.json 의 수집일(마지막 영업일)로 날짜를 고정(`?date=`)해
요일과 무관하게 같은 기대값으로 보고, 이어서 토·일(`?date=`)에서 `.hero.is-weekend`
(배지 `주말 휴장`·`다음 주 청약 미리보기`, `다음 주 청약 N건`, 다음 주 종목·기간·공모가·균등 증거금,
다음 주 피크 자금·겹치는 종목, `직전 영업일(11/20) 상장` 보조 카드, `오늘 청약`·`오늘 상장` 문구 0건,
공유 2버튼·탭·다크·데스크톱 유지, 다음 주 0건 빈 상태, 평일에는 주말 카드 없음,
`?date` 없는 오늘(KST)이 그날에 맞는 카드를 내는지)까지 확인합니다.

**홈 화면에 앱으로 추가(PWA)** 도 검사합니다. `manifest.webmanifest`(이름·`short_name`·`start_url`·`scope`·`display`·`background_color`·`theme_color`·아이콘 2개)와 아이콘 3종의 HTTP 200·PNG 크기(192·512·180), `sw.js` 200·fetch 핸들러 보유·**Cache Storage 미사용**, `<head>` 의 manifest·apple-touch·icon 링크·iOS 메타, 서비스 워커 등록·컨트롤러와 오프라인 안내, 그리고 설치 한 줄이 **기본 숨김 → Android 이벤트 뒤 표시(44px 이상·62px 높이·`#ben-link`와 `#banner-embed` 사이) → 누르면 `prompt()` 1회·수락 시 숨김+저장 / 거절 시 이번 화면만 숨김**, × 닫기 저장·재발생·새로고침 후 재노출 없음, iOS 안내 펼침·접힘·문구 일치, 카톡 인앱·standalone·iOS standalone 숨김, 데스크톱·다크에서 표시를 확인합니다. 헤드리스 크롬은 설치 조건을 스스로 판단하지 않으므로 `beforeinstallprompt` 모양의 이벤트를 직접 던져 확인합니다.

**정보 공유 바(`.share`)** 도 함께 검사합니다. 히어로와 철회·출처 사이 위치, **2버튼 고정**
(`청약 정보 공유` | `상장 정보 공유`)의 2열 그리드(같은 줄·같은 폭·높이 44px 이상·글자 잘림 없음),
왼쪽 `--sun-soft`/`--sun`·오른쪽 `--blue-soft`/`--blue` 색,
`navigator.share` 로 `{title, text, url}` 전달(`text`에 URL 없음 · title 은 `공모주 청약 정보`/`공모주 상장 정보`),
미지원(헤드리스)·`AbortError` 이외 오류 시 같은 버튼이 **각 포맷과 정확히 일치하는**
클립보드(현재 `data.json` 기준 기대값과 문자열 동일 · URL 1회 · 개인정보 0건)로 폴백하며
토스트와 라벨 `복사됐어요` 되돌림까지 동작하는지, `AbortError`(사용자가 닫음)에는 조용한지 —
모바일·다크·데스크톱에서 확인합니다.

풀 필드 mock 2건(12항목 + 청약 의견, 빈 줄 구분, 값이 빠진 종목)으로 청약 공유문을,
상장 mock 3건(7항목 · 값이 빠진 종목 · **장 시작 전 상장 예정**)으로 상장 공유문을 **고정 문자열과 대조**하고,
`미정`·`확인 필요` 항목이 줄로 나가지 않는지, 오늘 청약 0건이면 `ipo.next`로 `11/25 마감 예정` 폴백되는지,
상장 없는 날은 오른쪽 버튼이 `:disabled` + `오늘 상장 없음`(커서 default·연한 회색·눌러도 복사 없음),
청약·다음 청약까지 모두 없는 날은 왼쪽 버튼이 `오늘 청약 없음` 비활성으로 남는지도 검사합니다.

**장 시작 전 상장 예정(07:30~09:00)** 도 따로 검사합니다. 시초가·종가·직전 체결가가 모두 빈 mock 에서
`.hero.is-list .hprice.is-pre` 가 `09:00 상장 예정`(20px·데스크톱 22px, 빈 `<b>` 아님)과
`가격제한폭 3,420원 ~ 22,800원 (60~400%)`(공모가 5,700원에서 계산)을 보여 주고, `공모가` 줄·`오늘 상장` 배지는 그대로이며,
공유문은 `* 상장 시각: 09:00 (장 시작 전)` + 가격제한폭 1줄(중복 없음)로 고정 문자열과 일치하는지,
`priceBand` 가 이미 적힌 mock 에서는 계산값을 덧붙이지 않는지, 시초·종가가 들어온 상장일에는 `.is-pre` 가 없는지,
모바일·다크·데스크톱에서 가로 스크롤·요소 잘림·콘솔 오류가 없는지 확인합니다
(스크린샷: `preview-mobile-listing-premarket.png` · `-dark.png` · `preview-desktop-listing-premarket.png`).

**📱 주관사 앱 열기 버튼**도 함께 검사합니다. 오늘 상장 카드(`하나에어로다이내믹스` · 주관 IBK투자증권)에
`📱 IBK투자증권 앱 열기`가 **3줄 요약 아래·다음 청약 띠 위**에 1개 있고,
- **Android UA**: 확인된 딥링크가 없는 IBK투자증권이므로 `href`가 `https://play.google.com/store/apps/details?id=com.ibks.ione.mts`(`_blank`/`noopener` — 새 탭)
- **iPhone UA**: `https://apps.apple.com/kr/app/id6612018102`
- **Desktop UA**: `https://play.google.com/store/apps/details?id=com.ibks.ione.mts` (`_blank`/`noopener`)

로 바뀌는지, 청약 당일 mock(`KB증권 · NH투자증권`)에서
카드마다 `📱 KB증권 앱 열기`(Play 스토어)·`📱 NH투자증권 앱 열기`(`intent://txrun/#Intent;scheme=txsmart;package=com.wooriwm.txsmart;…;end`) 2개가 뜨는지(단일 주관사 카드는 1개),
`intent://` 는 `S.browser_fallback_url`(Play 인코딩)·`;end`·`target` 없음을, 스토어 링크는 `target="_blank"`·`noopener` 를 지키는지,
모두 높이 36px 이상·가로 스크롤 없음·요소 잘림 없음인지, 다크 모드에서도 같은 버튼이
보이고 38px을 유지하는지 확인합니다.

**블로그 배너 퍼가기(`.banner-embed`)** 도 함께 검사합니다. 접힌 상태에서는 한 줄(44px·`aria-expanded=false`),
누르면 `banner.png` 미리보기가 800×280 실제 크기로 로드되고(깨진 이미지·잘림 없음), 코드 원문이
`<a href="https://ipo.mydon.kr" …><img src="https://ipo.mydon.kr/banner.png" …></a>` 와 같으며,
`HTML 코드 복사`·`이미지 URL 복사`가 클립보드에 각각 그 문자열과 `https://ipo.mydon.kr/banner.png` 를 넣고
토스트·라벨 `복사됐어요` 되돌림까지 동작하는지, 이모지 없음·가로 스크롤·요소 잘림 없음,
모바일·다크·데스크톱에서 같은 모양인지 확인합니다.

```bash
python3 check_prod.py   # 배포 URL 검증 (같은 공유 바·배너 항목 포함)
```
검증 스크린샷(`preview-mobile*.png`, `preview-mobile-schedule*.png`, `preview-desktop*.png`, `preview-toast.png`)도 함께 갱신되지만 저장소에는 커밋하지 않습니다.
개인정보 검사어는 `privacy_terms.txt`(한 줄에 하나)에서 읽으며, 이 파일은 `.gitignore` 로 저장소에 올리지 않습니다.

## 데이터 갱신 방법

- **공모주**: `data.json`의 `ipo` 블록만 교체(`ipo.upcoming` 포함). 공유문에 나가는
  `ipo.subscribe[]`·`ipo.next`의 청약 정보 필드와 `ipo.listing`의 상장 정보 필드를 위 표대로 채우고,
  확인 못 한 값은 빈 문자열로 둡니다(`ipo.listing`은 `hasListing`과 `brokers`만 정확히).
- **혜택**: `benefits` 배열에 객체 추가.
  - `category`: `securities`(증권사·금융) 또는 `simple`(간편 이벤트·설문). 없으면 `securities`.
  - `provider`: 혜택을 주는 곳(예: `삼성증권`, `경기관광공사`).
  - `title`: 혜택명 / `benefit`: 카드에 크게 보이는 핵심 금액·조건 / `benefitNote`: 한 줄 설명.
  - `target`: 대상(선택) / `period`: 사람이 읽는 기간 문자열(예: `2026.11.02~11.30`).
  - `expiresAt`: `YYYY-MM-DD`. **상시 혜택은 `null`**. 기기 기준 오늘 날짜가 이 날짜를 지나면
    카드가 화면에서 자동으로 빠지고, 머리말에 "N건 자동으로 숨겼어요"로만 표시됩니다.
  - `howTo`: 어느 앱·폼에서 어떻게 신청·응모하는지 한 줄(카드의 `유의사항·신청 방법` 안).
  - `terms`: 유의사항 문자열 배열(같은 접힘 안).
  - `link`: `{label, url}` — 공식 페이지·폼. 카드의 `자세히 보기` 버튼(새 탭).
  - `verifiedAt`: 마지막으로 공식 페이지를 확인한 날짜.
  - 머리말 안내줄은 `benefitsAsOf`, 숨긴 건수를 자동으로 계산합니다. **확인되지 않은 금액·마감일은 넣지 않습니다.**
- `draft`: `true` 면 날짜 옆에 `draftNote` 배지가 붙습니다. 현재는 `false`.

## 자동 수집 (`scripts/fetch_ipo_feeds.py`)

API 키 없이 도는 수집기입니다. 기본 동작은 화면 데이터(`data.json`)를 건드리지 않고 `feeds.json` 만 쓰고,
`--sync-data` 를 붙이면 `data.json` 의 전체 일정(`ipo.upcoming`)과 `ipo.next`·`ipo.nextListing` 도
38커뮤니케이션 최신 표 기준으로 자동 병합 갱신합니다.

```bash
python3 scripts/fetch_ipo_feeds.py              # feeds.json 갱신 + 새 영상·새 일정 요약 출력
python3 scripts/fetch_ipo_feeds.py --dry-run    # 파일을 쓰지 않고 확인만
python3 scripts/fetch_ipo_feeds.py --sync-data  # + data.json 전체 일정 병합 (바뀌면 banner.png 도 재생성)
python3 scripts/fetch_ipo_feeds.py --sync-data --dry-run
```

- **유튜버 1줄 요약(화면)**: `app.js` 가 `data.json` 과 함께 `feeds.json` 을 읽어, 오늘 종목명이 제목에 들어간
  최신 영상(75일 이내)을 채널별로 찾습니다. `data.json` 의 `ipo.hanjan.items`·`ipo.gongmorin` 큐레이션 판단이 있으면
  그 배지(균등·비례·관점)를 먼저 쓰고, 비어 있는 채널만 `feeds.json` 영상으로 채웁니다.
  표시는 `채널 · 제목에서 읽은 톤(신중/수급/기대) · 업로드 날짜 · 영상›` + 영상 제목에서 뽑은 한 줄(1줄 말줄임).
  **예상 매도가·목표가·원화 금액이 들어간 문구는 요약으로 옮기지 않습니다**(제목에 있으면 요약 생략).
  관련 영상이 하나도 없으면 `공모주한잔·공주 관련 영상 없음` 한 줄만 남깁니다(상장 카드는 `ipo.gongmorin`
  판단을 붙이지 않고 종목명이 맞는 영상만 씁니다).
- **유튜브**: `공모주한잔`(UC8kMkLj4kAqMTeOeVQgxyUg), `공모주투자의법칙(공주)`(UCstq1xNCuEIR43dM3CMop3g) RSS에서
  최신 5개 영상의 제목·URL·업로드 시각을 가져옵니다.
- **38커뮤니케이션**(`http://www.38.co.kr/html/fund/index.htm?o=k`, EUC-KR): 공모주 청약일정 표
  (종목명·청약기간·확정/희망 공모가·경쟁률·주관사)와 IPO 신규상장 일정(`?o=nw` — 상장일·확정 공모가·시초가·첫날종가)을 파싱합니다.
- 지난 `feeds.json` 과 비교해 새로 올라온 영상·일정만 stdout 에 요약하고, 바뀐 내용이 없으면
  파일을 다시 쓰지 않습니다. 청약기간이 끝난 일정은 저장에서 뺍니다.

### `--sync-data` 병합 규칙

- **보존**: 같은 종목명이면 기존 항목의 키 순서와 38표에 없는 정밀 필드(`minShares`, `code`,
  `spac`, `ipo.next`의 `lockupRate`·`marketCap`·`minSubscription`·`fee`·`equalShares`·
  `expectedProRata`·`proRata10Shares`·`fullSubscription`·`listingDate`·`opinion`·`minShares` 등)를 절대 지우지 않습니다.
  (2026-11-23 확인: 38표에 `minShares`가 없는 항목을 다시 병합해도 값이 그대로 남고, `ipo.next` 도 같은 종목이면 `minShares` 를 유지합니다.)
- **minShares 미확인 알림**: 병합 뒤 `minShares` 가 비어 있는 종목은 `minShares 미확인(10주 추정): {종목} — 증권신고서 최소 청약 주수 확인 필요` 로 알려 줍니다.
- **갱신**: 청약기간·공모가(희망 → 확정 전환 포함)·주관사·상장일은 매 실행 최신 표 값으로 바뀝니다.
- **신규 종목**: 38 상세 페이지를 한 번 더 읽어 시장구분(`market`)·종목코드(`code`)·환불일(`refund`)을 채웁니다.
- **환불일**: 상세 페이지 값(공휴일 반영) 우선, 없으면 마감일 + 2영업일로 계산합니다.
- **`asOf`·`windowLabel`**: 수집일과 첫 청약일 ~ 마지막 청약일 범위로 자동 계산합니다.
- **`ipo.next`**: 아직 시작 안 한 청약 중 가장 이른 종목(같은 날이면 스팩을 뒤로) + '같은 날 N도 청약' 메모.
- **`ipo.nextListing`**: 가장 이른 상장 예정 종목 + '{요일} 상장' 메모.
- **배너**: `data.json` 내용이 실제로 바뀌었을 때만 `scripts/generate_banner.py` 로 `banner.png` 를 다시 만듭니다
  (`--no-banner` 로 생략). 두 파일은 항상 같은 커밋에 넣습니다.
- 38 청약일정 표를 못 읽은 실행은 `data.json` 을 손대지 않고 건너뜁니다(빈 일정으로 덮는 사고 방지).

### 공모주 인사이트

기존 워크플로가 공모주한잔·공모주투자의법칙의 YouTube RSS 응답을 재사용하고, 인사이트용으로 주식애소리·경제적자유민족·소유보다 경험(아이언)을 추가 수집해 `insights.json`을 갱신합니다. 인사이트 탭에는 게시 후 7일 이내 영상과 그 영상들의 종합 요약이 표시되고, 오늘의 인사이트는 최근 24시간에 처음 수집한 영상 중 자막이나 공개 영상에 근거한 요약이 있는 영상으로 작성합니다. 신규 요약이 없으면 마지막 종합과 작성 시각을 표시합니다.

- [Google AI Studio](https://aistudio.google.com/app/apikey)에서 무료 프로젝트용 키를 발급하고 GitHub Actions에 `GEMINI_API_KEY` 저장소 시크릿으로 등록합니다. 기본 모델은 `gemini-3.1-flash-lite`이며 `IPO_INSIGHTS_MODEL` 저장소 변수로 변경할 수 있습니다. 무료로만 운영하려면 프로젝트에 유료 결제를 연결하지 않습니다. [Gemini 무료 티어 요금](https://ai.google.dev/gemini-api/docs/pricing)
- Gemini가 사용 한도 초과(HTTP 429)를 반환하면 해당 실행의 남은 AI 호출을 중단합니다. 영상 정보와 기존 요약은 보존되며, 다음 배치에서 요약을 다시 시도합니다. 무료 티어에 전송한 자막과 응답은 Google 제품 개선에 사용될 수 있습니다. [Gemini API 약관](https://ai.google.dev/gemini-api/terms)
- 자막을 가져오지 못한 공개 영상은 Gemini가 영상과 음성을 직접 분석합니다. 무료로 운영하려면 Google AI Studio에서 키가 속한 프로젝트의 결제 티어를 Free로 유지합니다. 배치에서 영상 분석을 끄려면 `IPO_INSIGHTS_VIDEO_FALLBACK` 저장소 변수를 `false`로 설정합니다. 성공한 경우 화면에 ‘영상 기반 요약’으로 표시합니다. [Gemini 공개 영상 분석](https://ai.google.dev/gemini-api/docs/video-understanding#youtube)
- 영상 ID별 처리 결과를 저장하며, 실행당 미처리 영상 최대 4개를 요약합니다. 최근 7일 종합은 범위 안에서 요약된 영상 구성이 바뀔 때 갱신하고, 오늘 종합과 영상 구성이 같으면 결과를 재사용합니다. 키가 없거나 자막·영상에서 요약 근거를 확보하지 못하면 영상 정보만 표시합니다. 자막 또는 API 요청에 실패한 건은 게시 후 7일 이내에 다음 배치에서 다시 시도합니다.
- 수동 실행은 Actions의 **공모주 채널·청약일정 수집**에서 할 수 있습니다. 기존 배치 주기를 사용하며 청약 판단은 기존 `data.json`을 읽습니다.

## 상장일 시세 (`scripts/fetch_listing_price.py`)

네이버 금융 실시간 API(`polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{code}`)에서
시초가(`ov`)·현재가(`nv`)·고가(`hv`)·저가(`lv`)를 읽어 공모가 대비 등락률과 함께 JSON 으로 출력합니다.

```bash
python3 scripts/fetch_listing_price.py 271160 --ipo-price 5700          # 조회만 (JSON 출력)
python3 scripts/fetch_listing_price.py --mode open --apply-data         # 시초가 → ipo.listing.openPrice / openChange
python3 scripts/fetch_listing_price.py --mode close --apply-data --stamp 16:05  # 종가 → closePrice / closeChange
```

- 종목코드·공모가를 생략하면 `data.json` 의 `ipo.listing.code`·`ipo.listing.ipoPrice` 를 씁니다
  ('5,700원' 표기도 인식). 그마저 없으면 네이버 기준가(`sv`)를 기준으로 쓰고 `basis` 로 표시합니다.
- `--mode close` 는 15:30 전(장중)에는 경고를 출력합니다 — 종가 확정은 장 마감 뒤 16:05 루틴에서 적용하는 것이 안전합니다.
- `--apply-data` 는 `ipo.listing` 의 가격 필드만 바꿉니다(lockupRate·floatSummary·`points` 등은 손대지 않음).
  `--banner` 로 배너 재생성, `--stamp HH:MM` 으로 `updatedAt`/`updatedLabel` 갱신을 함께 할 수 있습니다.

## 데이터 기준

- `data.json`의 공모주 전체 일정(`ipo.upcoming`)은 `scripts/fetch_ipo_feeds.py --sync-data` 가
  38커뮤니케이션 청약일정(`?o=k`)·신규상장 일정(`?o=nw`) 표와 종목별 상세 페이지에서 자동 병합합니다
  (GitHub Actions가 평일 06:13·16:13 KST에 실행). 그 밖의 오늘 요약·유튜브 코멘트·분석 의견은
  매일 브리핑 루틴에서 사람/AI 확인으로 채웁니다.
  아델은 수요예측(11/12~11/18) 뒤 2026-11-20 증권신고서를 철회해 `ipo.cancelled`로 옮겼습니다.
- 증권사 혜택은 각 사 공식 이벤트 페이지에서 확인한 내용이며, 혜택·마감일·보상 한도는 예고 없이 바뀔 수 있습니다.
- 공모주 일정·경쟁률은 38커뮤니케이션과 각 유튜브 채널 공개 내용을 기준으로 합니다.

## 고지

이 페이지는 공개된 정보를 개인적으로 정리한 것으로, 투자 권유나 청약 권유가 아닙니다.
투자 판단과 책임은 이용자 본인에게 있습니다.
