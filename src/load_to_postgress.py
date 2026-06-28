"""
Load raw JSON data from the data lake into PostgreSQL.
Creates a raw.telegram_messages table with all scraped fields.

Usage:
    docker compose up -d
    python src/load_to_postgres.py --path data
"""

import os, json, glob, argparse, logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

logger = logging.getLogger("load_to_postgres")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "5432")
DB_NAME     = os.getenv("DB_NAME", "telegram_warehouse")
DB_USER     = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_engine():
    return create_engine(DATABASE_URL)


def create_raw_table(engine):
    """Creates the raw schema and telegram_messages table, truncating if it already exists."""
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS raw.telegram_messages (
                message_id    INTEGER,
                channel_name  TEXT,
                channel_title TEXT,
                message_date  TEXT,
                message_text  TEXT,
                has_media     BOOLEAN,
                image_path    TEXT,
                views         INTEGER,
                forwards      INTEGER
            )
        """))
        conn.execute(text("TRUNCATE TABLE raw.telegram_messages"))
        conn.commit()
    logger.info("raw.telegram_messages ready")


def load_json_files(engine, data_path: str):
    """Reads all channel JSON files from the data lake and inserts into raw.telegram_messages."""
    pattern = os.path.join(data_path, "raw", "telegram_messages", "*", "*.json")
    json_files = [f for f in glob.glob(pattern) if not f.endswith("_manifest.json")]

    total = 0
    with engine.connect() as conn:
        for filepath in sorted(json_files):
            with open(filepath, "r", encoding="utf-8") as f:
                messages = json.load(f)

            for msg in messages:
                conn.execute(
                    text("""
                        INSERT INTO raw.telegram_messages
                            (message_id, channel_name, channel_title, message_date,
                             message_text, has_media, image_path, views, forwards)
                        VALUES
                            (:message_id, :channel_name, :channel_title, :message_date,
                             :message_text, :has_media, :image_path, :views, :forwards)
                    """),
                    {
                        "message_id":    msg["message_id"],
                        "channel_name":  msg["channel_name"],
                        "channel_title": msg.get("channel_title", ""),
                        "message_date":  msg["message_date"],
                        "message_text":  msg.get("message_text", ""),
                        "has_media":     msg.get("has_media", False),
                        "image_path":    msg.get("image_path"),
                        "views":         msg.get("views", 0),
                        "forwards":      msg.get("forwards", 0),
                    },
                )
            total += len(messages)
            logger.info(f"Loaded {len(messages)} messages from {os.path.basename(filepath)}")

        conn.commit()
    logger.info(f"Total loaded: {total} messages")
    return total


def load_yolo_results(engine, csv_path: str = "data/yolo_results.csv"):
    """Loads YOLO detection results into raw.yolo_detections (Task 3, skipped if file missing)."""
    if not os.path.exists(csv_path):
        logger.info(f"No YOLO results found at {csv_path} — skipping")
        return

    import csv
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS raw.yolo_detections (
                image_path     TEXT,
                message_id     INTEGER,
                channel_name   TEXT,
                detected_class TEXT,
                confidence     REAL,
                image_category TEXT
            )
        """))
        conn.execute(text("TRUNCATE TABLE raw.yolo_detections"))

        with open(csv_path, "r") as f:
            for row in csv.DictReader(f):
                conn.execute(
                    text("""
                        INSERT INTO raw.yolo_detections
                            (image_path, message_id, channel_name, detected_class,
                             confidence, image_category)
                        VALUES
                            (:image_path, :message_id, :channel_name, :detected_class,
                             :confidence, :image_category)
                    """),
                    {
                        "image_path":     row["image_path"],
                        "message_id":     int(row["message_id"]),
                        "channel_name":   row["channel_name"],
                        "detected_class": row["detected_class"],
                        "confidence":     float(row["confidence"]),
                        "image_category": row["image_category"],
                    },
                )
        conn.commit()
    logger.info(f"YOLO results loaded from {csv_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load data lake JSON into PostgreSQL")
    parser.add_argument("--path", type=str, default="data")
    args = parser.parse_args()

    engine = get_engine()
    create_raw_table(engine)
    load_json_files(engine, args.path)
    load_yolo_results(engine)