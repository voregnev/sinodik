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
    "date":        ["date", "дата", "дата заказа", "ordered_at", "created"],
    "email":       ["email", "e-mail", "почта", "заказчик"],
    "order_type":  ["тип", "type", "тип записки", "тип_записок", "order_type"],
    "period_raw":  ["период", "period", "radio", "срок", "long"],
    "names_raw":   ["комментарий", "comment", "names", "имена", "текст", "commemoration_names"],
}


def _find_col(headers: dict[str, str], field: str) -> str:
    """Find column value by checking known aliases (exact, then prefix match)."""
    aliases = _COL_ALIASES.get(field, [])
    # Exact match first
    for alias in aliases:
        if alias in headers:
            return headers[alias]
    # Prefix match (e.g. "имена" matches "имена_для_поминовения_о_здравии_0")
    for alias in aliases:
        for col in headers:
            if col.startswith(alias):
                return headers[col]
    return ""


def parse_csv(content: bytes, delimiter: str = ";") -> list[CsvRow]:
    text = content.decode("utf-8-sig")

    # Простая авто-детекция разделителя:
    # если по умолчанию ожидаем `;`, но в первой строке только запятые —
    # считаем, что это CSV с запятой.
    effective_delimiter = delimiter
    if delimiter == ";":
        first_line = text.splitlines()[0] if text else ""
        if ";" not in first_line and "," in first_line:
            effective_delimiter = ","

    reader = csv.DictReader(io.StringIO(text), delimiter=effective_delimiter)

    rows: list[CsvRow] = []
    for raw in reader:
        r = {k.strip().lower(): (v.strip() if v else "") for k, v in raw.items()}

        date_str = _find_col(r, "date")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y"):
            try:
                date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue
        else:
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
