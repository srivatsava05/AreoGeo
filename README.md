# Geospatial File Measurement API

A FastAPI service that accepts KML files and ZIP archives containing Shapefiles, stores per-feature geometry and attributes, and calculates polygon area and line length in metres-based units.

## Requirements

- Python 3.11 or newer
- GDAL/OGR support for KML and Shapefile formats (GeoPandas' selected I/O engine must include the KML driver)

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e .
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive docs are at `/docs`. Copy `.env.example` to `.env` and adjust values as needed. The application reads environment variables directly. By default, uploads and JSON results are stored below `data/`, and file metadata is stored in SQLite.

## Run automated tests

Install the test dependencies and run the unit and integration suite:

```bash
python -m pip install -e ".[test]"
python -m pytest -q --durations=10
```

The tests cover CRS conversion, supported and unsupported geometry, invalid and antimeridian geometries, malformed and unsafe ZIP archives, API status and error behavior, size and feature limits, real Shapefile ZIP ingestion, and pagination over 2,500 features.

## Endpoints

### Upload and process

`POST /api/files/` accepts `multipart/form-data` with a field named `file`. The accepted inputs are `.kml` and `.zip`; a Shapefile archive must include exactly one `.shp` plus its `.shx` and `.dbf` sidecars. A `.prj` is recommended so the source coordinate reference system is known.

```bash
curl -F "file=@survey.kml" http://127.0.0.1:8000/api/files/
```

Example response:

```json
{
  "id": "7c7c1f88-2414-4e93-9d56-61188df21fe6",
  "filename": "survey.kml",
  "format": "kml",
  "feature_count": 120,
  "crs": "EPSG:4326",
  "measurement_crs": "+proj=laea ...",
  "status": "COMPLETED",
  "created_at": "2026-10-09T12:00:00Z",
  "error": null
}
```

Processing happens during the request. A processing failure is recorded and returned with status `FAILED`; the endpoint returns a file record so clients can inspect its error. Invalid upload structure is rejected with an HTTP 4xx response. Default upload and feature limits are configurable with `MAX_UPLOAD_MB` and `MAX_FEATURES`.

### File information

`GET /api/files/{id}/` returns the stored file record, including status, feature count, source CRS and the measurement CRS used for the first supported feature. Missing IDs return 404.

### Per-feature measurements

`GET /api/files/{id}/measurements/?offset=0&limit=100` returns a page of features. `limit` is capped at 1000. Each feature includes its original geometry, source CRS, properties, geometry type, measurement and any warning.

Polygon and MultiPolygon geometries receive area in square metres; LineString and MultiLineString receive length in metres. Point and other geometry families are retained and returned with an explanatory warning and no measurement. Empty geometries are also retained. Invalid or unmeasurable individual features do not stop other features from being processed.

## Architecture

```text
app/
├── api/routes/files.py       # Upload, metadata, and measurements endpoints
├── api/schemas/              # Response models
├── core/                     # Settings and domain errors
├── models/                   # SQLAlchemy file metadata
├── services/                 # Validation, reading, CRS, and measurement logic
├── storage/                  # Safe local file path handling
└── main.py                   # FastAPI application
data/                         # Local database, uploads, and feature results
```

Uploads are size-limited and Shapefile ZIP entries are checked for path traversal and encryption before extraction. File records live in SQLite; feature details and measurements are serialized one record per line to a JSONL result file, so measurement requests page stored results without rerunning GIS calculations or loading the entire results file into memory.

## CRS and measurement decisions

The input CRS is preserved on every feature. Coordinates are never measured as if longitude/latitude degrees were planar units. Geographic inputs are reprojected into a local azimuthal projection centered on each feature: Lambert azimuthal equal-area for area and azimuthal equidistant for length. This handles ordinary local datasets and polar locations without relying on a single UTM zone. For projected inputs, measurements use the input projection and convert its linear unit to metres. Reported CRS values identify the projection used for each measurement.

KML commonly uses WGS 84. Shapefiles should include a `.prj` file; if a source CRS is absent, features and attributes are retained but measurements are skipped with a warning because assigning a guessed CRS could produce misleading results.

## Design decisions and future scope

- **FastAPI** provides a small typed HTTP layer and generated OpenAPI documentation.
- **Synchronous processing** keeps the initial service deployable without a queue. For large files or long-running jobs, the upload flow can return 202 and move processing to Celery/RQ or a managed worker.
- **SQLite and local disk** make local setup simple. A multi-instance deployment should use PostgreSQL/PostGIS and shared object storage.
- **Per-feature local projections** avoid a misleading single UTM zone across differently located features. Very large geometries spanning broad regions may need a geodesic measurement policy or explicit user-selected CRS.

Learning outcomes include Python API design, geospatial file ingestion, CRS transformation, measurement units, validation, and persistence. Future work can add asynchronous jobs, authentication, retention policies, PostGIS querying, richer measurement options, and operational metrics.

## Repository submission

Initialize Git in this directory after reviewing the source. To publish, create a public GitHub repository and add it as `origin`, then push the initial branch. Do not commit `.env`, uploaded source data, local result files, or the SQLite database.
