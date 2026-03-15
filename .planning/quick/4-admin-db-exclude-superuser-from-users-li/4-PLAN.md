# Quick Task 4: Admin БД — список пользователей и вкладка Заказы

**Description:** admin DB: exclude superuser from users list; users list UI like Names (quick delete icon, edit, link to Orders); do not show Submitters list by default; Orders button activates Orders tab with user filter.

---

## Task 1: Backend — exclude superuser from list, add DELETE user

**Files:** `app/api/routes/admin.py`, `tests/test_admin_routes.py`

**Action:**
- In `list_users` (GET /admin/users): filter out the superuser. After building the list from DB, exclude rows where `u.email.lower() == settings.superuser_email.lower()`, so the superuser never appears in the response.
- Add `DELETE /admin/users/{user_id}`: load user by id; if not found 404; if `user.email.lower() == settings.superuser_email.lower()` return 400 "Cannot delete the superuser account". Otherwise delete the user (e.g. `await db.delete(user)` then `await db.commit()`). Return 204 No Content. Protect with `require_admin`. Optional: if deleting the last admin, return 400 (same logic as PATCH).
- Add test: list_users does not return superuser when superuser exists; admin DELETE non-superuser returns 204; DELETE superuser returns 400.

**Verify:** `docker compose run --rm api pytest tests/test_admin_routes.py -v -x`

**Done:** GET /admin/users excludes superuser; DELETE /admin/users/{id} exists with superuser guard; tests pass.

---

## Task 2: Frontend — Податели collapsed by default, list UI like Словарь имён

**Files:** `frontend/SinodikApp.jsx`

**Action:**
- **Collapsed by default:** SubmittersSection does not load or show the users list on mount. Show a single button "Податели" (same styling as section tabs). On first click: set expanded=true, call api("/admin/users") and show the list. So state: `expanded` (bool), `users`, `loading`; when !expanded render only the button; when expanded render list (and loading state while fetch).
- **Row UI like PersonManager (Словарь имён):** Each row: left — email + line with "Записок: X · Активных: Y"; right — edit icon (pencil), delete icon (trash), then link/button "Заказы". Use same card style (borderLeft 3px purple, padding, borderRadius 8). Edit: inline form for role (admin/user) and is_active (checkbox or toggle), Save/Cancel. Delete: on click call DELETE /api/v1/admin/users/{id} (with confirm "Удалить пользователя …?"), then refresh list. Заказы: call `onSelectOrders(u.email)` so that parent switches to section "orders" with filterByUserEmail.
- Ensure "Заказы" in a row activates the Записки tab with user filter (already implemented via onSelectOrders in DbManagePage).

**Verify:** Manual: open БД as admin, Податели not shown until button click; list has edit, delete, Заказы; Заказы opens Записки with filter; delete and edit work.

**Done:** Податели load on demand; list matches Names style with edit/delete/Заказы; Orders tab activates with user filter.
