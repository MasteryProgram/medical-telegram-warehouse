"""
Data Lake Utilities
===================
Handles all file I/O for the raw data lake layer.

Directory layout:
    data/raw/telegram_messages/YYYY-MM-DD/{channel_name}.json
    data/raw/telegram_messages/YYYY-MM-DD/_manifest.json
    data/raw/images/{channel_name}/{message_id}.jpg
    data/raw/csv/YYYY-MM-DD/telegram_data.csv
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def telegram_messages_partition_dir(base_path: str, date_str: str) -> str:
    return os.path.join(base_path, "raw", "telegram_messages", date_str)


def telegram_images_dir(base_path: str) -> str:
    return os.path.join(base_path, "raw", "images")


def channel_messages_json_path(base_path: str, date_str: str, channel_name: str) -> str:
    partition_dir = telegram_messages_partition_dir(base_path, date_str)
    ensure_dir(partition_dir)
    return os.path.join(partition_dir, f"{channel_name}.json")


def write_channel_messages_json(
    *, base_path: str, date_str: str, channel_name: str, messages: List[Dict[str, Any]],
) -> str:
    out_path = channel_messages_json_path(base_path, date_str, channel_name)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
    return out_path


def manifest_path(base_path: str, date_str: str) -> str:
    partition_dir = telegram_messages_partition_dir(base_path, date_str)
    ensure_dir(partition_dir)
    return os.path.join(partition_dir, "_manifest.json")


def write_manifest(
    *, base_path: str, date_str: str, channel_message_counts: Dict[str, int],
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    payload: Dict[str, Any] = {
        "date": date_str,
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "channels": channel_message_counts,
        "total_messages": sum(channel_message_counts.values()),
    }
    if extra:
        payload.update(extra)
    out_path = manifest_path(base_path, date_str)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_path


def read_channel_messages_json(base_path: str, date_str: str, channel_name: str) -> List[Dict[str, Any]]:
    path = channel_messages_json_path(base_path, date_str, channel_name)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_manifest(base_path: str, date_str: str) -> Optional[Dict[str, Any]]:
    path = manifest_path(base_path, date_str)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_available_dates(base_path: str) -> List[str]:
    root = os.path.join(base_path, "raw", "telegram_messages")
    if not os.path.exists(root):
        return []
    dates = [
        d for d in os.listdir(root)
        if os.path.isdir(os.path.join(root, d)) and not d.startswith("_")
    ]
    return sorted(dates)