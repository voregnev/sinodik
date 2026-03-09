from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.order_service import process_csv_upload

router = APIRouter()


@router.post("/upload/csv")
async def upload_csv(
    file: UploadFile = File(...),
    delimiter: str = Query(default=";"),
    db: AsyncSession = Depends(get_db),
):
    """Upload and process a CSV file with commemoration orders."""
    content = await file.read()
    stats = await process_csv_upload(db, content, delimiter=delimiter)
    return stats
