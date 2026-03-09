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
  3. Определить контекст падежа по неамбигуальным именам
  4. По контексту разрешить амбигуальные имена
  5. Если контекст не определён — default: родительный (церковная норма)

ПРЕФИКСЫ:
  Два разных префикса могут идти подряд: "иер. уб. Николая"
  → prefix = "иер. уб."

ПОСТФИКСЫ:
  "со чадом" / "со чады" — сохраняются в ParsedName.suffix.
  Остальные нераспознанные токены тихо отбрасываются.
"""

import re
from dataclasses import dataclass

from app.nlp.patterns import (
    PREFIX_MAP,
    PREFIX_RE,
    PREFIX_GENDER_HINTS,
    SUFFIX_RE,
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
    prefix: str | None = None   # в., нпр., иер. уб. и т.д.
    suffix: str | None = None   # со чадом / со чады
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
    """
    gen_votes = 0
    nom_votes = 0

    for token in tokens:
        cap = token.strip().rstrip(".")
        if not cap:
            continue
        cap = cap[0].upper() + cap[1:].lower() if len(cap) > 1 else cap.upper()

        if is_ambiguous(cap):
            continue

        gen_entries = lookup_genitive(cap)
        nom_entry = lookup_nominative(cap)

        if gen_entries and not nom_entry:
            gen_votes += 1
        elif nom_entry and not gen_entries:
            nom_votes += 1

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
) -> "ParsedName | None":
    """
    Разрешает один токен в ParsedName.
    Returns ParsedName or None if not a valid name.
    """
    cap = token[0].upper() + token[1:].lower() if len(token) > 1 else token.upper()

    # ── 1. Check ambiguous case ──
    if is_ambiguous(cap):
        pair = get_ambiguous_pair(cap)

        if gender_hint == "ж":
            entry = pair["ж"]
            return ParsedName(raw=token, canonical=entry.nominative,
                              genitive=entry.genitive, gender="ж",
                              confidence=0.95, was_ambiguous=True)
        if gender_hint == "м":
            entry = pair["м"]
            return ParsedName(raw=token, canonical=entry.nominative,
                              genitive=entry.genitive, gender="м",
                              confidence=0.95, was_ambiguous=True)

        if case_context == "gen":
            entry = pair["м"]
            return ParsedName(raw=token, canonical=entry.nominative,
                              genitive=entry.genitive, gender="м",
                              confidence=0.9, was_ambiguous=True)
        elif case_context == "nom":
            entry = pair["ж"]
            return ParsedName(raw=token, canonical=entry.nominative,
                              genitive=entry.genitive, gender="ж",
                              confidence=0.9, was_ambiguous=True)
        else:
            entry = pair["м"]
            return ParsedName(raw=token, canonical=entry.nominative,
                              genitive=entry.genitive, gender="м",
                              confidence=0.7, was_ambiguous=True)

    # ── 2. Exact nominative match ──
    nom_entry = lookup_nominative(cap)
    if nom_entry:
        return ParsedName(raw=token, canonical=nom_entry.nominative,
                          genitive=nom_entry.genitive, gender=nom_entry.gender,
                          confidence=1.0)

    # ── 3. Genitive match ──
    gen_entries = lookup_genitive(cap)
    if gen_entries:
        if gender_hint and len(gen_entries) > 1:
            for e in gen_entries:
                if e.gender == gender_hint:
                    return ParsedName(raw=token, canonical=e.nominative,
                                      genitive=e.genitive, gender=e.gender,
                                      confidence=0.95)
        entry = gen_entries[0]
        return ParsedName(raw=token, canonical=entry.nominative,
                          genitive=entry.genitive, gender=entry.gender,
                          confidence=1.0)

    # ── 4. Fallback: heuristic ──
    if VALID_NAME_RE.match(cap):
        canonical, genitive, gender = _heuristic_normalize(cap)
        return ParsedName(raw=token, canonical=canonical,
                          genitive=genitive, gender=gender,
                          confidence=0.5)

    return None


