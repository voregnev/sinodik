"""
Name extraction pipeline v2.

КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: определение падежа по контексту.

Записки пишутся "О здравии КОГО?" → родительный падеж.
Но люди пишут по-разному:
  - "Андрея, Ольги, Тамары"       — родительный (правильно)
  - "Андрей, Ольга, Тамара"       — именительный (тоже бывает)
  - "Андрея, Ольга, Александра"   — смешанный (бывает!)

ПРОБЛЕМА АМБИГУАЛЬНОСТИ:
  "Александра" = род.п.(Александр, м) ИЛИ им.п.(Александра, ж)
  "Евгения"    = род.п.(Евгений, м)  ИЛИ им.п.(Евгения, ж)
  "Валерия"    = род.п.(Валерий, м)  ИЛИ им.п.(Валерия, ж)
  "Серафима"   = род.п.(Серафим, м)  ИЛИ им.п.(Серафима, ж)
  "Валентина"  = род.п.(Валентин, м) ИЛИ им.п.(Валентина, ж)

АЛГОРИТМ:
  1. Извлечь все токены
  2. Для каждого — найти возможные NameEntry из словаря
  3. Определить контекст падежа по неамбигуальным именам:
     - "Андрея" — 100% родительный (нет жен. имени "Андрея")
     - "Андрей" — 100% именительный
  4. По контексту разрешить амбигуальные имена
  5. Если контекст не определён — default: родительный (церковная норма)
"""

import re
from dataclasses import dataclass

from app.nlp.patterns import (
    PREFIX_MAP,
    PREFIX_RE,
    PREFIX_GENDER_HINTS,
    GENDER_MARKERS_FEM,
    GENDER_MARKERS_MASC,
    NAME_DELIMITERS,
    NOISE_PATTERNS,
    VALID_NAME_RE,
)
from app.nlp.names_dict import (
    NameEntry,
    NOM_INDEX,
    GEN_INDEX,
    ANY_FORM_INDEX,
    ALL_NOMINATIVES,
    ALL_GENITIVES,
    AMBIGUOUS,
    lookup_nominative,
    lookup_genitive,
    lookup_any,
    is_ambiguous,
    get_ambiguous_pair,
)


# ═══════════════════════════════════════════════════════════
#  RESULT TYPES
# ═══════════════════════════════════════════════════════════

@dataclass
class ParsedName:
    """Result of parsing a single name."""

    raw: str                    # Исходная форма из текста
    canonical: str              # Именительный падеж (каноническая)
    genitive: str               # Родительный падеж
    gender: str                 # "м" | "ж"
    prefix: str | None = None   # воин, отрок, мл., нп.
    confidence: float = 1.0     # 0..1
    was_ambiguous: bool = False # Была ли неоднозначность


# ═══════════════════════════════════════════════════════════
#  CASE CONTEXT DETECTION
# ═══════════════════════════════════════════════════════════

def _detect_case_context(tokens: list[str]) -> str:
    """
    Определяет падеж контекста по НЕамбигуальным именам.

    Returns:
      "gen"  — родительный (большинство имён в род.п.)
      "nom"  — именительный (большинство в им.п.)
      "unknown" — не удалось определить

    Логика:
      Смотрим на имена, которые ОДНОЗНАЧНО определяются:
      - "Андрея" — есть ТОЛЬКО в GEN_INDEX → голос за "gen"
      - "Андрей" — есть ТОЛЬКО в NOM_INDEX (и нет в GEN как жен) → голос за "nom"
      - "Александра" — амбигуальная → не голосует
    """
    gen_votes = 0
    nom_votes = 0

    for token in tokens:
        cap = token.strip().rstrip(".")
        if not cap:
            continue
        cap = cap[0].upper() + cap[1:].lower() if len(cap) > 1 else cap.upper()

        # Skip ambiguous forms — they don't vote
        if is_ambiguous(cap):
            continue

        # Check: is this token ONLY a genitive form?
        gen_entries = lookup_genitive(cap)
        nom_entry = lookup_nominative(cap)

        if gen_entries and not nom_entry:
            # "Андрея" — only exists as genitive → gen context
            gen_votes += 1
        elif nom_entry and not gen_entries:
            # "Андрей" — only exists as nominative → nom context
            nom_votes += 1
        elif nom_entry and gen_entries:
            # Exists as both (e.g. name that is both nom and gen of different names)
            # Don't count — ambiguous
            pass

    if gen_votes > 0 and nom_votes == 0:
        return "gen"
    elif nom_votes > 0 and gen_votes == 0:
        return "nom"
    elif gen_votes > nom_votes:
        return "gen"
    elif nom_votes > gen_votes:
        return "nom"
    else:
        return "unknown"


