import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GoogleDocsConfigurationError(RuntimeError):
    pass


class GoogleDocsFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class GoogleDocContent:
    document_id: str
    title: str
    content: str


def fetch_google_docs(document_ids: list[str]) -> list[GoogleDocContent]:
    access_token = os.getenv("GOOGLE_DOCS_ACCESS_TOKEN", "").strip()
    if not access_token:
        raise GoogleDocsConfigurationError(
            "GOOGLE_DOCS_ACCESS_TOKEN is required for source_type='google_docs'."
        )

    fetched_docs: list[GoogleDocContent] = []
    for document_id in document_ids:
        cleaned_id = document_id.strip()
        if not cleaned_id:
            continue
        fetched_docs.append(_fetch_google_doc(cleaned_id, access_token))
    return fetched_docs


def _fetch_google_doc(document_id: str, access_token: str) -> GoogleDocContent:
    request = Request(
        url=f"https://docs.googleapis.com/v1/documents/{document_id}",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise GoogleDocsFetchError(
            f"Google Docs fetch failed for '{document_id}' with status {exc.code}."
        ) from exc
    except URLError as exc:
        raise GoogleDocsFetchError(
            f"Google Docs fetch failed for '{document_id}' due to network error."
        ) from exc

    title = str(payload.get("title", "")).strip() or f"Google Doc {document_id}"
    body = payload.get("body", {})
    content_parts: list[str] = []
    for block in body.get("content", []):
        paragraph = block.get("paragraph")
        if not paragraph:
            continue
        for element in paragraph.get("elements", []):
            text_run = element.get("textRun")
            if not text_run:
                continue
            text = str(text_run.get("content", ""))
            if text:
                content_parts.append(text)
    content = "".join(content_parts).strip()
    if not content:
        raise GoogleDocsFetchError(f"Google Docs document '{document_id}' has no readable text content.")
    return GoogleDocContent(document_id=document_id, title=title, content=content)
