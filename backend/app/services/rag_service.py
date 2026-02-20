"""
RAG service for denial codes and payer policies.
Uses Chroma + OpenAI embeddings for semantic search.
Optional: app runs without langchain_community; RAG is no-op if not installed.
"""

from pathlib import Path
from typing import Optional, Any

from ..core.config import get_settings

# Lazy imports so app starts when langchain_community/chromadb not installed
def _import_chroma() -> Any:
    try:
        from langchain_community.vectorstores import Chroma
        return Chroma
    except ImportError:
        return None

def _import_document() -> Any:
    try:
        from langchain_core.documents import Document
        return Document
    except ImportError:
        return None

def _get_embeddings_inner():
    try:
        from langchain_openai import OpenAIEmbeddings
        s = get_settings()
        if not s.OPENAI_API_KEY:
            return None
        return OpenAIEmbeddings(api_key=s.OPENAI_API_KEY, model="text-embedding-3-small")
    except ImportError:
        return None

# Default persist dir under backend (override via env if needed)
DEFAULT_CHROMA_DIR = Path(__file__).resolve().parent.parent.parent / "chroma_data"
DENIAL_CODES_COLLECTION = "denial_codes"
PAYER_POLICIES_COLLECTION = "payer_policies"


def _get_embeddings():
    return _get_embeddings_inner()


def _chroma_persist_dir() -> Path:
    # Allow override via env; Chroma uses CHROMA_PERSIST_DIR or similar in some setups
    return DEFAULT_CHROMA_DIR


def get_denial_codes_store():
    """Get or create Chroma vector store for denial codes. Returns None if RAG deps not installed."""
    Chroma = _import_chroma()
    if not Chroma:
        return None
    emb = _get_embeddings()
    if not emb:
        return None
    persist_dir = str(_chroma_persist_dir() / DENIAL_CODES_COLLECTION)
    return Chroma(
        collection_name=DENIAL_CODES_COLLECTION,
        embedding_function=emb,
        persist_directory=persist_dir,
    )


def get_payer_policies_store():
    """Get or create Chroma vector store for payer policies. Returns None if RAG deps not installed."""
    Chroma = _import_chroma()
    if not Chroma:
        return None
    emb = _get_embeddings()
    if not emb:
        return None
    persist_dir = str(_chroma_persist_dir() / PAYER_POLICIES_COLLECTION)
    return Chroma(
        collection_name=PAYER_POLICIES_COLLECTION,
        embedding_function=emb,
        persist_directory=persist_dir,
    )


def add_denial_codes(entries: list[dict]) -> int:
    """
    Ingest denial code entries into the vector store.
    Each entry can have: code, description, remedy (optional), payer (optional).
    Returns number of documents added.
    """
    store = get_denial_codes_store()
    if not store:
        return 0
    Document = _import_document()
    if not Document:
        return 0
    docs = []
    for i, e in enumerate(entries):
        code = e.get("code") or e.get("denial_code") or ""
        desc = e.get("description") or e.get("reason") or ""
        remedy = e.get("remedy") or ""
        payer = e.get("payer") or ""
        text = f"Code: {code}. Description: {desc}. Remedy: {remedy}. Payer: {payer}".strip()
        meta = {"code": code, "source": "denial_codes"}
        docs.append(Document(page_content=text, metadata=meta))
    if not docs:
        return 0
    store.add_documents(docs)
    return len(docs)


def add_payer_policies(entries: list[dict]) -> int:
    """
    Ingest payer policy text into the vector store.
    Each entry: payer_name (optional), text (required), source (optional).
    Returns number of documents added.
    """
    store = get_payer_policies_store()
    if not store:
        return 0
    Document = _import_document()
    if not Document:
        return 0
    docs = []
    for e in entries:
        text = e.get("text") or (e.get("content") or "")
        if not text.strip():
            continue
        payer = e.get("payer_name") or e.get("payer") or ""
        meta = {"payer_name": payer, "source": "payer_policies"}
        docs.append(Document(page_content=text, metadata=meta))
    if not docs:
        return 0
    store.add_documents(docs)
    return len(docs)


def query_denial_codes(query: str, k: int = 5) -> list[str]:
    """Return top-k relevant denial code snippets for the query (code or free text)."""
    store = get_denial_codes_store()
    if not store or not query.strip():
        return []
    try:
        docs = store.similarity_search(query.strip(), k=k)
        return [d.page_content for d in docs]
    except Exception:
        return []


def query_payer_policies(query: str, payer_name: Optional[str] = None, k: int = 5) -> list[str]:
    """Return top-k relevant payer policy snippets. Optionally filter by payer_name in metadata."""
    store = get_payer_policies_store()
    if not store or not query.strip():
        return []
    try:
        if payer_name and payer_name.strip():
            # Filter by metadata after search (Chroma supports where)
            docs = store.similarity_search(
                query.strip(),
                k=k * 2,
                filter={"payer_name": payer_name.strip()},
            )
        else:
            docs = store.similarity_search(query.strip(), k=k)
        return [d.page_content for d in docs[:k]]
    except Exception:
        try:
            docs = store.similarity_search(query.strip(), k=k)
            return [d.page_content for d in docs]
        except Exception:
            return []
