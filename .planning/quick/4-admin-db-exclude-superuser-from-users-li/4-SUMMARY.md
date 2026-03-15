# Quick 4: Admin БД — список подателей и вкладка Заказы — Summary

**Done:**
- Backend: GET /admin/users excludes superuser; DELETE /admin/users/{id} with superuser and last-admin guard; tests added.
- Frontend: Податели section collapsed by default (button "Податели"); on click loads list. List UI like Словарь имён: edit icon (inline role + is_active), delete icon (confirm + DELETE), "Заказы" button → activates Записки tab with filter by user. Superuser not shown in list (backend filter).

**Commits:**
- 2859264 feat(admin): exclude superuser from GET /admin/users, add DELETE /admin/users/{id}
- e461395 feat(admin): Податели collapsed by default, list like Names (edit, delete, Заказы)