# ═══════════════════════════════════════════════════════════
#  RESOLVE SINGLE TOKEN
# ═══════════════════════════════════════════════════════════

def _resolve_token(
    token: str,
    case_context: str,
    gender_hint: str | None = None,
) -> ParsedName | None:
    """
    Разрешает один токен в ParsedName.

    Args:
        token:         слово из текста ("Александра")
        case_context:  "gen" | "nom" | "unknown"
        gender_hint:   "м" | "ж" | None (из префикса или маркера)

    Returns:
        ParsedName or None if not a valid name.
    """
    cap = token[0].upper() + token[1:].lower() if len(token) > 1 else token.upper()

    # ── 1. Check ambiguous case ──
    if is_ambiguous(cap):
        pair = get_ambiguous_pair(cap)

        # Gender hint overrides everything
        if gender_hint == "ж":
            entry = pair["ж"]
            return ParsedName(
                raw=token, canonical=entry.nominative,
                genitive=entry.genitive, gender="ж",
                confidence=0.95, was_ambiguous=True,
            )
        if gender_hint == "м":
            entry = pair["м"]
            return ParsedName(
                raw=token, canonical=entry.nominative,
                genitive=entry.genitive, gender="м",
                confidence=0.95, was_ambiguous=True,
            )

        # Context-based resolution
        if case_context == "gen":
            # "Александра" in genitive context → Александр (м), род.п.
            entry = pair["м"]
            return ParsedName(
                raw=token, canonical=entry.nominative,
                genitive=entry.genitive, gender="м",
                confidence=0.9, was_ambiguous=True,
            )
        elif case_context == "nom":
            # "Александра" in nominative context → Александра (ж), им.п.
            entry = pair["ж"]
            return ParsedName(
                raw=token, canonical=entry.nominative,
                genitive=entry.genitive, gender="ж",
                confidence=0.9, was_ambiguous=True,
            )
        else:
            # Unknown context → default: genitive (church norm)
            # "Александра" → Александр (м)
            entry = pair["м"]
            return ParsedName(
                raw=token, canonical=entry.nominative,
                genitive=entry.genitive, gender="м",
                confidence=0.7, was_ambiguous=True,
            )

    # ── 2. Exact nominative match ──
    nom_entry = lookup_nominative(cap)
    if nom_entry:
        # If context is genitive and this looks like nominative,
        # the person just wrote it in nominative (common)
        return ParsedName(
            raw=token, canonical=nom_entry.nominative,
            genitive=nom_entry.genitive, gender=nom_entry.gender,
            confidence=1.0,
        )

    # ── 3. Genitive match ──
    gen_entries = lookup_genitive(cap)
    if gen_entries:
        # Pick best match based on gender hint
        if gender_hint and len(gen_entries) > 1:
            for e in gen_entries:
                if e.gender == gender_hint:
                    return ParsedName(
                        raw=token, canonical=e.nominative,
                        genitive=e.genitive, gender=e.gender,
                        confidence=0.95,
                    )
        # Take first (usually only one)
        entry = gen_entries[0]
        return ParsedName(
            raw=token, canonical=entry.nominative,
            genitive=entry.genitive, gender=entry.gender,
            confidence=1.0,
        )

    # ── 4. Fallback: heuristic genitive → nominative ──
    if VALID_NAME_RE.match(cap):
        canonical, genitive, gender = _heuristic_normalize(cap)
        return ParsedName(
            raw=token, canonical=canonical,
            genitive=genitive, gender=gender,
            confidence=0.5,
        )

    return None


def _heuristic_normalize(name: str) -> tuple[str, str, str]:
    """
    Heuristic: guess nominative, genitive, and gender
    for names NOT in the dictionary.

    Uses ending patterns:
      -а  → likely female nominative OR male genitive
      -я  → likely female nominative OR male genitive
      -ы  → likely female genitive (→ nominative -а)
      -и  → likely female genitive (-ия → -ия, -ья → -ья)
      consonant → likely male nominative
    """
    # Endings suggesting female genitive (convert to nominative)
    if name.endswith("ы"):
        nom = name[:-1] + "а"
        return nom, name, "ж"
    if name.endswith("ьи"):
        nom = name[:-1] + "я"
        return nom, name, "ж"
    if name.endswith("ии"):
        nom = name[:-2] + "ия"
        return nom, name, "ж"

    # Endings suggesting male genitive
    if name.endswith("а") and len(name) > 3:
        # Could be male gen (Михаила → Михаил) or female nom
        # Default to male gen in church context
        nom = name[:-1]  # strip -а
        return nom, name, "м"
    if name.endswith("я") and len(name) > 3:
        nom = name[:-1] + "й"  # Андрея → Андрей
        return nom, name, "м"

    # Looks like male nominative (consonant ending)
    last = name[-1].lower()
    if last not in "аяоеуюыиьъ":
        # Male nominative; guess genitive by adding -а
        gen = name + "а"
        return name, gen, "м"

    # Default: treat as-is, female
    gen = name[:-1] + "ы" if name.endswith("а") else name
    return name, gen, "ж"


