import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from utils.embeddings import EMBEDDING_DIM, get_embedding_model


def test_embedding_dim_is_positive_int() -> None:
    assert isinstance(EMBEDDING_DIM, int)
    assert EMBEDDING_DIM > 0


def test_get_embedding_model_returns_embeddings_like_object() -> None:
    model = get_embedding_model()
    assert hasattr(model, "embed_documents")

    vectors = model.embed_documents(["alpha", "beta"])
    assert len(vectors) == 2
    assert all(len(vector) == EMBEDDING_DIM for vector in vectors)
