thonimport logging
import re
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)

logger = logging.getLogger(__name__)

def get_video_id_from_url(url: str) -> Optional[str]:
    """
    Extract a YouTube video id from a variety of URL formats.

    Supports:
      - https://www.youtube.com/watch?v=VIDEO_ID
      - https://youtu.be/VIDEO_ID
      - https://www.youtube.com/embed/VIDEO_ID
      - https://www.youtube.com/shorts/VIDEO_ID
      - Raw 11-character ids (if passed directly).
    """
    # Raw ID
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url

    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()

    # youtu.be short links
    if hostname in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.lstrip("/")
        if video_id:
            return video_id

    # Standard YouTube domains
    if "youtube.com" in hostname or "youtube-nocookie.com" in hostname:
        qs = parse_qs(parsed.query)
        if "v" in qs and qs["v"]:
            return qs["v"][0]

        # Handle /embed/VIDEO_ID or /shorts/VIDEO_ID paths
        match = re.search(r"/(embed|shorts)/([^/?]+)", parsed.path)
        if match:
            return match.group(2)

    logger.error("Unable to extract video id from url: %s", url)
    return None

def fetch_transcript(
    video_id: str, languages: Optional[List[str]] = None
) -> Optional[List[Dict[str, str]]]:
    """
    Fetch the transcript segments for a given video id.

    Returns a list of segments, or None if no transcript is available.
    """
    try:
        if languages:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        else:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return transcript
    except (TranscriptsDisabled, NoTranscriptFound) as exc:
        logger.warning("Transcript not available for %s: %s", video_id, exc)
        return None
    except Exception as exc:
        logger.error("Unexpected error while fetching transcript for %s: %s", video_id, exc)
        return None

def transcript_to_text(transcript: List[Dict[str, str]]) -> str:
    """
    Convert raw transcript segments into a single text blob.
    """
    parts: List[str] = []
    for item in transcript:
        text = (item.get("text") or "").strip()
        if text:
            parts.append(text)
    return " ".join(parts)

def fetch_transcript_text(
    video_id: str, languages: Optional[List[str]] = None
) -> Optional[str]:
    """
    Convenience wrapper around fetch_transcript + transcript_to_text.
    """
    segments = fetch_transcript(video_id, languages)
    if not segments:
        return None
    return transcript_to_text(segments)