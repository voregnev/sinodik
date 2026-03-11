"""
Тест вызова LLM (Timeweb Cloud AI / OpenAI-compatible).

Запуск с переменными из docker-compose:
  docker compose run --rm api pytest tests/test_llm_client.py -v -s

Без SINODIK_OPENAI_* тест пропускается.
"""

import asyncio
import os
import pytest

# чтобы подхватить app.config при pythonpath=["app"]
pytest.importorskip("config")


@pytest.mark.skipif(
    not os.environ.get("SINODIK_OPENAI_BASE_URL") or not os.environ.get("SINODIK_OPENAI_API_KEY"),
    reason="SINODIK_OPENAI_BASE_URL and SINODIK_OPENAI_API_KEY required",
)
def test_llm_parse_names_integration():
    """Реальный запрос к LLM: извлечение имён из короткой строки."""
    from nlp.llm_client import llm_parse_names

    async def run():
        return await llm_parse_names("Василия, Ольги")

    result = asyncio.run(run())
    assert result is not None, "LLM должен вернуть список имён"
    assert len(result) >= 1, "Ожидалось хотя бы одно имя"
    for p in result:
        assert hasattr(p, "canonical") and p.canonical
        assert hasattr(p, "gender") and p.gender in ("м", "ж")
    print("LLM result:", [(p.canonical, p.genitive, p.gender) for p in result])
