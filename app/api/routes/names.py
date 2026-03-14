"""
Names endpoints v2: active commemorations today, search, stats, by-user.
"""

from datetime import date
from io import BytesIO
from pathlib import Path
import os

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from database import get_db
from models.models import User
from services.query_service import get_active_today, search_names, get_stats, get_by_user

router = APIRouter()


@router.get("/names/today")
async def names_today(
    order_type: str | None = Query(default=None, description="Filter: здравие | упокоение"),
    target_date: date | None = Query(default=None, description="Дата (default: сегодня)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Все активные поминовения на сегодня.

    Каждая запись = одно имя (Commemoration).
    Группировка по order_type.
    """
    names = await get_active_today(db, order_type=order_type, target_date=target_date)

    grouped = {"здравие": [], "упокоение": []}
    for n in names:
        otype = n["order_type"]
        if otype not in grouped:
            grouped[otype] = []
        grouped[otype].append(n)

    return {
        "date": (target_date or date.today()).isoformat(),
        "total": len(names),
        "groups": grouped,
    }


@router.get("/names/today.pdf")
async def names_today_pdf(
    order_type: str | None = Query(default=None, description="Filter: здравие | упокоение"),
    target_date: date | None = Query(default=None, description="Дата (default: сегодня)"),
    db: AsyncSession = Depends(get_db),
):
    """
    PDF-экспорт всех активных поминовений на сегодня.

    - Отдельная страница для каждого типа: О упокоении / О здравии
    - Внутри страницы блоки по периоду: сорокоуст, годовое, полугодовое (без подзаголовка для разового)
    - В каждом блоке имена сгруппированы по заказам, между заказами тонкая пунктирная линия
    - Внизу каждой страницы маленький номер страницы
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # ── Unicode-шрифт для кириллицы ────────────────────────────────────────
    # В Docker содержимое app смонтировано в /app → шрифты в /app/fonts
    font_path_env = os.getenv("SINODIK_PDF_FONT_PATH")
    _fonts_dirs = [
        Path("/app/fonts"),
        Path(__file__).resolve().parent.parent / "fonts",  # локально: app/fonts
    ]
    font_name_main = "SinodikMain"
    font_name_bold = "SinodikMain-Bold"

    def _register_unicode_font() -> bool:
        candidates: list[Path] = []
        if font_path_env:
            candidates.append(Path(font_path_env))
        for d in _fonts_dirs:
            candidates.append(d / "DejaVuSans.ttf")
            candidates.append(d / "DejaVuSansCondensed.ttf")
        candidates.extend([
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf"),
        ])
        main_font_file = next((p for p in candidates if p.is_file()), None)
        if not main_font_file:
            return False

        pdfmetrics.registerFont(TTFont(font_name_main, str(main_font_file)))

        bold_candidates = [
            main_font_file.with_name("DejaVuSans-Bold.ttf"),
            main_font_file.with_name("DejaVuSansCondensed-Bold.ttf"),
        ]
        for d in _fonts_dirs:
            bold_candidates.append(d / "DejaVuSans-Bold.ttf")
        bold_font_file = next((p for p in bold_candidates if p.is_file()), main_font_file)
        pdfmetrics.registerFont(TTFont(font_name_bold, str(bold_font_file)))
        return True

    has_unicode_font = _register_unicode_font()
    FONT_MAIN = font_name_main if has_unicode_font else "Helvetica"
    FONT_BOLD = font_name_bold if has_unicode_font else "Helvetica-Bold"
    FONT_ITALIC = FONT_MAIN  # упрощённо

    names = await get_active_today(db, order_type=order_type, target_date=target_date)

    current_date = target_date or date.today()
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    margin_left = 20 * mm
    margin_right = 20 * mm
    margin_top = 32 * mm  # место под крест + заголовок 24
    margin_bottom = 15 * mm

    line_height = 24  # полтора интервала (1.5 × 16)
    name_font_size = 20
    prefix_suffix_font_size = 14
    prefix_suffix_gray = 0.45  # бледнее
    small_line_height = 9

    # Колонтитул: православный крест ☦ (ч/б) + заголовок 24 по центру
    HEADER_TITLE_SIZE = 24
    HEADER_CROSS_SIZE = 22

    def draw_header(page_title: str):
        y_top = height - 12 * mm
        # Православный крест сверху, по центру, ч/б
        c.setFont(FONT_MAIN, HEADER_CROSS_SIZE)
        c.setFillColor(colors.black)
        c.drawCentredString(width / 2, y_top, "☦")
        # Заголовок крупно 24 по центру
        c.setFont(FONT_BOLD, HEADER_TITLE_SIZE)
        c.drawCentredString(width / 2, y_top - HEADER_TITLE_SIZE - 4, page_title)

    def draw_footer(page_num: int):
        """Подвал: дата и номер страницы мелко."""
        c.setFont(FONT_MAIN, 8)
        c.setFillColor(colors.grey)
        date_str = current_date.strftime("%d.%m.%Y")
        c.drawCentredString(width / 2, margin_bottom / 2 + 6, date_str)
        c.drawCentredString(width / 2, margin_bottom / 2 - 4, str(page_num))
        c.setFillColor(colors.black)

    page_number = 1

    type_titles = {
        "упокоение": "О упокоении",
        "здравие": "О здравии",
    }

    # Порядок страниц: здравие, потом упокоение
    type_order = ["здравие", "упокоение"]

    # Группируем данные по типу
    by_type: dict[str, list[dict]] = {"здравие": [], "упокоение": []}
    for n in names:
        t = n["order_type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(n)

    for t in type_order:
        records = by_type.get(t) or []
        if not records:
            continue

        # Новая страница для каждого типа
        draw_header(type_titles.get(t, t))

        y = height - margin_top - 50  # под крест и заголовок 24

        # Группировка: период → order_id → список имён
        periods_order = ["сорокоуст", "год", "полгода", "разовое"]
        # Подзаголовки периода — светло-серые тонкие линии (--, ----, -----, ------)
        period_labels = {
            "разовое": "--",
            "сорокоуст": "----",
            "полгода": "------",
            "год": "-----",
        }
        period_label_gray = 0.7  # светло-серый

        period_groups: dict[str, dict] = {}
        for r in records:
            p = r["period_type"]
            period_groups.setdefault(p, {})
            order_id = r.get("order_id") or 0
            period_groups[p].setdefault(order_id, {"user_email": r.get("user_email"), "items": []})
            period_groups[p][order_id]["items"].append(r)

        for p in periods_order:
            orders_for_period = period_groups.get(p)
            if not orders_for_period:
                continue

            # Подзаголовок периода (светло-серый, тонко)
            label = period_labels.get(p, "")
            if label:
                if y < margin_bottom + 3 * line_height:
                    draw_footer(page_number)
                    c.showPage()
                    page_number += 1
                    draw_header(type_titles.get(t, t))
                    y = height - margin_top - 50
                c.setFont(FONT_MAIN, 10)
                c.setFillColor(colors.Color(period_label_gray, period_label_gray, period_label_gray))
                c.drawCentredString(width / 2, y, label)
                c.setFillColor(colors.black)
                y -= line_height

            # Заказы внутри периода (без email)
            for order_id, data in orders_for_period.items():
                if y < margin_bottom + 4 * line_height:
                    draw_footer(page_number)
                    c.showPage()
                    page_number += 1
                    draw_header(type_titles.get(t, t))
                    y = height - margin_top - 50

                # Имена: центр, имя 20, префикс/суффикс 14 бледнее
                c.setFont(FONT_MAIN, name_font_size)
                for item in data["items"]:
                    if y < margin_bottom + 2 * line_height:
                        draw_footer(page_number)
                        c.showPage()
                        page_number += 1
                        draw_header(type_titles.get(t, t))
                        y = height - margin_top - 50
                        c.setFont(FONT_MAIN, name_font_size)

                    prefix = (item.get("prefix") or "").strip()
                    name = (item.get("genitive_name") or item.get("canonical_name") or "").strip()
                    suffix = (item.get("suffix") or "").strip()

                    # Ширины для центрирования
                    c.setFont(FONT_MAIN, prefix_suffix_font_size)
                    w_prefix = c.stringWidth(prefix, FONT_MAIN, prefix_suffix_font_size) if prefix else 0
                    c.setFont(FONT_MAIN, name_font_size)
                    w_name = c.stringWidth(name, FONT_MAIN, name_font_size) if name else 0
                    c.setFont(FONT_MAIN, prefix_suffix_font_size)
                    w_suffix = c.stringWidth(suffix, FONT_MAIN, prefix_suffix_font_size) if suffix else 0
                    gap = 4
                    total_w = w_prefix + (gap if prefix and name else 0) + w_name + (gap if name and suffix else 0) + w_suffix
                    x_start = (width - total_w) / 2

                    c.setFillColor(colors.Color(prefix_suffix_gray, prefix_suffix_gray, prefix_suffix_gray))
                    c.setFont(FONT_MAIN, prefix_suffix_font_size)
                    if prefix:
                        c.drawString(x_start, y, prefix)
                        x_start += w_prefix + gap
                    c.setFillColor(colors.black)
                    c.setFont(FONT_MAIN, name_font_size)
                    if name:
                        c.drawString(x_start, y, name)
                        x_start += w_name + gap
                    c.setFillColor(colors.Color(prefix_suffix_gray, prefix_suffix_gray, prefix_suffix_gray))
                    c.setFont(FONT_MAIN, prefix_suffix_font_size)
                    if suffix:
                        c.drawString(x_start, y, suffix)
                    c.setFillColor(colors.black)

                    y -= line_height

                # Пунктирная линия между заказами
                if y < margin_bottom + 2 * line_height:
                    draw_footer(page_number)
                    c.showPage()
                    page_number += 1
                    draw_header(type_titles.get(t, t))
                    y = height - margin_top - 50

                c.setStrokeColor(colors.lightgrey)
                c.setLineWidth(0.3)
                c.setDash(1, 2)
                c.line(margin_left, y, width - margin_right, y)
                c.setDash()  # сброс
                c.setStrokeColor(colors.black)
                y -= small_line_height

        # Номер страницы и переход к следующей (если ещё будут типы)
        draw_footer(page_number)
        if t != type_order[-1]:
            c.showPage()
            page_number += 1

    c.save()
    pdf_bytes = buf.getvalue()
    buf.close()

    filename = f"sinodik-{current_date.isoformat()}.pdf"
    headers = {
        "Content-Disposition": f'inline; filename="{filename}"',
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@router.get("/names/search")
async def names_search(
    q: str = Query(..., min_length=1, description="Поисковый запрос"),
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Fuzzy-поиск по справочнику имён."""
    results = await search_names(db, query=q, limit=limit)
    return {"query": q, "results": results, "count": len(results)}


@router.get("/names/stats")
async def names_stats(db: AsyncSession = Depends(get_db)):
    """Статистика: всего имён, записок, активных сегодня."""
    return await get_stats(db)


@router.get("/names/by-user")
async def names_by_user(
    current_user: User = Depends(get_current_user),
    email: str | None = Query(default=None, description="Email заказчика (только для admin)"),
    active_only: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
):
    """Все поминовения пользователя. Обычный пользователь видит только свои; admin может передать ?email= для другого."""
    if current_user.role == "admin" and email is not None:
        effective_email = email
    else:
        effective_email = current_user.email
    results = await get_by_user(db, user_email=effective_email, active_only=active_only)
    return {"user_email": effective_email, "commemorations": results, "count": len(results)}
