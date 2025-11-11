thonimport argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Make sure local "src" modules can be imported when running this file directly
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from extractors.youtube_parser import YouTubeMetadataExtractor
from extractors.transcript_utils import (
    get_video_id_from_url,
    fetch_transcript_text,
)
from outputs.exporters import (
    export_to_json,
    export_to_csv,
    export_to_xml,
    export_to_html_table,
    export_to_rss,
)

def configure_logging(level_str: str) -> None:
    level = getattr(logging, level_str.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

def get_project_root() -> Path:
    # src/runner.py -> project root is parent of src
    return Path(__file__).resolve().parent.parent

def load_settings(config_path: Optional[str] = None) -> Dict[str, Any]:
    root = get_project_root()

    if config_path:
        cfg_path = Path(config_path)
        if not cfg_path.is_absolute():
            cfg_path = root / cfg_path
        if not cfg_path.exists():
            raise FileNotFoundError(f"Config file not found at {cfg_path}")
        with cfg_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    # Default discovery: prefer settings.json, else fall back to settings.example.json
    config_dir = CURRENT_DIR / "config"
    candidates = [
        config_dir / "settings.json",
        config_dir / "settings.example.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            with candidate.open("r", encoding="utf-8") as f:
                return json.load(f)

    raise FileNotFoundError(
        "No settings.json or settings.example.json found in src/config/"
    )

def load_input_urls(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Input URL file not found at {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    urls: List[str] = []

    def add_url_from_item(item: Any) -> None:
        if isinstance(item, str):
            urls.append(item)
        elif isinstance(item, dict):
            for key in ("target_url", "url", "video_url"):
                if key in item and isinstance(item[key], str):
                    urls.append(item[key])
                    return

    if isinstance(data, list):
        for item in data:
            add_url_from_item(item)
    elif isinstance(data, dict):
        if "urls" in data and isinstance(data["urls"], list):
            for item in data["urls"]:
                add_url_from_item(item)

    return urls

def process_videos(
    urls: List[str],
    transcript_languages: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    extractor = YouTubeMetadataExtractor()
    records: List[Dict[str, Any]] = []

    for url in urls:
        logging.info("Processing URL: %s", url)
        video_id = get_video_id_from_url(url)
        if not video_id:
            logging.error("Skipping URL with unresolvable video id: %s", url)
            continue

        metadata = extractor.get_video_metadata(url)
        transcript_text = fetch_transcript_text(video_id, transcript_languages)

        record = {
            "title": metadata.get("title"),
            "views": metadata.get("views"),
            "target_url": metadata.get("target_url"),
            "transcript": transcript_text,
        }
        records.append(record)

    return records

def export_results(
    records: List[Dict[str, Any]],
    output_dir: Path,
    base_name: str,
    formats: List[str],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    formats = [f.lower() for f in formats]

    for fmt in formats:
        if fmt == "json":
            out_path = output_dir / f"{base_name}.json"
            export_to_json(records, out_path)
        elif fmt == "csv":
            out_path = output_dir / f"{base_name}.csv"
            export_to_csv(records, out_path)
        elif fmt == "xml":
            out_path = output_dir / f"{base_name}.xml"
            export_to_xml(records, out_path)
        elif fmt in ("html", "html_table"):
            out_path = output_dir / f"{base_name}.html"
            export_to_html_table(
                records,
                out_path,
                title="YouTube Transcript Export",
            )
        elif fmt == "rss":
            out_path = output_dir / f"{base_name}.rss"
            export_to_rss(
                records,
                out_path,
                channel_title="YouTube Transcript Export",
                channel_link="https://www.youtube.com",
                channel_description="Transcripts scraped from YouTube videos.",
            )
        else:
            logging.error("Unknown output format '%s', skipping.", fmt)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="YouTube Transcript Video Scraper (Fast & Cheap)"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to a custom JSON config file.",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Override the input JSON file with YouTube URLs.",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        help="Override output formats (e.g. json csv xml html rss).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Override output directory path.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Process only the first N URLs from the input file.",
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    settings = load_settings(args.config)

    log_level = settings.get("log_level", "INFO")
    configure_logging(log_level)

    root = get_project_root()

    input_file_setting = settings.get("input_file", "data/input_urls.sample.json")
    if args.input:
        input_file_setting = args.input

    input_path = Path(input_file_setting)
    if not input_path.is_absolute():
        input_path = root / input_path

    output_dir_setting = settings.get("output_dir", "data")
    if args.output_dir:
        output_dir_setting = args.output_dir

    output_dir = Path(output_dir_setting)
    if not output_dir.is_absolute():
        output_dir = root / output_dir

    base_name = settings.get("output_base_name", "youtube_transcripts")

    formats_setting = settings.get("output_formats", ["json"])
    if isinstance(formats_setting, str):
        formats_setting = [formats_setting]
    if args.formats:
        formats_setting = args.formats

    transcript_languages = settings.get("transcript_languages")
    if isinstance(transcript_languages, str):
        transcript_languages = [transcript_languages]

    urls = load_input_urls(input_path)
    if args.limit is not None and args.limit > 0:
        urls = urls[: args.limit]

    if not urls:
        logging.error("No URLs found in input file %s", input_path)
        sys.exit(1)

    logging.info("Loaded %d URL(s) from %s", len(urls), input_path)

    records = process_videos(urls, transcript_languages)

    if not records:
        logging.error("No records to export – scraping produced no results.")
        sys.exit(1)

    export_results(records, output_dir, base_name, formats_setting)

    logging.info("Done. Exported %d record(s).", len(records))

if __name__ == "__main__":
    main()