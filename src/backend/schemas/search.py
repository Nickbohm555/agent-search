from pydantic import BaseModel


class SearchSkeletonResponse(BaseModel):
    status: str
    message: str
