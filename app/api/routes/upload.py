from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_admin
from database import get_db
from models.models import User
from services.order_service import process_csv_upload

router = APIRouter()

# Имена разделителей, чтобы не кодировать символ в URL (?delimiter=semicolon вместо ?delimiter=%3B)
_DELIMITER_ALIASES: dict[str, str] = {
    "semicolon": ";",
    "comma": ",",
    "tab": "\t",
}


def _normalize_delimiter(value: str) -> str:
    """Один символ — как есть; иначе поиск по имени; по умолчанию ';'."""
    if not value:
        return ";"
    if len(value) == 1:
        return value
    return _DELIMITER_ALIASES.get(value.strip().lower(), ";")


@router.post("/upload/csv")
async def upload_csv(
    file: UploadFile = File(...),
    delimiter: str = Query(
        default=";",
        description="Разделитель CSV: один символ или имя: semicolon, comma, tab. Для ';' можно передать delimiter=semicolon без кодирования.",
    ),
    starts_at: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Upload and process a CSV file with commemoration orders.

    Optional starts_at sets the start date for all imported commemorations.
    If omitted, starts_at will be NULL (not yet started).
    """
    delimiter = _normalize_delimiter(delimiter)
    content = await file.read()
    stats = await process_csv_upload(db, content, delimiter=delimiter, starts_at=starts_at)
    return stats
