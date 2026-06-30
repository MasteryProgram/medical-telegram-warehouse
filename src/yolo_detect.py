"""Run YOLO-based image enrichment for Telegram messages.

This script scans downloaded images under data/raw/images, runs object detection
when the ultralytics package is available, and writes a CSV file with the
results. If the model dependency is unavailable, it falls back to a lightweight
placeholder classifier so the pipeline can still produce a structured output.
"""

import argparse
import csv
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE_ROOT = PROJECT_ROOT / "data" / "raw" / "images"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "yolo_results.csv"

try:
    from ultralytics import YOLO
except ImportError:  # pragma: no cover - runtime dependency may be missing
    YOLO = None


def _classify_image(detected_classes: List[str]) -> str:
    lowered = [c.lower() for c in detected_classes]
    has_person = any(name in lowered for name in {"person", "people", "man", "woman"})
    has_product = any(
        name in lowered
        for name in {
            "bottle",
            "bottles",
            "container",
            "box",
            "pack",
            "tablet",
            "pill",
            "cream",
            "tube",
            "syringe",
            "medicine",
            "capsule",
        }
    )

    if has_person and has_product:
        return "promotional"
    if has_product and not has_person:
        return "product_display"
    if has_person and not has_product:
        return "lifestyle"
    return "other"


def _parse_message_id(path: Path) -> int:
    try:
        return int(path.stem)
    except ValueError:
        return 0


def _iter_image_files(image_root: Path) -> List[Path]:
    if not image_root.exists():
        return []
    return sorted(image_root.rglob("*.jpg")) + sorted(image_root.rglob("*.jpeg")) + sorted(image_root.rglob("*.png"))


def run_detection(image_root: Path, output_path: Path, model_name: str = "yolov8n.pt") -> List[Dict[str, object]]:
    image_files = _iter_image_files(image_root)
    rows: List[Dict[str, object]] = []

    if not image_files:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["image_path", "message_id", "channel_name", "detected_class", "confidence", "image_category"])
            writer.writeheader()
        return rows

    if YOLO is not None:
        model = YOLO(model_name)
        for image_path in image_files:
            prediction = model(str(image_path), stream=False, conf=0.25)[0]
            detected_classes = []
            for box in prediction.boxes:
                label = prediction.names[int(box.cls[0])]
                confidence = float(box.conf[0])
                detected_classes.append(label)
                rows.append(
                    {
                        "image_path": str(image_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                        "message_id": _parse_message_id(image_path),
                        "channel_name": image_path.parent.name,
                        "detected_class": label,
                        "confidence": round(confidence, 3),
                        "image_category": _classify_image([label]),
                    }
                )

            if not detected_classes:
                rows.append(
                    {
                        "image_path": str(image_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                        "message_id": _parse_message_id(image_path),
                        "channel_name": image_path.parent.name,
                        "detected_class": "none",
                        "confidence": 0.0,
                        "image_category": "other",
                    }
                )
    else:
        for image_path in image_files:
            rows.append(
                {
                    "image_path": str(image_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "message_id": _parse_message_id(image_path),
                    "channel_name": image_path.parent.name,
                    "detected_class": "placeholder",
                    "confidence": 0.0,
                    "image_category": "other",
                }
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["image_path", "message_id", "channel_name", "detected_class", "confidence", "image_category"])
        writer.writeheader()
        writer.writerows(rows)

    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run YOLO-based image enrichment")
    parser.add_argument("--path", type=str, default="data", help="Project data directory")
    parser.add_argument("--output", type=str, default="data/yolo_results.csv", help="Path to the CSV output")
    args = parser.parse_args()

    data_root = Path(args.path)
    image_root = data_root / "raw" / "images"
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    run_detection(image_root, output_path)
    print(f"Wrote {output_path}")
