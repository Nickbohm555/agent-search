from __future__ import annotations

import os
import re
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

_RETRIEVED_LINE_PATTERN = re.compile(r"^\d+\.\s+title=(.*?)\s+source=(.*?)\s+content=(.*)$")
_WORD_PATTERN = re.compile(r"[a-z0-9]+")
_YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievedDocument:
    rank: int
    title: str
    source: str
    content: str


@dataclass(frozen=True)
class DocumentValidationConfig:
    min_relevance_score: float = 0.0
    source_allowlist: tuple[str, ...] = ()
    min_year: int | None = None
    max_year: int | None = None
    require_year_when_range_set: bool = False
    max_workers: int = 8


@dataclass(frozen=True)
class ValidatedDocumentResult:
    document: RetrievedDocument
    relevance_score: float
    passed: bool
    rejection_reasons: tuple[str, ...]


@dataclass(frozen=True)
class SubQuestionValidationResult:
    total_documents: int
    valid_documents: list[RetrievedDocument]
    validation_results: list[ValidatedDocumentResult]


def build_document_validation_config_from_env() -> DocumentValidationConfig:
    source_allowlist_raw = os.getenv("DOCUMENT_VALIDATION_SOURCE_ALLOWLIST", "")
    source_allowlist = tuple(
        item.strip().lower()
        for item in source_allowlist_raw.split(",")
        if item.strip()
    )

    min_year_raw = os.getenv("DOCUMENT_VALIDATION_MIN_YEAR")
    max_year_raw = os.getenv("DOCUMENT_VALIDATION_MAX_YEAR")
    max_workers_raw = os.getenv("DOCUMENT_VALIDATION_MAX_WORKERS", "8")
    require_year_raw = os.getenv("DOCUMENT_VALIDATION_REQUIRE_YEAR_WHEN_RANGE_SET", "false")

    return DocumentValidationConfig(
        min_relevance_score=float(os.getenv("DOCUMENT_VALIDATION_MIN_RELEVANCE_SCORE", "0.0")),
        source_allowlist=source_allowlist,
        min_year=int(min_year_raw) if min_year_raw not in (None, "") else None,
        max_year=int(max_year_raw) if max_year_raw not in (None, "") else None,
        require_year_when_range_set=require_year_raw.strip().lower() in {"1", "true", "yes", "on"},
        max_workers=max(1, int(max_workers_raw)),
    )


def parse_retrieved_documents(retrieved_output: str) -> list[RetrievedDocument]:
    if not isinstance(retrieved_output, str) or not retrieved_output.strip():
        return []

    parsed: list[RetrievedDocument] = []
    for line in retrieved_output.splitlines():
        match = _RETRIEVED_LINE_PATTERN.match(line.strip())
        if not match:
            continue
        title, source, content = match.groups()
        parsed.append(
            RetrievedDocument(
                rank=len(parsed) + 1,
                title=title.strip(),
                source=source.strip(),
                content=content.strip(),
            )
        )
    return parsed


def format_retrieved_documents(documents: list[RetrievedDocument]) -> str:
    """Serialize documents using the stable citation contract.

    Contract shape (one line per document):
    ``{index}. title={title} source={source} content={content}``
    """
    if not documents:
        return "No relevant documents found."
    formatted = "\n".join(
        f"{idx}. title={doc.title} source={doc.source} content={doc.content}"
        for idx, doc in enumerate(documents, start=1)
    )
    logger.info(
        "Document validation formatter emitted citation contract document_count=%s contract=%s",
        len(documents),
        "index.title.source.content",
    )
    return formatted


def _tokenize(value: str) -> set[str]:
    return {token for token in _WORD_PATTERN.findall(value.lower()) if token}


def _compute_relevance_score(sub_question: str, document: RetrievedDocument) -> float:
    query_tokens = _tokenize(sub_question)
    if not query_tokens:
        return 0.0
    doc_tokens = _tokenize(" ".join((document.title, document.content, document.source)))
    if not doc_tokens:
        return 0.0
    overlap = len(query_tokens & doc_tokens)
    return overlap / len(query_tokens)


def _extract_years(document: RetrievedDocument) -> list[int]:
    text = " ".join((document.title, document.content, document.source))
    return [int(match.group(0)) for match in _YEAR_PATTERN.finditer(text)]


def _validate_document(
    *,
    sub_question: str,
    document: RetrievedDocument,
    config: DocumentValidationConfig,
) -> ValidatedDocumentResult:
    rejection_reasons: list[str] = []
    relevance_score = _compute_relevance_score(sub_question, document)

    if relevance_score < config.min_relevance_score:
        rejection_reasons.append(
            f"relevance_below_threshold({relevance_score:.3f}<{config.min_relevance_score:.3f})"
        )

    source_allowlist = config.source_allowlist
    if source_allowlist:
        source_value = document.source.lower()
        if source_value not in source_allowlist:
            rejection_reasons.append("source_not_allowlisted")

    range_configured = config.min_year is not None or config.max_year is not None
    if range_configured:
        years = _extract_years(document)
        if not years:
            if config.require_year_when_range_set:
                rejection_reasons.append("missing_year")
        else:
            in_range = False
            for year in years:
                if config.min_year is not None and year < config.min_year:
                    continue
                if config.max_year is not None and year > config.max_year:
                    continue
                in_range = True
                break
            if not in_range:
                rejection_reasons.append("year_out_of_range")

    return ValidatedDocumentResult(
        document=document,
        relevance_score=relevance_score,
        passed=not rejection_reasons,
        rejection_reasons=tuple(rejection_reasons),
    )


def validate_subquestion_documents(
    *,
    sub_question: str,
    retrieved_output: str,
    config: DocumentValidationConfig,
) -> SubQuestionValidationResult:
    documents = parse_retrieved_documents(retrieved_output)
    if not documents:
        return SubQuestionValidationResult(
            total_documents=0,
            valid_documents=[],
            validation_results=[],
        )

    with ThreadPoolExecutor(max_workers=min(config.max_workers, len(documents))) as executor:
        validation_results = list(
            executor.map(
                lambda doc: _validate_document(sub_question=sub_question, document=doc, config=config),
                documents,
            )
        )

    valid_documents = [result.document for result in validation_results if result.passed]
    return SubQuestionValidationResult(
        total_documents=len(documents),
        valid_documents=valid_documents,
        validation_results=validation_results,
    )
