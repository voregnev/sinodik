"""
Tests for the name extraction pipeline.

Based on verified test cases (all 14 passed) from test.sh.
"""

import pytest
from app.nlp.name_extractor import extract_names, _detect_case_context, ParsedName


# ═══════════════════════════════════════════════════════════
#  CASE CONTEXT DETECTION
# ═══════════════════════════════════════════════════════════

class TestCaseContextDetection:
    @pytest.mark.parametrize("tokens, expected, desc", [
        (["Андрея", "Ольги", "Тамары"],    "gen",     "все в род.п."),
        (["Андрей", "Ольга", "Тамара"],     "nom",     "все в им.п."),
        (["Андрея", "Ольги", "Александра"], "gen",     "контекст род.п. → Александра=м"),
        (["Андрей", "Ольга", "Александра"], "nom",     "контекст им.п. → Александра=ж"),
        (["Александра", "Евгения"],          "unknown", "оба амбигуальные → unknown"),
        (["Михаила", "Александра"],          "gen",     "Михаила=gen → context gen"),
        (["Михаил", "Александра"],           "nom",     "Михаил=nom → context nom"),
    ])
    def test_context(self, tokens, expected, desc):
        assert _detect_case_context(tokens) == expected, desc


# ═══════════════════════════════════════════════════════════
#  FULL EXTRACTION — REAL CSV DATA
# ═══════════════════════════════════════════════════════════

class TestFullExtraction:

    @staticmethod
    def _canonical_pairs(text: str) -> list[tuple[str, str]]:
        return [(r.canonical, r.gender) for r in extract_names(text)]

    # ── Basic cases ───────────────────────────────────────

    def test_single_genitive(self):
        assert self._canonical_pairs("Тамары") == [("Тамара", "ж")]

    def test_three_genitive(self):
        assert self._canonical_pairs("Андрея, Ольги, Тамары") == [
            ("Андрей", "м"), ("Ольга", "ж"), ("Тамара", "ж"),
        ]

    def test_three_nominative(self):
        assert self._canonical_pairs("Андрей, Ольга, Тамара") == [
            ("Андрей", "м"), ("Ольга", "ж"), ("Тамара", "ж"),
        ]

    # ── Ambiguous names resolved by context ───────────────

    def test_aleksandra_genitive_context(self):
        """Александра + genitive context → Александр (м)."""
        result = extract_names("Андрея, Ольги, Александра")
        pairs = [(r.canonical, r.gender) for r in result]
        assert pairs == [("Андрей", "м"), ("Ольга", "ж"), ("Александр", "м")]
        assert result[2].was_ambiguous is True

    def test_aleksandra_nominative_context(self):
        """Александра + nominative context → Александра (ж)."""
        result = extract_names("Андрей, Ольга, Александра")
        pairs = [(r.canonical, r.gender) for r in result]
        assert pairs == [("Андрей", "м"), ("Ольга", "ж"), ("Александра", "ж")]
        assert result[2].was_ambiguous is True

    def test_all_ambiguous_genitive_context(self):
        """Михаила, Евгения, Валерия — gen context → все мужские."""
        assert self._canonical_pairs("Михаила, Евгения, Валерия") == [
            ("Михаил", "м"), ("Евгений", "м"), ("Валерий", "м"),
        ]

    def test_ambiguous_nominative_context(self):
        """Михаил, Евгения, Валерия — nom context → женские."""
        assert self._canonical_pairs("Михаил, Евгения, Валерия") == [
            ("Михаил", "м"), ("Евгения", "ж"), ("Валерия", "ж"),
        ]

    # ── Prefixes ──────────────────────────────────────────

    def test_prefix_voina(self):
        result = extract_names("воина Николая")
        assert len(result) == 1
        assert result[0].canonical == "Николай"
        assert result[0].prefix == "воин"

    def test_mixed_with_prefix_otrok(self):
        """Ангелины Анны Елисаветы отр.Тимофея — gen context, prefix отрок."""
        result = extract_names("Ангелины Анны Елисаветы  отр.Тимофея")
        pairs = [(r.canonical, r.gender) for r in result]
        assert pairs == [
            ("Ангелина", "ж"), ("Анна", "ж"), ("Елисавета", "ж"), ("Тимофей", "м"),
        ]
        assert result[3].prefix == "отрок"

    def test_prefix_bolyashchey(self):
        """болящей Евгении — prefix hint → женский."""
        result = extract_names("болящей Евгении")
        assert len(result) == 1
        assert result[0].canonical == "Евгения"
        assert result[0].gender == "ж"

    # ── Explicit gender marker ────────────────────────────

    def test_explicit_gender_marker(self):
        """Александра (жен.) — gender marker overrides default."""
        result = extract_names("Александра (жен.)")
        assert len(result) == 1
        assert result[0].canonical == "Александра"
        assert result[0].gender == "ж"
        assert result[0].was_ambiguous is True

    # ── Mixed genders ─────────────────────────────────────

    def test_mixed_genders_genitive(self):
        assert self._canonical_pairs("Людмилы Геннадия Ирины") == [
            ("Людмила", "ж"), ("Геннадий", "м"), ("Ирина", "ж"),
        ]

    def test_mixed_genders_genitive_church(self):
        assert self._canonical_pairs("Олега Иоанна Параскевы Нины") == [
            ("Олег", "м"), ("Иоанн", "м"), ("Параскева", "ж"), ("Нина", "ж"),
        ]

    def test_comma_separated_genitive(self):
        assert self._canonical_pairs("Сергия, Тамары, Ксении, Ольги, Веры.") == [
            ("Сергий", "м"), ("Тамара", "ж"), ("Ксения", "ж"),
            ("Ольга", "ж"), ("Вера", "ж"),
        ]


# ═══════════════════════════════════════════════════════════
#  EDGE CASES
# ═══════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_input(self):
        assert extract_names("") == []
        assert extract_names(None) == []
        assert extract_names("   ") == []

    def test_noise_email_stripped(self):
        result = extract_names("Андрея test@example.com Ольги")
        names = [r.canonical for r in result]
        assert "Андрей" in names
        assert "Ольга" in names

    def test_noise_phone_stripped(self):
        result = extract_names("Андрея +7 999 123 4567")
        assert len(result) == 1
        assert result[0].canonical == "Андрей"
