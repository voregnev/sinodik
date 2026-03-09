"""
LLM fallback: Claude Haiku for names that the regex pipeline couldn't parse.
"""

import json
import logging

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Ты парсер имён из церковных записок о поминовении. "
    "Извлеки имена из текста. Верни JSON массив объектов: "
    '[{"canonical": "Именительный", "genitive": "Родительный", '
    '"gender": "м или ж", "prefix": "воин/младенец/... или null"}]. '
    "Только JSON, без пояснений."
)


async def llm_parse_names(text: str):
    """
    Parse names using Claude Haiku as a fallback.

    Returns list[ParsedName] or None if LLM is unavailable.
    Import ParsedName lazily to avoid circular imports.
    """
    try:
        from anthropic import AsyncAnthropic
        from app.config import settings

        if not settings.anthropic_api_key:
            return None

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)

        response = await client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
        )

        data = json.loads(response.content[0].text)

        from app.nlp.name_extractor import ParsedName
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
