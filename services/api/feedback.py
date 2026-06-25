"""Feedback endpoint for user ratings on RAG answers."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from shared.db import get_conn
from shared.logging import get_logger

log = get_logger("feedback")
router = APIRouter()


class FeedbackIn(BaseModel):
    conversation_id: str = Field(..., min_length=1, max_length=200)
    message_id: str = Field(..., min_length=1, max_length=200)
    rating: int = Field(..., ge=0, le=1, description="1 = thumbs up, 0 = thumbs down")
    comment: str = Field("", max_length=2000)


@router.post("/v1/feedback")
def submit_feedback(body: FeedbackIn):
    """Record user feedback on an assistant response."""
    with get_conn() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS feedback ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  conversation_id TEXT NOT NULL,"
            "  message_id TEXT NOT NULL,"
            "  rating INTEGER NOT NULL,"
            "  comment TEXT DEFAULT '',"
            "  created_at TEXT NOT NULL DEFAULT (datetime('now'))"
            ")"
        )
        conn.execute(
            "INSERT INTO feedback (conversation_id, message_id, rating, comment) VALUES (?, ?, ?, ?)",
            (body.conversation_id, body.message_id, body.rating, body.comment),
        )
    log.info("feedback_recorded", rating=body.rating, message_id=body.message_id)
    return {"ok": True}
