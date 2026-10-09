import shutil
import json
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.core.config import settings
from app.core.errors import GeospatialInputError
from app.models.file_record import FileRecord, SessionLocal
from app.services.file_validation import identify_format, validate_zip
from app.services.geospatial_reader import process_file
from app.storage.local import file_directory

router = APIRouter(tags=["files"])


def _response(record: FileRecord) -> dict:
    return {"id": record.id, "filename": record.filename, "format": record.format,
            "feature_count": record.feature_count, "crs": record.crs,
            "measurement_crs": record.measurement_crs, "status": record.status,
            "created_at": record.created_at, "error": record.error}


@router.post("/files/", status_code=status.HTTP_201_CREATED)
def upload_file(file: UploadFile = File(...)) -> dict:
    try:
        file_format = identify_format(file.filename or "")
    except GeospatialInputError as exc:
        raise HTTPException(415, str(exc)) from exc
    file_id = str(uuid4())
    directory = file_directory(file_id)
    directory.mkdir(parents=True, exist_ok=True)
    upload_path = directory / ("source.kml" if file_format == "kml" else "source.zip")
    size = 0
    try:
        with upload_path.open("wb") as destination:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(413, "Upload exceeds the configured size limit.")
                destination.write(chunk)
        if size == 0:
            raise HTTPException(400, "Uploaded file is empty.")
        if file_format == "shapefile":
            validate_zip(upload_path)
        record = FileRecord(id=file_id, filename=Path(file.filename or "upload").name,
                            format=file_format, status="PROCESSING")
        with SessionLocal() as db:
            db.add(record)
            db.commit()
        try:
            count, crs, measurement_crs = process_file(upload_path, file_id, file_format)
            record.feature_count, record.crs = count, crs
            record.measurement_crs, record.status = measurement_crs, "COMPLETED"
        except Exception as exc:
            record.status = "FAILED"
            record.error = str(exc)[:2000] if isinstance(exc, GeospatialInputError) else f"Could not process geospatial data ({type(exc).__name__})."
        with SessionLocal() as db:
            db.merge(record)
            db.commit()
        return _response(record)
    except GeospatialInputError as exc:
        shutil.rmtree(directory, ignore_errors=True)
        raise HTTPException(400, str(exc)) from exc
    except HTTPException:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(directory, ignore_errors=True)
        raise HTTPException(400, f"Upload could not be accepted ({type(exc).__name__}).") from exc
    finally:
        file.file.close()


@router.get("/files/{file_id}/")
def get_file(file_id: UUID) -> dict:
    file_id = str(file_id)
    file_directory(file_id)
    with SessionLocal() as db:
        record = db.get(FileRecord, file_id)
    if not record:
        raise HTTPException(404, "File not found.")
    return _response(record)


@router.get("/files/{file_id}/measurements/")
def get_measurements(
    file_id: UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> dict:
    file_id = str(file_id)
    file_directory(file_id)
    with SessionLocal() as db:
        record = db.get(FileRecord, file_id)
    if not record:
        raise HTTPException(404, "File not found.")
    if record.status != "COMPLETED":
        raise HTTPException(409, f"File processing is {record.status.lower()}.")
    result_path = file_directory(file_id) / "features.jsonl"
    if not result_path.is_file():
        raise HTTPException(500, "Processed results are unavailable.")
    page = []
    with result_path.open(encoding="utf-8") as source:
        for index, line in enumerate(source):
            if index < offset:
                continue
            if len(page) >= limit:
                break
            page.append(json.loads(line))
    return {"file_id": file_id, "count": record.feature_count, "offset": offset, "limit": limit,
            "features": page}
