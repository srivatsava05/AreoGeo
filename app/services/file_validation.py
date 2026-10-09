import zipfile
from pathlib import Path

from app.core.errors import GeospatialInputError

SHAPEFILE_REQUIRED = {".shp", ".shx", ".dbf"}


def validate_zip(archive_path: Path) -> str:
    """Validate archive paths and locate a Shapefile without extracting untrusted paths."""
    try:
        with zipfile.ZipFile(archive_path) as archive:
            files = [item for item in archive.infolist() if not item.is_dir()]
            if not files:
                raise GeospatialInputError("The ZIP archive is empty.")
            for item in files:
                member = Path(item.filename.replace("\\", "/"))
                if member.is_absolute() or ".." in member.parts or item.flag_bits & 0x1:
                    raise GeospatialInputError("The ZIP contains an unsafe or encrypted entry.")
            shape_paths = [item.filename for item in files if Path(item.filename).suffix.lower() == ".shp"]
            if len(shape_paths) != 1:
                raise GeospatialInputError("The ZIP must contain exactly one .shp file.")
            shape_stem = Path(shape_paths[0]).with_suffix("").as_posix().lower()
            extensions = [
                Path(item.filename).suffix.lower()
                for item in files
                if Path(item.filename).with_suffix("").as_posix().lower() == shape_stem
            ]
            if len(extensions) != len(set(extensions)):
                raise GeospatialInputError("The ZIP contains duplicate Shapefile sidecars.")
            missing = SHAPEFILE_REQUIRED - set(extensions)
            if missing:
                raise GeospatialInputError(
                    "The Shapefile is missing required sidecar(s): " + ", ".join(sorted(missing))
                )
            if sum(item.file_size for item in files) > 500 * 1024 * 1024:
                raise GeospatialInputError("The uncompressed ZIP contents exceed 500 MB.")
            return shape_paths[0]
    except zipfile.BadZipFile as exc:
        raise GeospatialInputError("The uploaded file is not a valid ZIP archive.") from exc


def identify_format(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".kml":
        return "kml"
    if suffix == ".zip":
        return "shapefile"
    raise GeospatialInputError("Supported uploads are .kml and .zip Shapefile archives.")
