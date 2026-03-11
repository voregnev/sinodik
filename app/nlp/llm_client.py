"""
LLM fallback: OpenAI-compatible API for names that the regex pipeline couldn't parse.
"""

import json
import logging

from config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Ты парсер имён из церковных записок о поминовении. "
    "Извлеки ТОЛЬКО имена из списка поминовения. "
    "Список имён часто заканчивается точкой после последнего имени; после неё может идти комментарий "
    "(например «Оплатила с карты...», «Напишите...», «С Праздником!») — имена из комментария НЕ извлекай "
    "(плательщик, подпись и т.п. не для поминовения). "
    "Маркер «р.Б.» (раба Божья/раба Божьего) означает, что дальше идёт имя поминовения; после «р.Б. Имя.» может начинаться комментарий.\n\n"
    "Суффикс — только «со чадом» или «со чады» после имени; если есть, верни в поле suffix, иначе null. "
    "Маркеры пола «(муж.)»/«(жен.)» или «(м)»/«(ж)» влияют на определение пола имени — ставь в gender «м» или «ж», в suffix их не пиши. "
    "Префиксы в начале имени: воин (в.), младенец (мл.), отрок (отр.), нпр., болящий (б.), р.Б. и т.д. — в prefix.\n\n"
    "Верни JSON массив объектов: "
    '[{"canonical": "Именительный", "genitive": "Родительный", '
    '"gender": "м или ж", "prefix": "в./мл./отр./нпр./б./р.Б. или null", '
    '"suffix": "со чадом или со чады или null"}]. '
    "Только JSON, без пояснений."
)


def _is_configured() -> bool:
    return bool(settings.openai_base_url and settings.openai_model and settings.openai_api_key)


def _openai_headers() -> dict[str, str]:
    """Заголовки для OpenAI-совместимого API. Timeweb Cloud AI требует x-proxy-source (см. https://agent.timeweb.cloud/docs)."""
    headers: dict[str, str] = {}
    if "timeweb.cloud" in (settings.openai_base_url or ""):
        headers["x-proxy-source"] = getattr(settings, "openai_x_proxy_source", "") or ""
    return headers


async def llm_parse_names(text: str):
    """
    Parse names using an OpenAI-compatible API as a fallback.

    Returns list[ParsedName] or None if LLM is unavailable.
    """
    if not _is_configured():
        return None

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            default_headers=_openai_headers(),
        )

        response = await client.chat.completions.create(
            model=settings.openai_model,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )

        data = json.loads(response.choices[0].message.content)

        from nlp.name_extractor import ParsedName
        return [
            ParsedName(
                raw=item.get("canonical", ""),
                canonical=item["canonical"],
                genitive=item.get("genitive", item["canonical"]),
                gender=item.get("gender", "м"),
                prefix=item.get("prefix"),
                suffix=item.get("suffix"),
                confidence=0.8,
            )
            for item in data
        ]
    except Exception as e:
        logger.warning(f"LLM parse failed: {e}")
        return None
