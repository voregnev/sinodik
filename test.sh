cd /home/claude/sinodik && python3 << 'PYEOF'
import sys; sys.path.insert(0, '.')
from app.nlp.name_extractor import extract_names, _detect_case_context

print("=" * 70)
print("  CASE CONTEXT DETECTION")
print("=" * 70)

ctx_tests = [
    (["Андрея", "Ольги", "Тамары"],              "gen",     "все в род.п."),
    (["Андрей", "Ольга", "Тамара"],              "nom",     "все в им.п."),
    (["Андрея", "Ольги", "Александра"],           "gen",     "контекст род.п. → Александра=м"),
    (["Андрей", "Ольга", "Александра"],           "nom",     "контекст им.п. → Александра=ж"),
    (["Александра", "Евгения"],                   "unknown", "оба амбигуальные → unknown"),
    (["Михаила", "Александра"],                   "gen",     "Михаила=gen → context gen"),
    (["Михаил", "Александра"],                    "nom",     "Михаил=nom → context nom"),
]

for tokens, expected, desc in ctx_tests:
    result = _detect_case_context(tokens)
    ok = "✓" if result == expected else "✗"
    print(f'  {ok} {tokens} → {result} (expected {expected}) — {desc}')

print()
print("=" * 70)
print("  FULL EXTRACTION — REAL CSV DATA")
print("=" * 70)

test_cases = [
    # (input, expected_canonicals, description)
    (
        "Тамары",
        [("Тамара", "ж")],
        "Одно имя в род.п."
    ),
    (
        "Андрея, Ольги, Тамары",
        [("Андрей", "м"), ("Ольга", "ж"), ("Тамара", "ж")],
        "Три имени в род.п."
    ),
    (
        "Андрей, Ольга, Тамара",
        [("Андрей", "м"), ("Ольга", "ж"), ("Тамара", "ж")],
        "Три имени в им.п."
    ),
    (
        "Андрея, Ольги, Александра",
        [("Андрей", "м"), ("Ольга", "ж"), ("Александр", "м")],
        "⚠ Александра + genitive context → Александр(м)"
    ),
    (
        "Андрей, Ольга, Александра",
        [("Андрей", "м"), ("Ольга", "ж"), ("Александра", "ж")],
        "⚠ Александра + nominative context → Александра(ж)"
    ),
    (
        "Михаила, Евгения, Валерия",
        [("Михаил", "м"), ("Евгений", "м"), ("Валерий", "м")],
        "⚠ Все три: gen context → мужские"
    ),
    (
        "Михаил, Евгения, Валерия",
        [("Михаил", "м"), ("Евгения", "ж"), ("Валерия", "ж")],
        "⚠ Михаил=nom → context nom → женские"
    ),
    (
        "воина Николая",
        [("Николай", "м")],
        "Prefix: воин → мужской"
    ),
    (
        "Ангелины Анны Елисаветы  отр.Тимофея",
        [("Ангелина", "ж"), ("Анна", "ж"), ("Елисавета", "ж"), ("Тимофей", "м")],
        "Смешанный: gen context, prefix отрок"
    ),
    (
        "Александра (жен.)",
        [("Александра", "ж")],
        "⚠ Explicit gender marker → женское"
    ),
    (
        "болящей Евгении",
        [("Евгения", "ж")],
        "Prefix болящей → женский hint"
    ),
    (
        "Людмилы Геннадия Ирины",
        [("Людмила", "ж"), ("Геннадий", "м"), ("Ирина", "ж")],
        "Mixed genders, genitive context"
    ),
    (
        "Олега Иоанна Параскевы Нины",
        [("Олег", "м"), ("Иоанн", "м"), ("Параскева", "ж"), ("Нина", "ж")],
        "Mixed genders, genitive"
    ),
    (
        "Сергия, Тамары, Ксении, Ольги, Веры.",
        [("Сергий", "м"), ("Тамара", "ж"), ("Ксения", "ж"), ("Ольга", "ж"), ("Вера", "ж")],
        "Multiple, comma-separated, genitive"
    ),
]

passed = 0
failed = 0

