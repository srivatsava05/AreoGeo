from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from app.core.errors import GeospatialInputError
from app.services.file_validation import identify_format, validate_zip


def make_zip(path: Path, members: dict[str, bytes]) -> Path:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return path


def test_identifies_supported_and_unsupported_extensions():
    assert identify_format("MAP.KML") == "kml"
    assert identify_format("district.zip") == "shapefile"
    with pytest.raises(GeospatialInputError, match="Supported uploads"):
        identify_format("map.geojson")


def test_accepts_shapefile_nested_in_zip(tmp_path):
    archive = make_zip(tmp_path / "nested.zip", {
        "survey/blocks.shp": b"shp", "survey/blocks.shx": b"shx",
        "survey/blocks.dbf": b"dbf", "survey/blocks.prj": b"prj",
        "survey/blocks.cpg": b"utf-8",
    })
    assert validate_zip(archive) == "survey/blocks.shp"


@pytest.mark.parametrize("members, message", [
    ({}, "empty"),
    ({"a.shp": b"x"}, "missing required sidecar"),
    ({"a.shp": b"x", "a.shx": b"x", "a.dbf": b"x", "b.shp": b"x"}, "exactly one"),
    ({"../a.shp": b"x", "../a.shx": b"x", "../a.dbf": b"x"}, "unsafe"),
    ({"a.shp": b"x", "a.shx": b"x", "a.dbf": b"x", "a.prj": b"x", "a.DBF": b"duplicate"}, ""),
])
def test_rejects_bad_archives(tmp_path, members, message):
    archive = make_zip(tmp_path / "bad.zip", members)
    if not message:
        # Case-insensitive duplicate sidecars are ambiguous and should be rejected.
        with pytest.raises(GeospatialInputError):
            validate_zip(archive)
    else:
        with pytest.raises(GeospatialInputError, match=message):
            validate_zip(archive)


def test_rejects_non_zip(tmp_path):
    invalid = tmp_path / "broken.zip"
    invalid.write_bytes(b"not a zip")
    with pytest.raises(GeospatialInputError, match="valid ZIP"):
        validate_zip(invalid)
