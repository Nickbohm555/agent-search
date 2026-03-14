from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search.runtime.resume import attach_checkpoint_metadata


def test_attach_checkpoint_metadata_overrides_stale_checkpoint_id() -> None:
    payload = {
        "thread_id": "thread-live",
        "checkpoint_id": "stale-thread-id",
        "stage": "subquestions_ready",
        "subquestions": [{"subquestion_id": "sq-1", "sub_question": "What is NATO?"}],
    }

    normalized = attach_checkpoint_metadata(
        payload,
        checkpoint_id="checkpoint-live",
        thread_id="thread-live",
    )

    assert normalized == {
        "checkpoint_id": "checkpoint-live",
        "thread_id": "thread-live",
        "stage": "subquestions_ready",
        "subquestions": [{"subquestion_id": "sq-1", "sub_question": "What is NATO?"}],
    }
