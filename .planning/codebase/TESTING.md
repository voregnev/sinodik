# Testing: Sinodic

## Framework

- **pytest** with standard pytest conventions
- Runs inside Docker: `docker compose run --rm api pytest tests/ -v`
- Python 3.14 (matches production)

## Test Files

| File | What it covers |
|------|----------------|
| `tests/test_name_extractor.py` | NLP pipeline — 24+ parametrized cases |
| `tests/test_llm_client.py` | LLM fallback client |
| `tests/test.csv` | Sample CSV fixture |

## Test Organization

Tests are class-based, grouped by concern:

```python
class TestCaseContextDetection:
    @pytest.mark.parametrize("tokens, expected, desc", [...])
    def test_context(self, tokens, expected, desc): ...

class TestFullExtraction:
    def test_single_genitive(self): ...
    def test_prefix_voina(self): ...

class TestEdgeCases:
    def test_empty_input(self): ...
    def test_noise_email_stripped(self): ...
```

## What's Tested

### NLP Pipeline (well-covered)
- Case context detection (`_detect_case_context`) — parametrized with 7 cases
- Full name extraction (`extract_names`) — 14 real CSV data scenarios:
  - Single/multiple genitive names
  - Nominative names
  - Ambiguous names resolved by context
  - Prefix parsing (`воина`, `отр.`, `болящей`, `нпр.`)
  - Explicit gender markers `(жен.)/(муж.)`
  - Mixed genders, comma-separated input
- Edge cases: empty input, None input, noise stripping (email, phone)

### What's Not Tested
- HTTP API routes (no integration tests)
- Order/Commemoration creation pipeline
- DB queries (`query_service.py`)
- CSV parser
- Embedding service

## Test Patterns

**Helper method for concise assertions:**
```python
@staticmethod
def _canonical_pairs(text: str) -> list[tuple[str, str]]:
    return [(r.canonical, r.gender) for r in extract_names(text)]
```

**Assertions check both canonical name and gender:**
```python
assert self._canonical_pairs("Андрея, Ольги") == [("Андрей", "м"), ("Ольга", "ж")]
```

**Checking ParsedName fields directly for prefix/ambiguous tests:**
```python
result = extract_names("воина Николая")
assert result[0].canonical == "Николай"
assert result[0].prefix == "в."
assert result[0].was_ambiguous is True
```

## Running Tests

```bash
# All tests
docker compose run --rm api pytest tests/ -v

# Specific test file
docker compose run --rm api pytest tests/test_name_extractor.py -v

# Specific test class
docker compose run --rm api pytest tests/test_name_extractor.py::TestEdgeCases -v
```

## Coverage Gaps

- No DB/integration tests — only unit tests for pure NLP functions
- No API route tests
- No tests for the dedup logic in `order_service.py`
- No tests for `period_calculator.py`
- No tests for `csv_parser.py`
