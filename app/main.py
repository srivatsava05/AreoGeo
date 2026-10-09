from fastapi import FastAPI

from app.api.routes.files import router as files_router
from app.core.config import settings

app = FastAPI(
    title="Geospatial File Measurement API",
    description="Upload KML or zipped Shapefiles and retrieve feature measurements.",
    version="1.0.0",
)
app.include_router(files_router, prefix=settings.api_prefix)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
