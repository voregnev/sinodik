"""
Names endpoints v2: active commemorations today, search, stats, by-user.
"""

from datetime import date
from io import BytesIO
from pathlib import Path
import os

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
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
    margin_top = 25 * mm
    margin_bottom = 15 * mm

    line_height = 10  # pt
    small_line_height = 9

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

    def draw_header(page_title: str):
        c.setFont(FONT_BOLD, 16)
        c.drawCentredString(width / 2, height - margin_top, page_title)
        c.setFont(FONT_MAIN, 9)
        c.drawCentredString(
            width / 2,
            height - margin_top - 14,
            current_date.strftime("%d.%m.%Y"),
        )

    def draw_page_number(num: int):
        c.setFont(FONT_MAIN, 8)
        c.setFillColor(colors.grey)
        c.drawCentredString(width / 2, margin_bottom / 2, str(num))
        c.setFillColor(colors.black)

    for t in type_order:
        records = by_type.get(t) or []
        if not records:
            continue

        # Новая страница для каждого типа
        draw_header(type_titles.get(t, t))

        y = height - margin_top - 30

        # Группировка: период → order_id → список имён
        periods_order = ["сорокоуст", "год", "полгода", "разовое"]
        period_labels = {
            "сорокоуст": "сорокоуст",
            "год": "годовое",
            "полгода": "полугодовое",
        }

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

            # Подзаголовок периода (кроме разового)
            label = period_labels.get(p)
            if label:
                if y < margin_bottom + 3 * line_height:
                    draw_page_number(page_number)
                    c.showPage()
                    page_number += 1
                    draw_header(type_titles.get(t, t))
                    y = height - margin_top - 30
                c.setFont(FONT_BOLD, 11)
                c.drawString(margin_left, y, label)
                y -= line_height

            # Заказы внутри периода
            for order_id, data in orders_for_period.items():
                if y < margin_bottom + 4 * line_height:
                    draw_page_number(page_number)
                    c.showPage()
                    page_number += 1
                    draw_header(type_titles.get(t, t))
                    y = height - margin_top - 30

                # Имя/почта заказчика мелким шрифтом
                user_label = data["user_email"] or ""
                if user_label:
                    c.setFont(FONT_ITALIC, 8)
                    c.setFillColor(colors.grey)
                    c.drawString(margin_left, y, user_label)
                    c.setFillColor(colors.black)
                    y -= small_line_height

                # Сами имена
                c.setFont(FONT_MAIN, 10)
                for item in data["items"]:
                    if y < margin_bottom + 2 * line_height:
                        draw_page_number(page_number)
                        c.showPage()
                        page_number += 1
                        draw_header(type_titles.get(t, t))
                        y = height - margin_top - 30
                        c.setFont(FONT_MAIN, 10)

                    parts = []
                    if item.get("prefix"):
                        parts.append(item["prefix"])
                    name = item.get("genitive_name") or item.get("canonical_name") or ""
                    if name:
                        parts.append(name)
                    if item.get("suffix"):
                        parts.append(item["suffix"])
                    line = " ".join(parts)
                    c.drawString(margin_left, y, line)
                    y -= line_height

                # Пунктирная линия между заказами
                if y < margin_bottom + 2 * line_height:
                    draw_page_number(page_number)
                    c.showPage()
                    page_number += 1
                    draw_header(type_titles.get(t, t))
                    y = height - margin_top - 30

                c.setStrokeColor(colors.lightgrey)
                c.setLineWidth(0.3)
                c.setDash(1, 2)
                c.line(margin_left, y, width - margin_right, y)
                c.setDash()  # сброс
                c.setStrokeColor(colors.black)
                y -= small_line_height

        # Номер страницы и переход к следующей (если ещё будут типы)
        draw_page_number(page_number)
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
    email: str = Query(..., description="Email заказчика"),
    active_only: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
):
    """Все поминовения конкретного пользователя (по email)."""
    results = await get_by_user(db, user_email=email, active_only=active_only)
    return {"user_email": email, "commemorations": results, "count": len(results)}
