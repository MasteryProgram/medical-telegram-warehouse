from typing import List
from pydantic import BaseModel, Field


class TopProductItem(BaseModel):
    term: str = Field(..., description="Extracted product or topic term")
    count: int = Field(..., description="Number of mentions")


class TopProductsResponse(BaseModel):
    items: List[TopProductItem]


class ChannelActivityItem(BaseModel):
    date: str
    posts: int
    avg_views: float


class ChannelActivityResponse(BaseModel):
    channel_name: str
    items: List[ChannelActivityItem]


class MessageSearchItem(BaseModel):
    message_id: int
    channel_name: str
    message_date: str
    message_text: str
    views: int


class MessageSearchResponse(BaseModel):
    query: str
    items: List[MessageSearchItem]


class VisualContentItem(BaseModel):
    channel_name: str
    total_posts: int
    posts_with_images: int
    image_share_pct: float


class VisualContentResponse(BaseModel):
    items: List[VisualContentItem]
