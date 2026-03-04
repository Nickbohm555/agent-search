from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from observability import initialize_langfuse_tracing
from routers.agent import router as agent_router
from routers.health import router as health_router
from routers.internal_data import router as internal_data_router
from routers.mcp import router as mcp_router
from routers.search import router as search_router
from routers.web import router as web_router
from services.mcp_service import create_fastmcp_app
from services.runtime_service import initialize_runtime_handle


def _replace_fastmcp_mount_app(app: FastAPI, fastmcp_app) -> None:
    for route in app.routes:
        if isinstance(route, Mount) and route.path == "/mcp/fast":
            route.app = fastmcp_app
            return

    app.mount("/mcp/fast", fastmcp_app)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    # App-level observability/runtime handles are initialized once for all routers and tools.
    app.state.langfuse = initialize_langfuse_tracing()
    app.state.runtime_model = initialize_runtime_handle()

    fastmcp_http_app = create_fastmcp_app(app)
    _replace_fastmcp_mount_app(app, fastmcp_http_app)
    async with fastmcp_http_app.router.lifespan_context(fastmcp_http_app):
        yield


app = FastAPI(title="agent-search", version="0.1.0", lifespan=app_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(search_router)
app.include_router(agent_router)
app.include_router(internal_data_router)
app.include_router(web_router)
app.include_router(mcp_router)
app.mount("/mcp/fast", create_fastmcp_app(app))
