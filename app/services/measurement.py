from __future__ import annotations

import math
from typing import Any

import geopandas as gpd
from pyproj import CRS
from shapely.geometry import shape


def _local_crs(geometry: Any, source_crs: CRS, kind: str) -> CRS:
    """Build a local azimuthal projection for geographic coordinates, including polar areas."""
    centroid = gpd.GeoSeries([geometry], crs=source_crs).to_crs("EPSG:4326").iloc[0].centroid
    lon, lat = centroid.x, centroid.y
    projection = "laea" if kind == "area" else "aeqd"
    return CRS.from_proj4(
        f"+proj={projection} +lat_0={lat:.10f} +lon_0={lon:.10f} "
        "+datum=WGS84 +units=m +no_defs +type=crs"
    )


def measure(geometry_mapping: dict | None, source_crs: str | None) -> dict[str, Any]:
    if not geometry_mapping:
        return {"measurement_type": None, "measurement_value": None, "measurement_unit": None,
                "measurement_crs": None, "warning": "Feature has no geometry."}
    geom = shape(geometry_mapping)
    kind = geom.geom_type
    if kind in {"Polygon", "MultiPolygon"}:
        measure_kind, unit = "area", "m²"
    elif kind in {"LineString", "MultiLineString"}:
        measure_kind, unit = "length", "m"
    else:
        return {"measurement_type": None, "measurement_value": None, "measurement_unit": None,
                "measurement_crs": None, "warning": f"Measurement is not defined for {kind}."}
    if not geom.is_valid:
        return {"measurement_type": measure_kind, "measurement_value": None, "measurement_unit": unit,
                "measurement_crs": None, "warning": "Invalid geometry; measurement was skipped."}
    if geom.is_empty:
        return {"measurement_type": measure_kind, "measurement_value": None, "measurement_unit": unit,
                "measurement_crs": None, "warning": "Feature geometry is empty."}
    if not source_crs:
        return {"measurement_type": measure_kind, "measurement_value": None, "measurement_unit": unit,
                "measurement_crs": None, "warning": "Source CRS is missing; measurement was skipped."}
    src = CRS.from_user_input(source_crs)
    if src.is_geographic:
        geographic = gpd.GeoSeries([geom], crs=src).to_crs("EPSG:4326").iloc[0]
        min_x, _, max_x, _ = geographic.bounds
        if max_x - min_x > 180:
            return {"measurement_type": measure_kind, "measurement_value": None,
                    "measurement_unit": unit, "measurement_crs": None,
                    "warning": "Geometry crosses the antimeridian; measurement needs an explicit wrap-aware CRS."}
        target = _local_crs(geom, src, measure_kind)
    else:
        target = src
    projected = gpd.GeoSeries([geom], crs=src).to_crs(target).iloc[0]
    value = projected.area if measure_kind == "area" else projected.length
    if target.is_projected:
        axis = target.axis_info[0]
        to_meters = axis.unit_conversion_factor or 1.0
        value *= to_meters**2 if measure_kind == "area" else to_meters
    if not math.isfinite(value):
        return {"measurement_type": measure_kind, "measurement_value": None, "measurement_unit": unit,
                "measurement_crs": target.to_string(), "warning": "Measurement was not finite."}
    return {"measurement_type": measure_kind, "measurement_value": float(value), "measurement_unit": unit,
            "measurement_crs": target.to_string(), "warning": None}
