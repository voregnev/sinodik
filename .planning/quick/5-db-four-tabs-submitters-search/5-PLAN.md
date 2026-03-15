# Quick Task 5: Закладка БД — четыре вкладки, поиск по подателям

**Description:** Переделай закладку БД: четыре вкладки вверху — Податели, Поминовения, Записки, Словарь имён; податели — активный поиск по подстроке как в Списке имён.

---

## Task 1: Четыре вкладки вверху, Податели как равноправная вкладка

**Files:** `frontend/SinodikApp.jsx`

**Action:**
- In DbManagePage: replace current layout (SubmittersSection above + three tabs) with a single row of four tabs: Податели, Поминовения, Записки, Словарь имён. Section ids: `submitters`, `commemorations`, `orders`, `persons`.
- Only show these four tabs when user is admin. When not admin, do not show БД tab at all (existing behaviour).
- Remove the separate SubmittersSection block above the tabs; show SubmittersSection content only when `section === "submitters"` (as the content of the first tab).
- SubmittersSection: remove "expanded/collapsed" logic. It becomes a plain content panel: when the Податели tab is active, load users (useEffect when section === "submitters") and show the list. No "Свернуть" button; no single button that expands.

**Verify:** Open БД as admin → see four tabs; Податели shows list (loads on select); Поминовения / Записки / Словарь имён unchanged.

**Done:** Four equal tabs; Податели is first tab and shows list when selected.

---

## Task 2: Податели — активный поиск по подстроке (как Словарь имён)

**Files:** `frontend/SinodikApp.jsx`

**Action:**
- In SubmittersSection: add local state `search` (string). Add a search input above the list, same style as PersonManager: placeholder "Поиск по email...", value=search, onChange updates search. Filter the displayed list client-side: `filteredUsers = users.filter(u => u.email.toLowerCase().includes(search.trim().toLowerCase()))`. Show `filteredUsers` in the list (and "Нет пользователей" / "Нет совпадений" when filtered is empty). Dynamic filtering (no "Найти" button) — filter on every keystroke like a live search. Optionally show "Показано: N из M" when search is non-empty.

**Verify:** Open Податели, type in search → list filters by email substring; clear search → full list.

**Done:** Submitters list has live search by email substring.
