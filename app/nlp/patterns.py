"""
Regex patterns and prefix definitions for Slavic church name parsing.
Separated from name dictionary (names_dict.py).
"""

import re

# --- Known prefixes (church record modifiers) ---
# Maps raw patterns → normalized prefix label
PREFIX_MAP: dict[str, str] = {
    "воина":               "воин",
    "воин":                "воин",
    "мл.":                 "младенец",
    "мл":                  "младенец",
    "младенца":            "младенец",
    "младенец":            "младенец",
    "отр.":                "отрок",
    "отр":                 "отрок",
    "отрока":              "отрок",
    "отроковицы":          "отроковица",
    "отроковица":          "отроковица",
    "нп.":                 "новопреставленный",
    "нп":                  "новопреставленный",
    "новопреставленной":   "новопреставленный",
    "новопреставленного":  "новопреставленный",
    "новопреставленный":   "новопреставленный",
    "р.б.":                "раб Божий",
    "р.б":                 "раб Божий",
    "р. б.":               "раб Божий",
    "болящего":            "болящий",
    "болящей":             "болящая",
    "болящ.":              "болящий",
    "заблудшего":          "заблудший",
    "заблудшей":           "заблудшая",
    "путешествующего":     "путешествующий",
    "путешествующей":      "путешествующая",
    "непраздной":          "непраздная",
}

# ── Gender hints from prefix forms ──
# Суффикс "-его", "-ого" → мужской; "-ей", "-ой" → женский
PREFIX_GENDER_HINTS: dict[str, str] = {
    "воин":                "м",
    "младенец":            "м",   # м по умолч, но бывает и для девочек
    "отрок":               "м",
    "отроковица":          "ж",
    "болящий":             "м",
    "болящая":             "ж",
    "заблудший":           "м",
    "заблудшая":           "ж",
    "путешествующий":      "м",
    "путешествующая":      "ж",
    "непраздная":          "ж",
}

# Compiled regex: match any prefix at word boundary
_prefix_pattern = "|".join(
    re.escape(p) for p in sorted(PREFIX_MAP.keys(), key=len, reverse=True)
)
PREFIX_RE = re.compile(
    rf"(?:^|\s)({_prefix_pattern})[\.\s]*",
    re.IGNORECASE,
)

# Gender markers that can appear in parentheses or after name
GENDER_MARKERS_FEM = re.compile(r"\(\s*(?:жен\.?|ж\.?)\s*\)", re.IGNORECASE)
GENDER_MARKERS_MASC = re.compile(r"\(\s*(?:муж\.?|м\.?)\s*\)", re.IGNORECASE)

# --- Delimiters for splitting names ---
NAME_DELIMITERS = re.compile(r"[,;/\n\r\t]+")

# --- Noise filters: things that are NOT names ---
NOISE_PATTERNS = [
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),  # email
    re.compile(r"\*\d{4}"),                                                 # card
    re.compile(r"\+?\d[\d\s\-]{8,}"),                                      # phone
    re.compile(r"https?://\S+"),                                            # url
    re.compile(r"оплатил[аи]?\b.*", re.IGNORECASE),
    re.compile(r"напишите.*", re.IGNORECASE),
    re.compile(r"с праздником.*", re.IGNORECASE),
    re.compile(r"пожертвование.*", re.IGNORECASE),
    re.compile(r"средства пришли.*", re.IGNORECASE),
    re.compile(r"пропавшего без вести", re.IGNORECASE),
]

# --- Valid Slavic/church name pattern ---
VALID_NAME_RE = re.compile(r"^[А-ЯЁ][а-яё]{1,30}$")
