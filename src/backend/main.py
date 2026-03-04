from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from observability import initialize_langfuse_tracing
from routers.agent import router as agent_router
from routers.health import router as health_router
from routers.search import router as search_router

app = FastAPI(title="agent-search", version="0.1.0")

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


@app.on_event("startup")
def startup_observability() -> None:
    # Scaffold-only: stores an inert handle until Langfuse SDK wiring is implemented.
    app.state.langfuse = initialize_langfuse_tracing()
