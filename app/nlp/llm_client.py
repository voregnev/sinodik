"""
LLM fallback: OpenAI-compatible API for names that the regex pipeline couldn't parse.
"""

import json
import logging

from config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Ты парсер имён из церковных записок о поминовении. "
    "Извлеки имена из текста. Верни JSON массив объектов: "
    '[{"canonical": "Именительный", "genitive": "Родительный", '
    '"gender": "м или ж", "prefix": "воин/младенец/... или null"}]. '
    "Только JSON, без пояснений."
)


def _is_configured() -> bool:
    return bool(settings.openai_base_url and settings.openai_model and settings.openai_api_key)


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
                confidence=0.8,
            )
            for item in data
        ]
    except Exception as e:
        logger.warning(f"LLM parse failed: {e}")
        return None
