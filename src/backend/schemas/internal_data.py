from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class InternalDocumentInput(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source_ref: Optional[str] = None


class WikiLoadInput(BaseModel):
    url: Optional[str] = Field(default=None, min_length=1)
    topic: Optional[str] = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_topic_or_url(self) -> "WikiLoadInput":
        if not self.url and not self.topic:
            raise ValueError("wiki load requires either url or topic")
        return self


class InternalDataLoadRequest(BaseModel):
    source_type: Literal["inline", "wiki"] = "inline"
    documents: Optional[list[InternalDocumentInput]] = None
    wiki: Optional[WikiLoadInput] = None

    @model_validator(mode="after")
    def validate_source_payload(self) -> "InternalDataLoadRequest":
        if self.source_type == "inline":
            if not self.documents:
                raise ValueError("inline load requires at least one document")
            return self

        if self.source_type == "wiki":
            if self.documents:
                raise ValueError("wiki load does not accept inline documents")
            if self.wiki is None:
                raise ValueError("wiki load requires wiki payload")
            return self

        raise ValueError("unsupported source_type")


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
