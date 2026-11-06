from fastapi import APIRouter, Depends, File, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User
from app.permissions import Perm
from app.schemas import FileOut, FilesOut
from app.security import require
from app.services import files as svc
from app.services import projects as project_svc

router = APIRouter(tags=["files"])


@router.get("/projects/{project_id}/files")
def list_files(project_id: int, user: User = Depends(require(Perm.VIEW)), db: Session = Depends(get_db)) -> FilesOut:
    project = project_svc.get_project(db, project_id, user)
    return FilesOut(files=[FileOut.model_validate(f) for f in svc.list_files(db, project.id)], purge_on=svc.purge_date(project))


@router.post("/projects/{project_id}/files", status_code=201)
def upload(project_id: int, file: UploadFile = File(...), user: User = Depends(require(Perm.FILE_WRITE)),
           db: Session = Depends(get_db)) -> FileOut:
    data = file.file.read(settings.max_upload_mb * 1024 * 1024 + 1)  # au-delà de la limite : refusé sans tout lire
    return FileOut.model_validate(svc.add_file(db, user, project_svc.get_project(db, project_id, user), file.filename or "", data))


@router.get("/files/{file_id}/download")
def download(file_id: int, user: User = Depends(require(Perm.VIEW)), db: Session = Depends(get_db)) -> FileResponse:
    item = svc.get_file(db, file_id, user)
    return FileResponse(svc.path_of(item), media_type=item.content_type, filename=item.filename,
                        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


@router.delete("/files/{file_id}", status_code=204)
def delete(file_id: int, user: User = Depends(require(Perm.FILE_WRITE)), db: Session = Depends(get_db)) -> Response:
    svc.delete_file(db, user, svc.get_file(db, file_id, user))
    return Response(status_code=204)