# ═══════════════════════════════════════════════════════════
#  STRIP NOISE
# ═══════════════════════════════════════════════════════════

def strip_noise(text: str) -> str:
    """Remove emails, phones, payment info, etc."""
    for pattern in NOISE_PATTERNS:
        text = pattern.sub("", text)
    return text.strip()


# ═══════════════════════════════════════════════════════════
#  MAIN EXTRACTION FUNCTION
# ═══════════════════════════════════════════════════════════

def extract_names(text: str | None) -> list[ParsedName]:
    """
    Main extraction function.

    Two-pass algorithm:
      Pass 1: tokenize, extract prefixes, collect raw name tokens
      Pass 2: detect case context from unambiguous names,
              then resolve all tokens (including ambiguous ones)

    Input:  "Андрея, Ольги, Александра"
    Output: [ParsedName(canonical="Андрей", gender="м"),
             ParsedName(canonical="Ольга", gender="ж"),
             ParsedName(canonical="Александр", gender="м", was_ambiguous=True)]

    With context: "Андрея" is ONLY genitive → context=gen
    Therefore "Александра" = genitive of Александр (м)
    """
    if not text or not text.strip():
        return []

    cleaned = strip_noise(text)
    if not cleaned:
        return []

    # ── Pass 1: Tokenize + extract prefixes ──

    @dataclass
    class RawToken:
        text: str
        prefix: str | None = None
        gender_hint: str | None = None  # from prefix or (жен.) marker

    raw_tokens: list[RawToken] = []

    chunks = NAME_DELIMITERS.split(cleaned)

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        # Check for gender markers in the chunk: "Александра (жен.)"
        chunk_gender_hint = None
        if GENDER_MARKERS_FEM.search(chunk):
            chunk_gender_hint = "ж"
            chunk = GENDER_MARKERS_FEM.sub("", chunk).strip()
        elif GENDER_MARKERS_MASC.search(chunk):
            chunk_gender_hint = "м"
            chunk = GENDER_MARKERS_MASC.sub("", chunk).strip()

        tokens = chunk.split()
        current_prefix: str | None = None

        i = 0
        while i < len(tokens):
            token = tokens[i].strip().rstrip(".")
            if not token:
                i += 1
                continue

            # Check prefix
            token_lower = token.lower().rstrip(".")
            if token_lower in PREFIX_MAP:
                current_prefix = PREFIX_MAP[token_lower]
                i += 1
                continue

            # Combined prefix+name: "отр.Тимофея"
            prefix_match = PREFIX_RE.match(token)
            if prefix_match:
                pfx_text = prefix_match.group(1).lower().rstrip(".")
                if pfx_text in PREFIX_MAP:
                    current_prefix = PREFIX_MAP[pfx_text]
                    remainder = token[prefix_match.end():].strip()
                    if remainder:
                        token = remainder
                    else:
                        i += 1
                        continue

            clean_token = token.strip().rstrip(".")
            if not clean_token:
                i += 1
                continue

            # Validate: looks like a name?
            cap = clean_token[0].upper() + clean_token[1:].lower() if len(clean_token) > 1 else clean_token.upper()
            entries = lookup_any(cap)

            if entries or VALID_NAME_RE.match(cap):
                # Gender hint from prefix
                pfx_gender = PREFIX_GENDER_HINTS.get(current_prefix) if current_prefix else None
                gender_hint = chunk_gender_hint or pfx_gender

                raw_tokens.append(RawToken(
                    text=clean_token,
                    prefix=current_prefix,
                    gender_hint=gender_hint,
                ))

                # Prefix applies to next name only (except нп.)
                if current_prefix and current_prefix != "новопреставленный":
                    current_prefix = None
            else:
                current_prefix = None

            i += 1

    if not raw_tokens:
        return []

    # ── Pass 2: Detect context + resolve ──

    # Collect all token texts for context detection
    all_token_texts = [t.text for t in raw_tokens]
    case_context = _detect_case_context(all_token_texts)

    # Resolve each token
    results: list[ParsedName] = []

    for rt in raw_tokens:
        parsed = _resolve_token(rt.text, case_context, rt.gender_hint)
        if parsed:
            parsed.prefix = rt.prefix
            results.append(parsed)

    return results


def extract_names_batch(texts: list[str | None]) -> list[list[ParsedName]]:
    """Extract names from a batch of texts."""
    return [extract_names(t) for t in texts]
