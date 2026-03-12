from __future__ import annotations

import argparse
import sys
from pathlib import Path

from langchain_core.documents import Document

BACKEND_ROOT = Path(__file__).resolve().parents[2] / "src" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from db import DATABASE_URL
from services.vector_store_service import add_documents_to_store, get_vector_store
from utils.embeddings import get_embedding_model


def seed_collection(*, collection_name: str) -> int:
    vector_store = get_vector_store(
        connection=DATABASE_URL,
        collection_name=collection_name,
        embeddings=get_embedding_model(),
    )
    documents = [
        Document(
            page_content=(
                "NATO stands for the North Atlantic Treaty Organization. "
                "It is a political and military alliance founded in 1949."
            ),
            metadata={
                "title": "NATO",
                "source": "https://example.test/nato",
            },
        ),
        Document(
            page_content=(
                "The North Atlantic Treaty was signed in 1949 by founding member states. "
                "It established NATO as a collective defense alliance."
            ),
            metadata={
                "title": "North Atlantic Treaty",
                "source": "https://example.test/north-atlantic-treaty",
            },
        ),
        Document(
            page_content=(
                "Article 5 of the NATO treaty states that an armed attack against one ally "
                "shall be considered an attack against all allies."
            ),
            metadata={
                "title": "NATO Article 5",
                "source": "https://example.test/nato-article-5",
            },
        ),
    ]
    ids = add_documents_to_store(vector_store, documents)
    return len(ids)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--collection", required=True)
    args = parser.parse_args()
    inserted = seed_collection(collection_name=args.collection)
    print(inserted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