def _heuristic_normalize(name: str) -> tuple[str, str, str]:
    """Heuristic: guess nominative, genitive, gender for names not in dictionary."""
    if name.endswith("ы"):
        return name[:-1] + "а", name, "ж"
    if name.endswith("ьи"):
        return name[:-1] + "я", name, "ж"
    if name.endswith("ии"):
        return name[:-2] + "ия", name, "ж"
    if name.endswith("а") and len(name) > 3:
        return name[:-1], name, "м"
    if name.endswith("я") and len(name) > 3:
        return name[:-1] + "й", name, "м"

    last = name[-1].lower()
    if last not in "аяоеуюыиьъ":
        return name, name + "а", "м"

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
      Pass 1: tokenize, extract prefixes (allowing 2 consecutive), collect raw name tokens.
              Detects "со чадом" / "со чады" suffix in each chunk.
      Pass 2: detect case context, resolve all tokens.
    """
    if not text or not text.strip():
        return []

    cleaned = strip_noise(text)
    if not cleaned:
        return []

    # ── Pass 1: Tokenize + extract prefixes + detect suffixes ──

    @dataclass
    class RawToken:
        text: str
        prefix: str | None = None
        suffix: str | None = None
        gender_hint: str | None = None

    raw_tokens: list[RawToken] = []

    chunks = NAME_DELIMITERS.split(cleaned)

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        # Detect "со чадом" / "со чады" at end of chunk
        chunk_suffix: str | None = None
        suffix_match = SUFFIX_RE.search(chunk)
        if suffix_match:
            raw_suffix = suffix_match.group(1).lower()
            # Normalize variants
            if "чадам" in raw_suffix:
                chunk_suffix = "со чады"
            elif "чадом" in raw_suffix:
                chunk_suffix = "со чадом"
            else:
                chunk_suffix = "со чады"
            chunk = chunk[:suffix_match.start()].strip()

        # Check for gender markers
        chunk_gender_hint: str | None = None
        if GENDER_MARKERS_FEM.search(chunk):
            chunk_gender_hint = "ж"
            chunk = GENDER_MARKERS_FEM.sub("", chunk).strip()
        elif GENDER_MARKERS_MASC.search(chunk):
            chunk_gender_hint = "м"
            chunk = GENDER_MARKERS_MASC.sub("", chunk).strip()

        tokens = chunk.split()
        current_prefixes: list[str] = []
        chunk_names_start = len(raw_tokens)

        i = 0
        while i < len(tokens):
            token = tokens[i].strip()
            if not token:
                i += 1
                continue

            # Lookup key: try lowercase with trailing dot stripped, then with dot
            key_no_dot = token.lower().rstrip(".")
            key_with_dot = token.lower()

            canonical_pfx = PREFIX_MAP.get(key_no_dot) or PREFIX_MAP.get(key_with_dot)
            if canonical_pfx:
                current_prefixes.append(canonical_pfx)
                i += 1
                continue

            # Combined prefix+name (no space): "отр.Тимофея"
            prefix_match = PREFIX_RE.match(token)
            if prefix_match:
                pfx_raw = prefix_match.group(1).lower()
                cpfx = PREFIX_MAP.get(pfx_raw.rstrip(".")) or PREFIX_MAP.get(pfx_raw)
                if cpfx:
                    current_prefixes.append(cpfx)
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

            cap = (clean_token[0].upper() + clean_token[1:].lower()
                   if len(clean_token) > 1 else clean_token.upper())
            entries = lookup_any(cap)

            if entries or VALID_NAME_RE.match(cap):
                # Gender hint: from prefix (first one that provides a hint), or chunk marker
                pfx_gender: str | None = None
                for pfx in current_prefixes:
                    hint = PREFIX_GENDER_HINTS.get(pfx)
                    if hint:
                        pfx_gender = hint
                        break
                gender_hint = chunk_gender_hint or pfx_gender

                combined_prefix = " ".join(current_prefixes) if current_prefixes else None

                raw_tokens.append(RawToken(
                    text=clean_token,
                    prefix=combined_prefix,
                    gender_hint=gender_hint,
                ))
                # Reset prefix accumulator after each name
                current_prefixes = []
            else:
                # Non-name token — reset prefixes
                current_prefixes = []

            i += 1

        # Attach suffix to the LAST name extracted from this chunk
        if chunk_suffix and len(raw_tokens) > chunk_names_start:
            raw_tokens[-1].suffix = chunk_suffix

    if not raw_tokens:
        return []

    # ── Pass 2: Detect context + resolve ──

    all_token_texts = [t.text for t in raw_tokens]
    case_context = _detect_case_context(all_token_texts)

    results: list[ParsedName] = []

    for rt in raw_tokens:
        parsed = _resolve_token(rt.text, case_context, rt.gender_hint)
        if parsed:
            parsed.prefix = rt.prefix
            parsed.suffix = rt.suffix
            results.append(parsed)

    return results


def extract_names_batch(texts: list[str | None]) -> list[list[ParsedName]]:
    """Extract names from a batch of texts."""
    return [extract_names(t) for t in texts]
