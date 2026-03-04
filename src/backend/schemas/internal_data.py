from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


class InternalDocumentInput(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source_ref: Optional[str] = None


class InlineInternalDataLoadRequest(BaseModel):
    source_type: Literal["inline"] = "inline"
    documents: list[InternalDocumentInput] = Field(min_length=1)


class GoogleDocsInternalDataLoadRequest(BaseModel):
    source_type: Literal["google_docs"] = "google_docs"
    document_ids: list[str] = Field(min_length=1)


InternalDataLoadRequest = Annotated[
    Union[InlineInternalDataLoadRequest, GoogleDocsInternalDataLoadRequest],
    Field(discriminator="source_type"),
]


class InternalDataLoadResponse(BaseModel):
    status: Literal["success"]
    source_type: str
    documents_loaded: int
    chunks_created: int


class InternalDataRetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class InternalRetrievedChunk(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    source_type: str
    source_ref: Optional[str]
    content: str
    score: float


class InternalDataRetrieveResponse(BaseModel):
    query: str
    total_chunks_considered: int
    results: list[InternalRetrievedChunk]
