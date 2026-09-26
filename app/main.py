from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Trade Surveillance API",
    version="0.1.0",
    description=(
        "Privacy-preserving compliance endpoints for market-abuse alerts, "
        "trader risk aggregates, and audit events."
    ),
)
app.include_router(router, prefix="/v1")


@app.get("/healthz", tags=["system"])
def healthz() -> dict[str, str]:
    return {"status": "ok"}
