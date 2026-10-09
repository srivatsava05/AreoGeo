from datetime import datetime

from pydantic import BaseModel


class FileResponse(BaseModel):
    id: str
    filename: str
    format: str
    feature_count: int
    crs: str | None
    measurement_crs: str | None
    status: str
    created_at: datetime
    error: str | None = None


class MeasurementFeature(BaseModel):
    feature_id: str
    geometry_type: str | None
    geometry: dict | None
    crs: str | None
    properties: dict
    measurement_type: str | None = None
    measurement_value: float | None = None
    measurement_unit: str | None = None
    measurement_crs: str | None = None
    warning: str | None = None


class MeasurementPage(BaseModel):
    file_id: str
    count: int
    offset: int
    limit: int
    features: list[MeasurementFeature]
