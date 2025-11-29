from pydantic import BaseModel, HttpUrl, Field
from typing import Any, Optional, Literal


class IngestRequest(BaseModel):
    url: Optional[HttpUrl] = None
    name: Optional[str] = None
    force: Optional[bool] = False


class IngestResponse(BaseModel):
    tool_id: str
    status: str


class ChatRequest(BaseModel):
    tool_id: Optional[str] = None
    question: str = Field(min_length=3)
    # When 'global', retrieve across all tools; default 'tool' restricts to tool_id scope
    scope: Literal['tool', 'global'] = 'tool'
    # Prefer one_pager structured context and reduce external RAG load
    prefer_one_pager: bool = False
    # Optional hard cap on number of retrieved snippets to include in context/citations
    rag_limit: Optional[int] = None


class Citation(BaseModel):
    source_url: str
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]


class OnePager(BaseModel):
    # Minimal flexible structure for MVP; concrete shape evolves
    overview: str
    features: list[str] = []
    pricing: dict[str, Any] = {}
    tech_stack: list[str] = []
    last_updated: str


class ToolInfo(BaseModel):
    id: str
    name: str
    canonical_url: str | None = None
    status: str
    one_pager: dict[str, Any]
    documents: int
    updates: int
    sources: list[str] = []
    media_items: list[dict[str, Any]] = []
    media: list[dict[str, Any]] = []

