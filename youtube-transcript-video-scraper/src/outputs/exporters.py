thonimport csv
import json
import logging
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Dict, Iterable, List

from xml.etree.ElementTree import Element, SubElement, ElementTree

logger = logging.getLogger(__name__)

def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

def _normalize_records(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [dict(record) for record in records]

def export_to_json(records: Iterable[Dict[str, Any]], output_file: Path) -> None:
    _ensure_parent_dir(output_file)
    data = _normalize_records(records)
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("JSON export complete: %s", output_file)

def export_to_csv(records: Iterable[Dict[str, Any]], output_file: Path) -> None:
    _ensure_parent_dir(output_file)
    data = _normalize_records(records)

    # Collect all unique keys across all records
    fieldnames: List[str] = []
    for item in data:
        for key in item.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    if not fieldnames:
        logger.warning("No fields found; CSV export skipped.")
        return

    with output_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in data:
            writer.writerow(item)

    logger.info("CSV export complete: %s", output_file)

def export_to_xml(
    records: Iterable[Dict[str, Any]],
    output_file: Path,
    root_tag: str = "videos",
    item_tag: str = "video",
) -> None:
    _ensure_parent_dir(output_file)
    data = _normalize_records(records)

    root = Element(root_tag)
    for record in data:
        item_elem = SubElement(root, item_tag)
        for key, value in record.items():
            child = SubElement(item_elem, key)
            if value is None:
                child.text = ""
            else:
                child.text = str(value)

    tree = ElementTree(root)
    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    logger.info("XML export complete: %s", output_file)

def export_to_html_table(
    records: Iterable[Dict[str, Any]],
    output_file: Path,
    title: str = "YouTube Transcript Export",
) -> None:
    _ensure_parent_dir(output_file)
    data = _normalize_records(records)

    # Determine table columns
    columns: List[str] = []
    for item in data:
        for key in item.keys():
            if key not in columns:
                columns.append(key)

    html_parts: List[str] = []
    html_parts.append("<!DOCTYPE html>")
    html_parts.append("<html lang=\"en\">")
    html_parts.append("<head>")
    html_parts.append("<meta charset=\"UTF-8\" />")
    html_parts.append(f"<title>{escape(title)}</title>")
    html_parts.append(
        "<style>"
        "body { font-family: Arial, sans-serif; padding: 16px; }"
        "table { border-collapse: collapse; width: 100%; }"
        "th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top; }"
        "th { background-color: #f5f5f5; text-align: left; }"
        "tr:nth-child(even) { background-color: #fbfbfb; }"
        "</style>"
    )
    html_parts.append("</head>")
    html_parts.append("<body>")
    html_parts.append(f"<h1>{escape(title)}</h1>")

    generated_ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    html_parts.append(f"<p>Generated at: {escape(generated_ts)}</p>")

    if not columns:
        html_parts.append("<p>No data to display.</p>")
    else:
        html_parts.append("<table>")
        html_parts.append("<thead><tr>")
        for col in columns:
            html_parts.append(f"<th>{escape(col)}</th>")
        html_parts.append("</tr></thead>")
        html_parts.append("<tbody>")
        for item in data:
            html_parts.append("<tr>")
            for col in columns:
                value = item.get(col, "")
                text = "" if value is None else str(value)
                html_parts.append(f"<td>{escape(text)}</td>")
            html_parts.append("</tr>")
        html_parts.append("</tbody></table>")

    html_parts.append("</body></html>")

    with output_file.open("w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))

    logger.info("HTML table export complete: %s", output_file)

def export_to_rss(
    records: Iterable[Dict[str, Any]],
    output_file: Path,
    channel_title: str,
    channel_link: str,
    channel_description: str,
) -> None:
    _ensure_parent_dir(output_file)
    data = _normalize_records(records)

    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")

    title_elem = SubElement(channel, "title")
    title_elem.text = channel_title

    link_elem = SubElement(channel, "link")
    link_elem.text = channel_link

    desc_elem = SubElement(channel, "description")
    desc_elem.text = channel_description

    pub_date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    pub_elem = SubElement(channel, "pubDate")
    pub_elem.text = pub_date

    for record in data:
        item = SubElement(channel, "item")
        title_text = str(record.get("title") or "Untitled video")
        link_text = str(record.get("target_url") or "")
        description_parts: List[str] = []

        views = record.get("views")
        if views:
            description_parts.append(f"Views: {views}")

        transcript = record.get("transcript")
        if transcript:
            # Keep RSS description lightweight
            snippet = str(transcript)
            if len(snippet) > 500:
                snippet = snippet[:497] + "..."
            description_parts.append(f"Transcript snippet: {snippet}")

        title_elem = SubElement(item, "title")
        title_elem.text = title_text

        link_elem = SubElement(item, "link")
        link_elem.text = link_text

        desc_elem = SubElement(item, "description")
        desc_elem.text = " | ".join(description_parts) if description_parts else ""

        guid = SubElement(item, "guid")
        guid.text = link_text or title_text

    tree = ElementTree(rss)
    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    logger.info("RSS export complete: %s", output_file)