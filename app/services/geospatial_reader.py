from __future__ import annotations

import json
import math
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import mapping

from app.core.config import settings
from app.core.errors import GeospatialInputError
from app.services.file_validation import validate_zip
from app.services.measurement import measure


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
    if hasattr(value, "item"):
        return _json_value(value.item())
    return str(value)


def process_file(path: Path, file_id: str, file_format: str) -> tuple[int, str | None, str | None]:
    if file_format == "kml":
        frame = gpd.read_file(path, driver="KML")
    else:
        with tempfile.TemporaryDirectory(prefix="geo-") as scratch:
            shapefile_rel = validate_zip(path)
            source_member = Path(shapefile_rel.replace("\\", "/"))
            source_stem = source_member.with_suffix("").as_posix().lower()
            extracted_dir = Path(scratch) / "dataset"
            extracted_dir.mkdir()
            with zipfile.ZipFile(path) as archive:
                for item in archive.infolist():
                    if item.is_dir():
                        continue
                    member = Path(item.filename.replace("\\", "/"))
                    if member.with_suffix("").as_posix().lower() == source_stem:
                        target = extracted_dir / (source_member.stem + member.suffix.lower())
                        with archive.open(item) as source, target.open("wb") as destination:
                            shutil.copyfileobj(source, destination)
            frame = gpd.read_file(extracted_dir / f"{source_member.stem}.shp")
    if len(frame) > settings.max_features:
        raise GeospatialInputError(f"Feature limit exceeded ({settings.max_features}).")
    source_crs = frame.crs.to_string() if frame.crs else None
    result_path = settings.data_dir / file_id / "features.jsonl"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    measurement_crs = None
    count = 0
    with result_path.open("w", encoding="utf-8") as results:
        for index, row in frame.iterrows():
            geometry = row.geometry
            geometry_json = mapping(geometry) if geometry is not None else None
            props = {str(key): _json_value(value) for key, value in row.drop(labels=[frame.geometry.name]).items()}
            geometry_type = geometry.geom_type if geometry is not None else None
            try:
                result = measure(geometry_json, source_crs)
            except Exception as exc:
                result = {"measurement_type": None, "measurement_value": None, "measurement_unit": None,
                          "measurement_crs": None, "warning": f"Measurement failed: {type(exc).__name__}."}
            feature = {"feature_id": str(index), "geometry_type": geometry_type, "geometry": geometry_json,
                       "crs": source_crs, "properties": props, **result}
            results.write(json.dumps(feature, ensure_ascii=False, allow_nan=False) + "\n")
            measurement_crs = measurement_crs or feature.get("measurement_crs")
            count += 1
    return count, source_crs, measurement_crs
