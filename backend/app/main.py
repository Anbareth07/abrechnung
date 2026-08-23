from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import (
    categories,
    invoices,
    lease_units,
    meters,
    properties,
    settlements,
    techem,
    tenants,
)

app = FastAPI(title="Nebenkostenabrechnung", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Dev; für Produktion einschränken
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(properties.router)
app.include_router(lease_units.router)
app.include_router(tenants.router)
app.include_router(categories.router)
app.include_router(categories.config_router)
app.include_router(invoices.router)
app.include_router(meters.router)
app.include_router(meters.reading_router)
app.include_router(techem.router)
app.include_router(settlements.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
