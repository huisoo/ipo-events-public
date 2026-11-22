/* 마이돈 공모주 — 홈 화면에 추가(PWA)용 최소 서비스 워커
 *
 * 목적
 *   1) Android 크롬 설치 조건(`beforeinstallprompt`)을 채우는 fetch 핸들러 하나.
 *   2) 화면은 항상 최신으로 — 캐시를 두지 않는다.
 *
 * 캐시를 두지 않는 이유
 *   · data.json 은 평일 07:30·16:05 두 번 갱신되고, 디자인도 자주 바뀐다.
 *   · precache 를 걸면 옛 HTML·data.json 이 기기에 고정돼 하루 종일 어제 요약이 뜬다.
 *   · 그래서 모든 GET 은 network-first(fetch 패스스루)이고, HTTP 캐시는 _headers 의
 *     60초(max-age=60, must-revalidate) 규칙에 맡긴다. 별도 Cache Storage 는 쓰지 않는다.
 *   · 오프라인일 때만 안내 한 장(아래 OFFLINE_HTML)을 돌려줘 빈 오류 화면을 막는다.
 *     (안내 문구는 서비스 워커 안에 있으므로 데이터가 섞일 여지가 없다.)
 *
 * 배포 후 즉시 반영
 *   · activate 에서 skipWaiting + clients.claim, 예전 Cache Storage 가 있으면 모두 지운다.
 *   · 파일 자체는 _headers 로 짧게(60초) 캐시된다. 서비스 워커 스크립트는 브라우저가
 *     캐시를 우회해 확인하므로 새 배포가 바로 잡힌다.
 */
'use strict';

var OFFLINE_HTML = '<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">' +
  '<meta name="viewport" content="width=device-width, initial-scale=1">' +
  '<title>마이돈 공모주 — 연결이 끊겼어요</title>' +
  '<style>html,body{margin:0;height:100%;background:#f4f6f8;color:#191f28;' +
  'font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Noto Sans KR",system-ui,sans-serif;' +
  '-webkit-text-size-adjust:100%}main{display:flex;flex-direction:column;align-items:center;' +
  'justify-content:center;height:100%;padding:24px;text-align:center;gap:10px}' +
  'b{font-size:16px;letter-spacing:-.02em}p{margin:0;font-size:13px;line-height:1.6;color:#4e5968}' +
  'button{margin-top:10px;font:inherit;font-size:13px;font-weight:600;color:#fff;background:#3182f6;' +
  'border:0;border-radius:10px;padding:11px 18px}</style></head><body><main>' +
  '<b>인터넷 연결이 끊겼어요</b>' +
  '<p>연결을 확인한 뒤 다시 열어 주세요.<br>오늘의 공모주는 연결되면 바로 갱신됩니다.</p>' +
  '<button type="button" onclick="location.reload()">새로고침</button>' +
  '</main></body></html>';

self.addEventListener('install', function () {
  /* 새 서비스 워커를 기다리지 않고 바로 쓴다(설치 대기열에 옛 버전을 남기지 않음) */
  self.skipWaiting();
});

self.addEventListener('activate', function (event) {
  var done = Promise.resolve();
  if (self.caches && caches.keys) {
    done = caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) { return caches.delete(k); }));
    });
  }
  event.waitUntil(done.then(function () { return self.clients.claim(); }));
});

self.addEventListener('fetch', function (event) {
  var req = event.request;
  if (req.method !== 'GET') return;

  var url;
  try { url = new URL(req.url); } catch (e) { return; }
  /* 우리 사이트만 다룬다 — Pretendard CDN 같은 외부 요청은 브라우저에 그대로 맡긴다 */
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    fetch(req).catch(function () {
      /* 오프라인: 화면 이동이면 안내 한 장, 그 밖(데이터·이미지)은 조용히 실패 */
      if (req.mode === 'navigate') {
        return new Response(OFFLINE_HTML, {
          status: 200,
          headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' }
        });
      }
      return new Response('', { status: 504, statusText: 'Offline' });
    })
  );
});
