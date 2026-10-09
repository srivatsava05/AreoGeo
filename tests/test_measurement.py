import pytest
from pyproj import CRS
from shapely.geometry import GeometryCollection, LineString, Point, Polygon, box, mapping

from app.services.measurement import measure


def test_geographic_polygon_area_is_positive_and_metre_based():
    result = measure(mapping(box(0, 0, 0.001, 0.001)), "EPSG:4326")
    assert result["measurement_type"] == "area"
    assert result["measurement_unit"] == "m²"
    assert 12_000 < result["measurement_value"] < 13_000
    assert CRS.from_user_input(result["measurement_crs"]).is_projected


def test_geographic_line_length_is_projected():
    result = measure(mapping(LineString([(0, 0), (0.001, 0)])), "EPSG:4326")
    assert result["measurement_type"] == "length"
    assert 110 < result["measurement_value"] < 112
    assert result["measurement_unit"] == "m"


def test_projected_us_survey_feet_are_converted_to_metres():
    result = measure(mapping(box(1_000_000, 200_000, 1_000_010, 200_010)), "EPSG:2263")
    assert result["measurement_unit"] == "m²"
    assert 9.28 < result["measurement_value"] < 9.30


@pytest.mark.parametrize("geometry", [Point(1, 2), GeometryCollection([Point(1, 2)])])
def test_unsupported_geometry_is_preserved_as_unmeasured(geometry):
    result = measure(mapping(geometry), "EPSG:4326")
    assert result["measurement_value"] is None
    assert "not defined" in result["warning"]


def test_missing_crs_skips_supported_measurement():
    result = measure(mapping(box(0, 0, 1, 1)), None)
    assert result["measurement_type"] == "area"
    assert result["measurement_value"] is None
    assert "CRS is missing" in result["warning"]


def test_antimeridian_geometry_is_not_given_a_misleading_measurement():
    result = measure(mapping(LineString([(179, 10), (-179, 10)])), "EPSG:4326")
    assert result["measurement_value"] is None
    assert "antimeridian" in result["warning"]


def test_invalid_polygon_is_skipped():
    bow_tie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    result = measure(mapping(bow_tie), "EPSG:4326")
    assert result["measurement_value"] is None
    assert "Invalid geometry" in result["warning"]


def test_missing_geometry_is_reported():
    result = measure(None, "EPSG:4326")
    assert result["measurement_value"] is None
    assert "no geometry" in result["warning"]
