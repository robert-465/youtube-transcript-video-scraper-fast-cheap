thonimport logging
from typing import Any, Dict

from pytube import YouTube

class YouTubeMetadataExtractor:
    """
    Lightweight wrapper around pytube to fetch metadata for a YouTube video.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_video_metadata(self, url: str) -> Dict[str, Any]:
        """
        Fetch the title and view count for a YouTube video.

        Returns a dictionary:
        {
            "title": str | None,
            "views": str | None,  # formatted, e.g. "1,234 views"
            "target_url": str,
        }
        """
        try:
            yt = YouTube(url)
            title = yt.title or ""
            views = yt.views if yt.views is not None else 0
            formatted_views = f"{views:,} views"
            return {
                "title": title,
                "views": formatted_views,
                "target_url": url,
            }
        except Exception as exc:
            # Keep going even if metadata is not available
            self.logger.error(
                "Failed to fetch metadata for %s: %s", url, exc, exc_info=False
            )
            return {
                "title": None,
                "views": None,
                "target_url": url,
            }