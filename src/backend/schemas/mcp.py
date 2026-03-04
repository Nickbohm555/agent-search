from typing import Any, Literal

from pydantic import BaseModel, Field


class MCPJsonRpcRequest(BaseModel):
    jsonrpc: Literal["2.0"]
    method: str
    id: str | int | None = None
    params: dict[str, Any] = Field(default_factory=dict)

