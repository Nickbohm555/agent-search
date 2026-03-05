import logging
import warnings

from fastapi import FastAPI

# Ensure agent/tool/callback logs (INFO) appear in container stdout
_root = logging.getLogger()
_root.setLevel(logging.INFO)
if not _root.handlers:
    _h = logging.StreamHandler()
    _h.setLevel(logging.INFO)
    _root.addHandler(_h)
for _name in (
    "utils.agent_callbacks",
    "services.agent_service",
    "agents.coordinator",
    "tools.retriever_tool",
):
    logging.getLogger(_name).setLevel(logging.INFO)
from fastapi.middleware.cors import CORSMiddleware

from routers.agent import router as agent_router

# Suppress Pydantic schema warning from deps (e.g. LangChain) using typing.NotRequired
warnings.filterwarnings(
    "ignore",
    message=".*NotRequired.*is not a Python type.*",
    category=UserWarning,
    module="pydantic._internal._generate_schema",
)
from routers.internal_data import router as internal_data_router

app = FastAPI(title="agent-search", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)
app.include_router(internal_data_router)
