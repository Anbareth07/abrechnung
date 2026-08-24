from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .api import (
    categories,
    invoices,
    lease_units,
    meters,
    properties,
    settlements,
    strom,
    techem,
    tenants,
    wasser,
)

app = FastAPI(title="Nebenkostenabrechnung", version="0.1.0")

# Wildcard-Origins fuer maximale Kompatibilitaet (PC, Handy, beliebige Namen).
# Den Chrome-"Private Network Access"-Preflight beantwortet die Middleware unten
# selbst mit 200 + Access-Control-Allow-Private-Network.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PrivateNetworkAccessMiddleware(BaseHTTPMiddleware):
    """Beantwortet Chromes 'Private Network Access'-Preflight selbst mit 200
    und Access-Control-Allow-Private-Network (Starlette liefert sonst 400)."""

    async def dispatch(self, request: Request, call_next):
        if (
            request.method == "OPTIONS"
            and request.headers.get("access-control-request-private-network", "").lower() == "true"
        ):
            origin = request.headers.get("origin", "*")
            return Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                    "Access-Control-Allow-Private-Network": "true",
                    "Access-Control-Max-Age": "600",
                },
            )
        return await call_next(request)


# Aussen (nach CORS registriert) -> faengt den PNA-Preflight ab.
app.add_middleware(PrivateNetworkAccessMiddleware)

app.include_router(properties.router)
app.include_router(lease_units.router)
app.include_router(tenants.router)
app.include_router(categories.router)
app.include_router(categories.config_router)
app.include_router(invoices.router)
app.include_router(meters.router)
app.include_router(meters.reading_router)
app.include_router(techem.router)
app.include_router(strom.router)
app.include_router(wasser.router)
app.include_router(settlements.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
