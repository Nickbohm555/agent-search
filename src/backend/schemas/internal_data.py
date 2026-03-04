from typing import Literal, Optional

from pydantic import BaseModel, Field


class InternalDocumentInput(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source_ref: Optional[str] = None


class InternalDataLoadRequest(BaseModel):
    source_type: Literal["inline"] = "inline"
    documents: list[InternalDocumentInput] = Field(min_length=1)


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
