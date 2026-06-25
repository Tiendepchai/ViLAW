from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Document:
    id: str
    chu_de: str = ""
    de_muc: str = ""
    so_dieu: str = ""
    tieu_de_dieu: str = ""
    noi_dung: str = ""
    nguon: str = ""
    path_goc: str = ""


@dataclass
class Chunk:
    doc_id: str
    chunk_index: int
    text: str
    chunk_hash: str
    id: Optional[int] = None
    faiss_id: Optional[int] = None


@dataclass
class Conversation:
    id: str
    title: str = "New chat"
    created_at: int = 0
    updated_at: int = 0
    messages: list = field(default_factory=list)


@dataclass
class Message:
    id: str
    conversation_id: str
    role: str  # "user" | "assistant"
    content: str
    citations: str = "[]"
    created_at: int = 0
