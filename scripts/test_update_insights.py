"""Run with python -m unittest discover -s scripts -p test_update_insights.py."""
import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import update_insights


class InsightTest(unittest.TestCase):
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
              patch.dict(os.environ, {"OPENAI_API_KEY": "test"}),
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
