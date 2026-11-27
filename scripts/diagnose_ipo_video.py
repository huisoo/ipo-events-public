import json
import os
import re
import time
import urllib.error
from pathlib import Path
from unittest.mock import patch

import update_insights


def diagnose(key, video_id, video):
    start = time.monotonic()
    try:
        result = update_insights.summarize_video(key, video, video_id=video_id)
        return {"outcome": "summary" if result else "no_grounded_summary", "result": result}
    except (urllib.error.HTTPError, update_insights.GeminiQuotaExceeded) as exc:
        error = exc if isinstance(exc, urllib.error.HTTPError) else exc.__cause__
        try:
            payload = json.load(error).get("error", {})
        except (ValueError, OSError):
            payload = {}
        message = payload.get("message", "")
        reasons = [detail.get("reason", "") for detail in payload.get("details", [])]
        categories = {
            "video fetch": r"fetch|download|retrieve|access.*video",
            "video unavailable": r"private|unavailable|not found",
            "video length": r"duration|too long|length",
            "upstream timeout": r"deadline|timed out|timeout",
            "quota": r"quota|rate limit",
        }
        return {
            "outcome": "http_error",
            "http": error.code,
            "status": payload.get("status") if re.fullmatch(r"[A-Z_]{1,45}", payload.get("status", "")) else None,
            "reasons": [reason for reason in reasons if re.fullmatch(r"[A-Z_]{1,70}", reason)],
            "matched_message_categories": [name for name, pattern in categories.items()
                                           if re.search(pattern, message, re.I)],
        }
    except Exception as exc:
        return {"outcome": type(exc).__name__}
    finally:
        print(f"{video_id} elapsed_seconds={time.monotonic() - start:.1f}", flush=True)


key = os.environ["GEMINI_API_KEY"]
if not key:
    raise SystemExit("GEMINI_API_KEY is missing")
videos = json.loads(Path("insights.json").read_text())["videos"]
urlopen = update_insights.urllib.request.urlopen


def observed_urlopen(*args, **kwargs):
    response = urlopen(*args, **kwargs)
    print(f"HTTP response status={response.status}", flush=True)
    return response


with patch.object(update_insights.urllib.request, "urlopen", side_effect=observed_urlopen):
    for model in ("gemini-2.5-flash", "gemini-2.5-flash-lite"):
        with patch.dict(os.environ, {"IPO_INSIGHTS_MODEL": model}):
            video_id = "pI2F5ooQkrI"
            result = diagnose(key, video_id, videos[video_id])
            print("alternative_result", model, json.dumps(result, ensure_ascii=False), flush=True)
            if result["outcome"] == "summary":
                break
