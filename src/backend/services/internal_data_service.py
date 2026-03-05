import logging

from sqlalchemy.orm import Session

from common.db import wipe_all_internal_data
from schemas import (
    InternalDataLoadRequest,
    InternalDataLoadResponse,
    WikiSourceOption,
    WikiSourcesResponse,
)
from services.wiki_ingestion_service import list_wiki_sources

logger = logging.getLogger(__name__)


def wipe_internal_data(db: Session) -> None:
    """Wipe internal documents/chunks via shared DB helper."""
    wipe_all_internal_data(db)
    db.commit()
    logger.info("Internal data wipe committed.")


def list_wiki_sources_with_load_state(_db: Session) -> WikiSourcesResponse:
    """Return curated wiki sources; load-state persistence is added later."""
    options = [
        WikiSourceOption(
            source_id=source.source_id,
            label=source.label,
            article_query=source.article_query,
            already_loaded=False,
        )
        for source in list_wiki_sources()
    ]
    return WikiSourcesResponse(sources=options)


def load_internal_data(_payload: InternalDataLoadRequest, _db: Session) -> InternalDataLoadResponse:
    """Placeholder until wiki/doc load orchestration is implemented."""
    raise ValueError("Internal data load is not implemented yet.")
