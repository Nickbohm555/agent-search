import os
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass(frozen=True)
class ChunkingConfig:
    """Runtime config for deterministic LangChain chunk splitting.

    Called by `split_text` and loaded from environment by
    `load_chunking_config` so load ingestion can tune chunk size/overlap
    without code changes.
    """

    chunk_size: int = 1500
    chunk_overlap: int = 200
    separators: tuple[str, ...] = ("\n\n", "\n", ". ", " ", "")


def _positive_int(value: str, default: int) -> int:
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def load_chunking_config() -> ChunkingConfig:
    """Return env-driven chunking config for document ingestion.

    Called by `split_text`, which is used by
    `services/internal_data_service.py::_persist_documents`.
    """

    chunk_size = _positive_int(os.getenv("INTERNAL_DATA_CHUNK_SIZE", "1500"), 1500)
    chunk_overlap_raw = os.getenv("INTERNAL_DATA_CHUNK_OVERLAP", "200")
    chunk_overlap = _positive_int(chunk_overlap_raw, 200)
    chunk_overlap = min(chunk_overlap, chunk_size - 1)

    return ChunkingConfig(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def split_text(text: str, config: ChunkingConfig | None = None) -> list[str]:
    """Split one document into ordered LangChain chunks.

    Called by internal-data load persistence to produce embedding-ready chunks
    for both inline and wiki source documents. Returns an empty list for empty
    text so caller can decide fallback behavior.
    """

    if not text or not text.strip():
        return []

    resolved_config = config or load_chunking_config()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=resolved_config.chunk_size,
        chunk_overlap=resolved_config.chunk_overlap,
        separators=list(resolved_config.separators),
        keep_separator=False,
        strip_whitespace=True,
        length_function=len,
    )
    return [chunk for chunk in splitter.split_text(text.strip()) if chunk.strip()]
