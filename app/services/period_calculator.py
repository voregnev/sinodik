"""
Period & date calculation module.

Отдельная функция вычисления expires_at:
  starts_at + period → expires_at

Типы периодов:
  разовое    → +1 день
  сорокоуст  → +40 дней
  полгода    → +182 дня
  год        → +365 дней
"""

from datetime import datetime, timedelta


# ─── Period definitions ────────────────────────────────────

PERIOD_DAYS: dict[str, int] = {
    "разовое":    1,
    "сорокоуст":  40,
    "полгода":    182,
    "год":        365,
}

DEFAULT_PERIOD = "разовое"

# ─── Raw label → normalized period type ───────────────────

_RAW_TO_PERIOD: dict[str, str] = {
    "разовое (не выбрано)": "разовое",
    "разовое":              "разовое",
    "сорокоуст (40 дней)":  "сорокоуст",
    "сорокоуст":            "сорокоуст",
    "на полгода":           "полгода",
    "полгода":              "полгода",
    "на год":               "год",
    "год":                  "год",
}


# ═══════════════════════════════════════════════════════════
#  MAIN FUNCTION: вычисление даты окончания
# ═══════════════════════════════════════════════════════════

def calculate_expires_at(starts_at: datetime, period_type: str) -> datetime:
    """
    Вычисляет дату окончания поминовения.

    Args:
        starts_at:    дата начала чтения
        period_type:  нормализованный тип периода

    Returns:
        datetime: дата окончания (starts_at + N дней)

    Examples:
        >>> calculate_expires_at(datetime(2026, 3, 1), "сорокоуст")
        datetime(2026, 4, 10, ...)   # +40 дней

        >>> calculate_expires_at(datetime(2026, 1, 1), "год")
        datetime(2027, 1, 1, ...)    # +365 дней
    """
    days = PERIOD_DAYS.get(period_type, PERIOD_DAYS[DEFAULT_PERIOD])
    return starts_at + timedelta(days=days)


# ═══════════════════════════════════════════════════════════
#  HELPERS: нормализация сырых значений из CSV/формы
# ═══════════════════════════════════════════════════════════

def normalize_period_type(raw: str | None) -> str:
    """
    Нормализует сырое значение Radio поля из CSV.

    "Сорокоуст (40 дней)" → "сорокоуст"
    "На полгода"          → "полгода"
    None / ""             → "разовое"
    """
    if not raw or not raw.strip():
        return DEFAULT_PERIOD

    key = raw.strip().lower()
    return _RAW_TO_PERIOD.get(key, DEFAULT_PERIOD)


def normalize_order_type(raw: str | None) -> str:
    """
    Нормализует тип записки.

    "О здравии"    → "здравие"
    "Об упокоении" → "упокоение"
    """
    if not raw:
        return "здравие"
    low = raw.strip().lower()
    if "упокоен" in low:
        return "упокоение"
    return "здравие"


def get_period_days(period_type: str) -> int:
    """Возвращает количество дней для данного типа периода."""
    return PERIOD_DAYS.get(period_type, PERIOD_DAYS[DEFAULT_PERIOD])
