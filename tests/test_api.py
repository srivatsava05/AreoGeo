from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import geopandas as gpd
from dataclasses import replace
from fastapi.testclient import TestClient
from shapely.geometry import LineString, Point, box

from app.main import app
from app.models.file_record import FileRecord, SessionLocal

client = TestClient(app)


def frame(count=3):
    rows = [{"name": "parcel", "geometry": box(0, 0, 0.001, 0.001)},
            {"name": "road", "geometry": LineString([(0, 0), (0.001, 0)])},
            {"name": "marker", "geometry": Point(0, 0)}]
    if count > len(rows):
        rows += [{"name": f"point-{index}", "geometry": Point(index / 1000, 0)}
                 for index in range(count - len(rows))]
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")


def test_upload_metadata_and_paged_measurements(monkeypatch):
    monkeypatch.setattr(gpd, "read_file", lambda *args, **kwargs: frame())
    uploaded = client.post("/api/files/", files={"file": ("survey.kml", b"<kml />", "application/vnd.google-earth.kml+xml")})
    assert uploaded.status_code == 201
    metadata = uploaded.json()
    assert metadata["status"] == "COMPLETED"
    assert metadata["feature_count"] == 3
    assert metadata["crs"] == "EPSG:4326"
    assert client.get(f"/api/files/{metadata['id']}/").json()["filename"] == "survey.kml"
    page = client.get(f"/api/files/{metadata['id']}/measurements/?offset=0&limit=2").json()
    assert page["count"] == 3
    assert len(page["features"]) == 2
    assert page["features"][0]["measurement_unit"] == "m²"
    assert page["features"][1]["measurement_unit"] == "m"
    assert client.get(f"/api/files/{metadata['id']}/measurements/?offset=3").json()["features"] == []


def test_rejects_unknown_extension_and_empty_upload():
    assert client.post("/api/files/", files={"file": ("data.geojson", b"{}")}).status_code == 415
    assert client.post("/api/files/", files={"file": ("empty.kml", b"")}).status_code == 400


def test_rejects_upload_over_configured_size(monkeypatch):
    import app.api.routes.files as routes
    monkeypatch.setattr(routes, "settings", replace(routes.settings, max_upload_bytes=4))
    response = client.post("/api/files/", files={"file": ("large.kml", b"12345")})
    assert response.status_code == 413


def test_processing_error_is_persisted_and_measurement_endpoint_conflicts(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("reader exploded")
    monkeypatch.setattr(gpd, "read_file", fail)
    response = client.post("/api/files/", files={"file": ("bad.kml", b"<kml />")})
    assert response.status_code == 201
    metadata = response.json()
    assert metadata["status"] == "FAILED"
    assert "RuntimeError" in metadata["error"]
    assert client.get(f"/api/files/{metadata['id']}/measurements/").status_code == 409


def test_invalid_ids_and_missing_files_are_client_errors():
    assert client.get("/api/files/not-a-uuid/").status_code == 422
    assert client.get("/api/files/00000000-0000-0000-0000-000000000000/").status_code == 404


def test_feature_limit_fails_cleanly(monkeypatch):
    import app.services.geospatial_reader as reader
    monkeypatch.setattr(reader, "settings", replace(reader.settings, max_features=2))
    monkeypatch.setattr(gpd, "read_file", lambda *args, **kwargs: frame(3))
    response = client.post("/api/files/", files={"file": ("too-many.kml", b"<kml />")})
    assert response.json()["status"] == "FAILED"
    assert "Feature limit exceeded" in response.json()["error"]


def test_large_result_set_is_paged_without_losing_features(monkeypatch):
    monkeypatch.setattr(gpd, "read_file", lambda *args, **kwargs: frame(2500))
    response = client.post("/api/files/", files={"file": ("large.kml", b"<kml />")})
    file_id = response.json()["id"]
    page = client.get(f"/api/files/{file_id}/measurements/?offset=2400&limit=100").json()
    assert page["count"] == 2500
    assert len(page["features"]) == 100
    assert page["features"][0]["feature_id"] == "2400"


def test_real_shapefile_zip_upload_reads_and_measures(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    shapefile = source_dir / "parcels.shp"
    gpd.GeoDataFrame(
        [{"parcel_id": 17, "geometry": box(0, 0, 0.001, 0.001)}],
        geometry="geometry",
        crs="EPSG:4326",
    ).to_file(shapefile, index=False)
    archive_path = tmp_path / "parcels.zip"
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        for sidecar in source_dir.iterdir():
            archive.write(sidecar, f"survey/{sidecar.name}")

    response = client.post(
        "/api/files/",
        files={"file": ("parcels.zip", archive_path.read_bytes(), "application/zip")},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "COMPLETED"
    assert response.json()["feature_count"] == 1
    feature = client.get(f"/api/files/{response.json()['id']}/measurements/").json()["features"][0]
    assert feature["properties"]["parcel_id"] == 17
    assert feature["measurement_type"] == "area"
    assert 12_000 < feature["measurement_value"] < 13_000
