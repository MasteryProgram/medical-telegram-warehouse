import re
from typing import List

from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import text

from api.database import get_engine
from api.schemas import (
    ChannelActivityItem,
    ChannelActivityResponse,
    MessageSearchItem,
    MessageSearchResponse,
    TopProductItem,
    TopProductsResponse,
    VisualContentItem,
    VisualContentResponse,
)

app = FastAPI(title="Medical Telegram Warehouse API", version="1.0.0")

STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "have",
    "been",
    "into",
    "your",
    "our",
    "now",
    "via",
    "dm",
    "are",
    "will",
    "all",
    "not",
    "but",
    "you",
    "our",
    "can",
    "new",
    "stock",
    "available",
    "order",
    "call",
    "contact",
    "buy",
    "sale",
}


def _extract_terms(message_text: str) -> List[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+/.-]*", message_text.lower())
    return [token for token in tokens if len(token) > 2 and token not in STOP_WORDS]


@app.get("/", summary="API health check")
def read_root() -> dict:
    return {"status": "ok", "message": "Medical Telegram Warehouse API is running"}


@app.get("/api/reports/top-products", response_model=TopProductsResponse, summary="Top mentioned terms")
def top_products(limit: int = Query(default=10, ge=1, le=50)) -> TopProductsResponse:
    with get_engine().connect() as connection:
        result = connection.execute(text("SELECT message_text FROM fct_messages"))

    counts: dict[str, int] = {}
    for row in result:
        for term in _extract_terms(row[0] or ""):
            counts[term] = counts.get(term, 0) + 1

    items = [TopProductItem(term=term, count=count) for term, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit]]
    return TopProductsResponse(items=items)


@app.get("/api/channels/{channel_name}/activity", response_model=ChannelActivityResponse, summary="Channel posting activity")
def channel_activity(channel_name: str) -> ChannelActivityResponse:
    with get_engine().connect() as connection:
        result = connection.execute(
            text(
                """
                SELECT d.full_date AS date, COUNT(*) AS posts, AVG(f.views) AS avg_views
                FROM fct_messages f
                JOIN dim_channels c ON f.channel_key = c.channel_key
                JOIN dim_dates d ON f.date_key = d.date_key
                WHERE c.channel_name = :channel_name
                GROUP BY d.full_date
                ORDER BY d.full_date
                """
            ),
            {"channel_name": channel_name},
        )

    items = [ChannelActivityItem(date=row[0].strftime("%Y-%m-%d") if hasattr(row[0], "strftime") else str(row[0]), posts=int(row[1]), avg_views=float(row[2] or 0.0)) for row in result]
    return ChannelActivityResponse(channel_name=channel_name, items=items)


@app.get("/api/search/messages", response_model=MessageSearchResponse, summary="Search messages by keyword")
def search_messages(query: str = Query(..., min_length=2), limit: int = Query(default=20, ge=1, le=100)) -> MessageSearchResponse:
    pattern = f"%{query}%"
    with get_engine().connect() as connection:
        result = connection.execute(
            text(
                """
                SELECT f.message_id, c.channel_name, d.full_date AS message_date, f.message_text, f.views
                FROM fct_messages f
                JOIN dim_channels c ON f.channel_key = c.channel_key
                JOIN dim_dates d ON f.date_key = d.date_key
                WHERE f.message_text ILIKE :pattern
                ORDER BY f.message_id
                LIMIT :limit
                """
            ),
            {"pattern": pattern, "limit": limit},
        )

    items = [MessageSearchItem(message_id=int(row[0]), channel_name=row[1], message_date=row[2].strftime("%Y-%m-%d") if hasattr(row[2], "strftime") else str(row[2]), message_text=row[3] or "", views=int(row[4] or 0)) for row in result]
    return MessageSearchResponse(query=query, items=items)


@app.get("/api/reports/visual-content", response_model=VisualContentResponse, summary="Visual content usage by channel")
def visual_content() -> VisualContentResponse:
    with get_engine().connect() as connection:
        result = connection.execute(
            text(
                """
                SELECT c.channel_name, COUNT(*) AS total_posts,
                       SUM(CASE WHEN f.has_image THEN 1 ELSE 0 END) AS posts_with_images,
                       ROUND(AVG(CASE WHEN f.has_image THEN 1.0 ELSE 0.0 END) * 100, 2) AS image_share_pct
                FROM fct_messages f
                JOIN dim_channels c ON f.channel_key = c.channel_key
                GROUP BY c.channel_name
                ORDER BY c.channel_name
                """
            )
        )

    items = [VisualContentItem(channel_name=row[0], total_posts=int(row[1]), posts_with_images=int(row[2] or 0), image_share_pct=float(row[3] or 0.0)) for row in result]
    return VisualContentResponse(items=items)