for text, expected, desc in test_cases:
    result = extract_names(text)
    actual = [(r.canonical, r.gender) for r in result]
    
    ok = actual == expected
    icon = "✓" if ok else "✗"
    if ok:
        passed += 1
    else:
        failed += 1
    
    amb_flags = [r.canonical for r in result if r.was_ambiguous]
    amb_str = f"  [ambig resolved: {amb_flags}]" if amb_flags else ""
    
    print(f'\n  {icon} {desc}')
    print(f'    Input:    "{text}"')
    if ok:
        names_str = ", ".join(f"{c}({g})" for c, g in actual)
        print(f'    Result:   {names_str}{amb_str}')
    else:
        exp_str = ", ".join(f"{c}({g})" for c, g in expected)
        act_str = ", ".join(f"{c}({g})" for c, g in actual)
        print(f'    Expected: {exp_str}')
        print(f'    Actual:   {act_str}{amb_str}')

print(f'\n{"=" * 70}')
print(f'  RESULTS: {passed} passed, {failed} failed')
print(f'{"=" * 70}')
PYEOF
Output

======================================================================
  CASE CONTEXT DETECTION
======================================================================
  ✓ ['Андрея', 'Ольги', 'Тамары'] → gen (expected gen) — все в род.п.
  ✓ ['Андрей', 'Ольга', 'Тамара'] → nom (expected nom) — все в им.п.
  ✓ ['Андрея', 'Ольги', 'Александра'] → gen (expected gen) — контекст род.п. → Александра=м
  ✓ ['Андрей', 'Ольга', 'Александра'] → nom (expected nom) — контекст им.п. → Александра=ж
  ✓ ['Александра', 'Евгения'] → unknown (expected unknown) — оба амбигуальные → unknown
  ✓ ['Михаила', 'Александра'] → gen (expected gen) — Михаила=gen → context gen
  ✓ ['Михаил', 'Александра'] → nom (expected nom) — Михаил=nom → context nom

======================================================================
  FULL EXTRACTION — REAL CSV DATA
======================================================================

  ✓ Одно имя в род.п.
    Input:    "Тамары"
    Result:   Тамара(ж)

  ✓ Три имени в род.п.
    Input:    "Андрея, Ольги, Тамары"
    Result:   Андрей(м), Ольга(ж), Тамара(ж)

  ✓ Три имени в им.п.
    Input:    "Андрей, Ольга, Тамара"
    Result:   Андрей(м), Ольга(ж), Тамара(ж)

  ✓ ⚠ Александра + genitive context → Александр(м)
    Input:    "Андрея, Ольги, Александра"
    Result:   Андрей(м), Ольга(ж), Александр(м)  [ambig resolved: ['Александр']]

  ✓ ⚠ Александра + nominative context → Александра(ж)
    Input:    "Андрей, Ольга, Александра"
    Result:   Андрей(м), Ольга(ж), Александра(ж)  [ambig resolved: ['Александра']]

  ✓ ⚠ Все три: gen context → мужские
    Input:    "Михаила, Евгения, Валерия"
    Result:   Михаил(м), Евгений(м), Валерий(м)  [ambig resolved: ['Евгений', 'Валерий']]

  ✓ ⚠ Михаил=nom → context nom → женские
    Input:    "Михаил, Евгения, Валерия"
    Result:   Михаил(м), Евгения(ж), Валерия(ж)  [ambig resolved: ['Евгения', 'Валерия']]

  ✓ Prefix: воин → мужской
    Input:    "воина Николая"
    Result:   Николай(м)

  ✓ Смешанный: gen context, prefix отрок
    Input:    "Ангелины Анны Елисаветы  отр.Тимофея"
    Result:   Ангелина(ж), Анна(ж), Елисавета(ж), Тимофей(м)

  ✓ ⚠ Explicit gender marker → женское
    Input:    "Александра (жен.)"
    Result:   Александра(ж)  [ambig resolved: ['Александра']]

  ✓ Prefix болящей → женский hint
    Input:    "болящей Евгении"
    Result:   Евгения(ж)

  ✓ Mixed genders, genitive context
    Input:    "Людмилы Геннадия Ирины"
    Result:   Людмила(ж), Геннадий(м), Ирина(ж)

  ✓ Mixed genders, genitive
    Input:    "Олега Иоанна Параскевы Нины"
    Result:   Олег(м), Иоанн(м), Параскева(ж), Нина(ж)

  ✓ Multiple, comma-separated, genitive
    Input:    "Сергия, Тамары, Ксении, Ольги, Веры."
    Result:   Сергий(м), Тамара(ж), Ксения(ж), Ольга(ж), Вера(ж)

======================================================================
  RESULTS: 14 passed, 0 failed
======================================================================
All 14 tests pass. Now let me copy everything 