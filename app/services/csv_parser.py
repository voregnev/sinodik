"""
CSV parser: raw CSV bytes → list[CsvRow].

Supports various CSV formats from church payment systems.
Column names are normalized to handle different header spellings.
"""

import csv
import io
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CsvRow:
    external_id: str | None
    date: datetime
    email: str | None
    order_type: str
    period_raw: str | None
    names_raw: str


_COL_ALIASES: dict[str, list[str]] = {
    "external_id": ["tranid", "id", "номер", "transaction_id"],
    "date":        ["date", "дата", "дата заказа", "ordered_at"],
    "email":       ["email", "e-mail", "почта", "заказчик"],
    "order_type":  ["тип", "type", "тип записки", "order_type"],
    "period_raw":  ["период", "period", "radio", "срок"],
    "names_raw":   ["комментарий", "comment", "names", "имена", "текст"],
}


def _find_col(headers: dict[str, str], field: str) -> str:
    """Find column value by checking known aliases."""
    for alias in _COL_ALIASES.get(field, []):
        if alias in headers:
            return headers[alias]
    return ""


def parse_csv(content: bytes, delimiter: str = ";") -> list[CsvRow]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    rows: list[CsvRow] = []
    for raw in reader:
        r = {k.strip().lower(): (v.strip() if v else "") for k, v in raw.items()}

        date_str = _find_col(r, "date")
        try:
            date = datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                date = datetime.utcnow()

        names_raw = _find_col(r, "names_raw")
        if not names_raw:
            continue

        rows.append(CsvRow(
            external_id=_find_col(r, "external_id") or None,
            date=date,
            email=_find_col(r, "email") or None,
            order_type=_find_col(r, "order_type") or "здравие",
            period_raw=_find_col(r, "period_raw") or None,
            names_raw=names_raw,
        ))

    return rows
