"""Run with python -m unittest discover -s scripts -p test_update_insights.py."""
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import update_insights


def reply(data):
    return io.BytesIO(json.dumps({"candidates": [{"finishReason": "STOP", "content": {
        "parts": [{"text": json.dumps(data)}],
    }}]}).encode())


class InsightTest(unittest.TestCase):
    def test_gemini_json_request_and_response(self):
        response = {"candidates": [{"finishReason": "STOP", "content": {"parts": [
            {"text": "internal", "thought": True}, {"text": '{"overview":"요지"}'},
        ]}}]}
        with (patch.dict(os.environ, {"IPO_INSIGHTS_MODEL": ""}),
              patch.object(update_insights.urllib.request, "urlopen",
                           return_value=io.BytesIO(json.dumps(response).encode())) as urlopen):
            self.assertEqual(update_insights.ask("test", "요약", {"title": "영상"}), {"overview": "요지"})

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url,
                         "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent")
        self.assertEqual(request.get_header("X-goog-api-key"), "test")
        payload = json.loads(request.data)
        self.assertEqual(payload["generationConfig"]["responseMimeType"], "application/json")
        self.assertEqual(json.loads(payload["contents"][0]["parts"][0]["text"]), {"title": "영상"})

    def test_video_fallback_requires_opt_in_and_uses_video_input(self):
        now = dt.datetime(2026, 11, 27, 12, tzinfo=dt.timezone.utc)
        video_id = "A" * 11
        channels = [{"channelId": "channel", "channelTitle": "채널", "videos": [
            {"videoId": video_id, "title": "공모주", "published": now.isoformat()},
        ]}]
        summary = {"summary": ["첫 문장", "둘째 문장", "셋째 문장"], "category": "청약 분석"}
        daily = {"overview": "요지", "common": None, "contrasting": None}

        def reply(data):
            return io.BytesIO(json.dumps({"candidates": [{"finishReason": "STOP", "content": {
                "parts": [{"text": json.dumps(data)}],
            }}]}).encode())

        with (tempfile.TemporaryDirectory() as folder,
              patch.dict(os.environ, {"GEMINI_API_KEY": "test", "IPO_INSIGHTS_VIDEO_FALLBACK": ""}),
              patch.object(update_insights, "captions", side_effect=RuntimeError("blocked")),
              patch.object(update_insights.urllib.request, "urlopen",
                           side_effect=[reply(summary), reply(daily)]) as api):
            path = Path(folder) / "insights.json"
            update_insights.update_insights(channels, now, path)
            api.assert_not_called()
            with patch.dict(os.environ, {"IPO_INSIGHTS_VIDEO_FALLBACK": "true"}):
                update_insights.update_insights(channels, now, path)
                api.assert_not_called()
                update_insights.update_insights(channels, now, path, lambda ids: {video_id: 600})
                update_insights.update_insights(channels, now, path)

            result = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(result["videos"][video_id]["summarySource"], "video")
            self.assertEqual(result["videos"][video_id]["summary"], summary["summary"])
            self.assertEqual(result["today"]["videoIds"], [video_id])
            self.assertEqual(api.call_count, 2)
            self.assertEqual([call.kwargs["timeout"] for call in api.call_args_list], [90, 15])
            parts = json.loads(api.call_args_list[0].args[0].data)["contents"][0]["parts"]
            self.assertEqual(parts[0]["fileData"]["fileUri"], f"https://www.youtube.com/watch?v={video_id}")
            self.assertNotIn("videoMetadata", parts[0]["fileData"])
            self.assertEqual(json.loads(parts[1]["text"]), {"title": "공모주"})

    def test_existing_timeouts_are_saved_and_untried_videos_move_ahead(self):
        now = dt.datetime(2026, 11, 27, 12, tzinfo=dt.timezone.utc)
        ids = [char * 11 for char in "ABCDEFG"]
        batch = update_insights.BATCH_SIZE
        videos = {
            video_id: {"lengthSeconds": 600, "published": (now - dt.timedelta(hours=index)).isoformat()}
            for index, video_id in enumerate(ids)
        }
        with (tempfile.TemporaryDirectory() as folder,
              patch.dict(os.environ, {"GEMINI_API_KEY": "test", "IPO_INSIGHTS_VIDEO_FALLBACK": "true"}),
              patch.object(update_insights, "captions", return_value=""),
              patch.object(update_insights, "summarize_video", side_effect=TimeoutError) as summarize):
            path = Path(folder) / "insights.json"
            path.write_text(json.dumps({"videos": videos, "today": None, "weekly": None}), encoding="utf-8")
            update_insights.update_insights([], now, path)
            saved = json.loads(path.read_text(encoding="utf-8"))["videos"]
            self.assertEqual([saved[video_id]["attemptedAt"] for video_id in ids[:batch]], [now.isoformat()] * batch)
            self.assertNotIn("attemptedAt", saved[ids[batch]])
            self.assertEqual(saved[ids[0]]["failCount"], 1)

            summarize.reset_mock()
            update_insights.update_insights([], now + dt.timedelta(hours=1), path)
            self.assertEqual(summarize.call_args_list[0].kwargs["video_id"], ids[batch])

    def test_gemini_quota_preserves_prior_summary_and_stops_requests(self):
        now = dt.datetime(2026, 11, 27, 12, tzinfo=dt.timezone.utc)
        prior = {"overview": "이전 요약", "videoIds": []}
        channels = [{"channelId": "channel", "channelTitle": "채널", "videos": [
            {"videoId": video_id, "title": "공모주", "published": now.isoformat()}
            for video_id in ("A" * 11, "B" * 11)
        ]}]
        quota = urllib.error.HTTPError("https://generativelanguage.googleapis.com", 429, "Quota", {}, None)
        with (tempfile.TemporaryDirectory() as folder,
              patch.dict(os.environ, {"GEMINI_API_KEY": "test", "IPO_INSIGHTS_VIDEO_FALLBACK": ""}),
              patch.object(update_insights, "captions", return_value="실제 자막"),
              patch.object(update_insights.urllib.request, "urlopen", side_effect=quota) as urlopen):
            path = Path(folder) / "insights.json"
            path.write_text(json.dumps({"today": prior}), encoding="utf-8")
            update_insights.update_insights(channels, now, path)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["today"], prior)
            self.assertEqual(len(saved["videos"]), 2)
            self.assertTrue(all("summary" not in video for video in saved["videos"].values()))
            urlopen.assert_called_once()


    def test_weekly_summary_refreshes_when_a_video_ages_out(self):
        now = dt.datetime(2026, 11, 27, 12, tzinfo=dt.timezone.utc)
        old_id, new_id = "A" * 11, "B" * 11
        video = {"title": "공모주", "channelId": "channel", "channelTitle": "채널",
                 "summary": ["첫 문장", "둘째 문장", "셋째 문장"]}
        old_date = (now - dt.timedelta(days=6)).isoformat()
        videos = {old_id: {**video, "published": old_date, "collectedAt": old_date},
                  new_id: {**video, "published": now.isoformat(), "collectedAt": now.isoformat()}}
        summary = {"overview": "요지", "common": None, "contrasting": None}
        with (tempfile.TemporaryDirectory() as folder,
              patch.dict(os.environ, {"GEMINI_API_KEY": "test"}),
              patch.object(update_insights, "synthesize", return_value=summary) as synthesize):
            path = Path(folder) / "insights.json"
            path.write_text(json.dumps({"videos": videos}), encoding="utf-8")
            update_insights.update_insights([], now, path)
            current = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(current["today"]["videoIds"], [new_id])
            self.assertEqual(current["weekly"]["videoIds"], [old_id, new_id])
            self.assertEqual(synthesize.call_count, 2)

            update_insights.update_insights([], now + dt.timedelta(hours=1), path)
            self.assertEqual(synthesize.call_count, 2)
            update_insights.update_insights([], now + dt.timedelta(days=2), path)
            current = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(current["weekly"]["videoIds"], [new_id])
            self.assertEqual(synthesize.call_count, 2)
            update_insights.update_insights([], now + dt.timedelta(days=8), path)
            current = json.loads(path.read_text(encoding="utf-8"))
            self.assertIsNone(current["weekly"])
            self.assertEqual(current["today"]["videoIds"], [new_id])

    def test_missing_captions_and_failed_channel_preserve_prior_results(self):
        now = dt.datetime(2026, 11, 27, 12, tzinfo=dt.timezone.utc)
        first, second, unavailable, expired = ("A" * 11, "B" * 11, "C" * 11, "D" * 11)

        def channel(name, *entries):
            return {"channelId": name, "channelTitle": name, "videos": [
                {"videoId": video_id, "title": "상장일 전략",
                 "published": (now - dt.timedelta(hours=age)).isoformat()}
                for video_id, age in entries
            ]}

        channels = [channel("가", (first, 2), (unavailable, 1), (expired, 169)),
                    channel("나", (second, 3), (first, 2))]
        lines = ["첫 문장", "둘째 문장", "셋째 문장"]
        video_summary = {"summary": lines, "category": "상장 전략"}
        daily_summary = {"overview": "전체 요지", "common": "공통점", "contrasting": "차이점"}
        with (tempfile.TemporaryDirectory() as folder,
              patch.dict(os.environ, {"GEMINI_API_KEY": "test", "IPO_INSIGHTS_VIDEO_FALLBACK": ""}),
              patch.object(update_insights, "captions",
                           side_effect=lambda video_id: "" if video_id == unavailable else "실제 자막"),
              patch.object(update_insights, "ask", side_effect=[video_summary, video_summary, daily_summary]) as ask):
            path = Path(folder) / "insights.json"
            update_insights.update_insights(channels, now, path)
            original = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(original["videos"]), {first, second, unavailable})
            self.assertEqual(original["videos"][first]["summary"], lines)
            self.assertNotIn("summary", original["videos"][unavailable])
            self.assertEqual(original["today"]["videoIds"], [first, second])
            self.assertEqual(original["today"]["contrasting"], "차이점")
            self.assertEqual(ask.call_args_list[0].args[2]["transcript"], "실제 자막")

            update_insights.update_insights(channels[:1], now + dt.timedelta(hours=25), path)
            reloaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(reloaded["today"], original["today"])
            self.assertEqual(reloaded["videos"][second], original["videos"][second])
            self.assertEqual(ask.call_count, 3)

    def test_http_error_logs_status_and_body(self):
        body = io.BytesIO(b'{"error": {"message": "API key not valid"}}')
        error = urllib.error.HTTPError(
            "https://generativelanguage.googleapis.com", 400, "Bad Request", {}, body)
        stderr = io.StringIO()
        with (patch.object(update_insights.urllib.request, "urlopen", side_effect=error),
              patch("sys.stderr", stderr)):
            with self.assertRaises(urllib.error.HTTPError):
                update_insights.ask("test", "요약", {"title": "영상"})
        logged = stderr.getvalue()
        self.assertIn("Gemini HTTP 400", logged)
        self.assertIn("API key not valid", logged)

    def test_description_is_used_before_video_input(self):
        now = dt.datetime(2026, 11, 28, 1, tzinfo=dt.timezone.utc)
        video_id = "A" * 11
        description = "공모주 청약 일정과 상장 전략을 설명하는 긴 설명란입니다. " * 8
        channels = [{"channelId": "channel", "channelTitle": "채널", "videos": [
            {"videoId": video_id, "title": "공모주", "published": now.isoformat(), "description": description},
        ]}]
        summary = {"summary": ["첫 문장", "둘째 문장", "셋째 문장"], "category": "청약 분석"}
        daily = {"overview": "요지", "common": None, "contrasting": None}
        with (tempfile.TemporaryDirectory() as folder,
              patch.dict(os.environ, {"GEMINI_API_KEY": "test", "IPO_INSIGHTS_VIDEO_FALLBACK": "true"}),
              patch.object(update_insights, "captions", side_effect=RuntimeError("blocked")),
              patch.object(update_insights.urllib.request, "urlopen",
                           side_effect=[reply(summary), reply(daily)]) as api):
            path = Path(folder) / "insights.json"
            update_insights.update_insights(channels, now, path)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["videos"][video_id]["summarySource"], "notes")
            self.assertEqual(saved["videos"][video_id]["summary"], summary["summary"])
            self.assertNotIn("failCount", saved["videos"][video_id])
            self.assertEqual(api.call_count, 2)
            parts = json.loads(api.call_args_list[0].args[0].data)["contents"][0]["parts"]
            self.assertNotIn("fileData", parts[0])
            self.assertTrue(json.loads(parts[0]["text"])["notes"].startswith("공모주 청약 일정"))

    def test_live_video_analysis_is_limited_to_first_ten_minutes(self):
        now = dt.datetime(2026, 11, 28, 2, tzinfo=dt.timezone.utc)
        video_id = "A" * 11
        channels = [{"channelId": "channel", "channelTitle": "채널", "videos": [
            {"videoId": video_id, "title": "공모주 LIVE 풀버전", "lengthSeconds": 7200, "published": now.isoformat()},
        ]}]
        summary = {"summary": ["첫 문장", "둘째 문장", "셋째 문장"], "category": "시장 전망"}
        daily = {"overview": "요지", "common": None, "contrasting": None}
        with (tempfile.TemporaryDirectory() as folder,
              patch.dict(os.environ, {"GEMINI_API_KEY": "test", "IPO_INSIGHTS_VIDEO_FALLBACK": "true"}),
              patch.object(update_insights, "captions", return_value=""),
              patch.object(update_insights.urllib.request, "urlopen",
                           side_effect=[reply(summary), reply(daily)]) as api):
            path = Path(folder) / "insights.json"
            update_insights.update_insights(channels, now, path)
            parts = json.loads(api.call_args_list[0].args[0].data)["contents"][0]["parts"]
            self.assertEqual(parts[0]["fileData"]["videoMetadata"],
                             {"startOffset": "0s", "endOffset": "600s"})

    def test_failed_and_live_videos_wait_behind_normal_videos(self):
        now = dt.datetime(2026, 11, 28, 3, tzinfo=dt.timezone.utc)
        normals = [char * 11 for char in "ABCDE"]
        live_id, failed_id = "L" * 11, "F" * 11
        videos = {
            video_id: {"lengthSeconds": 600, "title": "청약 일정", "published": (now - dt.timedelta(minutes=index)).isoformat()}
            for index, video_id in enumerate(normals)
        }
        videos[live_id] = {"lengthSeconds": 7200, "title": "공모주 라이브",
                           "published": (now - dt.timedelta(minutes=30)).isoformat()}
        videos[failed_id] = {
            "title": "청약 일정",
            "published": (now - dt.timedelta(minutes=5)).isoformat(),
            "attemptedAt": (now - dt.timedelta(hours=1)).isoformat(),
            "failCount": update_insights.MAX_FAILURES,
        }
        with (tempfile.TemporaryDirectory() as folder,
              patch.dict(os.environ, {"GEMINI_API_KEY": "test", "IPO_INSIGHTS_VIDEO_FALLBACK": "true"}),
              patch.object(update_insights, "captions", return_value=""),
              patch.object(update_insights, "summarize_video", side_effect=TimeoutError) as summarize):
            path = Path(folder) / "insights.json"
            path.write_text(json.dumps({"videos": videos, "today": None, "weekly": None}), encoding="utf-8")
            update_insights.update_insights([], now, path)
            attempted = [call.kwargs["video_id"] for call in summarize.call_args_list]
            self.assertEqual(attempted, normals + [live_id])
            saved = json.loads(path.read_text(encoding="utf-8"))["videos"]
            self.assertEqual(saved[failed_id]["attemptedAt"], videos[failed_id]["attemptedAt"])
            self.assertEqual(saved[failed_id]["failCount"], update_insights.MAX_FAILURES)
            self.assertEqual(saved[live_id]["failCount"], 1)

    def test_channel_keywords_keep_only_matching_videos_in_the_insight_feed(self):
        now = dt.datetime(2026, 11, 28, 3, tzinfo=dt.timezone.utc)
        ipo_id, els_id, stale_id, other_id = "A" * 11, "B" * 11, "C" * 11, "D" * 11
        channel = {
            "channelId": "xuenxu", "channelTitle": "재테크의 여왕 슈엔슈",
            "insightKeywords": ["공모주", "청약"],
            "videos": [
                {"videoId": ipo_id, "title": "2026.11.12/ 11월 엠비디 공모주 청약(11.12~13)",
                 "published": (now - dt.timedelta(hours=2)).isoformat()},
                {"videoId": els_id, "title": "2026.11.28/ 11월 마지막주 추천 ELS",
                 "published": (now - dt.timedelta(hours=1)).isoformat()},
            ],
        }
        stale = {stale_id: {"title": "2026.11.28/ 11월 마지막주 추천 ELS", "channelId": "xuenxu",
                            "channelTitle": "재테크의 여왕 슈엔슈",
                            "published": (now - dt.timedelta(hours=3)).isoformat()},
                 other_id: {"title": "공모주 청약 경쟁률", "channelId": "other",
                            "channelTitle": "다른 채널",
                            "published": (now - dt.timedelta(hours=4)).isoformat()}}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "insights.json"
            path.write_text(json.dumps({"videos": stale}), encoding="utf-8")
            with patch.dict(os.environ, {"GEMINI_API_KEY": "", "YOUTUBE_API_KEY": ""}):
                update_insights.update_insights([channel], now, path)
            saved = json.loads(path.read_text(encoding="utf-8"))["videos"]
            self.assertEqual(set(saved), {ipo_id, other_id})
            self.assertEqual(saved[ipo_id]["channelTitle"], "재테크의 여왕 슈엔슈")
